# WhateverDevs: membros que precisam ser reimplementados

Assinaturas extraidas das DLLs reconstruidas pelo Cpp2IL. Os corpos nao existem
(IL2CPP), so as assinaturas -- o comportamento e o que precisa ser escrito.

## WhateverDevs.Core.Behaviours

### `class WhateverBehaviour<TLogger> : WhateverDevs.Core.Runtime.Common.LoggableMonoBehaviour<TLogger>`

Mencionado 86x no codigo do YAPU.

```csharp
bool TryGetCachedComponent<T>(out T& component);
T GetCachedComponent<T>();
bool TryGetCachedComponentInChildren<T>(out T& component, bool includeInactive);
T GetCachedComponentInChildren<T>(bool includeInactive);
bool TryGetCachedComponentInParent<T>(out T& component);
T GetCachedComponentInParent<T>();
```

### `class WhateverScriptable<TLogger> : WhateverDevs.Core.Runtime.Common.LoggableScriptableObject<TLogger>`

Mencionado 24x no codigo do YAPU.

```csharp
```

## WhateverDevs.Core.Runtime.Build

### `class BuildProcessorHook : WhateverDevs.Core.Runtime.Common.LoggableScriptableObject<WhateverDevs.Core.Runtime.Build.BuildProcessorHook>`

Mencionado 1x no codigo do YAPU.

```csharp
bool RunHook(string buildPath);
```

### `class Version : UnityEngine.ScriptableObject`

Mencionado 33x no codigo do YAPU.

```csharp
int GameVersion;
int MayorVersion;
int MinorVersion;
string Date;
WhateverDevs.Core.Runtime.Build.VersionStability Stability;
string ShortVersion { get; }
string FullVersion { get; }
string ToString(WhateverDevs.Core.Runtime.Build.VersionDisplayMode versionDisplayMode);
string ToString();
static string StabilityToString(WhateverDevs.Core.Runtime.Build.VersionStability stability);
```

## WhateverDevs.Core.Runtime.Common

### `class AppEventsListener : WhateverDevs.Core.Runtime.Common.Singleton<WhateverDevs.Core.Runtime.Common.AppEventsListener>`

Mencionado 2x no codigo do YAPU.

```csharp
System.Action<float> AppUpdate;
System.Action<float> PhysicsUpdate;
System.Action<string> ErrorLogged;
System.Action AppQuitting;
void RegisterLogEvent(string log, UnityEngine.LogType type);
```

### `class CoroutineRunner : WhateverDevs.Core.Runtime.Common.Singleton<WhateverDevs.Core.Runtime.Common.CoroutineRunner>`

Mencionado 59x no codigo do YAPU.

```csharp
static UnityEngine.Coroutine RunRoutine(System.Collections.IEnumerator routine);
```

### `class Loggable<TLoggable>`

Mencionado 15x no codigo do YAPU.

```csharp
log4net.ILog Logger { get; }
log4net.ILog StaticLogger { get; }
log4net.ILog GetLogger();
static log4net.ILog GetStaticLogger();
```

### `class Singleton<TSingleton> : WhateverDevs.Core.Behaviours.WhateverBehaviour<TSingleton>`

Mencionado 4x no codigo do YAPU.

```csharp
TSingleton Instance { get; }
void OnDestroy();
```

### `class Utils`

Mencionado 83x no codigo do YAPU.

