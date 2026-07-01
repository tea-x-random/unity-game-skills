# PixelLab API notes for Unity pixel art

Use PixelLab for **final pixel-native sprites and animation**. Keep Gemini as a concept/reference supplier only. Source of truth: the **live OpenAPI** at `api.pixellab.ai/v1/openapi.json` (verified 2026-07-01) — the PyPI `pixellab` SDK (1.0.5) lags it; see the SDK-lag caveat below.

## Key and package

- Canonical environment variable: `PIXEL_LABS_API_KEY`.
- Python package: `pixellab` (client: `pixellab.Client(secret=...)`).
- Helper script: `../scripts/generate_pixel_art.py` (subcommands map 1:1 to the methods below).

## Methods (SDK names = script subcommands)

| Method | Subcommand | Purpose |
| --- | --- | --- |
| `generate_image_pixflux` | `pixflux` | Text → pixel image. First anchor when the prompt fully defines subject/view/palette/canvas. |
| `generate_image_bitforge` | `bitforge` | Style/image-conditioned image. Anchor-derived variants, recolors, edits; accepts a `style_image` + `skeleton_keypoints`. |
| `rotate` | `rotate` | Turn an existing sprite to a new `direction`/`view`. Build directional sheets from one anchor. |
| `estimate_skeleton` | `estimate-skeleton` | Detect rest-pose keypoints from a base character → JSON template for animation. |
| `animate_with_skeleton` | `animate-skeleton` | **Pose-driven animation. Structurally consistent across frames — the PREFERRED animation path.** |
| `animate_with_text` | `animate-text` | Text/action animation conditioned on a reference image. Drifts more than skeleton; use when you have no posed skeleton. |
| `inpaint` | `inpaint` | Local edit inside a white mask. Fix a weapon/eye/outline/missing frame detail without rerolling. |
| `get_balance` | `balance` | Account credit balance (USD). |

## Enums (exact — do not invent values)

- `view` (CameraView): `side`, `low top-down`, `high top-down`. **There is no plain "top-down", "3/4", or "isometric" view** — isometric is the separate boolean `isometric=true`.
- `direction` (Direction, 8-way): `south`, `south-east`, `east`, `north-east`, `north`, `north-west`, `west`, `south-west`.
- `outline`: `single color black outline`, `single color outline`, `selective outline`, `lineless`.
- `shading`: `flat shading`, `basic shading`, `medium shading`, `detailed shading`, `highly detailed shading`.
- `detail`: `low detail`, `medium detail`, `highly detailed`.

## Guidance scales and ranges (live OpenAPI values — get these right)

- `text_guidance_scale` 1.0–20.0 (pixflux default 8.0; **bitforge live default 8.0** — older docs said 3.0; inpaint default 3.0).
- `extra_guidance_scale` — **DEPRECATED in the live API.** Do not tune it; treat any effect as a no-op.
- **`style_strength` is 0–100** (SDK default `0.0`). This is the single biggest footgun: `0.85` is essentially **no** style transfer. Same-asset variants: **60–100**. Cross-subject derivation from a golden anchor (new character/prop): **50–70** — very high strength transfers the anchor's *identity* (anchor-subject bleed), not just style.
- `skeleton_guidance_scale` (bitforge) default 1.0.
- **`guidance_scale` (animate-with-skeleton) 1.0–20.0, live default 4.0** — the single knob for identity + pose adherence. The old `reference_guidance_scale` (1.1) / `pose_guidance_scale` (3.0) pair no longer exists in the live schema.
- `image_guidance_scale` (animate-text **live default 1.4**; rotate default 3.0) 1.0–20.0.
- `init_image_strength` 0–1000 (default 300).
- `seed` — reproducibility/provenance metadata ONLY. It is never a cross-pose or cross-asset consistency mechanism; identity is carried by reference images, palettes, and skeletons.

## SDK 1.0.5 lags the live API (caveat + raw fallback)

