// Decorative enhancements only. Ordering, consent, media, and sessions remain in app.js.
const root = document.documentElement;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const calm = () => reducedMotion.matches || root.dataset.calmMotion === 'true';

// Horizontal pointer movement turns the photograph around its fixed center.
const editorialHero = document.querySelector('.hero');
const desktopMotion = window.matchMedia('(min-width: 701px) and (hover: hover) and (pointer: fine)');
let heroFrame = 0;
function resetHeroMotion() {
  cancelAnimationFrame(heroFrame);
  editorialHero?.style.removeProperty('--scene-angle');
  if (editorialHero) delete editorialHero.dataset.pointerRotation;
}
editorialHero?.addEventListener('pointermove', event => {
  if (calm() || !desktopMotion.matches || event.pointerType === 'touch') return;
  cancelAnimationFrame(heroFrame);
  heroFrame = requestAnimationFrame(() => {
    const rect = editorialHero.getBoundingClientRect();
    const x = Math.max(-.5, Math.min(.5, (event.clientX - rect.left) / rect.width - .5));
    editorialHero.dataset.pointerRotation = 'true';
    editorialHero.style.setProperty('--scene-angle', `${x * 20}deg`);
  });
});
editorialHero?.addEventListener('pointerleave', resetHeroMotion);
editorialHero?.addEventListener('pointercancel', resetHeroMotion);
reducedMotion.addEventListener('change', resetHeroMotion);
desktopMotion.addEventListener('change', resetHeroMotion);
new MutationObserver(resetHeroMotion).observe(root, { attributes: true, attributeFilter: ['data-calm-motion'] });
let headerFrame = 0;
function refreshHeaderSurface() {
  if (headerFrame) return;
  headerFrame = requestAnimationFrame(() => {
    headerFrame = 0;
    document.body.dataset.headerScrolled = String((editorialHero?.getBoundingClientRect().bottom || 0) < 140);
  });
}
addEventListener('scroll', refreshHeaderSurface, { passive: true });
addEventListener('resize', refreshHeaderSurface);
refreshHeaderSurface();
// Observe authoritative renders; this layer never submits an ordering action.
const count = document.querySelector('[data-cart-count]');
const total = document.querySelector('[data-cart-total]');
let previousCount = count?.textContent;
function syncCartFeedback() {
  const value = count?.textContent?.trim() || '0';
  if (value !== previousCount && count && !calm()) {
    count.classList.remove('cart-pop');
    void count.offsetWidth;
    count.classList.add('cart-pop');
  }
  previousCount = value;
}
const cartObserver = new MutationObserver(syncCartFeedback);
if (count) cartObserver.observe(count, { childList: true, characterData: true, subtree: true });
if (total) cartObserver.observe(total, { childList: true, characterData: true, subtree: true });
syncCartFeedback();

if ('IntersectionObserver' in window) {
  const links = [...document.querySelectorAll('.main-nav a')];
  const navigation = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      links.forEach(link => {
        const current = link.hash === `#${entry.target.id}`;
        link.classList.toggle('is-current', current);
        if (current) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }
  }, { rootMargin: '-15% 0px -55% 0px', threshold: 0 });
  links.forEach(link => { const target = document.querySelector(link.hash); if (target) navigation.observe(target); });
}


