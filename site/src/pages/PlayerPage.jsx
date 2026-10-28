import { FilterBar, PctBar, RankBadge, roleLabel } from '../components.jsx';
import { CLASS_COLORS, formatNumber, formatPct, formatValue } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { computeStat, earnedTitle, hasNumber, hasPercentile, valueIsNumber } from '../lib/stats.js';
import { CATEGORIES } from './StatPage.jsx';

const CATEGORY_ROLE = { tank: 'TANK', healer: 'HEALER', dps: 'DPS' };

// Drop filter values the player never played, so a filter carried over from
// another page cannot empty his card.
function restrict(filter, facets) {
  const out = {};
  for (const k of ['exp', 'cls', 'role']) out[k] = new Set([...filter[k]].filter(v => facets[k].has(v)));
  return out;
}

function StatRow({ data, stat, row, title }) {
  const showP = hasPercentile(stat), showN = hasNumber(stat);
  return (
    <li className={'srow' + (title ? (title.flip ? ' lo' : ' hi') : '')}>
      <div className="sname">
        <a href={href('stat', stat.id)}>{title ? title.name : stat.title}</a>
        <span className="sdesc">{stat.description}</span>
      </div>
      {!row ? <div className="sval muted">Not enough pulls</div> : (
        <div className="sval">
          <span className="big">{row.label ?? (valueIsNumber(stat) ? formatNumber(stat, row.value) : formatValue(stat, row.value))}</span>
          {row.label && <span className="muted">{formatValue(stat, row.value)}</span>}
          {showN && <span className="muted">{formatNumber(stat, row.number)}</span>}
          {showP && <span className="pct"><PctBar pct={row.pct} /> {formatPct(row.pct)}</span>}
        </div>
      )}
    </li>
  );
}

export default function PlayerPage({ data, name, filter }) {
  const p = data.byName.get(name);
  if (p == null) return <p className="empty">No player called “{name}”. Players need 15 reset weeks of raiding to show up.</p>;
  const pl = data.players[p];
  const { meta } = data;
  const facets = data.facets[p];
  const eff = restrict(filter, facets);
  const roleOk = r => facets.role.has(meta.roles.indexOf(r)) && (!eff.role.size || eff.role.has(meta.roles.indexOf(r)));

  const sections = CATEGORIES
    .filter(c => c.id === 'common' || roleOk(CATEGORY_ROLE[c.id]))
    .map(c => ({
      ...c,
      rows: meta.stats.filter(s => s.category === c.id).map(stat => {
        const row = computeStat(stat, data.stats[stat.id], eff, meta.settings).byPlayer.get(p);
        return { stat, row, title: earnedTitle(stat, row, meta.settings) };
      }),
    }));
  const titles = sections.flatMap(s => s.rows).filter(r => r.title);
  const rankName = pl.rank ? meta.rank.names[pl.rank - 1] : null;

  return (
    <>
      <header className="phead">
        <RankBadge player={pl} meta={meta} size={56} />
        <div>
          <h1 className="ptitle">{pl.name}</h1>
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
      {titles.length > 0 && (
        <section className="earned">
          <h2>Titles</h2>
          <div className="badges">
            {titles.map(({ stat, title }) => (
              <a key={stat.id} href={href('stat', stat.id, eff)} className={'badge' + (title.flip ? ' lo' : '')}>{title.name}</a>
            ))}
          </div>
        </section>
      )}
      {sections.map(s => (
        <section key={s.id}>
          <h2 className="cat">{s.id === 'common' ? 'All roles' : s.label}
            {s.id === 'common' && eff.role.size > 0 && <small> · as {[...eff.role].map(r => roleLabel(meta.roles[r])).join(' / ')}</small>}
          </h2>
          <ul className="srows">
            {s.rows.map(r => <StatRow key={r.stat.id} data={data} {...r} />)}
          </ul>
        </section>
      ))}
    </>
  );
}
