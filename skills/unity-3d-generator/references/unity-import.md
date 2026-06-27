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
var p = "Assets/Art/Models/hero/hero.fbx";
var imp = (UnityEditor.ModelImporter)UnityEditor.AssetImporter.GetAtPath(p);
imp.globalScale = 1.0f;                 // fix Tripo scale if needed
imp.isReadable = false;                 // saves memory unless mesh is read at runtime
imp.meshCompression = UnityEditor.ModelImporterMeshCompression.Medium;
imp.importBlendShapes = false;          // most casual assets don't need them
// Characters (biped, Mixamo-style): humanoid avatar so clips retarget
imp.animationType = UnityEditor.ModelImporterAnimationType.Human;   // creatures: .Generic
imp.SaveAndReimport();
return "configured " + p;
```

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

## Step 4 — make it a prefab and place it

```text
manage_gameobject(action="create", prefab_path="Assets/Art/Models/hero/hero.fbx", name="Hero")
manage_components(...)                      # add Collider / Rigidbody / gameplay scripts
manage_prefabs(action="create_from_gameobject", ...)   # save reusable prefab
```

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
