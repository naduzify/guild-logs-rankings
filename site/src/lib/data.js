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

  const byName = new Map(players.map((pl, i) => [pl.name, i]));
  const statById = new Map(meta.stats.map(s => [s.id, s]));
  return { meta, players, stats, facets, byName, statById };
}
