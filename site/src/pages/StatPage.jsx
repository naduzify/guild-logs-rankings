import { useRef, useState } from 'react';
import { FilterBar, InfoTip, PctBar, PlayerName, StatValue } from '../components.jsx';
import { BASE100, fold, formatInt, formatNumber, formatPct, formatValue, isBase100 } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat, explain, hasNumber, hasPercentile, isRankable, playerBreakdown, shareTotal, titlePercentile, valueIsNumber } from '../lib/stats.js';

export const CATEGORIES = [
  { id: 'common', label: 'Everyone' },
  { id: 'tank', label: 'Tanks' },
  { id: 'healer', label: 'Healers' },
  { id: 'dps', label: 'DPS' },
];

export function StatsIndex({ data, filter }) {
  // Highlights the achievements whose title (or flip title) contains the text, accents ignored; Enter scrolls to the first.
  const [find, setFind] = useState('');
  const list = useRef(null);
  const k = fold(find.trim());
  const found = s => k && [s.title, s.flip].some(t => t && fold(t).includes(k));
  const jump = e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    list.current?.querySelector('li.found')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  return (
    <div ref={list} className="statsindex">
      <h1 className="ptitle">All achievements</h1>
      <input className="findbox" type="search" placeholder="Highlight an achievement…" value={find} aria-label="Highlight an achievement"
        onChange={e => setFind(e.target.value)} onKeyDown={jump} />
      {CATEGORIES.map(c => (
        <section key={c.id}>
          <h2 className="cat">{c.label}</h2>
          <ul className="statlist">
            {data.meta.stats.filter(s => s.category === c.id).map(s => (
              <li key={s.id} className={found(s) ? 'found' : undefined}>
                <a href={href('stat', s.id, filter)}>{s.title}</a>
                {s.flip && <span className="flipname"> / {s.flip}</span>}
                <InfoTip stat={s} meta={data.meta} />
                <span className="sdesc">{s.description}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export default function StatPage({ data, id, filter }) {
  // Highlights rows as the player types (main or alt, accents ignored); it filters nothing.
  const [find, setFind] = useState('');
  const board = useRef(null);
  // Enter: bring the first highlighted row into view.
  const jump = e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    board.current?.querySelector('tr.found')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  const stat = data.statById.get(id);
  if (!stat) return <p className="empty">Unknown achievement. <a href={href('stats')}>See all achievements</a>.</p>;
  const { ranked, byPlayer } = computeStat(stat, data.stats[stat.id], filter, data.meta.settings, data.roleOk);
  const rows = isRankable(stat) ? ranked : [...byPlayer.values()].sort((a, b) => data.players[a.p].name.localeCompare(data.players[b.p].name));
  const showP = hasPercentile(stat), showN = hasNumber(stat);
  const showKills = stat.agg === 'parse';  // Parse Lord: the kills its average runs over
  const fmt = v => (valueIsNumber(stat) ? formatNumber(stat, v) : formatValue(stat, v));
  const { flip_percentile } = data.meta.settings;
  const title_percentile = titlePercentile(stat, data.meta.settings);
  const k = fold(find.trim());
  const found = p => k && data.players[p].chars.some(([n]) => fold(n).includes(k));

  return (
    <>
      <header className="stathead">
        <span className="kicker">{CATEGORIES.find(c => c.id === stat.category)?.label}</span>
        <h1 className="ptitle">{stat.title}{stat.flip && <span className="flipname"> / {stat.flip}</span>}</h1>
        <p className="lead">{stat.description}</p>
        <ul className="method" aria-label="How it is calculated">
          {explain(stat, data.meta.settings).map(l => <li key={l}>{l}</li>)}
        </ul>
      </header>
      <FilterBar meta={data.meta} filter={filter} onChange={f => go('stat', stat.id, f)} />
      {rows.length === 0 ? <p className="empty">Nobody qualifies with these filters.</p> : (
        <div className="tablebox">
          <table className="board" ref={board}>
            <thead>
              <tr>
                {isRankable(stat) && <th className="n">#</th>}
                <th className="l">
                  <span className="thfind">Player
                    <input type="search" placeholder="Highlight…" value={find} aria-label="Highlight a player"
                      onChange={e => setFind(e.target.value)} onKeyDown={jump} />
                  </span>
                </th>
                <th>{stat.agg === 'top' ? stat.title : isBase100(stat) ? 'Score (base 100)' : 'Value'}</th>
                {showN && <th className="hide-sm">Career</th>}
                {showKills && <th className="hide-sm">Kills</th>}
                {showP && <th className="l"><span className="lg">Percentile</span><abbr className="sm" title="Percentile">Pctl</abbr></th>}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const tag = showP && (r.pct >= title_percentile ? 'hi' : stat.flip && r.pct <= flip_percentile ? 'lo' : '');
                return (
                  <tr key={r.p} className={[tag, found(r.p) && 'found'].filter(Boolean).join(' ') || undefined}>
                    {isRankable(stat) && <td className="n">{r.pos}</td>}
                    <td className="l"><PlayerName data={data} p={r.p} filter={filter} /></td>
                    <td className={r.label ? 'v lbl' : 'v'}>{r.label ? <>{stat.breakdown
                      ? <a href={href('stat', [stat.id, data.players[r.p].name], filter)} title={`All of ${data.players[r.p].name}'s ${stat.title}`}>{r.label}</a>
                      : r.label} <span className="muted">{formatValue(stat, r.value)}{isBase100(stat) && ` ${BASE100}`}{shareTotal(stat, r)}</span></> : valueIsNumber(stat) ? fmt(r.value) : <StatValue stat={stat} row={r} parseColors />}</td>
                    {showN && <td className="v muted hide-sm">{formatNumber(stat, r.number)}</td>}
                    {showKills && <td className="v muted hide-sm">{formatInt(r.den)}</td>}
                    {showP && <td className="l"><PctBar pct={r.pct} /> <span className={r.pct >= 75 ? 'muted pctxt glow' : 'muted pctxt'}>{formatPct(r.pct, true, r.pos)}</span>
                      {/* A stat with a flip names both ends: its title at the top, its flip title at the bottom. */}
                      {tag === 'lo' && <span className="fliptag">{stat.flip}</span>}
                      {tag === 'hi' && stat.flip && <span className="fliptag earned">{stat.title}</span>}
                      {tag === 'hi' && <span className="sr-only">, {stat.title} title earned</span>}</td>}
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

// One player's own list on a breakdown stat (Arch-Nemesis: every ability that killed him; Suicide Pact: every
// raider he died with…), under the same filters as the ranking. Reached from the ranking and his player page.
export function BreakdownPage({ data, id, name, filter }) {
  // Highlights rows as the user types, as on the ranking (a raider also by his alts); Enter scrolls to the first.
  const [find, setFind] = useState('');
  const board = useRef(null);
  const jump = e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    board.current?.querySelector('tr.found')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  const stat = data.statById.get(id);
  const p = data.byName.get(name);
  if (!stat || !stat.breakdown) return <p className="empty">Unknown achievement. <a href={href('stats')}>See all achievements</a>.</p>;
  if (p == null) return <p className="empty">No player called “{name}”. <a href={href('stat', stat.id, filter)}>Back to {stat.title}</a>.</p>;
  const rows = playerBreakdown(stat, data.stats[stat.id] || [], filter, data.meta.settings, data.roleOk, p);
  const mean = stat.top_by === 'mean';
  const total = rows.reduce((t, r) => t + r.n, 0);
  const minDen = stat.min_den ?? data.meta.settings.min_den;
  // A raider of the label column who is ranked links to his own page.
  const labelCell = label => (stat.breakdown === 'Raider' && data.byName.has(label)
    ? <PlayerName data={data} p={data.byName.get(label)} filter={filter} /> : label);
  // Bosses and abilities show the expansions they were met in; raiders do not.
  const showExp = stat.breakdown !== 'Raider';
  const k = fold(find.trim());
  const found = label => {
    if (!k) return false;
    const q = stat.breakdown === 'Raider' && data.byName.get(label);
    return q != null && q !== false ? data.players[q].chars.some(([n]) => fold(n).includes(k)) : fold(label).includes(k);
  };
  return (
    <>
      <header className="stathead">
        <span className="kicker"><a href={href('stat', stat.id, filter)}>{stat.title}</a></span>
        <h1 className="ptitle"><PlayerName data={data} p={p} filter={filter} badge={30} /></h1>
        <p className="lead">{stat.description}</p>
        <ul className="method" aria-label="How it is calculated">
          <li>{stat.detail}</li>
          <li>{mean ? `Every boss he killed, by average score; ranked from ${minDen} kills.` : `Every ${stat.breakdown.toLowerCase()}, most ${stat.unit || 'times'} first.`}</li>
        </ul>
      </header>
      <FilterBar meta={data.meta} filter={filter} onChange={f => go('stat', [stat.id, name], f)} />
      {rows.length === 0 ? <p className="empty">Nothing under these filters.</p> : (
        <div className="tablebox">
          <table className="board" ref={board}>
            <thead>
              <tr>
                <th className="n">#</th>
                <th className="l">
                  <span className="thfind">{stat.breakdown}
                    <input type="search" placeholder="Highlight…" value={find} aria-label={`Highlight a ${stat.breakdown.toLowerCase()}`}
                      onChange={e => setFind(e.target.value)} onKeyDown={jump} />
                  </span>
                </th>
                {mean ? <><th>Score ({BASE100})</th><th>Kills</th></> : <><th>{stat.unit ? stat.unit[0].toUpperCase() + stat.unit.slice(1) : 'Count'}</th><th className="hide-sm">Share</th></>}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.label} className={[r.pos === 1 ? 'hi' : r.value == null && 'dim', found(r.label) && 'found'].filter(Boolean).join(' ') || undefined}>
                  <td className="n">{r.pos ?? ''}</td>
                  <td className="l">{labelCell(r.label)}{showExp && <span className="muted bdexp">{r.exps.map(e => data.meta.expansions[e].short).join(', ')}</span>}
                    {r.subs.length > 0 && <span className="bdsub">{r.subs.slice(0, 3).map(([b, n]) => (r.subs.length > 1 ? `${b} ×${formatInt(n)}` : b)).join(' · ')}{r.subs.length > 3 && ` · +${r.subs.length - 3} more`}</span>}</td>
                  {mean
                    ? <><td className="v">{r.value == null ? <span className="muted">–</span> : formatValue(stat, r.value)}</td><td className="v muted">{formatInt(r.d)}</td></>
                    : <><td className="v">{formatInt(r.n)}</td><td className="v muted hide-sm">{total ? `${(100 * r.n / total).toFixed(1)}%` : '–'}</td></>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

