import { useEffect, useRef, useState } from 'react';
import { reopenIntro, Search } from './components.jsx';
import { loadData } from './lib/data.js';
import { go, href, useRoute } from './lib/route.js';
import Home from './pages/Home.jsx';
import PlayerPage from './pages/PlayerPage.jsx';
import StatPage, { StatsIndex } from './pages/StatPage.jsx';

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const route = useRoute();

  useEffect(() => { loadData().then(setData, e => setError(e.message)); }, []);
  const main = useRef(null);
  const firstPage = useRef(true);
  useEffect(() => { window.scrollTo(0, 0); }, [route.page, route.arg]);

  // Hash routing changes nothing a screen reader notices: name the tab after the page and, on a
  // page change (not the first load), move the focus to its heading.
  useEffect(() => {
    if (!data) return;
    const { meta } = data;
    const stat = route.page === 'stat' && data.statById.get(route.arg);
    const part = route.page === 'player' ? route.arg : stat ? stat.title : route.page === 'stats' ? 'Achievements' : null;
    document.title = (part ? part + ' · ' : '') + `${meta.guild.name} Timewalking`;
    if (firstPage.current) { firstPage.current = false; return; }
    const target = main.current?.querySelector('h1') || main.current;
    if (target) { target.tabIndex = -1; target.focus({ preventScroll: true }); }
  }, [data, route.page, route.arg]);

  if (error) return <main className="wrap"><p className="empty">Could not load the data ({error}). Run <code>npm run mock</code> to generate test data.</p></main>;
  if (!data) return <main className="wrap"><p className="empty">Loading seven years of logs…</p></main>;

  const { filter } = route;
  let page;
  if (route.page === 'player') page = <PlayerPage key={route.arg} data={data} name={route.arg} filter={filter} />;
  else if (route.page === 'stat') page = <StatPage data={data} id={route.arg} filter={filter} />;
  else if (route.page === 'stats') page = <StatsIndex data={data} filter={filter} />;
  else page = <Home data={data} filter={filter} />;

  return (
    <>
      {data.meta.mock && <div className="mockbar">Mock data: every number on this page is random.</div>}
      <button type="button" className="skip" onClick={() => main.current?.focus()}>Skip to content</button>
      <header className="top">
        <div className="wrap topin">
          <a className="brand" href="../">Classic Logs<span>Timewalking</span></a>
          <nav><a href={href('home', null, filter)}>{data.meta.guild.name}</a><a href={href('stats', null, filter)}>Achievements</a></nav>
          <Search data={data} filter={filter} />
        </div>
      </header>
      <main className="wrap" ref={main} tabIndex={-1}>{page}</main>
      <footer className="wrap foot">
        Built from Warcraft Logs reports of guild {data.meta.guild.name}, {data.meta.guild.server}. Scores are base 100 against the raid of the night.
        {data.meta.home.intro && (
          <button type="button" className="linkbtn" onClick={() => { reopenIntro(data.meta); go('home', null, filter); window.scrollTo(0, 0); }}>
            {data.meta.home.intro.reopen}
          </button>
        )}
      </footer>
    </>
  );
}
