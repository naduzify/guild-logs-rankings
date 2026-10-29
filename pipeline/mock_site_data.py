"""Fake site data in the pipeline -> site format (docs/site-data.md).

Stand-in until the compute step exists: lets the site be built against the
real contract. Player names come from the reroll mapping, plus random filler
players; every number is random (seeded, so the output is stable).

Usage:
    python -m pipeline.mock_site_data [--players N] [--seed S]
"""

import argparse
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "site" / "public" / "fable" / "data"

CLASSES = ["Death Knight", "Druid", "Hunter", "Mage", "Monk", "Paladin", "Priest", "Rogue", "Shaman", "Warlock", "Warrior"]
ROLES = ["TANK", "DPS", "HEALER"]
CLASS_ROLES = {
    "Death Knight": ["TANK", "DPS"], "Druid": ["TANK", "DPS", "HEALER"], "Hunter": ["DPS"], "Mage": ["DPS"],
    "Monk": ["TANK", "DPS", "HEALER"], "Paladin": ["TANK", "DPS", "HEALER"], "Priest": ["DPS", "HEALER"],
    "Rogue": ["DPS"], "Shaman": ["DPS", "HEALER"], "Warlock": ["DPS"], "Warrior": ["TANK", "DPS"],
}
# First expansion index where the class exists.
CLASS_FROM = {"Death Knight": 2, "Monk": 4}
# Reset weeks per expansion, as [first, last) week indices.
WEEKS = [(0, 100), (100, 190), (190, 280), (280, 350), (350, 420)]
EXP_START = [date(2019, 8, 27), date(2021, 6, 1), date(2022, 9, 26), date(2024, 5, 20), date(2025, 7, 1)]
BOSSES = [
    ["Lucifron", "Ragnaros", "Onyxia", "Razorgore", "Nefarian", "C'Thun", "Patchwerk", "Loatheb", "Sapphiron", "Kel'Thuzad"],
    ["Gruul", "Magtheridon", "Lady Vashj", "Kael'thas", "Archimonde", "Illidan", "Kalecgos", "Brutallus", "M'uru", "Kil'jaeden"],
    ["Sartharion", "Malygos", "XT-002", "Mimiron", "Yogg-Saron", "Anub'arak", "Festergut", "Putricide", "Sindragosa", "The Lich King"],
    ["Halfus", "Cho'gall", "Nefarian", "Alysrazor", "Ragnaros", "Morchok", "Ultraxion", "Spine of Deathwing", "Madness of Deathwing"],
    ["Stone Guard", "Elegon", "Grand Empress", "Sha of Fear", "Horridon", "Ji-Kun", "Lei Shen", "Immerseus", "Thok", "Garrosh"],
]
NEMESES = [
    ["Lava Burst", "Wrath of Ragnaros", "Shadow Flame", "Frost Breath", "Mortal Wound"],
    ["Shatter", "Fel Flames", "Tainted Elemental", "Parasitic Shadowfiend", "Fire Bloom"],
    ["Fury of Frostmourne", "Mutated Infection", "Unchained Magic", "Defile", "Malleable Goo"],
    ["Blazing Inferno", "Fiery Vortex", "Hour of Twilight", "Elementium Bolt", "Cataclysm"],
    ["Overcharge", "Static Shock", "Swirling Corruption", "Defile Ground", "Whirling Corruption"],
]
SYLLABLES = ["ka", "zu", "ri", "mo", "tha", "gor", "lin", "dra", "vel", "ash", "no", "bel", "kri", "sha", "tor", "mi", "ra", "vex"]


def filler_name(rng: random.Random, taken: set) -> str:
    while True:
        name = "".join(rng.choice(SYLLABLES) for _ in range(rng.randint(2, 3))).capitalize()
        if name not in taken:
            taken.add(name)
            return name


