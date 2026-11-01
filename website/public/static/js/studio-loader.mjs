// The photographic campaign needs no WebGL bundle. Load the inspector on demand.
const host = document.querySelector('[data-food-studio]');
if (host) {
  let requested = false;
  function loadInspector() {
    if (requested || host.dataset.sceneMode !== 'inspect') return;
    requested = true;
    const fallback = host.querySelector('[data-fallback-src]');
    if (fallback && !fallback.getAttribute('src')) fallback.src = fallback.dataset.fallbackSrc;
    import('../vendor/food-studio.mjs?v=delivery-7').catch(() => {
      host.dataset.renderState = 'fallback';
      const status = host.querySelector('[data-studio-status]');
      if (status) status.textContent = 'The 3D view could not load. You can still browse and order.';
      host.querySelectorAll('.studio-control-deck button, .studio-control-deck input').forEach(el => { el.disabled = true; });
    });
  }
  new MutationObserver(loadInspector).observe(host, { attributes: true, attributeFilter: ['data-scene-mode'] });
  loadInspector();
}
