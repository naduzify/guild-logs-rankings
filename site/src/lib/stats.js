import { formatBig, formatPct } from './format.js';

// Aggregation of additive stat cells (docs/site-data.md).
// A cell is [player, expansion, class, role, ...values]; the site only sums
// the cells that pass the filters, then ranks players.

const V = 4; // index of the first value in a cell

const sumInto = (acc, cell) => { for (let i = 0; i < acc.length; i++) acc[i] += cell[V + i]; };

const AGG = {
  // [num, den] or [num, den, count]: with "min_den_on": "count", min_den applies to the count (number of
  // pulls) instead of den, for a den that is an amount (The Terrorist: the raid's friendly fire).
  ratio: { init: () => [0, 0, 0], add: (a, c) => { a[0] += c[V]; a[1] += c[V + 1]; a[2] += c[V + 2] ?? 0; },
    den: (a, s) => (s.min_den_on === 'count' ? a[2] : a[1]), value: a => a[0] / a[1],
    number: (a, s) => (s.number === 'den' ? a[1] : a[0]) },
  // Parse Lord, per boss and weighted by its kills: [(best + median) / 2 × kills, kills, best × kills, median × kills];
  // extra = average best and median.
  parse: { init: () => [0, 0, 0, 0], add: sumInto, den: a => a[1], value: a => a[0] / a[1], extra: a => [a[2] / a[1], a[3] / a[1]] },
  sum: { init: () => [0], add: sumInto, den: () => Infinity, value: a => a[0] },
  // Career totals in reference-tier terms: [scaled, actual]; ranked on the scaled one, the actual one in brackets.
  scaled: { init: () => [0, 0], add: sumInto, den: () => Infinity, value: a => a[0], extra: a => [a[1]] },
  distinct: { init: () => new Set(), add: (a, c) => c[V].forEach(x => a.add(x)), den: () => Infinity, value: a => a.size },
  // Ids are consecutive guild raid weeks: longest run of consecutive ids (Iron Man), longest hole between two (Comeback Kid).
  streak: { init: () => new Set(), add: (a, c) => c[V].forEach(x => a.add(x)), den: () => Infinity, value: a => runs(a).streak },
  gap: { init: () => new Set(), add: (a, c) => c[V].forEach(x => a.add(x)), den: () => Infinity, value: a => runs(a).gap },
  diff: { init: () => [0, 0, 0, 0], add: sumInto, den: a => Math.min(a[1], a[3]), value: a => a[0] / a[1] - a[2] / a[3] },
  spread: { init: () => [0, 0, 0], add: sumInto, den: a => a[0],
    value: ([n, s, ss]) => Math.sqrt(Math.max(0, ss / n - (s / n) ** 2)) },
  // [n, sx, sy, sxx, sxy, tiers]: regression sums, plus the raid tiers of the points (`min_tiers`).
  slope: { init: () => [0, 0, 0, 0, 0, new Set()],
    add: (a, c) => { for (let i = 0; i < 5; i++) a[i] += c[V + i]; (c[V + 5] || []).forEach(t => a[5].add(t)); },
    den: a => a[0], tiers: a => a[5].size,
    value: ([n, sx, sy, sxx, sxy]) => { const d = n * sxx - sx * sx; return d ? (n * sxy - sx * sy) / d : 0; } },
  top: { init: () => ({}), den: () => Infinity,
    add: (a, c) => { for (const [k, [n, d]] of Object.entries(c[V])) { const t = a[k] || (a[k] = [0, 0]); t[0] += n; t[1] += d; } } },
  max: { init: () => [-Infinity, null], den: () => Infinity,
    add: (a, c) => { if (c[V] > a[0]) { a[0] = c[V]; a[1] = c[V + 1]; } }, value: a => a[0], label: a => a[1] },
};

function runs(ids) {
  const xs = [...ids].sort((a, b) => a - b);
  let streak = xs.length ? 1 : 0, gap = 0, cur = 1;
  for (let i = 1; i < xs.length; i++) {
    const d = xs[i] - xs[i - 1];
    cur = d === 1 ? cur + 1 : 1;
    streak = Math.max(streak, cur);
    gap = Math.max(gap, d - 1);
  }
  return { streak, gap };
}

