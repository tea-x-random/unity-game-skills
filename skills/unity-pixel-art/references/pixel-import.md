# Unity import for pixel art

Pixel art fails quickly when Unity imports it like a photo. Apply these settings before approval.

## One pixel density — the texel-density law (generation-side, enforced at import)

The top cause of "sprites look pasted on" is **mixels** — mixed pixel densities. Hard rules:

- **One game = one PPU**, read from `art-spec craft.pixels_per_unit` (project SSOT; contract `runtime.pixels_per_unit` is the no-spec fallback). Never pick a local value per asset.
- **Generate at matched density:** ground/tile texel size must equal sprite pixel size — a 16px-per-tile world takes 16px-density characters (`craft.tile_size` × `craft.char_tiles` canvases), not a 64px-detailed hero on 16px tiles. This is fixed at GENERATION time; import cannot repair it.
- **No runtime non-integer scaling** of pixel sprites (scale 1 at the correct PPU; integer camera zoom only).
- **One light model:** sprites and the ground/3D surfaces they stand on share the spec's `craft.light_direction`; don't mix a top-lit floor with left-lit characters.

## Real transparency (only if a source lacks true alpha)

PixelLab `--no-background` outputs real alpha — use it. For sources WITHOUT true alpha (Gemini concepts, painterly/HD-2D sprites — Gemini's "transparent background" does NOT work; it paints a checkerboard), chroma-key:

1. Generate on a solid chroma background ("entire background completely filled with solid flat pure magenta RGB 255 0 255, uniform, no checkerboard, no gradient, no ground shadow"); use **cyan** for magenta/pink subjects — never a color the subject wears.
2. Key by the **measured** background color, not the assumed one: median-sample the four corners (~20×20 px), then set alpha=0 where `distance(pixel, bgColor) < ~70` (models drift — ask for pure magenta, get rose).
3. **Autocrop to the alpha bbox** (a few px pad) so a bottom-center pivot lands exactly at the feet.

## TextureImporter settings

```csharp
var path = "Assets/<Game>/Art/Approved/hero_walk/hero_walk.png";
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(path);
ti.textureType = UnityEditor.TextureImporterType.Sprite;
ti.spritePixelsPerUnit = 32; // = art-spec craft.pixels_per_unit (project PPU SSOT); contract runtime.pixels_per_unit when no spec exists
ti.filterMode = UnityEngine.FilterMode.Point;
ti.mipmapEnabled = false;
ti.textureCompression = UnityEditor.TextureImporterCompression.Uncompressed;
ti.alphaIsTransparency = true;
ti.spriteImportMode = UnityEditor.SpriteImportMode.Multiple; // Single for one sprite
ti.wrapMode = UnityEngine.TextureWrapMode.Clamp;
var s = new UnityEditor.TextureImporterPlatformSettings {
    name = "iPhone",
    overridden = true,
    maxTextureSize = 512,
    format = UnityEditor.TextureImporterFormat.RGBA32,
    compressionQuality = 100
};
ti.SetPlatformTextureSettings(s);
ti.SaveAndReimport();
```

Use `wrapMode = Repeat` only for tile textures/materials that intentionally repeat.

## Sheet slicing contract

For each generated sheet, record:

```yaml
sprite_sheet:
  rows: 4
  cols: 8
  cell_size: [32, 32]
  padding: 2
  extrude: 2
  clips:
    idle: { row: 0, frames: 4, fps: 6, loop: true }
    walk: { row: 1, frames: 8, fps: 10, loop: true }
  pivot: bottom_center
  ppu: 32
```

Slice from the post-extruded manifest so Unity uses the actual cell rect and ignores duplicated border pixels.

## Pixel Perfect Camera

Install `com.unity.2d.pixel-perfect` when the camera renders pixel art. Add a Pixel Perfect Camera component and align the art contract to it:

```csharp
var cam = UnityEngine.Camera.main;
var ppcType = System.Type.GetType("UnityEngine.U2D.PixelPerfectCamera, Unity.2D.PixelPerfect");
if (cam != null && ppcType != null && cam.GetComponent(ppcType) == null) {
    var ppc = cam.gameObject.AddComponent(ppcType);
    ppcType.GetProperty("assetsPPU")?.SetValue(ppc, 32);       // = art-spec craft.pixels_per_unit
    ppcType.GetProperty("refResolutionX")?.SetValue(ppc, 320); // = art-spec craft.base_render_resolution[0]
    ppcType.GetProperty("refResolutionY")?.SetValue(ppc, 180); // = art-spec craft.base_render_resolution[1]
    ppcType.GetProperty("upscaleRT")?.SetValue(ppc, true);
    ppcType.GetProperty("pixelSnapping")?.SetValue(ppc, true);
}
```

## Runtime placement rules

- Snap sprite roots to the pixel grid when possible.
- Keep camera zoom locked to integer scale or Pixel Perfect Camera scaling.
- Avoid sub-pixel scrolling unless the art style accepts shimmer.
- Keep sprite shadows as separate pixel-art blob/shadow sprites; do not bake inconsistent shadows into every cutout.
- Use SpriteAtlas groups by family/layer and verify membership before BeautyCell approval.
