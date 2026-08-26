import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { BattleStreams, Teams, Dex } from '@pkmn/sim';

const $ = (sel) => document.querySelector(sel);
const gen3 = Dex.forGen(3);

const TYPE_PT = { normal:'normal', fire:'fogo', water:'água', electric:'elétrico', grass:'planta',
  ice:'gelo', fighting:'lutador', poison:'venenoso', ground:'terrestre', flying:'voador',
  psychic:'psíquico', bug:'inseto', rock:'pedra', ghost:'fantasma', dragon:'dragão',
  dark:'sombrio', steel:'aço', fairy:'fada' };
const typeColor = (t) => getComputedStyle(document.documentElement).getPropertyValue(`--t-${(t || '').toLowerCase()}`).trim() || '#888';

const STATUS_PT = { brn: 'queimado', par: 'paralisado', psn: 'envenenado', tox: 'envenenado (grave)',
  slp: 'dormindo', frz: 'congelado' };
const STAT_PT = { atk: 'Ataque', def: 'Defesa', spa: 'Ataque Especial', spd: 'Defesa Especial', spe: 'Velocidade', accuracy: 'precisão', evasion: 'evasão' };
const REASON_PT = { flinch: 'ficou paralisado de medo', par: 'está paralisado', slp: 'está dormindo', frz: 'está congelado', partiallytrapped: 'está preso' };

// ---------------------------------------------------------------- carrega o elenco

let ROSTER = [];
try {
  ROSTER = (await (await fetch('models.json')).json()).species;
} catch (e) {
  document.body.innerHTML = `<p style="padding:40px;color:#ffb4a8">Não achei models.json. Rode via <code>python tools/serve.py</code>.</p>`;
  throw e;
}

// ---------------------------------------------------------------- tela de escolha

const picks = { p1: null, p2: null };

function renderList(side, query) {
  const ul = $(`.picker[data-side="${side}"] .list`);
  const q = (query || '').trim().toLowerCase();
  const items = ROSTER.filter((s) => !q || s.name.toLowerCase().includes(q) || String(s.dex).includes(q)
    || s.types.some((t) => t.includes(q) || (TYPE_PT[t] ?? '').includes(q)));
  ul.innerHTML = items.map((s) => `
    <li data-dex="${s.dex}" class="${picks[side]?.dex === s.dex ? 'sel' : ''}">
      <span class="dex">${String(s.dex).padStart(3, '0')}</span>
      <span class="nm">${s.name}</span>
      <span class="dots">${s.types.map((t) => `<i style="background:${typeColor(t)}"></i>`).join('')}</span>
    </li>`).join('');
  for (const li of ul.children) {
    li.onclick = () => choose(side, ROSTER.find((s) => s.dex === +li.dataset.dex));
  }
}

function choose(side, species) {
  picks[side] = species;
  renderList(side, $(`.picker[data-side="${side}"] .search`).value);
  const box = $(`.picker[data-side="${side}"] .chosen`);
  box.hidden = false;
  box.innerHTML = `<span>#${String(species.dex).padStart(3, '0')} <b>${species.name}</b></span>
    <span>${species.types.map((t) => `<span class="type" style="background:${typeColor(t)};padding:3px 7px;border-radius:5px;font-size:10px;font-weight:700;text-transform:uppercase;color:#08121b;margin-left:4px">${TYPE_PT[t] ?? t}</span>`).join('')}</span>`;
  $('#start-battle').disabled = !(picks.p1 && picks.p2);
}

for (const side of ['p1', 'p2']) {
  renderList(side, '');
  $(`.picker[data-side="${side}"] .search`).oninput = (e) => renderList(side, e.target.value);
}

$('#randomize').onclick = () => {
  const a = ROSTER[Math.floor(Math.random() * ROSTER.length)];
  let b = ROSTER[Math.floor(Math.random() * ROSTER.length)];
  while (b.dex === a.dex) b = ROSTER[Math.floor(Math.random() * ROSTER.length)];
  choose('p1', a);
  choose('p2', b);
};

// ---------------------------------------------------------------- montagem de time legal

