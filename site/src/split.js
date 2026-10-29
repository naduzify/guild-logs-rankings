// Guild chooser split: the cut between Alliance blue (Fable) and Horde red (NightShift), the white line
// drawn on it, the firefly path along it, and the slide of the cut when a guild is picked.
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

// `shift` slides the whole cut (px, along x from 560px, along y on phones): the page transition (slide()).
function seam(box, wide, shift = 0) {
  const vh = window.innerHeight;
  return wide
    ? WIDE.map(([x, y]) => [box.width / 2 + x + shift, resolveY(y, box.height, vh)])
    : PHONE.map(([x, y]) => [(x / 100) * box.width, box.height / 2 + y + shift]);
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

// More points along the cut (one every `step` px), so it can bend smoothly without losing its teeth.
function densify(pts, step = 16) {
  const out = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    const [a, b] = [pts[i - 1], pts[i]];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let k = 1; k <= n; k++) out.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
  }
  return out;
}

const length = pts => pts.slice(1).reduce((n, p, i) => n + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);
const fmt = pts => pts.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(', ');

export function mountSplit(split) {
  if (!split) return null;
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
  // Slide of the cut: 0 at rest; -1 hands the screen to the red side (NightShift), +1 to the blue side (Fable).
  // `bend` (same sign, 0 at both ends of the slide, full in the middle) pulls the middle of the cut ahead of
  // its ends, as if dragged by the centre of the screen.
  let slid = 0, bend = 0;

  // Shift (px) that pushes the cut just past the screen edge, toward the losing side.
  function reach(box, wide, dir) {
    const margin = 90; // the cut's broadest bite (64px) plus the line's glow
    if (wide) return dir * (box.width / 2 + margin);
    const top = -box.top, mid = box.height / 2;
    return dir > 0 ? top + window.innerHeight - mid + margin : top - mid - margin;
  }

  function render() {
    const box = split.getBoundingClientRect();
    const wide = wideQuery.matches;
    const { width: w, height: h } = box;
    let pts = seam(box, wide, slid && reach(box, wide, Math.sign(slid)) * Math.abs(slid));
    if (bend) {
      // A bell around the middle of the screen (along the cut), up to a fifth of the screen ahead.
      const vh = window.innerHeight;
      const [mid, spread, lead] = wide ? [-box.top + vh / 2, vh * 0.4, w * 0.2] : [w / 2, w * 0.4, vh * 0.22];
      pts = densify(pts).map(([x, y]) => {
        const d = lead * bend * Math.exp(-((((wide ? y : x) - mid) / spread) ** 2));
        return wide ? [x + d, y] : [x, y + d];
      });
    }
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

  return {
    // Slides the cut off the screen toward the losing side (dir: +1 Fable wins, -1 NightShift wins), easing
    // in and out over `ms`; resolves when the winning colour fills the screen. The side art does not move:
    // only the clip of the red layer and the line follow the cut.
    slide(dir, ms) {
      split.classList.add('sliding');
      return new Promise(done => {
        const start = performance.now();
        const step = now => {
          const t = Math.min(1, (now - start) / ms);
          slid = dir * (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
          bend = dir * Math.sin(Math.PI * t);
          render();
          if (t < 1) requestAnimationFrame(step); else done();
        };
        requestAnimationFrame(step);
      });
    },
    // Back to rest (page restored from the back-forward cache after a transition).
    reset() { slid = 0; bend = 0; split.classList.remove('sliding'); render(); },
  };
}
