"""Crawl complements for the stats the level 2 tables cannot feed (docs/stats.md).

Runs on reports the main crawl already cached, with the same cache and budget:
- per eligible pull (reports/<code>/extra_<fight>.json):
  friendly fire (The Terrorist), taunt casts (Attention Seeker), Era and WotLK consumable casts
  (The Junky, The Unprepared; the level 2 Casts table only keeps 5 abilities per player) and, when a tank-class player died,
  the buff events of defensive cooldowns (Blamed the Healer);
- per report (reports/<code>/trash.json): damage done on trash (Timekeeper / The Tourist);
- per report (reports/<code>/rankings.json): WCL parses of every kill (Parse Lord, ranked against
  the world, not the guild).

Lists: config/crawl.json "extras", compute.json "era_consumable_casts" and "wotlk_consumable_ids". They are applied as WCL
filters, so after changing one, re-fetch with --refresh.

Usage:
    python -m pipeline.crawl_extra [--kinds pull,trash,rankings] [--limit N] [--cost] [--refresh]
"""

import argparse
import json
import time

from pipeline.crawl import CONFIG, is_eligible, log_error
from pipeline.guild import expansion_of, list_reports
from pipeline.wcl import CACHE_DIR, ROOT, WCLClient, WCLError

EXTRAS = CONFIG["extras"]
COMPUTE = json.loads((ROOT / "config" / "compute.json").read_text(encoding="utf-8"))


def names_in(names: list) -> str:
    return "ability.name in (%s)" % ", ".join(json.dumps(n) for n in names)


FILTERS = {
    "ff": 'source.type = "player" and target.type = "player"',
    "taunts": names_in(EXTRAS["taunts"]),
    "consumables": names_in(COMPUTE["era_consumable_casts"]),
    "consumables_wotlk": "ability.id in (%s)" % ", ".join(str(i) for i in COMPUTE["wotlk_consumable_ids"]),
    "cds": names_in(EXTRAS["defensive_cds"]),
}

FIELDS = {
    "ff": "friendlyFire: table(dataType: DamageDone, fightIDs: $fid, filterExpression: $ff)",
    "taunts": "taunts: table(dataType: Casts, fightIDs: $fid, filterExpression: $taunts)",
    "consumables": "consumables: table(dataType: Casts, fightIDs: $fid, filterExpression: $consumables)",
    "cds": "cds: events(dataType: Buffs, fightIDs: $fid, filterExpression: $cds, limit: 10000) { data nextPageTimestamp }",
}


# Expansions whose WCL consumable counters are unusable -> their filter.
CONSUMABLES = {"classic": "consumables", "wotlk": "consumables_wotlk"}


def pull_query(parts: list) -> str:
    args = "$code: String!, $fid: [Int]!" + "".join(f", ${k}: String" for k in parts)
    return "query(%s) { reportData { report(code: $code) { %s } } }" % (args, " ".join(FIELDS[k] for k in parts))


TRASH_QUERY = """
query($code: String!, $end: Float!) { reportData { report(code: $code) {
  trash: table(dataType: DamageDone, killType: Trash, startTime: 0, endTime: $end)
} } }"""

# The Terrorist, Attention Seeker and The Nut Crusher on trash: friendly fire, taunts and interrupts over all
# trash fights of a report.
TRASH_EXTRA_QUERY = """
query($code: String!, $end: Float!, $ff: String, $taunts: String) { reportData { report(code: $code) {
  friendlyFire: table(dataType: DamageDone, killType: Trash, startTime: 0, endTime: $end, filterExpression: $ff)
  taunts: table(dataType: Casts, killType: Trash, startTime: 0, endTime: $end, filterExpression: $taunts)
  interrupts: table(dataType: Interrupts, killType: Trash, startTime: 0, endTime: $end)
} } }"""


# Parse Lord: WCL parses of the kills. "Today" (WCL's default, rankings.json) against today's rankings, for the
# best parse; "Historical" (rankings_historical.json) against the rankings around the date of the fight, for
# the median parse.
RANKINGS_QUERY = """
query($code: String!, $fid: [Int]!, $tf: RankingTimeframeType) {
  reportData { report(code: $code) { rankings(fightIDs: $fid, timeframe: $tf) } } }"""
RANKINGS_KINDS = {"rankings": "Today", "rankings_historical": "Historical"}


def cached(code: str, name: str) -> dict | None:
    path = CACHE_DIR / "classic" / "reports" / code / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["data"] if path.exists() else None


