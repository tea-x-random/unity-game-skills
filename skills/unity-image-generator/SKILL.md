---
name: unity-image-generator
description: "Generate and edit 2D image assets for Unity casual games using Google's Gemini image API, then import them as sprites/textures/UI. Use for 2D casual games (match-3, puzzle, hyper-casual): sprites, sprite sheets, character/prop art, backgrounds, tile art, UI panels, buttons, icons, logos, title/menu art, particle textures, and material/texture references. Also produces concept and texture references that feed unity-3d-generator (image-to-3D). Covers Unity 2D import: Sprite mode, pixels-per-unit, filtering, sprite atlas, and ASTC for iOS."
---

# Unity Image Generator

Generate 2D art with Gemini, then import it into Unity correctly for sprites, UI, or textures. This is the primary asset skill for **2D casual iOS games**, and the concept/reference source for image-to-3D.

## API key & script

Key resolution: `--api-key`, then `GEMINI_API_KEY`. Probe first:
```bash
bash ~/.claude/skills/unity-game-director/scripts/probe_asset_credentials.sh   # GEMINI_API_KEY=SET|MISSING
```
```bash
python3 ~/.claude/skills/unity-image-generator/scripts/generate_image.py \
  --prompt "..." --filename Assets/Art/Sprites/coin.png --resolution 2K
```
Flags: `--prompt/-p`, `--filename/-f` (write under `Assets/`), `--input-image/-i` (edit an existing image), `--resolution/-r {1K,2K,4K}`, `--api-key/-k`.

## Dependencies & quota gotchas (check these FIRST)

The script needs `google-genai` and `pillow`. On modern macOS the system Python is
externally-managed (PEP 668), so install into a venv rather than `pip install --user`:

```bash
python3 -m venv .artvenv && ./.artvenv/bin/pip install google-genai pillow
# run the script with .artvenv/bin/python ...
```

`ModuleNotFoundError: No module named 'google'` means this step was skipped.

**Image gen needs billing on; once it is, the pipeline works.** The script calls
`gemini-3-pro-image-preview` (`scripts/generate_image.py --prompt "..." --filename out.png --resolution 1K|2K|4K`).
One-time setup: `python3 -m venv .artvenv && .artvenv/bin/pip install google-genai pillow`. With
billing **enabled** on the Google AI / Gemini API project, generation succeeds and PNGs import via the
project's ArtImporter (Sprite + iOS ASTC). On a **free-tier** key it (and `gemini-2.5-flash-image`)
returns `429 RESOURCE_EXHAUSTED ... limit: 0` — NOT transient rate-limiting; retrying and
model-swapping both fail. If the probe shows a key but every image 429s with `limit: 0`, report it as a
billing blocker (an allowed asset-sourcing skip) and fall back to procedural/placeholder art — do not
loop on retries.

**Exporting an interactive-only key to a non-interactive tool process.** If `GEMINI_API_KEY` lives in
`~/.zshrc` (sourced only for interactive shells), a tool/agent shell won't have it. macOS has no
`timeout`, and `zsh -lc` does NOT source `~/.zshrc` — you must use `-i`:
```bash
export GEMINI_API_KEY="$(zsh -ic 'printf %s "$GEMINI_API_KEY"' | tail -1)"
```

## What to generate for casual games

- **Sprites / characters / props:** request transparent background, single centered subject, consistent style, clean edges. For pixel art, ask for crisp pixels and a fixed palette.
- **Sprite sheets:** request an evenly-spaced grid of frames on transparent background; slice in Unity (Sprite Editor / Grid By Cell).
- **Backgrounds / parallax layers:** request seamless or full-bleed layers sized to portrait phone aspect (e.g. 1080×1920 framing).
- **UI:** buttons, panels, frames, progress bars, currency/HUD icons, settings glyphs — flat, high-contrast, readable at small size, transparent background. Keep a consistent icon family.
- **Logos / title art / app icon:** bold silhouette, legible at thumbnail size, no tiny text. The iOS app icon must be square with no transparency.
- **Texture/material references and image-to-3D concepts:** front/side/back T-pose sheets, tiling material swatches — these feed `unity-3d-generator`.

Iterate by passing the previous output via `--input-image` to refine (recolor, clean edges, add variants).

## Import into Unity (via unity-mcp-bridge)

After writing the PNG under `Assets/`, `refresh_unity(scope="assets", wait_for_ready=true)`, then set import settings with `execute_code` (`TextureImporter`) — Unity's default `textureType` may not match intent:

```csharp
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath("Assets/Art/Sprites/coin.png");
ti.textureType = UnityEditor.TextureImporterType.Sprite;     // Sprite (2D and UI)
ti.spritePixelsPerUnit = 100;                                // match your world scale
ti.spriteImportMode = UnityEditor.SpriteImportMode.Single;   // or .Multiple for sheets, then slice
ti.filterMode = UnityEngine.FilterMode.Bilinear;             // Point for pixel art
ti.mipmapEnabled = false;                                    // off for UI/2D sprites
// iOS compression
var s = new UnityEditor.TextureImporterPlatformSettings {
    name="iPhone", overridden=true,
    format=UnityEditor.TextureImporterFormat.ASTC_6x6, maxTextureSize=2048, compressionQuality=100 };
ti.SetPlatformTextureSettings(s);
ti.SaveAndReimport();
return "imported sprite";
```

Then:
- **Sprites in scene:** `manage_gameobject` with a `SpriteRenderer`, assign the sprite.
- **UI:** UI Toolkit (background-image in USS) via `manage_ui`, or uGUI `Image` via `manage_gameobject`+`manage_components`. See `unity-ui-designer`.
- **Atlas:** group related sprites into a **Sprite Atlas** to cut draw calls (big win on mobile). Create the atlas asset and add the folder.

## Quality & mobile rules

- Keep a consistent art-direction across a family (same lighting, outline, palette).
- Pack sprites into atlases; power-of-two max sizes; mipmaps off for crisp 2D, on for 3D textures.
- Use ASTC on iOS; cap max texture size to the smallest that still looks sharp on device.
- **CJK / non-Latin text needs a matching font.** Unity's default LiberationSans SDF has NO kanji/hiragana, so a label like 牛 renders as blank/tofu. To show Japanese you must import a CJK TMP font asset (e.g. Noto Sans JP); until that exists, use romaji. (Also relevant to `unity-ui-designer`.)
- Report prompts, output paths, import settings applied, and where each asset is used.

## Field notes & lessons

- Gemini image pipeline confirmed working once billing is on (`gemini-3-pro-image-preview` via `generate_image.py`, `.artvenv` with google-genai+pillow); added the interactive-only key export trick for non-interactive tool shells (`zsh -ic`, not `-lc`; no `timeout` on macOS); noted CJK text needs a matching TMP font (default LiberationSans has no kanji/hiragana) — use romaji until imported.