/** Monta um PokemonSet nível 50 usando só golpes com fonte gen3 (3L/3M/3T/3S) do learnset real. */
async function buildRandomSet(speciesName, level = 50) {
  const species = gen3.species.get(speciesName);
  const learnsetData = await gen3.learnsets.get(species.id);
  const legalIds = Object.entries(learnsetData?.learnset ?? {})
    .filter(([, sources]) => sources.some((s) => s.startsWith('3')))
    .map(([id]) => id);

  const moveInfos = legalIds.map((id) => gen3.moves.get(id)).filter((m) => m?.exists);
  const damaging = moveInfos.filter((m) => m.category !== 'Status' && m.basePower > 0);
  const status = moveInfos.filter((m) => m.category === 'Status');
  const stab = damaging.filter((m) => species.types.includes(m.type)).sort((a, b) => b.basePower - a.basePower);
  const coverage = damaging.filter((m) => !species.types.includes(m.type)).sort((a, b) => b.basePower - a.basePower);

  const picked = [];
  for (const m of stab) if (picked.length < 2) picked.push(m);
  for (const m of coverage) if (picked.length < 3) picked.push(m);
  for (const m of status) if (picked.length < 4) picked.push(m);
  for (const m of [...stab, ...coverage, ...status]) { if (picked.length >= 4) break; if (!picked.includes(m)) picked.push(m); }

  const moves = picked.map((m) => m.id);
  if (!moves.length) moves.push(legalIds[0] ?? 'tackle');

  const higherStat = species.baseStats.atk >= species.baseStats.spa ? 'atk' : 'spa';
  const nature = higherStat === 'atk'
    ? (species.baseStats.atk > species.baseStats.spa + 5 ? 'Adamant' : 'Serious')
    : (species.baseStats.spa > species.baseStats.atk + 5 ? 'Modest' : 'Serious');
  const evs = { hp: 4, atk: 0, def: 0, spa: 0, spd: 0, spe: 252 };
  evs[higherStat] = 252;

  return {
    name: species.name, species: species.name, level, gender: species.gender || 'M',
    moves, ability: Object.values(species.abilities)[0], item: '', nature,
    evs, ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
    moveInfos: Object.fromEntries(picked.map((m) => [m.id, m])),   // cache p/ os botoes
  };
}

// ---------------------------------------------------------------- cena 3D

const canvas = $('#canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
camera.position.set(0, 2.5, 6.6);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.target.set(0, 1.1, -0.2);
controls.minDistance = 3;
controls.maxDistance = 12;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.AmbientLight(0xffffff, 1.3));
const key = new THREE.DirectionalLight(0xffffff, 1.9); key.position.set(4, 7, 5); scene.add(key);
const fill = new THREE.DirectionalLight(0xbcd4ff, 0.7); fill.position.set(-4, 3, -3); scene.add(fill);

function platform(x, z, radius, color) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, 0.08, 40),
    new THREE.MeshStandardMaterial({ color, roughness: 1 }));
  m.position.set(x, -0.04, z);
  scene.add(m);
}
platform(-1.9, 1.6, 1.15, 0xcfe6a8);
platform(1.9, -1.4, 1.35, 0xa9c9e0);

const gltfLoader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('./vendor/jsm/libs/draco/gltf/'));

function normalizeAndPlace(obj, x, z, targetSize = 1.55) {
  obj.updateWorldMatrix(true, true);
  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const scale = targetSize / Math.max(size.x, size.y, size.z, 0.001);
  obj.scale.multiplyScalar(scale);
  obj.position.sub(center.multiplyScalar(scale));
  obj.position.y += (size.y * scale) / 2;
  obj.position.x += x;
  obj.position.z += z;
  scene.add(obj);
  return obj;
}

async function loadCombatant(file, x, z) {
  const gltf = await gltfLoader.loadAsync(`../assets/gen3_glb/${file}`);
  const obj = normalizeAndPlace(gltf.scene, x, z);
  obj.userData.baseY = obj.position.y;
  obj.userData.phase = Math.random() * Math.PI * 2;
  return obj;
}

/** Pulso vermelho rapido nos materiais do modelo, pra sentir o golpe. */
function flash(obj) {
  if (!obj) return;
  const mats = [];
  obj.traverse((o) => { if (o.isMesh) for (const m of [].concat(o.material)) mats.push(m); });
  const t0 = performance.now();
  const dur = 260;
  function tick() {
    const t = Math.min(1, (performance.now() - t0) / dur);
    const intensity = Math.sin(t * Math.PI) * 0.85;
    for (const m of mats) { m.emissive?.setRGB(intensity, 0, 0); m.emissiveIntensity = 1; }
    if (t < 1) requestAnimationFrame(tick); else for (const m of mats) m.emissive?.setRGB(0, 0, 0);
  }
  tick();
}

/** Afunda e desaparece o modelo -- usado quando o Pokemon desmaia. */
function faintAway(obj) {
  if (!obj) return;
  const t0 = performance.now();
  const dur = 700;
  const y0 = obj.position.y;
  const mats = [];
  obj.traverse((o) => { if (o.isMesh) for (const m of [].concat(o.material)) { m.transparent = true; mats.push(m); } });
  function tick() {
    const t = Math.min(1, (performance.now() - t0) / dur);
    obj.position.y = y0 - t * 0.9;
    for (const m of mats) m.opacity = 1 - t;
    if (t < 1) requestAnimationFrame(tick); else obj.visible = false;
  }
  tick();
}

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  resize();
  const t = clock.getElapsedTime();
  for (const obj of [state.playerObj, state.foeObj]) {
    if (obj?.visible) obj.position.y = obj.userData.baseY + Math.sin(t * 1.6 + obj.userData.phase) * 0.035;
  }
  controls.update();
  renderer.render(scene, camera);
});

