using System.Text.Json;
using System.Text.Json.Serialization;

namespace BattleSim;

// Os dados vem exportados do @pkmn/sim por tools/export_gen3_data.mjs -- nada
// aqui e digitado a mao, entao stats/tipos/poder sao os mesmos do simulador
// que a comunidade competitiva usa.

public sealed class SpeciesData
{
    public int Dex { get; set; }
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string[] Types { get; set; } = [];
    public Dictionary<string, int> BaseStats { get; set; } = new();
    public string[] Abilities { get; set; } = [];
    public string Gender { get; set; } = "";
    public string[] LegalMoves { get; set; } = [];
}

public sealed class Secondary
{
    public int? Chance { get; set; }
    public string? Status { get; set; }
    public string? VolatileStatus { get; set; }
    public Dictionary<string, int>? Boosts { get; set; }
    public bool Self { get; set; }
}

public sealed class MoveData
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Type { get; set; } = "Normal";
    public string Category { get; set; } = "Status";   // Physical | Special | Status
    public int BasePower { get; set; }
    public int Accuracy { get; set; } = 100;           // -1 = nunca erra
    public int Pp { get; set; } = 5;
    public int Priority { get; set; }
    public int CritRatio { get; set; } = 1;
    public string[] Flags { get; set; } = [];
    public int[]? Drain { get; set; }                  // [num, den] do dano causado
    public int[]? Recoil { get; set; }                 // [num, den] do dano causado
    public string? Status { get; set; }
    public string? VolatileStatus { get; set; }
    public Dictionary<string, int>? Boosts { get; set; }
    public string Target { get; set; } = "normal";
    public Secondary[] Secondaries { get; set; } = [];
    public int[]? Multihit { get; set; }               // [min, max]
    public bool Ohko { get; set; }
    public bool WillCrit { get; set; }
    public string? SelfSwitch { get; set; }

    /// Golpe cuja logica propria vive em JS e nao foi portada (Counter, Solar Beam,
    /// Focus Punch...). O motor trata como dano simples; a validacao os ignora.
    public bool HasCallback { get; set; }
}

public sealed class NatureData
{
    public string? Plus { get; set; }
    public string? Minus { get; set; }
}

public sealed class GameData
{
    public required Dictionary<string, SpeciesData> Species { get; init; }
    public required Dictionary<string, MoveData> Moves { get; init; }
    public required Dictionary<string, Dictionary<string, double>> TypeChart { get; init; }
    public required Dictionary<string, NatureData> Natures { get; init; }

    static readonly JsonSerializerOptions Opts = new()
    {
        PropertyNameCaseInsensitive = true,
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
    };

    public static GameData Load(string dir)
    {
        T Read<T>(string file) =>
            JsonSerializer.Deserialize<T>(File.ReadAllText(Path.Combine(dir, file)), Opts)
            ?? throw new InvalidDataException($"falha ao ler {file}");

        var species = Read<List<SpeciesData>>("species.json");
        var moves = Read<List<MoveData>>("moves.json");

        return new GameData
        {
            Species = species.ToDictionary(s => s.Id, s => s),
            Moves = moves.ToDictionary(m => m.Id, m => m),
            TypeChart = Read<Dictionary<string, Dictionary<string, double>>>("typechart.json"),
            Natures = Read<Dictionary<string, NatureData>>("natures.json"),
        };
    }

    public SpeciesData SpeciesByName(string name) =>
        Species.Values.FirstOrDefault(s => s.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
        ?? throw new KeyNotFoundException($"especie desconhecida: {name}");

    /// Multiplicador de efetividade de um tipo de golpe contra um ou dois tipos defensivos.
    public double Effectiveness(string moveType, IEnumerable<string> defTypes)
    {
        double mult = 1;
        foreach (var t in defTypes)
            if (TypeChart.TryGetValue(moveType, out var row) && row.TryGetValue(t, out var m))
                mult *= m;
        return mult;
    }
}
