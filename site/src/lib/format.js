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

export const formatBig = n => compact.format(n);
export const formatInt = n => int.format(n);

// "Top 4%" for the upper half, "Bottom 12%" for the lower half.
export function formatPct(pct) {
  if (pct == null) return '';
  return pct >= 50 ? `Top ${Math.max(1, Math.round(100 - pct))}%` : `Bottom ${Math.max(1, Math.round(pct))}%`;
}

// Strip accents for search: "Chãos" matches "chaos".
export const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export const CLASS_COLORS = {
  'Death Knight': '#C41E3A', Druid: '#FF7C0A', Hunter: '#AAD372', Mage: '#3FC7EB', Monk: '#00FF98',
  Paladin: '#F48CBA', Priest: '#FFFFFF', Rogue: '#FFF468', Shaman: '#0070DD', Warlock: '#8788EE', Warrior: '#C69B6D',
};
