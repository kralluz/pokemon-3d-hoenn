using BattleSim;

// Modos:
//   dotnet run                          -> batalha demo Blaziken vs Swampert
//   dotnet run -- battle <A> <B>        -> batalha entre dois Pokemon
//   dotnet run -- calc <casos.json>     -> imprime faixas de dano em JSON (para validacao)

// o console do Windows nao usa UTF-8 por padrao e comeria os acentos do log
Console.OutputEncoding = System.Text.Encoding.UTF8;

var dataDir = Path.Combine(AppContext.BaseDirectory, "data");
if (!Directory.Exists(dataDir)) dataDir = Path.Combine("BattleSim", "data");
if (!Directory.Exists(dataDir)) dataDir = "data";

var data = GameData.Load(dataDir);

// se o primeiro argumento for um modo conhecido, consome-o; senao ja e nome de Pokemon
string[] rest = args;
string mode = "battle";
if (args.Length > 0 && args[0] is "battle" or "calc")
{
    mode = args[0];
    rest = args[1..];
}

if (mode == "calc")
{
    RunCalc(data, rest.Length > 0 ? rest[0] : throw new ArgumentException("faltou o arquivo de casos"));
    return;
}

RunBattle(data,
    rest.Length > 0 ? rest[0] : "Blaziken",
    rest.Length > 1 ? rest[1] : "Swampert");

// ---------------------------------------------------------------- modo batalha

static void RunBattle(GameData data, string nameA, string nameB)
{
    var rng = new Random();
    var engine = new Engine(data, rng);

    var a = BuildSet(engine, data, nameA, rng);
    var b = BuildSet(engine, data, nameB, rng);

    Console.WriteLine($"{a.Name} (Nv.{a.Level})  {string.Join(", ", a.Moves.Select(m => m.Name))}");
    Console.WriteLine($"{b.Name} (Nv.{b.Level})  {string.Join(", ", b.Moves.Select(m => m.Name))}");
    Console.WriteLine(new string('-', 60));

    for (int turn = 1; turn <= 50 && !a.Fainted && !b.Fainted; turn++)
    {
        Console.WriteLine($"\n--- turno {turn} ---");
        int before = engine.Log.Count;

        var ma = a.Moves[rng.Next(a.Moves.Count)];
        var mb = b.Moves[rng.Next(b.Moves.Count)];
        engine.RunTurn(a, ma, b, mb);

        foreach (var line in engine.Log.Skip(before)) Console.WriteLine("  " + line);
    }

    Console.WriteLine(new string('-', 60));
    Console.WriteLine(a.Fainted && b.Fainted ? "Empate!"
        : a.Fainted ? $">>> {b.Name} venceu! <<<"
        : b.Fainted ? $">>> {a.Name} venceu! <<<"
        : "Limite de turnos atingido.");
}

/// Mesma heuristica de moveset do prototipo JS: 2 STAB, cobertura, status.
static Battler BuildSet(Engine engine, GameData data, string name, Random rng)
{
    var sp = data.SpeciesByName(name);
    var legal = sp.LegalMoves.Where(data.Moves.ContainsKey).Select(id => data.Moves[id]).ToList();

    var dmg = legal.Where(m => m.Category != "Status" && m.BasePower > 0).ToList();
    var stab = dmg.Where(m => sp.Types.Contains(m.Type)).OrderByDescending(m => m.BasePower).ToList();
    var cover = dmg.Where(m => !sp.Types.Contains(m.Type)).OrderByDescending(m => m.BasePower).ToList();
    var status = legal.Where(m => m.Category == "Status").ToList();

    var picked = new List<MoveData>();
    foreach (var m in stab) if (picked.Count < 2) picked.Add(m);
    foreach (var m in cover) if (picked.Count < 3) picked.Add(m);
    foreach (var m in status) if (picked.Count < 4) picked.Add(m);
    foreach (var m in stab.Concat(cover).Concat(status))
    { if (picked.Count >= 4) break; if (!picked.Contains(m)) picked.Add(m); }
    if (picked.Count == 0 && legal.Count > 0) picked.Add(legal[0]);

    bool physAttacker = sp.BaseStats["atk"] >= sp.BaseStats["spa"];
    string nature = physAttacker ? "Adamant" : "Modest";
    var evs = new Dictionary<string, int> { ["hp"] = 4, ["spe"] = 252, [physAttacker ? "atk" : "spa"] = 252 };

    return engine.MakeBattler(sp.Name, picked.Select(m => m.Id), nature, 50, 31, evs);
}

// ---------------------------------------------------------------- modo calc (validacao)

/// Le casos {attacker, defender, move, nature, evs...} e imprime a faixa de dano
/// que o motor C# calcula. O script de validacao compara com o @pkmn/sim.
static void RunCalc(GameData data, string casesFile)
{
    var engine = new Engine(data, new Random(1));
    var json = System.Text.Json.JsonDocument.Parse(File.ReadAllText(casesFile));
    var results = new List<object>();

    foreach (var c in json.RootElement.EnumerateArray())
    {
        string atkName = c.GetProperty("attacker").GetString()!;
        string defName = c.GetProperty("defender").GetString()!;
        string moveId = c.GetProperty("move").GetString()!;

        var atk = engine.MakeBattler(atkName, [moveId], "Serious", 50, 31,
            new Dictionary<string, int> { ["hp"] = 0, ["atk"] = 0, ["def"] = 0, ["spa"] = 0, ["spd"] = 0, ["spe"] = 0 });
        var def = engine.MakeBattler(defName, [moveId], "Serious", 50, 31,
            new Dictionary<string, int> { ["hp"] = 0, ["atk"] = 0, ["def"] = 0, ["spa"] = 0, ["spd"] = 0, ["spe"] = 0 });

        var move = data.Moves[moveId];
        var (min, max) = engine.DamageRange(atk, def, move);

        results.Add(new
        {
            attacker = atkName, defender = defName, move = moveId,
            min, max,
            atkHp = atk.MaxHp, defHp = def.MaxHp,
            atkStat = atk.Stats, defStat = def.Stats,
        });
    }

    Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(results));
}
