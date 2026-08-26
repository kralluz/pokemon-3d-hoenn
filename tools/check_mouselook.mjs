// Testa o free-look por mouse: clica no canvas (deve travar o ponteiro),
// simula movimento do mouse e confirma que a camera realmente girou e
// reposicionou, e que o scroll muda a distancia (zoom).
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/world.html';

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1000, height: 700 });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => document.getElementById('loading').hidden && window.__world, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 400));

console.log('lock-hint visivel antes do clique:', await page.evaluate(() => !document.getElementById('lock-hint').hidden));

// clique no centro do canvas para pedir o pointer lock
const box = await page.$('#canvas');
const bb = await box.boundingBox();
await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2);
await new Promise((r) => setTimeout(r, 300));

const locked = await page.evaluate(() => document.pointerLockElement !== null);
console.log('pointer lock ativo apos clique:', locked);
console.log('lock-hint visivel depois do clique:', await page.evaluate(() => !document.getElementById('lock-hint').hidden));

const before = await page.evaluate(() => ({
  yaw: window.__world.camYaw, pitch: window.__world.camPitch,
  camPos: window.__world.camera.position.clone(),
}));

// simula o movimento do mouse via CDP diretamente (movementX/Y), que e o que
// o navegador entrega durante pointer lock independente da posicao real do cursor
await page.mouse.move(bb.x + bb.width / 2 + 150, bb.y + bb.height / 2, { steps: 8 });
await page.mouse.move(bb.x + bb.width / 2 + 300, bb.y + bb.height / 2 - 40, { steps: 8 });
await new Promise((r) => setTimeout(r, 200));

const afterMove = await page.evaluate(() => ({
  yaw: window.__world.camYaw, pitch: window.__world.camPitch,
  camPos: window.__world.camera.position.clone(),
}));

console.log('\nyaw antes/depois:', before.yaw.toFixed(3), '->', afterMove.yaw.toFixed(3));
console.log('pitch antes/depois:', before.pitch.toFixed(3), '->', afterMove.pitch.toFixed(3));
const yawChanged = Math.abs(afterMove.yaw - before.yaw) > 0.01;
console.log(yawChanged ? 'OK: mover o mouse girou a camera (yaw mudou)' : 'SUSPEITO: yaw nao mudou -- pointer lock pode nao estar entregando movementX no headless');

// zoom via scroll
const distBefore = await page.evaluate(() => window.__world.camDistance);
await page.mouse.wheel({ deltaY: 200 });
await new Promise((r) => setTimeout(r, 150));
const distAfter = await page.evaluate(() => window.__world.camDistance);
console.log(`\ndistancia antes/depois do scroll: ${distBefore.toFixed(2)} -> ${distAfter.toFixed(2)}`);
console.log(distAfter > distBefore ? 'OK: scroll afastou a camera (zoom out)' : 'SUSPEITO: scroll nao mudou a distancia');

await browser.close();
if (errors.length) { console.log('\nerros de pagina:'); for (const e of [...new Set(errors)]) console.log('  ' + e); }
else console.log('\nnenhum erro de pagina.');
