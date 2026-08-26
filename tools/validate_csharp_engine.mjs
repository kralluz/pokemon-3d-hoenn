// Valida o motor C# contra o @smogon/calc -- o calculador de dano oficial da
// comunidade competitiva, mesma familia do Pokemon Showdown.
//
// Gera N casos aleatorios (atacante, defensor, golpe), roda os dois lados e
// compara a faixa de dano (roll minimo 85 e maximo 100). Golpes com logica
// propria em JS (Counter, Solar Beam...) sao pulados: nao foram portados.
//
// Uso: node tools/validate_csharp_engine.mjs [n]
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { calculate, Generations, Pokemon, Move } from '@smogon/calc';

const N = Number(process.argv[2] ?? 300);
const DATA = path.join('csharp', 'BattleSim', 'data');
const EXE = path.join('csharp', 'BattleSim', 'bin', 'Debug', 'net9.0', 'BattleSim.exe');

const species = JSON.parse(fs.readFileSync(path.join(DATA, 'species.json'), 'utf8'));
const moves = JSON.parse(fs.readFileSync(path.join(DATA, 'moves.json'), 'utf8'));
const moveById = Object.fromEntries(moves.map((m) => [m.id, m]));
const gen = Generations.get(3);

// so golpes de dano SEM logica propria em JS -- o resto nao foi portado
const testable = moves.filter((m) => m.category !== 'Status' && m.basePower > 0
  && !m.hasCallback && !m.ohko && !m.multihit);

console.log(`golpes testaveis: ${testable.length} de ${moves.length} ` +
  `(${moves.length - testable.length} pulados: status, callback, OHKO ou multi-hit)`);

// ---------------------------------------------------------------- gera casos

const rng = (n) => Math.floor(Math.random() * n);
const cases = [];
const seen = new Set();
let guard = 0;
while (cases.length < N && guard++ < N * 40) {
  const atk = species[rng(species.length)];
  const def = species[rng(species.length)];
  const legal = atk.legalMoves.filter((id) => testable.some((t) => t.id === id));
  if (!legal.length) continue;
  const move = legal[rng(legal.length)];
  const key = `${atk.name}|${def.name}|${move}`;
  if (seen.has(key)) continue;
  seen.add(key);
  cases.push({ attacker: atk.name, defender: def.name, move });
}
console.log(`casos gerados: ${cases.length}\n`);

const casesFile = path.join(process.env.TEMP ?? '.', 'calc_cases.json');
fs.writeFileSync(casesFile, JSON.stringify(cases));

// ---------------------------------------------------------------- roda o C#

const raw = execFileSync(EXE, ['calc', casesFile], { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
const csharp = JSON.parse(raw.slice(raw.indexOf('[')));

// ---------------------------------------------------------------- compara

let ok = 0;
const mismatches = [];
const statMismatches = [];

for (let i = 0; i < cases.length; i++) {
  const c = cases[i];
  const cs = csharp[i];
  const md = moveById[c.move];

  // mesmo set do lado C#: nivel 50, IV 31, EV 0, natureza neutra.
  // Habilidade fixada em Pressure (inerte para dano) dos dois lados: o motor C#
  // ainda nao implementa habilidades, entao deixar a habilidade real ativa no
  // calc compararia coisas diferentes (Pure Power dobra ataque, Thick Fat corta
  // dano de gelo/fogo...). Habilidades sao um item conhecido em aberto.
  const opts = { level: 50, ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
                 evs: { hp: 0, atk: 0, def: 0, spa: 0, spd: 0, spe: 0 }, nature: 'Serious',
                 ability: 'Pressure' };
  let result;
  try {
    result = calculate(gen, new Pokemon(gen, c.attacker, opts), new Pokemon(gen, c.defender, opts),
      new Move(gen, md.name, { species: c.attacker }));
  } catch (e) {
    mismatches.push({ ...c, erro: 'calc falhou: ' + e.message });
    continue;
  }

  const rolls = result.damage;
  const arr = Array.isArray(rolls) ? rolls.flat() : [rolls];
  const expMin = Math.min(...arr), expMax = Math.max(...arr);

  // HP maximo tambem precisa bater -- valida a formula de stat, nao so a de dano
  const expHp = result.defender.maxHP();
  if (cs.defHp !== expHp) {
    statMismatches.push({ pokemon: c.defender, csharp: cs.defHp, esperado: expHp });
  }

  if (cs.min === expMin && cs.max === expMax) { ok++; continue; }
  const phys = md.category === 'Physical';
  mismatches.push({
    ...c, csharp: [cs.min, cs.max], esperado: [expMin, expMax],
    statsCs: { atk: phys ? cs.atkStat.atk : cs.atkStat.spa, def: phys ? cs.defStat.def : cs.defStat.spd },
    statsCalc: { atk: phys ? result.attacker.stats.atk : result.attacker.stats.spa,
                 def: phys ? result.defender.stats.def : result.defender.stats.spd },
    tipos: `${c.attacker}[${result.attacker.types}] -> ${c.defender}[${result.defender.types}]`,
  });
}

// ---------------------------------------------------------------- relatorio

const total = cases.length;
console.log(`faixa de dano identica: ${ok}/${total} (${(ok / total * 100).toFixed(1)}%)`);
console.log(`HP maximo divergente:   ${statMismatches.length}`);

if (statMismatches.length) {
  console.log('\nDIVERGENCIA DE STAT (formula de HP):');
  for (const s of statMismatches.slice(0, 5)) console.log('  ', JSON.stringify(s));
}

if (mismatches.length) {
  console.log(`\ndivergencias de dano: ${mismatches.length}`);
  for (const m of mismatches.slice(0, 15)) {
    const md = moveById[m.move];
    console.log(`  ${m.attacker} -> ${m.defender} com ${md?.name ?? m.move} (${md?.type}/${md?.category}, ${md?.basePower}bp)`);
    console.log(`     C#: ${JSON.stringify(m.csharp ?? m.erro)}   esperado: ${JSON.stringify(m.esperado ?? '-')}`);
    if (m.statsCs) console.log(`     stats C#: ${JSON.stringify(m.statsCs)}  calc: ${JSON.stringify(m.statsCalc)}  ${m.tipos}`);
  }
} else {
  console.log('\nnenhuma divergencia.');
}

process.exitCode = mismatches.length || statMismatches.length ? 1 : 0;
