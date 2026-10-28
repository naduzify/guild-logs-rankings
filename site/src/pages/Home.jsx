import { FilterBar, PlayerName } from '../components.jsx';
import { formatBig, formatInt, formatValue } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat } from '../lib/stats.js';

function GuildTotals({ data, filter }) {
  const rows = data.meta.guild_totals.filter(([e]) => !filter.exp.size || filter.exp.has(e));
  const t = rows.reduce((a, [, pulls, kills, wipes, dmg, secs]) =>
    ({ pulls: a.pulls + pulls, kills: a.kills + kills, wipes: a.wipes + wipes, dmg: a.dmg + dmg, secs: a.secs + secs }),
  { pulls: 0, kills: 0, wipes: 0, dmg: 0, secs: 0 });
  const tiles = [
    ['Boss kills', formatInt(t.kills)],
    ['Wipes', formatInt(t.wipes)],
    ['Damage dealt', formatBig(t.dmg)],
    ['Hours on bosses', formatInt(t.secs / 3600)],
    ['Pulls', formatInt(t.pulls)],
  ];
  return (
    <section className="tiles">
      {tiles.map(([k, v]) => <div key={k} className="tile"><span className="tv">{v}</span><span className="tk">{k}</span></div>)}
    </section>
  );
}

function TopCard({ data, stat, filter }) {
  const { ranked } = computeStat(stat, data.stats[stat.id], filter, data.meta.settings);
  const top = ranked.slice(0, data.meta.home.top_n);
  return (
    <article className="card">
      <a className="ctitle" href={href('stat', stat.id, filter)}>{stat.title}</a>
      <p className="cdesc">{stat.description}</p>
      {top.length === 0 ? <p className="empty">Nobody qualifies with these filters.</p> : (
        <ol className="podium">
          {top.map(r => (
            <li key={r.p}>
              <span className="pos">{r.pos}</span>
              <PlayerName data={data} p={r.p} filter={filter} />
              <span className="val">{formatValue(stat, r.value)}</span>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}

export default function Home({ data, filter }) {
  const { meta } = data;
  const featured = meta.home.featured.map(id => data.statById.get(id)).filter(Boolean);
  return (
    <>
      <section className="hero">
        <h1>{meta.guild.name}<small>{meta.guild.server}</small></h1>
        <p>Seven years of raiding, from Molten Core to Siege of Orgrimmar. Every pull, every wipe, every questionable decision.</p>
      </section>
      <FilterBar meta={meta} filter={filter} onChange={f => go('home', null, f)} note="Guild totals follow the expansion filter only." />
      <GuildTotals data={data} filter={filter} />
      <div className="sechead">
        <h2>Hall of fame</h2>
        <a href={href('stats', null, filter)}>All {meta.stats.length} titles →</a>
      </div>
      <section className="cards">
        {featured.map(s => <TopCard key={s.id} data={data} stat={s} filter={filter} />)}
      </section>
    </>
  );
}
