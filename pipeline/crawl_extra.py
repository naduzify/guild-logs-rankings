"""Crawl complements for the stats the level 2 tables cannot feed (docs/stats.md).

Runs on reports the main crawl already cached, with the same cache and budget:
- per eligible pull (reports/<code>/extra_<fight>.json):
  friendly fire (The Terrorist), taunt casts (Attention Seeker), Era and WotLK consumable casts
  (The Junky, The Unprepared; the level 2 Casts table only keeps 5 abilities per player) and, when a tank-class player died,
  the buff events of defensive cooldowns (Blamed the Healer);
- per report (reports/<code>/trash.json): damage done on trash (Timekeeper / The Tourist);
- per report (reports/<code>/rankings.json): WCL parses of every kill (Parse Lord, ranked against
  the world, not the guild);
- per report (reports/<code>/trash_deaths.json): deaths on trash, with their killing blows (Headhunter,
  Collateral Damage);
- per report (reports/<code>/ff_events.json): friendly fire events of the abilities whose first hit is
  single target and the rest AoE (compute.json single_target.first_hit_only), for the single target
  version of The Terrorist; only reports where one of them hit a raid member.

Lists: config/crawl.json "extras", compute.json "era_consumable_casts" and "wotlk_consumable_ids". They are applied as WCL
filters, so after changing one, re-fetch with --refresh.

Usage:
    python -m pipeline.crawl_extra [--guild fable|nightshift] [--kinds pull,trash,trash_deaths,ff_events,...] [--limit N] [--cost] [--refresh]
"""

import argparse
import json
import time

from pipeline.crawl import CONFIG, is_eligible, log_error
from pipeline.crawl import unique_reports
from pipeline.guild import GUILDS, expansion_of
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
FIRST_HIT = COMPUTE["single_target"]["first_hit_only"]
FILTERS["ff_first_hit"] = FILTERS["ff"] + " and " + names_in(FIRST_HIT)

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


# Headhunter and Collateral Damage on trash: deaths over all trash fights of a report (with the events
# before each death, which name the source of the killing blow).
TRASH_DEATHS_QUERY = """
query($code: String!, $end: Float!) { reportData { report(code: $code) {
  deaths: table(dataType: Deaths, killType: Trash, startTime: 0, endTime: $end)
} } }"""

# The Terrorist, single target: friendly fire events of the first_hit_only abilities, over the whole report.
FF_EVENTS_QUERY = """
query($code: String!, $start: Float!, $end: Float!, $ff: String) { reportData { report(code: $code) {
  events(dataType: DamageDone, startTime: $start, endTime: $end, filterExpression: $ff, limit: 10000) { data nextPageTimestamp }
} } }"""


def first_hit_in_ff(code: str) -> bool:
    """Whether a first_hit_only ability shows in the report's friendly fire tables (pulls or trash)."""
    folder = CACHE_DIR / HOST / "reports" / code
    for path in [*folder.glob("extra_*.json"), folder / "trash_extra.json"]:
        if not path.exists():
            continue
        ff = json.loads(path.read_text(encoding="utf-8"))["data"]["reportData"]["report"].get("friendlyFire") or {}
        for e in ff.get("data", {}).get("entries", []):
            if any(a.get("name") in FIRST_HIT for a in e.get("abilities", [])):
                return True
    return False


def ff_events(client: WCLClient, code: str, end: float) -> None:
    """All pages of the first_hit_only friendly fire events of a report, in one cache file."""
    path = CACHE_DIR / HOST / "reports" / code / "ff_events.json"
    events, start = [], 0
    while start is not None:
        variables = {"code": code, "start": start, "end": end, "ff": FILTERS["ff_first_hit"]}
        page = client.query(FF_EVENTS_QUERY, variables)["reportData"]["report"]["events"]
        events += page["data"]
        start = page.get("nextPageTimestamp")
    payload = {"query": FF_EVENTS_QUERY, "variables": {"code": code, "end": end, "ff": FILTERS["ff_first_hit"]},
               "fetched_at": time.time(), "data": {"events": events}}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# Parse Lord: WCL parses of the kills. "Historical" (rankings_historical.json) against the rankings around the
