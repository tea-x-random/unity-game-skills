# Unity import for pixel art

Pixel art fails quickly when Unity imports it like a photo. Apply these settings before approval.

## TextureImporter settings

```csharp
var path = "Assets/Art/Pixel/hero_walk.png";
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(path);
ti.textureType = UnityEditor.TextureImporterType.Sprite;
ti.spritePixelsPerUnit = 32; // match the asset contract; common: canvas height == 1 Unity unit
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
    ppcType.GetProperty("assetsPPU")?.SetValue(ppc, 32);
    ppcType.GetProperty("refResolutionX")?.SetValue(ppc, 320);
    ppcType.GetProperty("refResolutionY")?.SetValue(ppc, 180);
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
