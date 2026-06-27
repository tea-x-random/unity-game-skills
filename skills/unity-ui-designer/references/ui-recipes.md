# UI Recipes — casual iOS, via unity-mcp-bridge

All Editor changes go through MCP. Enable the group once per session and confirm readiness:

```text
manage_tools(action="enable_group", group="ui")            # exposes manage_ui (UI Toolkit)
read mcpforunity://editor/state  -> ready_for_tools==true, is_compiling==false
read mcpforunity://project/info  -> branch on uiToolkit vs uGUI/TMP
```

Phone test resolution used below: **1080x1920** portrait (also re-check 1170x2532 tall and 1536x2048 short).

---

## A) UI Toolkit — HUD + Win screen (UXML + USS via manage_ui)

### HUD UXML (`Assets/UI/HUD.uxml`)

```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="root" class="safe-root">
    <ui:VisualElement name="top-bar" class="top-bar">
      <ui:Label name="score" text="0" class="score" />
      <ui:VisualElement class="coin-pill">
        <ui:VisualElement class="coin-icon" />
        <ui:Label name="coins" text="0" class="coin-count" />
      </ui:VisualElement>
    </ui:VisualElement>
    <ui:VisualElement class="spacer" />
    <ui:VisualElement name="bottom-bar" class="bottom-bar">
      <ui:Button name="pause-btn" class="icon-btn" />
    </ui:VisualElement>
  </ui:VisualElement>
</ui:UXML>
```

### HUD USS (`Assets/UI/HUD.uss`) — flexbox + percentage, safe-area padding

```css
.safe-root {
  flex-grow: 1; flex-direction: column;
  /* runtime SafeArea helper overwrites these paddings from Screen.safeArea */
  padding-top: 48px; padding-bottom: 34px; padding-left: 16px; padding-right: 16px;
}
.top-bar { flex-direction: row; justify-content: space-between; align-items: flex-start; }
.spacer { flex-grow: 1; }
.bottom-bar { flex-direction: row; justify-content: flex-end; align-items: flex-end; }
.score { font-size: 64px; -unity-font-style: bold; color: rgb(255,255,255); }
.coin-pill { flex-direction: row; align-items: center; padding: 8px 16px;
  background-color: rgba(0,0,0,0.4); border-radius: 24px; }
.coin-icon { width: 32px; height: 32px; background-image: url("project://database/Assets/UI/coin.png"); }
.coin-count { font-size: 36px; color: rgb(255,221,87); margin-left: 8px; }
.icon-btn { width: 96px; height: 96px; border-radius: 24px; }   /* 96px @2x >= 44pt */
```

### Win screen USS additions (popup scale-in)

```css
.dim { position: absolute; left:0; top:0; right:0; bottom:0; background-color: rgba(0,0,0,0.6); }
.win-card { width: 80%; align-self: center; padding: 32px; border-radius: 32px;
  background-color: rgb(34,40,56); scale: 0.6 0.6; transition: scale 0.25s ease-out; }
.win-card.show { scale: 1 1; }            /* toggle .show class in C# to play scale-in */
.cta { height: 110px; border-radius: 28px; font-size: 40px; }   /* >=44pt, thumb zone */
```

### Ordered MCP calls (UI Toolkit)

```text
1. manage_ui(action="create", path="Assets/UI/HUD.uxml", ...)      # author UXML
2. manage_ui(action="create", path="Assets/UI/HUD.uss", ...)       # author USS
3. manage_gameobject(action="create", name="HUDDocument")
4. manage_components(action="add", target="HUDDocument", component="UIDocument")
   -> set sourceAsset = Assets/UI/HUD.uxml, PanelSettings (scale-with-screen, ref 1080x1920)
5. create_script HudController.cs  -> SetScore/SetCoins, ShowWin (AddToClassList("show"))
   -> wait is_compiling==false -> read_console(types=["error"]) clean
6. manage_components(action="add", target="HUDDocument", component="SafeAreaUITK")  # padding helper
7. manage_components(action="add", target="HUDDocument", component="HudController")
8. manage_editor(action="play") -> trigger win -> manage_scene(action="screenshot")
```

---

## B) uGUI — HUD + Win screen (manage_gameobject + manage_components)

Hierarchy to build:

