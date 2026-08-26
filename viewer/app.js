import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const $ = (id) => document.getElementById(id);
const TYPES = ['normal','fire','water','electric','grass','ice','fighting','poison','ground',
               'flying','psychic','bug','rock','ghost','dragon','dark','steel','fairy'];
const TYPE_PT = { normal:'normal', fire:'fogo', water:'água', electric:'elétrico', grass:'planta',
  ice:'gelo', fighting:'lutador', poison:'venenoso', ground:'terrestre', flying:'voador',
  psychic:'psíquico', bug:'inseto', rock:'pedra', ghost:'fantasma', dragon:'dragão',
  dark:'sombrio', steel:'aço', fairy:'fada' };
const typeColor = (t) => getComputedStyle(document.documentElement).getPropertyValue(`--t-${t}`).trim() || '#888';

// ---------------------------------------------------------------- estado

let DATA = null;
let filtered = [];
let current = null;      // especie selecionada
let currentVariant = null;
let activeTypes = new Set();
let hasThumbs = false;   // miniaturas sao opcionais (veja tools/thumbs.mjs)
let mixer = null, clips = [], action = null;

// ---------------------------------------------------------------- three.js

const canvas = $('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 200);
camera.position.set(0, 1.35, 4.2);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.075;
controls.target.set(0, 0.95, 0);
controls.minDistance = 0.8;
controls.maxDistance = 14;
controls.autoRotateSpeed = 1.9;
controls.autoRotate = true;

scene.add(new THREE.AmbientLight(0xffffff, 1.35));
const hemi = new THREE.HemisphereLight(0xdbe9ff, 0x2a2f38, 1.15);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 1.9);
key.position.set(3.5, 6, 4.5);
scene.add(key);
const fill = new THREE.DirectionalLight(0xbcd4ff, 0.75);
fill.position.set(-4, 2.2, -3.5);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 0.5);
rim.position.set(0, 2.5, -6);
scene.add(rim);

const grid = new THREE.GridHelper(14, 28, 0x2f3947, 0x1e2733);
grid.material.transparent = true;
grid.material.opacity = 0.55;
scene.add(grid);

const root = new THREE.Group();
root.name = 'root';
scene.add(root);

// expostos para os scripts de diagnostico e de geracao de miniaturas em tools/
window.__viewer = { THREE, scene, camera, renderer, root, controls, grid,
                    get fitCamera() { return fitCamera; } };

const maxAniso = renderer.capabilities.getMaxAnisotropy();
const clock = new THREE.Clock();

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  if (canvas.width !== w * renderer.getPixelRatio() || canvas.height !== h * renderer.getPixelRatio()) {
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    const obj = root.children[0];
    if (obj) fitCamera(obj, { animate: true });
  }
}

function tick() {
  requestAnimationFrame(tick);
  resize();
  const dt = clock.getDelta();
  if (mixer) mixer.update(dt);
  controls.update();
  renderer.render(scene, camera);
}
tick();

// ---------------------------------------------------------------- carga de modelos

const cache = new Map();          // id -> Object3D (LRU simples)
const CACHE_MAX = 8;
const gltfLoader = new GLTFLoader().setDRACOLoader(
  new DRACOLoader().setDecoderPath('./vendor/jsm/libs/draco/gltf/'));
let loadToken = 0;

function disposeObject(obj) {
  obj.traverse((o) => {
    if (o.isMesh) {
      o.geometry?.dispose();
      for (const m of [].concat(o.material)) {
        for (const k of ['map', 'normalMap', 'emissiveMap', 'specularMap', 'alphaMap']) m[k]?.dispose?.();
        m.dispose();
      }
    }
  });
}

function trimCache(keep) {
  while (cache.size > CACHE_MAX) {
    const oldest = cache.keys().next().value;
    if (oldest === keep) break;
    disposeObject(cache.get(oldest));
    cache.delete(oldest);
  }
}