def make_players(rng: random.Random, count: int, ntiers_by_exp: list) -> list:
    rerolls = json.loads((ROOT / "fable_rerolls.json").read_text(encoding="utf-8"))["rerolls"]
    taken = {n for main, alts in rerolls.items() for n in [main, *alts]}
    roster = list(rerolls.items())
    while len(roster) < count:
        roster.append((filler_name(rng, taken), [filler_name(rng, taken) for _ in range(rng.choice([0, 0, 0, 1, 2]))]))

    players = []
    for main, alts in roster[:count]:
        first = rng.choices(range(5), weights=[6, 3, 3, 2, 2])[0]
        last = rng.randint(first, min(4, first + rng.choice([0, 1, 2, 4])))
        chars = []
        for name in [main, *alts]:
            options = [c for c in CLASSES if CLASS_FROM.get(c, 0) <= last]
            chars.append([name, CLASSES.index(rng.choice(options))])
        # Per expansion: which character, and which roles, the player raided with.
        played = []
        for e in range(first, last + 1):
            usable = [i for i, (_, c) in enumerate(chars) if CLASS_FROM.get(CLASSES[c], 0) <= e] or [0]
            for ci in rng.sample(usable, k=min(len(usable), rng.choice([1, 1, 1, 2]))):
                cls = CLASSES[chars[ci][1]]
                roles = CLASS_ROLES[cls]
                main_role = rng.choice(roles)
                played.append((e, chars[ci][1], ROLES.index(main_role), rng.randint(40, 320)))
                if len(roles) > 1 and rng.random() < 0.3:
                    other = rng.choice([r for r in roles if r != main_role])
                    played.append((e, chars[ci][1], ROLES.index(other), rng.randint(5, 60)))
        tiers = [t for e in range(first, last + 1) for t in ntiers_by_exp[e] if rng.random() < 0.85]
        players.append({"name": main, "chars": chars, "tiers": tiers, "rank": min(14, len(tiers)), "_played": played,
                        "_trait": {s: rng.gauss(0, 1) for s in range(64)}})
    return players


