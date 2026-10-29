"""Base stats table: one row per (player, character, pull, role), from the raw WCL tables.

First stage of the compute step (docs/stats.md): raw per-pull metrics, the player
mapping (main + rerolls) and base 100 scores against the median of the role in
the pull. Reads either the data/samples/ pulls or the raw crawl cache, and prints
sanity checks so data problems show up before the stats are built on top.

Usage:
    python -m pipeline.facts --samples
    python -m pipeline.facts --cache [--limit N]
"""

import argparse
import csv
import json
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
CACHE_DIR = ROOT / "data" / "cache"
OUT_DIR = ROOT / "data" / "facts"
CONFIG = json.loads((ROOT / "config" / "compute.json").read_text(encoding="utf-8"))
CRAWL = json.loads((ROOT / "config" / "crawl.json").read_text(encoding="utf-8"))
ERA = "classic"
ERA_SHOULDER_FROM_MS = datetime.fromisoformat(CONFIG["enchants"]["era_shoulder_from"]).replace(tzinfo=timezone.utc).timestamp() * 1000

ROLE_KEYS = {"tanks": "TANK", "healers": "HEALER", "dps": "DPS"}
# Metric used for each role's performance score, base 100 vs the role median in the pull.
SCORE_METRIC = {"DPS": "damage_done", "HEALER": "healing_done", "TANK": "damage_taken"}


def norm(name: str) -> str:
    """Name key for matching characters: NFC (same accents, any encoding form), case-insensitive."""
    return unicodedata.normalize("NFC", name).casefold()


def load_mapping() -> dict:
    rerolls = json.loads((ROOT / "fable_rerolls.json").read_text(encoding="utf-8"))["rerolls"]
    owner, clashes = {}, []
    for main, alts in rerolls.items():
        for char in [main, *alts]:
            key = norm(char)
            if key in owner and owner[key] != main:
                clashes.append((char, owner[key], main))
            owner[key] = main
    for char, a, b in clashes:
        print(f"WARNING mapping: {char} belongs to both {a} and {b}")
    return owner


# --- sources -----------------------------------------------------------------

def pulls_from_samples():
    for path in sorted(SAMPLES_DIR.glob("*.json")):
        if path.stem.endswith("_light"):
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        yield {"source": path.stem, "expansion": d["expansion"], "report": d["report"], "report_start": None,
               "zone": d["zone"], "fight": d["fight"], "tables": {k: v["data"] for k, v in d["tables"].items()}}


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["data"]["reportData"]


def pulls_from_cache(host: str = "classic", limit: int | None = None):
    from pipeline.guild import expansion_of  # needs requests/dotenv: only for the cache source

    guild = {}
    for page in sorted((CACHE_DIR / host / "guild").glob("reports_page_*.json")):
        for r in _payload(page)["reports"]["data"]:
            guild[r["code"]] = r
    done = 0
    for rdir in sorted((CACHE_DIR / host / "reports").iterdir()):
        # The trial crawl (pipeline/probe.py) named the fight list fights.json; same content as report.json.
        rep_file = next((f for f in (rdir / "report.json", rdir / "fights.json") if f.exists()), None)
        if not rep_file:
            continue
        rep = _payload(rep_file)["report"]
        if rep["code"] in CRAWL["excluded_reports"]:
            continue  # PTR logs
        fights = {f["id"]: f for f in rep["fights"]}
        exp = expansion_of(guild.get(rep["code"], rep))
        for tpath in sorted(rdir.glob("tables_*.json")):
            fight = fights.get(int(tpath.stem.split("_")[1]))
            if not fight:
                continue
            tables = {k: v["data"] for k, v in _payload(tpath)["report"].items()}
            # Crawl complements (pipeline/crawl_extra.py), when fetched: filtered tables and buff events.
            xpath = rdir / f"extra_{fight['id']:03d}.json"
            extra = _payload(xpath)["report"] if xpath.exists() else None
            actors = {a["id"]: a["name"] for a in (rep.get("masterData") or {}).get("actors", [])}
            yield {"source": f"{rep['code']}#{fight['id']}", "expansion": exp, "report": rep["code"],
                   "report_start": rep["startTime"], "zone": (rep.get("zone") or {}).get("name"),
                   "fight": fight, "tables": tables, "extra": extra, "actors": actors}
            done += 1
            if limit and done >= limit:
                return


