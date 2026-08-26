// Roda partidas sorteadas repetidas vezes ate reproduzir uma que nao termina
// no numero de rodadas esperado, e despeja o log completo + estado da requisicao
// pra diagnosticar.
import puppeteer from 'puppeteer-core';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const base = process.argv[2] ?? 'http://localhost:8080/viewer/battle.html';
const maxAttempts = 12;

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: 'new',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
});

for (let attempt = 1; attempt <= maxAttempts; attempt++) {
  const page = await browser.newPage();
  await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
  await page.waitForSelector('#randomize', { timeout: 20000 });
  await page.click('#randomize');
  const chosen = await page.evaluate(() => ({
    p1: document.querySelector('.picker[data-side="p1"] .chosen b')?.textContent,
    p2: document.querySelector('.picker[data-side="p2"] .chosen b')?.textContent,
  }));
  await page.click('#start-battle');
  await page.waitForFunction(() => window.__battle?.state?.playerObj, { timeout: 30000 });

  let winnerShown = false, clicks = 0, noButtonStreak = 0;
  for (let i = 0; i < 60 && !winnerShown; i++) {
    winnerShown = await page.evaluate(() => !document.getElementById('banner').hidden);
    if (winnerShown) break;
    const clicked = await page.evaluate(() => {
      const btn = document.querySelector('.movebtn:not(:disabled)');
      if (btn) { btn.click(); return true; }
      return false;
    });
    if (clicked) { clicks++; noButtonStreak = 0; } else { noButtonStreak++; }
    await new Promise((r) => setTimeout(r, 300));
  }

  if (winnerShown) {
    console.log(`tentativa ${attempt}: ${chosen.p1} vs ${chosen.p2} -> OK em ${clicks} golpes`);
    await page.close();
    continue;
  }

  console.log(`\n=== REPRODUZIDO na tentativa ${attempt}: ${chosen.p1} vs ${chosen.p2} ===`);
  console.log(`golpes clicados: ${clicks}, rodadas sem botao disponivel: ${noButtonStreak}`);
  console.log('conteudo de #moves agora:', await page.evaluate(() => document.getElementById('moves').innerHTML));
  console.log('HP:', await page.evaluate(() => window.__battle.state.hp));
  console.log('log completo:');
  console.log(await page.evaluate(() => document.getElementById('log').innerText));
  await page.screenshot({ path: 'C:/Users/CARLOS~1/AppData/Local/Temp/stall.png', fullPage: true });
  await page.close();
  break;
}

await browser.close();
