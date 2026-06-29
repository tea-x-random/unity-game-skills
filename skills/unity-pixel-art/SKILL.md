---
name: unity-pixel-art
description: "Generate production-ready PIXEL-NATIVE 2D game sprites, sprite sheets, tilesets, icons, rotations, and animation frames for Unity using PixelLab for final art, with Gemini only for exploratory concepts/style boards. Use when the requested game art is pixel art, low-res sprite art, tilemaps, top-down/side-view 2D sprites, directional character sheets, animation strips, or any final 2D pixel asset. Enforces anchor-first sprite production, fixed canvas sizes and palettes, transparent backgrounds, Unity point-filter import, pixel-perfect camera compatibility, alpha/palette/sheet QA, and explicitly forbids Tripo/3D-render downscaling as the source of pixel art."
---

# Unity Pixel Art

Create **pixel-native** game assets for Unity. Use Gemini for exploration only; use **PixelLab** for final pixels.

## Routing rule

- **Gemini → exploration:** mood boards, rough silhouettes, palette exploration, UI/style-guide thumbnails, non-final reference sheets.
- **PixelLab → final pixel art:** characters, props, tilesets, icons, directional sheets, animation frames, variants, and recolors.
- **Do not make pixel art by rendering Tripo/3D and downscaling it.** 3D pre-render is acceptable for high-res/painterly 2D, but pixel art must be authored/generatively produced at the target pixel canvas so silhouettes, clusters, outlines, and palette choices are deliberate.

If another skill routes a **pixel-art** asset to `unity-image-generator` or `unity-3d-generator`, override it here: Gemini may provide concept references; PixelLab produces the approved source sprites.

## Required references

Read only the branch you need:

- `references/pixellab-api.md` — PixelLab models, script usage, endpoint/SDK notes.
- `references/pixel-import.md` — Unity import settings, slicing, and pixel-perfect camera snippets.

## Anchor-first production workflow

1. **Lock the art contract.** Pull `style_id`, canvas size, view, palette, outline rule, PPU, pivot, target role, and animation list from `art-spec.yaml` / `asset-contract.yaml`.
2. **Explore cheaply with Gemini if needed.** Generate concept boards or silhouette sheets only. Do not approve Gemini pixels as final pixel-art assets.
3. **Generate one anchor sprite in PixelLab.** Use a native canvas (`16`, `32`, `64`, `128`, or a project-approved size), transparent/no-background output, and the locked palette. This anchor becomes the only source of truth.
4. **QA the anchor before variants.** Run alpha/padding/palette/silhouette checks with `unity-image-generator/scripts/validate_sprite.py`; optionally run a Gemini vision critique for subject/readability.
5. **Derive frames/rotations/variants from the anchor.** Use PixelLab image-conditioned generation (BitForge) or rotation/animation APIs when available. Keep one base sprite driving directions, walk/idle/attack strips, damage states, and palette variants.
6. **Repack sheets with padding/extrusion.** Use `extrude_atlas.py` before Unity slicing so point filtering and atlas packing do not bleed neighboring cells.
7. **Import with pixel settings.** Point filter, no compression, no mipmaps, correct PPU, multiple-sprite slicing for sheets, SpriteAtlas family grouping, and Pixel Perfect Camera settings.
8. **Promote only approved assets.** The final artifact must include the sprite PNG/sheet, QA reports, manifest, Unity import contract, prefab, and BeautyCell screenshot before it enters the approved registry.

## Canvas and style rules

- Pick the canvas from gameplay readability: icons `16–32`, pickups/props `32–64`, characters `32–128`, bosses/large set pieces `128+` only when the camera supports it.
- Generate at the **final pixel canvas**, not a high-res illustration to shrink later.
- State the exact view (`side`, `top-down`, `high top-down`, `low top-down`, `3/4 orthographic`) and pivot/baseline.
- Use a fixed palette (`4–16` colors for small assets; document exceptions). If palette drift appears, condition the next pass with the anchor and palette.
- Keep animation frame counts small and game-readable: idle `4–6`, walk/run `6–8`, attack `6–10`, hit `2–4`, death `6–10`.
- Prefer one row per clip (`idle`, `walk`, `attack`) or a documented grid (`rows=clips`, `cols=frames`) with a sidecar manifest.

