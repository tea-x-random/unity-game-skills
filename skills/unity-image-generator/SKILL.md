---
name: unity-image-generator
description: "Generate and edit STATIC 2D image assets for Unity casual games using Google's Gemini image API, then import them as sprites/textures/UI. Use for 2D casual games (match-3, puzzle, hyper-casual): static sprites, character/prop art, backgrounds, tile/ground art, tiling textures, UI panels, buttons, icons, logos, title/menu art, particle textures, and material/texture references. For ANIMATED/motion assets (characters, animated actors, multi-angle/turnaround, anything that needs smooth animation) prefer Tripo (unity-3d-generator) to rig + animate, and for 2D pre-render the rig to sprite frames — this skill's role there is producing the high-quality concept/reference images that condition those Tripo models (image-to-3D). Covers Unity 2D import: Sprite mode, pixels-per-unit, filtering, sprite atlas, and ASTC for iOS."
---

# Unity Image Generator

Generate **static** 2D art with Gemini, then import it into Unity correctly for sprites, UI, or textures. This is the skill for **static 2D art, textures/grounds, backgrounds, UI/icons, and reference/concept images**. Anything that **moves** — characters, animated actors, multi-angle/turnaround assets, anything needing smooth animation — should be produced with **Tripo** (`unity-3d-generator`: rig + animate; for 2D, **pre-render the rig to sprite frames**), with Gemini providing the high-quality reference images that condition those Tripo models.

## Gemini vs Tripo — pick the right tool (library-wide rule)

> **Motion → Tripo, static → Gemini.** This is the canonical, library-wide policy.

- **Anything that needs motion, smooth animation, multiple poses, or turnaround consistency → Tripo** (`unity-3d-generator`): rig + animate, and for **2D games render the rig to sprite frames** (see `unity-3d-generator` → "Use Tripo for 2D games too" + `../unity-3d-generator/references/prerender-2d.md`, then `unity-animation`). One rigged, rendered model gives consistent identity across frames and angles and drift-free animation.
- **Gemini (this skill) → static art:** concepts, tiling ground/textures, backgrounds, UI, icons, logos, and 2D art that doesn't move or need multiple angles — plus the **reference images that condition Tripo** (image-to-3D).
- **Gemini frame-by-frame animation DRIFTS** (each independently generated frame loses identity) and is a **FALLBACK ONLY** — reach for it only when `TRIPO_API_KEY` is **MISSING**/quota-blocked, or when the motion is trivial.

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
- **Sprite sheets:** request an evenly-spaced grid of frames on transparent background; slice in Unity (Sprite Editor / Grid By Cell). For **animated assets, produce frames via Tripo rig + pre-render by DEFAULT** (`unity-3d-generator` pre-render → `unity-animation`) — one rigged model gives drift-free, consistent frames across states/angles. Direct Gemini per-state frame strips (idle/walk/attack) sliced by `unity-animation` are the **FALLBACK** only when Tripo is unavailable (`TRIPO_API_KEY` missing/quota-blocked) or the motion is trivial.
- **Backgrounds / parallax layers:** request seamless or full-bleed layers sized to portrait phone aspect (e.g. 1080×1920 framing).
- **UI:** buttons, panels, frames, progress bars, currency/HUD icons, settings glyphs — flat, high-contrast, readable at small size, transparent background. Keep a consistent icon family.
- **Logos / title art / app icon:** bold silhouette, legible at thumbnail size, no tiny text. The iOS app icon must be square with no transparency.
- **Texture/material references and image-to-3D concepts:** front/side/back T-pose sheets, tiling material swatches — these feed `unity-3d-generator`. **When the concept will be rigged/animated via Tripo, generate a clean full-body T-pose (or A-pose)** — arms away from the torso, legs apart, no props crossing the body — because auto-rigging fails on action poses; generate the action (e.g. a bow-draw) later as animation clips, not in the static concept (see `../unity-3d-generator/SKILL.md` → "Riggable characters need a clean full-body T-pose").

