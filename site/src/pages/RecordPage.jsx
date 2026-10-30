import { FilterBar } from '../components.jsx';
import { formatInt } from '../lib/format.js';
import { duration, rankBosses, RECORDS } from '../lib/records.js';
import { go, href } from '../lib/route.js';

// A guild record (Loot Pinata, Guild Nemesis…) in full: one row per boss, no players. Only the expansion
// filter applies; role and class mean nothing for a boss.
export default function RecordPage({ data, kind, filter }) {
  const { meta } = data;
  const rec = (meta.home.records || []).find(r => r.kind === kind);
  const rule = rec && RECORDS[rec.kind];
  if (!rule) return <p className="empty">Unknown guild record. <a href={href('home', null, filter)}>Back to the guild page</a>.</p>;
  const rows = rankBosses(meta, rec, filter);
  const cols = [[3, 'Kills', formatInt], [4, 'Wipes', formatInt], [5, 'Fastest', duration], [6, 'Slowest', duration]];
  const others = cols.filter(([c]) => c !== rule.col);
  const main = cols.find(([c]) => c === rule.col);

  return (
    <>
      <header className="stathead">
        <span className="kicker">Guild record</span>
        <h1 className="ptitle">{rec.title}</h1>
        <p className="lead">{rec.description}</p>
        <ul className="method" aria-label="How it is calculated">
          <li>One row per boss (heroic apart), over the guild's eligible pulls; kill times from the start to the end of the pull.</li>
          {rec.exclude?.length > 0 && <li>Left out: {rec.exclude.join(', ')}.</li>}
        </ul>
      </header>
      <FilterBar meta={meta} filter={filter} groups={['exp']} onChange={f => go('record', kind, f)} />
      {rows.length === 0 ? <p className="empty">No boss with these filters.</p> : (
        <div className="tablebox">
          <table className="board">
            <thead>
              <tr>
                <th className="n">#</th>
                <th className="l">Boss</th>
                <th>{rule.label}</th>
                {others.map(([c, label]) => <th key={c} className="hide-sm">{label}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ pos, row }) => (
                <tr key={`${row[0]}-${row[1]}-${row[2]}`}>
                  <td className="n">{pos}</td>
                  <td className="l">{row[1]}{row[2] ? ' (H)' : ''} <span className="muted">{meta.expansions[row[0]].short}</span></td>
                  <td className="v">{main[2](row[main[0]])}</td>
                  {others.map(([c, , fmt]) => <td key={c} className="v muted hide-sm">{row[c] ? fmt(row[c]) : '–'}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
