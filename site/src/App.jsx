import { useEffect, useState } from 'react';
import { Search } from './components.jsx';
import { loadData } from './lib/data.js';
import { href, useRoute } from './lib/route.js';
import Home from './pages/Home.jsx';
import PlayerPage from './pages/PlayerPage.jsx';
import StatPage, { StatsIndex } from './pages/StatPage.jsx';

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const route = useRoute();

  useEffect(() => { loadData().then(setData, e => setError(e.message)); }, []);
  useEffect(() => { window.scrollTo(0, 0); }, [route.page, route.arg]);

  if (error) return <main className="wrap"><p className="empty">Could not load the data ({error}). Run <code>npm run mock</code> to generate test data.</p></main>;
  if (!data) return <main className="wrap"><p className="empty">Loading seven years of logs…</p></main>;

  const { filter } = route;
  let page;
  if (route.page === 'player') page = <PlayerPage data={data} name={route.arg} filter={filter} />;
  else if (route.page === 'stat') page = <StatPage data={data} id={route.arg} filter={filter} />;
  else if (route.page === 'stats') page = <StatsIndex data={data} filter={filter} />;
  else page = <Home data={data} filter={filter} />;

  return (
    <>
      {data.meta.mock && <div className="mockbar">Mock data: every number on this page is random.</div>}
      <header className="top">
        <div className="wrap topin">
          <a className="brand" href={href('home', null, filter)}>{data.meta.guild.name}<span>Timewalking</span></a>
          <nav><a href={href('stats', null, filter)}>Titles</a></nav>
          <Search data={data} filter={filter} />
        </div>
      </header>
      <main className="wrap">{page}</main>
      <footer className="wrap foot">
        Built from Warcraft Logs reports of guild {data.meta.guild.name}, {data.meta.guild.server}. Scores are base 100 against the raid of the night.
      </footer>
    </>
  );
}
