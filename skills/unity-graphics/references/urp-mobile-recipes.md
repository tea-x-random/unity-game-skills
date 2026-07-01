# URP Mobile Recipes (Casual iOS)

Concrete, ordered recipes. All Editor changes go through MCP (`manage_graphics`, `manage_material`, `manage_texture`, `manage_shader`, `manage_scene`, `execute_code`), never raw YAML. Enable tools first: `manage_tools(action="enable_group", group="vfx")` and, for any shader/render C#, `manage_tools(action="enable_group", group="docs")`.

**Unity 6 note:** RenderGraph, URP Volume components, and Renderer Features changed since 2022.3. Before writing shader/render code, verify symbols with `unity_reflect` / `unity_docs`. Property names below (`UniversalRenderPipelineAsset`, `Bloom`, etc.) should be confirmed against the live Editor on 6000.x.

---

## 1. Set up / confirm URP

1. Read `mcpforunity://project/info`; check `renderPipeline`. If already URP, skip to recipe 2.
2. If missing, install the package:
   - `manage_packages(action="add", package="com.unity.render-pipelines.universal")` (then expect a domain reload — wait for `editor/state` ready, `is_compiling==false`).
3. Create a URP asset + renderer and assign it (`execute_code`):

```csharp
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEditor;

// Create a Universal Renderer + URP asset (API names: verify via unity_reflect on Unity 6).
var rendererData = ScriptableObject.CreateInstance<UniversalRendererData>();
AssetDatabase.CreateAsset(rendererData, "Assets/Settings/MobileRenderer.asset");

var urp = UniversalRenderPipelineAsset.Create(rendererData);
AssetDatabase.CreateAsset(urp, "Assets/Settings/MobileURP.asset");

GraphicsSettings.defaultRenderPipeline = urp;
QualitySettings.renderPipeline = urp;   // per active quality level
AssetDatabase.SaveAssets();
```

4. `refresh_unity(scope="all", wait_for_ready=true)`, then `manage_scene(action="screenshot")` to confirm the scene renders under URP.

---

## 2. Mobile-friendly URP asset (shadows / HDR / MSAA tradeoffs)

Tune the URP asset for phones via `manage_graphics` where exposed, else `execute_code` on `UniversalRenderPipelineAsset` (verify property names on Unity 6):

- **Render Scale:** 1.0 high-end, 0.8–0.9 low-end.
- **MSAA:** 2x is a good default for stylized edges; 4x only on new devices; Disabled on the low tier.
- **HDR:** ON only if you use Bloom/tonemapping; it costs bandwidth — turn OFF if no post.
- **Shadows:** one shadow-casting light, Cascade Count = 1, Shadow Distance short (e.g. 20–40m), Soft Shadows Low or Hard. Disable shadows entirely on the low tier (use blob shadows).
- **Additional Lights:** Per-Pixel count low (0–2) or Per-Vertex; Disabled is ideal for fully baked scenes.
- **Depth/Opaque texture:** OFF unless an effect needs them (saves a pass).

Verify: `manage_graphics(action="stats_get")` before/after; confirm SetPass/draw calls dropped.

---

## 3. Stylized unlit material (cheapest premium look)

```text
manage_tools(action="enable_group", group="vfx")
manage_material(action="create", path="Assets/<Game>/Art/Materials/Stylized_Mint.mat", shader="Universal Render Pipeline/Unlit")
manage_material(action="set_property", path="Assets/<Game>/Art/Materials/Stylized_Mint.mat",
                property="_BaseColor", value=[0.55, 0.85, 0.7, 1])
# Enable GPU instancing so shared instances batch:
manage_material(action="set_property", path="Assets/<Game>/Art/Materials/Stylized_Mint.mat",
                property="enableInstancing", value=true)
```

- For lit stylized surfaces use `Universal Render Pipeline/Lit` with low `_Smoothness`, `_Metallic=0`, and a flat `_BaseColor` (no albedo map needed).
- Keep total unique materials small; reuse this material across many objects so SRP Batcher + instancing keep SetPass calls flat.
- If a texture IS used: `manage_texture` to set ASTC compression for iOS (verify via `stats_get` it's not RGBA32 uncompressed).

---

## 4. Baked lighting workflow

1. Mark static geometry contributing to GI (`execute_code` setting `GameObjectUtility.SetStaticEditorFlags` / `StaticEditorFlags.ContributeGI`).
2. Set the directional light mode to **Baked** (or **Mixed** only if it must cast realtime shadows on movers).
3. Add a **Light Probe Group** spanning the play area so dynamic objects sample baked ambience.
4. Add **one baked Reflection Probe** near any glossy hero object (low resolution).
5. Bake:

```text
manage_graphics(action="bake_lighting")        # or the bake action exposed by the tool
# wait for bake to finish (poll editor/state / stats), then:
manage_scene(action="screenshot", include_image=true)
```

6. Confirm static geometry shows soft baked shading and movers aren't flat-lit. Re-bake after moving lights/geometry.

---

## 5. Conservative post-processing Volume

Requires URP active + post enabled on the renderer + **Post Processing** ticked on the Camera.

1. Create a global Volume GameObject and profile:

```text
manage_gameobject(action="create", name="GlobalVolume")
# Add Volume component (set isGlobal=true) and a VolumeProfile via execute_code if the
# component tool can't author the profile directly; verify Volume API on Unity 6 with unity_reflect.
```

2. Add only cheap overrides to the profile (`execute_code`, confirm types via `unity_reflect`):
   - **Tonemapping** = ACES (or Neutral).
   - **Color Adjustments** — slight contrast/saturation, post-exposure for mood.
   - **White Balance** — subtle temperature shift for warmth/coolness.
   - **Vignette** — low intensity for focus.
   - **Bloom** — low Intensity, Threshold ~1.0, applied to emissive accents only. Keep High Quality Filtering OFF on mobile.
3. **Do not add** SSAO, Depth of Field, Motion Blur, or strong Chromatic Aberration on the low/old-device tier.
4. Enable post on the camera and verify:

```text
manage_scene(action="screenshot", include_image=true)
manage_graphics(action="stats_get")     # confirm fill-rate cost didn't blow the budget
```

If the screenshot looks washed or the stats spike, dial bloom/exposure back. Tonemapping + vignette alone already lift the frame.
