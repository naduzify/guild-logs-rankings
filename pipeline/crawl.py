"""Full crawl: every guild report, level 2 tables for every eligible boss pull.

Eligibility (config/crawl.json): fight size per expansion, difficulty, minimum
number of players. Everything is cached under data/cache/, so the crawl can be
stopped at any time and resumed by running it again.

Each guild has its own cache folder, named after its WCL site (data/cache/classic for
Fable, data/cache/fresh for NightShift), so the guilds' data never mix. For a guild
still raiding, --refresh-list re-fetches the report listing; reports that ended less
than RECENT_HOURS ago are skipped, so a night still being logged is not cached half done.

Usage:
    python -m pipeline.crawl [--guild fable|nightshift] [--refresh-list] [--limit N]
"""

import argparse
import json
import time

from pipeline.guild import GUILDS, expansion_of, list_reports
from pipeline.wcl import CACHE_DIR, ROOT, WCLClient, WCLError

CONFIG = json.loads((ROOT / "config" / "crawl.json").read_text(encoding="utf-8"))
RECENT_HOURS = 24

REPORT_QUERY = """
query($code: String!) {
  reportData {
    report(code: $code) {
      code title startTime endTime
      zone { id name }
      fights(killType: Encounters) {
        id encounterID name difficulty size kill startTime endTime fightPercentage bossPercentage friendlyPlayers
      }
      masterData { actors(type: "Player") { id name server subType } }
    }
  }
}"""

TABLES_QUERY = "query($code: String!, $fid: [Int]!) { reportData { report(code: $code) { %s } } }" % " ".join(
    f"{t[0].lower() + t[1:]}: table(dataType: {t}, fightIDs: $fid)" for t in CONFIG["tables"]
)


def is_eligible(fight: dict, expansion: str) -> bool:
    return (
        fight.get("size") == CONFIG["eligible_size"][expansion]
        and fight.get("difficulty") in CONFIG["eligible_difficulties"]
        and len(fight.get("friendlyPlayers") or []) >= CONFIG["min_players"]
    )


def log_error(code: str, error: Exception, host: str = "classic") -> None:
    with (CACHE_DIR / host / "crawl_errors.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"code": code, "error": str(error)[:500], "at": time.time()}) + "\n")


def recent(report: dict) -> bool:
    return report["endTime"] / 1000 > time.time() - RECENT_HOURS * 3600


def unique_reports(client: WCLClient, guild: str, refresh_list: bool = False) -> list[dict]:
    """The guild's reports, oldest first, each code once even if it is on several guild sheets."""
    by_code = {}
    for r in list_reports(client, guild, refresh_list):
        by_code.setdefault(r["code"], r)
    return sorted(by_code.values(), key=lambda r: r["startTime"])


def crawl(guild: str, refresh_list: bool, limit: int | None) -> None:
    client = WCLClient(GUILDS[guild]["host"])
    print("guild:", guild, "endpoint:", client.url)
    reports = unique_reports(client, guild, refresh_list)
    if limit:
        reports = reports[:limit]

    started, pulls_done = time.time(), 0
    for i, r in enumerate(reports, 1):
        code, exp = r["code"], expansion_of(r, guild)
        if recent(r):
            print(f"[{i}/{len(reports)}] {exp} {code}: skipped, ended less than {RECENT_HOURS} h ago", flush=True)
            continue
        try:
            report = client.cached_query(f"reports/{code}/report", REPORT_QUERY, {"code": code})["reportData"]["report"]
            eligible = [f for f in report["fights"] if is_eligible(f, exp)]
            for f in eligible:
                client.cached_query(f"reports/{code}/tables_{f['id']:03d}", TABLES_QUERY, {"code": code, "fid": [f["id"]]})
            pulls_done += len(eligible)
        except WCLError as e:
            log_error(code, e, client.host)
            print(f"  error on {code}, logged: {str(e)[:120]}")
            continue
        zone = (r.get("zone") or {}).get("name", "?")
        hours = (time.time() - started) / 3600
        print(f"[{i}/{len(reports)}] {exp} {code} {zone}: {len(eligible)}/{len(report['fights'])} pulls "
              f"(total {pulls_done}, {client.requests_made} requests, {hours:.1f} h)", flush=True)

    print("done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guild", choices=sorted(GUILDS), default="fable")
    parser.add_argument("--refresh-list", action="store_true", help="re-fetch the report listing (guild still raiding)")
    parser.add_argument("--limit", type=int, help="only the N oldest reports (testing)")
    a = parser.parse_args()
    crawl(a.guild, a.refresh_list, a.limit)


if __name__ == "__main__":
    main()
