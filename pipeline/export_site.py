"""Site export: facts table -> site/public/data/{meta,players,stats}.json (docs/site-data.md).

Second and third stages of the compute step: pull dedup across reports, reset weeks,
15-week qualification, raid tiers and PvP ranks, then every stat as additive cells
(player, expansion, class, role). Stats that need data not crawled yet are exported
empty and listed in meta.pending.

Usage:
    python -m pipeline.export_site            # from the raw crawl cache
"""

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.facts import CONFIG, ROOT, add_scores, load_mapping, norm, pull_rows, pulls_from_cache

OUT_DIR = ROOT / "site" / "public" / "data"
WEEK_MS = 7 * 24 * 3600 * 1000
EXP_INDEX = {"classic": 0, "tbc": 1, "wotlk": 2, "cata": 3, "mop": 4}
ROLES = ["TANK", "DPS", "HEALER"]
CLASSES = ["Death Knight", "Druid", "Hunter", "Mage", "Monk", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"]
CLASS_NAME = {"DeathKnight": "Death Knight"}
# Stats that need data the crawl does not have yet (docs/stats.md) or a model still to write.
PENDING = {"overachiever", "the-terrorist", "attention-seeker", "blamed-the-healer", "timekeeper"}


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
                    keep = max(reports, key=lambda rep: per_report[rep])
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

    def sum(self, sid, key, n):
        self._get(sid, key, lambda: [0.0])[0] += n

    def ids(self, sid, key, x):
        self._get(sid, key, set).add(x)

    def diff(self, sid, key, a, ad, b, bd):
        v = self._get(sid, key, lambda: [0.0] * 4); v[0] += a; v[1] += ad; v[2] += b; v[3] += bd

    def spread(self, sid, key, x):
        v = self._get(sid, key, lambda: [0, 0.0, 0.0]); v[0] += 1; v[1] += x; v[2] += x * x

    def slope(self, sid, key, x, y):
        v = self._get(sid, key, lambda: [0, 0.0, 0.0, 0.0, 0.0]); v[0] += 1; v[1] += x; v[2] += y; v[3] += x * x; v[4] += x * y

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
                    vals = [round(x, 4) if isinstance(x, float) else x for x in v]
                cells.append([p, e, c, r, *vals])
            out[sid] = cells
        return out


def base100(rows, metric, group_key):
    """{id(row): 100 * value / median of its group}, groups with a zero median skipped."""
    groups = defaultdict(list)
    for r in rows:
        if r.get(metric) is not None:
            groups[group_key(r)].append(r)
    out = {}
    for rs in groups.values():
        med = statistics.median(r[metric] for r in rs)
        if med:
            for r in rs:
                out[id(r)] = 100 * r[metric] / med
    return out


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
    tz = ZoneInfo(CONFIG["night"]["timezone"])
    exp_ids = [x["id"] for x in tiers_cfg["expansions"]]
    tier_of = {}
    for i, t in enumerate(tiers_cfg["tiers"]):
        for z in t["zones"]:
            tier_of[(exp_ids.index(t["expansion"]), z)] = i
    unknown_zones = Counter()
    for r in rows:
        r["e"] = EXP_INDEX[r["expansion"]]
        r["week"] = int((r["start_ms"] - anchor) // WEEK_MS)
        r["tier"] = tier_of.get((r["e"], r["zone"]))
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
    for r in rows:
        weeks[r["player"]].add(r["week"])
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
        tiers = sorted(t for t, w in tier_weeks[pl].items() if len(w) >= min_w)
        players.append({"name": pl, "chars": [[ch, CLASSES.index(char_class[ch])] for ch in chars if ch in char_class],
                        "tiers": tiers, "rank": min(max_rank, len(tiers))})
    print(f"players: {len(weeks)} seen, {len(qualified)} qualified (15+ reset weeks)")

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
    received = base100(rows, "healing_received", lambda r: (r["source"], r["role"]))
    magnet = base100(rows, "avoidable_taken", lambda r: (r["source"], r["role"]))
    healers_k = [r for r in kills if r["role"] == "HEALER"]
    smite = base100(healers_k, "damage_done", lambda r: r["source"])
    for r in rows:
        r["fiend"] = min(r["avoidable_taken"], r["self_healing"]) if r["role"] == "HEALER" else None
    fiend = base100([r for r in rows if r["role"] == "HEALER"], "fiend", lambda r: r["source"])
    one_button = base100([r for r in kills if r["role"] == "DPS"], "top_ability_share", lambda r: (r["class"], r["e"]))

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

    interruptible = {src for src, rs in pulls.items() if any(r["interrupts"] for r in rs)}
    final_bosses = set(CONFIG["final_bosses"])
    night = CONFIG["night"]
    boss_ids = {}

    cells = Cells()
    for r in rows:
        if r["player"] not in pid or r["char"] not in char_class:
            continue
        k = (pid[r["player"]], r["e"], CLASSES.index(char_class[r["char"]]), ROLES.index(r["role"]))
        kill, wipe, score, role = r["kill"], not r["kill"], r["score"], r["role"]
        dead = bool(r["deaths"] or r["deaths_scripted"])

        cells.sum("hours-played", k, r["duration_ms"] / 3_600_000)
        cells.sum("boss-kills", k, kill)
        cells.sum("wipes", k, wipe)
        cells.ids("the-gang", k, r["week"])
        cells.ids("the-undecided", k, char_id[r["char"]])
        if kill:
            cells.ids("kill-collector", k, boss_ids.setdefault(boss_key(r), len(boss_ids)))
        cells.ratio("the-immortal", k, wipe)
        local = datetime.fromtimestamp(r["start_ms"] / 1000, tz)
        cells.ratio("night-owl", k, night["from_hour"] <= local.hour < night["to_hour"])
        bk = boss_key(r)
        absent = boss_pulls[bk] - mine_pulls[(r["player"], bk)]
        if absent > 0:
            cells.diff("black-cat", k, wipe, 1, (boss_wipes[bk] - mine_wipes[(r["player"], bk)]) / absent, 1)
        cells.ratio("fishbait", k, r["first_death"])
        cells.ratio("floor-inspector", k, r["deaths"])
        if wipe:
            cells.ratio("the-roach", k, not dead)
        if kill and not dead and (r["pull_players"] - r["pull_dead"]) < r["pull_players"] / 2:
            cells.sum("last-stand", k, 1)
        if r["killed_by"]:
            cells.top("arch-nemesis", k, r["killed_by"], 1)
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
        if kill and score is not None:
            cells.spread("metronome", k, score)
            cells.top("comfort-boss", k, r["encounter"], score)
            cells.slope("glow-up", k, r["week"], score)
            prog = first_kill.get(bk) == r["source"]
            cells.diff("clutch-player", k, score if prog else 0, prog, 0 if prog else score, not prog)

        if role == "TANK":
            if id(r) in sponge:
                cells.ratio("damage-sponge", k, sponge[id(r)])
            cells.ratio("brick-wall", k, r["deaths"])
            if id(r) in secret:
                cells.ratio("secret-dps", k, secret[id(r)])
            if r["damage_taken"]:
                cells.ratio("add-wrangler", k, r["damage_taken_adds"] / r["damage_taken"])
            if kill and med_duration.get(bk):
                cells.ratio("pacemaker", k, 100 * r["duration_ms"] / med_duration[bk])
        elif role == "HEALER":
            if kill and score is not None:
                cells.ratio("healing-machine", k, score)
            done = r["healing_done"] + r["overheal"]
            if done:
                cells.ratio("sniper", k, r["overheal"] / done)
            if r["healing_done"]:
                cells.ratio("tanks-personal-nurse", k, r["healing_on_tanks"] / r["healing_done"])
            if id(r) in smite:
                cells.ratio("smite-lord", k, smite[id(r)])
            for target, amount in r["heal_targets"].items():
                main = owner.get(norm(target), target)
                if main != r["player"]:
                    cells.top("favorite-patient", k, main, amount)
            if id(r) in fiend:
                cells.ratio("parse-fiend", k, fiend[id(r)])
        else:
            if kill and score is not None:
                cells.ratio("big-pumper", k, score)
                day = datetime.fromtimestamp(r["start_ms"] / 1000, tz).date().isoformat()
                cells.best("main-character-moment", k, score, f"{r['encounter']} · {day}")
                if r["encounter"] in final_bosses:
                    cells.ratio("final-boss-energy", k, score)
            if r["damage_done"]:
                cells.ratio("tunnel-vision", k, r["damage_boss"] / r["damage_done"])
            if id(r) in one_button:
                cells.ratio("one-button-wonder", k, one_button[id(r)])
            if r["engineering_damage"]:
                cells.sum("engineers-pride", k, r["engineering_damage"])

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
        "pending": sorted(PENDING),
        "guild": {"name": "Fable", "server": "Arugal (AU)"},
        "expansions": tiers_cfg["expansions"],
        "tiers": [{k: t[k] for k in ("id", "name", "short", "expansion")} for t in tiers_cfg["tiers"]],
        "classes": CLASSES,
        "roles": ROLES,
        "rank": {"max": max_rank, "names": tiers_cfg["rank"]["names"]},
        "settings": {k: site_cfg[k] for k in ("title_percentile", "flip_percentile", "min_den")},
        "home": {k: v for k, v in site_cfg["home"].items() if not k.startswith("_")},
        "player": {k: v for k, v in site_cfg["player"].items() if not k.startswith("_")},
        "stats": stats_cfg,
        "guild_totals": guild_totals,
        "guild_bosses": guild_bosses,
        "guild_raiders": guild_raiders,
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
