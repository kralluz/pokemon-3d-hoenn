using System.Text;
using System.Text.RegularExpressions;
using Mono.Cecil;

// Maps how much of the private WhateverDevs libraries YAPU actually needs, and generates a
// no-op shim for the Odin Inspector attributes so the framework can compile without the
// paid plugin. Reads the Cpp2IL-rebuilt assemblies from the demo build.
//
// usage: <gameAssembliesDir> <yapuSourceDir> <outDir>
string asmDir = args[0], srcDir = args[1], outDir = args[2];
Directory.CreateDirectory(outDir);

var resolver = new DefaultAssemblyResolver();
resolver.AddSearchDirectory(asmDir);
var rp = new ReaderParameters { AssemblyResolver = resolver };
var asms = Directory.GetFiles(asmDir, "*.dll")
    .Select(f => { try { return AssemblyDefinition.ReadAssembly(f, rp); } catch { return null; } })
    .Where(a => a != null).Select(a => a!).ToList();

static IEnumerable<TypeDefinition> Flatten(TypeDefinition t)
{
    yield return t;
    foreach (var n in t.NestedTypes) foreach (var x in Flatten(n)) yield return x;
}

var allTypes = asms.SelectMany(a => a.Modules).SelectMany(m => m.Types).SelectMany(Flatten).ToList();

// ---------- every identifier that appears in the YAPU C# source ----------
var srcText = new StringBuilder();
foreach (var f in Directory.EnumerateFiles(srcDir, "*.cs", SearchOption.AllDirectories))
    srcText.Append(File.ReadAllText(f)).Append('\n');
var source = srcText.ToString();
var srcIdents = new HashSet<string>(Regex.Matches(source, @"[A-Za-z_]\w*").Select(m => m.Value));

static string Bare(string name) { int i = name.IndexOf('`'); return i < 0 ? name : name[..i]; }
// Attributes are written `[FoldoutGroup]` in source but named FoldoutGroupAttribute in metadata.
static string Sugar(string name) =>
    name.EndsWith("Attribute") && name.Length > 9 ? name[..^9] : name;

// ---------- part 1: WhateverDevs surface actually referenced ----------
var wdTypes = allTypes.Where(t => t.Namespace.StartsWith("WhateverDevs")).ToList();
var used = wdTypes.Where(t => srcIdents.Contains(Bare(t.Name)))
                  .GroupBy(t => t.Namespace + "." + Bare(t.Name))
                  .Select(g => g.OrderByDescending(t => t.GenericParameters.Count).First())
                  .ToList();

// How often each one is named in the source, as a rough weight.
int Uses(TypeDefinition t) =>
    Regex.Matches(source, $@"\b{Regex.Escape(Bare(t.Name))}\b").Count;

var report = new StringBuilder();
report.AppendLine("# Superficie das libs WhateverDevs usada pelo YAPU");
report.AppendLine();
report.AppendLine($"Tipos publicos nas DLLs: **{wdTypes.Count(t => t.IsPublic)}**  ");
report.AppendLine($"Tipos efetivamente nomeados no codigo do YAPU: **{used.Count}**");
report.AppendLine();
report.AppendLine("| tipo | namespace | membros publicos | mencoes no fonte | forma |");
report.AppendLine("|---|---|---|---|---|");
foreach (var t in used.OrderByDescending(Uses))
{
    int members = t.Methods.Count(m => m.IsPublic && !m.IsConstructor)
                + t.Fields.Count(f => f.IsPublic) + t.Properties.Count;
    string shape = t.IsInterface ? "interface" : t.IsEnum ? "enum"
                 : t.IsAbstract ? "classe abstrata" : t.IsValueType ? "struct" : "classe";
    report.AppendLine($"| `{Bare(t.Name)}` | {t.Namespace} | {members} | {Uses(t)} | {shape} |");
}
File.WriteAllText(Path.Combine(outDir, "whateverdevs-usage.md"), report.ToString());
Console.WriteLine($"WhateverDevs: {wdTypes.Count(t => t.IsPublic)} publicos, {used.Count} usados pelo YAPU");