def cell_values(stat: dict, idx: int, rng: random.Random, player: dict, p: int, e: int, pulls: int):
    trait = player["_trait"][idx]
    noise = lambda sd: rng.gauss(trait, sd)
    agg, fmt = stat["agg"], stat["format"]
    kills = max(1, int(pulls * rng.uniform(0.4, 0.7)))
    # Overview counts: kills and wipes must add up to the pulls of the cell.
    if stat["id"] == "hours-played":
        return [round(pulls * rng.uniform(3.5, 5.5) / 60, 1)]
    if stat["id"] in ("boss-kills", "wipes"):
        k = int(pulls * (0.4 + 0.25 * (player["_trait"][0] > 0)))
        return [k if stat["id"] == "boss-kills" else pulls - k]

    if agg == "ratio":
        if fmt == "pct":
            rate = min(0.98, max(0.0, 0.25 + 0.1 * noise(0.5)))
            den = pulls
            return [round(rate * den, 2), den] + ([den] if stat.get("min_den_on") == "count" else [])
        if fmt == "score":
            return [round(kills * max(20, 100 + 18 * noise(0.6)), 1), kills]
        if fmt == "signed":
            return [round(kills * 8 * noise(0.6), 1), kills]
        rate = max(0.0, 0.3 + 0.12 * noise(0.5))
        return [round(rate * pulls, 1), pulls]
    if agg == "parse":
        bosses = max(1, kills // 4)
        best = [min(99.0, max(5.0, 60 + 12 * noise(0.6) + rng.uniform(0, 15))) for _ in range(bosses)]
        med = [max(1.0, b - rng.uniform(3, 20)) for b in best]
        return [round(sum((b + m) / 2 for b, m in zip(best, med)), 1), bosses, round(sum(best), 1), round(sum(med), 1)]
    if agg == "scaled":
        actual = max(0, int(50_000_000 * pulls * (1 + e) ** 3 * max(0.1, 1 + 0.4 * noise(0.5))))
        return [round(actual / (1 + e) ** 3, 1), actual]
    if agg == "sum":
        scale = 2_000_000 if fmt == "big" else 6
        return [max(0, int(scale * pulls / 100 * max(0.0, 1 + 0.5 * noise(0.5))))]
    if agg in ("streak", "gap"):
        lo, hi = WEEKS[e]
        return [sorted(rng.sample(range(lo, hi), min(hi - lo, max(1, int((hi - lo) * min(1.0, pulls / 300) * rng.uniform(0.5, 1.0))))))]
    if agg == "distinct":
        if stat["id"] == "identity-crisis":
            return [[p * 10 + c for c, _ in enumerate(player["chars"])][: rng.randint(1, len(player["chars"]))]]
        lo, hi = WEEKS[e] if stat["id"] == "the-gang" else (e * 40, e * 40 + len(BOSSES[e]) * 2)
        k = min(hi - lo, max(1, int((hi - lo) * min(1.0, pulls / 300) * rng.uniform(0.5, 1.0))))
        return [sorted(rng.sample(range(lo, hi), k))]
    if agg == "diff":
        a = 0.45 + 0.04 * noise(0.5)
        b = 0.45
        return [round(a * pulls, 1), pulls, round(b * pulls, 1), pulls]
    if agg == "spread":
        scores = [100 + rng.gauss(0, 12 + 4 * abs(trait)) for _ in range(kills)]
        return [kills, round(sum(scores), 1), round(sum(s * s for s in scores), 1)]
    if agg == "slope":
        lo, hi = WEEKS[e]
        xs = [rng.uniform(lo, hi) for _ in range(kills)]
        ys = [100 + 0.05 * trait * (x - 200) + rng.gauss(0, 10) for x in xs]
        tiers = rng.sample(range(e * 4, e * 4 + 4), rng.randint(1, 4))
        return [kills, round(sum(xs), 1), round(sum(ys), 1), round(sum(x * x for x in xs), 1), round(sum(x * y for x, y in zip(xs, ys)), 1), tiers]
    if agg == "top":
        if stat["id"] in ("favorite-patient", "guardian-angel"):
            labels = player["_friends"]
            return [{l: [int(rng.uniform(1e6, 4e7)), rng.randint(5, 60)] for l in rng.sample(labels, 3)}]
        labels = NEMESES[e] if stat["id"] == "arch-nemesis" else player["_friends"] if stat["id"] == "suicide-pact" else BOSSES[e]
        if stat["top_by"] == "mean":
            return [{l: [round(n * (100 + 20 * noise(0.8)), 1), n] for l in rng.sample(labels, 3) for n in [rng.randint(1, 12)]}]
        return [{l: [rng.randint(1, 25), 1] for l in rng.sample(labels, 3)}]
    if agg == "max":
        day = EXP_START[e] + timedelta(weeks=rng.randint(0, WEEKS[e][1] - WEEKS[e][0] - 1))
        if stat["id"] == "obliterated":
            return [round(400 + 150 * noise(0.7), 1), f"{rng.choice(NEMESES[e])} · {rng.choice(BOSSES[e])} · {day.isoformat()}"]
        return [round(150 + 30 * noise(0.7), 1), f"{rng.choice(BOSSES[e])} · {day.isoformat()}"]
    raise ValueError(f"unknown agg {agg}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--players", type=int, default=140)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    tiers_cfg = json.loads((ROOT / "config" / "tiers.json").read_text(encoding="utf-8"))
    stats_cfg = json.loads((ROOT / "config" / "stats.json").read_text(encoding="utf-8"))["stats"]
    site_cfg = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
    exp_ids = [x["id"] for x in tiers_cfg["expansions"]]
    tiers = [{k: t[k] for k in ("id", "name", "short", "expansion")} for t in tiers_cfg["tiers"]]
    ntiers_by_exp = [[i for i, t in enumerate(tiers) if t["expansion"] == x] for x in exp_ids]

    players = make_players(rng, args.players, ntiers_by_exp)
    names = [pl["name"] for pl in players]
    for pl in players:
        pl["_friends"] = rng.sample([n for n in names if n != pl["name"]], 8)

    stats = {}
    for idx, stat in enumerate(stats_cfg):
        role_only = {"tank": 0, "dps": 1, "healer": 2}.get(stat["category"])
        cells = []
        for p, pl in enumerate(players):
            for e, c, r, pulls in pl["_played"]:
                if role_only is not None and r != role_only:
                    continue
                cells.append([p, e, c, r, *cell_values(stat, idx, rng, pl, p, e, pulls)])
        stats[stat["id"]] = cells

    guild_totals = []
    for e in range(len(exp_ids)):
        pulls = rng.randint(1500, 4000)
        kills = int(pulls * rng.uniform(0.35, 0.6))
        boss_secs = pulls * rng.randint(200, 360)
        guild_totals.append([e, pulls, kills, pulls - kills, rng.randint(2, 9) * 10**10 * (e + 1), boss_secs, int(boss_secs * rng.uniform(2.2, 3))])

    # Raiders by bitmask of the expansions they raided in: qualified players, plus pugs seen in one or two expansions.
    masks = {}
    for pl in players:
        m = sum(1 << e for e in {e for e, _, _, _ in pl["_played"]})
        masks[m] = masks.get(m, 0) + 1
    for _ in range(args.players * 3):
        e = rng.randrange(len(exp_ids))
        m = 1 << e | (1 << (e + 1) if e + 1 < len(exp_ids) and rng.random() < 0.2 else 0)
        masks[m] = masks.get(m, 0) + 1
    guild_raiders = sorted(masks.items())

    # Ghosts of Fable: raiders below the min_weeks cut, [name, reset weeks, expansion mask, class index].
    taken = {pl["name"] for pl in players}
    ghosts = []
    for _ in range(args.players * 2):
        e = rng.randrange(len(exp_ids))
        ghosts.append([filler_name(rng, taken), rng.randint(1, 14), 1 << e, rng.randrange(len(CLASSES))])
    ghosts.sort(key=lambda g: (-g[1], g[0]))

    guild_bosses = []
    for e, bosses in enumerate(BOSSES):
        for boss in bosses:
            for heroic in ([0, 1] if e >= 2 else [0]):
                fastest = rng.randint(40, 300)
                guild_bosses.append([e, boss, heroic, rng.randint(5, 120), rng.randint(0, 250), fastest, fastest + rng.randint(30, 600)])

    meta = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mock": True,
        "guild": {"name": "Fable", "server": "Arugal (AU)"},
        "expansions": tiers_cfg["expansions"],
        "tiers": tiers,
        "classes": CLASSES,
        "roles": ROLES,
        "rank": {"max": tiers_cfg["rank"]["max"], "names": tiers_cfg["rank"]["names"]},
        "settings": {k: site_cfg[k] for k in ("title_percentile", "flip_percentile", "min_den", "min_weeks")},
        "home": {k: v for k, v in site_cfg["home"].items() if not k.startswith("_")},
        "player": {k: v for k, v in site_cfg["player"].items() if not k.startswith("_")},
        "stats": stats_cfg,
        "guild_totals": guild_totals,
        "guild_bosses": guild_bosses,
        "guild_raiders": guild_raiders,
        "ghosts": ghosts,
    }
    for pl in players:
        idx = {q["name"]: i for i, q in enumerate(players)}
        pl["friends"] = sorted(([idx[n], *(rng.randint(0, 40) for _ in range(5))] for n in pl["_friends"] if n in idx),
                               key=lambda f: -sum(f[1:]))
    public_players = [{k: pl[k] for k in ("name", "chars", "tiers", "rank", "friends")} for pl in players]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in (("meta", meta), ("players", public_players), ("stats", stats)):
        (OUT_DIR / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT_DIR.glob("*.json"))
    print(f"{len(players)} players, {sum(len(c) for c in stats.values())} cells, {size / 1e6:.1f} MB -> {OUT_DIR}")


if __name__ == "__main__":
    main()