```csharp
static int Modulus(int a, int n);
static bool IsDontDestroyOnLoad(UnityEngine.GameObject gameObject);
static void SetPositionAndRotation(UnityEngine.Transform transform, WhateverDevs.Core.Runtime.DataStructures.PositionData positionData);
static void SetPosition(UnityEngine.Transform transform, WhateverDevs.Core.Runtime.DataStructures.PositionData positionData);
static void SetRotation(UnityEngine.Transform transform, WhateverDevs.Core.Runtime.DataStructures.PositionData positionData);
static bool IsNullEmptyOrWhiteSpace(string value);
static UnityEngine.Vector3Int ToInts(UnityEngine.Vector3 vector);
static UnityEngine.Vector3 ToFloats(UnityEngine.Vector3Int vector);
static System.Collections.Generic.List<T> ShallowClone<T>(System.Collections.Generic.List<T> original);
static T Random<T>(System.Collections.Generic.List<T> original);
static void AddIfNew<T>(System.Collections.Generic.List<T> original, T element);
static WhateverDevs.Core.Runtime.DataStructures.SerializableDictionary<TK, TV> ToSerializableDictionary<TK, TV>(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> enumerable);
static System.Collections.Generic.List<UnityEngine.Vector2> ToVector2List(System.Collections.Generic.List<UnityEngine.Vector3> original);
static System.Collections.Generic.List<UnityEngine.Vector3> ToVector3List(System.Collections.Generic.List<UnityEngine.Vector2> original);
static T[] ResizeArray<T>(T[] original, int rows, int cols);
static System.Collections.Generic.IEnumerable<T> GetAllItems<T>();
static void CopyFilesRecursively(System.IO.DirectoryInfo source, System.IO.DirectoryInfo target);
static void DeleteDirectory(string targetDir);
static void CloseGame();
```

## WhateverDevs.Core.Runtime.Configuration

### `class ConfigurationData`

Mencionado 4x no codigo do YAPU.

```csharp
```

### `class ConfigurationJsonFilePersisterOnPersistentDataPath : WhateverDevs.Core.Runtime.Configuration.ConfigurationJsonFilePersisterOnLocalFolder`

Mencionado 1x no codigo do YAPU.

```csharp
```

### `class ConfigurationManager : WhateverDevs.Core.Runtime.Common.Initializable<WhateverDevs.Core.Runtime.Configuration.ConfigurationManager>`

Mencionado 12x no codigo do YAPU.

```csharp
System.Collections.Generic.List<WhateverDevs.Core.Runtime.Configuration.IConfiguration> Configurations { get; set; }
System.Action<WhateverDevs.Core.Runtime.Configuration.ConfigurationData> ConfigurationUpdated { get; set; }
void Construct(System.Collections.Generic.List<WhateverDevs.Core.Runtime.Configuration.IConfiguration> configurations);
bool GetConfiguration<TConfigurationData>(out TConfigurationData& configurationData);
bool GetDefaultConfiguration<TConfigurationData>(out TConfigurationData& configurationData);
bool SetConfiguration<TConfigurationData>(TConfigurationData configurationData);
```

### `class ConfigurationManagerInstaller : Zenject.ScriptableObjectInstaller`

Mencionado 3x no codigo do YAPU.

```csharp
WhateverDevs.Core.Runtime.Configuration.ConfigurationScriptableHolder[] ConfigurationsToInstall;
void InstallBindings();
```

### `class ConfigurationScriptableHolderUsingFirstValidPersister<TConfigurationData> : WhateverDevs.Core.Runtime.Configuration.ConfigurationScriptableHolder<TConfigurationData>`

Mencionado 4x no codigo do YAPU.

```csharp
bool Load();
```

### `interface IConfiguration<TConfigurationData>`

Mencionado 1x no codigo do YAPU.

```csharp
System.Collections.Generic.List<WhateverDevs.Core.Runtime.Persistence.IPersister> Persisters { get; set; }
TConfigurationData ConfigurationData { get; set; }
```

### `interface IConfigurationManager`

Mencionado 33x no codigo do YAPU.

```csharp
System.Collections.Generic.List<WhateverDevs.Core.Runtime.Configuration.IConfiguration> Configurations { get; set; }
System.Action<WhateverDevs.Core.Runtime.Configuration.ConfigurationData> ConfigurationUpdated { get; set; }
bool GetConfiguration<TConfigurationData>(out TConfigurationData& configurationData);
bool GetDefaultConfiguration<TConfigurationData>(out TConfigurationData& configurationData);
bool SetConfiguration<TConfigurationData>(TConfigurationData configurationData);
```

## WhateverDevs.Core.Runtime.DataStructures

### `class DescendingComparer<T>`

