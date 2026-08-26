// Confirma a direcao real de A/D: pressiona so D, mede pra que lado (em relacao
// a direita da camera) o personagem realmente andou.
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/world.html';

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1000, height: 700 });
await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => document.getElementById('loading').hidden && window.__world, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 400));

async function testKey(key) {
  const before = await page.evaluate(() => {
    const w = window.__world;
    const cam = w.camera;
    const fwd = new w.THREE.Vector3(); cam.getWorldDirection(fwd); fwd.y = 0; fwd.normalize();
    const rightExpected = new w.THREE.Vector3().crossVectors(fwd, new w.THREE.Vector3(0, 1, 0));
    return { pos: w.person.pivot.position.clone(), rightExpected };
  });
  await page.keyboard.down(key);
  await new Promise((r) => setTimeout(r, 500));
  await page.keyboard.up(key);
  await new Promise((r) => setTimeout(r, 100));
  const after = await page.evaluate(() => window.__world.person.pivot.position.clone());

  const delta = { x: after.x - before.pos.x, z: after.z - before.pos.z };
  const dot = delta.x * before.rightExpected.x + delta.z * before.rightExpected.z;
  return { delta, dot };
}

const d = await testKey('KeyD');
console.log('tecla D -> delta:', d.delta, '| produto escalar com "direita real da camera":', d.dot.toFixed(3));
console.log(d.dot > 0.1 ? 'CORRETO: D andou para a direita' : d.dot < -0.1 ? 'BUG CONFIRMADO: D andou para a ESQUERDA' : 'inconclusivo');

const a = await testKey('KeyA');
console.log('\ntecla A -> delta:', a.delta, '| produto escalar com "direita real da camera":', a.dot.toFixed(3));
console.log(a.dot < -0.1 ? 'CORRETO: A andou para a esquerda' : a.dot > 0.1 ? 'BUG CONFIRMADO: A andou para a DIREITA' : 'inconclusivo');

await browser.close();
