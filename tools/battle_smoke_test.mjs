// Prova de vida do motor de batalha: uma luta Gen 3 completa, Blaziken vs
// Swampert, jogada por comandos de texto via BattleStream. Se isso rodar do
// inicio ao fim sem erro, o @pkmn/sim esta funcionando no projeto.
import { BattleStreams, Teams, Dex } from '@pkmn/sim';

const team1 = [{
  name: 'Blaziken', species: 'Blaziken', level: 50, gender: 'M',
  moves: ['flareblitz', 'skyuppercut', 'return', 'thunderpunch'],
  ability: 'Blaze', item: '', nature: 'Adamant',
  evs: { hp: 85, atk: 85, def: 85, spa: 85, spd: 85, spe: 85 },
  ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
}];
const team2 = [{
  name: 'Swampert', species: 'Swampert', level: 50, gender: 'M',
  moves: ['surf', 'earthquake', 'icebeam', 'toxic'],
  ability: 'Torrent', item: '', nature: 'Bold',
  evs: { hp: 85, atk: 85, def: 85, spa: 85, spd: 85, spe: 85 },
  ivs: { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 },
}];

console.log(`@pkmn/sim carregado. Formato: gen3customgame\n`);

const stream = new BattleStreams.BattleStream();
const streams = BattleStreams.getPlayerStreams(stream);

let turns = 0;
const log = [];

(async () => {
  for await (const chunk of streams.omniscient) {
    log.push(chunk);
    for (const line of chunk.split('\n')) {
      if (line.startsWith('|turn|')) { turns++; console.log(`--- turno ${line.split('|')[2]} ---`); }
      if (line.startsWith('|move|')) console.log('  ' + line.split('|').slice(2).join(' usa '));
      if (line.startsWith('|-damage|')) console.log('    dano ->', line.split('|')[2], line.split('|')[3]);
      if (line.startsWith('|-crit|')) console.log('    CRITICO!');
      if (line.startsWith('|faint|')) console.log('    ' + line.split('|')[2], 'desmaiou');
      if (line.startsWith('|win|')) console.log(`\n>>> vencedor: ${line.split('|')[2]} <<<`);
    }
  }
})();

(async () => {
  for await (const chunk of streams.p1) {
    const req = chunk.split('\n').find((l) => l.startsWith('|request|'));
    if (!req) continue;
    const data = JSON.parse(req.slice('|request|'.length));
    if (data.wait) continue;
    if (data.forceSwitch) { streams.p1.write('switch 1'); continue; }
    const moves = data.active[0].moves;
    const pick = moves.findIndex((m) => !m.disabled) + 1 || 1;
    streams.p1.write(`move ${pick}`);
  }
})();

(async () => {
  for await (const chunk of streams.p2) {
    const req = chunk.split('\n').find((l) => l.startsWith('|request|'));
    if (!req) continue;
    const data = JSON.parse(req.slice('|request|'.length));
    if (data.wait) continue;
    if (data.forceSwitch) { streams.p2.write('switch 1'); continue; }
    const moves = data.active[0].moves;
    const pick = moves.findIndex((m) => !m.disabled) + 1 || 1;
    streams.p2.write(`move ${pick}`);
  }
})();

void streams.omniscient.write(`>start {"formatid":"gen3customgame"}`);
void streams.omniscient.write(`>player p1 {"name":"Ash","team":${JSON.stringify(Teams.pack(team1))}}`);
void streams.omniscient.write(`>player p2 {"name":"Misty","team":${JSON.stringify(Teams.pack(team2))}}`);

// da tempo do log terminar de fluir antes de fechar o processo
setTimeout(() => {
  console.log(`\n${turns} turnos jogados, ${log.length} mensagens de protocolo recebidas.`);
  console.log(Dex.forGen(3) ? 'Dex Gen 3 carregada com sucesso.' : 'FALHA ao carregar Dex Gen 3.');
  process.exit(0);
}, 3000);
