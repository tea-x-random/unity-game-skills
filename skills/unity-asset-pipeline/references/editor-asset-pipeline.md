# Unity editor asset-pipeline snippets

Use these snippets via `unity-mcp-bridge` `execute_code` or promote them into `Assets/Editor/AssetPipeline/*.cs` in a real project. They are intentionally small patterns, not a complete package manager.

## 1) AssetContractTag component

Create once in the project so prefabs can carry contract provenance:

```csharp
using UnityEngine;

public sealed class AssetContractTag : MonoBehaviour
{
    public string assetId;
    public string contractPath;
    public string family;
    public string role;
    public string styleId;
}
```

## 2) ApplyAssetContract (import settings gate)

Use the contract values rather than Unity defaults. The validator must throw on mismatch instead of silently reimporting with a bad default.

```csharp
using UnityEditor;
using UnityEngine;

public static class ApplyAssetContract
{
    // settingsFromContract is built from the contract's import: block —
    // filterMode (Point for pixel art, Bilinear for non-pixel rendered sprites),
    // mipmaps, spriteMeshType, alphaIsTransparency, sprite mode. NEVER hardcode
    // these here; a hardcoded FilterMode blurs pixel art or crunches painterly art.
    public static void ApplySpriteImport(
        string assetPath,
        float pixelsPerUnit,                              // art-spec craft.pixels_per_unit (project PPU SSOT)
        TextureImporterSettings settingsFromContract,
        TextureImporterCompression defaultCompression,    // contract import.compression (Uncompressed for pixel art)
        int maxTextureSize,
        TextureImporterFormat iosFormat)
    {
        var ti = AssetImporter.GetAtPath(assetPath) as TextureImporter;
        if (ti == null) throw new System.Exception($"No TextureImporter at {assetPath}");

        settingsFromContract.textureType = TextureImporterType.Sprite;
        settingsFromContract.spritePixelsPerUnit = pixelsPerUnit;
        ti.SetTextureSettings(settingsFromContract);      // apply the contract, not Unity defaults

        // Default platform too — an iOS-only override leaves the editor/Android
        // import drifting from the contract.
        ti.textureCompression = defaultCompression;
        ti.maxTextureSize = maxTextureSize;

        ti.SetPlatformTextureSettings(new TextureImporterPlatformSettings {
            name = "iPhone",
            overridden = true,
            maxTextureSize = maxTextureSize,
            format = iosFormat,
            compressionQuality = 100
        });

        EditorUtility.SetDirty(ti);
        ti.SaveAndReimport();
        ValidateSpriteImport(assetPath, pixelsPerUnit, settingsFromContract, defaultCompression, maxTextureSize, iosFormat);
    }

    static void ValidateSpriteImport(
        string assetPath,
        float ppu,
        TextureImporterSettings expected,
        TextureImporterCompression expectedCompression,
        int maxSize,
        TextureImporterFormat expectedIosFormat)
    {
        var ti = AssetImporter.GetAtPath(assetPath) as TextureImporter;
        if (ti.textureType != TextureImporterType.Sprite) throw new System.Exception("textureType mismatch");
        if (ti.spriteImportMode != (SpriteImportMode)expected.spriteMode) throw new System.Exception("spriteImportMode mismatch");
        if (Mathf.Abs(ti.spritePixelsPerUnit - ppu) > 0.01f) throw new System.Exception("PPU mismatch");
        if (ti.filterMode != expected.filterMode) throw new System.Exception($"filterMode mismatch: realized {ti.filterMode}, contract {expected.filterMode}");
        if (ti.mipmapEnabled != expected.mipmapEnabled) throw new System.Exception("mipmap mismatch vs contract");
        if (ti.textureCompression != expectedCompression) throw new System.Exception("default-platform compression mismatch vs contract");

        var ios = ti.GetPlatformTextureSettings("iPhone");
        if (!ios.overridden || ios.maxTextureSize > maxSize) throw new System.Exception("iOS texture settings mismatch");
        // GetPlatformTextureSettings returns the REQUESTED format. Assert the
        // realized format: GetAutomaticFormat for Automatic, otherwise the request.
        var realized = ios.format == TextureImporterFormat.Automatic
            ? ti.GetAutomaticFormat("iPhone")
            : ios.format;
        if (realized != expectedIosFormat) throw new System.Exception($"iOS format mismatch: realized {realized}, contract {expectedIosFormat}");
        // Belt-and-braces: the imported Texture2D.format reflects the ACTIVE build
        // target's realized format — record it in the import QA report.
        var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
        if (tex == null) throw new System.Exception("imported Texture2D missing");
    }
}
```

For tiling/material textures, invert the defaults: `textureType=Default`, `wrapMode=Repeat`, `mipmapEnabled=true`, and do not require alpha.

