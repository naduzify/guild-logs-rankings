"""Trial crawl: a few random reports per expansion, to check before the full crawl
- role detection per fight (Summary table playerDetails),
- target hit points on heal events (needed for Sniper / Savior),
- real size of the raw cache.

Usage:
    python -m pipeline.probe crawl [--per-expansion 5] [--seed 42]
    python -m pipeline.probe analyze
"""

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict

from pipeline.guild import EXPANSIONS, expansion_of, list_reports
from pipeline.wcl import CACHE_DIR, WCLClient, WCLError

ELIGIBLE_SIZE = {"classic": 40, "tbc": 25, "wotlk": 25, "cata": 25, "mop": 25}
TABLES = [
    "Summary", "DamageDone", "Healing", "DamageTaken", "Deaths",
    "Interrupts", "Dispels", "Casts", "Buffs", "Debuffs",
]
HEAL_EVENTS_LIMIT = 10000
SELECTION_FILE = CACHE_DIR / "probe_selection.json"

FIGHTS_QUERY = """
query($code: String!) {
  reportData {
    report(code: $code) {
      code title startTime endTime
      zone { id name }
      fights(killType: Encounters) {
        id encounterID name difficulty size kill startTime endTime fightPercentage bossPercentage
      }
      masterData { actors(type: "Player") { id name server subType } }
    }
  }
}"""

TABLES_QUERY = "query($code: String!, $fid: [Int]!) { reportData { report(code: $code) { %s } } }" % " ".join(
    f"{t[0].lower() + t[1:]}: table(dataType: {t}, fightIDs: $fid)" for t in TABLES
)

HEAL_EVENTS_QUERY = """
query($code: String!, $fid: [Int]!, $limit: Int!) {
  reportData {
    report(code: $code) {
      events(dataType: Healing, fightIDs: $fid, limit: $limit, includeResources: true) {
        data nextPageTimestamp
      }
    }
  }
}"""


def fetch_fights(client: WCLClient, code: str) -> dict:
    return client.cached_query(f"reports/{code}/fights", FIGHTS_QUERY, {"code": code})["reportData"]["report"]


def crawl(per_expansion: int, seed: int) -> None:
    client = WCLClient("classic")
    print("endpoint:", client.url)
    print("rate limit before:", client.rate_limit())

    reports = list_reports(client)
    by_exp = defaultdict(list)
    for r in reports:
        by_exp[expansion_of(r)].append(r)
    print(f"{len(reports)} guild reports: " + ", ".join(f"{e}={len(by_exp[e])}" for e in EXPANSIONS))

    # Random pick, keeping only reports with at least one boss kill in the eligible format.
    rng = random.Random(seed)
    selection = {}
    for exp in EXPANSIONS:
        pool = [r for r in by_exp[exp] if r.get("zone")]
        rng.shuffle(pool)
        picked = []
        for r in pool:
            if len(picked) == per_expansion:
                break
            report = fetch_fights(client, r["code"])
            if any(f["kill"] and f.get("size") == ELIGIBLE_SIZE[exp] for f in report["fights"]):
                picked.append(r["code"])
        selection[exp] = picked
        print(f"{exp}: {picked}")
    SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_FILE.write_text(json.dumps({"seed": seed, "selection": selection}, indent=2), encoding="utf-8")

    for exp, codes in selection.items():
        for code in codes:
            report = fetch_fights(client, code)
            print(f"[{exp}] {code} {report['zone']['name'] if report.get('zone') else '?'}: {len(report['fights'])} boss pulls")
            for f in report["fights"]:
                client.cached_query(f"reports/{code}/tables_{f['id']:03d}", TABLES_QUERY, {"code": code, "fid": [f["id"]]})
            # Level 3 sample: heal events of the first eligible kill.
            kill = next(f for f in report["fights"] if f["kill"] and f.get("size") == ELIGIBLE_SIZE[exp])
            client.cached_query(
                f"reports/{code}/heal_events_{kill['id']:03d}",
                HEAL_EVENTS_QUERY,
                {"code": code, "fid": [kill["id"]], "limit": HEAL_EVENTS_LIMIT},
            )

    print(f"done, {client.requests_made} API requests this run")
    print("rate limit after:", client.rate_limit())


# ---------------------------------------------------------------- analysis


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))["data"]


