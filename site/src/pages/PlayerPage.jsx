import { useState } from 'react';
import { FilterBar, InfoTip, PctBar, RankBadge, StatValue, roleLabel } from '../components.jsx';
import { BASE100, CLASS_COLORS, formatBig, formatInt, formatNumber, formatPct, formatValue, isBase100, rankBand } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat, earnedTitle, hasNumber, hasPercentile, isRankable, shareTotal, valueIsNumber } from '../lib/stats.js';

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
  const value = valueIsNumber(stat) ? formatNumber(stat, row.value) : <StatValue stat={stat} row={row} />;
  return {
    label: flipSide ? stat.flip : stat.title,
    earned: earnedTitle(stat, row, settings),
    flipSide,
    // `top` shows the winning label (a boss, a spell), `max` the score with its pull underneath.
    main: stat.agg === 'top' ? row.label : value,
    sub: stat.agg === 'top' ? formatValue(stat, row.value) + (stat.top_by === 'share' ? shareTotal(stat, row) : isBase100(stat) ? ` ${BASE100}` : stat.unit ? ` ${stat.unit}` : '') : row.label,
    // The main value is a base 100 score: say so, so it is not read as a raw amount.
    base100: stat.agg !== 'top' && !valueIsNumber(stat) && isBase100(stat),
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
      {v.base100 && <div className="sunit">{BASE100}</div>}
      {v.sub && <div className="ssub">{v.sub}</div>}
      {big && <p className="sdesc">{v.desc}</p>}
      <footer className="sfoot">
        {v.pct != null && <span className="pct stacked"><span className={v.pct >= 75 ? 'ptext glow' : 'ptext'}>{formatPct(v.pct)}</span><PctBar pct={v.pct} /></span>}
        {big && v.pos && <span>{v.pos}</span>}
        {big && v.number && <span>{v.number}</span>}
      </footer>
    </article>
  );
}

// Ornamented heading, as Guild Legends on the home page; nothing when the config has no text.
function SectionTitle({ text }) {
  return text ? <h2 className="ornament ptitlesec"><span>{text}</span></h2> : null;
}

function Section({ data, id, title, kicker, items, open, onToggle }) {
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
    <section className="psec" aria-label={kicker ? `${title}, ${kicker}` : title}>
      <SectionTitle text={cfg.section_titles?.[id]} />
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

// "Your best friend(s)": the ranked player(s) he shared the most raid nights with (players.json friends),
// every name when several are tied. Independent of the filters.
function BestFriend({ data, player, filter }) {
  const f = player.friends;
  const cfg = data.meta.player.best_friend;
  if (!f || !f.names.length || !cfg) return null;
  const plural = f.names.length > 1;
  return (
    <section className="bestfriend" aria-label={plural ? cfg.title_plural : cfg.title}>
      <span className="bflabel">{plural ? cfg.title_plural : cfg.title}</span>
      <p className="bfnames">
        {f.names.map((n, i) => (
          <span key={n}>
            {i > 0 && ', '}
            {data.byName.has(n) ? <a href={href('player', n, filter)}>{n}</a> : n}
          </span>
        ))}
      </p>
      <span className="bfdetail">{cfg.detail.replace('{nights}', formatInt(f.nights))}</span>
    </section>
  );
}

export default function PlayerPage({ data, name, filter }) {
  const [openSections, setOpenSections] = useState({});
  const [toggles, setToggles] = useState({});
  const p = data.byName.get(name);
  if (p == null) return <p className="empty">No player called “{name}”. Players need 15 reset weeks of raiding to show up.</p>;
  const pl = data.players[p];
  const { meta } = data;
  const facets = data.facets[p];
  const eff = restrict(filter, facets);
  const overviewIds = new Set(meta.player.overview.map(o => o.stat));
  const titles = meta.player.section_titles || {};

  const result = stat => {
    const { byPlayer, ranked } = computeStat(stat, data.stats[stat.id] || [], eff, meta.settings, data.roleOk);
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
            {/* Every character; minor rerolls (few reset weeks) without their class. */}
            {pl.chars.map(ch => (data.isMain(ch)
              ? <span key={ch[0]} className="char" style={{ '--cls': CLASS_COLORS[meta.classes[ch[1]]] }}>{ch[0]} <small>{meta.classes[ch[1]]}</small></span>
              : <span key={ch[0]} className="char minor" title={ch[2] != null ? `${ch[2]} reset week${ch[2] > 1 ? 's' : ''}` : undefined}>{ch[0]}</span>
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

      {/* Under the filters, above the overview; it does not depend on the filters. */}
      <BestFriend data={data} player={pl} filter={filter} />

      {/* Career totals, with the guild rank in a corner band coloured like a parse. */}
      <SectionTitle text={titles.highlights} />
      <section className="highlights" aria-label={titles.highlights || 'Career totals'}>
        {(meta.player.highlights || []).map(({ stat: baseId, label: baseLabel, toggle }) => {
          // A toggle ("Bosses only") switches the card to another stat.
          const on = !!(toggle && toggles[baseId] && data.statById.get(toggle.stat));
          const id = on ? toggle.stat : baseId;
          const label = on ? toggle.title || baseLabel : baseLabel;
          const stat = data.statById.get(id);
          if (!stat) return null;
          const { row, total } = result(stat);
          const band = row && rankBand(row);
          return (
            <article key={baseId} className="scard big hcard" style={band ? { '--band': band.bg, ...(band.fg && { '--band-text': band.fg }) } : undefined}>
              {row && <span className="ribbonwrap"><span className="ribbon rankband">#{row.pos}</span></span>}
              <header><a className="slabel" href={href('stat', stat.id)}>{label}</a><InfoTip stat={stat} meta={meta} /></header>
              <div className="svalue grad">{row ? formatBig(row.value) : '–'}</div>
              {row?.extra && <div className="hactual">{stat.scale_note && <span className="sunit">{stat.scale_note}</span>} <small>({formatBig(row.extra[0])} actual)</small></div>}
              {row && <footer className="sfoot">#{row.pos} of {total} in the guild</footer>}
              {toggle && data.statById.get(toggle.stat) && (
                <button type="button" role="switch" className="htoggle" aria-checked={on}
                  onClick={() => setToggles(t => ({ ...t, [baseId]: !t[baseId] }))}>
                  <span className="track" aria-hidden="true"><span className="thumb" /></span>
                  {toggle.label}
                </button>
              )}
            </article>
          );
        })}
      </section>

      <section className="overview" aria-label="Overview">
        {meta.player.overview.map(({ stat: id, label, percentile }) => {
          const stat = data.statById.get(id);
          if (!stat) return null;
          const { row } = result(stat);
          return (
            <article key={id} className="scard big otile">
              <header><a className="slabel" href={href('stat', stat.id)}>{label}</a><InfoTip stat={stat} meta={meta} /></header>
              <div className="svalue">{row ? formatInt(row.value) : '–'}</div>
              {row && (percentile ?? hasPercentile(stat)) && (
                <footer className="sfoot"><span className="pct stacked"><span className={row.pct >= 75 ? 'ptext glow' : 'ptext'}>{formatPct(row.pct)}</span><PctBar pct={row.pct} /></span></footer>
              )}
            </article>
          );
        })}
      </section>

      {sections.map(s => (
        <Section key={s.id} data={data} id={s.id} title={s.title} kicker={s.kicker} items={s.items}
          open={!!openSections[s.id]} onToggle={() => setOpenSections(o => ({ ...o, [s.id]: !o[s.id] }))} />
      ))}
    </>
  );
}
