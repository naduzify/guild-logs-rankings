import { useState } from 'react';
import { FilterBar, InfoTip, PctBar, RankBadge, roleLabel } from '../components.jsx';
import { CLASS_COLORS, formatInt, formatNumber, formatPct, formatValue } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat, earnedTitle, hasNumber, hasPercentile, isRankable, valueIsNumber } from '../lib/stats.js';

const ROLE_CATEGORY = { TANK: 'tank', HEALER: 'healer', DPS: 'dps' };

// Drop filter values the player never played, so a filter carried over from
// another page cannot empty his card.
function restrict(filter, facets) {
  const out = {};
  for (const k of ['exp', 'cls', 'role']) out[k] = new Set([...filter[k]].filter(v => facets[k].has(v)));
  return out;
}

// Roles the player played under the expansion/class filters, most hours first: the first one is his main role.
function rolesByWeight(data, p, eff) {
  const hours = new Map();
  for (const [cp, e, c, r, h] of data.stats['hours-played'] || []) {
    if (cp !== p || (eff.exp.size && !eff.exp.has(e)) || (eff.cls.size && !eff.cls.has(c))) continue;
    hours.set(r, (hours.get(r) || 0) + h);
  }
  return [...hours.entries()].sort((a, b) => b[1] - a[1]).map(([r]) => data.meta.roles[r]);
}

// How remarkable a result is: high percentile, or low percentile on a stat that has a flip title.
function notability(stat, row) {
  if (!row || !isRankable(stat)) return null;
  return stat.flip ? Math.max(row.pct, 100 - row.pct) : row.pct;
}

function cardView(data, stat, row, total) {
  const settings = data.meta.settings;
  const flipSide = stat.flip && row && isRankable(stat) && row.pct < 50;
  const value = valueIsNumber(stat) ? formatNumber(stat, row.value) : formatValue(stat, row.value);
  return {
    label: flipSide ? stat.flip : stat.title,
    earned: earnedTitle(stat, row, settings),
    flipSide,
    // `top` shows the winning label (a boss, a spell), `max` the score with its pull underneath.
    main: stat.agg === 'top' ? row.label : value,
    sub: stat.agg === 'top' ? formatValue(stat, row.value) + (stat.unit ? ` ${stat.unit}` : '') : row.label,
    number: hasNumber(stat) ? formatNumber(stat, row.number) : null,
    pct: hasPercentile(stat) ? row.pct : null,
    pos: isRankable(stat) ? `#${row.pos} of ${total}` : null,
    desc: flipSide ? stat.detail : stat.description,
  };
}

function StatCard({ data, stat, row, total, big }) {
  if (!row) {
    return (
      <article className="scard small empty-card">
        <header><a className="slabel" href={href('stat', stat.id)}>{stat.title}</a><InfoTip stat={stat} meta={data.meta} /></header>
        <div className="svalue">–</div>
        <p className="sfoot">Not enough pulls</p>
      </article>
    );
  }
  const v = cardView(data, stat, row, total);
  const tone = v.earned ? (v.earned.flip ? ' lo' : ' hi') : v.flipSide ? ' flipside' : '';
  return (
    <article className={'scard ' + (big ? 'big' : 'small') + tone}>
      {v.earned && <span className="ribbonwrap"><span className="ribbon">{v.earned.flip ? 'Infamous' : 'Earned'}</span></span>}
      <header><a className="slabel" href={href('stat', stat.id)}>{v.label}</a><InfoTip stat={stat} meta={data.meta} /></header>
      <div className="svalue">{v.main}</div>
      {v.sub && <div className="ssub">{v.sub}</div>}
      {big && <p className="sdesc">{v.desc}</p>}
      <footer className="sfoot">
        {v.pct != null && <span className="pct"><PctBar pct={v.pct} /> {formatPct(v.pct)}</span>}
        {big && v.pos && <span>{v.pos}</span>}
        {big && v.number && <span>{v.number}</span>}
      </footer>
    </article>
  );
}