# --- one pull -> rows --------------------------------------------------------

def _by_name(entries: list) -> dict:
    return {e["name"]: e for e in entries if "name" in e}


def _detail_counts(groups: list) -> Counter:
    """Interrupts / dispels tables: enemy spell -> details[] per player. Returns player -> count."""
    out = Counter()
    for g in groups:
        for spell in g.get("entries", []):
            for det in spell.get("details", []):
                out[det["name"]] += det.get("total", 0)
    return out


def era_tanks(roles: dict, taken: dict) -> set:
    """Classic Era tanks: a tanking class that WCL lists as a tank (Protection / Guardian talents), or
    that took at least min_melee_share of the boss melee (main tanks) or of the adds melee (off-tanks)
    in the pull (tanks in a DPS spec, e.g. Feral or fury-prot).

    The DamageTaken table splits damage by ability and by source, not both, so melee is estimated:
    boss melee = min(his "Melee" taken, his damage from Boss sources), adds melee = min(the rest of
    his "Melee" taken, his damage from other NPC sources).
    """
    cfg = CONFIG["era_tank"]
    boss, adds = {}, {}
    for name in roles:
        e = taken.get(name, {})
        melee = sum(a.get("total", 0) for a in e.get("abilities", []) if a.get("name") == "Melee")
        from_boss = sum(x.get("total", 0) for x in e.get("sources", []) if x.get("type") == "Boss")
        from_npc = sum(x.get("total", 0) for x in e.get("sources", []) if x.get("type") != "Boss")
        boss[name] = min(melee, from_boss)
        adds[name] = min(melee - boss[name], from_npc)
    tb, ta, share = sum(boss.values()), sum(adds.values()), cfg["min_melee_share"]
    # WCL healers stay healers: a healer hit by adds is not an off-tank.
    return {n for n, (role, p) in roles.items() if p.get("type") in cfg["classes"] and role != "HEALER"
            and (role == "TANK" or (tb and boss[n] / tb >= share) or (ta and adds[n] / ta >= share))}


def tank_deaths_with_cd(events: list, deaths: list, actors: dict, tanks: set) -> Counter:
    """Tank name -> deaths (scripted ones excluded) with a defensive cooldown on him at the time of death.

    `events` are buff events already filtered on the cooldowns (config/crawl.json extras). A buff counts
    when applied before the death and not removed more than cd_death_tolerance_ms before it: WCL logs the
    removal of the buffs of a dying player 100 to 400 ms before the death itself.
    """
    spans = defaultdict(list)  # (target id, buff) -> [[start, end]], end None while still up
    for e in sorted(events, key=lambda e: e["timestamp"]):
        key = (e.get("targetID"), e.get("abilityGameID"))
        if e["type"] in ("applybuff", "refreshbuff", "applybuffstack"):
            if not spans[key] or spans[key][-1][1] is not None:
                spans[key].append([e["timestamp"], None])
        elif e["type"] == "removebuff" and spans[key] and spans[key][-1][1] is None:
            spans[key][-1][1] = e["timestamp"]
    scripted = set(CONFIG["scripted_deaths"])
    out = Counter()
    for d in deaths:
        name = actors.get(d.get("id"), d.get("name"))
        if name not in tanks or (d.get("killingBlow") or {}).get("name") in scripted:
            continue
        ts = d["timestamp"]
        tol = CONFIG["cd_death_tolerance_ms"]
        if any(tid == d.get("id") and a <= ts and (b is None or b >= ts - tol)
               for (tid, _), ss in spans.items() for a, b in ss):
            out[name] += 1
    return out