## PixelLab helper script

Use the bundled script for final generation. It resolves keys as `--api-key` → `PIXEL_LABS_API_KEY`.

```bash
python3 ~/.claude/skills/unity-pixel-art/scripts/generate_pixel_art.py pixflux \
  --description "32x32 pixel art gold coin pickup, side view, 8 color palette, transparent background" \
  --width 32 --height 32 \
  --output Assets/Art/Pixel/coin_anchor.png \
  --manifest Assets/Art/Pixel/coin_anchor.pixellab.json
```

For variants/frames that must stay on-model, condition on the approved anchor:

```bash
python3 ~/.claude/skills/unity-pixel-art/scripts/generate_pixel_art.py bitforge \
  --description "same 32x32 coin, sparkle frame 2 of 4, same palette, same silhouette center" \
  --width 32 --height 32 \
  --style-image Assets/Art/Pixel/coin_anchor.png \
  --style-strength 0.85 \
  --no-background \
  --output Assets/Art/Pixel/coin_sparkle_02.png \
  --manifest Assets/Art/Pixel/coin_sparkle_02.pixellab.json
```

Before a paid batch, check credits and use `--dry-run` to verify dimensions, prompt, and conditioning inputs:

```bash
python3 ~/.claude/skills/unity-pixel-art/scripts/generate_pixel_art.py balance
python3 ~/.claude/skills/unity-pixel-art/scripts/generate_pixel_art.py --dry-run pixflux --description "..." --width 32 --height 32 --output /tmp/preview.png
```

## QA gates

Run after every final PixelLab output:

```bash
python3 ~/.claude/skills/unity-image-generator/scripts/validate_sprite.py \
  Assets/Art/Pixel/coin_anchor.png \
  --require-alpha --min-padding 1 --max-width 128 --max-height 128 \
  --palette '#2B1E12,#6B3E16,#D28A22,#FFD46B,#FFF3B0' \
  --json-report Assets/Art/QA/coin_anchor.sprite-qa.json
```

For tilesets:

```bash
python3 ~/.claude/skills/unity-image-generator/scripts/validate_sprite.py \
  Assets/Art/Pixel/grass_tile.png \
  --tile --square --power-of-two --expected-finish flat \
  --json-report Assets/Art/QA/grass_tile.sprite-qa.json
```

Reject pixel assets for:

- generated at the wrong native canvas;
- anti-aliased/high-res painted edges that are not pixel-native;
- palette drift outside the approved palette;
- inconsistent baseline/pivot across frames;
- loose alpha padding or non-transparent corners;
- animation frames that change identity, outfit, proportions, or weapon placement;
- imported with bilinear filtering, compression, mipmaps, or wrong PPU.

## Unity import summary

Use `references/pixel-import.md` for snippets. Minimum settings:

- `TextureImporterType.Sprite`
- `FilterMode.Point`
- `TextureImporterCompression.Uncompressed`
- `mipmapEnabled = false`
- `SpriteImportMode.Multiple` for sheets
- consistent `spritePixelsPerUnit`
- Pixel Perfect Camera (`com.unity.2d.pixel-perfect`) when the game camera renders pixel art.

## Handoff to other skills

- `unity-image-generator`: concept boards, non-pixel static art, UI mockups, vision critique, sprite validators.
- `unity-animation`: Animator setup, frame timing, events, slicing; source frames come from this skill for pixel art.
- `unity-asset-pipeline`: asset contract, prefab factory, registry, BeautyCell gate.
- `unity-scene-composition`: screen-space scale, readability, layer density, camera contract.
