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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
CACHE_DIR = ROOT / "data" / "cache"
OUT_DIR = ROOT / "data" / "facts"
CONFIG = json.loads((ROOT / "config" / "compute.json").read_text(encoding="utf-8"))

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
        rep_file = rdir / "report.json"
        if not rep_file.exists():
            continue
        rep = _payload(rep_file)["report"]
        fights = {f["id"]: f for f in rep["fights"]}
        exp = expansion_of(guild.get(rep["code"], rep))
        for tpath in sorted(rdir.glob("tables_*.json")):
            fight = fights[int(tpath.stem.split("_")[1])]
            tables = {k: v["data"] for k, v in _payload(tpath)["report"].items()}
            yield {"source": f"{rep['code']}#{fight['id']}", "expansion": exp, "report": rep["code"],
                   "report_start": rep["startTime"], "zone": (rep.get("zone") or {}).get("name"),
                   "fight": fight, "tables": tables}
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


def pull_rows(pull: dict, owner: dict, issues: Counter) -> list[dict]:
    t, f = pull["tables"], pull["fight"]
    summary = t["summary"]
    details = summary.get("playerDetails", {})
    duration = f["endTime"] - f["startTime"]

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
    tanks = {n for n, (r, _) in roles.items() if r == "TANK"}

    dmg, heal, taken, casts = (_by_name(t[k]["entries"]) for k in ("damageDone", "healing", "damageTaken", "casts"))
    for table, by in (("damageDone", dmg), ("healing", heal), ("damageTaken", taken), ("casts", casts)):
        extra = set(by) - set(roles)
        if extra:
            issues[f"non-player entries ignored in {table}"] += len(extra)

    interrupts = _detail_counts(t["interrupts"]["entries"])
    dispels = _detail_counts(t["dispels"]["entries"])

    scripted = set(CONFIG["scripted_deaths"])
    deaths = defaultdict(list)
    for d in t["deaths"]["entries"]:
        blow = (d.get("killingBlow") or {}).get("name")
        deaths[d["name"]].append((d["timestamp"], blow in scripted, blow))
    real = sorted((ts, n) for n, ds in deaths.items() for ts, s, _ in ds if not s)
    first_dead = real[0][1] if real else None

    rows = []
    for name, (role, p) in roles.items():
        d, h, k, c = dmg.get(name, {}), heal.get(name, {}), taken.get(name, {}), casts.get(name, {})
        if not c:
            issues["role listed but absent from casts table"] += 1
        gear = (p.get("combatantInfo") or {}).get("gear") or []
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
            "deaths": sum(1 for _, s, _ in my_deaths if not s), "deaths_scripted": sum(1 for _, s, _ in my_deaths if s),
            "killed_by": next((b for _, s, b in my_deaths if not s), None),
            "first_death": name == first_dead,
            "interrupts": interrupts.get(name, 0), "dispels": dispels.get(name, 0),
            "casts": c.get("total", 0), "casts_active_ms": c.get("activeTime", 0),
            "potions": p.get("potionUse", 0), "healthstones": p.get("healthstoneUse", 0),
            "gear_slots": len(gear), "enchanted_slots": sum(1 for g in gear if g.get("permanentEnchant")),
        })
    for n in set(interrupts) | set(dispels):
        if n not in roles:
            issues["interrupts/dispels by non-player entries"] += 1
    return rows


def add_scores(rows: list[dict]) -> None:
    """score = metric / median of the same role in the same pull x 100 (kills only, docs/decisions.md)."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["source"], r["role"])].append(r)
    for (_, role), rs in groups.items():
        metric = SCORE_METRIC[role]
        med = statistics.median(r[metric] for r in rs)
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
            no_gear = sum(1 for r in rs if not r["gear_slots"])
            print(f"   gear known for {len(rs) - no_gear}/{len(rs)}, enchanted {sum(r['enchanted_slots'] for r in rs)}/{sum(r['gear_slots'] for r in rs)} slots"
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
              f" no gear {sum(1 for rs in ps if not sum(r['gear_slots'] for r in rs))}/{n}")
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
