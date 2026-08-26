import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const $ = (id) => document.getElementById(id);
const ENV = '../assets/environment/';
const CHAR = '../assets/character/';
const GROUND_RADIUS = 48;

// -------------------------------------------------------------- cena base

const canvas = $('canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8fd6ea);
scene.fog = new THREE.Fog(0x8fd6ea, 35, 90);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 300);

const sun = new THREE.DirectionalLight(0xfff3d6, 2.4);
sun.position.set(18, 28, 12);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -35;
sun.shadow.camera.right = 35;
sun.shadow.camera.top = 35;
sun.shadow.camera.bottom = -35;
sun.shadow.camera.far = 80;
sun.shadow.bias = -0.0015;
scene.add(sun);
scene.add(new THREE.HemisphereLight(0xbfe3ff, 0x5b7a4a, 1.15));

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(GROUND_RADIUS, 64),
  new THREE.MeshStandardMaterial({ color: 0x6fb85a, roughness: 1 }),
);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const world = new THREE.Group();
scene.add(world);

// -------------------------------------------------------------- camera free-look (pointer lock)
//
// O mouse controla a camera direto, sem precisar segurar botao: clique no
// canvas trava o cursor (Pointer Lock API), mover o mouse gira a camera ao
// redor do jogador, scroll da zoom. Esc ou perder o foco destrava sozinho
// (padrao do navegador).

const MOUSE_SENS = 0.0024;
const MIN_DIST = 3.5, MAX_DIST = 14;
const MIN_PITCH = -1.3, MAX_PITCH = -0.05;   // radianos; 0 = horizonte, negativo = olhando de cima

let camYaw = 0;
let camPitch = -0.5;
let camDistance = 7;
const camTarget = new THREE.Vector3(0, 1.1, 4);

canvas.style.cursor = 'grab';
canvas.addEventListener('click', () => canvas.requestPointerLock());
document.addEventListener('pointerlockchange', () => {
  const locked = document.pointerLockElement === canvas;
  canvas.style.cursor = locked ? 'none' : 'grab';
  $('lock-hint').hidden = locked;
});
document.addEventListener('mousemove', (e) => {
  if (document.pointerLockElement !== canvas) return;
  camYaw -= e.movementX * MOUSE_SENS;
  camPitch = Math.max(MIN_PITCH, Math.min(MAX_PITCH, camPitch - e.movementY * MOUSE_SENS));
});
canvas.addEventListener('wheel', (e) => {
  camDistance = Math.max(MIN_DIST, Math.min(MAX_DIST, camDistance + e.deltaY * 0.012));
  e.preventDefault();
}, { passive: false });

/** Recalcula a posicao da camera a partir de yaw/pitch/distancia -- sempre em orbita do alvo. */
function updateCamera(pivotPos, dt) {
  camTarget.lerp(new THREE.Vector3(pivotPos.x, 1.1, pivotPos.z), 1 - Math.pow(0.0001, dt));
  const cp = Math.cos(camPitch);
  const offset = new THREE.Vector3(
    Math.sin(camYaw) * cp,
    -Math.sin(camPitch),
    Math.cos(camYaw) * cp,
  ).multiplyScalar(camDistance);
  camera.position.copy(camTarget).add(offset);
  camera.lookAt(camTarget);
}

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

// -------------------------------------------------------------- cenario

const gltfLoader = new GLTFLoader();
const fbxLoader = new FBXLoader();

async function loadDecor(names) {
  const protos = {};
  await Promise.all(names.map(async (name) => {
    const gltf = await gltfLoader.loadAsync(ENV + name);
    const proto = gltf.scene;
    proto.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      // os GLB da Kenney Nature Kit nao gravam metallicFactor -- o padrao do
      // glTF pra isso e 1.0 (100% metalico). Sem environment map pra refletir,
      // um material metalico so mostra especular; em certos angulos o brilho
      // cai a zero e o objeto renderiza solido preto. Sao assets flat-color,
      // nunca deveriam ser metalicos.
      for (const m of [].concat(o.material)) {
        if (m.isMeshStandardMaterial) { m.metalness = 0; m.roughness = 1; m.needsUpdate = true; }
      }
    });
    protos[name] = proto;
  }));
  return protos;
}

function place(proto, x, z, { scale = 1, yaw = Math.random() * Math.PI * 2 } = {}) {
  const inst = proto.clone(true);
  inst.position.set(x, 0, z);
  inst.rotation.y = yaw;
  inst.scale.setScalar(scale);
  world.add(inst);
  return inst;
}

