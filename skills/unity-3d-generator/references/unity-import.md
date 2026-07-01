# Importing generated 3D assets into Unity

Everything here runs through `unity-mcp-bridge`. The Editor must be open and `editor/state` ready.

## Format choice

- **FBX** imports natively — best for rigged/animated characters. Tripo v1.0-rig retargets export correct FBX.
- **GLB/glTF** needs **glTFast** (`com.unity.cloud.gltfast`). If absent, either add the package (`manage_packages`) or convert GLB→FBX offline. GLB is fine for static props once glTFast is present.

## Step 1 — get it into the project

Download placed the file under `Assets/...`. Then:
```text
refresh_unity(scope="assets", wait_for_ready=true)
read_console(types=["error"])     # confirm import had no errors
```

## Step 2 — configure import settings via execute_code (defaults are wrong for mobile)

`manage_asset(action="import")` only reimports; it cannot set importer properties. Drive `ModelImporter` directly:

```csharp
// execute_code payload (enable scripting_ext group first)
var p = "Assets/<Game>/Art/Source/TripoRaw/hero/hero.fbx";
var imp = (UnityEditor.ModelImporter)UnityEditor.AssetImporter.GetAtPath(p);
imp.globalScale = 1.0f;                 // provisional — the scale gate (Step 2b) computes the real value
imp.isReadable = false;                 // saves memory unless mesh is read at runtime
imp.meshCompression = UnityEditor.ModelImporterMeshCompression.Medium;
imp.importBlendShapes = false;          // most casual assets don't need them
// Characters (biped, Mixamo-style): humanoid avatar so clips retarget
imp.animationType = UnityEditor.ModelImporterAnimationType.Human;   // creatures: .Generic
imp.SaveAndReimport();
return "configured " + p;
```

## Step 2b — scale gate: measure bounds vs the art-spec `scale` block (mandatory, FAIL out-of-range)

Tripo model scale is arbitrary — never trust `globalScale = 1.0`. The art-spec `scale` block is the SSOT (`unit_rule: 1 Unity unit = 1 meter`, `character_height_m`, `standard_door_height_m`; props use the AssetBrief's `scale_m`). After every (re)import, measure the realized bounds and gate:

```csharp
// execute_code payload — measure realized height, enforce the role's target ±15%
var p = "Assets/<Game>/Art/Source/TripoRaw/hero/hero.fbx";  // same staged file as Step 2
float target = 1.5f;   // from art-spec scale block: characters → scale.character_height_m,
                       // doors → scale.standard_door_height_m, props → AssetBrief scale_m (Y)
var go = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.GameObject>(p);
var inst = (UnityEngine.GameObject)UnityEngine.Object.Instantiate(go);
var b = new UnityEngine.Bounds(inst.transform.position, UnityEngine.Vector3.zero);
foreach (var r in inst.GetComponentsInChildren<UnityEngine.Renderer>()) b.Encapsulate(r.bounds);
UnityEngine.Object.DestroyImmediate(inst);
float h = b.size.y;    // meters, per scale.unit_rule
if (h < target * 0.85f || h > target * 1.15f) {
    var imp = (UnityEditor.ModelImporter)UnityEditor.AssetImporter.GetAtPath(p);
    imp.globalScale *= (h > 0f ? target / h : 1f);
    imp.SaveAndReimport();
    return "SCALE FAIL: " + h + "m vs target " + target + "m — globalScale corrected, RE-RUN this gate";
}
return "scale OK: " + h + "m (target " + target + "m)";
```

The gate is a **fail step**, not a log line: an out-of-range model must not proceed to prefab/contract until a re-measure passes. (No art-spec / exploratory work: skip with an explicit note that scale is unlocked.)

## Step 3 — textures: ASTC for iOS

The build path can force the wrong compression on mobile. Set an explicit iOS platform override on the model's textures (or the extracted textures):
```csharp
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(texPath);
var s = new UnityEditor.TextureImporterPlatformSettings {
    name = "iPhone", overridden = true,
    format = UnityEditor.TextureImporterFormat.ASTC_6x6,  // 6x6 good default; 4x4 for hero, 8x8 for backgrounds
    maxTextureSize = 1024, compressionQuality = 100
};
ti.SetPlatformTextureSettings(s);
ti.SaveAndReimport();
```

## Step 3b — re-shade to the spec (materials must converge)

Imported Tripo PBR rarely matches the game's locked look. Converge to the art-spec's `materials` (`response`, `roughness_range`, `metallic_usage`, `texture_language`) and `rendering.shader_family`:

- **Unity-side (default):** swap imported materials to the project's shared `shader_family` material(s) and clamp `_Smoothness`/`_Metallic` into the spec ranges via `manage_material`.
- **Source-side (baked texture itself off-style):** re-texture with a Tripo `texture_model` postprocess — `unity_3d_asset.py postprocess --type texture_model --original-task-id <gen_task> --texture-prompt "<verbatim spec style tokens>"` — then re-download and reimport.

Raw Tripo PBR next to flat/cel 2D fails the `unity-aaa-graphics` finish-consistency axis; this step is part of import, not optional polish.

## Step 4 — contract → prefab factory → registry (production)

Production models do NOT get hand-wrapped into scene prefabs. Route through `unity-asset-pipeline`:

1. Write `asset-contract.yaml` (id, family, role, `style_id`, source provenance, `runtime` prefab path/collider/material_profile, `camera_contract`).
2. `validate_asset_manifest.py <contract> --art-spec <spec>` must exit 0.
3. **ApplyAssetContract** → **GeneratePrefabFromContract** (attaches collider, shared material, shadow profile; saves to `runtime.prefab`) → registry entry in `Assets/<Game>/Art/Approved/registry.yaml`.
4. Scene builders instantiate the REGISTRY prefab only — never the raw FBX/GLB.

Standalone/exploratory (no pipeline): `manage_gameobject(action="create", prefab_path=...)` + `manage_components(...)` + `manage_prefabs(action="create_from_gameobject", ...)` is allowed, but the result is a flagged placeholder — not an approved asset.

## Step 5 — animation (Mecanim)

1. Imported clips live inside the FBX. Confirm names: `manage_asset(action="get_info", ...)` or inspect via `execute_code`.
2. Create an **Animator Controller**, add states for each clip, wire transitions (parameters: `Speed`, `Grounded`, `Jump`...).
3. Add an `Animator` component to the prefab referencing the controller.
4. Strip Tripo root motion at the gameplay layer (don't bake in-place at generation): zero only the horizontal root translation, keep vertical (jump/gait bob). Drive locomotion from code.
5. Verify in Play Mode + screenshot; check the clip plays without limb stretching (`validate-animation` flagged none).

## Mobile budgets (casual iOS)

- Keep per-asset triangles modest; use `--face-limit` / low-poly postprocess at generation time.
- Share/atlas materials; enable **GPU instancing** on materials used by repeated props.
- Turn off Read/Write and blendshapes you don't use; prefer Medium/High mesh compression.
- Hero models can carry detail; repeated background props should be cheap or instanced.
