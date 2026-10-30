import { useEffect, useState } from 'react';

// Hash routes: #/ , #/stats , #/stat/<id> , #/stat/<id>/<player> (his own breakdown), #/record/<kind> ,
// #/player/<name>, with filters in the query
// (?exp=0,2&cls=5&role=0) so a filtered page can be shared as a link.

const SETS = ['exp', 'cls', 'role'];

// A truncated shared link ("%E0") would throw and blank the page: keep the raw text instead.
function safeDecode(s) {
  try { return decodeURIComponent(s); } catch { return s; }
}

export function parseHash(hash = window.location.hash) {
  const [path, query = ''] = hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query);
  const filter = {};
  for (const k of SETS) {
    const raw = params.get(k);
    filter[k] = new Set(raw ? raw.split(',').map(Number).filter(Number.isInteger) : []);
  }
  const parts = (path || '/').split('/').filter(Boolean).map(safeDecode);
  return { page: parts[0] || 'home', arg: parts[1] ?? null, arg2: parts[2] ?? null, filter };
}

// arg may be a list of path parts: href('stat', [id, player]).
export function href(page, arg, filter) {
  const args = arg == null ? [] : [].concat(arg);
  let path = page === 'home' ? '/' : `/${page}${args.map(a => '/' + encodeURIComponent(a)).join('')}`;
  const q = filter ? SETS.filter(k => filter[k].size).map(k => `${k}=${[...filter[k]].sort((a, b) => a - b).join(',')}`) : [];
  return '#' + path + (q.length ? '?' + q.join('&') : '');
}

export function useRoute() {
  const [route, setRoute] = useState(() => parseHash());
  useEffect(() => {
    const on = () => { setRoute(parseHash()); };
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return route;
}

export function go(page, arg, filter) {
  window.location.hash = href(page, arg, filter);
}