def enchant_slots(gear: list, cls: str, pull: dict) -> tuple[int, int]:
    """(enchantable slots, enchanted ones) for one player, per config/compute.json "enchants"."""
    cfg = CONFIG["enchants"]
    era = pull["expansion"] == ERA
    start = pull["report_start"] and pull["report_start"] + pull["fight"]["startTime"]
    era_shoulders = (start and start >= ERA_SHOULDER_FROM_MS) or pull["zone"] in cfg["era_shoulder_zones"]
    skipped = {cfg["slots"][k] for k in cfg["skip_by_expansion"].get(pull["expansion"], [])}
    slots = set(cfg["slots"].values()) - skipped
    able = done = 0
    for g in gear:
        slot = g.get("slot")
        if slot not in slots or not g.get("id"):
            continue  # not enchantable, or empty slot (two-hander, no ranged)
        if slot == cfg["slots"]["shoulder"] and era and not era_shoulders:
            continue
        if slot == cfg["slots"]["ranged"] and cls not in cfg["ranged_classes"]:
            continue
        if slot == cfg["slots"]["off_hand"] and not (g.get("icon") or "").startswith(tuple(cfg["off_hand_weapon_icons"])):
            continue  # caster held-in-off-hand item
        able += 1
        done += bool(g.get("permanentEnchant"))
    return able, done


