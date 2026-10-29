"""Round trip of the reroll mapping (fable_rerolls.json) through a spreadsheet.

export: writes data/exports/rerolls.csv, one line per character seen in an eligible pull (ranked
players and ghosts alike), with the player it is mapped to and what helps decide (class, role,
reset weeks, dates). Open it in Google Sheets, fix the Player column, download it back as CSV.

import: reads that CSV back and rewrites fable_rerolls.json: every character goes to the player in
its Player column; a player is listed with his other characters as rerolls. Only the Player and
Character columns are read.

Usage:
    python -m pipeline.rerolls_sheet export
    python -m pipeline.rerolls_sheet import path/to/rerolls.csv
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pipeline.export_site import CLASS_NAME, WEEK_MS, dedup, load
from pipeline.facts import CONFIG, ROOT, load_mapping, norm, pull_rows, pulls_from_cache

MAPPING = ROOT / "fable_rerolls.json"
OUT = ROOT / "data" / "exports" / "rerolls.csv"
COLUMNS = ["Player", "Character", "Class", "Main role", "Status", "Player weeks", "Character weeks",
           "Pulls", "Expansions", "First raid", "Last raid", "Mapped"]


def export() -> None:
    owner = load_mapping()
    mapped = set(owner)
    issues = Counter()
    pulls = defaultdict(list)
    for p in pulls_from_cache():
        for r in pull_rows(p, owner, issues):
            pulls[r["source"]].append(r)
    rows = [r for rs in dedup(pulls).values() for r in rs]

    anchor = datetime.fromisoformat(CONFIG["reset_anchor_utc"]).replace(tzinfo=timezone.utc).timestamp() * 1000
    tz = ZoneInfo(CONFIG["night"]["timezone"])
    exps = load("tiers")["expansions"]
    exp_order = {"classic": 0, "tbc": 1, "wotlk": 2, "cata": 3, "mop": 4}
    player_weeks, char_weeks = defaultdict(set), defaultdict(set)
    info = defaultdict(lambda: {"class": Counter(), "role": Counter(), "exp": set(), "pulls": 0, "first": None, "last": None})
    for r in rows:
        week = int((r["start_ms"] - anchor) // WEEK_MS)
        player_weeks[r["player"]].add(week)
        char_weeks[r["char"]].add(week)
        c = info[r["char"]]
        c["player"] = r["player"]
        if r["class"] and r["class"] != "Unknown":
            c["class"][CLASS_NAME.get(r["class"], r["class"])] += 1
        c["role"][r["role"]] += 1
        c["exp"].add(exp_order[r["expansion"]])
        c["pulls"] += 1
        c["first"] = min(c["first"] or r["start_ms"], r["start_ms"])
        c["last"] = max(c["last"] or r["start_ms"], r["start_ms"])

    # Sydney date, 6 hours back so that pulls after midnight stay on their evening.
    day = lambda ms: (datetime.fromtimestamp(ms / 1000, tz) - timedelta(hours=6)).date().isoformat()
    lines = []
    for ch, c in info.items():
        pl = c["player"]
        lines.append([
            pl, ch,
            c["class"].most_common(1)[0][0] if c["class"] else "",
            {"TANK": "Tank", "DPS": "DPS", "HEALER": "Healer"}[c["role"].most_common(1)[0][0]],
            "Ranked" if len(player_weeks[pl]) >= 15 else "Ghost",
            len(player_weeks[pl]), len(char_weeks[ch]), c["pulls"],
            ", ".join(exps[e]["short"] for e in sorted(c["exp"])),
            day(c["first"]), day(c["last"]),
            "yes" if norm(ch) in mapped else "",
        ])
    # Players with the most reset weeks first, each player's characters together, most played first.
    lines.sort(key=lambda l: (-l[5], norm(l[0]), l[0] != l[1], -l[6], norm(l[1])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(lines)
    players = {l[0] for l in lines}
    print(f"{len(lines)} characters, {len(players)} players "
          f"({sum(1 for p in players if len(player_weeks[p]) >= 15)} ranked) -> {OUT}")


def import_(path: str) -> None:
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = [(l["Player"].strip(), l["Character"].strip()) for l in csv.DictReader(f)]
    chars = defaultdict(list)
    seen = {}
    for pl, ch in lines:
        if not pl or not ch:
            continue
        if norm(ch) in seen and seen[norm(ch)] != pl:
            raise SystemExit(f"{ch} is given to both {seen[norm(ch)]} and {pl}")
        seen[norm(ch)] = pl
        if norm(ch) != norm(pl):
            chars[pl].append(ch)
    data = json.loads(MAPPING.read_text(encoding="utf-8"))
    data["rerolls"] = {pl: sorted(alts, key=norm) for pl, alts in sorted(chars.items(), key=lambda kv: norm(kv[0]))}
    MAPPING.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['rerolls'])} players with rerolls, {sum(map(len, data['rerolls'].values()))} rerolls -> {MAPPING}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export")
    imp = sub.add_parser("import")
    imp.add_argument("csv")
    a = parser.parse_args()
    export() if a.cmd == "export" else import_(a.csv)


if __name__ == "__main__":
    main()
