// Gera as miniaturas da lista (viewer/thumbs/<id>.png) renderizando cada modelo
// no proprio viewer, em Chrome headless. Serve tambem como teste de cobertura:
// se algum modelo nao renderizar, aparece aqui.
//
// Uso: node tools/thumbs.mjs [baseURL] [--force]
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv.find((a) => a.startsWith('http')) ?? 'http://localhost:8099/viewer/';
const force = process.argv.includes('--force');
const OUT = path.join('viewer', 'thumbs');
const SIZE = 400;

fs.mkdirSync(OUT, { recursive: true });
const data = JSON.parse(fs.readFileSync(path.join('viewer', 'models.json'), 'utf8'));
const jobs = data.species.flatMap((s) => s.variants.map((v) => ({ id: v.id, name: s.name })));

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
         '--hide-scrollbars', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: SIZE, height: SIZE, deviceScaleFactor: 2 });

const fails = [];
page.on('pageerror', (e) => fails.push('pageerror: ' + e.message));

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForFunction(() => window.__viewer && document.querySelectorAll('#list li').length > 0,
  { timeout: 30000 });

// esconde a interface e o fundo para sobrar so o modelo, com alpha
await page.addStyleTag({ content: `
  #sidebar, #controls, #info, #stats, #hint, #loading, #error { display: none !important; }
  html, body { background: transparent !important; }
  #stage { width: 100vw; }
` });
await page.evaluate(() => { window.__viewer.grid.visible = false; window.__viewer.controls.autoRotate = false; });

let done = 0, skipped = 0;
for (const job of jobs) {
  const file = path.join(OUT, `${job.id}.png`);
  if (!force && fs.existsSync(file)) { skipped++; continue; }

  const ok = await page.evaluate(async (id) => {
    location.hash = id;
    const t0 = Date.now();
    while (Date.now() - t0 < 45000) {
      await new Promise((r) => setTimeout(r, 120));
      const loaded = document.getElementById('loading').hidden
        && window.__viewer.root.children.length > 0
        && location.hash.slice(1) === id;
      if (loaded) break;
    }
    const v = window.__viewer;
    const obj = v.root.children[0];
    if (!obj) return false;
    // angulo 3/4 fixo, igual para todos, e reenquadra para a janela quadrada
    v.fitCamera(obj);
    const d = v.camera.position.distanceTo(v.controls.target);
    v.camera.position.set(
      v.controls.target.x + d * 0.42,
      v.controls.target.y + d * 0.22,
      v.controls.target.z + d * 0.88);
    v.camera.lookAt(v.controls.target);
    v.controls.update();
    await new Promise((r) => requestAnimationFrame(r));
    return true;
  }, job.id);

  if (!ok) { fails.push(`${job.id}: nao carregou`); continue; }
  await new Promise((r) => setTimeout(r, 220));   // deixa as texturas assentarem

  const el = await page.$('#canvas');
  await el.screenshot({ path: file, omitBackground: true });

  done++;
  if (done % 20 === 0) console.log(`  ${done}/${jobs.length - skipped}…`);
}

await browser.close();
console.log(`\nminiaturas geradas: ${done}  (puladas, ja existiam: ${skipped})`);
if (fails.length) {
  console.log('falhas:');
  for (const f of [...new Set(fails)]) console.log('  ' + f);
  process.exitCode = 1;
} else {
  console.log('todos os modelos renderizaram.');
}
