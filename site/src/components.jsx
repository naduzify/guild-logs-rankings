import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { playedClasses } from './lib/data.js';
import { CLASS_COLORS, fold, formatValue, parseColor } from './lib/format.js';
import { go, href } from './lib/route.js';
import { explain } from './lib/stats.js';

const WIDE = '(min-width: 720px)';
const GAP = 12;

// "i" button showing how an achievement is calculated. On wide screens the box opens offset
// beside the button (placed in JS, clamped to the viewport); on phones it is a sheet at the
// bottom of the screen (CSS). Hover opens it where hover exists; tap, click or keyboard toggles it.
export function InfoTip({ stat, meta }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const ref = useRef(null);
  const box = useRef(null);
  const id = useId();
  const hover = useRef(typeof window !== 'undefined' && !!window.matchMedia?.('(hover: hover)').matches);

  useEffect(() => {
    if (!open) return;
    const close = e => { if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current?.contains(e.target)) setOpen(false); };
    const shut = () => setOpen(false);
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    window.addEventListener('scroll', shut, { passive: true });
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
      window.removeEventListener('scroll', shut);
    };
  }, [open]);

  useLayoutEffect(() => {
    if (!open || !window.matchMedia(WIDE).matches) { setPos(null); return; }
    const b = ref.current.getBoundingClientRect();
    const { width, height } = box.current.getBoundingClientRect();
    const vw = document.documentElement.clientWidth, vh = window.innerHeight;
    // Down and to the right of the button; flip left / up when it would leave the screen.
    let left = b.right + 6, top = b.top - 6;
    if (left + width > vw - GAP) left = b.left - width - 6;
    if (left < GAP) left = Math.min(Math.max(GAP, b.left - width / 2), vw - width - GAP);
    if (top + height > vh - GAP) top = Math.max(GAP, vh - height - GAP);
    setPos({ left, top });
  }, [open]);

  return (
    <span ref={ref} className={'tip' + (open ? ' open' : '')}
      onMouseEnter={() => hover.current && setOpen(true)} onMouseLeave={() => hover.current && setOpen(false)}>
      <button type="button" className="tipbtn" aria-label={`How ${stat.title} is calculated`} aria-expanded={open}
        aria-describedby={id}
        onClick={e => {
          e.preventDefault(); e.stopPropagation();
          // A mouse click lands while hover has already opened the box: keep it open. Keyboard (detail 0) toggles.
          const keep = hover.current && e.detail > 0;
          setOpen(o => keep || !o);
        }}>i</button>
      <span ref={box} id={id} role="tooltip" className="tipbox"
        style={pos ? { left: pos.left, top: pos.top, right: 'auto', bottom: 'auto' } : undefined}>
        <b>{stat.title}{stat.flip && ` / ${stat.flip}`}</b>
        {explain(stat, meta.settings).map(l => <span key={l}>{l}</span>)}
      </span>
    </span>
  );
}

// A ranked value; Parse Lords adds its best and median parse in small: "71.0 (74.5 | 67.5)", scaled
// totals their actual total: "1.2B (71.1B)".
// `parseColors` paints the average in its Warcraft Logs parse colour, in bold (Parse Lords page).
export function StatValue({ stat, row, parseColors = false }) {
  const main = formatValue(stat, row.value);
  if (stat.agg === 'scaled' && row.extra) {
    return <>{main} <small className="vdetail" title="actual total">({formatValue(stat, row.extra[0])})</small></>;
  }
  if (stat.format !== 'parse' || !row.extra) return main;
  const [best, median] = row.extra;
  return (
    <>
      {parseColors ? <strong style={{ color: parseColor(row.value) }}>{main}</strong> : main}{' '}
      <small className="vdetail" title="best | median">({best.toFixed(1)} | {median.toFixed(1)})</small>
    </>
  );
}

const ROLE_LABELS = { TANK: 'Tank', DPS: 'DPS', HEALER: 'Healer' };
export const roleLabel = r => ROLE_LABELS[r] || r;

export function RankBadge({ player, meta, size = 22 }) {
  if (!player.rank) return null;
  const name = meta.rank.names[player.rank - 1];
  const tiers = player.tiers.length;
  const tip = `Rank ${player.rank} · ${name} · ${tiers} raid tier${tiers > 1 ? 's' : ''}`;
  return (
    <img className="rank" src={`../ranks/${player.rank}.jpg`} width={size} height={size}
      alt={tip} title={tip} loading="lazy" />
  );
}

// Name of a player with his rank badge, linking to his page; one dot per class played under the filters.
export function PlayerName({ data, p, filter, badge }) {
  const pl = data.players[p];
  const classes = playedClasses(data, p, filter);
  return (
    <a className="pname" href={href('player', pl.name, filter)}>
      <RankBadge player={pl} meta={data.meta} size={badge} />
      <span className="pn">{pl.name}</span>
      {classes.length > 0 && (
        <span className="cdots" role="img" title={classes.join(', ')} aria-label={classes.join(', ')}>
          {classes.map(c => <i key={c} style={{ background: CLASS_COLORS[c] }} />)}
        </span>
      )}
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
  const id = useId();
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

  const shown = open && hits.length > 0;
  return (
    <div className="search">
      <input ref={input} type="search" placeholder="Find a player or an alt…" value={q} aria-label="Search players"
        role="combobox" aria-autocomplete="list" aria-expanded={shown} aria-controls={shown ? id + 'hits' : undefined}
        aria-activedescendant={shown ? `${id}hit${sel}` : undefined}
        onChange={e => { setQ(e.target.value); setSel(0); setOpen(true); }}
        onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)} onKeyDown={onKey} />
      {shown && (
        <ul className="hits" id={id + 'hits'} role="listbox" aria-label="Players">
          {hits.map((p, i) => {
            const pl = data.players[p];
            const alts = pl.chars.slice(1).map(c => c[0]);
            return (
              <li key={p} id={`${id}hit${i}`} role="option" aria-selected={i === sel} onMouseDown={() => pick(p)} onMouseEnter={() => setSel(i)}>
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

// "How to read this site" panel (texts in meta.home.intro). Shown on the guild home until dismissed; the
// choice is kept in localStorage per guild (a preference of this browser only, sent nowhere). Storage can
// be blocked (private window): the panel then simply shows on every visit.
const introKey = meta => `clt:${meta.guild.name.toLowerCase()}:intro-dismissed`;
const store = {
  get: k => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* blocked */ } },
};
export const INTRO_EVENT = 'clt:show-intro';
// Footer link: forget the dismissal, then show the panel (the caller goes to the home page).
export function reopenIntro(meta) {
  store.set(introKey(meta), null);
  window.dispatchEvent(new Event(INTRO_EVENT));
}

export function Intro({ meta }) {
  const cfg = meta.home.intro;
  const [open, setOpen] = useState(() => !store.get(introKey(meta)));
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener(INTRO_EVENT, show);
    return () => window.removeEventListener(INTRO_EVENT, show);
  }, []);
  if (!cfg || !open) return null;
  const close = () => { store.set(introKey(meta), '1'); setOpen(false); };
  return (
    <section className="intro" aria-labelledby="intro-title">
      <h2 id="intro-title">{cfg.title}</h2>
      <ul>
        {cfg.items.map(([term, text]) => <li key={term}><strong>{term}</strong> {text}</li>)}
      </ul>
      <button type="button" className="introok" onClick={close}>{cfg.dismiss}</button>
    </section>
  );
}