## AAA prompt engineering (avoid flat/MS-Paint output)

One-line prompts produce one-line art. A production prompt names, in order: **subject**; **view/framing** (top-down, 3/4, side, centered); **art style + 1–2 named touchstones**; **shape language** (chunky, rounded, angular); **material & color** with palette tokens (hex or named); **lighting** (direction + quality — e.g. soft key from upper-left, warm rim); **render fidelity** (high-detail, clean edges, subtle shading, baked ambient occlusion); **output spec** (transparent background OR seamless tiling, single subject, no text/UI); and a **negative prompt** (`NOT: flat single-color fill, MS-Paint, programmer art, jagged edges, muddy, blurry, watermark, text`).

For the full template, full negative-prompt list, and per-genre exemplar prompts, see `../unity-aaa-graphics/references/prompt-library.md` — keep prompts here concise; the library has the depth.

## Environment & terrain textures (most-missed assets)

Top-down and side games need **real textured ground and paths, not flat color fills** — this is what removes most of the "amateur" look in tower-defense / top-down maps. Generate **seamlessly tiling** ground / path / tileset textures, e.g.:

```
seamless tiling stylized grass ground texture, top-down, hand-painted painterly style,
soft varied green palette (#6Fae5a / #4f8a3e), subtle dirt patches and clumps, even soft
lighting, high-detail, clean edges, no seams, no subject, no text — NOT: flat single-color
fill, MS-Paint, harsh tiling seams
```

Import tiling textures with `wrapMode = TextureWrapMode.Repeat` and **mipmaps ON** for material/3D use (the opposite of UI sprites). Apply to a material's albedo and set tiling so the pattern repeats across the surface.

## Refine loop (regenerate, don't just reroll)

Generate at **1K** first to check composition. If framing/subject is wrong, **rewrite the prompt** (don't just reroll the same one). Once composition is right, refine at **2K** via `--input-image`, reusing **verbatim style tokens** (style name, touchstones, palette) to avoid drift across passes. Use the prompt-library's per-asset rubric to judge each pass. Iterating via `--input-image` also handles recolors, edge cleanup, and variants.

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

- **Real generated art is the default for primary visible surfaces** (characters, props, ground, paths, backgrounds, UI). Procedural placeholder art is a *fallback only* when the key is MISSING or quota-blocked (see the billing-blocker note above) — not a first choice.
- Keep a consistent art-direction across a family (same lighting, outline, palette).
- Pack sprites into atlases; power-of-two max sizes; mipmaps off for crisp 2D, on for 3D textures.
- Use ASTC on iOS; cap max texture size to the smallest that still looks sharp on device.
- **Non-Latin text needs a font that covers the script.** Unity's default LiberationSans SDF has no glyphs for many scripts (CJK, Cyrillic, Arabic, etc.), so those labels render as blank "tofu" boxes. Import a TMP font asset that covers your target script (e.g. an appropriate Noto family font); until it exists, fall back to a supported script. (Also relevant to `unity-ui-designer`.)
- Report prompts, output paths, import settings applied, and where each asset is used.

## Field notes & lessons

- **Policy: Motion → Tripo, static → Gemini.** Anything that moves or needs multiple poses/turnaround consistency goes through Tripo (rig + animate; pre-render to sprites for 2D) with Gemini supplying the reference images that condition it. Gemini is for static art, textures, grounds, backgrounds, UI/icons, and concept/reference images; its frame-by-frame animation drifts and is a fallback only when `TRIPO_API_KEY` is missing/quota-blocked.
- Gemini image pipeline confirmed working once billing is on (`gemini-3-pro-image-preview` via `generate_image.py`, `.artvenv` with google-genai+pillow); added the interactive-only key export trick for non-interactive tool shells (`zsh -ic`, not `-lc`; no `timeout` on macOS); noted non-Latin text needs a matching TMP font (default LiberationSans has no glyphs for many scripts) — fall back to a supported script until imported.
