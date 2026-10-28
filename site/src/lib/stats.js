// Aggregation of additive stat cells (docs/site-data.md).
// A cell is [player, expansion, class, role, ...values]; the site only sums
// the cells that pass the filters, then ranks players.

const V = 4; // index of the first value in a cell

const sumInto = (acc, cell) => { for (let i = 0; i < acc.length; i++) acc[i] += cell[V + i]; };

const AGG = {
  ratio: { init: () => [0, 0], add: sumInto, den: a => a[1], value: a => a[0] / a[1],
    number: (a, s) => (s.number === 'den' ? a[1] : a[0]) },
  sum: { init: () => [0], add: sumInto, den: () => Infinity, value: a => a[0] },
  distinct: { init: () => new Set(), add: (a, c) => c[V].forEach(x => a.add(x)), den: () => Infinity, value: a => a.size },
  diff: { init: () => [0, 0, 0, 0], add: sumInto, den: a => Math.min(a[1], a[3]), value: a => a[0] / a[1] - a[2] / a[3] },
  spread: { init: () => [0, 0, 0], add: sumInto, den: a => a[0],
    value: ([n, s, ss]) => Math.sqrt(Math.max(0, ss / n - (s / n) ** 2)) },
  slope: { init: () => [0, 0, 0, 0, 0], add: sumInto, den: a => a[0],
    value: ([n, sx, sy, sxx, sxy]) => { const d = n * sxx - sx * sx; return d ? (n * sxy - sx * sy) / d : 0; } },
  top: { init: () => ({}), den: () => Infinity,
    add: (a, c) => { for (const [k, [n, d]] of Object.entries(c[V])) { const t = a[k] || (a[k] = [0, 0]); t[0] += n; t[1] += d; } } },
  max: { init: () => [-Infinity, null], den: () => Infinity,
    add: (a, c) => { if (c[V] > a[0]) { a[0] = c[V]; a[1] = c[V + 1]; } }, value: a => a[0], label: a => a[1] },
};

// `top` picks the label with the highest count, or the highest mean among labels with enough samples.
function topOf(acc, stat, minDen) {
  let best = null;
  for (const [label, [n, d]] of Object.entries(acc)) {
    const v = stat.top_by === 'mean' ? (d >= minDen ? n / d : null) : n;
    if (v != null && (!best || v > best.value)) best = { label, value: v };
  }
  return best;
}

export function filterKey(f) {
  return ['exp', 'cls', 'role'].map(k => [...f[k]].sort().join(',')).join('|');
}

function passes(f, cell) {
  return (!f.exp.size || f.exp.has(cell[1])) && (!f.cls.size || f.cls.has(cell[2])) && (!f.role.size || f.role.has(cell[3]));
}

const cache = new Map();

// Returns { byPlayer: Map(player -> row), ranked: rows best first }.
// row = { p, value, number, label, pct, pos } ; pct/pos only for rankable stats.
export function computeStat(stat, cells, filter, settings) {
  const key = stat.id + '#' + filterKey(filter);
  if (cache.has(key)) return cache.get(key);

  const agg = AGG[stat.agg];
  const accs = new Map();
  for (const cell of cells) {
    if (!passes(filter, cell)) continue;
    let a = accs.get(cell[0]);
    if (!a) accs.set(cell[0], (a = agg.init()));
    agg.add(a, cell);
  }

  const minDen = stat.min_den ?? settings.min_den;
  const byPlayer = new Map();
  for (const [p, a] of accs) {
    if (stat.agg === 'top') {
      const t = topOf(a, stat, minDen);
      if (t) byPlayer.set(p, { p, value: t.value, number: t.value, label: t.label });
      continue;
    }
    if (agg.den(a) < minDen) continue;
    const value = agg.value(a);
    if (!Number.isFinite(value)) continue;
    byPlayer.set(p, { p, value, number: agg.number ? agg.number(a, stat) : value, label: agg.label?.(a) ?? null });
  }

  const asc = stat.direction === 'asc';
  const ranked = [...byPlayer.values()].sort((x, y) => (asc ? x.value - y.value : y.value - x.value));
  const n = ranked.length;
  ranked.forEach((r, i) => {
    // Ties share the position of the first tied player.
    r.pos = i > 0 && ranked[i - 1].value === r.value ? ranked[i - 1].pos : i + 1;
    r.pct = n > 1 ? (100 * (n - r.pos)) / (n - 1) : 100;
  });

  const out = { byPlayer, ranked };
  cache.set(key, out);
  return out;
}

export const isRankable = stat => stat.display !== 'T';
export const hasPercentile = stat => stat.display.includes('P');
// A separate career number column only makes sense for ratios: elsewhere the number is the value itself.
export const hasNumber = stat => stat.display.includes('N') && stat.agg === 'ratio';
export const valueIsNumber = stat => stat.agg === 'sum' || stat.agg === 'distinct';

// Title earned by a player on a stat, if any: the main title at the top, the flip at the bottom.
export function earnedTitle(stat, row, settings) {
  if (!row || !hasPercentile(stat)) return null;
  if (row.pct >= settings.title_percentile) return { name: stat.title, flip: false };
  if (stat.flip && row.pct <= settings.flip_percentile) return { name: stat.flip, flip: true };
  return null;
}
