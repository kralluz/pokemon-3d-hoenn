using System.Text.RegularExpressions;
using System.Text.Json;
using Mono.Cecil;

// args: <gameAssembliesDir> <outJson> <typeFullName>...
string dir = args[0], outPath = args[1];
var roots = args.Skip(2).ToArray();

var resolver = new DefaultAssemblyResolver();
resolver.AddSearchDirectory(dir);
var rp = new ReaderParameters { AssemblyResolver = resolver };
var asms = Directory.GetFiles(dir, "*.dll")
    .Select(f => { try { return AssemblyDefinition.ReadAssembly(f, rp); } catch { return null; } })
    .Where(a => a != null).ToList();

TypeDefinition? Find(string full)
{
    var all = asms.SelectMany(a => a!.Modules).SelectMany(m => m.Types).SelectMany(Flatten).ToList();
    // Fall back to the short name for types the C# source scan could not qualify
    // (third-party assemblies, mostly).
    return all.FirstOrDefault(t => t.FullName == full)
        // Prefer game/plugin types over same-named engine ones (e.g. UnityEngine.SceneManager).
        ?? all.FirstOrDefault(t => t.Name == full && !t.Namespace.StartsWith("UnityEngine")
                                                  && !t.Namespace.StartsWith("System"))
        ?? all.FirstOrDefault(t => t.Name == full);
}

static IEnumerable<TypeDefinition> Flatten(TypeDefinition t)
{
    yield return t;
    foreach (var n in t.NestedTypes) foreach (var x in Flatten(n)) yield return x;
}

static bool IsUnityObject(TypeDefinition? t)
{
    while (t != null)
    {
        if (t.FullName == "UnityEngine.Object") return true;
        t = t.BaseType?.Resolve();
    }
    return false;
}

var primMap = new Dictionary<string, (string code, bool align)>
{
    ["System.Boolean"] = ("bool", true),
    ["System.Byte"] = ("u8", true),
    ["System.SByte"] = ("i8", true),
    ["System.Char"] = ("char", true),
    ["System.Int16"] = ("i16", true),
    ["System.UInt16"] = ("u16", true),
    ["System.Int32"] = ("i32", false),
    ["System.UInt32"] = ("u32", false),
    ["System.Int64"] = ("i64", false),
    ["System.UInt64"] = ("u64", false),
    ["System.Single"] = ("f32", false),
    ["System.Double"] = ("f64", false),
};

// [SerializeField] / [NonSerialized] markers recovered from the YAPU C# source,
// because Cpp2IL strips custom attributes from the IL2CPP-rebuilt assembly.
var serDoc = JsonDocument.Parse(File.ReadAllText(Environment.GetEnvironmentVariable("SERFIELDS")!));
var serSet = serDoc.RootElement.GetProperty("serialize").EnumerateArray().Select(e => e.GetString()!).ToHashSet();
var nonSet = serDoc.RootElement.GetProperty("nonSerialized").EnumerateArray().Select(e => e.GetString()!).ToHashSet();
static string Strip(string full) => Regex.Replace(full, "`[0-9]+", "");

var warnings = new List<string>();
var abstractTypes = new HashSet<string>();
object? Node(TypeReference tr, int depth, HashSet<string> stack, bool isRoot = false)
{
    if (depth > 12) { warnings.Add("depth limit at " + tr.FullName); return null; }

    if (tr is ArrayType at)
    {
        var e = Node(at.ElementType, depth + 1, stack);
        return e == null ? null : new Dictionary<string, object?> { ["kind"] = "array", ["elem"] = e };
    }
    if (tr is GenericInstanceType git && git.ElementType.FullName == "System.Collections.Generic.List`1")
    {
        var e = Node(git.GenericArguments[0], depth + 1, stack);
        return e == null ? null : new Dictionary<string, object?> { ["kind"] = "array", ["elem"] = e };
    }
    if (tr.FullName == "System.String")
        return new Dictionary<string, object?> { ["kind"] = "string" };
    if (primMap.TryGetValue(tr.FullName, out var p))
        return new Dictionary<string, object?> { ["kind"] = "prim", ["type"] = p.code, ["align"] = p.align };

    var td = tr.Resolve();
    if (td == null) { warnings.Add("unresolved " + tr.FullName); return null; }

