# Headless / batch-mode Editor recipes (no MCP)

Proven end-to-end on a real Unity **6000.5.0f1** build (URP 17.5.0, Input System 1.19.0): scene built,
EditMode+PlayMode tests green, and screenshots captured entirely via
`Unity -batchmode [-quit] -projectPath <p> -executeMethod <Class.Method> -logFile <log>`.
These are the traps and the exact APIs that avoid them.

## Batch-run mechanics

- **First batch run is slow (~4 min):** package resolve + full import (~2600 files). Later runs are fast.
- **`Library/PackageCache` dirs are content-hashed, not versioned** (`com.unity.render-pipelines.universal@0c18adc4ff89`) — locate packages by name prefix, never by version string.
- **Licensing handshake errors in the log are noise** (`[Licensing::Client] Error: HandshakeResponse…`) when the process exits 0. Gate on `error CS`, `Exception`, `Safe Mode`, and your own `[Tag]` log lines instead.
- **NEVER run two Unity batch processes on one project simultaneously** — runs are serialized (build → EditMode → PlayMode). `-runTests` must NOT be combined with `-quit`.
- Pin package versions to the **editor's own recommendations**: read `<Editor>/Unity.app/Contents/Resources/PackageManager/Editor/manifest.json` (`packages.<id>.version`). It is also where deprecations show up (e.g. `com.unity.textmeshpro` is deprecated on 6000.5 — TMP ships inside `com.unity.ugui`).

## URP 17.5 asmdef split (Unity 6.5)

`Renderer2DData` and the URP `PixelPerfectCamera` moved to a **separate asmdef**:
`Unity.RenderPipelines.Universal.2D.Runtime`. The namespace is unchanged
(`UnityEngine.Rendering.Universal`), so the compile error is a bare CS0246 with no hint. Reference
**both** `Unity.RenderPipelines.Universal.Runtime` and `Unity.RenderPipelines.Universal.2D.Runtime`
(plus `Unity.RenderPipelines.Core.Runtime` for `ResourceReloader`) in any asmdef touching 2D URP types.

## Activate URP headless (no editor UI)

```csharp
var rendererData = ScriptableObject.CreateInstance<Renderer2DData>();
// populate its [Reload] shader/material defaults (public static, core RP assembly):
Type.GetType("UnityEngine.Rendering.ResourceReloader, Unity.RenderPipelines.Core.Runtime")
    ?.GetMethod("ReloadAllNullIn", BindingFlags.Public | BindingFlags.Static)
    ?.Invoke(null, new object[] { rendererData, "Packages/com.unity.render-pipelines.universal" });
AssetDatabase.CreateAsset(rendererData, rendererPath);

// URP's own factory initializes defaults — public static on 17.5, call directly or via reflection:
var pipeline = UniversalRenderPipelineAsset.Create(rendererData);
AssetDatabase.CreateAsset(pipeline, pipelinePath);

// global settings asset (internal static Ensure(bool canCreateNewAsset = true)) — reflection:
typeof(UniversalRenderPipelineAsset).Assembly
    .GetType("UnityEngine.Rendering.Universal.UniversalRenderPipelineGlobalSettings")
    ?.GetMethod("Ensure", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
    ?.Invoke(null, new object[] { true });   // auto-creates Assets/UniversalRenderPipelineGlobalSettings.asset

GraphicsSettings.defaultRenderPipeline = pipeline;   // + set QualitySettings.renderPipeline per quality level
```

The only log this produces is an informational "URP Global Settings Asset has been created" — not an error.

## NewScene invalidates prefab-asset references (silent `{fileID: 0}`)

`EditorSceneManager.NewScene(...)` unloads unused assets. A prefab **component reference held in a
C# local** from before the call (e.g. the return of `SaveAsPrefabAsset(...).GetComponent<T>()`)
becomes a destroyed wrapper — `SerializedObject` wiring silently writes **null** and the scene saves
`goblinPrefab: {fileID: 0}` with zero errors. Rules:

