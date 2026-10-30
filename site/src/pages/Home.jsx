import { useState } from 'react';
import { FilterBar, InfoTip, Intro, PlayerName, StatValue } from '../components.jsx';
import { BASE100, CLASS_COLORS, formatInt, isBase100 } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { rankBosses, RECORDS } from '../lib/records.js';
import { computeStat } from '../lib/stats.js';

function GuildTotals({ data, filter }) {
  const rows = data.meta.guild_totals.filter(([e]) => !filter.exp.size || filter.exp.has(e));
  const t = rows.reduce((a, [, pulls, kills, wipes, , , raidSecs]) =>
    ({ pulls: a.pulls + pulls, kills: a.kills + kills, wipes: a.wipes + wipes, raidSecs: a.raidSecs + raidSecs }),
  { pulls: 0, kills: 0, wipes: 0, raidSecs: 0 });
  // A raider counts once if he raided in any of the filtered expansions.
  const want = filter.exp.size ? [...filter.exp].reduce((m, e) => m | 1 << e, 0) : -1;
  const raiders = data.meta.guild_raiders.reduce((n, [mask, count]) => n + (mask & want ? count : 0), 0);
  const tiles = [
    ['Hours in raid', formatInt(t.raidSecs / 3600)],
    ['Boss kills', formatInt(t.kills)],
    ['Wipes', formatInt(t.wipes)],
    ['Raiders', formatInt(raiders)],
    ['Pulls', formatInt(t.pulls)],
  ];
  return (
    <section className="tiles">
      {tiles.map(([k, v]) => <div key={k} className="tile"><span className="tv">{v}</span><span className="tk">{k}</span></div>)}
    </section>
  );
}

// Each record card shows the first boss of its ranking; the title and "View more" open the full list.
function GuildRecords({ data, filter }) {
  const { meta } = data;
  return (
    <section className="records">
      {meta.home.records.map(rec => {
        const kind = RECORDS[rec.kind];
        const r = rankBosses(meta, rec, filter)[0]?.row;
        return (
          <article key={rec.kind} className="scard big">
            <a className="slabel" href={href('record', rec.kind, filter)}>{rec.title}</a>
            <span className="svalue">{r ? kind.value(r) : '–'}</span>
            {r && <span className="rboss">{r[1]}{r[2] ? ' (H)' : ''} <small>{meta.expansions[r[0]].short}</small></span>}
            <p className="sdesc">{rec.description}</p>
            <a className="cmore" href={href('record', rec.kind, filter)} aria-label={`View every boss for ${rec.title}`}>View more →</a>
          </article>
        );
      })}
    </section>
  );
}

// Drawn once per page load, so the Hall of fame stays put while filters change.
let featuredIds = null;
function drawFeatured(meta) {
  if (!featuredIds) {
    const pinned = new Set((meta.home.pinned || []).filter(x => typeof x === 'string'));
    // Common stats only: a tank, healer or DPS stat would leave an empty card under a role or class filter.
    const pool = meta.stats.filter(s => s.category === 'common' && s.hall_of_fame !== false && !pinned.has(s.id)).map(s => s.id);
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    featuredIds = pool;
  }
  return featuredIds;
}

function TopCard({ data, stat, filter, legend = false }) {
  const { ranked } = computeStat(stat, data.stats[stat.id], filter, data.meta.settings, data.roleOk);
  const top = ranked.slice(0, legend ? data.meta.home.pinned_top_n ?? 5 : data.meta.home.top_n);
  // Legend cards (pinned stats) feature every player placed 1st to 3rd (ties included), scaled by place.
  const leaders = legend ? top.filter(r => r.pos <= 3) : [];
  const rest = legend ? top.filter(r => r.pos > 3) : top;
  // A long legend top (pinned_columns: 2, e.g. NightShift's top 10) goes two-column from 720px, stacked on
  // phones: the first pinned_left rows on the left (leaders stretched to the height of the right column),
  // the rest on the right.
  const cols = legend && (data.meta.home.pinned_columns ?? 1) > 1;
  const split = cols ? Math.max(0, (data.meta.home.pinned_left ?? leaders.length) - leaders.length) : rest.length;
  const podium = list => list.length > 0 && (
    <ol className="podium">
      {list.map(r => (
        <li key={r.p}>
          <span className="pos">{r.pos}</span>
          <PlayerName data={data} p={r.p} filter={filter} />
          <span className="val"><StatValue stat={stat} row={r} /></span>
        </li>
      ))}
    </ol>
  );
  return (
    <article className={legend ? 'card legend' : 'card'}>
      <div className="cname">
        <a className="ctitle" href={href('stat', stat.id, filter)}>{stat.title}</a>
        {isBase100(stat) && <span className="b100">{BASE100}</span>}
        <InfoTip stat={stat} meta={data.meta} />
      </div>
      <p className="cdesc">{stat.description}</p>
      {top.length === 0 ? <p className="empty">Nobody qualifies with these filters.</p> : (<div className={cols ? 'lcols' : undefined}>
        <div className="lleft">
          {leaders.length > 0 && <div className="champions">
            {leaders.map(r => (
              <div key={r.p} className={`champion c${r.pos}`}>
                <span className="pos">{r.pos}</span>
                <PlayerName data={data} p={r.p} filter={filter} badge={r.pos === 1 ? 34 : 27} />
                <span className="val"><StatValue stat={stat} row={r} /></span>
              </div>
            ))}
          </div>}
          {podium(rest.slice(0, split))}
        </div>
        {podium(rest.slice(split))}
      </div>)}
      {/* The title links too; this explicit link is the clear, tappable way to the full ranking. */}
      <a className="cmore" href={href('stat', stat.id, filter)} aria-label={`View the full ${stat.title} ranking`}>View more →</a>
    </article>
  );
}

