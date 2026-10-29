// Entry of the guild chooser (/): the red / blue split, its firefly, and the transition to a guild page
// (styles are linked from the HTML).
import { mountSplit } from './split.js';

const split = mountSplit(document.querySelector('.split'));
const cards = [...document.querySelectorAll('.guilds .guild')];
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
const wait = ms => new Promise(r => setTimeout(r, ms));
// Steps of the transition (ms), matched by styles.css: the card pulses once, the cut slides the other guild
// off the screen while the card glides to the middle (slower, easing out), then the card and the title fade out.
const PULSE = 420, SLIDE = 850, CARD = 1100, FADE = 380;

for (const card of cards) {
  card.addEventListener('click', async e => {
    // New tab, new window, reduced motion: plain link.
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || reduced.matches || !split) return;
    e.preventDefault();
    if (document.body.classList.contains('leaving')) return;
    document.body.classList.add('leaving');
    const other = cards.find(c => c !== card);
    card.classList.add('chosen');
    await wait(PULSE);
    // To the middle of the screen, where it stays while the cut runs on: across when the cards sit side by
    // side (the title stays clear above), down or up when they are stacked (phones).
    const r = card.getBoundingClientRect();
    const sideBySide = Math.abs(r.top - other.getBoundingClientRect().top) < 1;
    card.style.translate = sideBySide
      ? `${window.innerWidth / 2 - (r.left + r.width / 2)}px 0px`
      : `0px ${window.innerHeight / 2 - (r.top + r.height / 2)}px`;
    other.classList.add('dropped');
    await Promise.all([split.slide(card.classList.contains('horde') ? -1 : 1, SLIDE), wait(CARD)]);
    document.body.classList.add('faded');
    await wait(FADE);
    // The guild page fades its content in when it comes from here.
    try { sessionStorage.setItem('clt:enter', '1'); } catch { /* storage blocked: no fade-in, nothing else lost */ }
    window.location.href = card.href;
  });
}

// Back from a guild page, the browser may restore this page as it was left (all one colour): start over.
window.addEventListener('pageshow', e => {
  if (!e.persisted) return;
  document.body.classList.remove('leaving', 'faded');
  for (const c of cards) { c.classList.remove('chosen', 'dropped'); c.style.translate = ''; }
  split?.reset();
});