Mencionado 2x no codigo do YAPU.

```csharp
int Compare(T x, T y);
```

### `class ObjectPair<T1, T2>`

Mencionado 21x no codigo do YAPU.

```csharp
T1 Key;
T2 Value;
```

### `class SerializableDictionary<TK, TV> : System.Collections.Generic.List<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>>`

Mencionado 220x no codigo do YAPU.

```csharp
System.Collections.Generic.List<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> SerializedList;
bool IsReadOnly { get; }
System.Collections.Generic.ICollection<TK> Keys { get; }
System.Collections.Generic.ICollection<TV> Values { get; }
TV Item { get; set; }
bool ContainsKey(TK key);
bool Contains(System.Collections.Generic.KeyValuePair<TK, TV> item);
bool TryGetValue(TK key, out TV& value);
void Add(TK key, TV value);
void Add(System.Collections.Generic.KeyValuePair<TK, TV> item);
bool Remove(TK key);
bool Remove(System.Collections.Generic.KeyValuePair<TK, TV> item);
System.Collections.Generic.IEnumerator<System.Collections.Generic.KeyValuePair<TK, TV>> GetEnumerator();
void CopyTo(System.Collections.Generic.KeyValuePair<TK, TV>[] array, int arrayIndex);
void OnBeforeSerialize();
void OnAfterDeserialize();
void OnDeserialization(object sender);
void GetObjectData(System.Runtime.Serialization.SerializationInfo info, System.Runtime.Serialization.StreamingContext context);
WhateverDevs.Core.Runtime.DataStructures.SerializableDictionary<TK, TV> ShallowClone();
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Where(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Where(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, bool> predicate);
System.Collections.Generic.IEnumerable<TResult> Select<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult> selector);
System.Collections.Generic.IEnumerable<TResult> Select<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, TResult> selector);
System.Collections.Generic.IEnumerable<TResult> SelectMany<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, System.Collections.Generic.IEnumerable<TResult>> selector);
System.Collections.Generic.IEnumerable<TResult> SelectMany<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, System.Collections.Generic.IEnumerable<TResult>> selector);
System.Collections.Generic.IEnumerable<TResult> SelectMany<TResult, TCollection>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, System.Collections.Generic.IEnumerable<TCollection>> collectionSelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TCollection, TResult> resultSelector);
System.Collections.Generic.IEnumerable<TResult> SelectMany<TResult, TCollection>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, System.Collections.Generic.IEnumerable<TCollection>> collectionSelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TCollection, TResult> resultSelector);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Take(int offset);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> TakeWhile(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> TakeWhile(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, bool> predicate);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Skip(int count);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> SkipWhile(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> SkipWhile(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, int, bool> predicate);
System.Collections.Generic.IEnumerable<TResult> Join<TResult>(System.Collections.Generic.IEnumerable<TResult> inner, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult> outerKeySelector, System.Func<TResult, TResult> innerKeySelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult, TResult> resultSelector);
System.Collections.Generic.IEnumerable<TResult> Join<TResult>(System.Collections.Generic.IEnumerable<TResult> inner, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult> outerKeySelector, System.Func<TResult, TResult> innerKeySelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult, TResult> resultSelector, System.Collections.Generic.IEqualityComparer<TResult> comparer);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Concat(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Distinct();
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Distinct(System.Collections.Generic.IEqualityComparer<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> comparer);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> First();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> First(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> FirstOrDefault();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> FirstOrDefault(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Last();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Last(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> LastOrDefault();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> LastOrDefault(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Single();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Single(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> SingleOrDefault();
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> SingleOrDefault(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, bool> predicate);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> ElementAt(int index);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> ElementAtOrDefault(int index);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Except(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Except(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second, System.Collections.Generic.IEqualityComparer<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> comparer);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Intersect(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Intersect(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second, System.Collections.Generic.IEqualityComparer<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> comparer);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Min();
TResult Min<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult> selector);
WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV> Max();
TResult Max<TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TResult> selector);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> OrderBy(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, System.IComparable> keySelector);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> OrderByDescending(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, System.IComparable> keySelector);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Union(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second);
System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> Union(System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> second, System.Collections.Generic.IEqualityComparer<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>> comparer);
System.Collections.Generic.IEnumerable<System.Linq.IGrouping<TKey, TElement>> GroupBy<TKey, TElement>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TKey> keySelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TElement> elementSelector);
System.Collections.Generic.IEnumerable<System.Linq.IGrouping<TKey, TElement>> GroupBy<TKey, TElement>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TKey> keySelector, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TElement> elementSelector, System.Collections.Generic.IEqualityComparer<TKey> comparer);
System.Collections.Generic.IEnumerable<TResult> GroupBy<TKey, TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TKey> keySelector, System.Func<TKey, System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>>, TResult> resultSelector);
System.Collections.Generic.IEnumerable<TResult> GroupBy<TKey, TResult>(System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TKey> keySelector, System.Func<TKey, System.Collections.Generic.IEnumerable<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>>, TResult> resultSelector, System.Collections.Generic.IEqualityComparer<TKey> comparer);
System.Collections.Generic.IEnumerable<TResult> OfType<TResult>();
System.Collections.Generic.IEnumerable<TResult> Cast<TResult>();
System.Collections.Generic.IEnumerable<TResult> Zip<TSecond, TResult>(System.Collections.Generic.IEnumerable<TSecond> second, System.Func<WhateverDevs.Core.Runtime.DataStructures.ObjectPair<TK, TV>, TSecond, TResult> resultSelector);
```