/** Filtragem anisotropica -- vale para qualquer formato. */
function polishTextures(obj) {
  obj.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) {
      for (const slot of ['map', 'emissiveMap', 'normalMap', 'roughnessMap', 'metalnessMap']) {
        if (m[slot]) { m[slot].anisotropy = maxAniso; m[slot].needsUpdate = true; }
      }
    }
  });
}

/** Escala e centraliza o modelo para caber num cubo de ~2 unidades, apoiado na grade. */
function frame(obj) {
  obj.updateWorldMatrix(true, true);
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const scale = 1.9 / Math.max(size.x, size.y, size.z);

  obj.scale.multiplyScalar(scale);
  obj.position.sub(center.multiplyScalar(scale));
  obj.position.y += (size.y * scale) / 2;   // apoia a base em y=0
}

/**
 * Aproxima a camera o suficiente para o modelo preencher o quadro, levando em
 * conta o formato da janela -- senao bicho comprido (Rayquaza) ou baixinho
 * (Castform) ficam perdidos no meio da tela.
 */
function fitCamera(obj, { animate = false } = {}) {
  obj.updateWorldMatrix(true, true);
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  // como o modelo so gira em Y, o pior caso na horizontal e a diagonal XZ --
  // usar a esfera envolvente inteira deixaria a camera longe demais
  const radiusXZ = Math.hypot(size.x, size.z) / 2;
  const halfY = size.y / 2;

  const vFov = THREE.MathUtils.degToRad(camera.fov);
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * camera.aspect);
  const dist = Math.max(halfY / Math.sin(vFov / 2),
                        radiusXZ / Math.sin(hFov / 2)) * 1.08;

  const target = new THREE.Vector3(0, center.y, 0);
  const dir = animate
    ? camera.position.clone().sub(controls.target).normalize()
    : new THREE.Vector3(0, 0.2, 1).normalize();

  controls.target.copy(target);
  camera.position.copy(target).addScaledVector(dir, dist);
  camera.near = Math.max(0.01, dist * 0.05);
  camera.far = dist + radiusXZ * 6;
  camera.updateProjectionMatrix();
  controls.minDistance = dist * 0.25;
  controls.maxDistance = dist * 4;
  controls.update();
}

function meshStats(obj) {
  let verts = 0, tris = 0, bones = 0, meshes = 0;
  obj.traverse((o) => {
    if (o.isBone) bones++;
    if (o.isMesh) {
      meshes++;
      const g = o.geometry;
      verts += g.attributes.position.count;
      tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
    }
  });
  return { verts, tris: Math.round(tris), bones, meshes };
}

async function loadVariant(species, variant) {
  const token = ++loadToken;
  current = species;
  currentVariant = variant;

  renderInfo();
  renderVariants();
  markListSelection();
  location.hash = variant.form === '00' || species.variants.length === 1
    ? String(species.dex) : variant.id;

  $('error').hidden = true;

  let obj = cache.get(variant.id);
  if (obj) {
    cache.delete(variant.id);
    cache.set(variant.id, obj);
  } else {
    $('loading').hidden = false;
    $('loading-text').textContent = `carregando ${species.name}…`;
    const url = `${DATA.root}/${variant.file}`;
    try {
      const gltf = await gltfLoader.loadAsync(url, onProgress);
      obj = gltf.scene;
      obj.userData.clips = gltf.animations || [];
    } catch (err) {
      if (token !== loadToken) return;
      $('loading').hidden = true;
      showError(`Não consegui carregar <code>${variant.file}</code>.<br>${err.message}`);
      return;
    }
    if (token !== loadToken) { disposeObject(obj); return; }
    polishTextures(obj);
    frame(obj);
    cache.set(variant.id, obj);
  }

  if (token !== loadToken) return;
  $('loading').hidden = true;

  root.clear();
  if (mixer) { mixer.stopAllAction(); mixer = null; }
  root.add(obj);
  fitCamera(obj);
  trimCache(variant.id);

  clips = obj.userData.clips || [];
  setupAnimations(obj);

  const s = meshStats(obj);
  $('stats').innerHTML = [
    `${s.verts.toLocaleString('pt-BR')} vértices`,
    `${s.tris.toLocaleString('pt-BR')} triângulos`,
    `${s.bones} ossos · ${s.meshes} malha${s.meshes > 1 ? 's' : ''}`,
    variant.textures
      ? `${variant.kb} KB · ${variant.textures.length} textura${variant.textures.length > 1 ? 's' : ''}`
      : `${variant.kb} KB`,
    clips.length ? `${clips.length} animações` : `sem keyframes`,
  ].join('<br>');
}