## 3) GeneratePrefabFromContract

Pattern: create a GameObject, add the renderer/collider/material profile from contract, save as prefab, stamp provenance.

```csharp
using UnityEditor;
using UnityEngine;

public static class GeneratePrefabFromContract
{
    public static string CreateSpritePrefab(
        string id,
        string contractPath,
        string spritePath,
        string prefabPath,
        string materialPath,
        string family,
        string role,
        string styleId)
    {
        var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(spritePath);
        if (sprite == null) throw new System.Exception($"Missing sprite {spritePath}");
        var mat = AssetDatabase.LoadAssetAtPath<Material>(materialPath);

        var go = new GameObject(id);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        if (mat != null) sr.sharedMaterial = mat;

        // Replace with the collider type/size from the parsed contract.
        var col = go.AddComponent<CapsuleCollider2D>();
        col.isTrigger = false;

        var tag = go.AddComponent<AssetContractTag>();
        tag.assetId = id;
        tag.contractPath = contractPath;
        tag.family = family;
        tag.role = role;
        tag.styleId = styleId;

        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(prefabPath));
        var prefab = PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
        if (prefab == null) throw new System.Exception("Prefab save failed");
        return prefabPath;
    }
}
```

## 4) RenderBeautyCell

Use camera-based capture for deterministic reference frames. For Screen Space Overlay UI, use the game-view capture path in `manage_camera` rather than direct camera rendering.

```csharp
using UnityEditor;
using UnityEngine;

public static class RenderBeautyCell
{
    public static string Capture(Camera camera, string outputPath, int width = 1170, int height = 2532)
    {
        var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
        var oldTarget = camera.targetTexture;
        var oldActive = RenderTexture.active;
        camera.targetTexture = rt;
        RenderTexture.active = rt;
        camera.Render();

        var tex = new Texture2D(width, height, TextureFormat.RGBA32, false);
        tex.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        tex.Apply();
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(outputPath));
        System.IO.File.WriteAllBytes(outputPath, tex.EncodeToPNG());

        camera.targetTexture = oldTarget;
        RenderTexture.active = oldActive;
        Object.DestroyImmediate(tex);
        Object.DestroyImmediate(rt);
        AssetDatabase.Refresh();
        return outputPath;
    }
}
```

## 5) CompareReferenceFrames

Start with deterministic pixel metrics; use human review for subjective art direction only after the numeric gate passes.

```csharp
using UnityEngine;

public static class CompareReferenceFrames
{
    public static float MeanAbsoluteDifference(Texture2D a, Texture2D b)
    {
        if (a.width != b.width || a.height != b.height) throw new System.Exception("size mismatch");
        var pa = a.GetPixels32();
        var pb = b.GetPixels32();
        long total = 0;
        for (int i = 0; i < pa.Length; i++)
        {
            total += Mathf.Abs(pa[i].r - pb[i].r);
            total += Mathf.Abs(pa[i].g - pb[i].g);
            total += Mathf.Abs(pa[i].b - pb[i].b);
            total += Mathf.Abs(pa[i].a - pb[i].a);
        }
        return total / (pa.Length * 4f * 255f);
    }
}
```

## 6) BakeModelToAtlas pattern

For pre-rendered 3D → 2D sprites, create a bake scene with one camera, one lighting rig, one material profile, transparent clear color, and a turntable/animation sampler. Output to PNG atlas; then run `validate_sprite.py --require-alpha --art-spec <spec>` (fails without a resolvable art-spec; `--no-art-spec` only for exploratory bakes) and import with `SpriteImportMode.Multiple`.

## 7) Import presets + AssetPostprocessor (make correct import the default)

Do not rely on each agent remembering import settings. Create project presets such as:

```
Assets/<Game>/Art/ImportPresets/Sprite_Foreground.preset
Assets/<Game>/Art/ImportPresets/Sprite_BackgroundTile.preset
Assets/<Game>/Art/ImportPresets/UI_Icon.preset
Assets/<Game>/Art/ImportPresets/Texture_TilingMaterial.preset
```

Then use an `AssetPostprocessor` to route imports by folder/contract. The postprocessor should apply the preset first, then override contract-specific values (PPU, max size, platform format, secondary textures, atlas group metadata).

The sprite PPU comes from the project PPU SSOT (`art-spec.yaml: craft.pixels_per_unit`) — never a hardcoded number. Small cached reader:

```csharp
using System.IO;
using System.Text.RegularExpressions;

public static class ProjectArtSpec
{
    static float? _ppu;
    static bool _warned;
    // Nullable on purpose: an AssetPostprocessor has no --no-art-spec escape hatch,
    // so a missing spec must NOT throw on every pre-spec/exploratory import. It warns
    // once and leaves Unity defaults; the HARD production gates stay with
    // validate_asset_manifest.py + the ApplySpriteImport contract validator.
    public static float? PixelsPerUnitOrNull
    {
        get
        {
            if (_ppu.HasValue) return _ppu;
            // Canonical: Assets/<Game>/Art/_ArtDirection/art-spec.yaml (legacy roots
            // Assets/GameArt/ and Assets/Art/ are reserved aliases — probe all).
            foreach (var specPath in Directory.GetFiles("Assets", "art-spec.yaml", SearchOption.AllDirectories))
            {
                var m = Regex.Match(File.ReadAllText(specPath), @"pixels_per_unit:\s*([0-9.]+)");
                if (m.Success) { _ppu = float.Parse(m.Groups[1].Value); return _ppu.Value; }
            }
            if (!_warned)
            {
                _warned = true;
                UnityEngine.Debug.LogWarning(
                    "No art-spec craft.pixels_per_unit found — sprite imported with Unity-default PPU. " +
                    "Fine for pre-spec/exploratory art only; production imports require the spec " +
                    "(one game = one PPU; validate_asset_manifest.py enforces it).");
            }
            return null;
        }
    }
}
```

Routing pattern — note tilemap tiles and backgrounds are SPRITES and MUST share the project PPU (a `Default`-typed tile texture gets no PPU at all and the scene mixes pixel densities); reserve `Default`+`Repeat` for true tiling material textures only:

```csharp
using UnityEditor;

public sealed class ArtAssetPostprocessor : AssetPostprocessor
{
    void OnPreprocessTexture()
    {
        if (!assetPath.StartsWith("Assets/") || !assetPath.Contains("/Art/")) return;
        var ti = (TextureImporter)assetImporter;

        if (assetPath.Contains("/Materials/") || assetPath.Contains("/TilingTextures/"))
        {
            // True tiling/material textures only (no PPU concept).
            ti.textureType = TextureImporterType.Default;
            ti.wrapMode = UnityEngine.TextureWrapMode.Repeat;
            ti.mipmapEnabled = true;
        }
        else if (assetPath.Contains("/Tiles/") || assetPath.Contains("/Background/")
              || assetPath.Contains("/Sprites/") || assetPath.Contains("/Approved/"))
        {
            ti.textureType = TextureImporterType.Sprite;
            ti.alphaIsTransparency = true;
            ti.mipmapEnabled = false;
            var ppu = ProjectArtSpec.PixelsPerUnitOrNull;          // art-spec SSOT, never hardcoded
            if (ppu.HasValue) ti.spritePixelsPerUnit = ppu.Value;  // no spec yet: warn once, keep Unity default
        }
    }
}
```

A preset/postprocessor is not a substitute for validation; it reduces drift. The import validator still compares realized settings to the contract.

## 8) SpriteAtlas membership gate

Sprite atlases are a production gate for 2D mobile: sprites are grouped by family/layer/use-case so batching and memory behavior are predictable. Add `atlas_group` and `sprite_atlas` to each contract. Before approval, verify the sprite is packed into the expected atlas.

Suggested grouping:

- `Characters_Hero.spriteatlas`
- `Characters_Enemies.spriteatlas`
- `Environment_Midground.spriteatlas`
- `Environment_BackgroundTiles.spriteatlas`
- `UI_Icons.spriteatlas`
- `VFX_Particles.spriteatlas`

Editor pattern:

```csharp
using UnityEditor;
using UnityEditor.U2D;
using UnityEngine.U2D;

public static class AtlasGate
{
    public static void AddToAtlas(string atlasPath, string assetPath)
    {
        var atlas = AssetDatabase.LoadAssetAtPath<SpriteAtlas>(atlasPath);
        var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(assetPath);
        if (atlas == null || asset == null) throw new System.Exception("Missing atlas or asset");
        atlas.Add(new[] { asset });
        EditorUtility.SetDirty(atlas);
        AssetDatabase.SaveAssets();
    }
}
```

The BeautyCell can then use Frame Debugger/rendering stats to confirm the atlas grouping actually reduces texture swaps/draw calls.

## 9) Addressables labels (asset registry -> runtime loading)

If the project uses Addressables, the asset registry should map directly to Addressable groups/labels. The contract fields:

```yaml
addressables:
  address: art/environment/meadow_tree_a
  group: Art_Environment
  labels: [art, environment, meadow_vegetation]
```

Gate before approval:

- Addressable entry exists for `runtime.prefab`.
- Address matches contract.
- Group matches contract.
- Labels include family + role.
- Addressables Analyze has no blocking errors.

## 10) Secondary textures for 2D lighting

If the game uses URP 2D Renderer / Sprite-Lit materials, contracts must record secondary textures:

```yaml
secondary_textures:
  normal_map: Assets/<Game>/Art/Approved/tree/tree_n.png
  mask_map: Assets/<Game>/Art/Approved/tree/tree_mask.png
```

