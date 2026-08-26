namespace BattleSim;

/// Um Pokemon em batalha: estatisticas calculadas, HP atual, status e estagios.
public sealed class Battler
{
    public required SpeciesData Species { get; init; }
    public required string Nature { get; init; }
    public required List<MoveData> Moves { get; init; }
    public required Dictionary<string, int> Stats { get; init; }
    public required Dictionary<string, int> Pp { get; set; }
    public int Level { get; init; } = 50;
    public int MaxHp { get; init; }
    public int Hp { get; set; }

    /// null | "brn" | "par" | "psn" | "tox" | "slp" | "frz"
    public string? Status { get; set; }
    public int SleepTurns { get; set; }
    public int ToxicCounter { get; set; }

    public Dictionary<string, int> Boosts { get; } = new()
    {
        ["atk"] = 0, ["def"] = 0, ["spa"] = 0, ["spd"] = 0, ["spe"] = 0,
        ["accuracy"] = 0, ["evasion"] = 0,
    };

    public string Name => Species.Name;
    public bool Fainted => Hp <= 0;

    public override string ToString() => $"{Name} {Hp}/{MaxHp}";
}

public sealed class Engine(GameData data, Random rng)
{
    readonly GameData _d = data;
    readonly Random _rng = rng;

    // ------------------------------------------------------------ estatisticas

    /// Formula de HP da Gen 3. Base 1 (Shedinja) sempre resulta em 1 -- caso
    /// especial do jogo, nao sai da formula.
    public static int CalcHp(int baseStat, int iv, int ev, int level) =>
        baseStat == 1 ? 1 : (2 * baseStat + iv + ev / 4) * level / 100 + level + 10;

    /// Formula das demais estatisticas na Gen 3, ja com o modificador de natureza.
    public static int CalcStat(int baseStat, int iv, int ev, int level, double natureMod) =>
        (int)(((2 * baseStat + iv + ev / 4) * level / 100 + 5) * natureMod);

    public Battler MakeBattler(string speciesName, IEnumerable<string> moveIds,
                               string nature = "Serious", int level = 50,
                               int iv = 31, Dictionary<string, int>? evs = null)
    {
        var sp = _d.SpeciesByName(speciesName);
        evs ??= new Dictionary<string, int> { ["hp"] = 0, ["atk"] = 0, ["def"] = 0, ["spa"] = 0, ["spd"] = 0, ["spe"] = 0 };
        var nat = _d.Natures.TryGetValue(nature, out var n) ? n : new NatureData();

        double Mod(string stat) =>
            nat.Plus == stat && nat.Minus != stat ? 1.1
            : nat.Minus == stat && nat.Plus != stat ? 0.9
            : 1.0;

        int Ev(string s) => evs.TryGetValue(s, out var v) ? v : 0;

        int maxHp = CalcHp(sp.BaseStats["hp"], iv, Ev("hp"), level);
        var stats = new Dictionary<string, int>();
        foreach (var s in new[] { "atk", "def", "spa", "spd", "spe" })
            stats[s] = CalcStat(sp.BaseStats[s], iv, Ev(s), level, Mod(s));

        var moves = moveIds.Select(id => _d.Moves[id]).ToList();
        return new Battler
        {
            Species = sp, Nature = nature, Moves = moves, Stats = stats, Level = level,
            MaxHp = maxHp, Hp = maxHp,
            Pp = moves.ToDictionary(m => m.Id, m => m.Pp * 8 / 5),   // PP maximo com 3 PP Ups
        };
    }

    // ------------------------------------------------------------ estagios

    /// Multiplicador de estagio para atk/def/spa/spd/spe na Gen 3.
    public static double StageMult(int stage) =>
        stage >= 0 ? (2.0 + stage) / 2.0 : 2.0 / (2 - stage);

    /// Precisao e evasao usam uma tabela diferente na Gen 3.
    public static double AccuracyStageMult(int stage) =>
        stage >= 0 ? (3.0 + stage) / 3.0 : 3.0 / (3 - stage);

    // ------------------------------------------------------------ dano

    /// Chance de critico por estagio de crit-ratio na Gen 3: 1/16, 1/8, 1/4, 1/3, 1/2.
    public static double CritChance(int ratio) => ratio switch
    {
        <= 1 => 1.0 / 16, 2 => 1.0 / 8, 3 => 1.0 / 4, 4 => 1.0 / 3, _ => 1.0 / 2,
    };

    public sealed record DamageResult(int Damage, double Effectiveness, bool Crit);