```text
Canvas (Canvas + CanvasScaler + GraphicRaycaster)
 └ SafeArea (RectTransform + SafeArea.cs, stretched full screen)
    ├ TopBar (anchored top-stretch)
    │   ├ ScoreText (TextMeshProUGUI, anchored top-left)
    │   └ CoinPill (Image) -> CoinIcon (Image) + CoinText (TextMeshProUGUI)
    ├ BottomBar (anchored bottom)
    │   └ PauseButton (Button + Image, >= 88x88 px)
    └ WinPanel (inactive) -> Dim (Image) + Card -> Title + ContinueButton (Button, h=110)
```

### Canvas Scaler config (set via manage_components)

```text
CanvasScaler.uiScaleMode      = ScaleWithScreenSize
CanvasScaler.referenceResolution = (1080, 1920)
CanvasScaler.screenMatchMode  = MatchWidthOrHeight
CanvasScaler.matchWidthOrHeight = 0.5     # bias 0..1 toward width for portrait
```

### Ordered MCP calls (uGUI)

```text
1. manage_gameobject(action="create", name="Canvas")
   manage_components(action="add", target="Canvas", component="Canvas")          # renderMode=ScreenSpaceOverlay
   manage_components(action="add", target="Canvas", component="CanvasScaler")    # config above
   manage_components(action="add", target="Canvas", component="GraphicRaycaster")
2. create_script SafeArea.cs (snippet in SKILL.md) -> compile clean
   manage_gameobject(action="create", name="SafeArea", parent="Canvas")
   manage_components(action="add", target="SafeArea", component="SafeArea")       # full-screen RectTransform
3. Build TopBar/BottomBar/children with manage_gameobject; add TextMeshProUGUI / Image / Button
   via manage_components. Set anchors per element (top-left, bottom, etc).
4. PauseButton/ContinueButton RectTransform size >= 88x88 (>=44pt @2x); spacing between buttons.
5. WinPanel starts SetActive(false); HudController shows it + count-up score.
6. manage_editor(action="play") -> trigger states -> manage_scene(action="screenshot") @ 1080x1920
```

---

## C) SafeArea C# component (uGUI) — full file

```csharp
using UnityEngine;

[RequireComponent(typeof(RectTransform))]
public class SafeArea : MonoBehaviour {
    RectTransform rt;
    Rect lastSafe;
    Vector2Int lastRes;

    void Awake() { rt = GetComponent<RectTransform>(); Apply(); }

    void Update() {
        if (Screen.safeArea != lastSafe ||
            Screen.width != lastRes.x || Screen.height != lastRes.y)
            Apply();
    }

    void Apply() {
        lastSafe = Screen.safeArea;
        lastRes  = new Vector2Int(Screen.width, Screen.height);

        Vector2 min = lastSafe.position;
        Vector2 max = lastSafe.position + lastSafe.size;
        min.x /= Screen.width;  min.y /= Screen.height;
        max.x /= Screen.width;  max.y /= Screen.height;

        rt.anchorMin = min;
        rt.anchorMax = max;
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
    }
}
```

### SafeArea helper for UI Toolkit (padding the root)

```csharp
using UnityEngine;
using UnityEngine.UIElements;

[RequireComponent(typeof(UIDocument))]
public class SafeAreaUITK : MonoBehaviour {
    VisualElement root; Rect last;
    void OnEnable() { root = GetComponent<UIDocument>().rootVisualElement.Q("root"); Apply(); }
    void Update() { if (Screen.safeArea != last) Apply(); }
    void Apply() {
        last = Screen.safeArea;
        var s = Screen.safeArea;
        root.style.paddingTop    = s.yMin;                 // y is bottom-up
        root.style.paddingBottom = Screen.height - s.yMax;
        root.style.paddingLeft   = s.xMin;
        root.style.paddingRight  = Screen.width - s.xMax;
    }
}
```

---

## D) Design tokens + shared widget factories (runtime-built UI)

For a runtime-constructed UI (an `AppRoot` builder + `GameTheme` token object), centralize tokens on the theme and create every widget through ONE factory that reads them. This is what stops menu/text drift.

### Token layer on the theme

