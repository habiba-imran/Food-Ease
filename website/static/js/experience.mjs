// Decorative enhancements only. Ordering, consent, media, and sessions remain in app.js.
const root = document.documentElement;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
const calm = () => reducedMotion.matches || root.dataset.calmMotion === 'true';

// Editorial view controls affect the hero presentation only.
const editorialHero = document.querySelector('.hero');
const foodStudio = document.querySelector('[data-food-studio]');
const sceneViewButtons = [...document.querySelectorAll('[data-scene-view]')];
function setSceneView(view) {
  if (!foodStudio) return;
  foodStudio.dataset.sceneMode = view;
  document.body.dataset.heroView = view;
  sceneViewButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.sceneView === view)));
  const canvas = foodStudio.querySelector('canvas');
  if (canvas) canvas.tabIndex = view === 'inspect' ? 0 : -1;
}
sceneViewButtons.forEach(button => button.addEventListener('click', () => setSceneView(button.dataset.sceneView)));
setSceneView(foodStudio?.dataset.sceneMode || 'campaign');
const campaignPause = document.querySelector('[data-campaign-pause]');
campaignPause?.addEventListener('click', () => {
  const paused = root.dataset.campaignPaused !== 'true';
  root.dataset.campaignPaused = String(paused);
  campaignPause.setAttribute('aria-pressed', String(paused));
  campaignPause.setAttribute('aria-label', paused ? 'Play hero motion' : 'Pause hero motion');
  campaignPause.textContent = paused ? '▷' : 'Ⅱ';
});
let heroFrame = 0;
editorialHero?.addEventListener('pointermove', event => {
  if (calm() || !finePointer.matches || foodStudio?.dataset.sceneMode !== 'campaign') return;
  cancelAnimationFrame(heroFrame);
  heroFrame = requestAnimationFrame(() => {
    const r = editorialHero.getBoundingClientRect();
    const x = (event.clientX - r.left) / r.width - .5;
    const y = (event.clientY - r.top) / r.height - .5;
    editorialHero.style.setProperty('--scene-x', `${x * 30}px`);
    editorialHero.style.setProperty('--scene-y', `${y * 22}px`);
    editorialHero.style.setProperty('--scene-yaw', `${x * 9}deg`);
  });
});
editorialHero?.addEventListener('pointerleave', () => {
  cancelAnimationFrame(heroFrame);
  ['--scene-x', '--scene-y', '--scene-yaw'].forEach(key => editorialHero.style.removeProperty(key));
});
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
const stage = document.querySelector('[data-immersive-stage]');
let frame = 0;

function resetTilt() {
  cancelAnimationFrame(frame);
  stage?.style.removeProperty('--tilt-x');
  stage?.style.removeProperty('--tilt-y');
}
stage?.addEventListener('pointermove', event => {
  if (calm() || !finePointer.matches) return;
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    const rect = stage.getBoundingClientRect();
    stage.style.setProperty('--tilt-x', `${(0.5 - (event.clientY - rect.top) / rect.height) * 8}deg`);
    stage.style.setProperty('--tilt-y', `${((event.clientX - rect.left) / rect.width - 0.5) * 10}deg`);
  });
});
stage?.addEventListener('pointerleave', resetTilt);
stage?.addEventListener('pointercancel', resetTilt);
reducedMotion.addEventListener('change', resetTilt);

if (stage) {
  const dishTransition = new MutationObserver(() => {
    const photo = stage.querySelector('[data-preview-photo]');
    if (!photo || calm()) return;
    photo.getAnimations().forEach(animation => animation.cancel());
    photo.animate([
      { opacity: 0.25, transform: 'translate(-50%, -48%) rotate(-5deg) scale(.97)' },
      { opacity: 1, transform: 'translate(-50%, -50%) rotate(-9deg) translateZ(32px)' },
    ], { duration: 320, easing: 'cubic-bezier(.2,.65,.3,1)' });
  });
  dishTransition.observe(stage, { attributes: true, attributeFilter: ['data-preview-tone'] });
}