// ---------------------------------------------------------------- estado da luta

const state = { stream: null, playerObj: null, foeObj: null, hp: {}, over: false };

function hud(side) { return side === 'p1' ? $('.hud-player') : $('.hud-foe'); }

function setHpBar(side, cur, max) {
  state.hp[side] = { cur, max };
  const pct = Math.max(0, Math.min(100, (cur / max) * 100));
  const el = hud(side);
  const fill = el.querySelector('.hpfill');
  fill.style.width = pct + '%';
  fill.classList.toggle('mid', pct <= 50 && pct > 20);
  fill.classList.toggle('low', pct <= 20);
  if (side === 'p1') el.querySelector('.hpnum').textContent = `${cur} / ${max}`;
}

function setNameplate(side, name, level) {
  const el = hud(side);
  el.querySelector('.name').textContent = name;
  el.querySelector('.lvl').textContent = `Nv. ${level}`;
}

function logLine(html, cls = '') {
  const p = document.createElement('p');
  if (cls) p.className = cls;
  p.innerHTML = html;
  $('#log').appendChild(p);
  $('#log').scrollTop = $('#log').scrollHeight;
}

function shortName(raw) {
  return raw.replace(/^p[12][ab]?:\s*/, '');
}

function parseHpToken(tok, side) {
  const m = /^(\d+)\/(\d+)/.exec(tok);
  if (m) return { cur: +m[1], max: +m[2] };
  if (tok.startsWith('0')) return { cur: 0, max: state.hp[side]?.max ?? 100 };
  return null;
}

function handleOmniLine(line) {
  const parts = line.split('|');
  const cmd = parts[1];

  const sideOf = (tag) => (tag?.startsWith('p1') ? 'p1' : tag?.startsWith('p2') ? 'p2' : null);

  switch (cmd) {
    case 'turn':
      logLine(`Turno ${parts[2]}`, 'turn');
      break;
    case 'switch':
    case 'drag': {
      const side = sideOf(parts[2]);
      const hp = parseHpToken(parts[4], side);
      if (side && hp) setHpBar(side, hp.cur, hp.max);
      break;
    }
    case 'move':
      logLine(`<b>${shortName(parts[2])}</b> usou <b>${parts[3]}</b>!`);
      break;
    case '-damage':
    case '-heal': {
      const side = sideOf(parts[2]);
      const hp = parseHpToken(parts[3], side);
      if (side && hp) setHpBar(side, hp.cur, hp.max);
      if (side) flash(side === 'p1' ? state.playerObj : state.foeObj);
      break;
    }
    case '-crit':
      logLine('Foi um golpe crítico!', 'crit');
      break;
    case '-supereffective':
      logLine('É super efetivo!', 'dmg');
      break;
    case '-resisted':
      logLine('Não foi muito eficaz...');
      break;
    case '-immune':
      logLine(`Não afetou ${shortName(parts[2])}...`);
      break;
    case '-miss':
      logLine(`${shortName(parts[2])} errou o golpe!`);
      break;
    case '-fail':
      logLine('Mas falhou!');
      break;
    case '-status':
      logLine(`${shortName(parts[2])} ficou ${STATUS_PT[parts[3]] ?? parts[3]}!`);
      break;
    case '-curestatus':
      logLine(`${shortName(parts[2])} se recuperou.`);
      break;
    case '-boost':
      logLine(`${STAT_PT[parts[3]] ?? parts[3]} de ${shortName(parts[2])} subiu!`);
      break;
    case '-unboost':
      logLine(`${STAT_PT[parts[3]] ?? parts[3]} de ${shortName(parts[2])} caiu!`);
      break;
    case '-ability':
      logLine(`${shortName(parts[2])} ativou ${parts[3]}!`);
      break;
    case '-weather':
      if (parts[3] !== '[upkeep]') logLine(`O clima mudou: ${parts[2]}.`);
      break;
    case 'cant':
      logLine(`${shortName(parts[2])} não conseguiu se mover${parts[3] ? ' (' + (REASON_PT[parts[3]] ?? parts[3]) + ')' : ''}!`);
      break;
    case 'faint': {
      const side = sideOf(parts[2]);
      logLine(`${shortName(parts[2])} desmaiou!`, 'dmg');
      if (side) { setHpBar(side, 0, state.hp[side]?.max ?? 100); faintAway(side === 'p1' ? state.playerObj : state.foeObj); }
      break;
    }
    case 'win':
      logLine(`${parts[2]} venceu a batalha!`, 'win');
      endBattle(parts[2] === 'Você' ? 'win' : 'lose');
      break;
    case 'tie':
      // os dois desmaiam no mesmo turno -- ex.: o ultimo golpe e um Explosion
      // que derruba o oponente e o proprio usuario junto
      logLine('Os dois desmaiaram ao mesmo tempo. Empate!', 'win');
      endBattle('tie');
      break;
  }
}

