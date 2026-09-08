/* UI only. Research fields intentionally remain disconnected. */
(() => {
  'use strict';
  document.documentElement.classList.add('enhanced');
  const nav = document.getElementById('chapterNav');
  const toggle = document.getElementById('menuToggle');
  const mobile = window.matchMedia('(max-width: 767px)');
  const links = [...nav.querySelectorAll('a')];
  const sections = links.map(link => document.querySelector(link.hash));
  function menu(open) {
    nav.hidden = mobile.matches && !open;
    toggle.setAttribute('aria-expanded', String(!nav.hidden));
  }
  menu(false);
  mobile.addEventListener('change', () => menu(false));
  toggle.addEventListener('click', () => menu(nav.hidden));
  nav.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mobile.matches) { menu(false); toggle.focus(); }
  });
  links.forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    menu(false);
    const heading = document.querySelector(link.hash).querySelector('h1,h2');
    heading.tabIndex = -1;
    history.pushState(null, '', link.hash);
    document.querySelector(link.hash).scrollIntoView({ block: 'start' });
    heading.focus({ preventScroll: true });
  }));
  function updateActive() {
    const offset = mobile.matches ? 140 : 100;
    let current = sections[0];
    for (const section of sections) if (section.getBoundingClientRect().top <= offset) current = section;
    links.forEach(link => {
      if (link.hash === '#' + current.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  let queued = false;
  window.addEventListener('scroll', () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { updateActive(); queued = false; });
  }, { passive: true });
  window.addEventListener('resize', updateActive);
  updateActive();
  document.getElementById('expandMethods').addEventListener('click', () => {
    document.querySelectorAll('.methods details').forEach(detail => { detail.open = true; });
  });
  document.getElementById('collapseMethods').addEventListener('click', () => {
    document.querySelectorAll('.methods details').forEach(detail => { detail.open = false; });
  });
})();
