// Anda uma distancia longa numa direcao e mede quanto a POSICAO da camera
// se deslocou -- deve acompanhar o jogador quase 1:1 (a camera e recalculada
// a cada frame a partir de camTarget, que persegue o jogador rapido).
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/world.html';

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => document.getElementById('loading').hidden && window.__world, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 400));

const before = await page.evaluate(() => ({
  cam: window.__world.camera.position.clone(),
  player: window.__world.person.pivot.position.clone(),
}));

await page.keyboard.down('ShiftLeft');
await page.keyboard.down('KeyW');
await new Promise((r) => setTimeout(r, 3000));
await page.keyboard.up('KeyW');
await page.keyboard.up('ShiftLeft');
await new Promise((r) => setTimeout(r, 300));

const after = await page.evaluate(() => ({
  cam: window.__world.camera.position.clone(),
  player: window.__world.person.pivot.position.clone(),
}));

const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
const playerMoved = dist(before.player, after.player);
const camMoved = dist(before.cam, after.cam);
const ratio = camMoved / playerMoved;

console.log('jogador andou:', playerMoved.toFixed(2));
console.log('camera se moveu:', camMoved.toFixed(2), `(${(ratio * 100).toFixed(0)}% do jogador)`);
console.log(ratio > 0.9 ? '\nOK: a camera acompanha o jogador de verdade' : '\nBUG: a camera esta ficando pra tras do alvo');

await browser.close();
