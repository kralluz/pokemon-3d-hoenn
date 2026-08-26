// Anda pelo mapa em varias direcoes e tira screenshots em cada ponto, pra achar
// qualquer bug visual real: decor flutuando, z-fighting, chao sumindo, etc.
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/world.html';
const outDir = process.argv[3] ?? 'C:/Users/CARLOS~1/AppData/Local/Temp/explore';
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800 });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => document.getElementById('loading').hidden && window.__world, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 500));
await page.screenshot({ path: path.join(outDir, '00_start.png') });

async function walk(key, ms, label) {
  await page.keyboard.down('ShiftLeft');
  await page.keyboard.down(key);
  await new Promise((r) => setTimeout(r, ms));
  await page.keyboard.up(key);
  await page.keyboard.up('ShiftLeft');
  await new Promise((r) => setTimeout(r, 300));
  const pos = await page.evaluate(() => {
    const p = window.__world.person.pivot.position;
    return { x: +p.x.toFixed(2), z: +p.z.toFixed(2) };
  });
  await page.screenshot({ path: path.join(outDir, label + '.png') });
  console.log(label, 'posicao:', pos);
}

await walk('KeyW', 2500, '01_norte');
await walk('KeyD', 2500, '02_leste');
await walk('KeyS', 3000, '03_sul');
await walk('KeyA', 3000, '04_oeste');
await walk('KeyW', 4000, '05_borda_da_floresta');

// orbita bastante pra ver o cenario de varios angulos
const box = await page.$('#canvas');
const bb = await box.boundingBox();
await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
await page.mouse.down();
await page.mouse.move(bb.x + bb.width / 2 + 500, bb.y + bb.height / 2 + 120, { steps: 25 });
await page.mouse.up();
await new Promise((r) => setTimeout(r, 400));
await page.screenshot({ path: path.join(outDir, '06_orbita.png') });

await browser.close();
if (errors.length) { console.log('\nerros:'); for (const e of [...new Set(errors)]) console.log('  ' + e); }
else console.log('\nnenhum erro de console/pagina durante toda a exploracao.');
console.log('\nscreenshots em', outDir);