// ---------- part 1b: exact member-by-member spec of what must be reimplemented ----------
static string Sig(MethodDefinition m)
{
    var ps = string.Join(", ", m.Parameters.Select(p =>
        (p.IsOut ? "out " : p.ParameterType.IsByReference ? "ref " : "")
        + TypeName(p.ParameterType) + " " + p.Name));
    string gen = m.HasGenericParameters ? "<" + string.Join(", ", m.GenericParameters.Select(g => g.Name)) + ">" : "";
    return $"{TypeName(m.ReturnType)} {m.Name}{gen}({ps})";
}

var api = new StringBuilder();
api.AppendLine("# WhateverDevs: membros que precisam ser reimplementados");
api.AppendLine();
api.AppendLine("Assinaturas extraidas das DLLs reconstruidas pelo Cpp2IL. Os corpos nao existem");
api.AppendLine("(IL2CPP), so as assinaturas -- o comportamento e o que precisa ser escrito.");
api.AppendLine();

foreach (var nsg in used.GroupBy(t => t.Namespace).OrderBy(g => g.Key))
{
    api.AppendLine($"## {nsg.Key}");
    api.AppendLine();
    foreach (var t in nsg.OrderBy(t => t.Name))
    {
        string gen = t.HasGenericParameters ? "<" + string.Join(", ", t.GenericParameters.Select(g => g.Name)) + ">" : "";
        string shape = t.IsInterface ? "interface" : t.IsEnum ? "enum" : t.IsValueType ? "struct" : "class";
        string bas = t.BaseType != null && t.BaseType.FullName != "System.Object"
                   ? " : " + TypeName(t.BaseType) : "";
        api.AppendLine($"### `{shape} {Bare(t.Name)}{gen}{bas}`");
        api.AppendLine();
        api.AppendLine($"Mencionado {Uses(t)}x no codigo do YAPU.");
        api.AppendLine();
        api.AppendLine("```csharp");
        foreach (var f in t.Fields.Where(f => f.IsPublic && !f.Name.Contains('<')))
            api.AppendLine($"{(f.IsStatic ? "static " : "")}{TypeName(f.FieldType)} {f.Name};");
        foreach (var pr in t.Properties.Where(pr => pr.GetMethod?.IsPublic == true || pr.SetMethod?.IsPublic == true))
            api.AppendLine($"{TypeName(pr.PropertyType)} {pr.Name} {{ {(pr.GetMethod?.IsPublic == true ? "get; " : "")}{(pr.SetMethod?.IsPublic == true ? "set; " : "")}}}");
        foreach (var m in t.Methods.Where(m => m.IsPublic && !m.IsConstructor && !m.IsGetter && !m.IsSetter
                                            && !m.Name.Contains('<')))
            api.AppendLine($"{(m.IsStatic ? "static " : "")}{Sig(m)};");
        api.AppendLine("```");
        api.AppendLine();
    }
}
File.WriteAllText(Path.Combine(outDir, "whateverdevs-api.md"), api.ToString());
Console.WriteLine("spec de membros -> whateverdevs-api.md");

// ---------- part 2: Odin attribute shim ----------
var odinSeed = allTypes.Where(t => t.Namespace.StartsWith("Sirenix") && t.IsPublic
                                && srcIdents.Contains(Sugar(Bare(t.Name))))
                       .GroupBy(t => Bare(t.Name)).Select(g => g.First()).ToList();

// Transitive closure: an emitted member may mention another Sirenix type (ButtonStyle,
// SdfIconType, InfoMessageType...), and the shim will not compile unless that one is
// emitted too.
var byName = allTypes.Where(t => t.Namespace.StartsWith("Sirenix"))
                     .GroupBy(t => t.FullName).ToDictionary(g => g.Key, g => g.First());
var odin = new List<TypeDefinition>();
var queue = new Queue<TypeDefinition>(odinSeed);
var inSet = new HashSet<string>(odinSeed.Select(t => t.FullName));
while (queue.Count > 0)
{
    var t = queue.Dequeue();
    odin.Add(t);
    IEnumerable<TypeReference> refs = t.Fields.Where(f => f.IsPublic && !f.IsStatic).Select(f => f.FieldType)
        .Concat(t.Properties.Where(pr => pr.GetMethod?.IsPublic == true).Select(pr => pr.PropertyType))
        .Concat(t.Methods.Where(m => m.IsConstructor && m.IsPublic).SelectMany(m => m.Parameters).Select(p => p.ParameterType));
    foreach (var r in refs)
    {
        var rt = r is ArrayType at2 ? at2.ElementType : r;
        if (!rt.FullName.StartsWith("Sirenix") || !inSet.Add(rt.FullName)) continue;
        if (byName.TryGetValue(rt.FullName, out var def)) queue.Enqueue(def);
    }
}

