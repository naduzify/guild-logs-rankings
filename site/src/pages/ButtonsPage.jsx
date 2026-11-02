import { useEffect, useRef, useState } from 'react';
import { FilterBar, PlayerName } from '../components.jsx';
import { loadButtons } from '../lib/data.js';
import { fold, formatInt } from '../lib/format.js';
import { go, href } from '../lib/route.js';
import { playerButtons } from '../lib/stats.js';
import { restrict } from './PlayerPage.jsx';
import { FindBox } from './StatPage.jsx';

// Every Single Button: everything one player used, under the same filters as their page. Not a ranking.
export default function ButtonsPage({ data, name, filter }) {
  const [cells, setCells] = useState(null);
  const [error, setError] = useState(false);
  const [bossesOnly, setBossesOnly] = useState(false);
  const [find, setFind] = useState('');
  const board = useRef(null);
  useEffect(() => { loadButtons().then(setCells, () => setError(true)); }, []);
  const jump = () => board.current?.querySelector('tr.found')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

  const cfg = data.meta.player.buttons;
  const p = data.byName.get(name);
  if (p == null) return <p className="empty">No player called “{name}”.</p>;
  const eff = restrict(filter, data.facets[p]);
  const rows = cells ? playerButtons(cells, eff, p, bossesOnly) : [];
  const total = rows.reduce((t, r) => t + r.n, 0);
  const k = fold(find.trim());

  return (
    <>
      <header className="stathead">
        <span className="kicker">{cfg.title}</span>
        <h1 className="ptitle"><PlayerName data={data} p={p} filter={filter} badge={30} /></h1>
        <p className="lead">{cfg.description}</p>
        <ul className="method" aria-label="How it is counted">
          <li>{cfg.detail}</li>
        </ul>
      </header>
      <FilterBar meta={data.meta} filter={eff} available={data.facets[p]} onChange={f => go('buttons', name, f)} />
      <button type="button" role="switch" className="htoggle stoggle" aria-checked={bossesOnly} onClick={() => setBossesOnly(b => !b)}>
        <span className="track" aria-hidden="true"><span className="thumb" /></span>
        {cfg.toggle}
      </button>
      {error ? <p className="empty">No ability data for this guild yet.</p>
        : !cells ? <p className="empty">Counting every button…</p>
        : rows.length === 0 ? <p className="empty">Nothing under these filters.</p> : (
        <div className="tablebox">
          <table className="board" ref={board}>
            <thead>
              <tr>
                <th className="n">#</th>
                <th className="l">
                  <span className="thfind">{cfg.column}
                    <FindBox value={find} label={`Highlight an ${cfg.column.toLowerCase()}`} onChange={setFind} onGo={jump} />
                  </span>
                </th>
                <th>{cfg.count}</th>
                <th className="hide-sm">Share</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.label} className={[r.pos === 1 && 'hi', k && fold(r.label).includes(k) && 'found'].filter(Boolean).join(' ') || undefined}>
                  <td className="n">{r.pos}</td>
                  <td className="l bdl">{r.label}<span className="muted bdexp">{r.exps.map(e => data.meta.expansions[e].short).join(', ')}</span></td>
                  <td className="v">{formatInt(r.n)}</td>
                  <td className="v muted hide-sm">{`${(100 * r.n / total).toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted"><a href={href('player', name, filter)}>Back to {name}</a> · {formatInt(total)} {cfg.count.toLowerCase()} in total</p>
    </>
  );
}