function renderMoves(request) {
  const box = $('#moves');
  if (!request || request.wait || state.over) {
    box.innerHTML = `<h3>Ação</h3><p class="waiting">${state.over ? '' : 'aguardando o oponente…'}</p>`;
    return;
  }
  if (request.forceSwitch) {
    state.stream.write('p1', 'switch 1');
    return;
  }
  const moves = request.active?.[0]?.moves ?? [];
  box.innerHTML = `<h3>Escolha o golpe</h3><div class="movegrid">${
    moves.map((m, i) => {
      const info = state.p1Set.moveInfos[m.id];
      const type = info?.type ?? 'Normal';
      return `<button class="movebtn" data-i="${i + 1}" ${m.disabled ? 'disabled' : ''}>
        <span class="mv-name">${m.move}</span>
        <span class="mv-meta">
          <span class="type" style="background:${typeColor(type)}">${TYPE_PT[type.toLowerCase()] ?? type}</span>
          <span class="pp">${m.pp}/${m.maxpp} PP</span>
        </span>
      </button>`;
    }).join('')
  }</div>`;
  for (const btn of box.querySelectorAll('.movebtn')) {
    btn.onclick = () => {
      state.stream.write('p1', `move ${btn.dataset.i}`);
      box.innerHTML = `<h3>Ação</h3><p class="waiting">aguardando o oponente…</p>`;
    };
  }
}

function endBattle(result) {
  state.over = true;
  const b = $('#banner');
  b.hidden = false;
  const title = result === 'tie' ? 'Empate!' : result === 'win' ? 'Você venceu!' : 'Você perdeu!';
  const cls = result === 'tie' ? '' : result;
  b.innerHTML = `
    <div class="title ${cls}">${title}</div>
    <button id="rematch">Batalhar de novo</button>`;
  $('#rematch').onclick = () => location.reload();
}

async function startBattle(p1species, p2species) {
  $('#setup').hidden = true;
  $('#arena-screen').hidden = false;
  resize();

  const [set1, set2] = await Promise.all([buildRandomSet(p1species.name), buildRandomSet(p2species.name)]);
  state.p1Set = set1;
  state.p2Set = set2;

  setNameplate('p1', p1species.name, 50);
  setNameplate('p2', p2species.name, 50);

  const [playerObj, foeObj] = await Promise.all([
    loadCombatant(p1species.variants[0].file, -1.9, 1.6),
    loadCombatant(p2species.variants[0].file, 1.9, -1.4),
  ]);
  state.playerObj = playerObj;
  state.foeObj = foeObj;

  const battleStream = new BattleStreams.BattleStream();
  const streams = BattleStreams.getPlayerStreams(battleStream);
  state.stream = { write: (side, cmd) => streams[side].write(cmd) };

  (async () => {
    for await (const chunk of streams.omniscient) {
      for (const line of chunk.split('\n')) if (line.startsWith('|')) handleOmniLine(line);
    }
  })();

  (async () => {
    for await (const chunk of streams.p1) {
      const req = chunk.split('\n').find((l) => l.startsWith('|request|'));
      if (!req) continue;
      renderMoves(JSON.parse(req.slice('|request|'.length)));
    }
  })();

  (async () => {
    for await (const chunk of streams.p2) {
      const req = chunk.split('\n').find((l) => l.startsWith('|request|'));
      if (!req) continue;
      const data = JSON.parse(req.slice('|request|'.length));
      if (data.wait) continue;
      if (data.forceSwitch) { streams.p2.write('switch 1'); continue; }
      const options = data.active[0].moves;
      const usable = options.map((m, i) => ({ m, i })).filter(({ m }) => !m.disabled);
      const pick = (usable.length ? usable : options.map((m, i) => ({ m, i })))[
        Math.floor(Math.random() * (usable.length || options.length))
      ];
      streams.p2.write(`move ${pick.i + 1}`);
    }
  })();

  streams.omniscient.write(`>start ${JSON.stringify({ formatid: 'gen3customgame' })}`);
  streams.omniscient.write(`>player p1 ${JSON.stringify({ name: 'Você', team: Teams.pack([set1]) })}`);
  streams.omniscient.write(`>player p2 ${JSON.stringify({ name: p2species.name, team: Teams.pack([set2]) })}`);

  window.__battle = { THREE, scene, camera, renderer, controls, state };
}

$('#start-battle').onclick = () => {
  if (picks.p1 && picks.p2) startBattle(picks.p1, picks.p2);
};