def pull_rows(pull: dict, owner: dict, issues: Counter) -> list[dict]:
    t, f = pull["tables"], pull["fight"]
    summary = t["summary"]
    details = summary.get("playerDetails", {})
    duration = f["endTime"] - f["startTime"]
    era = pull["expansion"] == ERA

    if f.get("size") != CRAWL["eligible_size"].get(pull["expansion"]) or f.get("difficulty") not in CRAWL["eligible_difficulties"]:
        issues["pulls dropped: size or difficulty not eligible"] += 1
        return []
    if f.get("encounterID") in CONFIG["excluded_encounters"]:
        issues["pulls dropped: excluded encounter (vehicle or cannon fight)"] += 1
        return []

    roles = {}
    if isinstance(details, dict) and details:
        for key, role in ROLE_KEYS.items():
            for p in details.get(key, []):
                if p["name"] in roles:
                    issues["player listed in two roles in one pull"] += 1
                roles[p["name"]] = (role, p)
    else:
        # A few pulls come with an empty playerDetails list: roles from the composition, no gear or potions.
        issues["pulls without playerDetails (roles from composition)"] += 1
        role_of = {"tank": "TANK", "healer": "HEALER", "dps": "DPS"}
        for p in summary.get("composition", []):
            spec = next(iter(p.get("specs") or []), {})
            roles[p["name"]] = (role_of.get(spec.get("role"), "DPS"), {"type": p.get("type"), "specs": [spec.get("spec")]})
    if len(roles) < CONFIG["min_players"]:
        issues[f"pulls dropped: fewer than {CONFIG['min_players']} players (fake log)"] += 1
        return []

    dmg, heal, taken, casts = (_by_name(t[k]["entries"]) for k in ("damageDone", "healing", "damageTaken", "casts"))
    if era:
        # WCL's Era tank detection is completed with players tanking in a DPS spec.
        era_tank_set = era_tanks(roles, taken)
        for name, (role, p) in list(roles.items()):
            new = "TANK" if name in era_tank_set else ("DPS" if role == "TANK" else role)
            if new != role:
                issues[f"era role changed {role} -> {new}"] += 1
                roles[name] = (new, p)
    # Every expansion: WCL sometimes lists a class that cannot tank (a hunter with his pet) as a tank.
    for name, (role, p) in list(roles.items()):
        if role == "TANK" and p.get("type") not in CONFIG["tank_classes"]:
            issues[f"tank role dropped for class {p.get('type')}"] += 1
            roles[name] = ("DPS", p)
    tanks = {n for n, (r, _) in roles.items() if r == "TANK"}
    for table, by in (("damageDone", dmg), ("healing", heal), ("damageTaken", taken), ("casts", casts)):
        extra = set(by) - set(roles)
        if extra:
            issues[f"non-player entries ignored in {table}"] += len(extra)

    x = pull.get("extra") or {}
    ff, taunts, consumables = (_by_name(x[k]["data"]["entries"]) if k in x else None for k in ("friendlyFire", "taunts", "consumables"))
    cd_deaths = tank_deaths_with_cd(x["cds"]["data"], t["deaths"]["entries"], pull.get("actors", {}), tanks) if "cds" in x else None

    interrupts = _detail_counts(t["interrupts"]["entries"])
    dispels = _detail_counts(t["dispels"]["entries"])

    scripted = set(CONFIG["scripted_deaths"])
    deaths = defaultdict(list)
    overkill = {}  # name -> (biggest overkill of a non-scripted death, killing blow)
    for d in t["deaths"]["entries"]:
        blow = (d.get("killingBlow") or {}).get("name")
        deaths[d["name"]].append((d["timestamp"], blow in scripted, blow))
        if blow not in scripted and d.get("overkill", 0) > overkill.get(d["name"], (0, None))[0]:
            overkill[d["name"]] = (d["overkill"], blow)
    real = sorted((ts, n) for n, ds in deaths.items() if n in roles for ts, s, _ in ds if not s)
    first_dead = real[0][1] if real else None
    pull_dead = sum(1 for n in roles if deaths.get(n))  # any death, scripted or battle-rezzed, counts

    # Healing received, from every healer's targets (pets and totems included as healers).
    received = Counter()
    for e in t["healing"]["entries"]:
        for x in e.get("targets", []):
            received[x.get("name")] += x.get("total", 0)
    # "Avoidable" damage: a non-melee enemy ability that hit fewer than half the players of the pull.
    hit = Counter()
    for name in roles:
        for a in taken.get(name, {}).get("abilities", []):
            if a.get("name") != "Melee" and a.get("total", 0) > 0:
                hit[a["name"]] += 1
    avoidable = {a for a, n in hit.items() if n < len(roles) / 2}
    engineering = set(CONFIG["engineering_abilities"])

    rows = []
    for name, (role, p) in roles.items():
        d, h, k, c = dmg.get(name, {}), heal.get(name, {}), taken.get(name, {}), casts.get(name, {})
        if not c:
            issues["role listed but absent from casts table"] += 1
        gear = (p.get("combatantInfo") or {}).get("gear") or []
        enchantable, enchanted = enchant_slots(gear, p.get("type"), pull)
        if era:
            # The filtered consumables table when fetched; else the level 2 Casts table (5 abilities per player only).
            src = consumables.get(name, {}) if consumables is not None else c
            cast = Counter({a["name"]: a.get("total", 0) for a in src.get("abilities", [])})
            stones = sum(n for a, n in cast.items() if "Healthstone" in a and a in CONFIG["era_consumable_casts"])
            potions = sum(cast[a] for a in CONFIG["era_consumable_casts"]) - stones
        elif pull["expansion"] == "wotlk":
            # WCL's counters are broken in WotLK: same sources as Era, matched on ability IDs.
            src = consumables.get(name, {}) if consumables is not None else c
            used = [a for a in src.get("abilities", []) if a.get("guid") in CONFIG["wotlk_consumable_ids"]]
            stones = sum(a.get("total", 0) for a in used if "Healthstone" in a.get("name", ""))
            potions = sum(a.get("total", 0) for a in used) - stones
        else:
            potions, stones = p.get("potionUse", 0), p.get("healthstoneUse", 0)
        ilvl = ((p.get("combatantInfo") or {}).get("stats") or {}).get("Item Level")
        my_deaths = deaths.get(name, [])
        rows.append({
            "source": pull["source"], "expansion": pull["expansion"], "report": pull["report"], "fight": f["id"],
            "start_ms": (pull["report_start"] + f["startTime"]) if pull["report_start"] else None,
            "zone": pull["zone"], "encounter_id": f["encounterID"], "encounter": f["name"],
            "difficulty": f["difficulty"], "size": f["size"], "kill": bool(f["kill"]), "duration_ms": duration,
            "char": name, "player": owner.get(norm(name), name), "mapped": norm(name) in owner,
            "class": p.get("type"), "spec": next(iter(p.get("specs") or []), None), "role": role,
            "ilvl": (ilvl or {}).get("min") if isinstance(ilvl, dict) else ilvl,
            "damage_done": d.get("total", 0),
            "damage_boss": sum(x.get("total", 0) for x in d.get("targets", []) if x.get("type") == "Boss"),
            "active_ms": d.get("activeTime", 0),
            "healing_done": h.get("total", 0), "overheal": h.get("overheal", 0),
            "healing_on_tanks": sum(x.get("total", 0) for x in h.get("targets", []) if x.get("name") in tanks),
            "damage_taken": k.get("total", 0),
            "damage_taken_adds": sum(x.get("total", 0) for x in k.get("sources", []) if x.get("type") != "Boss"),
            "avoidable_taken": sum(a.get("total", 0) for a in k.get("abilities", []) if a.get("name") in avoidable),
            "healing_received": received.get(name, 0),
            "self_healing": next((x.get("total", 0) for x in h.get("targets", []) if x.get("name") == name), 0),
            "heal_targets": json.dumps({x["name"]: x.get("total", 0) for x in h.get("targets", []) if x.get("name") in roles}, ensure_ascii=False),
            "top_ability_share": round(max((a.get("total", 0) for a in d.get("abilities", [])), default=0) / d["total"], 4) if d.get("total") else None,
            "engineering_damage": sum(a.get("total", 0) for a in d.get("abilities", []) if a.get("name") in engineering),
            "pull_players": len(roles), "pull_dead": pull_dead,
            "boss_pct": f.get("fightPercentage"),
            "deaths": sum(1 for _, s, _ in my_deaths if not s), "deaths_scripted": sum(1 for _, s, _ in my_deaths if s),
            "killed_by": next((b for _, s, b in my_deaths if not s), None),
            "death_times": json.dumps(sorted(ts for ts, s, _ in my_deaths if not s)),
            "overkill": overkill.get(name, (0, None))[0], "overkill_by": overkill.get(name, (0, None))[1],
            "first_death": name == first_dead,
            "interrupts": interrupts.get(name, 0), "dispels": dispels.get(name, 0),
            "casts": c.get("total", 0), "casts_active_ms": c.get("activeTime", 0),
            "potions": potions, "healthstones": stones,
            # Crawl complements: None when not fetched yet for this pull.
            "friendly_fire": None if ff is None else sum(
                y.get("total", 0) for y in ff.get(name, {}).get("targets", []) if y.get("name") != name),
            "taunts": None if taunts is None else taunts.get(name, {}).get("total", 0),
            "deaths_with_cd": None if cd_deaths is None else cd_deaths.get(name, 0),
            "gear_known": bool(gear), "enchantable_slots": enchantable, "enchanted_slots": enchanted,
        })
    for n in set(interrupts) | set(dispels):
        if n not in roles:
            issues["interrupts/dispels by non-player entries"] += 1
    return rows