static string TypeName(TypeReference t)
{
    if (t is ArrayType at) return TypeName(at.ElementType) + "[]";
    if (t is GenericInstanceType gi)
        return Bare(gi.ElementType.FullName.Replace('/', '.'))
             + "<" + string.Join(", ", gi.GenericArguments.Select(TypeName)) + ">";
    return t.FullName switch
    {
        "System.Void" => "void", "System.String" => "string", "System.Boolean" => "bool",
        "System.Int32" => "int", "System.Single" => "float", "System.Double" => "double",
        "System.Object" => "object", "System.Type" => "System.Type",
        _ => t.FullName.Replace('/', '.'),
    };
}

var shim = new StringBuilder();
shim.AppendLine("""
// Auto-gerado por tools/yapu-unblock. NAO EDITAR A MAO.
//
// Stubs sem comportamento dos atributos do Odin Inspector, para o YAPU compilar sem o
// plugin pago. O YAPU nao usa a *serializacao* do Odin (nenhum SerializedScriptableObject
// nem OdinSerialize), so os atributos de inspector -- entao o jogo roda igual; o que se
// perde e o visual do inspector e as ferramentas de editor.
//
// Se voce comprar o Odin, apague este arquivo: as assinaturas foram geradas a partir da
// Sirenix.OdinInspector.Attributes.dll do proprio build, entao sao compativeis.
#if !ODIN_INSPECTOR
using System;
using System.Diagnostics;

""");

foreach (var nsGroup in odin.GroupBy(t => t.Namespace).OrderBy(g => g.Key))
{
shim.AppendLine($"namespace {nsGroup.Key}");
shim.AppendLine("{");
foreach (var t in nsGroup.OrderBy(t => t.Name))
{
    string name = Bare(t.Name);
    if (t.IsEnum)
    {
        shim.AppendLine($"    public enum {name}");
        shim.AppendLine("    {");
        foreach (var f in t.Fields.Where(f => f.IsStatic && f.HasConstant))
            shim.AppendLine($"        {f.Name} = {f.Constant},");
        shim.AppendLine("    }");
        shim.AppendLine();
        continue;
    }
    if (t.IsInterface) continue;

    bool isAttr = false;
    for (var b = t.BaseType?.Resolve(); b != null; b = b.BaseType?.Resolve())
        if (b.FullName == "System.Attribute") { isAttr = true; break; }

    if (isAttr)
    {
        shim.AppendLine("    [AttributeUsage(AttributeTargets.All, AllowMultiple = true)]");
        shim.AppendLine("    [Conditional(\"UNITY_EDITOR\")]");
        shim.AppendLine($"    public class {name} : Attribute");
    }
    else shim.AppendLine($"    public class {name}");

    shim.AppendLine("    {");
    foreach (var f in t.Fields.Where(f => f.IsPublic && !f.IsStatic))
        shim.AppendLine($"        public {TypeName(f.FieldType)} {f.Name};");
    foreach (var pr in t.Properties.Where(pr => pr.GetMethod?.IsPublic == true))
        shim.AppendLine($"        public {TypeName(pr.PropertyType)} {pr.Name} {{ get; set; }}");
    var seen = new HashSet<string>();
    foreach (var c in t.Methods.Where(m => m.IsConstructor && m.IsPublic))
    {
        var ps = string.Join(", ", c.Parameters.Select((p, i) => $"{TypeName(p.ParameterType)} p{i}"
                                                              + (p.IsOptional ? " = default" : "")));
        if (!seen.Add(ps)) continue;
        shim.AppendLine($"        public {name}({ps}) {{ }}");
    }
    if (!seen.Contains("")) shim.AppendLine($"        public {name}() {{ }}");
    shim.AppendLine("    }");
    shim.AppendLine();
}
shim.AppendLine("}");
shim.AppendLine();
}
shim.AppendLine("#endif");
File.WriteAllText(Path.Combine(outDir, "OdinShim.cs"), shim.ToString());
Console.WriteLine($"Odin: {odin.Count} tipos referenciados -> OdinShim.cs");