# date of the fight, used for both the best and the median parse; "Today" (WCL's default, rankings.json) against
# today's rankings, only a stand-in for kills without a historical parse (no longer crawled by default).
RANKINGS_QUERY = """
query($code: String!, $fid: [Int]!, $tf: RankingTimeframeType) {
  reportData { report(code: $code) { rankings(fightIDs: $fid, timeframe: $tf) } } }"""
RANKINGS_KINDS = {"rankings": "Today", "rankings_historical": "Historical"}


# Cache folder of the guild being crawled (its WCL site), set by crawl().
HOST = "classic"


def cached(code: str, name: str) -> dict | None:
    path = CACHE_DIR / HOST / "reports" / code / f"{name}.json"
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


def crawl(guild: str, kinds: set, limit: int | None, cost: bool, refresh: bool) -> None:
    global HOST
    HOST = GUILDS[guild]["host"]
    client = WCLClient(HOST)
    print("guild:", guild, "endpoint:", client.url)
    meter = Meter(client, cost)
    reports = unique_reports(client, guild)
    done = 0
    for i, r in enumerate(reports, 1):
        code, exp = r["code"], expansion_of(r, guild)
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
                    path = CACHE_DIR / HOST / f"{key}.json"
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
                path = CACHE_DIR / HOST / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    end = report["endTime"] - report["startTime"]
                    meter.run("trash", lambda: client.cached_query(key, TRASH_QUERY, {"code": code, "end": end}))
                    n += 1
            if "trash_extra" in kinds:
                key = f"reports/{code}/trash_extra"
                path = CACHE_DIR / HOST / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    variables = {"code": code, "end": report["endTime"] - report["startTime"],
                                 "ff": FILTERS["ff"], "taunts": FILTERS["taunts"]}
                    meter.run("trash_extra", lambda: client.cached_query(key, TRASH_EXTRA_QUERY, variables))
                    n += 1
            end = report["endTime"] - report["startTime"]
            if "trash_deaths" in kinds:
                key = f"reports/{code}/trash_deaths"
                path = CACHE_DIR / HOST / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    meter.run("trash_deaths", lambda: client.cached_query(key, TRASH_DEATHS_QUERY, {"code": code, "end": end}))
                    n += 1
            if "ff_events" in kinds:
                path = CACHE_DIR / HOST / "reports" / code / "ff_events.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists() and first_hit_in_ff(code):
                    meter.run("ff_events", lambda: ff_events(client, code, end))
                    n += 1
            for kind, timeframe in RANKINGS_KINDS.items():
                if kind not in kinds:
                    continue
                key = f"reports/{code}/{kind}"
                path = CACHE_DIR / HOST / f"{key}.json"
                if refresh and path.exists():
                    path.unlink()
                if not path.exists():
                    fids = [f["id"] for f in eligible if f.get("kill")]
                    if fids:
                        variables = {"code": code, "fid": fids, "tf": timeframe}
                        meter.run(kind, lambda: client.cached_query(key, RANKINGS_QUERY, variables))
                        n += 1
        except WCLError as e:
            log_error(code, e, HOST)
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
    parser.add_argument("--kinds", default="pull,trash,trash_extra,rankings_historical,trash_deaths,ff_events",
                        help="pull, trash, trash_extra, rankings, rankings_historical, trash_deaths, ff_events (comma separated)")
    parser.add_argument("--guild", choices=sorted(GUILDS), default="fable")
    parser.add_argument("--limit", type=int, help="stop after N reports with eligible pulls (testing)")
    parser.add_argument("--cost", action="store_true", help="measure points spent per query")
    parser.add_argument("--refresh", action="store_true", help="re-fetch what is already cached (after a list change)")
    a = parser.parse_args()
    crawl(a.guild, set(a.kinds.split(",")), a.limit, a.cost, a.refresh)


if __name__ == "__main__":
    main()