PyPI `pixellab` 1.0.5 (latest, and the installed version) still sends the **legacy** `reference_guidance_scale`/`pose_guidance_scale` names on animate-with-skeleton and cannot send the live `guidance_scale` — so tuning the old flags through the SDK is likely a **no-op** and the server default (4.0) governs. To actually tune it, POST raw (the helper script does this when you pass `--guidance-scale`):

```python
import requests
resp = requests.post(
    "https://api.pixellab.ai/v1/animate-with-skeleton",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "image_size": {"width": 48, "height": 48},
        "guidance_scale": 4.0,
        "view": "side", "direction": "east",
        "skeleton_keypoints": frames,                      # list of frames = lists of keypoints
        "reference_image": {"type": "base64", "base64": ref_png_b64},
        "color_image": {"type": "base64", "base64": subpalette_png_b64},
    },
)
frames_b64 = [img["base64"] for img in resp.json()["images"]]
```

## Palette lock = `color_image`, NOT a hex list

There is **no `target_palette` parameter.** PixelLab forces a palette via `color_image` — an image whose pixels define the allowed colors — and the live API accepts it on **pixflux, bitforge, rotate, animate-with-skeleton, animate-with-text, and inpaint**. Rules:

- **Any PixelLab call without a `color_image` is invalid** on production paths. The helper script auto-attaches `art-spec conditioning.master_palette_png`; it FAILS loudly if the SDK would drop `color_image`.
- **Derived frames/rotations use the anchor's extracted sub-palette** (subset of the master) — forcing the full game palette on a 5-color coin's frames permits cross-asset color borrowing. Produce the swatch from the approved anchor: `compare_frames_to_anchor.py --anchor <anchor.png> --emit-subpalette <id>_subpalette.png`, then pass it via `--color-image` (omitting `--color-image` falls back to the FULL master palette, which the derived-frame rule forbids).
- `--palette '#aabbcc' ...` builds a swatch for exploration; if you pass hexes in the prompt text instead of a `color_image`, the palette is **not** enforced. `color_image` strictness is strong guidance, not verified as an absolute lock — keep `validate_sprite.py --palette` as the backstop.

## Style-reference batching (web app only)

PixelLab Pro's "Create images from style references" batch tool has **no API endpoint** — the API's only style conditioning is bitforge's single `style_image` per call. Treat batch style-referencing as a manual web-app step; scripted pipelines loop bitforge calls against the golden anchor instead.

## Image size

`image_size` is `{width, height}`. Generate at the **final pixel canvas**, derived from the spec's tiles (`craft.tile_size` × `craft.char_tiles`; typical `16`/`32`/`48`/`64`/`128`). Do not generate a 1024px illustration and downscale. Canvas caveats:

- **bitforge `skeleton_keypoints`** (pose-guided stills) works best at **16/32/64** canvases — that is where the spec attaches its quality warning.
- **animate-with-skeleton supports up to 256** — a 48×48 skeleton animation is fully supported.
- Style-referenced generation caps at **80×80 (plan tier 1) / 140×140 (tier 2+)** — see the large-canvas escape hatch in SKILL.md.

## Consistent animated character — the skeleton workflow