def tank_died(code: str, fight: dict, actors: dict) -> bool:
    tables = cached(code, f"tables_{fight['id']:03d}")
    deaths = tables["reportData"]["report"]["deaths"]["data"]["entries"] if tables else []
    return any(actors.get(d["id"]) in COMPUTE["tank_classes"] for d in deaths)


class Meter:
    """Points spent per query, read from rateLimitData (noisy while the main crawl runs)."""

    def __init__(self, client: WCLClient, on: bool):
        self.client, self.on, self.costs = client, on, {}

    def run(self, kind: str, fn):
        if not self.on:
            return fn()
        before = self.client.rate_limit()["pointsSpentThisHour"]
        out = fn()
        spent = self.client.rate_limit()["pointsSpentThisHour"] - before
        if spent >= 0:  # negative across an hourly reset
            self.costs.setdefault(kind, []).append(spent)
        return out

    def report(self):
        for kind, xs in self.costs.items():
            print(f"cost {kind}: {len(xs)} queries, mean {sum(xs) / len(xs):.2f} points, max {max(xs):.2f}")


def crawl(kinds: set, limit: int | None, cost: bool, refresh: bool) -> None:
    client = WCLClient("classic")
    meter = Meter(client, cost)
    reports = sorted(list_reports(client), key=lambda r: r["startTime"])
    done = 0
    for i, r in enumerate(reports, 1):
        code, exp = r["code"], expansion_of(r)
        if code in CONFIG["excluded_reports"]:
            continue  # PTR logs
        report = cached(code, "report")
        if report is None:
            continue  # not crawled yet by pipeline.crawl
        report = report["reportData"]["report"]
        eligible = [f for f in report["fights"] if is_eligible(f, exp)]
        if not eligible:
            continue
        actors = {a["id"]: a.get("subType") for a in report["masterData"]["actors"]}
        n = 0
        try:
            if "pull" in kinds:
                for f in eligible:
                    key = f"reports/{code}/extra_{f['id']:03d}"
                    path = CACHE_DIR / "classic" / f"{key}.json"
                    if refresh and path.exists():
                        path.unlink()
                    if path.exists():
                        continue
                    parts = ["ff", "taunts"] + (["consumables"] if exp in CONSUMABLES else [])
                    if tank_died(code, f, actors):
                        parts.append("cds")
                    variables = {"code": code, "fid": [f["id"]], **{k: FILTERS[k] for k in parts}}
                    if "consumables" in parts:
                        variables["consumables"] = FILTERS[CONSUMABLES[exp]]
                    meter.run("+".join(parts), lambda: client.cached_query(key, pull_query(parts), variables))
                    n += 1
            if "trash" in kinds:
                key = f"reports/{code}/trash"
                path = CACHE_DIR / "classic" / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    end = report["endTime"] - report["startTime"]
                    meter.run("trash", lambda: client.cached_query(key, TRASH_QUERY, {"code": code, "end": end}))
                    n += 1
            if "trash_extra" in kinds:
                key = f"reports/{code}/trash_extra"
                path = CACHE_DIR / "classic" / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    variables = {"code": code, "end": report["endTime"] - report["startTime"],
                                 "ff": FILTERS["ff"], "taunts": FILTERS["taunts"]}
                    meter.run("trash_extra", lambda: client.cached_query(key, TRASH_EXTRA_QUERY, variables))
                    n += 1
            for kind, timeframe in RANKINGS_KINDS.items():
                if kind not in kinds:
                    continue
                key = f"reports/{code}/{kind}"
                path = CACHE_DIR / "classic" / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    fids = [f["id"] for f in eligible if f.get("kill")]
                    if fids:
                        variables = {"code": code, "fid": fids, "tf": timeframe}
                        meter.run(kind, lambda: client.cached_query(key, RANKINGS_QUERY, variables))
                        n += 1
        except WCLError as e:
            log_error(code, e)
            print(f"  error on {code}, logged: {str(e)[:200]}")
            continue
        done += 1
        print(f"[{i}/{len(reports)}] {exp} {code}: {n} queries ({client.requests_made} requests)", flush=True)
        if limit and done >= limit:
            break
    meter.report()
    print("done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kinds", default="pull,trash,trash_extra,rankings,rankings_historical",
                        help="pull, trash, trash_extra, rankings, rankings_historical (comma separated)")
    parser.add_argument("--limit", type=int, help="stop after N reports with eligible pulls (testing)")
    parser.add_argument("--cost", action="store_true", help="measure points spent per query")
    parser.add_argument("--refresh", action="store_true", help="re-fetch what is already cached (after a list change)")
    a = parser.parse_args()
    crawl(set(a.kinds.split(",")), a.limit, a.cost, a.refresh)


if __name__ == "__main__":
    main()
