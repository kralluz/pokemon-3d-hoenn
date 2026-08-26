// Abre o viewer no Chrome headless, navega por alguns Pokemon e salva screenshots.
// Serve para conferir que o render funciona de verdade, sem abrir o navegador na mao.
//
// Uso: node tools/shoot.mjs <baseURL> <pastaSaida> [alvo ...]
//   alvo = numero da dex ou id de variante (ex.: 384, 0254_sceptile_mega)
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8099/viewer/';
const outDir = process.argv[3] ?? 'shots';
const targets = process.argv.slice(4);
if (!targets.length) targets.push('252');

fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
         '--hide-scrollbars', '--no-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 880, deviceScaleFactor: 1 });

const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('requestfailed', (r) => errors.push(`404/fail: ${r.url().split('/').slice(-2).join('/')}`));

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });

// espera o index carregar e a lista aparecer
await page.waitForFunction(() => document.querySelectorAll('#list li').length > 0, { timeout: 30000 });

const summary = [];
for (const t of targets) {
  const before = await page.evaluate(() => document.getElementById('i-name').textContent);
  await page.evaluate((h) => { location.hash = h; }, t);
  // espera o nome trocar (ou ja ser o alvo) E o loading sumir -- so o loading da corrida
  await page.waitForFunction((b) => {
    const n = document.getElementById('i-name').textContent;
    return document.getElementById('loading').hidden && (n !== b || document.getElementById('error').hidden === false);
  }, { timeout: 60000 }, before).catch(() => {});
  await page.waitForFunction(() => document.getElementById('loading').hidden, { timeout: 60000 });
  await new Promise((r) => setTimeout(r, 900)); // deixa texturas e damping assentarem

  const info = await page.evaluate(() => {
    const cv = document.getElementById('canvas');
    const gl = cv.getContext('webgl2') || cv.getContext('webgl');
    return {
      name: document.getElementById('i-name').textContent,
      dex: document.getElementById('i-dex').textContent,
      types: [...document.querySelectorAll('#i-types .type')].map((e) => e.textContent),
      variants: [...document.querySelectorAll('#variants button')].map((e) => e.textContent),
      stats: document.getElementById('stats').innerText.replace(/\n/g, ' | '),
      errorShown: !document.getElementById('error').hidden,
      renderer: gl ? gl.getParameter(gl.VERSION) : 'sem webgl',
    };
  });

  const file = path.join(outDir, `${t}.png`);
  await page.screenshot({ path: file });

  // mede quanto do canvas nao e fundo, para detectar tela vazia
  const shot = await page.screenshot({ clip: { x: 310, y: 0, width: 1130, height: 880 }, encoding: 'binary' });
  fs.writeFileSync(path.join(outDir, `${t}_stage.png`), shot);

  summary.push({ target: t, ...info, file });
  console.log(`${t.padEnd(24)} ${info.dex} ${info.name.padEnd(12)} ${info.types.join('/')} ` +
              `[${info.variants.join(', ')}]  ${info.stats}${info.errorShown ? '  <<< ERRO NA TELA' : ''}`);
}

await browser.close();

console.log(`\nrenderer: ${summary[0]?.renderer}`);
if (errors.length) {
  console.log('\nproblemas no console:');
  for (const e of [...new Set(errors)].slice(0, 20)) console.log('  ' + e);
} else {
  console.log('\nnenhum erro de console ou request.');
}
