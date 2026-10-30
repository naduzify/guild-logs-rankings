import { formatInt } from './format.js';

// Guild records (config/site.json -> home.records), over the boss rows of meta.guild_bosses:
// [exp, boss, heroic, kills, wipes, fastest, slowest]. Each kind ranks the bosses by one column;
// the home card shows the first, the record page the whole list.
export const duration = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

export const RECORDS = {
  most_kills: { col: 3, desc: true, label: 'Kills', value: r => `${formatInt(r[3])} kills` },
  most_wipes: { col: 4, desc: true, label: 'Wipes', value: r => `${formatInt(r[4])} wipes` },
  fastest_kill: { col: 5, desc: false, label: 'Fastest kill', value: r => duration(r[5]) },
  slowest_kill: { col: 6, desc: true, label: 'Slowest kill', value: r => duration(r[6]) },
};

// The boss rows of a record under the expansion filter, best first, with positions (ties share one).
// Bosses listed in the record's exclude, and bosses with nothing to rank (no kill, no wipe), are left out.
export function rankBosses(meta, rec, filter) {
  const kind = RECORDS[rec.kind];
  if (!kind) return [];
  const rows = (meta.guild_bosses || []).filter(r => (!filter.exp.size || filter.exp.has(r[0]))
    && !(rec.exclude || []).includes(r[1]) && r[kind.col] != null && r[kind.col] > 0);
  rows.sort((a, b) => (kind.desc ? b[kind.col] - a[kind.col] : a[kind.col] - b[kind.col]));
  let pos = 0;
  return rows.map((r, i) => {
    if (i === 0 || r[kind.col] !== rows[i - 1][kind.col]) pos = i + 1;
    return { pos, row: r };
  });
}