### `struct Tag : System.ValueType`

Mencionado 2x no codigo do YAPU.

```csharp
string Value;
string ToString();
static string op_Implicit(WhateverDevs.Core.Runtime.DataStructures.Tag tag);
static WhateverDevs.Core.Runtime.DataStructures.Tag op_Implicit(string value);
```

## WhateverDevs.Core.Runtime.DependencyInjection

### `class GameObjectFactory<TComponent> : Zenject.PlaceholderFactory<TComponent>`

Mencionado 17x no codigo do YAPU.

```csharp
TComponent CreateGameObject(UnityEngine.Transform parent);
TComponent CreateUiGameObject(UnityEngine.Transform parent);
TComponent CreateGameObject(UnityEngine.Vector3 position, UnityEngine.Quaternion rotation);
TComponent CreateGameObject(UnityEngine.Transform parent, UnityEngine.Vector3 position, UnityEngine.Quaternion rotation);
TComponent CreateUiGameObject(UnityEngine.Transform parent, UnityEngine.Vector3 position, UnityEngine.Quaternion rotation);
```

### `class LazySingletonScriptableInstaller<T> : Zenject.ScriptableObjectInstaller`

Mencionado 11x no codigo do YAPU.

```csharp
void InstallBindings();
```

## WhateverDevs.Core.Runtime.Logger

### `class LogHandler`

Mencionado 1x no codigo do YAPU.

```csharp
static void Initialize();
void LogException(System.Exception exception, UnityEngine.Object context);
void LogFormat(UnityEngine.LogType logType, UnityEngine.Object context, string format, object[] args);
```

## WhateverDevs.Core.Runtime.Persistence

### `interface IPersister`

Mencionado 1x no codigo do YAPU.

```csharp
bool Save<TOriginal>(TOriginal data, string destination, bool suppressErrors);
bool Load<TOriginal>(out TOriginal& data, string origin, bool suppressErrors);
```

## WhateverDevs.Core.Runtime.Serialization

### `interface ISerializer<TSerialized>`

Mencionado 26x no codigo do YAPU.

```csharp
TSerialized To<TOriginal>(TOriginal original);
TOriginal From<TOriginal>(TSerialized serialized);
```

### `class JsonSerializer : WhateverDevs.Core.Runtime.Common.Loggable<WhateverDevs.Core.Runtime.Serialization.JsonSerializer>`

Mencionado 1x no codigo do YAPU.

