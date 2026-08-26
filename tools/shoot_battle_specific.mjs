// Igual shoot_battle.mjs, mas escolhe P1/P2 por nome (busca) em vez de sortear --
// para forcar casos extremos como Wobbuffet/Ditto (movesets quase sem golpe de dano).
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/battle.html';
const name1 = process.argv[3] ?? 'Wobbuffet';
const name2 = process.argv[4] ?? 'Ditto';

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});
const page = await browser.newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
await page.waitForSelector('#randomize', { timeout: 20000 });

async function pick(side, name) {
  await page.type(`.picker[data-side="${side}"] .search`, name, { delay: 10 });
  await new Promise((r) => setTimeout(r, 150));
  await page.click(`.picker[data-side="${side}"] .list li`);
}
await pick('p1', name1);
await pick('p2', name2);

const chosen = await page.evaluate(() => ({
  p1: document.querySelector('.picker[data-side="p1"] .chosen b')?.textContent,
  p2: document.querySelector('.picker[data-side="p2"] .chosen b')?.textContent,
}));
console.log('escolhidos:', chosen);

await page.click('#start-battle');
await page.waitForFunction(() => window.__battle?.state?.playerObj && window.__battle?.state?.foeObj, { timeout: 30000 });
await new Promise((r) => setTimeout(r, 500));

const sets = await page.evaluate(() => ({
  p1: { moves: window.__battle.state.p1Set.moves, ability: window.__battle.state.p1Set.ability },
  p2: { moves: window.__battle.state.p2Set.moves, ability: window.__battle.state.p2Set.ability },
}));
console.log('movesets montados:', JSON.stringify(sets));

let winnerShown = false;
for (let i = 0; i < 80 && !winnerShown; i++) {
  winnerShown = await page.evaluate(() => !document.getElementById('banner').hidden);
  if (winnerShown) break;
  await page.evaluate(() => document.querySelector('.movebtn:not(:disabled)')?.click());
  await new Promise((r) => setTimeout(r, 300));
}

const hpAfter = await page.evaluate(() => window.__battle.state.hp);
const bannerText = await page.evaluate(() => document.getElementById('banner').innerText);
console.log('HP final:', hpAfter);
console.log('resultado:', winnerShown ? bannerText.split('\n')[0] : 'NAO TERMINOU em 80 rodadas (pode ser loop de Struggle infinito, ok para status puro)');

await browser.close();
console.log(errors.length ? '\nerros:\n' + [...new Set(errors)].join('\n') : '\nnenhum erro.');