function onProgress(e) {
  if (e.lengthComputable && e.total) {
    $('loading-text').textContent = `carregando ${current?.name ?? ''}… ${Math.round((e.loaded / e.total) * 100)}%`;
  }
}

function setupAnimations(obj) {
  const wrap = document.querySelector('.anim');
  const sel = $('anim-select');
  if (!clips.length) { wrap.hidden = true; return; }
  wrap.hidden = false;
  sel.innerHTML = clips.map((c, i) => `<option value="${i}">${c.name}</option>`).join('');
  mixer = new THREE.AnimationMixer(obj);
  playClip(0);
}

function playClip(i) {
  if (!mixer || !clips[i]) return;
  action?.fadeOut(0.2);
  action = mixer.clipAction(clips[i]);
  action.reset().fadeIn(0.2).play();
}

function showError(html) {
  const el = $('error');
  el.innerHTML = html;
  el.hidden = false;
}

// ---------------------------------------------------------------- interface

function renderInfo() {
  $('i-dex').textContent = String(current.dex).padStart(3, '0');
  $('i-name').textContent = current.name;
  $('i-types').innerHTML = current.types
    .map((t) => `<span class="type" style="background:${typeColor(t)}">${TYPE_PT[t] ?? t}</span>`)
    .join('');
}

function renderVariants() {
  const el = $('variants');
  if (current.variants.length < 2) { el.innerHTML = ''; return; }
  el.innerHTML = current.variants
    .map((v) => `<button data-id="${v.id}" class="${v.id === currentVariant.id ? 'on' : ''}">${v.label}</button>`)
    .join('');
  for (const b of el.querySelectorAll('button')) {
    b.onclick = () => loadVariant(current, current.variants.find((v) => v.id === b.dataset.id));
  }
}

function renderTypeFilters() {
  const present = TYPES.filter((t) => DATA.species.some((s) => s.types.includes(t)));
  $('types').innerHTML = present
    .map((t) => `<button data-type="${t}" style="--tc:${typeColor(t)}">${TYPE_PT[t]}</button>`)
    .join('');
  for (const b of $('types').querySelectorAll('button')) {
    b.onclick = () => {
      const t = b.dataset.type;
      activeTypes.has(t) ? activeTypes.delete(t) : activeTypes.add(t);
      b.classList.toggle('on', activeTypes.has(t));
      applyFilter();
    };
  }
}

function renderList() {
  $('list').innerHTML = filtered.map((s) => {
    const dots = s.types.map((t) => `<i style="background:${typeColor(t)}"></i>`).join('');
    const forms = s.variants.length > 1 ? `<span class="li-forms">${s.variants.length}</span>` : '';
    const thumb = hasThumbs
      ? `<img class="li-thumb" loading="lazy" alt="" src="thumbs/${s.variants[0].id}.png">` : '';
    return `<li data-dex="${s.dex}">
      ${thumb}<span class="li-dex">${String(s.dex).padStart(3, '0')}</span>
      <span class="li-name">${s.name}</span>
      ${forms}<span class="li-dots">${dots}</span>
    </li>`;
  }).join('');
  for (const li of $('list').children) {
    li.onclick = () => {
      const sp = DATA.species.find((s) => s.dex === +li.dataset.dex);
      loadVariant(sp, sp.variants[0]);
    };
  }
  markListSelection();
  $('count').textContent = `${filtered.length} de ${DATA.species.length} espécies · ` +
    `${filtered.reduce((n, s) => n + s.variants.length, 0)} modelos`;
}

