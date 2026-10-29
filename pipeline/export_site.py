"""Site export: facts table -> site/public/fable/data/{meta,players,stats}.json (docs/site-data.md).

Second and third stages of the compute step: pull dedup across reports, reset weeks,
15-week qualification, raid tiers and PvP ranks, then every stat as additive cells
(player, expansion, class, role). Stats that need data not crawled yet are exported
empty and listed in meta.pending.

Usage:
    python -m pipeline.export_site            # from the raw crawl cache
"""

import bisect
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pipeline.facts import CACHE_DIR, CONFIG, ROOT, _payload, add_scores, load_mapping, norm, pull_rows, pulls_from_cache

OUT_DIR = ROOT / "site" / "public" / "fable" / "data"
WEEK_MS = 7 * 24 * 3600 * 1000
EXP_INDEX = {"classic": 0, "tbc": 1, "wotlk": 2, "cata": 3, "mop": 4}
ROLES = ["TANK", "DPS", "HEALER"]
CLASSES = ["Death Knight", "Druid", "Hunter", "Mage", "Monk", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"]
CLASS_NAME = {"DeathKnight": "Death Knight"}
# Stats that need data the crawl does not have yet (docs/stats.md) or a model still to write.
PENDING = set()  # stats with no computation yet (shown as such on the site)


def load(name: str) -> dict:
    return json.loads((ROOT / "config" / f"{name}.json").read_text(encoding="utf-8"))


# --- pulls -------------------------------------------------------------------

def dedup(pulls: dict) -> dict:
    """Same boss pull logged in two reports (overlapping times): keep the report with the most boss pulls."""
    per_report = Counter(rs[0]["report"] for rs in pulls.values())
    groups = defaultdict(list)
    for src, rs in pulls.items():
        r = rs[0]
        groups[(r["encounter_id"], r["difficulty"])].append((r["start_ms"], r["start_ms"] + r["duration_ms"], src, r["report"]))
    drop = set()
    for items in groups.values():
        items.sort()
        cluster, end = [], -1
        for it in items + [(float("inf"), 0, None, None)]:
            if it[0] > end and cluster:
                reports = {c[3] for c in cluster}
                if len(reports) > 1:
                    keep = max(sorted(reports), key=lambda rep: per_report[rep])  # ties: first code, for a stable export
                    drop.update(c[2] for c in cluster if c[3] != keep)
                cluster, end = [], -1
            if it[2] is not None:
                cluster.append(it)
                end = max(end, it[1])
    print(f"dedup: {len(drop)} pulls dropped (logged twice)")
    return {s: rs for s, rs in pulls.items() if s not in drop}


# --- cells -------------------------------------------------------------------

class Cells:
    """Accumulates additive values per (stat, player, expansion, class, role)."""

    def __init__(self):
        self.data = defaultdict(dict)

    def _get(self, sid, key, init):
        d = self.data[sid]
        if key not in d:
            d[key] = init()
        return d[key]

    def ratio(self, sid, key, num, den=1):
        a = self._get(sid, key, lambda: [0.0, 0.0]); a[0] += num; a[1] += den

    def parse(self, sid, key, best, median):
        """One boss of Parse Lord: (best + median) / 2, plus best and median themselves."""
        v = self._get(sid, key, lambda: [0.0, 0, 0.0, 0.0])
        v[0] += (best + median) / 2; v[1] += 1; v[2] += best; v[3] += median

    def sum(self, sid, key, n):
        self._get(sid, key, lambda: [0.0])[0] += n

    def ids(self, sid, key, x):
        self._get(sid, key, set).add(x)

    def diff(self, sid, key, a, ad, b, bd):
        v = self._get(sid, key, lambda: [0.0] * 4); v[0] += a; v[1] += ad; v[2] += b; v[3] += bd

    def spread(self, sid, key, x):
        v = self._get(sid, key, lambda: [0, 0.0, 0.0]); v[0] += 1; v[1] += x; v[2] += x * x

    def slope(self, sid, key, x, y, tier=None):
        """Regression sums, plus the raid tiers of the points (a stat can ask for a minimum of tiers)."""
        v = self._get(sid, key, lambda: [0, 0.0, 0.0, 0.0, 0.0, set()]); v[0] += 1; v[1] += x; v[2] += y; v[3] += x * x; v[4] += x * y
        if tier is not None:
            v[5].add(tier)

    def top(self, sid, key, label, num, den=1):
        t = self._get(sid, key, dict).setdefault(label, [0.0, 0])
        t[0] += num; t[1] += den

    def best(self, sid, key, v, label):
        cur = self._get(sid, key, lambda: [float("-inf"), None])
        if v > cur[0]:
            cur[0], cur[1] = v, label

    def export(self, stat_ids) -> dict:
        out = {}
        for sid in stat_ids:
            cells = []
            for (p, e, c, r), v in self.data.get(sid, {}).items():
                if isinstance(v, set):
                    vals = [sorted(v)]
                elif isinstance(v, dict):
                    vals = [{k: [round(a, 1), b] for k, (a, b) in v.items()}]
                else:
                    vals = [round(x, 4) if isinstance(x, float) else sorted(x) if isinstance(x, set) else x for x in v]
                cells.append([p, e, c, r, *vals])
            out[sid] = cells
        return out


def base100(rows, metric, group_key):
    """{id(row): 100 * value / median of its group}. As the performance scores (facts.add_scores), the median
    leaves out the rows at 0 and needs min_score_peers of them: a median of 1 (a short pull where nearly
    nobody was healed) gave values in the millions. Groups below that are skipped."""
    groups = defaultdict(list)
    for r in rows:
        if r.get(metric) is not None:
            groups[group_key(r)].append(r)
    out = {}
    for rs in groups.values():
        active = [r[metric] for r in rs if r[metric] > 0]
        if len(active) < CONFIG["min_score_peers"]:
            continue
        med = statistics.median(active)
        if med:
            for r in rs:
                out[id(r)] = 100 * r[metric] / med
    return out


def ilvl_residuals(kills: list) -> dict:
    """Overachiever: {id(row): score minus the mean score of other guild players at the same gear level}.

    Gear level = item level minus the median of the same role in the pull. Peers: other players,
    same expansion and role, within the expansion's ilvl tolerance (config "overachiever").
    """
    tol_cfg = CONFIG["overachiever"]["ilvl_tolerance"]
    by_pull = defaultdict(list)
    for r in kills:
        by_pull[(r["source"], r["role"])].append(r["ilvl"])
    groups = defaultdict(list)
    for r in kills:
        rel = r["ilvl"] - statistics.median(by_pull[(r["source"], r["role"])])
        groups[(r["expansion"], r["role"])].append((rel, r["score"], r["player"], r))

    out = {}
    for (exp, _), items in groups.items():
        tol = tol_cfg.get(exp, tol_cfg["default"])
        items.sort(key=lambda x: x[0])
        xs = [x[0] for x in items]
        prefix = [0.0]
        for x in items:
            prefix.append(prefix[-1] + x[1])
        # The same sums per player, to take his own kills out of his peers.
        mine = defaultdict(lambda: ([], [0.0]))
        for rel, score, pl, _ in items:
            xs_p, pre_p = mine[pl]
            xs_p.append(rel)
            pre_p.append(pre_p[-1] + score)
        for rel, score, pl, r in items:
            lo, hi = bisect.bisect_left(xs, rel - tol), bisect.bisect_right(xs, rel + tol)
            xs_p, pre_p = mine[pl]
            plo, phi = bisect.bisect_left(xs_p, rel - tol), bisect.bisect_right(xs_p, rel + tol)
            n = (hi - lo) - (phi - plo)
            if n >= CONFIG["overachiever"]["min_peers"]:
                total = (prefix[hi] - prefix[lo]) - (pre_p[phi] - pre_p[plo])
                out[id(r)] = score - total / n
    return out


# Career totals comparable across expansions (compute.json scaled_totals_tier): stat -> (row field, reference
# players, average). Damage taken uses the raid's mean, not its median: in a 40-man raid the median player
# takes next to nothing and tanks would be worth huge multiples of it.
SCALED = {"damage-done-bosses": ("damage_done", "DPS", statistics.median), "healing-done": ("healing_done", "HEALER", statistics.median),
          "damage-taken": ("damage_taken", None, statistics.mean)}


def scaled_totals(rows: list, ref_tier: int) -> tuple[dict, dict, dict]:
    """(id(row), stat) -> the row's amount at the reference tier's level: amount / median rate of the
    reference players of its pull (seconds of an average raider) x the guild's median rate on the
    reference tier's kills. Pulls without reference players (no healer) or of zero length count 0.
    Also returns, per stat, the rate of each pull and the reference rate (trash damage uses them)."""
    by_pull = defaultdict(list)
    for r in rows:
        by_pull[r["source"]].append(r)
    out, rates, refs_by_stat = {}, {}, {}
    for sid, (field, role, average) in SCALED.items():
        rate, refs = {}, []
        for src, rs in by_pull.items():
            sec = (rs[0]["duration_ms"] or 0) / 1000
            vals = [r[field] for r in rs if role is None or r["role"] == role]
            m = average(vals) / sec if vals and sec > 0 else 0
            if m > 0:
                rate[src] = m
                if rs[0]["kill"] and rs[0]["tier"] == ref_tier:
                    refs.append(m)
        ref = statistics.median(refs)
        rates[sid], refs_by_stat[sid] = rate, ref
        print(f"scaled {sid}: reference {ref:,.0f}/s on {len(refs)} kills")
        for r in rows:
            if r["source"] in rate:
                out[(id(r), sid)] = r[field] / rate[r["source"]] * ref
    return out, rates, refs_by_stat


def trash_damage(pulls: dict, rate: dict, ref: float, tz) -> list:
    """Damage Done (bosses and trash): [(boss row of the character that night, scaled trash, actual trash)].

    Trash damage comes from reports/<code>/trash.json (pipeline/crawl_extra.py, one table per report). When a
    night was logged in several reports, only the one holding the most kept boss pulls counts, so the trash
    is not counted twice. A character's trash goes to his role and expansion of the night (his most played
    role in that report's boss pulls) and is scaled like his boss damage: divided by the median of the
    night's pull rates (median DPS rate of each pull), times the reference rate."""
    by_night = defaultdict(lambda: defaultdict(list))
    for src, rs in pulls.items():
        by_night[raid_night(rs[0]["start_ms"], tz)][rs[0]["report"]].append(src)
    out = []
    for reports in by_night.values():
        code, srcs = max(reports.items(), key=lambda kv: (len(kv[1]), kv[0]))
        path = CACHE_DIR / "classic" / "reports" / code / "trash.json"
        night_rates = [rate[s] for s in srcs if s in rate]
        if not path.exists() or not night_rates:
            continue
        factor = ref / statistics.median(night_rates)
        mine = defaultdict(list)
        for s in srcs:
            for r in pulls[s]:
                mine[r["char"]].append(r)
        for e in _payload(path)["report"]["trash"]["data"].get("entries", []):
            rs = mine.get(e.get("name"))
            if rs and e.get("total"):
                role = Counter(r["role"] for r in rs).most_common(1)[0][0]
                row = next(r for r in rs if r["role"] == role)
                out.append((row, e["total"] * factor, e["total"]))
    return out


def raid_time(rows: list) -> dict:
    """Hours Raiding: {id(row): ms}. Each raid night of a character counts from his first to his last
    boss pull (same nights as the home page's Hours in raid: a report is cut at gaps longer than
    night_gap_hours). The time is spread over his pulls (from the end of the previous one to the end
    of this one), so it adds up per expansion, class and role."""
    gap = CONFIG["night_gap_hours"] * 3_600_000
    mine = defaultdict(list)
    for r in rows:
        mine[(r["report"], r["char"])].append(r)
    out = {}
    for rs in mine.values():
        rs.sort(key=lambda r: r["start_ms"])
        prev_end = None
        for r in rs:
            end = r["start_ms"] + r["duration_ms"]
            if prev_end is None or r["start_ms"] - prev_end > gap:
                out[id(r)] = r["duration_ms"]  # first pull of a night
            else:
                out[id(r)] = max(0, end - prev_end)
            prev_end = end if prev_end is None else max(prev_end, end)
    return out


def timekeeper(rows: list, pid: dict, char_class: dict, cells) -> None:
    """Timekeeper / The Tourist: each DPS's share of the raid's trash damage over a report (one night,
    cache reports/<code>/trash.json from pipeline/crawl_extra.py), base 100 vs the night's DPS median,
    then divided by the mean of his class in the expansion (AoE classes do far more trash damage).
    A character's role and expansion for the night are those of his boss pulls in that report; one who
    tanked a boss that night is left out (he probably tanked the trash too)."""
    by_report = defaultdict(lambda: defaultdict(Counter))
    exp_of = {}
    for r in rows:
        by_report[r["report"]][r["char"]][r["role"]] += 1
        exp_of[r["report"]] = r["e"]
    owner = {r["char"]: r["player"] for r in rows}
    values = []  # (character, expansion, base 100 vs the night)
    for code, chars in by_report.items():
        path = CACHE_DIR / "classic" / "reports" / code / "trash.json"
        if not path.exists():
            continue
        entries = _payload(path)["report"]["trash"]["data"].get("entries", [])
        dmg = {e["name"]: e.get("total", 0) for e in entries if e.get("name") in chars}
        total = sum(dmg.values())
        dps = {ch: d / total for ch, d in dmg.items()
               if total and chars[ch].most_common(1)[0][0] == "DPS" and not chars[ch]["TANK"]}
        if len(dps) < CONFIG["min_players"] // 2:
            continue  # no real trash in this report
        med = statistics.median(dps.values())
        if med:
            values += [(ch, exp_of[code], 100 * share / med) for ch, share in dps.items() if ch in char_class]
    by_class = defaultdict(list)
    for ch, e, v in values:
        by_class[(e, char_class[ch])].append(v)
    class_mean = {k: statistics.mean(v) for k, v in by_class.items()}
    for ch, e, v in values:
        mean = class_mean[(e, char_class[ch])]
        if mean and owner[ch] in pid:
            k = (pid[owner[ch]], e, CLASSES.index(char_class[ch]), ROLES.index("DPS"))
            cells.ratio("timekeeper", k, 100 * v / mean)


def parse_lord(rows: list, pid: dict, char_class: dict, cells) -> None:
    """Parse Lord: WCL parses (cache reports/<code>/rankings.json from pipeline/crawl_extra.py), the
    only stat ranked against the world. Per cell and boss, (best + median parse) / 2; one value per boss."""
    parses, loaded = {}, set()
    for r in rows:
        code = r["report"]
        if code in loaded:
            continue
        loaded.add(code)
        path = CACHE_DIR / "classic" / "reports" / code / "rankings.json"
        if not path.exists():
            continue
        for fight in _payload(path)["report"]["rankings"].get("data", []):
            for role in (fight.get("roles") or {}).values():
                for ch in role.get("characters", []):
                    if ch.get("rankPercent") is not None:
                        parses[(code, fight["fightID"], ch["name"])] = ch["rankPercent"]
    groups = defaultdict(list)
    for r in rows:
        x = parses.get((r["report"], r["fight"], r["char"]))
        if x is None or not r["kill"] or r["role"] not in ("DPS", "HEALER") or r["player"] not in pid or r["char"] not in char_class:
            continue
        k = (pid[r["player"]], r["e"], CLASSES.index(char_class[r["char"]]), ROLES.index(r["role"]))
        groups[(k, r["encounter_id"], r["difficulty"])].append(x)
    for (k, _, _), xs in groups.items():
        cells.parse("parse-lord", k, max(xs), statistics.median(xs))


def raid_night(start_ms: int, tz) -> str:
    """Raid night of a pull: its local date, 6 hours back so that pulls after midnight stay on their evening."""
    return (datetime.fromtimestamp(start_ms / 1000, tz) - timedelta(hours=6)).date().isoformat()


def late_and_early(pulls: dict, tz) -> dict:
    """Late Arrival / Early Leaver: {(night, player): (first row, last row, late, early)}.

    A night's first and last bosses are the encounters (with difficulty) of its first and last pulls,
    across every report of the night. A player is late when he is in none of the pulls of the first
    boss, early when in none of the last boss's. Nights with a single boss are left out."""
    nights = defaultdict(list)
    for rs in pulls.values():
        nights[raid_night(rs[0]["start_ms"], tz)].append(rs)
    boss = lambda r: (r["encounter_id"], r["difficulty"])
    out = {}
    for night, ps in nights.items():
        ps.sort(key=lambda rs: rs[0]["start_ms"])
        first, last = boss(ps[0][0]), boss(ps[-1][0])
        if first == last:
            continue
        mine = defaultdict(list)
        for rs in ps:
            for r in rs:
                mine[r["player"]].append(r)
        for pl, rs in mine.items():
            bosses = {boss(r) for r in rs}
            out[(night, pl)] = (rs[0], rs[-1], first not in bosses, last not in bosses)
    return out


def suicide_pacts(rs: list) -> list:
    """Suicide Pact: pairs of rows of one pull whose players died within window_s of each other, counting
    only the deaths before max_dead_share of the raid is down (the wipe itself would pair everyone)."""
    cfg = CONFIG["suicide_pact"]
    deaths = sorted((t, r["player"], i) for i, r in enumerate(rs) for t in json.loads(r["death_times"]))
    deaths = deaths[: int(len(rs) * cfg["max_dead_share"])]
    pairs = set()
    for a, (ta, pa, ia) in enumerate(deaths):
        for tb, pb, ib in deaths[a + 1:]:
            if tb - ta > cfg["window_s"] * 1000:
                break
            if pa != pb:
                pairs.add((ia, ib))
    return [(rs[a], rs[b]) for a, b in pairs]


# --- main --------------------------------------------------------------------

def main() -> None:
    tiers_cfg, stats_cfg, site_cfg = load("tiers"), load("stats")["stats"], load("site")
    owner = load_mapping()
    issues = Counter()
    rows = [row for p in pulls_from_cache() for row in pull_rows(p, owner, issues)]
    add_scores(rows)
    pulls = defaultdict(list)
    for r in rows:
        pulls[r["source"]].append(r)
    pulls = dedup(pulls)
    rows = [r for rs in pulls.values() for r in rs]

    anchor = datetime.fromisoformat(CONFIG["reset_anchor_utc"]).replace(tzinfo=timezone.utc).timestamp() * 1000
    tz = ZoneInfo(CONFIG["timezone"])
    exp_ids = [x["id"] for x in tiers_cfg["expansions"]]
    tier_of = {}
    for i, t in enumerate(tiers_cfg["tiers"]):
        for z in t["zones"]:
            tier_of[(exp_ids.index(t["expansion"]), z)] = i
    # The zone is the report's, not the fight's: a report labeled Zul'Aman can hold Sunwell pulls.
    # So a boss takes the tier its pulls most often have across the guild's logs.
    boss_tiers = defaultdict(Counter)
    for r in rows:
        r["e"] = EXP_INDEX[r["expansion"]]
        t = tier_of.get((r["e"], r["zone"]))
        if t is not None:
            boss_tiers[(r["e"], r["encounter_id"])][t] += 1
    boss_tier = {k: c.most_common(1)[0][0] for k, c in boss_tiers.items()}
    unknown_zones = Counter()
    for r in rows:
        r["week"] = int((r["start_ms"] - anchor) // WEEK_MS)
        r["tier"] = boss_tier.get((r["e"], r["encounter_id"]))
        if r["tier"] is None:
            unknown_zones[(r["expansion"], r["zone"])] += 1
        r["heal_targets"] = json.loads(r["heal_targets"]) if isinstance(r["heal_targets"], str) else r["heal_targets"]
    for z, n in unknown_zones.items():
        print(f"WARNING zone without a tier: {z} ({n} rows)")

    # Character class: its most frequent known class.
    seen = defaultdict(Counter)
    for r in rows:
        if r["class"] and r["class"] != "Unknown":
            seen[r["char"]][CLASS_NAME.get(r["class"], r["class"])] += 1
    char_class = {ch: c.most_common(1)[0][0] for ch, c in seen.items()}

    # Qualification and ranks, on all characters of a player.
    weeks, tier_weeks, char_pulls, exp_mask = defaultdict(set), defaultdict(lambda: defaultdict(set)), defaultdict(Counter), defaultdict(int)
    role_weeks, char_weeks = defaultdict(lambda: defaultdict(set)), defaultdict(set)
    for r in rows:
        weeks[r["player"]].add(r["week"])
        char_weeks[r["char"]].add(r["week"])
        role_weeks[r["player"]][r["role"]].add(r["week"])
        if r["tier"] is not None:
            tier_weeks[r["player"]][r["tier"]].add(r["week"])
        char_pulls[r["player"]][r["char"]] += 1
        exp_mask[r["player"]] |= 1 << r["e"]
    qualified = sorted((pl for pl, w in weeks.items() if len(w) >= 15), key=norm)
    pid = {pl: i for i, pl in enumerate(qualified)}
    min_w, max_rank = tiers_cfg["rank"]["min_weeks_per_tier"], tiers_cfg["rank"]["max"]
    players, char_id = [], {}
    for pl in qualified:
        chars = sorted(char_pulls[pl], key=lambda ch: (ch != pl, -char_pulls[pl][ch]))
        for ch in chars:
            char_id[ch] = len(char_id)
        # A tier may set its own min_weeks (short tiers, e.g. Naxx in Era: 5 weeks of logs before TBC).
        tiers = sorted(t for t, w in tier_weeks[pl].items() if len(w) >= tiers_cfg["tiers"][t].get("min_weeks", min_w))
        # [name, class index (null if unknown), reset weeks]: every character, the site hides the class of minor ones.
        players.append({"name": pl, "chars": [[ch, CLASSES.index(char_class[ch]) if ch in char_class else None, len(char_weeks[ch])] for ch in chars],
                        "tiers": tiers, "rank": min(max_rank, len(tiers)),
                        "role_weeks": [len(role_weeks[pl][role]) for role in ROLES]})
    print(f"players: {len(weeks)} seen, {len(qualified)} qualified (15+ reset weeks)")
    # Ghosts of Fable: everyone else seen in eligible pulls, [name, reset weeks, expansion mask, class of
    # their most played character]; most weeks first.
    ghosts = []
    for pl in weeks:
        if pl in pid:
            continue
        top = next((char_class[ch] for ch, _ in char_pulls[pl].most_common() if char_class.get(ch) in CLASSES), None)
        ghosts.append([pl, len(weeks[pl]), exp_mask[pl], CLASSES.index(top) if top else None])
    ghosts.sort(key=lambda g: (-g[1], norm(g[0])))

    # Best friend: for each ranked player, the ranked player(s) he shared the most raid nights with. Two
    # players share a night when they were in at least one same eligible pull that night (a night is the
    # Sydney date, 6 hours back so that pulls after midnight stay on their evening).
    shared = defaultdict(set)
    for rs in pulls.values():
        here = sorted({r["player"] for r in rs if r["player"] in pid})
        if len(here) < 2 or rs[0]["start_ms"] is None:
            continue
        night = raid_night(rs[0]["start_ms"], tz)
        for i, a in enumerate(here):
            for b in here[i + 1:]:
                shared[(a, b)].add(night)
    together = defaultdict(Counter)
    for (a, b), nights in shared.items():
        together[a][b] = together[b][a] = len(nights)
    for pl in players:
        c = together[pl["name"]]
        best = max(c.values(), default=0)
        pl["friends"] = {"names": sorted((n for n, k in c.items() if k == best), key=norm), "nights": best} if best else None

    # Guild-wide references, on every row (qualified or not).
    boss_key = lambda r: (r["encounter_id"], r["difficulty"])
    kills = [r for r in rows if r["kill"]]
    first_kill = {}
    for r in sorted(kills, key=lambda r: r["start_ms"]):
        first_kill.setdefault(boss_key(r), r["source"])
    kill_duration = defaultdict(list)
    for src, rs in pulls.items():
        if rs[0]["kill"]:
            kill_duration[boss_key(rs[0])].append(rs[0]["duration_ms"])
    med_duration = {k: statistics.median(v) for k, v in kill_duration.items()}

    tank_total = Counter()
    for r in rows:
        if r["role"] == "TANK":
            tank_total[r["source"]] += r["damage_taken"]
    for r in rows:
        r["tank_share"] = r["damage_taken"] / tank_total[r["source"]] if r["role"] == "TANK" and tank_total[r["source"]] else None
    tanks_k = [r for r in kills if r["role"] == "TANK"]
    sponge = base100(tanks_k, "tank_share", boss_key)
    secret = base100(tanks_k, "damage_done", boss_key)
    # Healers Love Him: healing received from others (self-healing, potions and healthstones left out), base 100
    # vs the role in the pull, then vs the mean of his class and role in the expansion: warlocks (Life Tap) are
    # healed far more than other DPS. A mean, not a median: most DPS of some classes get no heal at all.
    for r in rows:
        r["received_others"] = r["healing_received"] - r["self_healing"]
    received = base100(rows, "received_others", lambda r: (r["source"], r["role"]))
    by_class = defaultdict(list)
    for r in rows:
        if id(r) in received:
            by_class[(r["e"], r["class"], r["role"])].append(received[id(r)])
    class_med = {k: statistics.mean(v) for k, v in by_class.items()}
    for r in rows:
        if id(r) in received:
            med = class_med[(r["e"], r["class"], r["role"])]
            if med:
                received[id(r)] = 100 * received[id(r)] / med
            else:
                del received[id(r)]
    magnet = base100(rows, "avoidable_taken", lambda r: (r["source"], r["role"]))
    healers_k = [r for r in kills if r["role"] == "HEALER"]
    smite = base100(healers_k, "damage_done", lambda r: r["source"])
    # Sniped / Sniper: overheal share, base 100 vs the healers of the same class and expansion. Overheal depends
    # mostly on the class (Beacon of Light paladins 73% in WotLK, Discipline priests' shields 23%).
    for r in rows:
        done = r["healing_done"] + r["overheal"]
        r["overheal_share"] = r["overheal"] / done if r["role"] == "HEALER" and done else None
    sniped = base100([r for r in rows if r["role"] == "HEALER"], "overheal_share", lambda r: (r["e"], r["class"]))
    for r in rows:
        r["fiend"] = min(r["avoidable_taken"], r["self_healing"]) if r["role"] == "HEALER" else None
    fiend = base100([r for r in rows if r["role"] == "HEALER"], "fiend", lambda r: r["source"])
    one_button = base100([r for r in kills if r["role"] == "DPS"], "top_ability_share", lambda r: (r["class"], r["e"]))
    over = ilvl_residuals([r for r in kills if r["role"] in ("DPS", "HEALER") and r["score"] is not None
                           and r["ilvl"] not in (None, "")])

    # Black Cat: wipe rate on a boss when the player is there, vs the guild's rate on that boss without him.
    boss_pulls, boss_wipes = Counter(), Counter()
    present = defaultdict(set)
    for src, rs in pulls.items():
        boss_pulls[boss_key(rs[0])] += 1
        boss_wipes[boss_key(rs[0])] += not rs[0]["kill"]
        for r in rs:
            present[r["player"]].add(src)
    mine_pulls, mine_wipes = Counter(), Counter()
    for pl in qualified:
        for src in present[pl]:
            r0 = pulls[src][0]
            mine_pulls[(pl, boss_key(r0))] += 1
            mine_wipes[(pl, boss_key(r0))] += not r0["kill"]

    # Iron Man / Comeback Kid: weeks numbered among the weeks the guild raided, so guild breaks are not absences.
    guild_week = {w: i for i, w in enumerate(sorted({r["week"] for r in rows}))}
    # Loot Hoarder: item levels of each kill, to count the players he out-gears.
    ilvls = defaultdict(list)
    for r in kills:
        if r["ilvl"] not in (None, ""):
            ilvls[r["source"]].append(r["ilvl"])
    for v in ilvls.values():
        v.sort()
    # Obliterated: biggest overkill, as a multiple of the median overkill of the expansion (health pools grow
    # with each one). Instant kill mechanics (every death to them far above that median) are left out.
    ob_cfg, exp_overkills, ability_overkills = CONFIG["obliterated"], defaultdict(list), defaultdict(list)
    for r in rows:
        if r["overkill"]:
            exp_overkills[r["e"]].append(r["overkill"])
            ability_overkills[(r["e"], boss_key(r), r["overkill_by"])].append(r["overkill"])
    med_overkill = {e: statistics.median(v) for e, v in exp_overkills.items()}
    instakills = {k for k, v in ability_overkills.items()
                  if len(v) >= ob_cfg["min_deaths"] and min(v) > ob_cfg["instakill_factor"] * med_overkill[k[0]]}
    print("obliterated: instant kills left out:", ", ".join(sorted({a for _, _, a in instakills})) or "none")
    row_of = {(r["source"], r["char"]): r for r in rows}
    ranked = lambda r: r["player"] in pid and r["char"] in char_class
    key_of = lambda r: (pid[r["player"]], r["e"], CLASSES.index(char_class[r["char"]]), ROLES.index(r["role"]))
    nemesis_ignore = set(CONFIG["arch_nemesis_ignore"])

    interruptible = {src for src, rs in pulls.items() if any(r["interrupts"] for r in rs)}
    raid_taken = {src: sum(r["damage_taken"] for r in rs) for src, rs in pulls.items()}
    final_bosses = set(CONFIG["final_bosses"])
    boss_ids = {}

    raid_ms = raid_time(rows)
    ref_tier = next(i for i, t in enumerate(tiers_cfg["tiers"]) if t["id"] == CONFIG["scaled_totals_tier"])
    scaled, scaled_rates, scaled_refs = scaled_totals(rows, ref_tier)

    cells = Cells()
    for r in rows:
        if r["player"] not in pid or r["char"] not in char_class:
            continue
        k = (pid[r["player"]], r["e"], CLASSES.index(char_class[r["char"]]), ROLES.index(r["role"]))
        kill, wipe, score, role = r["kill"], not r["kill"], r["score"], r["role"]
        dead = bool(r["deaths"] or r["deaths_scripted"])

        cells.sum("hours-played", k, raid_ms[id(r)] / 3_600_000)
        cells.sum("boss-kills", k, kill)
        cells.sum("wipes", k, wipe)
        for sid, (field, _, _) in SCALED.items():
            cells.ratio(sid, k, scaled.get((id(r), sid), 0.0), r[field])  # [scaled, actual]
        cells.ratio("damage-done", k, scaled.get((id(r), "damage-done-bosses"), 0.0), r["damage_done"])
        cells.ids("the-gang", k, r["week"])
        if len(char_weeks[r["char"]]) >= site_cfg["min_char_weeks"]:  # minor rerolls do not count
            cells.ids("identity-crisis", k, char_id[r["char"]])
        cells.ids("iron-man", k, guild_week[r["week"]])
        cells.ids("comeback-kid", k, guild_week[r["week"]])
        bk = boss_key(r)
        if kill:
            cells.ids("kill-collector", k, boss_ids.setdefault(bk, len(boss_ids)))
            if first_kill.get(bk) == r["source"]:
                cells.ids("pioneer", k, boss_ids[bk])
            cells.ratio("spectator", k, r["deaths"] > 0)
            raid = ilvls.get(r["source"], [])
            if r["ilvl"] not in (None, "") and len(raid) > 1:
                below = bisect.bisect_left(raid, r["ilvl"])
                ties = bisect.bisect_right(raid, r["ilvl"]) - below - 1
                cells.ratio("loot-hoarder", k, (below + ties / 2) / (len(raid) - 1))
        else:
            if r["boss_pct"] is not None:
                cells.ratio("heartbreaker", k, r["boss_pct"] < CONFIG["heartbreak_pct"])
            cells.top("personal-hell", k, r["encounter"], 1)
        cells.ratio("the-immortal", k, wipe)
        absent = boss_pulls[bk] - mine_pulls[(r["player"], bk)]
        if absent > 0:
            cells.diff("black-cat", k, wipe, 1, (boss_wipes[bk] - mine_wipes[(r["player"], bk)]) / absent, 1)
        cells.ratio("fishbait", k, r["first_death"])
        cells.ratio("floor-inspector", k, r["deaths"])
        if wipe:
            cells.ratio("the-roach", k, not dead)
        if kill and not dead and (r["pull_players"] - r["pull_dead"]) < r["pull_players"] / 2:
            cells.sum("last-stand", k, 1)
        if r["killed_by"] and r["killed_by"] not in nemesis_ignore:
            cells.top("arch-nemesis", k, r["killed_by"], 1)
        if r["overkill"] and (r["e"], bk, r["overkill_by"]) not in instakills:
            day = datetime.fromtimestamp(r["start_ms"] / 1000, tz).date().isoformat()
            cells.best("obliterated", k, r["overkill"] / med_overkill[r["e"]], f"{r['overkill_by']} · {r['encounter']} · {day}")
        if r["healing_received"]:
            cells.ratio("self-made", k, r["self_healing"] / r["healing_received"])
        if r["friendly_fire"] is not None and raid_taken[r["source"]]:
            cells.ratio("the-terrorist", k, r["friendly_fire"] / raid_taken[r["source"]])
        if id(r) in received:
            cells.ratio("healers-love-him", k, received[id(r)])
        if id(r) in magnet:
            cells.ratio("mechanic-magnet", k, magnet[id(r)])
        cells.ratio("the-junky", k, r["potions"] + r["healthstones"])
        if kill and r["enchantable_slots"]:
            cells.ratio("the-unprepared", k, 1 - r["enchanted_slots"] / r["enchantable_slots"])
        if r["source"] in interruptible:
            cells.ratio("the-nut-crusher", k, r["interrupts"])
        cells.ratio("the-janitor", k, r["dispels"])
        if r["duration_ms"]:
            cells.ratio("the-sweat", k, min(1, r["casts_active_ms"] / r["duration_ms"]))
        # Performance scores of DPS and healers only: a tank's score is his damage taken, not a performance.
        if kill and score is not None and role != "TANK":
            cells.spread("metronome", k, score)
            cells.top("comfort-boss", k, r["encounter"], score)
            cells.slope("glow-up", k, r["week"], score, r["tier"])
            prog = first_kill.get(bk) == r["source"]
            if id(r) in over:
                cells.ratio("overachiever", k, over[id(r)])
            cells.diff("clutch-player", k, score if prog else 0, prog, 0 if prog else score, not prog)

        if role == "TANK":
            if id(r) in sponge:
                cells.ratio("damage-sponge", k, sponge[id(r)])
            cells.ratio("brick-wall", k, r["deaths"])
            if id(r) in secret:
                cells.ratio("secret-dps", k, secret[id(r)])
            if r["damage_taken"]:
                cells.ratio("add-wrangler", k, r["damage_taken_adds"] / r["damage_taken"])
            if r["taunts"] is not None:
                cells.ratio("attention-seeker", k, r["taunts"], r["duration_ms"] / 60000)
            if r["deaths_with_cd"]:
                cells.sum("blamed-the-healer", k, r["deaths_with_cd"])
            if kill and med_duration.get(bk):
                cells.ratio("pacemaker", k, 100 * r["duration_ms"] / med_duration[bk])
        elif role == "HEALER":
            if kill and score is not None:
                cells.ratio("healing-machine", k, score)
            if id(r) in sniped:
                cells.ratio("sniped", k, sniped[id(r)])
            if r["healing_done"]:
                cells.ratio("tanks-personal-nurse", k, r["healing_on_tanks"] / r["healing_done"])
            if id(r) in smite:
                cells.ratio("smite-lord", k, smite[id(r)])
            for target, amount in r["heal_targets"].items():
                main = owner.get(norm(target), target)
                if main != r["player"]:
                    cells.top("favorite-patient", k, main, amount)
                    patient = row_of.get((r["source"], target))
                    if patient and ranked(patient):
                        cells.top("guardian-angel", key_of(patient), r["player"], amount)
            if id(r) in fiend:
                cells.ratio("parse-fiend", k, fiend[id(r)])
        else:
            if kill and score is not None:
                cells.ratio("big-pumper", k, score)
                day = datetime.fromtimestamp(r["start_ms"] / 1000, tz).date().isoformat()
                cells.best("main-character-moment", k, score, f"{r['encounter']} · {day}")
                fin = r["encounter"] in final_bosses
                cells.diff("final-boss-energy", k, score if fin else 0, fin, 0 if fin else score, not fin)
            if r["damage_done"]:
                cells.ratio("tunnel-vision", k, r["damage_boss"] / r["damage_done"])
            if id(r) in one_button:
                cells.ratio("one-button-wonder", k, one_button[id(r)])
            if r["engineering_damage"]:
                cells.sum("engineers-pride", k, r["engineering_damage"])

    # Per night and per pair of players: Late Arrival / Early Leaver, Suicide Pact.
    for (first, last, late, early) in late_and_early(pulls, tz).values():
        if ranked(first):
            cells.ratio("late-arrival", key_of(first), late)
        if ranked(last):
            cells.ratio("early-leaver", key_of(last), early)
    for rs in pulls.values():
        for a, b in suicide_pacts(rs):
            for me, mate in ((a, b), (b, a)):
                if ranked(me):
                    cells.top("suicide-pact", key_of(me), mate["player"], 1)

    # Damage Done: boss damage (above) plus trash damage, once per character and night.
    trash = trash_damage(pulls, scaled_rates["damage-done-bosses"], scaled_refs["damage-done-bosses"], tz)
    for row, sc, actual in trash:
        if ranked(row):
            cells.ratio("damage-done", key_of(row), sc, actual)
    print(f"damage done: trash of {len({r['report'] for r, _, _ in trash})} reports added")

    timekeeper(rows, pid, char_class, cells)
    parse_lord(rows, pid, char_class, cells)

    stats = cells.export([s["id"] for s in stats_cfg])
    empty = [s["id"] for s in stats_cfg if not stats[s["id"]]]
    print(f"stats: {sum(len(v) for v in stats.values())} cells; empty: {', '.join(empty)}")

    # Guild facts for the home page, on every deduplicated pull.
    totals = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    report_pulls = defaultdict(list)
    bosses = defaultdict(lambda: [0, 0, None, None])
    for src, rs in pulls.items():
        r0 = rs[0]
        t = totals[r0["e"]]
        t[0] += 1; t[1] += r0["kill"]; t[2] += not r0["kill"]
        t[3] += sum(r["damage_done"] for r in rs); t[4] += r0["duration_ms"] / 1000
        report_pulls[r0["report"]].append((r0["start_ms"], r0["start_ms"] + r0["duration_ms"], r0["e"]))
        b = bosses[(r0["e"], r0["encounter"], int(r0["difficulty"] == 4))]
        if r0["kill"]:
            s = r0["duration_ms"] / 1000
            b[0] += 1
            b[2] = s if b[2] is None else min(b[2], s)
            b[3] = s if b[3] is None else max(b[3], s)
        else:
            b[1] += 1
    # Hours in raid: each raid night from its first to its last boss pull (trash fights are not in the
    # cache). Some reports hold several nights: a gap longer than night_gap_hours starts a new night.
    gap = CONFIG["night_gap_hours"] * 3_600_000
    for items in report_pulls.values():
        items.sort()
        lo, hi, e = items[0]
        for start, end, e2 in items[1:] + [(float("inf"), 0, None)]:
            if start - hi > gap:
                totals[e][5] += (hi - lo) / 1000
                lo, hi, e = start, end, e2
            else:
                hi = max(hi, end)
    guild_totals = [[e, *[round(x) for x in totals[e]]] for e in sorted(totals)]
    guild_bosses = [[e, boss, h, k, w, round(f) if f else None, round(s) if s else None] for (e, boss, h), (k, w, f, s) in sorted(bosses.items())]
    guild_raiders = sorted(Counter(exp_mask.values()).items())

    meta = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mock": False,
        "partial": True,
        "pending": sorted(PENDING | set(empty)),
        "guild": {"name": "Fable", "server": "Arugal (AU)"},
        "expansions": tiers_cfg["expansions"],
        "tiers": [{k: t[k] for k in ("id", "name", "short", "expansion")} for t in tiers_cfg["tiers"]],
        "classes": CLASSES,
        "roles": ROLES,
        "rank": {"max": max_rank, "names": tiers_cfg["rank"]["names"]},
        "settings": {k: site_cfg[k] for k in ("title_percentile", "flip_percentile", "min_den", "min_role_weeks", "min_char_weeks")},
        "home": {k: v for k, v in site_cfg["home"].items() if not k.startswith("_")},
        "player": {k: v for k, v in site_cfg["player"].items() if not k.startswith("_")},
        "stats": stats_cfg,
        "guild_totals": guild_totals,
        "guild_bosses": guild_bosses,
        "guild_raiders": guild_raiders,
        "ghosts": ghosts,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in (("meta", meta), ("players", players), ("stats", stats)):
        (OUT_DIR / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT_DIR.glob("*.json"))
    print(f"{len(pulls)} pulls, {len(players)} players -> {OUT_DIR.relative_to(ROOT)} ({size / 1e6:.1f} MB)")
    for k, v in sorted(issues.items()):
        print(f"issue: {k}: {v}")


if __name__ == "__main__":
    main()