1. Build prefabs first; **reload their components with `AssetDatabase.LoadAssetAtPath<T>(path)` AFTER
   `NewScene`, immediately before `SerializedObject` wiring.**
2. Always finish with a **post-save VerifyWired pass** that fails loudly:

```csharp
static void VerifyWired(UnityEngine.Object target, params string[] fields)
{
    var so = new SerializedObject(target);
    foreach (string f in fields)
    {
        var p = so.FindProperty(f);
        if (p == null || p.objectReferenceValue == null)
            Debug.LogError($"[SceneBuilder] WIRING NULL: {target.GetType().Name}.{f}");
    }
}
```

## ImportPackage is async — it no-ops under `-batchmode -quit`

`AssetDatabase.ImportPackage(path, false)` queues an async import that never completes before
`-quit` kills the process — **and logs nothing**. Use the internal synchronous variant and verify:

```csharp
typeof(AssetDatabase).GetMethod("ImportPackageImmediately", BindingFlags.NonPublic | BindingFlags.Static)
    ?.Invoke(null, new object[] { Path.GetFullPath(packagePath) });
AssetDatabase.Refresh();
if (AssetDatabase.LoadAssetAtPath<Object>(expectedAssetPath) == null)
    Debug.LogError("import FAILED — expected asset missing");   // never trust the call alone
```

(Canonical use case: TMP Essential Resources from `Packages/com.unity.ugui/Package Resources/`.)

## Headless screenshots (URP on Metal works)

`Camera.Render()` is not the SRP path. Use the Unity 6 render request — it renders correctly
headless on Metal under URP, edit mode and play mode:

```csharp
var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
var request = new RenderPipeline.StandardRequest { destination = rt };
if (RenderPipeline.SupportsRenderRequest(camera, request))
    RenderPipeline.SubmitRenderRequest(camera, request);
RenderTexture.active = rt;  // then ReadPixels -> EncodeToPNG
```

- **Screen-Space-Overlay UI is NOT included** in camera RT captures (expected — it draws to the screen).
- Always assert the PNG is **non-black** (sample pixels) — "file exists" is not evidence.
- Related trap when compositing sprites headless: see the URP 2D batcher texture-binding rule in
  `unity-asset-pipeline/references/editor-asset-pipeline.md` (one Sprite-Unlit material per asset).

## Pre-flight: the project lock

An open Editor (user launched via Hub) holds the project lock; batch runs then die at startup
with exit 1 and only a misleading "Package Manager server was shutdown" in the log — no explicit
lock error. ALWAYS pre-flight: `pgrep -fl Unity | grep <project-name>` and coordinate with the
user before killing anything (their unsaved scene edits die with the process).

## Capturing UI headless

Screen-Space-Overlay canvases never appear in camera RT captures (no game view in batch). To
produce UI-inclusive evidence: temporarily switch the canvas to Screen-Space-Camera (assign the
game camera, plane distance ~1), render via RenderPipeline.SubmitRenderRequest(StandardRequest),
then restore Overlay mode. State in the report which capture path was used.

## Long lock-waits and background-task caps

Waiting out a project lock inside one capped background shell gets killed mid-wait (exit 144)
with unflushed progress. Split the retry from the execution (short probe runs, or a Monitor-style
until-loop), and treat the user's live Editor as a first-class scheduling constraint: probe
`pgrep -f "projectpath <project>"` before every batch chain, and coordinate with the user —
never kill their session.

## Contract-driven frame counts (zero-touch strip revisions)

A frame-count change on an animation strip ripples through three editor-script sites (importer
slice count, clip keyframes, import-verify names). Read `animation.clips[].frames` (and fps/loop)
from the asset-contract YAML in the editor scripts instead of hardcoding — regenerated strips
then re-import with zero code edits. Reusable runtime patterns proven here: single pooled VFX
instance keyed to an action cooldown (cooldown > VFX lifetime = no pool bookkeeping), and
hitstop via the game loop's OWN clock (drain dt, never Time.timeScale) — deterministic,
test-friendly, and right for turn/card games too.
