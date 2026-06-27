# Localization workflow — step by step (Unity 6, com.unity.localization)

Concrete, Unity-6-accurate steps for the extract → tables → export → translate → import → QA loop. Where an exact API is uncertain, the **Editor workflow** is described rather than invented code. Drive scriptable parts through `unity-mcp-bridge` `execute_code`; do the rest in the Localization windows.

> Reconnect note: every package add / C# compile triggers a ~5s domain reload that drops the MCP bridge. Focus the Unity Editor to reconnect (see `unity-mcp-bridge`). Do package and settings steps first, then batch the rest.

---

## 1. Install the package

Editor: Window ▸ Package Manager ▸ `+` ▸ *Add package by name* → `com.unity.localization`.

Or add to `Packages/manifest.json` `dependencies` (pin a Unity-6-compatible version that Package Manager resolves), then let resolution run:

```json
"com.unity.localization": "1.5.4"
```

(Use the version Package Manager offers for your Unity 6 install; don't hardcode a stale one blindly.)

## 2. Create Localization Settings

Editor: Project Settings ▸ Localization ▸ **Create** (saves `Assets/Localization/Localization Settings.asset`). This is the root asset (available locales, startup selectors, string/asset databases). Confirm it's in **Preloaded Assets** (Project Settings ▸ Player) so it loads on device.

## 3. Add locales

Editor: Window ▸ Asset Management ▸ Localization Tables ▸ **Locale Generator** → tick target locales → Generate. Each becomes a `Locale` asset.

Scriptable (via `execute_code`):

```csharp
using UnityEditor.Localization;
using UnityEngine.Localization;

LocalizationEditorSettings.AddLocale(Locale.CreateLocale(SystemLanguage.English));
LocalizationEditorSettings.AddLocale(Locale.CreateLocale(SystemLanguage.Japanese));
LocalizationEditorSettings.AddLocale(Locale.CreateLocale(new UnityEngine.Localization.LocaleIdentifier("zh-Hans")));
LocalizationEditorSettings.AddLocale(Locale.CreateLocale(new UnityEngine.Localization.LocaleIdentifier("ar")));
```

## 4. Configure startup locale selectors (persist + system default)

Editor: Project Settings ▸ Localization ▸ **Locale Selectors** list (ordered, first match wins). Add in this order:

1. **PlayerPref Locale Selector** — restores the player's saved choice across launches.
2. **System Locale Selector** — first run defaults to device language.
3. **Specific Locale Selector** — set to your source locale as a guaranteed fallback.

Runtime language switch (the PlayerPref selector persists it automatically):

```csharp
using UnityEngine.Localization.Settings;
using System.Collections;

IEnumerator SetLocale(int localeIndex) {
    yield return LocalizationSettings.InitializationOperation; // wait for boot
    LocalizationSettings.SelectedLocale =
        LocalizationSettings.AvailableLocales.Locales[localeIndex];
}
```

Always wait on `LocalizationSettings.InitializationOperation` before reading any localized value at startup.

## 5. Create String Tables (organized by screen)

Editor: Localization Tables window ▸ **New Table Collection** ▸ String Table Collection → name it per screen (`Menu`, `HUD`, `Shop`, `Results`) → select locales → Create. Add entries with a stable **Key** (`menu.play`) and per-locale values.

Scriptable:

```csharp
using UnityEditor.Localization;

var collection = LocalizationEditorSettings.CreateStringTableCollection(
    "Menu", "Assets/Localization/Tables");
collection.SharedData.AddKey("menu.play");
collection.SharedData.AddKey("menu.settings");
// set a value for a specific locale's table:
var enTable = collection.GetTable("en") as UnityEngine.Localization.Tables.StringTable;
enTable.AddEntry("menu.play", "Play");
UnityEditor.EditorUtility.SetDirty(enTable);
```

Asset Tables: same flow but **Asset Table Collection** — entries reference locale-specific `Sprite`/`AudioClip`/`TMP_FontAsset` assets.

## 6. Bind UI to keys (reference by key, never literal)

- **uGUI / TMP:** add a `LocalizeStringEvent` to the `TMP_Text` GameObject; set its `StringReference` to `Table/Key`; wire the event to `TMP_Text.text`. For images/audio use `LocalizeSpriteEvent` / `LocalizeAudioClipEvent`.
- **In code:**

```csharp
using UnityEngine.Localization;

[SerializeField] LocalizedString playLabel; // assign Table+Key in Inspector
void OnEnable() => playLabel.StringChanged += s => label.text = s;
void OnDisable() => playLabel.StringChanged -= s => label.text = s;
```

Via MCP, build the UI with `manage_gameobject` + `manage_components` (uGUI) or `manage_ui` (UI Toolkit) — never raw YAML (see `unity-ui-designer`). Add `LocalizeStringEvent` as a component and set its serialized `StringReference` table/key.

## 7. Smart Strings (grammar in the table)

Tick **Smart** on the entry, then use SmartFormat (ICU-style) syntax in the value:

```
Welcome back, {playerName}!
{count:plural:one {You have # coin}|other {You have # coins}}
{gender:select:male {He} female {She} other {They}} reached level {lvl}
{score:choose(0|1):No points|One point|{} points}
```

Supply runtime values via local/persistent variables on the `LocalizedString` (e.g. `IntVariable`, `StringVariable`, an `ObjectVariable`):

```csharp
using UnityEngine.Localization.SmartFormat.PersistentVariables;
playLabel.Add("count", new IntVariable { Value = coinCount });
```

Each locale supplies its own plural categories — never build plurals/gender with C# `if`.

## 8. Number / date / currency formatting

Format with the selected locale's culture, not invariant defaults:

```csharp
var culture = LocalizationSettings.SelectedLocale.Identifier.CultureInfo;
string price = amount.ToString("C", culture); // localized currency symbol/placement
string when  = date.ToString("d", culture);   // localized date order
```

Or use Smart Strings number formatting so the table controls presentation.

## 9. Export for translators (CSV or XLIFF)

Editor: Localization Tables window ▸ select the collection ▸ **Export** ▸ **CSV** (round-trips with Google Sheets via the Google Sheets extension) or **XLIFF** (standard CAT-tool format — Trados, memoQ, Crowdin, etc.).

- **CSV** is easiest for a spreadsheet/Google-Sheets handoff; add a CSV Extension to the collection for column mapping. The Google Sheets provider can push/pull directly.
- **XLIFF** is preferred when working with professional translators / TMS — it carries metadata and keys cleanly per locale.

Translators edit only the export. They never touch Unity or code.

## 10. Import translations

Editor: Localization Tables window ▸ select collection ▸ **Import** ▸ CSV/XLIFF → pick the returned file → import. Re-import is idempotent on keys; new/changed values land in the right per-locale table. Save the project.

## 11. Fonts per script + fallback chain (no tofu)

1. Import script-covering fonts (e.g. Noto Sans CJK / Arabic / Thai, OFL-licensed) and generate `TMP_FontAsset`s — **dynamic atlas**, cap 2048² for mobile (full SDF settings in `unity-ui-designer`).
2. **Per-locale font swap:** add a `TMP_FontAsset` entry to an Asset Table and drive the label's font via `LocalizedAsset<TMP_FontAsset>` / `Localize*Event`; OR
3. **Fallback chain:** on the primary `TMP_FontAsset`, add fallbacks in priority order (Latin → CJK → Arabic → Symbols); TMP walks the list until a glyph matches.
4. Pre-warm heavy CJK screens with `TryAddCharacters()` on a loading screen to avoid runtime atlas-build hitches.

## 12. RTL (Arabic / Hebrew)

Unity Localization does **not** shape or mirror automatically.

- **Shaping:** enable TMP RTL support or add a shaping library (e.g. RTLTMPro) so Arabic glyphs connect and flow right-to-left.
- **Layout mirror:** flip horizontal anchors/alignment, reverse horizontal layout groups, move back/primary buttons to the right. Treat it as a dedicated layout pass and re-run the safe-area check.

## 13. Pseudolocalization

Editor: Locale settings ▸ add a **Pseudo-Locale** (it wraps a source locale). Add methods:

- **Expander** — pad ~+40% to expose truncation/overflow.
- **Accenter** — accented look-alikes; any plain ASCII left on screen is a hardcoded string that bypassed the tables.
- **Mirror** — smoke-test RTL/mirrored layout before real Arabic.

Select the pseudo-locale at runtime and play through every screen. Fix all leaks/truncation before sending anything to translators.

## 14. QA gates (evidence)

- Switch each shipped locale at runtime; screenshot menu/HUD/results/settings at phone resolution — real glyphs, **no tofu**.
- Longest locale (de/ru) shows no truncation/overflow; content inside safe area.
- RTL locale reads right-to-left, shaped, mirrored.
- Pseudoloc clean — no leaked ASCII.
- Numbers/dates/currency in locale format.
- Locale persists across relaunch; first run = device language.
- Hand store metadata to `unity-qa-release` / `unity-aso-growth` for per-locale listing localization.

---

## MCP / execute_code note

- **Package + settings + locales + table creation** are scriptable via `LocalizationEditorSettings` (and `LocalizationSettings` at runtime) — run them through `unity-mcp-bridge` `execute_code` (snippets above). Wrap edits with `EditorUtility.SetDirty` + `AssetDatabase.SaveAssets`.
- **UI binding** goes through `manage_gameobject` + `manage_components` (uGUI) or `manage_ui` (UI Toolkit) — add `LocalizeStringEvent` and set its serialized `StringReference`; never hand-write `.unity`/`.prefab`/`.asset` YAML (GUID/fileID-linked).
- **Export/Import and Pseudo-Locale creation** are primarily Editor-window operations; where no stable scripting API is confirmed, do them in the Localization Tables / Locale windows rather than guessing an API. After any C# compile or package change, expect the ~5s bridge drop and reconnect by focusing the Editor.
- Always confirm `mcpforunity://editor/state` `ready_for_tools==true` before a batch, and `read_console(types=["error"])` after compiles.
