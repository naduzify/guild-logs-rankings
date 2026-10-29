// Guild chooser split: the cut between Alliance blue (Fable) and Horde red (NightShift), the white line
// drawn on it, and the firefly path along it.
// The .split layer spans 100vh above the card grid, the grid itself, and 100vh below it, so a point is
// written as [x, y] with y = { pct, vh, px } of that box. Near the cards the cut stays inside the gap
// between them (72px on phones, 96px wide); away from them it takes a few broad bites.

// From 560px: x in px from the centre line, top to bottom.
const WIDE = [
  [8, { pct: 0, vh: 0, px: 0 }],
  [-64, { vh: 1, px: -480 }],
  [58, { vh: 1, px: -220 }],
  [-10, { vh: 1 }],
  [16, { pct: 0.5 }],
  [-12, { pct: 1, vh: -1 }],
  [60, { pct: 1, vh: -1, px: 220 }],
  [-58, { pct: 1, vh: -1, px: 480 }],
  [6, { pct: 1 }],
];
// Phones: x in % of the width, y in px from the middle of the box (the gap between the stacked cards).
const PHONE = [[100, -6], [74, 22], [48, -22], [22, 18], [0, -4]];

const resolveY = (y, h, vh) => (y.pct || 0) * h + (y.vh || 0) * vh + (y.px || 0);

function seam(box, wide) {
  const vh = window.innerHeight;
  return wide
    ? WIDE.map(([x, y]) => [box.width / 2 + x, resolveY(y, box.height, vh)])
    : PHONE.map(([x, y]) => [(x / 100) * box.width, box.height / 2 + y]);
}

// Part of the cut inside [lo, hi] along `axis` (0 = x, 1 = y), cut at the edges.
function clip(points, axis, lo, hi) {
  const lerp = (a, b, v) => { const t = (v - a[axis]) / (b[axis] - a[axis]); return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; };
  const out = [];
  points.forEach((p, i) => {
    const q = points[i + 1];
    if (p[axis] >= lo && p[axis] <= hi) out.push(p);
    if (!q) return;
    for (const edge of [lo, hi]) if ((p[axis] - edge) * (q[axis] - edge) < 0) out.push(lerp(p, q, edge));
  });
  return out.sort((a, b) => a[axis] - b[axis]);
}

const length = pts => pts.slice(1).reduce((n, p, i) => n + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);
const fmt = pts => pts.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(', ');

export function mountSplit(split) {
  if (!split) return;
  const red = split.querySelector('.split-horde');
  const fly = split.querySelector('.firefly');
  // After-images: copies of the firefly that run the same path a few ms behind, fainter and smaller.
  const TRAIL = 30;
  const flies = [fly];
  for (let i = 1; i <= TRAIL; i++) {
    const ghost = fly.cloneNode();
    ghost.classList.add('ghost');
    ghost.style.setProperty('--i', i);
    ghost.style.setProperty('--k', 1 - i / (TRAIL + 1));
    fly.before(ghost);
    flies.push(ghost);
  }
  const line = split.querySelector('.split-line');
  const wideQuery = window.matchMedia('(min-width: 560px)');

  function render() {
    const box = split.getBoundingClientRect();
    const wide = wideQuery.matches;
    const pts = seam(box, wide);
    const { width: w, height: h } = box;
    // Where the screen sits in the layer: the side art (Varian, Garrosh) is laid on the screen, not the layer.
    split.style.setProperty('--screen-top', `${-box.top}px`);
    split.style.setProperty('--screen-h', `${window.innerHeight}px`);
    // Red side (NightShift, second card): right of the cut from 560px, below it on phones.
    red.style.clipPath = wide
      ? `polygon(${w}px 0px, ${fmt(pts)}, ${w}px ${h}px)`
      : `polygon(${w}px ${h}px, 0px ${h}px, ${fmt([...pts].reverse())}, ${w}px ${h}px)`;
    line.setAttribute('viewBox', `0 0 ${w} ${h}`);
    line.firstElementChild.setAttribute('points', pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' '));
    // The firefly only travels the part of the cut on screen, top to bottom and back (left to right on phones).
    // Run at 1000px/s; each run (forth, then back) is 9% of the animation cycle (styles.css), each followed by a pause.
    const path = wide ? clip(pts, 1, -box.top, -box.top + window.innerHeight) : clip(pts, 0, 0, w);
    if (path.length < 2) { flies.forEach(f => f.classList.remove('on')); return; }
    split.style.setProperty('--fly-path', `path('M ${path.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ')}')`);
    split.style.setProperty('--fly-time', `${Math.max(2, length(path) / 1000 / 0.09).toFixed(2)}s`);
    flies.forEach(f => f.classList.add('on'));
  }

  let queued = false;
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; render(); }); } };
  render();
  window.addEventListener('resize', schedule);
  window.addEventListener('scroll', schedule, { passive: true });
  wideQuery.addEventListener('change', schedule);
}
