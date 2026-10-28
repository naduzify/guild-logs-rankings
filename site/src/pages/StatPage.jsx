import { FilterBar, PctBar, PlayerName } from '../components.jsx';
import { formatNumber, formatPct, formatValue } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat, hasNumber, hasPercentile, isRankable, valueIsNumber } from '../lib/stats.js';

export const CATEGORIES = [
  { id: 'common', label: 'Everyone' },
  { id: 'tank', label: 'Tanks' },
  { id: 'healer', label: 'Healers' },
  { id: 'dps', label: 'DPS' },
];

export function StatsIndex({ data, filter }) {
  return (
    <>
      <h1 className="ptitle">All titles</h1>
      {CATEGORIES.map(c => (
        <section key={c.id}>
          <h2 className="cat">{c.label}</h2>
          <ul className="statlist">
            {data.meta.stats.filter(s => s.category === c.id).map(s => (
              <li key={s.id}>
                <a href={href('stat', s.id, filter)}>{s.title}</a>
                {s.flip && <span className="flipname"> / {s.flip}</span>}
                <span className="sdesc">{s.description}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

export default function StatPage({ data, id, filter }) {
  const stat = data.statById.get(id);
  if (!stat) return <p className="empty">Unknown title. <a href={href('stats')}>See all titles</a>.</p>;
  const { ranked, byPlayer } = computeStat(stat, data.stats[stat.id], filter, data.meta.settings);
  const rows = isRankable(stat) ? ranked : [...byPlayer.values()].sort((a, b) => data.players[a.p].name.localeCompare(data.players[b.p].name));
  const showP = hasPercentile(stat), showN = hasNumber(stat);
  const fmt = v => (valueIsNumber(stat) ? formatNumber(stat, v) : formatValue(stat, v));
  const { title_percentile, flip_percentile } = data.meta.settings;

  return (
    <>
      <header className="stathead">
        <span className="kicker">{CATEGORIES.find(c => c.id === stat.category)?.label}</span>
        <h1 className="ptitle">{stat.title}{stat.flip && <span className="flipname"> / {stat.flip}</span>}</h1>
        <p className="lead">{stat.description}</p>
        <p className="detail">{stat.detail}</p>
        {stat.joke && <p className="joke">{stat.joke}</p>}
      </header>
      <FilterBar meta={data.meta} filter={filter} onChange={f => go('stat', stat.id, f)} />
      {rows.length === 0 ? <p className="empty">Nobody qualifies with these filters.</p> : (
        <div className="tablebox">
          <table className="board">
            <thead>
              <tr>
                {isRankable(stat) && <th className="n">#</th>}
                <th className="l">Player</th>
                <th>{stat.agg === 'top' ? stat.title : 'Value'}</th>
                {showN && <th>Career</th>}
                {showP && <th className="l">Percentile</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const tag = showP && (r.pct >= title_percentile ? 'hi' : stat.flip && r.pct <= flip_percentile ? 'lo' : '');
                return (
                  <tr key={r.p} className={tag || undefined}>
                    {isRankable(stat) && <td className="n">{r.pos}</td>}
                    <td className="l"><PlayerName data={data} p={r.p} filter={filter} /></td>
                    <td className="v">{r.label ? <>{r.label} <span className="muted">{formatValue(stat, r.value)}</span></> : fmt(r.value)}</td>
                    {showN && <td className="v muted">{formatNumber(stat, r.number)}</td>}
                    {showP && <td className="l"><PctBar pct={r.pct} /> <span className="muted">{formatPct(r.pct)}</span>
                      {tag === 'lo' && <span className="fliptag">{stat.flip}</span>}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