def dir_size(path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*.json"))


def analyze() -> None:
    base = CACHE_DIR / "classic"
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))["selection"]
    all_reports = []
    for page in sorted((base / "guild").glob("reports_page_*.json")):
        all_reports.extend(load(page)["reportData"]["reports"]["data"])
    total_by_exp = Counter(expansion_of(r) for r in all_reports)

    out = ["# Crawl d'essai — résultats bruts", ""]
    for exp in EXPANSIONS:
        codes = selection.get(exp, [])
        out += [f"## {exp} ({len(codes)} rapports sur {total_by_exp[exp]})", ""]
        sizes, role_rows, heal_rows = [], [], []
        for code in codes:
            rdir = base / "reports" / code
            sizes.append(dir_size(rdir))
            report = load(rdir / "fights.json")["reportData"]["report"]
            fmt = Counter((f.get("size"), f.get("difficulty"), "kill" if f["kill"] else "wipe") for f in report["fights"])
            out.append(f"- `{code}` {report['zone']['name']} — {sizes[-1] / 1e6:.1f} Mo — pulls (taille, difficulté, issue) : "
                       + ", ".join(f"{k}×{n}" for k, n in sorted(fmt.items(), key=str)))

            for f in report["fights"]:
                if f.get("size") != ELIGIBLE_SIZE[exp] or not (rdir / f"tables_{f['id']:03d}.json").exists():
                    continue
                tables = load(rdir / f"tables_{f['id']:03d}.json")["reportData"]["report"]
                pd = ((tables.get("summary") or {}).get("data") or {}).get("playerDetails") or {}
                counts = {role: len(pd.get(role) or []) for role in ("tanks", "healers", "dps")}
                names = [p["name"] for role in ("tanks", "healers", "dps") for p in pd.get(role) or []]
                no_spec = sum(1 for role in ("tanks", "healers", "dps") for p in pd.get(role) or [] if not p.get("specs"))
                role_rows.append((counts, len(names) - len(set(names)), no_spec))

            heal_file = next(rdir.glob("heal_events_*.json"), None)
            if heal_file:
                ev = load(heal_file)["reportData"]["report"]["events"]["data"]
                heals = [e for e in ev if e.get("type") == "heal"]
                with_hp = [e for e in heals if "hitPoints" in e and "maxHitPoints" in e]
                on_target = [e for e in with_hp if e.get("resourceActor") == 2]
                pct = [100 * e["hitPoints"] / e["maxHitPoints"] for e in on_target if e["maxHitPoints"]]
                heal_rows.append({
                    "code": code, "heals": len(heals), "with_hp": len(with_hp),
                    "resource_actor": dict(Counter(e.get("resourceActor") for e in with_hp)),
                    "max_hp_sample": sorted({e["maxHitPoints"] for e in on_target})[:3],
                    "after_heal_lt10": sum(p < 10 for p in pct), "after_heal_gt75": sum(p > 75 for p in pct),
                    "paged": "oui" if load(heal_file)["reportData"]["report"]["events"]["nextPageTimestamp"] else "non",
                })

        out.append("")
        if role_rows:
            for role in ("tanks", "healers", "dps"):
                vals = [c[role] for c, _, _ in role_rows]
                out.append(f"- {role} par pull éligible : min {min(vals)}, médiane {statistics.median(vals)}, max {max(vals)}")
            out.append(f"- pulls éligibles : {len(role_rows)} ; joueurs dans 2 rôles du même pull : {sum(d for _, d, _ in role_rows)} ; "
                       f"sans spec : {sum(s for _, _, s in role_rows)}")
        for h in heal_rows:
            out.append(f"- soins `{h['code']}` : {h['heals']} events heal, {h['with_hp']} avec PV, resourceActor {h['resource_actor']}, "
                       f"maxHP ex. {h['max_hp_sample']}, PV après soin <10 % : {h['after_heal_lt10']}, >75 % : {h['after_heal_gt75']}, "
                       f"page suivante : {h['paged']}")
        if sizes:
            avg = statistics.mean(sizes)
            out.append(f"- volume : moyenne {avg / 1e6:.1f} Mo/rapport → extrapolé {avg * total_by_exp[exp] / 1e9:.2f} Go "
                       f"pour {total_by_exp[exp]} rapports (niveau 2 + 1 page d'events soins)")
        out.append("")

    text = "\n".join(out)
    (CACHE_DIR / "probe_summary.md").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl")
    c.add_argument("--per-expansion", type=int, default=5)
    c.add_argument("--seed", type=int, default=42)
    sub.add_parser("analyze")
    args = parser.parse_args()
    try:
        if args.cmd == "crawl":
            crawl(args.per_expansion, args.seed)
        else:
            analyze()
    except WCLError as e:
        raise SystemExit(f"WCL error: {e}")


if __name__ == "__main__":
    main()