// `top` picks the label with the highest count, or the highest mean among labels with enough samples.
// `share` picks the highest count among labels with enough samples, valued as its share of all labels.
function topOf(acc, stat, minDen) {
  let best = null, total = 0;
  for (const [label, [n, d]] of Object.entries(acc)) {
    total += n;
    const v = stat.top_by === 'mean' ? (d >= minDen ? n / d : null) : stat.top_by === 'share' && d < minDen ? null : n;
    if (v != null && (!best || v > best.value)) best = { label, value: v, number: n };
  }
  if (best && stat.top_by === 'share') best.value = total ? best.number / total : 0;
  return best;
}

export function filterKey(f) {
  return ['exp', 'cls', 'role'].map(k => [...f[k]].sort().join(',')).join('|');
}

function passes(f, cell) {
  return (!f.exp.size || f.exp.has(cell[1])) && (!f.cls.size || f.cls.has(cell[2])) && (!f.role.size || f.role.has(cell[3]));
}

const cache = new Map();
const ROLE_CATEGORIES = new Set(['tank', 'healer', 'dps']);

// Returns { byPlayer: Map(player -> row), ranked: rows best first }.
// row = { p, value, number, label, pct, pos } ; pct/pos only for rankable stats.
// roleOk[player][role]: enough reset weeks in that role. A player's cells in a role he is not ranked on
// are left out of role achievements, and of common ones when the role filter is set.
export function computeStat(stat, cells, filter, settings, roleOk) {
  const key = stat.id + '#' + filterKey(filter);
  if (cache.has(key)) return cache.get(key);

  const agg = AGG[stat.agg];
  const gated = roleOk && (ROLE_CATEGORIES.has(stat.category) || filter.role.size > 0);
  const accs = new Map();
  for (const cell of cells) {
    if (!passes(filter, cell)) continue;
    const ok = gated && roleOk[cell[0]];
    if (ok && !ok[cell[3]]) continue;
    let a = accs.get(cell[0]);
    if (!a) accs.set(cell[0], (a = agg.init()));
    agg.add(a, cell);
  }

  const minDen = stat.min_den ?? settings.min_den;
  const byPlayer = new Map();
  for (const [p, a] of accs) {
    if (stat.agg === 'top') {
      const t = topOf(a, stat, minDen);
      if (t) byPlayer.set(p, { p, value: t.value, number: t.number, label: t.label });
      continue;
    }
    if (agg.den(a, stat) < minDen) continue;
    if (stat.min_tiers && agg.tiers && agg.tiers(a) < stat.min_tiers) continue;
    const value = agg.value(a);
    if (!Number.isFinite(value)) continue;
    byPlayer.set(p, { p, value, number: agg.number ? agg.number(a, stat) : value, label: agg.label?.(a) ?? null, extra: agg.extra?.(a) ?? null, den: agg.den(a, stat) });
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

// One player's whole `top` breakdown (Arch-Nemesis, Personal Hell…: stats with a `breakdown`), under the same
// filters and role gating as computeStat. Rows { label, n, d, value } best first: by count, or by mean for a
// `mean` top (labels under min_den come last, with no value: too few samples to rank). exps: the expansion
// indices the label was met in (a boss or an ability can exist in several: Kel'Thuzad in Era and WotLK).
// subs: [[name, n]] most first, when the cells carry them (Arch-Nemesis: the bosses of each ability).
export function playerBreakdown(stat, cells, filter, settings, roleOk, p) {
  const gated = roleOk && (ROLE_CATEGORIES.has(stat.category) || filter.role.size > 0);
  const acc = {}, exps = {}, subs = {};
  for (const cell of cells) {
    if (cell[0] !== p || !passes(filter, cell)) continue;
    if (gated && roleOk[p] && !roleOk[p][cell[3]]) continue;
    AGG.top.add(acc, cell);
    for (const [label, t] of Object.entries(cell[V])) {
      (exps[label] || (exps[label] = new Set())).add(cell[1]);
      if (t[2]) {
        const s = subs[label] || (subs[label] = {});
        for (const [name, n] of Object.entries(t[2])) s[name] = (s[name] || 0) + n;
      }
    }
  }
  const minDen = stat.min_den ?? settings.min_den;
  const rows = Object.entries(acc).map(([label, [n, d]]) => ({
    label, n, d, value: stat.top_by === 'mean' ? (d >= minDen ? n / d : null) : n, exps: [...exps[label]].sort((a, b) => a - b),
    subs: Object.entries(subs[label] || {}).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
  }));
  rows.sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity) || b.d - a.d || a.label.localeCompare(b.label));
  let pos = 0;
  rows.forEach((r, i) => {
    if (r.value == null) return;
    if (i === 0 || r.value !== rows[i - 1].value) pos = i + 1;
    r.pos = pos;
  });
  return rows;
}