```csharp
public sealed class GameTheme : ScriptableObject {
    public enum Type { Display, Title, Heading, Subhead, Body, Label, Caption }
    // Typography scale — the ONLY font sizes in the project
    public float typeDisplay=78, typeTitle=56, typeHeading=44, typeSubhead=32,
                 typeBody=30, typeLabel=26, typeCaption=22;
    public float Size(Type t) => t switch {
        Type.Display=>typeDisplay, Type.Title=>typeTitle, Type.Heading=>typeHeading,
        Type.Subhead=>typeSubhead, Type.Body=>typeBody, Type.Label=>typeLabel, _=>typeCaption };
    // Spacing scale, radii, touch target
    public float spaceXs=4, spaceS=8, spaceM=16, spaceL=24, spaceXl=32, spaceXxl=48;
    public float radiusS=12, radiusM=20, radiusL=32, touchMin=88; // 88px @2x = 44pt
    // Semantic color roles (extend the existing palette)
    public Color textPrimary, textMuted, textOnColor, panel, accent, conflict, success;
}
```

### One shared factory per widget (used by EVERY screen)

```csharp
// The ONLY way text is created — call sites pass a ROLE, never a number.
static TMP_Text Label(Transform parent, string text, GameTheme.Type role,
                      Color color, TextAlignmentOptions align) {
    var go = new GameObject("Label", typeof(RectTransform));
    go.transform.SetParent(parent, false);
    var t = go.AddComponent<TextMeshProUGUI>();
    t.text = text; t.fontSize = theme.Size(role);   // <- token, not literal
    t.color = color; t.alignment = align; t.raycastTarget = false;
    return t;
}
// Button/Card/IconButton apply theme radius/spacing/touchMin internally; no screen styles inline.
```

Rules: no call site passes a raw size; no screen news up a raw `TextMeshProUGUI`/`Image`/`Button`; do NOT fork `Label` per screen (the example game had three → drift). Restyling = edit the one factory.

### Strings: one provider

```csharp
// Every label shown on 2+ screens lives here, not as literals at call sites.
public static class Labels {
    public static string Difficulty(Difficulty d) => /* one switch */ ...;
}
// Later: swap this switch for a per-locale .json/.strings table — localization seam, zero call-site changes.
```

---

## E) TMP font for international text (CJK) — dynamic atlas, set as default

Decide required scripts UP FRONT (LiberationSans default = tofu for CJK). Build a dynamic-atlas SDF asset and make it the project default so all text inherits it.

```csharp
// Editor/loader code (runs via execute_code or an editor tool — not a committed runtime path):
// 1. Build a DYNAMIC TMP_FontAsset for crisp SDF + runtime glyphs.
var fa = TMP_FontAsset.CreateFontAsset(
    sourceFont,                 // e.g. a Noto family font (OFL, covers the required script) — verify it has the script
    samplingPointSize: 110,     // high for crisp display type (Unity baseline 50–70 for plain Latin)
    atlasPadding: 11,           // ~1:10 of sampling; room for SDF gradient
    UnityEngine.TextCore.LowLevel.GlyphRenderMode.SDFAA,
    atlasWidth: 2048, atlasHeight: 2048,  // cap 2048² for mobile
    AtlasPopulationMode.Dynamic,          // adds arbitrary glyphs at runtime + multi-atlas fallback
    enableMultiAtlasSupport: true);
// 2. Set it as the project TMP DEFAULT so every label inherits it (no per-label font).
var so = new UnityEditor.SerializedObject(TMP_Settings.instance);
so.FindProperty("m_defaultFontAsset").objectReferenceValue = fa;
so.ApplyModifiedProperties();
// 3. (Mixed scripts) add fallbacks in priority order on fa.fallbackFontAssetTable: Latin -> CJK -> Symbols.
// 4. (Many glyphs at once) pre-warm on a loading screen: fa.TryAddCharacters("...needed glyphs...");
```

After wiring, **screenshot a screen with the required script** and confirm real glyphs, not □ tofu. The example game regenerated this asset several times for crispness — settle it once, up front.

---

## Notes

- Coordinate updates with `mcpforunity://editor/state`; expect a ~5s domain-reload drop after each compile — wait and retry.
- Reference asset paths in USS via `url("project://database/Assets/...")`; import sprites/icons first (pair with `unity-image-generator`).
- For uGUI text always use **TextMeshProUGUI**, never legacy `UnityEngine.UI.Text`.
- Always finish with a `manage_scene(action="screenshot")` at phone resolution and re-check one tall + one short aspect.