// Reveal static copy below the campaign as it enters the reading area.
// Live status/transcript text and interactive controls are deliberately excluded.
const textTargets = [...document.querySelectorAll(
  '.spotlight-intro .eyebrow, .spotlight-intro h2, .spotlight-intro > p, ' +
  '.feature-band h2, .feature-band p, .section-heading > *, ' +
  '.ar-copy > .eyebrow, .ar-copy h2, .ar-copy > p:not([aria-live]), ' +
  '.access-deck .eyebrow, .access-deck h2, .assistant-copy > p, .assistant-copy h2, ' +
  '.site-footer p, .footer-wordmark'
)];
if ('IntersectionObserver' in window && !calm()) {
  const textEntrances = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const text = entry.target;
      text.dataset.textReveal = 'shown';
      if (!calm()) {
        text.classList.add('text-reveal-in');
        text.addEventListener('animationend', () => text.classList.remove('text-reveal-in'), { once: true });
      }
      textEntrances.unobserve(text);
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: .12 });
  textTargets.forEach((text, index) => {
    text.style.setProperty('--text-delay', `${index % 3 * 65}ms`);
    text.dataset.textReveal = 'pending';
    textEntrances.observe(text);
  });
  const revealAllText = () => {
    if (!calm()) return;
    textEntrances.disconnect();
    textTargets.forEach(text => {
      text.dataset.textReveal = 'shown';
      text.classList.remove('text-reveal-in');
    });
  };
  reducedMotion.addEventListener('change', revealAllText);
  new MutationObserver(revealAllText).observe(root, {
    attributes: true, attributeFilter: ['data-calm-motion'],
  });
}

// Respect a requested deep link after the application's first authoritative render.
if (location.hash) {
  const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (target) {
    const applyInitialAnchor = () => {
      if (!root.dataset.foodeaseRevision) return false;
      requestAnimationFrame(() => requestAnimationFrame(() => target.scrollIntoView({ block: 'start', behavior: 'instant' })));
      return true;
    };
    if (!applyInitialAnchor()) {
      const firstRender = new MutationObserver(() => { if (applyInitialAnchor()) firstRender.disconnect(); });
      firstRender.observe(root, { attributes: true, attributeFilter: ['data-foodease-revision'] });
    }
  }
}

if ('IntersectionObserver' in window) {
  const cardsEntering = new IntersectionObserver(entries => {
    entries.filter(entry => entry.isIntersecting).forEach((entry, i) => {
      if (!calm()) {
        entry.target.style.animationDelay = `${Math.min(i, 3) * 55}ms`;
        entry.target.classList.add('card-enter');
        entry.target.addEventListener('animationend', () => {
          entry.target.classList.remove('card-enter'); entry.target.style.removeProperty('animation-delay');
        }, { once: true });
      }
      cardsEntering.unobserve(entry.target);
    });
  }, { threshold: .08 });
  document.querySelectorAll('[data-menu-item]').forEach(card => cardsEntering.observe(card));
}

// Acknowledge Add only after the authoritative cart count increases.
let pendingAdd = null;
document.addEventListener('click', event => {
  const button = event.target.closest('[data-add-item]');
  if (button && !button.disabled) pendingAdd = { button, at: performance.now() };
}, { capture: true });
let feedbackCount = Number(count?.textContent || 0);
const addFeedback = new MutationObserver(() => {
  const next = Number(count?.textContent || 0);
  if (next > feedbackCount && pendingAdd && performance.now() - pendingAdd.at < 3000) {
    const button = pendingAdd.button;
    button.classList.add('is-added');
    setTimeout(() => button.classList.remove('is-added'), 1400);
  }
  pendingAdd = null;
  feedbackCount = next;
});
if (count) addFeedback.observe(count, { childList: true, characterData: true, subtree: true });