    /// Ordem interna dos tipos na Gen 3. A efetividade dos dois tipos do
    /// defensor e aplicada nesta ordem, nao na ordem em que a especie declara.
    static readonly string[] TypePrecedence =
    [
        "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
        "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel",
    ];

    static (string First, string? Second) OrderedDefenderTypes(string[] types)
    {
        if (types.Length < 2 || types[0] == types[1]) return (types[0], null);
        return Array.IndexOf(TypePrecedence, types[0]) > Array.IndexOf(TypePrecedence, types[1])
            ? (types[1], types[0])
            : (types[0], types[1]);
    }

    double TypeMult(string moveType, string defType) =>
        _d.TypeChart.TryGetValue(moveType, out var row) && row.TryGetValue(defType, out var v) ? v : 1;

    /// Equivalente ao `Battle.modify` do Showdown: ponto fixo 4096 com
    /// arredondamento pra cima no meio. E o que faz o STAB 1.5 arredondar
    /// igual ao jogo -- multiplicar por 1.5 direto da resultado diferente.
    static int Modify(int value, int numerator, int denominator = 1)
    {
        int modifier = numerator * 4096 / denominator;
        return (int)(((long)value * modifier + 2048 - 1) / 4096);
    }

    /// Formula de dano da Gen 3, na ordem exata do `modifyDamage` de Gen 3 do
    /// Showdown (data/mods/gen3/scripts.js). A ordem importa: cada etapa trunca,
    /// entao trocar a ordem muda o resultado em +-1.
    /// `roll` de 85 a 100; se null, sorteia.
    public DamageResult CalcDamage(Battler atk, Battler def, MoveData move, int? roll = null, bool? forceCrit = null)
    {
        if (move.Category == "Status" || move.BasePower <= 0)
            return new DamageResult(0, 1, false);

        double eff = _d.Effectiveness(move.Type, def.Species.Types);
        if (eff == 0) return new DamageResult(0, 0, false);

        bool physical = move.Category == "Physical";
        bool crit = forceCrit ?? (move.WillCrit || _rng.NextDouble() < CritChance(move.CritRatio));

        string atkStat = physical ? "atk" : "spa";
        string defStat = physical ? "def" : "spd";

        // num critico da Gen 3 os estagios que prejudicam o atacante e os que
        // beneficiam o defensor sao ignorados
        int atkStage = atk.Boosts[atkStat];
        int defStage = def.Boosts[defStat];
        if (crit)
        {
            if (atkStage < 0) atkStage = 0;
            if (defStage > 0) defStage = 0;
        }

        int a = (int)(atk.Stats[atkStat] * StageMult(atkStage));
        int dfs = (int)(def.Stats[defStat] * StageMult(defStage));

        // na Gen 3 Explosion e Self-Destruct cortam a Defesa do alvo pela metade
        if (move.Id is "explosion" or "selfdestruct") dfs /= 2;

        if (dfs < 1) dfs = 1;

        // 1) dano base, truncando a cada divisao
        int dmg = (2 * atk.Level / 5 + 2) * move.BasePower * a / dfs / 50;

        // 2) queimadura: metade do DANO BASE (nao do stat de ataque)
        if (physical && atk.Status == "brn") dmg = Modify(dmg, 1, 2);

        // 3) piso de 1 para golpe fisico antes do +2
        if (physical && dmg < 1) dmg = 1;

        // 4) +2
        dmg += 2;

        // 5) critico
        if (crit) dmg = Modify(dmg, 2);

        // 6) STAB
        if (atk.Species.Types.Contains(move.Type)) dmg = dmg * 3 / 2;

        // 7) tipo: os dois tipos entram SEPARADOS, truncando entre um e outro,
        //    e na ordem canonica interna do jogo (TypePrecedence) -- nao na
        //    ordem declarada da especie. Combinar num multiplicador so, ou
        //    trocar a ordem, erra em 1 quando o valor e impar.
        var (t1, t2) = OrderedDefenderTypes(def.Species.Types);
        double e1 = TypeMult(move.Type, t1);
        double e2 = t2 is null ? 1 : TypeMult(move.Type, t2);
        if (e1 == 0 || e2 == 0) return new DamageResult(0, 0, crit);
        dmg = (int)Math.Floor(dmg * e1);
        dmg = (int)Math.Floor(dmg * e2);

        // 8) aleatorio por ultimo, depois de STAB e tipo
        int r = roll ?? (100 - _rng.Next(16));
        dmg = dmg * r / 100;

        return new DamageResult(Math.Max(1, dmg), eff, crit);
    }