    if (td.IsEnum)
    {
        var ut = td.Fields.First(f => f.Name == "value__").FieldType.FullName;
        var up = primMap[ut];
        return new Dictionary<string, object?> { ["kind"] = "prim", ["type"] = up.code, ["align"] = up.align, ["enum"] = td.FullName };
    }
    // Cpp2IL strips [Serializable], so the abstract-class shape is the only signal left.
    if (!isRoot && td.IsAbstract && !td.IsInterface && !IsUnityObject(td))
    {
        // Unity stores these as [SerializeReference] managed references: the field holds a
        // 64-bit rid and the real object lives in the registry appended after the fields.
        abstractTypes.Add(td.FullName);
        return new Dictionary<string, object?> { ["kind"] = "managedref", ["type"] = td.FullName };
    }
    if (IsUnityObject(td) && !isRoot)
        return new Dictionary<string, object?> { ["kind"] = "pptr", ["type"] = td.FullName };

    // Unity special-cased structs
    switch (td.FullName)
    {
        case "UnityEngine.Color32":
            return new Dictionary<string, object?> { ["kind"] = "prim", ["type"] = "u32", ["align"] = false, ["enum"] = "Color32" };
        case "UnityEngine.AnimationCurve":
        {
            // Unity lays this out as m_Curve (vector of Keyframe) + three ints.
            Dictionary<string, object?> F(string n, object? node) =>
                new() { ["name"] = n, ["node"] = node };
            Dictionary<string, object?> P(string t, bool al = false) =>
                new() { ["kind"] = "prim", ["type"] = t, ["align"] = al };
            var keyframe = new Dictionary<string, object?>
            {
                ["kind"] = "class", ["name"] = "UnityEngine.Keyframe",
                ["fields"] = new List<object>
                {
                    F("time", P("f32")), F("value", P("f32")),
                    F("inSlope", P("f32")), F("outSlope", P("f32")),
                    F("weightedMode", P("i32")),
                    F("inWeight", P("f32")), F("outWeight", P("f32")),
                },
            };
            return new Dictionary<string, object?>
            {
                ["kind"] = "class", ["name"] = "UnityEngine.AnimationCurve",
                ["fields"] = new List<object>
                {
                    F("m_Curve", new Dictionary<string, object?> { ["kind"] = "array", ["elem"] = keyframe }),
                    F("m_PreInfinity", P("i32")), F("m_PostInfinity", P("i32")),
                    F("m_RotationOrder", P("i32")),
                },
            };
        }
        case "UnityEngine.Gradient":
            warnings.Add("special type not modelled: " + td.FullName);
            return null;
    }

    if (!isRoot && !td.IsValueType && !td.IsSerializable && !td.CustomAttributes.Any(c => c.AttributeType.Name == "SerializableAttribute"))
    { warnings.Add("not [Serializable]: " + td.FullName); return null; }

    string key = tr.FullName;
    if (!stack.Add(key)) { warnings.Add("cycle at " + key); return null; }

    static TypeReference Sub(TypeReference t, Dictionary<string, TypeReference> m)
    {
        if (t is GenericParameter gp && m.TryGetValue(gp.Name, out var r)) return r;
        if (t is GenericInstanceType g)
        {
            var ni = new GenericInstanceType(g.ElementType);
            foreach (var a in g.GenericArguments) ni.GenericArguments.Add(Sub(a, m));
            return ni;
        }
        if (t is ArrayType a2) return new ArrayType(Sub(a2.ElementType, m));
        return t;
    }

    static Dictionary<string, TypeReference> MapFor(TypeDefinition def, TypeReference asWritten)
    {
        var m = new Dictionary<string, TypeReference>();
        if (asWritten is GenericInstanceType gi)
            for (int i = 0; i < gi.GenericArguments.Count && i < def.GenericParameters.Count; i++)
                m[def.GenericParameters[i].Name] = gi.GenericArguments[i];
        return m;
    }

    var fields = new List<object>();

    // Walk the base chain keeping each level's generic arguments: resolving straight to the
    // TypeDefinition would turn `Foo : SerializableDictionary<Status, float>` back into the
    // open generic and leave its fields typed TK/TV, which cannot be laid out.
    var chain = new List<(TypeDefinition Def, Dictionary<string, TypeReference> Map)>();
    var curDef = td;
    var curMap = MapFor(td, tr);
    // Stop at framework base types: Unity never serializes their internals, and walking into
    // List<T> would pull in _items/_size/_version and wreck the layout.
    while (curDef != null && !curDef.Namespace.StartsWith("System")
           && curDef.FullName != "UnityEngine.ScriptableObject" && curDef.FullName != "UnityEngine.MonoBehaviour")
    {
        chain.Insert(0, (curDef, curMap));
        var baseRef = curDef.BaseType;
        if (baseRef == null) break;
        var baseSub = Sub(baseRef, curMap);
        var baseDef = baseRef.Resolve();
        if (baseDef == null) break;
        curMap = MapFor(baseDef, baseSub);
        curDef = baseDef;
    }

