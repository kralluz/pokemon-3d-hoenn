// Exporta os dados de Gen 3 do @pkmn/sim para JSON, que o motor C# consome.
// Assim as estatisticas, tipos e dados de golpe vem da mesma fonte padrao-ouro
// que o protótipo JS usa -- nada e digitado a mao.
//
// Uso: node tools/export_gen3_data.mjs [saida]
import fs from 'node:fs';
import path from 'node:path';
import { Dex } from '@pkmn/sim';

const out = process.argv[2] ?? path.join('csharp', 'BattleSim', 'data');
fs.mkdirSync(out, { recursive: true });

const gen3 = Dex.forGen(3);
const roster = JSON.parse(fs.readFileSync(path.join('viewer', 'models.json'), 'utf8')).species;

// ---------------------------------------------------------------- especies

const species = [];
const moveIds = new Set();

for (const sp of roster) {
  const s = gen3.species.get(sp.name);
  const ls = await gen3.learnsets.get(s.id);
  const legal = Object.entries(ls?.learnset ?? {})
    .filter(([, srcs]) => srcs.some((x) => x.startsWith('3')))
    .map(([id]) => id);
  for (const id of legal) moveIds.add(id);

  species.push({
    dex: sp.dex,
    id: s.id,
    name: s.name,
    types: s.types,
    baseStats: s.baseStats,
    abilities: Object.values(s.abilities),
    gender: s.gender || '',
    legalMoves: legal,
  });
}

// ---------------------------------------------------------------- golpes

const moves = [];
for (const id of [...moveIds].sort()) {
  const m = gen3.moves.get(id);
  if (!m?.exists) continue;
  moves.push({
    id: m.id,
    name: m.name,
    type: m.type,
    category: m.category,               // Physical | Special | Status
    basePower: m.basePower,
    accuracy: m.accuracy === true ? -1 : m.accuracy,   // -1 = nunca erra
    pp: m.pp,
    priority: m.priority,
    critRatio: m.critRatio ?? 1,
    flags: Object.keys(m.flags ?? {}),
    drain: m.drain ?? null,
    recoil: m.recoil ?? null,
    status: m.status ?? null,
    volatileStatus: m.volatileStatus ?? null,
    boosts: m.boosts ?? null,
    target: m.target,
    secondaries: (m.secondaries ?? []).map((s) => ({
      chance: s.chance ?? null,
      status: s.status ?? null,
      volatileStatus: s.volatileStatus ?? null,
      boosts: s.boosts ?? null,
      self: !!s.self,
    })),
    // normaliza para [min,max] sempre, pra simplificar a leitura no C#
    multihit: m.multihit == null ? null : (Array.isArray(m.multihit) ? m.multihit : [m.multihit, m.multihit]),
    ohko: !!m.ohko,
    willCrit: !!m.willCrit,
    selfSwitch: m.selfSwitch ?? null,
    // sinaliza para o motor C# que este golpe tem logica propria em JS que
    // nao foi portada -- vira dano simples e o teste sabe ignorar
    hasCallback: !!(m.basePowerCallback || m.onHit || m.onTry || m.onModifyMove || m.damageCallback),
  });
}

// ---------------------------------------------------------------- tabela de tipos

const TYPES = ['Normal', 'Fighting', 'Flying', 'Poison', 'Ground', 'Rock', 'Bug', 'Ghost',
  'Steel', 'Fire', 'Water', 'Grass', 'Electric', 'Psychic', 'Ice', 'Dragon', 'Dark'];

const typechart = {};
for (const atk of TYPES) {
  typechart[atk] = {};
  for (const def of TYPES) {
    // gen3.getEffectiveness devolve -1/0/1/2 em escala log2; damageTaken cobre imunidade
    const dt = gen3.types.get(def)?.damageTaken?.[atk];
    let mult;
    if (dt === 3) mult = 0;             // imune
    else if (dt === 1) mult = 2;        // super efetivo
    else if (dt === 2) mult = 0.5;      // resiste
    else mult = 1;
    typechart[atk][def] = mult;
  }
}

// ---------------------------------------------------------------- naturezas

const natures = {};
for (const n of gen3.natures.all()) {
  natures[n.name] = { plus: n.plus ?? null, minus: n.minus ?? null };
}

const write = (name, data) => {
  fs.writeFileSync(path.join(out, name), JSON.stringify(data, null, 1));
  const kb = (fs.statSync(path.join(out, name)).size / 1024).toFixed(0);
  console.log(`  ${name.padEnd(16)} ${kb} KB`);
};

write('species.json', species);
write('moves.json', moves);
write('typechart.json', typechart);
write('natures.json', natures);

const withCb = moves.filter((m) => m.hasCallback).length;
console.log(`\n${species.length} especies, ${moves.length} golpes, ${TYPES.length} tipos, ${Object.keys(natures).length} naturezas`);
console.log(`golpes com logica propria em JS (nao portada): ${withCb} (${(withCb / moves.length * 100).toFixed(0)}%)`);
console.log(`saida: ${out}`);