export const isRankable = stat => stat.display !== 'T';
export const hasPercentile = stat => stat.display.includes('P');
// A separate career number column only makes sense for ratios: elsewhere the number is the value itself.
export const hasNumber = stat => stat.display.includes('N') && stat.agg === 'ratio';
export const valueIsNumber = stat => ['sum', 'distinct', 'streak', 'gap'].includes(stat.agg);
// A `share` top shows its raw total in brackets after the share.
export const shareTotal = (stat, row) => (stat.top_by === 'share' ? ` (${formatBig(row.number)}${stat.unit ? ' ' + stat.unit : ''})` : '');

const ROLE_SCOPE = {
  common: 'Counts every role: use the role filter to split tank, DPS and healer.',
  tank: 'Only pulls played as a tank.',
  healer: 'Only pulls played as a healer.',
  dps: 'Only pulls played as DPS.',
};

// Plain-English method of an achievement, for its tooltip: what is measured, on which pulls, how it ranks.
export function explain(stat, settings) {
  const lines = [stat.detail, ROLE_SCOPE[stat.category]];
  const w = settings.min_role_weeks;
  if (w) lines.push(ROLE_CATEGORIES.has(stat.category)
    ? `Only players with at least ${w} reset weeks in the role.`
    : `With the role filter set, only players with at least ${w} reset weeks in that role.`);
  const minDen = stat.min_den ?? settings.min_den;
  if (hasPercentile(stat)) {
    const sample = stat.agg === 'spread' || stat.agg === 'slope' ? 'kills' : 'pulls';
    const counted = valueIsNumber(stat) && stat.agg !== 'sum';
    let rank = counted ? 'Percentile among players under the current filters'
      : `Percentile among players with at least ${minDen} ${sample} under the current filters`;
    rank += stat.direction === 'asc' ? ' (lower is better).' : '.';
    lines.push(rank);
    let earn = `${formatPct(titlePercentile(stat, settings))} and above earn “${stat.title}”`;
    if (stat.flip) earn += `, ${formatPct(settings.flip_percentile)} and below earn “${stat.flip}”`;
    lines.push(earn + '.');
  } else if (stat.top_by === 'share') {
    lines.push('Ranked from the highest share.');
  } else if (stat.agg === 'max') {
    lines.push('Best single pull of the career, ranked from highest.');
  } else if (stat.display === 'T') {
    lines.push(stat.top_by === 'mean' ? `Highest average, on at least ${minDen} kills. Shown on each player's page, not ranked.`
      : "Most frequent one. Shown on each player's page, not ranked.");
  } else {
    lines.push('Career total, ranked from highest.');
  }
  return lines.filter(Boolean);
}

// Percentile from which a stat's title is earned: its own `title_percentile`, else the site-wide one.
export const titlePercentile = (stat, settings) => stat.title_percentile ?? settings.title_percentile;

// Title earned by a player on a stat, if any: the main title at the top, the flip at the bottom.
export function earnedTitle(stat, row, settings) {
  if (!row || !hasPercentile(stat)) return null;
  if (row.pct >= titlePercentile(stat, settings)) return { name: stat.title, flip: false };
  if (stat.flip && row.pct <= settings.flip_percentile) return { name: stat.flip, flip: true };
  return null;
}