// The existing cart trigger moves with the menu navigation, retaining its listeners and name.
const menu = document.querySelector('#popular');
const header = document.querySelector('.site-header');
const categoryNav = document.querySelector('[data-menu-category-nav]');
const categoryLinks = [...document.querySelectorAll('[data-category-jump]')];
const categoryGroups = [...document.querySelectorAll('[data-menu-category-group]')];
const menuCart = document.querySelector('.cart-button');
const cartHome = document.createComment('navbar cart home');
menuCart?.before(cartHome);
let categoryFrame = 0;
let currentCategory = '';
function refreshMenuNavigation() {
  if (categoryFrame) return;
  categoryFrame = requestAnimationFrame(() => {
    categoryFrame = 0;
    if (!menu || !header || !categoryNav) return;
    const bounds = menu.getBoundingClientRect();
    const inMenu = bounds.top <= (innerWidth <= 700 ? 150 : 112) && bounds.bottom > 100;
    document.body.dataset.menuNavigation = String(inMenu);
    categoryNav.hidden = !inMenu;
    if (menuCart && menuCart.classList.contains('is-floating-cart') !== inMenu) {
      const focused = document.activeElement === menuCart;
      menuCart.classList.toggle('is-floating-cart', inMenu);
      if (inMenu) document.body.append(menuCart);
      else cartHome.after(menuCart);
      if (focused) menuCart.focus({ preventScroll: true });
    }
    root.style.setProperty('--header-clearance', `${header.offsetHeight + 20}px`);
    if (!inMenu) return;
    const active = categoryGroups.find(group => !group.hidden && group.getBoundingClientRect().bottom > header.offsetHeight + 32);
    const id = active?.dataset.menuCategoryGroup || '';
    if (currentCategory === id) return;
    currentCategory = id;
    categoryLinks.forEach(link => {
      const selected = link.dataset.categoryJump === id;
      link.classList.toggle('is-current', selected);
      if (selected) {
        link.setAttribute('aria-current', 'location');
        categoryNav.scrollTo({ left: link.offsetLeft - categoryNav.clientWidth / 2 + link.offsetWidth / 2, behavior: calm() ? 'instant' : 'smooth' });
      } else link.removeAttribute('aria-current');
    });
  });
}
addEventListener('scroll', refreshMenuNavigation, { passive: true });
addEventListener('resize', refreshMenuNavigation);
if (header) new ResizeObserver(refreshMenuNavigation).observe(header);
new MutationObserver(refreshMenuNavigation).observe(root, { attributes: true, attributeFilter: ['data-foodease-revision'] });
refreshMenuNavigation();

// A small original-image preview remains visible until the sharper version decodes.
const imageStages = [...document.querySelectorAll('.menu-art[data-detail-item]')];
for (const stage of imageStages) {
  const photo = stage.querySelector('.food-photo');
  const ready = () => { if (photo.naturalWidth) stage.dataset.imageState = 'ready'; };
  photo.addEventListener('load', ready);
  if (photo.complete) ready();
}
if ('IntersectionObserver' in window) {
  const nearbyImages = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.querySelectorAll('img').forEach(img => { img.loading = 'eager'; });
      nearbyImages.unobserve(entry.target);
    }
  }, { rootMargin: '600px 0px' });
  imageStages.forEach(stage => nearbyImages.observe(stage));
}
// Animated suggestions are decorative; the input value and accessible name stay stable.
const search = document.querySelector('#menu-search');
const suggestion = document.querySelector('[data-search-suggestion]');
if (search && suggestion) {
  const words = [...document.querySelectorAll('[data-category-trigger]')].map(button => button.querySelector('strong')?.textContent.trim()).filter(Boolean);
  let word = 0, length = words[0]?.length || 0, deleting = true, timer, visible = false;
  const tick = () => {
    clearTimeout(timer);
    if (!visible || calm() || document.hidden || document.activeElement === search || search.value || !words.length) return;
    const text = words[word];
    length += deleting ? -1 : 1;
    suggestion.textContent = text.slice(0, Math.max(0, length));
    let delay = deleting ? 48 : 85;
    if (length <= 0) { deleting = false; word = (word + 1) % words.length; delay = 280; }
    else if (length >= text.length && !deleting) { deleting = true; delay = 1600; }
    timer = setTimeout(tick, delay);
  };
  suggestion.textContent = words[0] || 'Biryani';
  const resume = () => { clearTimeout(timer); timer = setTimeout(tick, 1300); };
  search.addEventListener('focus', () => clearTimeout(timer));
  search.addEventListener('input', resume);
  search.addEventListener('blur', resume);
  document.addEventListener('visibilitychange', resume);
  reducedMotion.addEventListener('change', resume);
  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; resume(); }).observe(search);
  new MutationObserver(resume).observe(root, { attributes: true, attributeFilter: ['data-calm-motion'] });
  resume();
}
