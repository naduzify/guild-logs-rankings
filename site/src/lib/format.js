const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const int = new Intl.NumberFormat('en', { maximumFractionDigits: 0 });

export function formatValue(stat, v) {
  if (v == null) return '–';
  switch (stat.format) {
    case 'pct': return `${(v * 100).toFixed(1)}%`;
    case 'score': return int.format(v);
    case 'parse': return v.toFixed(1);
    case 'rate': return `${v.toFixed(2)} ${stat.rate_unit || ''}`.trim();
    case 'big': return compact.format(v);
    case 'signed': return `${v >= 0 ? '+' : ''}${v.toFixed(1)}`;
    case 'pp': return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)} pts`;
    case 'times': return `×${int.format(v)}`;
    default: return int.format(v);
  }
}

export function formatNumber(stat, n) {
  if (n == null) return '–';
  const s = stat.format === 'big' || n >= 1e6 ? compact.format(n) : int.format(n);
  return stat.unit ? `${s} ${stat.unit}` : s;
}

// Scores are relative to the role median of the pull (100 = median), never raw amounts: always label them.
export const isBase100 = stat => stat.format === 'score';
export const BASE100 = 'base 100';

// Warcraft Logs parse colours, lightened where needed to stay readable on the navy table rows.
const PARSE_COLORS = [[99, '#ee82bd'], [95, '#ff8000'], [75, '#c48af7'], [50, '#4d9bff'], [25, '#1eff00'], [0, '#9d9d9d']];
export const parseColor = v => PARSE_COLORS.find(([min]) => v >= min)[1];
// Guild rank band: light gold for #1, else parse colours by percentile, with a darker purple than the
// table's; white text on the purple, dark text on the lighter bands.
const BAND_COLORS = [[99, '#ee82bd'], [95, '#ff8000'], [75, '#8b3fd9', '#fff'], [50, '#4d9bff'], [25, '#1eff00'], [0, '#9d9d9d']];
export function rankBand(row) {
  if (row.pos === 1) return { bg: '#f6e7a6', fg: null };
  const [, bg, fg = null] = BAND_COLORS.find(([min]) => row.pct >= min);
  return { bg, fg };
}

export const formatBig = n => compact.format(n);
export const formatInt = n => int.format(n);

const ordinal = n => {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] || 'th');
};

// "96th percentile" (higher is better), kept within 1st..99th. `short` drops the word, for the Percentile column.
export function formatPct(pct, short = false) {
  if (pct == null) return '';
  const p = ordinal(Math.min(99, Math.max(1, Math.round(pct))));
  return short ? p : `${p} percentile`;
}

// Strip accents for search: "Chãos" matches "chaos".
export const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export const CLASS_COLORS = {
  'Death Knight': '#C41E3A', Druid: '#FF7C0A', Hunter: '#AAD372', Mage: '#3FC7EB', Monk: '#00FF98',
  Paladin: '#F48CBA', Priest: '#FFFFFF', Rogue: '#FFF468', Shaman: '#0070DD', Warlock: '#8788EE', Warrior: '#C69B6D',
};