    /// Faixa de dano possivel (rolls 85 a 100), sem critico. Util para validacao.
    public (int Min, int Max) DamageRange(Battler atk, Battler def, MoveData move)
    {
        int min = CalcDamage(atk, def, move, roll: 85, forceCrit: false).Damage;
        int max = CalcDamage(atk, def, move, roll: 100, forceCrit: false).Damage;
        return (min, max);
    }

    // ------------------------------------------------------------ turno

    public List<string> Log { get; } = [];
    void Say(string s) => Log.Add(s);

    public int EffectiveSpeed(Battler b)
    {
        int spe = (int)(b.Stats["spe"] * StageMult(b.Boosts["spe"]));
        if (b.Status == "par") spe /= 4;    // paralisia divide por 4 na Gen 3
        return spe;
    }

    bool RollAccuracy(Battler atk, Battler def, MoveData move)
    {
        if (move.Accuracy < 0) return true;                     // nunca erra
        double acc = move.Accuracy
                     * AccuracyStageMult(atk.Boosts["accuracy"])
                     / AccuracyStageMult(def.Boosts["evasion"]);
        return _rng.Next(1, 101) <= Math.Max(1, (int)acc);
    }

    /// Resolve o impedimento por status antes do golpe. true = nao consegue agir.
    bool BlockedByStatus(Battler b)
    {
        switch (b.Status)
        {
            case "slp":
                if (b.SleepTurns > 0)
                {
                    b.SleepTurns--;
                    Say($"{b.Name} está dormindo.");
                    return true;
                }
                b.Status = null;
                Say($"{b.Name} acordou!");
                return false;
            case "frz":
                if (_rng.NextDouble() < 0.20) { b.Status = null; Say($"{b.Name} descongelou!"); return false; }
                Say($"{b.Name} está congelado.");
                return true;
            case "par":
                if (_rng.NextDouble() < 0.25) { Say($"{b.Name} está paralisado e não conseguiu se mover!"); return true; }
                return false;
            default:
                return false;
        }
    }

    void ApplyBoosts(Battler target, Dictionary<string, int> boosts, string who)
    {
        foreach (var (stat, delta) in boosts)
        {
            if (!target.Boosts.ContainsKey(stat)) continue;
            int before = target.Boosts[stat];
            target.Boosts[stat] = Math.Clamp(before + delta, -6, 6);
            if (target.Boosts[stat] == before) continue;
            string label = stat switch
            {
                "atk" => "Ataque", "def" => "Defesa", "spa" => "Ataque Especial",
                "spd" => "Defesa Especial", "spe" => "Velocidade",
                "accuracy" => "Precisão", "evasion" => "Evasão", _ => stat,
            };
            Say($"{label} de {who} {(delta > 0 ? "subiu" : "caiu")}!");
        }
    }

    void TryStatus(Battler target, string status)
    {
        if (target.Status != null || target.Fainted) return;
        // imunidades de tipo basicas da Gen 3
        var t = target.Species.Types;
        if (status is "brn" && t.Contains("Fire")) return;
        if (status is "frz" && t.Contains("Ice")) return;
        if (status is "psn" or "tox" && (t.Contains("Poison") || t.Contains("Steel"))) return;
        if (status is "par" && t.Contains("Electric")) return;   // na Gen 3 isso nao valia, mas evita loop chato

        target.Status = status;
        if (status == "slp") target.SleepTurns = _rng.Next(1, 5);
        if (status == "tox") target.ToxicCounter = 1;
        string label = status switch
        {
            "brn" => "queimado", "par" => "paralisado", "psn" => "envenenado",
            "tox" => "gravemente envenenado", "slp" => "no sono", "frz" => "congelado", _ => status,
        };
        Say($"{target.Name} ficou {label}!");
    }