function Section({ data, title, kicker, items, open, onToggle }) {
  const cfg = data.meta.player;
  const big = items
    .filter(it => it.note != null && it.note >= cfg.featured_min_pct)
    .sort((a, b) => b.note - a.note)
    .slice(0, cfg.featured_per_category);
  const bigIds = new Set(big.map(it => it.stat.id));
  // Small cards: text results (nemesis, comfort boss…) first, then by how remarkable they are.
  const rank = it => (it.row && it.note == null ? 101 : it.note ?? -1);
  const small = items.filter(it => !bigIds.has(it.stat.id)).sort((a, b) => rank(b) - rank(a));
  const shown = open ? small : small.slice(0, cfg.visible_small);
  return (
    // No visible heading: categories are told apart by spacing only.
    <section className="psec" aria-label={kicker ? `${title}, ${kicker}` : title}>
      {big.length > 0 && <div className="bigcards">{big.map(it => <StatCard key={it.stat.id} data={data} {...it} big />)}</div>}
      <div className="smallcards">{shown.map(it => <StatCard key={it.stat.id} data={data} {...it} />)}</div>
      {small.length > cfg.visible_small && (
        <button type="button" className="more" onClick={onToggle} aria-expanded={open}>
          {open ? 'Show fewer' : `Show ${small.length - cfg.visible_small} more`}
        </button>
      )}
    </section>
  );
}

export default function PlayerPage({ data, name, filter }) {
  const [openSections, setOpenSections] = useState({});
  const p = data.byName.get(name);
  if (p == null) return <p className="empty">No player called “{name}”. Players need 15 reset weeks of raiding to show up.</p>;
  const pl = data.players[p];
  const { meta } = data;
  const facets = data.facets[p];
  const eff = restrict(filter, facets);
  const overviewIds = new Set(meta.player.overview.map(o => o.stat));

  const result = stat => {
    const { byPlayer, ranked } = computeStat(stat, data.stats[stat.id] || [], eff, meta.settings);
    const row = byPlayer.get(p);
    return { stat, row, total: ranked.length, note: notability(stat, row) };
  };
  const itemsOf = category => meta.stats.filter(s => s.category === category && !overviewIds.has(s.id)).map(result);

  const roleOk = r => !eff.role.size || eff.role.has(meta.roles.indexOf(r));
  const roles = rolesByWeight(data, p, eff).filter(roleOk);
  const sections = [{ id: 'common', title: 'Common', kicker: eff.role.size ? `as ${[...eff.role].map(r => roleLabel(meta.roles[r])).join(' / ')}` : 'all roles' }]
    .concat(roles.map((r, i) => ({ id: ROLE_CATEGORY[r], title: roleLabel(r), kicker: i === 0 ? 'main role' : null })))
    .map(s => ({ ...s, items: itemsOf(s.id) }))
    .filter(s => s.items.some(it => it.row));

  const rankName = pl.rank ? meta.rank.names[pl.rank - 1] : null;

  return (
    <>
      <header className="phead">
        <RankBadge player={pl} meta={meta} size={64} />
        <div>
          <h1 className="ptitle grad">{pl.name}</h1>
          {rankName && <p className="rankline">{rankName} · rank {pl.rank} · {pl.tiers.length} raid tier{pl.tiers.length > 1 ? 's' : ''}</p>}
          <p className="chars">
            {pl.chars.map(([n, c]) => (
              <span key={n} className="char" style={{ '--cls': CLASS_COLORS[meta.classes[c]] }}>{n} <small>{meta.classes[c]}</small></span>
            ))}
          </p>
        </div>
      </header>
      <div className="tierstrip" aria-label="Raid tiers">
        {meta.tiers.map((t, i) => (
          <span key={t.id} className={'tier' + (pl.tiers.includes(i) ? ' on' : '')} title={t.name}>{t.short}</span>
        ))}
      </div>
      <FilterBar meta={meta} filter={eff} available={facets} onChange={f => go('player', pl.name, f)}
        note={`Percentiles compare ${pl.name} with every player under the same filters.`} />

      <section className="overview" aria-label="Overview">
        {meta.player.overview.map(({ stat: id, label }) => {
          const stat = data.statById.get(id);
          if (!stat) return null;
          const { row } = result(stat);
          return (
            <div key={id} className="otile">
              <span className="olabel">{label}</span>
              <span className="ovalue">{row ? formatInt(row.value) : '–'}</span>
              <span className="opct">{row && hasPercentile(stat) ? formatPct(row.pct) : ' '}</span>
            </div>
          );
        })}
      </section>

      {sections.map(s => (
        <Section key={s.id} data={data} title={s.title} kicker={s.kicker} items={s.items}
          open={!!openSections[s.id]} onToggle={() => setOpenSections(o => ({ ...o, [s.id]: !o[s.id] }))} />
      ))}
    </>
  );
}
