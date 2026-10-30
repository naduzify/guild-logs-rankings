"""Fetch the parses (rankings) of reports that pipeline.crawl_extra could not get in one query.

WCL answers some rankings queries with a server error every time, typically for reports with many kills.
This asks for the kills in small chunks, splitting a failing chunk down to one kill, and writes the merged
result to the usual cache file (reports/<code>/<kind>.json, same shape: rankings.data is one entry per
fight). A kill that still fails on its own is left out and listed at the end.

Only reports listed in the guild's crawl_errors.jsonl, with eligible kills and no cache file for the kind,
are touched, so it can run alongside pipeline.crawl_extra (which never goes back to a report it has passed).
With --all, every report missing the file is fetched this way (instead of pipeline.crawl_extra), which
avoids the failed whole-report attempts on expansions where many reports are too big.

Usage:
    python -m pipeline.repair_rankings [--guild fable|nightshift] [--kinds rankings_historical] [--chunk 4] [--all]
"""

import argparse
import json
import time

from pipeline.crawl import CONFIG, is_eligible, unique_reports
from pipeline.crawl_extra import RANKINGS_KINDS, RANKINGS_QUERY
from pipeline.guild import GUILDS, expansion_of
from pipeline.wcl import CACHE_DIR, WCLClient, WCLError


def fetch(client: WCLClient, code: str, fids: list, timeframe: str, failed: list) -> list:
    """Rankings entries for these fights, splitting the request in two when WCL fails on it."""
    try:
        data = client.query(RANKINGS_QUERY, {"code": code, "fid": fids, "tf": timeframe})
        return data["reportData"]["report"]["rankings"].get("data", [])
    except WCLError as e:
        if len(fids) == 1:
            failed.append((code, fids[0], str(e)[:120]))
            return []
        half = len(fids) // 2
        return fetch(client, code, fids[:half], timeframe, failed) + fetch(client, code, fids[half:], timeframe, failed)


def repair(guild: str, kinds: list, chunk: int, everything: bool) -> None:
    host = GUILDS[guild]["host"]
    client = WCLClient(host)
    errors = CACHE_DIR / host / "crawl_errors.jsonl"
    erred = {json.loads(line)["code"] for line in errors.read_text(encoding="utf-8").splitlines()} if errors.exists() else set()
    failed, done = [], 0
    for r in unique_reports(client, guild):
        code = r["code"]
        if code in CONFIG["excluded_reports"] or (code not in erred and not everything):
            continue
        rdir = CACHE_DIR / host / "reports" / code
        if not (rdir / "report.json").exists():
            continue
        report = json.loads((rdir / "report.json").read_text(encoding="utf-8"))["data"]["reportData"]["report"]
        kills = [f["id"] for f in report["fights"] if is_eligible(f, expansion_of(r, guild)) and f.get("kill")]
        if not kills:
            continue
        for kind in kinds:
            path = rdir / f"{kind}.json"
            if path.exists():
                continue
            entries = []
            for i in range(0, len(kills), chunk):
                entries += fetch(client, code, kills[i:i + chunk], RANKINGS_KINDS[kind], failed)
            payload = {"query": RANKINGS_QUERY, "variables": {"code": code, "fid": kills, "tf": RANKINGS_KINDS[kind],
                                                              "chunked": chunk}, "fetched_at": time.time(),
                       "data": {"reportData": {"report": {"rankings": {"data": entries}}}}}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            done += 1
            print(f"{guild} {code} {kind}: {len(entries)}/{len(kills)} kills", flush=True)
    print(f"repaired {done} files; kills still failing: {len(failed)}")
    for f in failed:
        print("  ", *f)
    print("done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guild", choices=sorted(GUILDS), default="fable")
    parser.add_argument("--kinds", default="rankings_historical", help="rankings, rankings_historical (comma separated)")
    parser.add_argument("--chunk", type=int, default=4, help="kills per query")
    parser.add_argument("--all", action="store_true", help="every report missing the file, not only those in crawl_errors")
    a = parser.parse_args()
    repair(a.guild, a.kinds.split(","), a.chunk, a.all)


if __name__ == "__main__":
    main()
