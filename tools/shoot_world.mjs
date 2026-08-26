// Testa viewer/world.html em Chrome headless: carrega, simula WASD/espaço, tira
// screenshots antes e depois de andar, e reporta erros de console/rede.
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/world.html';
const outDir = process.argv[3] ?? 'C:/Users/CARLOS~1/AppData/Local/Temp/world';
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800 });

const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('requestfailed', (r) => errors.push(`falha: ${r.url().split('/').slice(-2).join('/')} (${r.failure()?.errorText})`));

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => document.getElementById('loading').hidden && window.__world, { timeout: 60000 })
  .catch(() => {});

if (!(await page.evaluate(() => !!window.__world))) {
  const errText = await page.evaluate(() => document.getElementById('error').innerText).catch(() => '');
  console.log('mundo nao carregou. erro na tela:', errText);
  console.log('erros de console/rede:', errors);
  await page.screenshot({ path: path.join(outDir, 'fail.png') });
  await browser.close();
  process.exit(1);
}

await new Promise((r) => setTimeout(r, 500));
const before = await page.evaluate(() => {
  const p = window.__world.person.pivot.position;
  return { x: p.x, z: p.z };
});
await page.screenshot({ path: path.join(outDir, '1_parado.png') });

// segura W (andar) por 1.2s
await page.keyboard.down('KeyW');
await new Promise((r) => setTimeout(r, 1200));
const midAction = await page.evaluate(() => {
  const w = window.__world;
  const p = w.person.pivot.position;
  return { x: p.x, z: p.z, acao: Object.entries(w.person.actions).find(([, a]) => a.isRunning() && a.weight > 0.5)?.[0] };
});
await page.screenshot({ path: path.join(outDir, '2_andando.png') });
await page.keyboard.up('KeyW');

// corre com shift+W por 1s
await page.keyboard.down('ShiftLeft');
await page.keyboard.down('KeyW');
await new Promise((r) => setTimeout(r, 1000));
await page.keyboard.up('KeyW');
await page.keyboard.up('ShiftLeft');
const afterRun = await page.evaluate(() => {
  const p = window.__world.person.pivot.position;
  return { x: p.x, z: p.z };
});

// pulo
await page.keyboard.down('Space');
await new Promise((r) => setTimeout(r, 120));
await page.keyboard.up('Space');
await new Promise((r) => setTimeout(r, 150));
const midJump = await page.evaluate(() => {
  const w = window.__world;
  return Object.entries(w.person.actions).find(([, a]) => a.isRunning() && a.weight > 0.5)?.[0];
});
await page.screenshot({ path: path.join(outDir, '3_pulando.png') });
await new Promise((r) => setTimeout(r, 500));

// orbita a camera (arrastar botao esquerdo)
const box = await page.$('#canvas');
const bb = await box.boundingBox();
await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
await page.mouse.down();
await page.mouse.move(bb.x + bb.width / 2 + 220, bb.y + bb.height / 2 - 60, { steps: 12 });
await page.mouse.up();
await new Promise((r) => setTimeout(r, 400));
await page.screenshot({ path: path.join(outDir, '4_orbitado.png') });

console.log('posicao inicial:', before);
console.log('acao durante W:', midAction.acao, '| posicao apos 1.2s andando:', { x: +midAction.x.toFixed(2), z: +midAction.z.toFixed(2) });
console.log('posicao apos correr 1s:', { x: +afterRun.x.toFixed(2), z: +afterRun.z.toFixed(2) });
console.log('acao durante o pulo:', midJump);

const distAndando = Math.hypot(midAction.x - before.x, midAction.z - before.z);
const distCorrendo = Math.hypot(afterRun.x - midAction.x, afterRun.z - midAction.z);
console.log(`\ndistancia andando (1.2s): ${distAndando.toFixed(2)}  |  distancia correndo (1.0s): ${distCorrendo.toFixed(2)}`);
console.log(distCorrendo > distAndando ? 'OK: correr e mais rapido que andar' : 'SUSPEITO: correr nao ficou mais rapido');

await browser.close();
if (errors.length) {
  console.log('\nerros de console/rede:');
  for (const e of [...new Set(errors)]) console.log('  ' + e);
} else {
  console.log('\nnenhum erro de console ou rede.');
}
console.log('\nscreenshots em', outDir);
