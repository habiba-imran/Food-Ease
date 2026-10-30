import * as THREE from 'three';
import { createFoodMaterials } from './food-materials.mjs';

// A self-contained illustrated food model. It has no shopping, voice, or media access.
const studio = document.querySelector('[data-food-studio]');
if (studio) {
  let initialized = false, scheduled = false, inView = false;
  function scheduleInitialization() {
    // The menu/session must finish its first render before optional GPU/material work.
    if (!inView || initialized || scheduled || studio.dataset.sceneMode === 'campaign' || !document.documentElement.dataset.foodeaseRevision) return;
    scheduled = true;
    const initialize = () => {
      scheduled = false;
      const rect = studio.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > innerHeight) return;
      initialized = true; startup.disconnect(); createStudio(studio);
    };
    if ('requestIdleCallback' in window) requestIdleCallback(initialize, { timeout: 1200 });
    else setTimeout(initialize, 100);
  }
  const startup = new IntersectionObserver(entries => { inView = entries[0].isIntersecting; scheduleInitialization(); });
  const appReady = new MutationObserver(() => {
    if (!document.documentElement.dataset.foodeaseRevision) return;
    appReady.disconnect(); scheduleInitialization();
  });
  appReady.observe(document.documentElement, { attributes: true, attributeFilter: ['data-foodease-revision'] });
  const sceneMode = new MutationObserver(scheduleInitialization);
  sceneMode.observe(studio, { attributes: true, attributeFilter: ['data-scene-mode'] });
  startup.observe(studio);
}

