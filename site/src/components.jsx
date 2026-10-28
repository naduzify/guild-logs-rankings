import { useEffect, useMemo, useRef, useState } from 'react';
import { CLASS_COLORS, fold } from './lib/format.js';
import { go, href } from './lib/route.js';
import { explain } from './lib/stats.js';

// "i" button showing how an achievement is calculated. Hover on desktop; tap on touch screens,
// where it opens as a sheet at the bottom of the screen (CSS), and closes on any tap outside.
export function InfoTip({ stat, meta }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const close = e => { if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close); };
  }, [open]);
  return (
    <span ref={ref} className={'tip' + (open ? ' open' : '')}>
      <button type="button" className="tipbtn" aria-label={`How ${stat.title} is calculated`} aria-expanded={open}
        onClick={e => { e.preventDefault(); e.stopPropagation(); setOpen(o => !o); }}>i</button>
      <span role="tooltip" className="tipbox">
        <b>{stat.title}{stat.flip && ` / ${stat.flip}`}</b>
        {explain(stat, meta.settings).map(l => <span key={l}>{l}</span>)}
      </span>
    </span>
  );
}

const ROLE_LABELS = { TANK: 'Tank', DPS: 'DPS', HEALER: 'Healer' };
export const roleLabel = r => ROLE_LABELS[r] || r;

export function RankBadge({ player, meta, size = 20 }) {
  if (!player.rank) return null;
  const name = meta.rank.names[player.rank - 1];
  const tiers = player.tiers.length;
  const tip = `Rank ${player.rank} · ${name} · ${tiers} raid tier${tiers > 1 ? 's' : ''}`;
  return (
    <img className="rank" src={`${import.meta.env.BASE_URL}ranks/${player.rank}.jpg`} width={size} height={size}
      alt={tip} title={tip} loading="lazy" />
  );
}

// Name of a player with his rank badge, linking to his page; the main class colours the name.
export function PlayerName({ data, p, filter }) {
  const pl = data.players[p];
  const cls = data.meta.classes[pl.chars[0][1]];
  return (
    <a className="pname" href={href('player', pl.name, filter)}>
      <RankBadge player={pl} meta={data.meta} />
      <span style={{ '--cls': CLASS_COLORS[cls] }}>{pl.name}</span>
    </a>
  );
}

function Chip({ on, onClick, children, dot }) {
  return (
    <button type="button" className="chip" aria-pressed={on} onClick={onClick}>
      {dot && <i className="dot" style={{ background: dot }} />}
      {children}
    </button>
  );
}

// Expansion / role / class chips. `available` (a player's facets) hides values he never played.
export function FilterBar({ meta, filter, onChange, available, note }) {
  const toggle = (k, v) => {
    const next = { ...filter, [k]: new Set(filter[k]) };
    next[k].has(v) ? next[k].delete(v) : next[k].add(v);
    onChange(next);
  };
  const [open, setOpen] = useState(false);
  const show = (k, i) => !available || available[k].has(i);
  const any = filter.exp.size + filter.cls.size + filter.role.size;
  return (
    <div className={'filters' + (open ? ' open' : '')}>
      <button type="button" className="ftoggle" aria-expanded={open} onClick={() => setOpen(o => !o)}>
        <span>Filters {any > 0 && <span className="count">· {any} active</span>}</span>
        <span className="chev" aria-hidden="true">▾</span>
      </button>
      <div className="fbody">
      <div className="grp"><b>Expansion</b>
        {meta.expansions.map((x, i) => show('exp', i) &&
          <Chip key={x.id} on={filter.exp.has(i)} onClick={() => toggle('exp', i)}>{x.short}</Chip>)}
      </div>
      <div className="grp"><b>Role</b>
        {meta.roles.map((r, i) => show('role', i) &&
          <Chip key={r} on={filter.role.has(i)} onClick={() => toggle('role', i)}>{roleLabel(r)}</Chip>)}
      </div>
      <div className="grp"><b>Class</b>
        {meta.classes.map((c, i) => show('cls', i) &&
          <Chip key={c} on={filter.cls.has(i)} dot={CLASS_COLORS[c]} onClick={() => toggle('cls', i)}>{c}</Chip>)}
      </div>
      {any ? <button type="button" className="btn" onClick={() => onChange({ exp: new Set(), cls: new Set(), role: new Set() })}>Reset filters</button> : null}
      {note && <span className="fnote">{note}</span>}
      </div>
    </div>
  );
}

// Player search: matches mains and their alts, accents ignored. Enter opens the first match.
export function Search({ data, filter }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState(0);
  const input = useRef(null);
  const index = useMemo(() => data.players.map((pl, p) => ({ p, keys: pl.chars.map(([n]) => fold(n)) })), [data]);

  const hits = useMemo(() => {
    const k = fold(q.trim());
    if (!k) return [];
    const starts = [], contains = [];
    for (const it of index) {
      if (it.keys.some(n => n.startsWith(k))) starts.push(it.p);
      else if (it.keys.some(n => n.includes(k))) contains.push(it.p);
    }
    return [...starts, ...contains].slice(0, 8);
  }, [q, index]);

  const pick = p => {
    setQ(''); setOpen(false); input.current?.blur();
    go('player', data.players[p].name, filter);
  };
  const onKey = e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel(s => Math.min(s + 1, hits.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(s => Math.max(s - 1, 0)); }
    else if (e.key === 'Enter' && hits.length) pick(hits[sel]);
    else if (e.key === 'Escape') setOpen(false);
  };

  return (
    <div className="search">
      <input ref={input} type="search" placeholder="Find a player or an alt…" value={q} aria-label="Search players"
        onChange={e => { setQ(e.target.value); setSel(0); setOpen(true); }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} onKeyDown={onKey} />
      {open && hits.length > 0 && (
        <ul className="hits" role="listbox">
          {hits.map((p, i) => {
            const pl = data.players[p];
            const alts = pl.chars.slice(1).map(c => c[0]);
            return (
              <li key={p} role="option" aria-selected={i === sel} onMouseDown={() => pick(p)} onMouseEnter={() => setSel(i)}>
                <RankBadge player={pl} meta={data.meta} />
                <span className="hn">{pl.name}</span>
                {alts.length > 0 && <span className="ha">{alts.join(', ')}</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function PctBar({ pct }) {
  return <span className="pbar" aria-hidden="true"><span style={{ width: `${Math.max(2, pct)}%` }} /></span>;
}