function markListSelection() {
  for (const li of $('list').children) {
    const on = current && +li.dataset.dex === current.dex;
    li.classList.toggle('sel', on);
    if (on) li.scrollIntoView({ block: 'nearest' });
  }
}

function applyFilter() {
  const q = $('search').value.trim().toLowerCase();
  $('clear-search').hidden = !q;
  filtered = DATA.species.filter((s) => {
    if (activeTypes.size && !s.types.some((t) => activeTypes.has(t))) return false;
    if (!q) return true;
    return s.name.toLowerCase().includes(q)
      || String(s.dex) === q || String(s.dex).padStart(3, '0').includes(q)
      || s.types.some((t) => t.includes(q) || (TYPE_PT[t] ?? '').includes(q))
      || s.variants.some((v) => v.label.toLowerCase().includes(q));
  });
  renderList();
}

function step(delta) {
  if (!filtered.length) return;
  const i = filtered.findIndex((s) => s.dex === current?.dex);
  const next = filtered[Math.max(0, Math.min(filtered.length - 1, (i < 0 ? 0 : i + delta)))];
  if (next) loadVariant(next, next.variants[0]);
}

// ---------------------------------------------------------------- controles

$('search').oninput = applyFilter;
$('clear-search').onclick = () => { $('search').value = ''; applyFilter(); $('search').focus(); };
$('anim-select').onchange = (e) => playClip(+e.target.value);

const toggle = (btn, fn) => {
  $(btn).onclick = () => { const on = $(btn).classList.toggle('on'); fn(on); };
};
toggle('t-rotate', (on) => { controls.autoRotate = on; });
toggle('t-grid', (on) => { grid.visible = on; });
toggle('t-wire', (on) => {
  root.traverse((o) => { if (o.isMesh) for (const m of [].concat(o.material)) m.wireframe = on; });
});
toggle('t-bg', (on) => {
  document.body.classList.toggle('light-stage', on);
  grid.material.color.set(on ? 0x9aa8b8 : 0x2f3947);
  hemi.groundColor.set(on ? 0xbfc9d4 : 0x2a2f38);
});
$('t-reset').onclick = () => {
  const obj = root.children[0];
  if (obj) fitCamera(obj);
};

addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
    if (e.key === 'Escape') e.target.blur();
    return;
  }
  const keys = { ArrowDown: () => step(1), ArrowUp: () => step(-1),
                 r: () => $('t-rotate').click(), w: () => $('t-wire').click(),
                 g: () => $('t-grid').click(), b: () => $('t-bg').click(),
                 ' ': () => $('t-reset').click(), '/': () => $('search').focus() };
  const fn = keys[e.key] ?? keys[e.key.toLowerCase()];
  if (fn) { e.preventDefault(); fn(); }
});

// ---------------------------------------------------------------- boot

function fromHash() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (!h) return null;
  for (const s of DATA.species) {
    for (const v of s.variants) if (v.id === h) return [s, v];
    if (String(s.dex) === h || s.slug === h.toLowerCase()) return [s, s.variants[0]];
  }
  return null;
}

(async function init() {
  try {
    DATA = await (await fetch('models.json')).json();
  } catch (err) {
    showError(`Não achei <code>models.json</code>.<br><br>` +
      `Este viewer precisa rodar via servidor HTTP (abrir o arquivo direto com <code>file://</code> não funciona).<br>` +
      `Rode <code>python tools/serve.py</code> na raiz do projeto.`);
    $('loading').hidden = true;
    return;
  }
  // o proprio index diz se as miniaturas existem (tools/build_viewer_index.py)
  hasThumbs = DATA.thumbs === true;
  document.body.classList.toggle('with-thumbs', hasThumbs);

  renderTypeFilters();
  applyFilter();
  const [sp, v] = fromHash() ?? [DATA.species[0], DATA.species[0].variants[0]];
  loadVariant(sp, v);
})();

addEventListener('hashchange', () => {
  const hit = fromHash();
  if (hit && hit[1].id !== currentVariant?.id) loadVariant(hit[0], hit[1]);
});
