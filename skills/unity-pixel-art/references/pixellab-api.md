# PixelLab API notes for Unity pixel art

Use PixelLab for **final pixel-native sprites**. Keep Gemini as a concept/reference supplier only.

## Key and package

- Canonical environment variable: `PIXEL_LABS_API_KEY`.
- Python package: `pixellab`.
- Helper script: `../scripts/generate_pixel_art.py`.

## Models / methods to route to

- **PixFlux** (`create_image_pixflux` / older SDKs may expose `generate_image_pixflux`): text-to-pixel-image. Use for first anchor sprites when the prompt fully defines subject, view, palette, and canvas.
- **BitForge** (`create_image_bitforge` / older SDKs may expose `generate_image_bitforge`): image/style-conditioned pixel generation. Use for anchor-derived variants, frames, recolors, and consistency-preserving edits.
- **Pixen** (`create_image_pixen` where available): alternative text-to-pixel model; useful for small simple sprites.
- **Rotations / direction generation** (including four-direction character APIs where available): use when a directional sheet is required, conditioned by the locked anchor whenever possible.
- **Animation APIs**: use skeleton/text animation APIs when available for walk/idle/attack loops, then QA identity and baseline before slicing.
- **Inpaint/edit APIs**: use for local fixes (weapon, eye, outline, missing frame detail) rather than rerolling the whole sprite.

## Native sizes

Prefer `16`, `32`, `64`, or `128` px canvases unless the art contract says otherwise. Do not generate a 1024px illustration and downscale it to pixel art.

## Prompt fields

Every final PixelLab request should state:

```text
<canvas WxH> pixel art <subject>, <role>, <view>, <pose/frame>,
transparent/no background, fixed palette <hexes or named palette>,
outline rule, lighting/shadow rule, pivot/baseline, no text, no watermark,
no high-res painting, no antialiasing, no gradient blur
```

For sheets, add:

```text
rows/columns, frame order, same canvas per cell, same baseline and center,
no camera/framing drift, same outfit/weapon/proportions every frame
```

## Script examples

Text-to-anchor:

```bash
python3 skills/unity-pixel-art/scripts/generate_pixel_art.py pixflux \
  --description "32x32 pixel art side-view acorn pickup, transparent background, fixed 6-color warm autumn palette, dark brown one-pixel outline, centered, bottom pivot" \
  --width 32 --height 32 \
  --no-background \
  --palette '#2B1E12' '#6B3E16' '#D28A22' '#FFD46B' \
  --output Assets/Art/Pixel/acorn_anchor.png \
  --manifest Assets/Art/Pixel/acorn_anchor.pixellab.json
```

Image-conditioned variant:

```bash
python3 skills/unity-pixel-art/scripts/generate_pixel_art.py bitforge \
  --description "same 32x32 acorn, cracked damaged variant, same palette, same outline, same bottom pivot" \
  --width 32 --height 32 \
  --style-image Assets/Art/Pixel/acorn_anchor.png \
  --style-strength 0.85 \
  --no-background \
  --output Assets/Art/Pixel/acorn_damaged.png \
  --manifest Assets/Art/Pixel/acorn_damaged.pixellab.json
```

## Cost discipline

PixelLab calls are paid. Before generating:

1. Check credentials/probe output.
2. Check PixelLab balance/credits (`generate_pixel_art.py balance`) before batch generation.
3. Use `--dry-run` to inspect request payload.
4. Generate one anchor before any batch.
5. Prefer conditioning from the anchor over best-of-N rerolls.
6. Batch only after the anchor passes QA.
