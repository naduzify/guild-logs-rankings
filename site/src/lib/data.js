// Loads the three pipeline exports (docs/site-data.md) and derives lookups the pages share.

// Relative to the guild page (/fable/), in dev and in the build alike.
const url = name => `./data/${name}.json`;

export async function loadData() {
  const [meta, players, stats] = await Promise.all(
    ['meta', 'players', 'stats'].map(n => fetch(url(n)).then(r => {
      if (!r.ok) throw new Error(`${n}.json: HTTP ${r.status}`);
      return r.json();
    })),
  );

  // Expansions, classes and roles each player actually played, from every stat's cells.
  const facets = players.map(() => ({ exp: new Set(), cls: new Set(), role: new Set() }));
  for (const cells of Object.values(stats)) {
    for (const [p, e, c, r] of cells) {
      const f = facets[p];
      f.exp.add(e); f.cls.add(c); f.role.add(r);
    }
  }

  // Time played per (expansion, class, role), for the class dots next to a name: [[e, c, r, hours], …].
  const played = players.map(() => new Map());
  for (const [p, e, c, r, v] of stats['hours-played'] || []) {
    const k = `${e}|${c}|${r}`;
    played[p].set(k, (played[p].get(k) || 0) + (Number(v) || 0));
  }
  const playedRows = played.map(m => [...m].map(([k, h]) => [...k.split('|').map(Number), h]));

  // Roles each player is ranked on: enough reset weeks in that role (settings.min_role_weeks).
  // null when the export has no role_weeks (mock data): every role passes.
  const roleOk = players.map(pl => pl.role_weeks?.map(w => w >= (meta.settings.min_role_weeks ?? 0)) ?? null);

  // Classes of each player's real characters (settings.min_char_weeks reset weeks; no weeks given = mock data):
  // a class played only on a minor reroll gives no dot next to the name.
  const isMain = ch => ch[1] != null && (ch[2] ?? Infinity) >= (meta.settings.min_char_weeks ?? 0);
  const mainClasses = players.map(pl => new Set(pl.chars.filter(isMain).map(ch => ch[1])));

  const byName = new Map(players.map((pl, i) => [pl.name, i]));
  const statById = new Map(meta.stats.map(s => [s.id, s]));
  return { meta, players, stats, facets, played: playedRows, mainClasses, isMain, roleOk, byName, statById };
}

// Classes a player played under the active filters, most played first.
export function playedClasses(data, p, filter) {
  const hours = new Map();
  for (const [e, c, r, h] of data.played[p]) {
    if (filter.exp.size && !filter.exp.has(e)) continue;
    if (filter.role.size && !filter.role.has(r)) continue;
    if (filter.cls.size && !filter.cls.has(c)) continue;
    if (!data.mainClasses[p].has(c)) continue;
    hours.set(c, (hours.get(c) || 0) + h);
  }
  return [...hours].sort((a, b) => b[1] - a[1]).map(([c]) => data.meta.classes[c]);
}