    foreach (var (lvl, lvlMap) in chain)
        foreach (var f in lvl.Fields)
        {
            if (f.IsStatic || f.HasConstant || f.IsInitOnly) continue;
            if (f.Name.Contains('<')) continue;   // compiler-generated backing field
            string srcKey = Strip(lvl.FullName) + "." + f.Name;
            // For third-party types we have no C# source, so the [SerializeField] set cannot
            // tell us anything -- fall back to Unity's own rule and let the byte-consumption
            // check catch any type where that guess is wrong.
            bool noSource = !Strip(lvl.FullName).StartsWith("Varguiniano.YAPU");
            bool serField = f.CustomAttributes.Any(c => c.AttributeType.Name == "SerializeFieldAttribute")
                            || serSet.Contains(srcKey) || noSource;
            if (f.CustomAttributes.Any(c => c.AttributeType.Name == "NonSerializedAttribute")
                || nonSet.Contains(srcKey)) continue;
            if (!f.IsPublic && !serField) continue;
            var n = Node(Sub(f.FieldType, lvlMap), depth + 1, stack);
            if (n == null) { warnings.Add($"skip field {lvl.FullName}.{f.Name} : {f.FieldType.FullName}"); continue; }
            fields.Add(new Dictionary<string, object?> { ["name"] = f.Name, ["node"] = n });
        }

    stack.Remove(key);
    return new Dictionary<string, object?> { ["kind"] = "class", ["name"] = tr.FullName, ["fields"] = fields };
}

if (Environment.GetEnvironmentVariable("DUMPFIELDS") is string dumpType && dumpType.Length > 0)
{
    var t0 = Find(dumpType)!;
    var ch = new List<TypeDefinition>(); var c0 = t0;
    while (c0 != null && !c0.Namespace.StartsWith("System")
           && c0.FullName != "UnityEngine.ScriptableObject" && c0.FullName != "UnityEngine.MonoBehaviour")
    { ch.Insert(0, c0); c0 = c0.BaseType?.Resolve(); }
    foreach (var lvl in ch)
        foreach (var f in lvl.Fields)
        {
            if (f.IsStatic || f.HasConstant || f.IsInitOnly || f.Name.Contains('<')) continue;
            string key = Strip(lvl.FullName) + "." + f.Name;
            bool inc = f.IsPublic || serSet.Contains(key) || !Strip(lvl.FullName).StartsWith("Varguiniano.YAPU");
            Console.WriteLine($"{(inc ? "IN " : "OUT")}  {(f.IsPublic ? "pub" : "prv")}  {lvl.Name,-16} {f.Name,-42} {f.FieldType.Name}");
        }
    return;
}

var result = new Dictionary<string, object?>();
foreach (var r in roots)
{
    var t = Find(r);
    if (t == null) { Console.WriteLine("NOT FOUND: " + r); continue; }
    result[r] = Node(t, 0, new HashSet<string>(), true);
}
// Concrete implementations that can appear in the managed-reference registry.
var allTypes = asms.SelectMany(a => a!.Modules).SelectMany(m => m.Types).SelectMany(Flatten).ToList();
var refTypes = new Dictionary<string, object?>();
var done = new HashSet<string>();
while (true)
{
    var pending = abstractTypes.Where(t => !done.Contains(t)).ToList();
    if (pending.Count == 0) break;
    foreach (var abs in pending)
    {
        done.Add(abs);
        foreach (var t in allTypes)
        {
            if (t.IsAbstract || t.IsInterface || refTypes.ContainsKey(t.FullName)) continue;
            bool derives = false;
            var c = t;
            while (c != null) { if (c.FullName == abs) { derives = true; break; } c = c.BaseType?.Resolve(); }
            if (!derives) continue;
            refTypes[t.FullName] = Node(t, 0, new HashSet<string>(), true);
        }
    }
}
Console.WriteLine($"abstract roots: {done.Count}, concrete ref types: {refTypes.Count}");

File.WriteAllText(outPath, JsonSerializer.Serialize(new { layouts = result, refTypes, warnings },
    new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"wrote {outPath}; warnings: {warnings.Count}");
foreach (var w in warnings.Distinct().Take(60)) Console.WriteLine("  " + w);