// Observe authoritative renders; this layer never submits an ordering action.
const count = document.querySelector('[data-cart-count]');
const total = document.querySelector('[data-cart-total]');
const mobileTotal = document.querySelector('[data-mobile-cart-total]');
let previousCount = count?.textContent;
function syncCartFeedback() {
  const value = count?.textContent?.trim() || '0';
  if (mobileTotal) mobileTotal.textContent = value === '0' ? 'View bag ↗' : `${value} ${value === '1' ? 'item' : 'items'} · ${total?.textContent || ''} ↗`;
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
    if (!calm() && root.dataset.visualMotionPaused !== 'true') return;
    textEntrances.disconnect();
    textTargets.forEach(text => {
      text.dataset.textReveal = 'shown';
      text.classList.remove('text-reveal-in');
    });
  };
  reducedMotion.addEventListener('change', revealAllText);
  new MutationObserver(revealAllText).observe(root, {
    attributes: true, attributeFilter: ['data-calm-motion', 'data-visual-motion-paused'],
  });
}

// Suppress the floating mobile shortcut when its destination or a modal is visible.
const mobileCart = document.querySelector('.mobile-cart-link');
let cartInView = false;
function syncMobileCart() {
  if (!mobileCart) return;
  mobileCart.hidden = cartInView || Number(count?.textContent || 0) === 0 || !!document.querySelector('dialog[open]');
}
if ('IntersectionObserver' in window) {
  const cartVisibility = new IntersectionObserver(entries => {
    cartInView = entries[0].isIntersecting;
    syncMobileCart();
  }, { threshold: 0 });
  const cart = document.querySelector('#cart-preview');
  if (cart) cartVisibility.observe(cart);
}
const dialogObserver = new MutationObserver(syncMobileCart);
document.querySelectorAll('dialog').forEach(dialog => dialogObserver.observe(dialog, { attributes: true, attributeFilter: ['open'] }));
if (count) dialogObserver.observe(count, { childList: true, characterData: true, subtree: true });
syncMobileCart();

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

// Tactile food cards: pointer tilt on desktop, ordinary scrolling on touch devices.
document.querySelectorAll('[data-menu-item]').forEach(card => {
  let tiltFrame = 0;
  card.addEventListener('pointermove', event => {
    if (calm() || !finePointer.matches) return;
    cancelAnimationFrame(tiltFrame);
    tiltFrame = requestAnimationFrame(() => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--card-rx', `${(.5 - (event.clientY - r.top) / r.height) * 7}deg`);
      card.style.setProperty('--card-ry', `${((event.clientX - r.left) / r.width - .5) * 9}deg`);
    });
  });
  card.addEventListener('pointerleave', () => {
    cancelAnimationFrame(tiltFrame);
    card.style.removeProperty('--card-rx'); card.style.removeProperty('--card-ry');
  });
});

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

// Animate a dish to the bag only after the authoritative cart count increases.
let pendingDish = null;
document.addEventListener('click', event => {
  const button = event.target.closest('[data-add-item]');
  const photo = button?.closest('[data-menu-item]')?.querySelector('img');
  if (photo && !button.disabled) pendingDish = { src: photo.src, rect: photo.getBoundingClientRect(), at: performance.now() };
}, { capture: true });
let flightCount = Number(count?.textContent || 0);
const flightObserver = new MutationObserver(() => {
  const next = Number(count?.textContent || 0);
  if (next > flightCount && pendingDish && performance.now() - pendingDish.at < 3000 && !calm()) {
    const bag = document.querySelector('.cart-button');
    const destination = bag?.getBoundingClientRect();
    if (destination) {
      const source = pendingDish.rect;
      const dish = document.createElement('img');
      dish.src = pendingDish.src; dish.alt = ''; dish.className = 'cart-flight'; dish.setAttribute('aria-hidden', 'true');
      dish.style.left = `${source.left + source.width / 2 - 32}px`; dish.style.top = `${source.top + source.height / 2 - 32}px`;
      document.body.append(dish);
      const dx = destination.left + destination.width / 2 - source.left - source.width / 2;
      const dy = destination.top + destination.height / 2 - source.top - source.height / 2;
      const animation = dish.animate([
        { transform: 'translate(0,0) scale(1)', opacity: 1 },
        { transform: `translate(${dx * .5}px,${dy * .55 - 70}px) scale(.8)`, opacity: 1, offset: .5 },
        { transform: `translate(${dx}px,${dy}px) scale(.12)`, opacity: .2 },
      ], { duration: 700, easing: 'cubic-bezier(.25,.6,.4,1)' });
      animation.finished.catch(() => {}).finally(() => dish.remove());
    }
  }
  pendingDish = null; flightCount = next;
});
if (count) flightObserver.observe(count, { childList: true, characterData: true, subtree: true });
