// Testa viewer/battle.html de ponta a ponta em Chrome headless: escolhe dois
// Pokemon, inicia a luta, clica golpes ate ter um vencedor, tira screenshots e
// confirma que HP/log realmente mudaram (nao so "carregou sem erro").
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/battle.html';
const outDir = process.argv[3] ?? 'C:/Users/CARLOS~1/AppData/Local/Temp/battle';
fs.mkdirSync(outDir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });

const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForSelector('#randomize', { timeout: 20000 });

await page.click('#randomize');
const chosen = await page.evaluate(() => ({
  p1: document.querySelector('.picker[data-side="p1"] .chosen b')?.textContent,
  p2: document.querySelector('.picker[data-side="p2"] .chosen b')?.textContent,
}));
console.log('sorteados:', chosen);

await page.click('#start-battle');
await page.waitForFunction(() => window.__battle?.state?.playerObj && window.__battle?.state?.foeObj,
  { timeout: 30000 });
await new Promise((r) => setTimeout(r, 600));
await page.screenshot({ path: path.join(outDir, '1_inicio.png') });

const hpBefore = await page.evaluate(() => window.__battle.state.hp);
console.log('HP inicial:', hpBefore);

let turns = 0;
let winnerShown = false;
for (let i = 0; i < 40 && !winnerShown; i++) {
  winnerShown = await page.evaluate(() => !document.getElementById('banner').hidden);
  if (winnerShown) break;

  const clicked = await page.evaluate(() => {
    const btn = document.querySelector('.movebtn:not(:disabled)');
    if (btn) { btn.click(); return true; }
    return false;
  });
  if (clicked) turns++;
  await new Promise((r) => setTimeout(r, 350));
}

await new Promise((r) => setTimeout(r, 500));
await page.screenshot({ path: path.join(outDir, '2_meio.png') });

// espera o banner de vitoria aparecer (pode levar mais alguns ciclos)
for (let i = 0; i < 20; i++) {
  winnerShown = await page.evaluate(() => !document.getElementById('banner').hidden);
  if (winnerShown) break;
  const clicked = await page.evaluate(() => {
    const btn = document.querySelector('.movebtn:not(:disabled)');
    if (btn) { btn.click(); return true; }
    return false;
  });
  await new Promise((r) => setTimeout(r, 350));
}

const hpAfter = await page.evaluate(() => window.__battle.state.hp);
const logCount = await page.evaluate(() => document.getElementById('log').children.length);
const bannerText = await page.evaluate(() => document.getElementById('banner').innerText);

await page.screenshot({ path: path.join(outDir, '3_fim.png') });

console.log(`\ngolpes clicados: ${turns}`);
console.log('HP final:', hpAfter);
console.log('linhas no log:', logCount);
console.log('banner:', winnerShown ? bannerText.replace('\n', ' | ') : 'NAO APARECEU (suspeito)');

const hpChanged = JSON.stringify(hpBefore) !== JSON.stringify(hpAfter);
console.log(hpChanged ? 'OK: HP mudou durante a luta' : 'SUSPEITO: HP identico do inicio ao fim');
console.log(logCount > 3 ? 'OK: log populado' : 'SUSPEITO: log quase vazio');
console.log(winnerShown ? 'OK: banner de vencedor apareceu' : 'FALHOU: batalha nao terminou em 60 golpes');

await browser.close();
if (errors.length) { console.log('\nerros de console/pagina:'); for (const e of [...new Set(errors)]) console.log('  ' + e); }
else console.log('\nnenhum erro de console/pagina.');
console.log('\nscreenshots em', outDir);