```csharp
string To<TOriginal>(TOriginal original);
TOriginal From<TOriginal>(string serialized);
```

## WhateverDevs.Core.Runtime.Ui

### `class EasyUpdateText<T> : WhateverDevs.Core.Behaviours.WhateverBehaviour<T>`

Mencionado 3x no codigo do YAPU.

```csharp
bool TextInTheSameObject;
TMPro.TMP_Text TextReference;
TMPro.TMP_Text Text { get; }
void UpdateText(string text);
```

### `class HidableAndSubscribableButton : WhateverDevs.Core.Runtime.Ui.EasySubscribableButton`

Mencionado 1x no codigo do YAPU.

```csharp
bool Shown;
bool SetHeightToZeroWhenHiding;
bool ToggleInteractable;
bool ToggleBlockRaycasts;
void Show();
void Hide();
void Show(bool show);
```

### `class HidableUiElement<T> : WhateverDevs.Core.Behaviours.WhateverBehaviour<T>`

Mencionado 114x no codigo do YAPU.

```csharp
bool ToggleInteractable;
bool ToggleBlockRaycasts;
bool Shown { get; }
void Show(bool show);
```

## WhateverDevs.Localization.Runtime

### `interface ILocalizer`

Mencionado 498x no codigo do YAPU.

```csharp
string Item { get; }
void LoadNewLanguageValues(System.Collections.Generic.List<WhateverDevs.Localization.Runtime.ScriptableLanguage> newLanguages);
void ReDownloadLanguagesFromGoogleSheet();
string GetText(string key, bool modifiersAreLocalizableKeys, string[] valueModifiers);
string GetText(string key, string language, bool modifiersAreLocalizableKeys, string[] valueModifiers);
string GetText(string key, int languageIndex, bool modifiersAreLocalizableKeys, string[] valueModifiers);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys, string language);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys, int languageIndex);
System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> GetTexts(System.Collections.Generic.List<string> keys, System.Collections.Generic.List<string> languages);
System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> GetTexts(System.Collections.Generic.List<string> keys, System.Collections.Generic.List<int> languageIndexes);
string GetCurrentLanguage();
int GetCurrentLanguageIndex();
int GetLanguageIndex(string language);
System.Collections.Generic.List<string> GetAllLanguageIds();
void SetLanguage(string language);
void SetLanguage(int language);
void SubscribeToLanguageChange(System.Action<string> callback);
void SubscribeToLanguageChange(System.Action callback);
void UnsubscribeFromLanguageChange(System.Action<string> callback);
void UnsubscribeFromLanguageChange(System.Action callback);
```

### `class Localizer : WhateverDevs.Core.Runtime.Common.Loggable<WhateverDevs.Localization.Runtime.Localizer>`

Mencionado 412x no codigo do YAPU.

```csharp
string Item { get; }
void Construct(WhateverDevs.Core.Runtime.Configuration.IConfigurationManager configurationManagerReference, WhateverDevs.Localization.Runtime.LocalizerSettings settings);
void LoadNewLanguageValues(System.Collections.Generic.List<WhateverDevs.Localization.Runtime.ScriptableLanguage> newLanguages);
void ReDownloadLanguagesFromGoogleSheet();
string GetText(string key, bool modifiersAreLocalizableKeys, string[] valueModifiers);
string GetText(string key, string language, bool modifiersAreLocalizableKeys, string[] valueModifiers);
string GetText(string key, int languageIndex, bool modifiersAreLocalizableKeys, string[] valueModifiers);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys, string language);
System.Collections.Generic.List<string> GetTexts(System.Collections.Generic.List<string> keys, int languageIndex);
System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> GetTexts(System.Collections.Generic.List<string> keys, System.Collections.Generic.List<string> languages);
System.Collections.Generic.Dictionary<string, System.Collections.Generic.List<string>> GetTexts(System.Collections.Generic.List<string> keys, System.Collections.Generic.List<int> languageIndexes);
string GetCurrentLanguage();
int GetCurrentLanguageIndex();
int GetLanguageIndex(string language);
System.Collections.Generic.List<string> GetAllLanguageIds();
void SetLanguage(string language);
void SetLanguage(int language);
void SubscribeToLanguageChange(System.Action<string> callback);
void SubscribeToLanguageChange(System.Action callback);
void UnsubscribeFromLanguageChange(System.Action<string> callback);
void UnsubscribeFromLanguageChange(System.Action callback);
```

