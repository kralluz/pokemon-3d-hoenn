// Verifica, fora do navegador, que o FBXLoader do three.js consegue parsear os
// modelos baixados: geometria, esqueleto, texturas e clipes de animacao.
//
// Uso: node tools/verify_fbx.mjs [pasta ...]      (sem args = varre tudo)
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// stubs minimos de DOM: o TextureLoader do three precisa de document/Image
globalThis.document = {
  createElementNS: () => ({ addEventListener() {}, removeEventListener() {}, style: {}, set src(_v) {} }),
};
globalThis.self = globalThis;

const loaderURL = pathToFileURL(path.resolve('viewer/vendor/jsm/loaders/FBXLoader.js'));
const { FBXLoader } = await import(loaderURL.href);

const ROOT = 'assets/gen3';
let dirs = process.argv.slice(2);
if (!dirs.length) {
  dirs = fs.readdirSync(ROOT).filter((d) => fs.statSync(path.join(ROOT, d)).isDirectory());
}

let ok = 0;
const problems = [];
const verbose = dirs.length <= 10;

for (const dir of dirs) {
  const folder = path.join(ROOT, dir);
  const fbx = fs.readdirSync(folder).find((f) => f.toLowerCase().endsWith('.fbx'));
  if (!fbx) { problems.push([dir, 'sem .fbx']); continue; }

  const buf = fs.readFileSync(path.join(folder, fbx));
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);

  try {
    const group = new FBXLoader().parse(ab, folder.replace(/\\/g, '/') + '/');
    let meshes = 0, skinned = 0, bones = 0, verts = 0;
    const mats = new Set(), texs = new Set();
    group.traverse((o) => {
      if (o.isBone) bones++;
      if (o.isSkinnedMesh) skinned++;
      if (o.isMesh) {
        meshes++;
        verts += o.geometry.attributes.position.count;
        for (const m of [].concat(o.material)) {
          mats.add(m.type);
          for (const slot of ['map', 'normalMap', 'emissiveMap']) {
            const url = m[slot]?.image?.src || m[slot]?.name;
            if (url) texs.add(String(url).split('/').pop());
          }
        }
      }
    });

    if (!meshes) { problems.push([dir, 'nenhuma malha']); continue; }
    ok++;
    if (verbose) {
      console.log(
        `${dir.padEnd(28)} malhas=${meshes} (skinned ${skinned}) ossos=${bones} ` +
        `verts=${verts} anims=${group.animations.length} mats=${[...mats].join('/')} texs=${texs.size}`
      );
      if (group.animations.length) {
        const list = group.animations.slice(0, 5).map((a) => `${a.name}(${a.duration.toFixed(2)}s)`);
        console.log(`   ${list.join(', ')} ...`);
      }
    }
  } catch (e) {
    problems.push([dir, e.message.slice(0, 90)]);
  }
}

console.log(`\nparseados com sucesso: ${ok}/${dirs.length}`);
if (problems.length) {
  console.log('problemas:');
  for (const [d, m] of problems) console.log(`  ${d.padEnd(28)} ${m}`);
  process.exitCode = 1;
}