Text-only animation drifts (identity changes frame to frame). For real, gameplay-readable motion use the base-character → skeleton → animation pipeline. (All commands below run under the art-spec gate — with no `--color-image` the script auto-attaches the master palette; on derived frames pass the anchor's sub-palette via `--color-image`, emitted with `compare_frames_to_anchor.py --emit-subpalette`.)

1. **Generate a base character** at the tile-derived native canvas, transparent background. The game golden is the only `pixflux` roll; other characters are `bitforge` on their golden:
   ```bash
   python3 ../scripts/generate_pixel_art.py pixflux \
     --description "pixel art knight, side view, facing east, single color black outline" \
     --canvas character --no-background --view side --direction east \
     --output "Assets/<Game>/Art/Source/SourceImages/knight_base.png"
   ```
2. **Estimate its skeleton** (rest pose keypoints → reusable JSON template). **Skeleton-template library convention:** save ONE client-authored biped keypoint JSON per game (canonical path: `Assets/<Game>/Art/_ArtDirection/sheets/biped_<size>.skeleton.json`, referenced by `art-spec characters.<id>.skeleton_template`) and reuse it for every humanoid — uniform proportions across the whole cast:
   ```bash
   python3 ../scripts/generate_pixel_art.py estimate-skeleton \
     --image "Assets/<Game>/Art/Source/SourceImages/knight_base.png" \
     --output "Assets/<Game>/Art/_ArtDirection/sheets/biped_48.skeleton.json"
   ```
3. **Author per-frame poses.** `skeleton_keypoints` is a list of frames; each frame is `{"keypoints": [{"x", "y", "label", "z_index"}, ...]}`. Labels are fixed: `NOSE, NECK, RIGHT/LEFT SHOULDER|ELBOW|ARM, RIGHT/LEFT HIP|KNEE|LEG, RIGHT/LEFT EYE|EAR`. Start from the game's skeleton template and move joints per frame (a walk = legs/arms swinging across ~6–8 frames). Coordinates are in pixels on the target canvas.
4. **Animate with the skeleton**, conditioning identity on the base character (canvas defaults to the reference; the live `guidance_scale` defaults to 4.0 server-side — pass `--guidance-scale` only to tune, which uses the raw HTTP path):
   ```bash
   python3 ../scripts/generate_pixel_art.py animate-skeleton \
     --skeleton-json knight_walk_frames.json \
     --view side --direction east \
     --reference-image "Assets/<Game>/Art/Source/SourceImages/knight_base.png" \
     --color-image "Assets/<Game>/Art/Approved/hero_knight/hero_knight_subpalette.png" \
     --output "Assets/<Game>/Art/Source/SourceImages/knight_walk.png"
   # writes knight_walk_00.png ... and a packed knight_walk_strip.png
   ```
5. **Directional sheets:** `rotate` the base (and each keyframe) to other directions instead of regenerating from scratch (canvas defaults to the source; keep the sub-palette lock):
   ```bash
   python3 ../scripts/generate_pixel_art.py rotate \
     --from-image "Assets/<Game>/Art/Source/SourceImages/knight_base.png" \
     --from-direction east --to-direction south \
     --color-image "Assets/<Game>/Art/Approved/hero_knight/hero_knight_subpalette.png" \
     --output "Assets/<Game>/Art/Source/SourceImages/knight_base_south.png"
   ```
6. **Fix, don't reroll — single-frame repair loop.** When `compare_frames_to_anchor.py` fails ONE frame, never re-roll the whole strip:
   - `inpaint` with a white mask over the broken region (stray pixel, wrong eye, outline gap) on that frame; or
   - re-run `animate-skeleton` with `--init-images` listing the approved frame PNGs (high `--init-image-strength` freezes them) plus the slot to regenerate — optionally `--mask-images` to constrain the repair region per frame.

`animate-text` (description + `action` + `reference_image` + `n_frames`) is the fallback when you cannot author a skeleton — it stays on the reference but drifts more than skeleton animation. Either way, gate frames with `../scripts/compare_frames_to_anchor.py` (palette/baseline/bbox/IoU vs the anchor) before slicing.

## Prompt fields (text paths: pixflux / bitforge / inpaint / animate-text)

State subject, role, the exact `view`/`direction` enum values, pose/frame, transparent background (`--no-background`), palette (`--palette`/`--color-image`), outline/shading/detail enums, and "no text, no watermark, no antialiasing, no gradient blur" in `--negative-description`.

## Cost discipline

PixelLab calls are paid. Before generating:

1. Check credentials/probe output.
2. `generate_pixel_art.py balance` before any batch.
3. `--dry-run` to inspect the request payload and confirm enums/canvas/palette/anchor resolution (it runs the same art-spec gate).
4. Generate ONE golden/anchor, QA it, then derive everything else from it (bitforge `style_strength` 60–100 same-asset / 50–70 cross-subject, rotate, animate-skeleton) instead of best-of-N rerolls.
5. Repair single bad frames (`inpaint`, `--init-images` freeze) instead of re-rolling strips.
6. Batch only after the anchor passes QA.