def add_scores(rows: list[dict]) -> None:
    """score = metric / median of the same role in the same pull x 100 (kills only, docs/decisions.md).

    The median leaves out players at 0 (disconnected, AFK, wrong role) and needs min_score_peers of
    them: a median of one or two players (a healer next to two "healers" at 0) gave scores in the tens
    of thousands. Pulls below that get no score."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["source"], r["role"])].append(r)
    for (_, role), rs in groups.items():
        metric = SCORE_METRIC[role]
        active = [r[metric] for r in rs if r[metric] > 0]
        med = statistics.median(active) if len(active) >= CONFIG["min_score_peers"] else 0
        for r in rs:
            r["score"] = round(100 * r[metric] / med, 1) if med and r["kill"] else None


# --- checks ------------------------------------------------------------------

def report(rows: list[dict], issues: Counter, verbose: bool) -> None:
    pulls = defaultdict(list)
    for r in rows:
        pulls[r["source"]].append(r)

    if verbose:
        for src, rs in pulls.items():
            r0 = rs[0]
            roles = Counter(r["role"] for r in rs)
            print(f"\n## {src}  ({r0['expansion']}, {r0['encounter']}, {'kill' if r0['kill'] else 'wipe'}, {r0['duration_ms'] / 60000:.1f} min)")
            print(f"   roles {dict(roles)} | unmapped chars {sum(not r['mapped'] for r in rs)}/{len(rs)}")
            for role in ("TANK", "HEALER", "DPS"):
                sc = sorted((r["score"], r["char"]) for r in rs if r["role"] == role and r["score"] is not None)
                if sc:
                    print(f"   {role:6} scores min {sc[0][0]:>6} ({sc[0][1]}), max {sc[-1][0]:>6} ({sc[-1][1]})")
            dead = [r for r in rs if r["deaths"] or r["deaths_scripted"]]
            print(f"   deaths {sum(r['deaths'] for r in rs)} (+{sum(r['deaths_scripted'] for r in rs)} scripted), first: {next((r['char'] for r in rs if r['first_death']), '-')}"
                  f" | interrupts {sum(r['interrupts'] for r in rs)} | dispels {sum(r['dispels'] for r in rs)}"
                  f" | potions {sum(r['potions'] for r in rs)} | healthstones {sum(r['healthstones'] for r in rs)}")
            no_gear = sum(1 for r in rs if not r["gear_known"])
            print(f"   gear known for {len(rs) - no_gear}/{len(rs)}, enchanted {sum(r['enchanted_slots'] for r in rs)}/{sum(r['enchantable_slots'] for r in rs)} enchantable slots"
                  f" | ilvl known {sum(r['ilvl'] is not None for r in rs)}/{len(rs)} | dead {len(dead)}")

    print("\n== Checks ==")
    by_exp = defaultdict(list)
    for src, rs in pulls.items():
        by_exp[rs[0]["expansion"]].append(rs)
    for exp, ps in by_exp.items():
        n = len(ps)
        size = Counter(len(rs) for rs in ps)
        no_tank = sum(1 for rs in ps if not any(r["role"] == "TANK" for r in rs))
        no_heal = sum(1 for rs in ps if not any(r["role"] == "HEALER" for r in rs))
        print(f"{exp}: {n} pulls, {sum(len(rs) for rs in ps)} rows | players per pull min {min(size)} max {max(size)}"
              f" | pulls without tank {no_tank}, without healer {no_heal}")
        print(f"   pulls with 0 potions {sum(1 for rs in ps if not sum(r['potions'] for r in rs))}/{n},"
              f" 0 interrupts {sum(1 for rs in ps if not sum(r['interrupts'] for r in rs))}/{n},"
              f" 0 dispels {sum(1 for rs in ps if not sum(r['dispels'] for r in rs))}/{n},"
              f" no gear {sum(1 for rs in ps if not any(r['gear_known'] for r in rs))}/{n}")
        able = sum(r["enchantable_slots"] for rs in ps for r in rs)
        print(f"   tanks per pull {sorted(Counter(sum(r['role'] == 'TANK' for r in rs) for rs in ps).items())}"
              f" | enchanted {sum(r['enchanted_slots'] for rs in ps for r in rs) / max(able, 1):.0%} of enchantable slots")
        small = [rs[0] for rs in ps if len(rs) < 0.75 * rs[0]["size"]]
        if small:
            print(f"   pulls with fewer than 75% of the raid size: {len(small)}, e.g. "
                  + ", ".join(f"{r['source']} {r['encounter']} ({sum(1 for x in rows if x['source'] == r['source'])}/{r['size']})" for r in small[:4]))
        zero = sum(1 for rs in ps for r in rs if r["kill"] and r[SCORE_METRIC[r["role"]]] == 0)
        print(f"   rows with a 0 score metric on kills (AFK, disconnect, wrong role): {zero}")
    unm = Counter(r["char"] for r in rows if not r["mapped"])
    print(f"unmapped characters: {len(unm)} (mapped {len({r['char'] for r in rows if r['mapped']})})")
    for k, v in sorted(issues.items()):
        print(f"issue: {k}: {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--samples", action="store_true")
    src.add_argument("--cache", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    owner = load_mapping()
    issues = Counter()
    pulls = pulls_from_samples() if args.samples else pulls_from_cache(limit=args.limit)
    rows = [row for p in pulls for row in pull_rows(p, owner, issues)]
    add_scores(rows)
    report(rows, issues, verbose=args.samples)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"facts_{'samples' if args.samples else 'cache'}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} rows -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
