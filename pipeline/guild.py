"""Guild report listing and expansion classification, shared by the probe and the crawl."""

from datetime import datetime, timezone

from pipeline.wcl import WCLClient

GUILD_ID = 482770
EXPANSIONS = ["classic", "tbc", "wotlk", "cata", "mop"]
# Fallback when a report has no zone/expansion: release dates on Arugal (UTC).
EXPANSION_START = [
    ("tbc", datetime(2021, 6, 1, tzinfo=timezone.utc)),
    ("wotlk", datetime(2022, 9, 26, tzinfo=timezone.utc)),
    ("cata", datetime(2024, 5, 20, tzinfo=timezone.utc)),
    ("mop", datetime(2025, 7, 1, tzinfo=timezone.utc)),
]

REPORTS_QUERY = """
query($guild: Int!, $page: Int!) {
  reportData {
    reports(guildID: $guild, limit: 100, page: $page) {
      has_more_pages
      data { code title startTime endTime zone { id name expansion { id name } } }
    }
  }
}"""


def expansion_of(report: dict) -> str:
    zone = report.get("zone") or {}
    name = ((zone.get("expansion") or {}).get("name") or "").lower()
    for key, needle in [("tbc", "burning"), ("wotlk", "lich"), ("cata", "cataclysm"), ("mop", "pandaria")]:
        if needle in name:
            return key
    if "classic" in name or "vanilla" in name:
        return "classic"
    started = datetime.fromtimestamp(report["startTime"] / 1000, tz=timezone.utc)
    exp = "classic"
    for key, start in EXPANSION_START:
        if started >= start:
            exp = key
    return exp


def list_reports(client: WCLClient) -> list[dict]:
    reports, page = [], 1
    while True:
        data = client.cached_query(f"guild/reports_page_{page:03d}", REPORTS_QUERY, {"guild": GUILD_ID, "page": page})
        block = data["reportData"]["reports"]
        reports.extend(block["data"])
        if not block["has_more_pages"]:
            return reports
        page += 1