/** Distribui instancias num anel [rMin, rMax] em volta da origem, evitando amontoar. */
function scatterRing(proto, count, rMin, rMax, opts = {}) {
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + Math.random() * (Math.PI * 2 / count) * 0.6;
    const r = rMin + Math.random() * (rMax - rMin);
    place(proto, Math.cos(a) * r, Math.sin(a) * r, {
      scale: (opts.scaleMin ?? 0.85) + Math.random() * ((opts.scaleMax ?? 1.25) - (opts.scaleMin ?? 0.85)),
      ...opts,
    });
  }
}

async function buildScene() {
  const trees = ['tree_default.glb', 'tree_detailed.glb', 'tree_oak.glb', 'tree_pineDefaultA.glb', 'tree_pineRoundA.glb'];
  const decorNames = [
    ...trees, 'tree_palm.glb', 'tree_pineGroundA.glb', 'tree_pineGroundB.glb',
    'rock_largeA.glb', 'rock_largeB.glb', 'rock_smallA.glb', 'rock_smallB.glb', 'rock_tallA.glb',
    'grass.glb', 'grass_large.glb', 'flower_purpleA.glb', 'flower_redA.glb', 'flower_yellowA.glb',
    'mushroom_red.glb', 'mushroom_tan.glb', 'log.glb', 'log_stack.glb',
    'stump_round.glb', 'stump_squareDetailed.glb', 'fence_simple.glb', 'fence_gate.glb',
    'bridge_wood.glb', 'bridge_side_wood.glb', 'path_stone.glb', 'path_wood.glb',
    'ground_pathTile.glb', 'ground_pathStraight.glb', 'ground_pathCorner.glb',
    'ground_riverStraight.glb', 'ground_riverCorner.glb', 'ground_riverTile.glb',
  ];
  const P = await loadDecor(decorNames);

  // borda de floresta -- deixa o centro livre para andar
  for (const name of trees) scatterRing(P[name], 8, 32, GROUND_RADIUS - 3, { scaleMin: 1.1, scaleMax: 1.7 });
  scatterRing(P['tree_palm.glb'], 5, 30, 42, { scaleMin: 1, scaleMax: 1.4 });
  scatterRing(P['rock_largeA.glb'], 4, 34, 44);
  scatterRing(P['rock_largeB.glb'], 4, 30, 40);

  // clareira: pedras, flores, cogumelos e tocos espalhados
  const meadow = ['rock_smallA.glb', 'rock_smallB.glb', 'flower_purpleA.glb', 'flower_redA.glb',
    'flower_yellowA.glb', 'mushroom_red.glb', 'mushroom_tan.glb', 'grass.glb', 'grass_large.glb'];
  for (const name of meadow) scatterRing(P[name], 10, 6, 24, { scaleMin: 0.7, scaleMax: 1.3 });

  // um riacho decorativo cruzando um canto
  const river = [
    [-14, -20, 'ground_riverStraight.glb', Math.PI / 2],
    [-10, -20, 'ground_riverStraight.glb', Math.PI / 2],
    [-6, -20, 'ground_riverCorner.glb', 0],
    [-6, -16, 'ground_riverStraight.glb', 0],
    [-6, -12, 'ground_riverTile.glb', 0],
  ];
  for (const [x, z, name, yaw] of river) place(P[name], x, z, { scale: 1, yaw });
  place(P['bridge_wood.glb'], -6, -20, { scale: 1, yaw: Math.PI / 2 });

  // trilha de pedras saindo do centro, mais uma cerca e tocos perto do spawn
  for (let i = 1; i <= 6; i++) place(P['path_stone.glb'], 2.2 * i, 1.5 * i * 0.3, { scale: 1, yaw: 0.2 });
  place(P['stump_round.glb'], -3, 2, { scale: 1.2 });
  place(P['log.glb'], -4.5, 3.5, { scale: 1, yaw: 1.1 });
  place(P['fence_simple.glb'], 6, 6, { scale: 1, yaw: 0.4 });
  place(P['fence_gate.glb'], 8, 5, { scale: 1, yaw: 0.4 });
}

// -------------------------------------------------------------- personagem

const ANIM_FILES = { idle: 'idle.fbx', run: 'run.fbx', jump: 'jump.fbx' };

