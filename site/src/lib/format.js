const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
const int = new Intl.NumberFormat('en', { maximumFractionDigits: 0 });

export function formatValue(stat, v) {
  if (v == null) return '–';
  switch (stat.format) {
    case 'pct': return `${(v * 100).toFixed(1)}%`;
    case 'score': return int.format(v);
    case 'rate': return `${v.toFixed(2)} ${stat.rate_unit || ''}`.trim();
    case 'big': return compact.format(v);
    case 'signed': return `${v >= 0 ? '+' : ''}${v.toFixed(1)}`;
    case 'pp': return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)} pts`;
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

// Text colour on a class colour fill: navy or white, whichever contrasts more (white only on Death Knight and Shaman).
const luminance = hex => {
  const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(x => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const NAVY_DEEP = '#061529';
export const classInk = hex => ((luminance(hex) + 0.05) / (luminance(NAVY_DEEP) + 0.05) >= 1.05 / (luminance(hex) + 0.05) ? NAVY_DEEP : '#ffffff');