function createStudio(host) {
  const canvas = host.querySelector('canvas');
  const viewport = host.querySelector('[data-studio-viewport]');
  const slider = host.querySelector('[data-studio-spread]');
  const pauseButton = host.querySelector('[data-studio-pause]');
  const explodeButton = host.querySelector('[data-studio-explode]');
  const status = host.querySelector('[data-studio-status]');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const calm = () => motion.matches || document.documentElement.dataset.calmMotion === 'true';
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  } catch {
    host.dataset.renderState = 'fallback';
    status.textContent = '3D is unavailable on this device. Food ordering still works.';
    host.querySelectorAll('button, input').forEach(el => { el.disabled = true; });
    canvas.tabIndex = -1;
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 40);
  camera.position.set(4.5, 2.8, 6.7);
  camera.lookAt(0, 0.12, 0);
  scene.add(new THREE.HemisphereLight(0xfff2db, 0x724329, 1.8));
  const key = new THREE.DirectionalLight(0xffefd9, 3.5);
  key.position.set(-3, 6, 5); scene.add(key);
  key.castShadow = true; key.shadow.mapSize.set(512, 512);
  key.shadow.camera.left = key.shadow.camera.bottom = -3.5;
  key.shadow.camera.right = key.shadow.camera.top = 3.5;
  key.shadow.camera.near = .5; key.shadow.camera.far = 15;
  key.shadow.normalBias = .03;
  const rim = new THREE.DirectionalLight(0xffffff, 1.8);
  rim.position.set(4, 3, -4); scene.add(rim);

  const burger = new THREE.Group();
  burger.rotation.z = -0.12;
  scene.add(burger);
  const layers = [];
  const material = (color, roughness = .65) => new THREE.MeshStandardMaterial({ color, roughness, metalness: 0 });
  const foodMaterials = createFoodMaterials();
  const bunMat = foodMaterials.bun, edgeMat = foodMaterials.crust;
  const pattyMat = foodMaterials.patty, cheeseMat = foodMaterials.cheese;
  const lettuceMat = foodMaterials.lettuce, tomatoMat = foodMaterials.tomato;
  const seedMat = material('#fff0c0'), onionMat = material('#e5b2d9');
  const mesh = (geometry, mat, parent, x = 0, y = 0, z = 0) => {
    const item = new THREE.Mesh(geometry, mat); item.castShadow = true; item.receiveShadow = true;
    item.position.set(x, y, z); parent.add(item); return item;
  };
  function layer(y) {
    const group = new THREE.Group(); group.userData.base = y; group.position.y = y;
    layers.push(group); burger.add(group); return group;
  }
  const bottom = layer(-.86);
  mesh(new THREE.CylinderGeometry(1.17, 1.03, .27, 64), bunMat, bottom);
  mesh(new THREE.TorusGeometry(1.08, .11, 12, 64), edgeMat, bottom, 0, -.04).rotation.x = Math.PI / 2;
  const patty = layer(-.54);
  const meat = mesh(new THREE.SphereGeometry(1, 48, 24), pattyMat, patty);
  meat.scale.set(1.19, .19, 1.16);
  // Small baked edges give the silhouette texture without external textures or models.
  for (let i = 0; i < 28; i++) {
    const a = i * Math.PI * 2 / 28;
    const crumb = mesh(new THREE.IcosahedronGeometry(.10, 0), pattyMat, patty, Math.cos(a) * 1.1, Math.sin(i * 2.3) * .035, Math.sin(a) * 1.1);
    crumb.scale.y = .55;
  }
  const cheese = layer(-.29);
  const slice = mesh(new THREE.BoxGeometry(1.9, .065, 1.9, 1, 1, 1), cheeseMat, cheese);
  slice.rotation.y = Math.PI / 4;
  const tomatoes = layer(-.10);
  for (let i = 0; i < 3; i++) {
    const a = i * Math.PI * 2 / 3;
    const x = Math.cos(a) * .55, z = Math.sin(a) * .55;
    mesh(new THREE.CylinderGeometry(.56, .56, .12, 40), tomatoMat, tomatoes, x, 0, z);
    mesh(new THREE.TorusGeometry(.39, .018, 8, 36), material('#e17b4f'), tomatoes, x, .067, z).rotation.x = Math.PI / 2;
  }
  const greens = layer(.10);
  const leafGeometry = new THREE.CylinderGeometry(1.32, 1.25, .09, 80);
  const positions = leafGeometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i), z = positions.getZ(i), a = Math.atan2(z, x);
    const ripple = 1 + Math.sin(a * 11) * .055;
    positions.setXYZ(i, x * ripple, positions.getY(i) + Math.sin(a * 9) * .065, z * ripple);
  }
  leafGeometry.computeVertexNormals(); mesh(leafGeometry, lettuceMat, greens);
  const onions = layer(.26);
  for (let i = 0; i < 3; i++) {
    const ring = mesh(new THREE.TorusGeometry(.37, .055, 10, 40), onionMat, onions, (i - 1) * .52, 0, Math.sin(i * 3) * .35);
    ring.rotation.x = Math.PI / 2;
  }
  const crown = layer(.42);
  const dome = mesh(new THREE.SphereGeometry(1.23, 64, 32, 0, Math.PI * 2, 0, Math.PI / 2), bunMat, crown);
  dome.scale.y = .58;
  mesh(new THREE.CylinderGeometry(1.23, 1.23, .08, 64), edgeMat, crown);
  const sesame = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), seedMat, 55);
  const matrix = new THREE.Object3D();
  for (let i = 0; i < 55; i++) {
    const a = i * 2.399963, r = Math.sqrt((i + .5) / 55) * 1.13;
    matrix.position.set(Math.cos(a) * r, Math.sqrt(1.23 ** 2 - r ** 2) * .58 + .012, Math.sin(a) * r);
    matrix.rotation.set(0, a, Math.cos(a) * .25);
    matrix.scale.set(.065, .025, .028); matrix.updateMatrix(); sesame.setMatrixAt(i, matrix.matrix);
  }
  crown.add(sesame);

  // A contact shadow and concentric plate provide a spatial ground plane.
  const plate = new THREE.Group(); plate.position.y = -1.8; scene.add(plate);
  mesh(new THREE.CylinderGeometry(1.85, 1.65, .10, 80), foodMaterials.ceramic, plate);
  const plateRing = mesh(new THREE.TorusGeometry(1.65, .035, 10, 80), material('#d2ba85'), plate, 0, .06);
  plateRing.rotation.x = Math.PI / 2;

  let paused = false, visible = false, disposed = false, request = 0;
  let rotation = -.6, targetRotation = -.6, spread = .35, targetSpread = .35;
  let drag = null, last = 0, elapsed = 0;
  function setSpread(value) {
    targetSpread = value / 100; slider.value = String(value);
    host.querySelector('[data-spread-value]').textContent = `${value}%`;
    explodeButton.setAttribute('aria-pressed', String(value > 65));
    explodeButton.firstChild.textContent = value > 65 ? 'Bring it together ' : 'Explore the layers ';
    host.dataset.exploded = String(value > 65);
    wake();
  }
  slider.addEventListener('input', () => setSpread(Number(slider.value)));
  explodeButton.addEventListener('click', () => setSpread(targetSpread > .65 ? 0 : 100));
  function syncPause() {
    const stopped = paused || calm();
    document.documentElement.dataset.visualMotionPaused = String(stopped);
    pauseButton.setAttribute('aria-pressed', String(stopped));
    pauseButton.setAttribute('aria-label', stopped ? 'Play decorative animations' : 'Pause decorative animations');
    pauseButton.textContent = stopped ? '▷' : 'Ⅱ';
    host.dataset.motion = stopped ? 'paused' : 'playing';
    if (calm()) pauseButton.disabled = true; else pauseButton.disabled = false;
    wake();
  }
  pauseButton.addEventListener('click', () => { paused = !paused; syncPause(); });
  host.querySelectorAll('[data-studio-turn]').forEach(button => button.addEventListener('click', () => {
    targetRotation += Number(button.dataset.studioTurn) * Math.PI / 4;
    paused = true; syncPause();
  }));
  canvas.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) return;
    event.preventDefault(); paused = true;
    targetRotation = event.key === 'Home' ? -.6 : targetRotation + (event.key === 'ArrowLeft' ? -1 : 1) * Math.PI / 6;
    syncPause();
  });
  canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    drag = { x: event.clientX, y: event.clientY, base: targetRotation, active: false, id: event.pointerId };
  });
  canvas.addEventListener('pointermove', event => {
    if (!drag) return;
    const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    if (!drag.active && Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy) * 1.2) {
      drag.active = true; canvas.setPointerCapture(event.pointerId); paused = true; syncPause();
    }
    if (drag.active) { targetRotation = drag.base + dx * .012; host.dataset.dragged = 'true'; wake(); }
  });
  const release = () => { if (drag && canvas.hasPointerCapture(drag.id)) canvas.releasePointerCapture(drag.id); drag = null; };
  canvas.addEventListener('pointerup', release); canvas.addEventListener('pointercancel', release);
  canvas.addEventListener('lostpointercapture', () => { drag = null; });

  function resize() {
    const { width, height } = viewport.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false); camera.aspect = width / height;
    camera.position.set(4.5, 2.8, 6.7).multiplyScalar(camera.aspect < 1 ? 1.12 : 1);
    camera.lookAt(0, .12, 0); camera.updateProjectionMatrix(); wake();
  }
  const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(viewport);
  function draw(time) {
    request = 0;
    if (disposed || !visible || document.hidden || host.dataset.sceneMode === 'campaign') { last = 0; return; }
    if (last && time - last < 1000 / 30) { request = requestAnimationFrame(draw); return; }
    const dt = last ? Math.min((time - last) / 1000, .05) : 0; last = time; elapsed += dt;
    const moving = !paused && !calm() && !drag?.active;
    if (moving) targetRotation += dt * .18;
    const smoothing = calm() ? 1 : 1 - Math.exp(-dt * 7);
    rotation += (targetRotation - rotation) * smoothing;
    spread += (targetSpread - spread) * smoothing;
    burger.rotation.y = rotation;
    burger.position.y = moving ? Math.sin(elapsed * 1.4) * .075 : 0;
    // Keep the full separated stack in frame on narrow and short viewports.
    const framing = (camera.aspect < 1 ? 1.12 : 1) * (1 + Math.max(0, spread - .35) * .32);
    camera.position.set(4.5, 2.8, 6.7).multiplyScalar(framing);
    camera.lookAt(0, -.05, 0);
    layers.forEach((part, i) => { part.position.y = part.userData.base + (i - 3) * spread * .42; });
    plate.position.y = -1.8 - spread * .65;
    renderer.render(scene, camera);
    host.dataset.rotation = rotation.toFixed(3);
    host.dataset.layerSpread = spread.toFixed(3);
    const settling = Math.abs(targetRotation - rotation) > .001 || Math.abs(targetSpread - spread) > .001;
    if (moving || settling) request = requestAnimationFrame(draw);
  }
  function wake() { if (!disposed && visible && !document.hidden && !request) request = requestAnimationFrame(draw); }
  const visibility = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; wake(); }, { rootMargin: '80px' });
  visibility.observe(host);
  document.addEventListener('visibilitychange', () => { last = 0; wake(); });
  motion.addEventListener('change', syncPause);
  const preferences = new MutationObserver(syncPause);
  preferences.observe(document.documentElement, { attributes: true, attributeFilter: ['data-calm-motion'] });
  const mode = new MutationObserver(wake);
  mode.observe(host, { attributes: true, attributeFilter: ['data-scene-mode'] });
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault(); disposed = true; cancelAnimationFrame(request);
    host.dataset.renderState = 'fallback'; status.textContent = '3D paused by your device. Reload to try again.';
    host.querySelectorAll('button, input').forEach(el => { el.disabled = true; });
  });
  window.addEventListener('pagehide', event => {
    if (event.persisted) return;
    disposed = true; cancelAnimationFrame(request); resizeObserver.disconnect(); visibility.disconnect(); preferences.disconnect(); mode.disconnect();
    scene.traverse(object => { object.geometry?.dispose(); if (object.material) object.material.dispose(); });
    foodMaterials.disposeTextures(); renderer.dispose();
  }, { once: true });
  host.dataset.renderState = 'ready'; syncPause(); resize();
}