## WhateverDevs.Localization.Runtime.TextPostProcessors

### `class LocalizedTextPostProcessor : WhateverDevs.Core.Behaviours.WhateverScriptable<WhateverDevs.Localization.Runtime.TextPostProcessors.LocalizedTextPostProcessor>`

Mencionado 2x no codigo do YAPU.

```csharp
bool PostProcessText(ref System.String& text, object[] extraParams);
```

## WhateverDevs.Localization.Runtime.Ui

### `class LocalizedTextMeshPro : WhateverDevs.Core.Runtime.Ui.EasyUpdateText<WhateverDevs.Localization.Runtime.Ui.LocalizedTextMeshPro>`

Mencionado 77x no codigo do YAPU.

```csharp
bool SetOnEnable;
string LocalizationKey;
void SetValue(string key, bool modifiersAreLocalizableKeys, string[] valueModifiers);
```

## WhateverDevs.SceneManagement.Runtime.SceneManagement

### `interface ISceneManager`

Mencionado 11x no codigo do YAPU.

```csharp
System.Collections.Generic.List<string> LoadedScenes { get; }
string[] SceneNames { get; }
bool IsSceneAvailable(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
bool IsSceneAvailable(string scene);
void LoadScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference sceneReference, System.Action<float> progressCallback, System.Action<bool> callback, UnityEngine.SceneManagement.LoadSceneMode mode);
void LoadScene(string sceneName, System.Action<float> progressCallback, System.Action<bool> callback, UnityEngine.SceneManagement.LoadSceneMode mode);
void UnloadScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference sceneReference, System.Action<float> progressCallback, System.Action<bool> callback);
void UnloadScene(string sceneName, System.Action<float> progressCallback, System.Action<bool> callback);
UnityEngine.SceneManagement.Scene GetActiveScene();
string GetActiveSceneName();
void SetActiveScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
void SetActiveScene(string sceneName);
void MoveObjectToActiveScene(UnityEngine.GameObject gameObject);
void MoveObjectToScene(UnityEngine.GameObject gameObject, WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
void MoveObjectToScene(UnityEngine.GameObject gameObject, string scene);
```

### `class SceneManager : WhateverDevs.Core.Runtime.Common.LoggableScriptableObject<WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneManager>`

Mencionado 3x no codigo do YAPU.

```csharp
System.Collections.Generic.List<string> NonAddressableScenes;
System.Collections.Generic.List<UnityEngine.AddressableAssets.AssetReference> AddressableScenes;
WhateverDevs.Core.Runtime.DataStructures.SerializableDictionary<string, string> SceneNameGuidDictionary;
WhateverDevs.SceneManagement.Runtime.AddressableManagement.IAddressableManager AddressableManager;
System.Collections.Generic.List<string> LoadedScenes { get; set; }
string[] SceneNames { get; }
System.Collections.Generic.List<string> SceneNamesList { get; }
void Reset();
bool IsSceneAvailable(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
bool IsSceneAvailable(string scene);
void LoadScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference sceneReference, System.Action<float> progressCallback, System.Action<bool> callback, UnityEngine.SceneManagement.LoadSceneMode mode);
void LoadScene(string sceneName, System.Action<float> progressCallback, System.Action<bool> callback, UnityEngine.SceneManagement.LoadSceneMode mode);
void UnloadScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference sceneReference, System.Action<float> progressCallback, System.Action<bool> callback);
void UnloadScene(string sceneName, System.Action<float> progressCallback, System.Action<bool> callback);
UnityEngine.SceneManagement.Scene GetActiveScene();
string GetActiveSceneName();
void SetActiveScene(WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
void SetActiveScene(string sceneName);
void MoveObjectToActiveScene(UnityEngine.GameObject gameObject);
void MoveObjectToScene(UnityEngine.GameObject gameObject, WhateverDevs.SceneManagement.Runtime.SceneManagement.SceneReference scene);
void MoveObjectToScene(UnityEngine.GameObject gameObject, string scene);
```