async function loadCharacter() {
  const char = await fbxLoader.loadAsync(CHAR + 'character.fbx');
  char.scale.setScalar(0.00465);   // bbox crua ~376 unidades de altura -> ~1.75m
  char.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

  const tex = await new THREE.TextureLoader().loadAsync(CHAR + 'character_skin.png');
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.flipY = false;   // texturas de FBX ja vem com a orientacao certa
  char.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) {
      m.map = tex;
      m.needsUpdate = true;
    }
  });

  const clips = {};
  for (const [key, file] of Object.entries(ANIM_FILES)) {
    const g = await fbxLoader.loadAsync(CHAR + file);
    clips[key] = g.animations.find((a) => !/targeting|pose/i.test(a.name)) ?? g.animations[0];
  }

  const pivot = new THREE.Group();
  pivot.add(char);
  world.add(pivot);

  const mixer = new THREE.AnimationMixer(char);
  const actions = Object.fromEntries(Object.entries(clips).map(([k, c]) => [k, mixer.clipAction(c)]));
  actions.jump.setLoop(THREE.LoopOnce);
  actions.jump.clampWhenFinished = true;
  let current = actions.idle.play();

  function setAction(name, fade = 0.15) {
    if (current === actions[name]) return;
    const next = actions[name].reset().fadeIn(fade).play();
    current.fadeOut(fade);
    current = next;
  }

  return { pivot, mixer, actions, setAction };
}

// -------------------------------------------------------------- controle e movimento

const keys = new Set();
addEventListener('keydown', (e) => {
  keys.add(e.code);
  if (e.code === 'Space') e.preventDefault();
});
addEventListener('keyup', (e) => keys.delete(e.code));
addEventListener('blur', () => keys.clear());

const WALK_SPEED = 3.2;
const RUN_SPEED = 6.4;
const TURN_SPEED = 12;
const forward = new THREE.Vector3();
const right = new THREE.Vector3();
const moveDir = new THREE.Vector3();

function updateCharacter(person, dt) {
  const { pivot, mixer, setAction } = person;

  // direcao "pra frente" derivada direto do yaw da camera -- mesma convencao
  // usada em updateCamera() (offset.z = cos(yaw), offset.x = sin(yaw), e a
  // camera fica ATRAS do alvo nessa direcao, entao "pra frente" e o inverso)
  forward.set(-Math.sin(camYaw), 0, -Math.cos(camYaw));
  right.crossVectors(forward, new THREE.Vector3(0, 1, 0));

  moveDir.set(0, 0, 0);
  if (keys.has('KeyW') || keys.has('ArrowUp')) moveDir.add(forward);
  if (keys.has('KeyS') || keys.has('ArrowDown')) moveDir.sub(forward);
  if (keys.has('KeyD') || keys.has('ArrowRight')) moveDir.add(right);
  if (keys.has('KeyA') || keys.has('ArrowLeft')) moveDir.sub(right);

  const moving = moveDir.lengthSq() > 0.0001;

  if (moving) {
    moveDir.normalize();
    const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? RUN_SPEED : WALK_SPEED;
    const next = pivot.position.clone().addScaledVector(moveDir, speed * dt);
    if (next.length() < GROUND_RADIUS - 1.5) pivot.position.copy(next);

    const targetYaw = Math.atan2(moveDir.x, moveDir.z);
    let diff = targetYaw - pivot.rotation.y;
    diff = Math.atan2(Math.sin(diff), Math.cos(diff));
    pivot.rotation.y += diff * Math.min(1, TURN_SPEED * dt);
  }

  // dispara o pulo ANTES de calcular "jumping" -- senao, no frame do disparo,
  // o bloco idle/run la embaixo roda com o valor antigo (false) e cancela o
  // clip de pulo no mesmo instante em que ele comeca
  if (keys.has('Space') && !person.jumpUntil) {
    person.jumpUntil = performance.now() + 520;
    setAction('jump', 0.05);
  }
  const jumping = !!person.jumpUntil && performance.now() < person.jumpUntil;
  if (person.jumpUntil && !jumping) person.jumpUntil = null;

  if (!jumping) setAction(moving ? 'run' : 'idle');

  mixer.update(dt);
  updateCamera(pivot.position, dt);
}

// -------------------------------------------------------------- boot

function showError(html) {
  $('error').innerHTML = html;
  $('error').hidden = false;
  $('loading').hidden = true;
}

(async function init() {
  resize();
  try {
    const [, person] = await Promise.all([buildScene(), loadCharacter()]);
    $('loading').hidden = true;

    person.pivot.position.set(0, 0, 4);
    camTarget.set(0, 1.1, 4);
    updateCamera(person.pivot.position, 1);   // dt=1 crava a camera na posicao final de primeira

    window.__world = { THREE, scene, camera, renderer, world, person, keys, camTarget,
                       setCamYaw: (v) => { camYaw = v; }, setCamPitch: (v) => { camPitch = v; },
                       get camYaw() { return camYaw; }, get camPitch() { return camPitch; },
                       get camDistance() { return camDistance; } };

    const clock = new THREE.Clock();
    renderer.setAnimationLoop(() => {
      resize();
      updateCharacter(person, Math.min(clock.getDelta(), 0.05));
      renderer.render(scene, camera);
    });
  } catch (err) {
    showError(`Não consegui montar o mundo.<br><code>${err.message}</code>`);
    console.error(err);
  }
})();