    /// Executa o golpe de `atk` contra `def`.
    public void UseMove(Battler atk, Battler def, MoveData move)
    {
        if (atk.Fainted || def.Fainted) return;
        if (BlockedByStatus(atk)) return;

        if (atk.Pp.TryGetValue(move.Id, out var pp) && pp <= 0)
        {
            Say($"{atk.Name} não tem PP para {move.Name}!");
            return;
        }
        atk.Pp[move.Id] = Math.Max(0, pp - 1);

        Say($"{atk.Name} usou {move.Name}!");

        if (!RollAccuracy(atk, def, move))
        {
            Say($"{atk.Name} errou o golpe!");
            return;
        }

        if (move.Category == "Status")
        {
            if (move.Status != null) TryStatus(def, move.Status);
            if (move.Boosts != null)
            {
                // alvo do boost: "self" mexe no proprio usuario
                bool onSelf = move.Target is "self" or "adjacentAllyOrSelf";
                ApplyBoosts(onSelf ? atk : def, move.Boosts, onSelf ? atk.Name : def.Name);
            }
            return;
        }

        int hits = 1;
        if (move.Multihit is { Length: 2 } mh)
            hits = mh[0] == mh[1] ? mh[0] : _rng.Next(mh[0], mh[1] + 1);

        int totalDealt = 0;
        for (int i = 0; i < hits && !def.Fainted; i++)
        {
            var res = CalcDamage(atk, def, move);
            if (res.Effectiveness == 0)
            {
                Say($"Não afeta {def.Name}...");
                return;
            }
            int dealt = Math.Min(res.Damage, def.Hp);
            def.Hp -= dealt;
            totalDealt += dealt;

            if (res.Crit) Say("Golpe crítico!");
            if (i == 0)
            {
                if (res.Effectiveness > 1) Say("É super efetivo!");
                else if (res.Effectiveness < 1) Say("Não foi muito eficaz...");
            }
        }
        if (hits > 1) Say($"Acertou {hits} vezes!");
        Say($"  {def.Name}: {def.Hp}/{def.MaxHp}");

        if (move.Recoil is { Length: 2 } rc && totalDealt > 0)
        {
            int self = Math.Max(1, totalDealt * rc[0] / rc[1]);
            atk.Hp = Math.Max(0, atk.Hp - self);
            Say($"{atk.Name} sofreu {self} de recuo. ({atk.Hp}/{atk.MaxHp})");
        }
        if (move.Drain is { Length: 2 } dr && totalDealt > 0)
        {
            int heal = Math.Min(atk.MaxHp - atk.Hp, Math.Max(1, totalDealt * dr[0] / dr[1]));
            atk.Hp += heal;
            if (heal > 0) Say($"{atk.Name} recuperou {heal} de HP. ({atk.Hp}/{atk.MaxHp})");
        }

        foreach (var sec in move.Secondaries)
        {
            if (sec.Chance is int c && _rng.Next(1, 101) > c) continue;
            var target = sec.Self ? atk : def;
            if (sec.Status != null) TryStatus(target, sec.Status);
            if (sec.Boosts != null) ApplyBoosts(target, sec.Boosts, target.Name);
        }

        if (def.Fainted) Say($"{def.Name} desmaiou!");
        if (atk.Fainted) Say($"{atk.Name} desmaiou!");
    }

    /// Dano de fim de turno por status.
    public void EndOfTurn(Battler b)
    {
        if (b.Fainted) return;
        switch (b.Status)
        {
            case "brn":
                b.Hp = Math.Max(0, b.Hp - Math.Max(1, b.MaxHp / 8));
                Say($"{b.Name} sofre com a queimadura. ({b.Hp}/{b.MaxHp})");
                break;
            case "psn":
                b.Hp = Math.Max(0, b.Hp - Math.Max(1, b.MaxHp / 8));
                Say($"{b.Name} sofre com o veneno. ({b.Hp}/{b.MaxHp})");
                break;
            case "tox":
                b.Hp = Math.Max(0, b.Hp - Math.Max(1, b.MaxHp * b.ToxicCounter / 16));
                b.ToxicCounter++;
                Say($"{b.Name} sofre com o veneno grave. ({b.Hp}/{b.MaxHp})");
                break;
        }
        if (b.Fainted) Say($"{b.Name} desmaiou!");
    }

    /// Roda um turno completo: decide a ordem por prioridade e velocidade.
    public void RunTurn(Battler p1, MoveData m1, Battler p2, MoveData m2)
    {
        bool p1First;
        if (m1.Priority != m2.Priority) p1First = m1.Priority > m2.Priority;
        else
        {
            int s1 = EffectiveSpeed(p1), s2 = EffectiveSpeed(p2);
            p1First = s1 != s2 ? s1 > s2 : _rng.Next(2) == 0;
        }

        var (first, fMove, second, sMove) = p1First ? (p1, m1, p2, m2) : (p2, m2, p1, m1);

        UseMove(first, second, fMove);
        if (!second.Fainted && !first.Fainted) UseMove(second, first, sMove);

        EndOfTurn(first);
        EndOfTurn(second);
    }
}