Gate before approval:

- secondary textures exist when the material profile requires them;
- normal map imported as NormalMap;
- mask map imported as Default/linear as appropriate;
- SpriteRenderer material/shader matches the material profile;
- BeautyCell LightingTest proves the asset reacts consistently to the shared 2D lights.

Do not generate normal/mask maps for a flat unlit style unless the art-spec says the style uses 2D lighting; this is a capability gate, not a universal requirement.

## 11) Strip slicing on Unity 6000.5 (ISpriteEditorDataProvider)

The Sprite Editor data API is the current way to slice animation strips headlessly. Exact requirements (verified against the live 2d.sprite package on 6000.5):

- The consuming Editor asmdef MUST reference **`Unity.2D.Sprite.Editor`** (namespace `UnityEditor.U2D.Sprites`) — the types are not in `UnityEditor` proper.
- Set the importer to `SpriteImportMode.Multiple` (via `TextureImporterSettings`) and `SaveAndReimport()` FIRST, then run the data provider pass, `Apply()`, and `SaveAndReimport()` again.
- Every new `SpriteRect` needs `spriteID = GUID.Generate()` — a default GUID produces broken sub-assets.
- Pair names to IDs with **`new SpriteNameFileIdPair(name, guid)`** — the `long fileId` constructor/property is **obsolete** on 6000.5 (`GetFileGUID`/`SetFileGUID` replace it).
- Register the pairs via **`ISpriteNameFileIdDataProvider.SetNameFileIdPairs`** so name→fileID stays stable and scene/prefab/AnimationClip references survive reimports.

```csharp
var factory = new SpriteDataProviderFactories();
factory.Init();
var dp = factory.GetSpriteEditorDataProviderFromObject(textureImporter);
dp.InitSpriteEditorDataProvider();
var rects = Enumerable.Range(0, frameCount).Select(i => new SpriteRect {
    name = $"{baseName}_{i}",
    rect = new Rect(i * frameW, 0, frameW, frameH),
    alignment = SpriteAlignment.Custom, pivot = new Vector2(0.5f, 0f),
    spriteID = GUID.Generate()
}).ToArray();
dp.SetSpriteRects(rects);
dp.GetDataProvider<ISpriteNameFileIdDataProvider>()
  ?.SetNameFileIdPairs(rects.Select(r => new SpriteNameFileIdPair(r.name, r.spriteID)));
dp.Apply();
textureImporter.SaveAndReimport();
```

Then verify: `AssetDatabase.LoadAllAssetsAtPath(path).OfType<Sprite>()` has the expected count AND names — log FAIL lines on mismatch.

## 12) URP 2D batcher headless texture-binding rule: one Sprite-Unlit material per asset

Observed on 6000.5 + URP 17.5, batch-mode renders (edit-mode `StandardRequest` captures AND PlayMode): SpriteRenderers **sharing one material** (the default `Sprite-Lit-Default`) with different sprite textures get merged into one draw that binds the FIRST batch texture — every sprite in the frame renders with the background's texture. Sprite/texture references are all correct; the merge is the bug, and nothing errors.

**Rule:** assign **one material per asset** using the art-spec shader family (`Universal Render Pipeline/2D/Sprite-Unlit-Default`) with the asset's texture pre-bound as `mainTexture`. Instantiate from the package template `Packages/com.unity.render-pipelines.universal/Runtime/Materials/Sprite-Unlit-Default.mat`, save under `Assets/<Game>/Materials/<asset_id>.mat`, set `SpriteRenderer.sharedMaterial` in the prefab factory. Distinct materials cannot be merged across assets; per-sprite textures within ONE asset's material (animation strips) still bind correctly. This also satisfies the art-spec mobile budget (`max_materials_per_prop: 1`) and Unlit needs no Light2D.

## 13) Scene art references must go THROUGH registry prefab instances

`check_scene_registry.py` allows a scene art reference (guid with an art extension: .png/.mat/.prefab/…) ONLY if it is a registry prefab or a file inside a registered asset's approved folder. Consequences for scene assembly:

- A plain scene GameObject whose SpriteRenderer references a project-local `.mat` or approved `.png` **directly** puts that guid in the `.unity` file — a `.mat` under `Assets/<Game>/Materials/` FAILS the gate.
- **Reference art only through registry prefab INSTANCES.** A prefab instance serializes just `m_SourcePrefab` (the registry prefab guid — allowed); the sprite/material references stay inside the prefab file, which the gate does not scan.
- **Instance overrides with plain values are safe**: e.g. a tiled ground band = the `StoneTile` registry prefab instantiated with `drawMode = Tiled`, `size = (22, 3)` overrides — no guid enters the scene. Never rebuild the same visual as a raw scene SpriteRenderer to "save a prefab".
