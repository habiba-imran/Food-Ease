import * as THREE from 'three';

// Small, deterministic material maps generated once. No image downloads or animation loop.
export function createFoodMaterials() {
  const textures = [];
  function canvasTexture(kind, seed) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 512;
    const ctx = canvas.getContext('2d');
    let state = seed;
    const random = () => { state = (Math.imul(state, 1664525) + 1013904223) | 0; return (state >>> 0) / 4294967296; };
    const colors = {
      bread: [190, 119, 43], crust: [141, 75, 27], beef: [76, 39, 24],
      leaf: [64, 117, 27], cheese: [239, 179, 48], tomato: [194, 47, 24], ceramic: [237, 222, 187],
    };
    const base = colors[kind];
    const pixels = ctx.createImageData(512, 512);
    for (let y = 0; y < 512; y++) {
      for (let x = 0; x < 512; x++) {
        const offset = (y * 512 + x) * 4;
        const noise = (random() - .5) * (kind === 'beef' ? 55 : 24);
        const broad = Math.sin(x * .032) * Math.cos(y * .027) * 10 + Math.sin((x + y) * .075) * 4;
        const baked = kind === 'bread' ? Math.sin(y / 512 * Math.PI) * 27 : 0;
        for (let c = 0; c < 3; c++) pixels.data[offset + c] = Math.max(0, Math.min(255, base[c] + noise + broad + baked));
        pixels.data[offset + 3] = 255;
      }
    }
    ctx.putImageData(pixels, 0, 0);
    if (kind === 'bread' || kind === 'crust') {
      // Uneven toasted pores and tiny flour flecks read across the dome UVs.
      for (let i = 0; i < 2200; i++) {
        const x = random() * 512, y = random() * 512, r = random() * 1.8 + .25;
        ctx.fillStyle = i % 5 ? `rgba(70,32,10,${random() * .28})` : 'rgba(255,233,173,.35)';
        ctx.beginPath(); ctx.ellipse(x, y, r * 1.6, r, random() * 3, 0, Math.PI * 2); ctx.fill();
      }
    } else if (kind === 'beef') {
      for (let i = 0; i < 900; i++) {
        ctx.fillStyle = i % 3 ? '#2e1b1290' : '#b4784355';
        ctx.beginPath(); ctx.arc(random() * 512, random() * 512, random() * 4 + 1, 0, Math.PI * 2); ctx.fill();
      }
      ctx.save(); ctx.translate(256, 256); ctx.rotate(-.55);
      for (let x = -350; x < 350; x += 76) {
        ctx.strokeStyle = '#1d160f9c'; ctx.lineWidth = 8;
        ctx.beginPath(); ctx.moveTo(x, -380); ctx.bezierCurveTo(x + 11, -100, x - 8, 100, x, 380); ctx.stroke();
        ctx.strokeStyle = '#c08a4250'; ctx.lineWidth = 2; ctx.stroke();
      }
      ctx.restore();
    } else if (kind === 'leaf') {
      ctx.strokeStyle = '#c2d26090'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(250, 0); ctx.bezierCurveTo(290, 160, 220, 360, 256, 512); ctx.stroke();
      for (let y = 20; y < 512; y += 29) {
        ctx.lineWidth = 1 + random(); ctx.beginPath(); ctx.moveTo(257, y);
        ctx.bezierCurveTo(160, y + 12, 90, y - 75, 0, y - 65); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(260, y); ctx.bezierCurveTo(360, y + 12, 420, y - 75, 512, y - 65); ctx.stroke();
      }
    } else if (kind === 'cheese') {
      for (let i = 0; i < 150; i++) {
        ctx.fillStyle = '#fff1ad48'; ctx.beginPath(); ctx.ellipse(random() * 512, random() * 512, random() * 4 + 1, random() * 2 + 1, 0, 0, 7); ctx.fill();
      }
    } else if (kind === 'tomato') {
      ctx.translate(256, 256);
      for (let i = 0; i < 8; i++) {
        ctx.rotate(Math.PI / 4); ctx.strokeStyle = '#ffb06b60'; ctx.lineWidth = 5;
        ctx.beginPath(); ctx.moveTo(20, 0); ctx.quadraticCurveTo(130, 35, 220, 0); ctx.stroke();
        for (let j = 0; j < 5; j++) {
          ctx.fillStyle = '#f4d686a0'; ctx.beginPath(); ctx.ellipse(80 + j * 24, 18 + random() * 22, 5, 2.5, -.4, 0, 7); ctx.fill();
        }
      }
    }
    const map = new THREE.CanvasTexture(canvas);
    map.colorSpace = THREE.SRGBColorSpace;
    map.anisotropy = 2;
    const bump = new THREE.CanvasTexture(canvas);
    bump.colorSpace = THREE.NoColorSpace;
    textures.push(map, bump);
    return { map, bump };
  }
  function material(kind, seed, roughness, bumpScale) {
    const { map, bump } = canvasTexture(kind, seed);
    return new THREE.MeshStandardMaterial({ color: '#ffffff', map, bumpMap: bump, bumpScale, roughness, metalness: 0 });
  }
  return {
    bun: material('bread', 492, .78, .045),
    crust: material('crust', 109, .85, .025),
    patty: material('beef', 211, .98, .075),
    lettuce: material('leaf', 335, .72, .035),
    cheese: material('cheese', 741, .55, .008),
    tomato: material('tomato', 102, .45, .012),
    ceramic: material('ceramic', 841, .55, .006),
    disposeTextures() { textures.forEach(texture => texture.dispose()); },
  };
}