### `struct SceneReference : System.ValueType`

Mencionado 16x no codigo do YAPU.

```csharp
string SceneName;
```

## WhateverDevs.SceneManagement.Runtime.Utils

### `class Helper`

Mencionado 6x no codigo do YAPU.

```csharp
static int CheckVersion(string version1, string version2);
```

## WhateverDevs.TwoDAudio.Runtime

### `class AudioLibrary : WhateverDevs.Core.Runtime.Common.LoggableScriptableObject<WhateverDevs.TwoDAudio.Runtime.AudioLibrary>`

Mencionado 2x no codigo do YAPU.

```csharp
float SecondsToUnLoadFreeAudiosFromRam;
void Construct(WhateverDevs.SceneManagement.Runtime.AddressableManagement.IAddressableManager addressableManagerReference);
bool IsInitialized();
System.Collections.Generic.List<string> GetAllAudioNames();
System.Collections.Generic.List<UnityEngine.AudioClip> GetAllAudios();
bool IsAudioAvailable(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference);
bool IsAudioAvailable(string audioName);
bool IsAudioAvailable(UnityEngine.AudioClip audio);
void GetAudioAsset(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, System.Action<bool, UnityEngine.AudioClip, UnityEngine.Audio.AudioMixerGroup> callback);
void GetAudioAsset(string audioName, System.Action<bool, UnityEngine.AudioClip, UnityEngine.Audio.AudioMixerGroup> callback);
void GetAudioAsset(UnityEngine.AudioClip audio, System.Action<bool, UnityEngine.AudioClip, UnityEngine.Audio.AudioMixerGroup> callback);
void FreeAudioAsset(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference);
void FreeAudioAsset(string audioName);
UnityEngine.Audio.AudioMixerGroup GetGroupForAudio(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference);
UnityEngine.Audio.AudioMixerGroup GetGroupForAudio(string audioName);
UnityEngine.Audio.AudioMixerGroup GetGroupForAudio(UnityEngine.AudioClip audio);
```

### `class AudioManager : WhateverDevs.Core.Runtime.Common.Singleton<WhateverDevs.TwoDAudio.Runtime.AudioManager>`

Mencionado 156x no codigo do YAPU.

```csharp
bool IsAudioAvailable(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference);
void PlayAudio(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, bool loop, float pitch, float volume, float fadeTime);
System.Collections.IEnumerator IsAudioPlaying(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, System.Action<bool> result);
void StopAudio(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, float fadeTime);
System.Collections.IEnumerator UnmuteAllAudios(float fadeTime);
System.Collections.IEnumerator MuteAllAudios(float fadeTime);
void StopAllAudios();
static float LinearVolumeToLogarithmicVolume(float linearVolume);
static float LogarithmicVolumeToLinearVolume(float logarithmicVolume);
```

### `struct AudioReference : System.ValueType`

Mencionado 232x no codigo do YAPU.

```csharp
string Audio;
```

### `interface IAudioManager`

Mencionado 46x no codigo do YAPU.

```csharp
bool IsAudioAvailable(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference);
void PlayAudio(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, bool loop, float pitch, float volume, float fadeTime);
System.Collections.IEnumerator IsAudioPlaying(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, System.Action<bool> result);
void StopAudio(WhateverDevs.TwoDAudio.Runtime.AudioReference audioReference, float fadeTime);
System.Collections.IEnumerator UnmuteAllAudios(float fadeTime);
System.Collections.IEnumerator MuteAllAudios(float fadeTime);
void StopAllAudios();
static float LinearVolumeToLogarithmicVolume(float linearVolume);
static float LogarithmicVolumeToLinearVolume(float logarithmicVolume);
```

