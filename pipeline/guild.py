"""Guild report listing and expansion classification, shared by the probe and the crawl."""

import json
from datetime import datetime, timezone

from pipeline.wcl import CACHE_DIR, ROOT, WCLClient

EXPANSIONS = ["classic", "tbc", "wotlk", "cata", "mop"]

# Each guild: the WCL site it lives on, its guild sheets (merged), and the fallback dates
# used when a report has no zone/expansion (release dates on the guild's realm, UTC).
GUILDS = {
    "fable": {
        "host": "classic",
        "ids": [482770],
        "expansion_start": [
            ("tbc", datetime(2021, 6, 1, tzinfo=timezone.utc)),
            ("wotlk", datetime(2022, 9, 26, tzinfo=timezone.utc)),
            ("cata", datetime(2024, 5, 20, tzinfo=timezone.utc)),
            ("mop", datetime(2025, 7, 1, tzinfo=timezone.utc)),
        ],
    },
    # Anniversary realm (Thunderstrike EU), still active. Two raid teams from TBC on.
    "nightshift": {
        "host": "fresh",
        "ids": [773182, 818103],
        "expansion_start": [
            # First report in a TBC zone on the guild's sheets (2026-10-30 listing).
            ("tbc", datetime(2026, 2, 19, tzinfo=timezone.utc)),
        ],
    },
}
GUILD_ID = GUILDS["fable"]["ids"][0]

# Reports whose WCL zone gives the wrong expansion (config/crawl.json).
FORCED = json.loads((ROOT / "config" / "crawl.json").read_text(encoding="utf-8"))["report_expansion"]

REPORTS_QUERY = """
query($guild: Int!, $page: Int!) {
  reportData {
    reports(guildID: $guild, limit: 100, page: $page) {
      has_more_pages
      data { code title startTime endTime zone { id name expansion { id name } } }
    }
  }
}"""


def expansion_of(report: dict, guild: str = "fable") -> str:
    if report.get("code") in FORCED:
        return FORCED[report["code"]]
    zone = report.get("zone") or {}
    name = ((zone.get("expansion") or {}).get("name") or "").lower()
    for key, needle in [("tbc", "burning"), ("wotlk", "lich"), ("cata", "cataclysm"), ("mop", "pandaria")]:
        if needle in name:
            return key
    if "classic" in name or "vanilla" in name:
        return "classic"
    started = datetime.fromtimestamp(report["startTime"] / 1000, tz=timezone.utc)
    exp = "classic"
    for key, start in GUILDS[guild]["expansion_start"]:
        if started >= start:
            exp = key
    return exp


def list_reports(client: WCLClient, guild: str = "fable", refresh: bool = False) -> list[dict]:
    """All reports of the guild's sheets. refresh re-fetches the listing (for a guild still raiding)."""
    ids = GUILDS[guild]["ids"]
    reports = []
    for gid in ids:
        # Single-sheet guilds keep the original cache names (guild/reports_page_NNN).
        prefix = "reports_page_" + (f"{gid}_" if len(ids) > 1 else "")
        if refresh:
            for p in (CACHE_DIR / client.host / "guild").glob(f"{prefix}*.json"):
                p.unlink()
        page = 1
        while True:
            data = client.cached_query(f"guild/{prefix}{page:03d}", REPORTS_QUERY, {"guild": gid, "page": page})
            block = data["reportData"]["reports"]
            reports.extend({**r, "guildID": gid} for r in block["data"])
            if not block["has_more_pages"]:
                break
            page += 1
    return reports