// Hand-made honour of the Guild Legends (no stat behind it): a portrait on the left, the name on the right,
// no position and no rank badge. A name that is a ranked player links to his page; a missing portrait hides.
function HonourCard({ data, honour, filter }) {
  return (
    <article className="card legend honour">
      <div className="cname"><span className="ctitle">{honour.title}</span></div>
      <p className="cdesc">{honour.description}</p>
      {honour.entries.map((e, i) => {
        const p = data.byName.get(e.name);
        return (
          <div key={e.name} className={`honoree h${i + 1}`}>
            {e.image && <img className="portrait" src={e.image} alt="" onError={ev => { ev.currentTarget.hidden = true; }} />}
            <div className="htext">
              {p != null
                ? <a className="hname" href={href('player', e.name, filter)}>{e.name}</a>
                : <span className="hname">{e.name}</span>}
              {e.caption && <p className="hcaption">{e.caption}</p>}
            </div>
          </div>
        );
      })}
    </article>
  );
}

// Ghosts of the guild: raiders below the reset weeks cut, most weeks first. Follows the expansion filter.
function Ghosts({ data, filter }) {
  const { meta } = data;
  const [open, setOpen] = useState(false);
  const cfg = meta.home.ghosts;
  if (!cfg || !meta.ghosts) return null;
  const want = filter.exp.size ? [...filter.exp].reduce((m, e) => m | 1 << e, 0) : -1;
  const ghosts = meta.ghosts.filter(([, , mask]) => mask & want);
  const shown = open ? ghosts : ghosts.slice(0, cfg.visible);
  return (
    <section className="ghosts" aria-labelledby="ghosts-title">
      <div className="sechead"><h2 id="ghosts-title">{cfg.title}</h2><span className="muted">{formatInt(ghosts.length)} raiders</span></div>
      <p className="cdesc">{cfg.description}</p>
      <ul className="ghostlist">
        {shown.map(([name, weeks, , c]) => (
          <li key={name} title={`${weeks} reset week${weeks > 1 ? 's' : ''}${c != null ? ' · ' + meta.classes[c] : ''}`}>
            {c != null && <i style={{ background: CLASS_COLORS[meta.classes[c]] }} />}
            {name}{c != null && <span className="sr-only">, {meta.classes[c]},</span>}<small>{weeks}w</small>
          </li>
        ))}
      </ul>
      {ghosts.length > cfg.visible && (
        <button type="button" className="more" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? 'Show fewer' : `Show all ${formatInt(ghosts.length)}`}
        </button>
      )}
    </section>
  );
}

export default function Home({ data, filter }) {
  const { meta } = data;
  // Pinned: achievement ids, or hand-made honours (objects).
  const pinned = (meta.home.pinned || []).map(x => (typeof x === 'string' ? data.statById.get(x) : x)).filter(Boolean);
  // The shuffled pool, in order, keeping the first featured_count that rank someone under the filters: some
  // common stats rank DPS and healers only (Parse Lord, Glow Up…) and would be empty with the Tank filter.
  const featured = [];
  for (const id of drawFeatured(meta)) {
    if (featured.length >= meta.home.featured_count) break;
    const s = data.statById.get(id);
    if (s && computeStat(s, data.stats[s.id], filter, meta.settings, data.roleOk).ranked.length) featured.push(s);
  }
  return (
    <>
      <section className="hero">
        <h1><img className="gicon" src="./guild-icon.png" alt="" width="40" height="40" />{meta.guild.name}<small>{meta.guild.server}</small></h1>
        {meta.guild.tagline && <p>{meta.guild.tagline}</p>}
      </section>
      <Intro meta={meta} />
      <FilterBar meta={meta} filter={filter} onChange={f => go('home', null, f)} note="Guild totals follow the expansion filter only." />
      <GuildTotals data={data} filter={filter} />
      <GuildRecords data={data} filter={filter} />
      {pinned.length > 0 && (
        <section className="legends" aria-label={meta.home.pinned_title || 'Guild Legends'}>
          <h2 className="ornament"><span>{meta.home.pinned_title || 'Guild Legends'}</span></h2>
          <div className="cards pinned">
            {pinned.map(x => (x.entries ? <HonourCard key={x.id} data={data} honour={x} filter={filter} />
              : <TopCard key={x.id} data={data} stat={x} filter={filter} legend />))}
          </div>
        </section>
      )}
      <div className="sechead">
        <h2>Hall of fame</h2>
        <a href={href('stats', null, filter)}>All {meta.stats.filter(s => s.category !== 'overview').length} achievements →</a>
      </div>
      <section className="cards">
        {featured.map(s => <TopCard key={s.id} data={data} stat={s} filter={filter} />)}
      </section>
      <Ghosts data={data} filter={filter} />
    </>
  );
}
