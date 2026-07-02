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
| `generate_image_bitforge` | `bitforge` | Image-conditioned generation. Anchor-derived subjects/variants/recolors/edits via `init_image` (`style_image` is broken — see below); accepts `skeleton_keypoints`. |
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
- **`style_image`/`style_strength` are BROKEN on the live bitforge endpoint (verified 2026-07-01 with paid probes):** every strength (20/60/100), square and rectangular canvases, opaque and transparent refs, SDK and raw HTTP — all return **structured noise**, never a subject. Do not route conditioning through them; the schema advertises 0–100 but the output is unusable.
- **The working conditioning channel is `init_image` + `init_image_strength` (1–999):** the golden is a structural/style init and the description re-subjects it. Live calibration: **cross-subject derivation ~75–150** (100–110 = clean new subject inheriting proportions/baseline/palette; 175+ visibly bleeds the anchor's identity — plume/helmet/outfit leaking); **same-asset variants/recolors 250–400**. bitforge also **500s when the reference image's dimensions ≠ `image_size`** — the helper script auto crop/pads (never resamples) the reference to the target canvas.
- `skeleton_guidance_scale` (bitforge) default 1.0.
- **`guidance_scale` (animate-with-skeleton) 1.0–20.0, live default 4.0** — the single knob for identity + pose adherence. The old `reference_guidance_scale` (1.1) / `pose_guidance_scale` (3.0) pair no longer exists in the live schema.
- `image_guidance_scale` (animate-text **live default 1.4**; rotate default 3.0) 1.0–20.0.
- `init_image_strength` 0–1000 (default 300).
- `seed` — reproducibility/provenance metadata ONLY. It is never a cross-pose or cross-asset consistency mechanism; identity is carried by reference images, palettes, and skeletons.

## SDK 1.0.5 is INCOMPATIBLE with animate-with-skeleton (always raw)

PyPI `pixellab` 1.0.5 (latest, and the installed version) cannot call the live `/animate-with-skeleton` at all (verified 2026-07-01): it serializes absent `inpainting_images`/`mask_images` as `null`, which the API 422s ("Input should be a valid list"), still sends the **legacy** `reference_guidance_scale`/`pose_guidance_scale` names, and cannot send the live `guidance_scale`. **The helper script therefore ALWAYS uses raw HTTP for `animate-skeleton`.** Additional live constraints the script auto-handles:

- Canvas must be **square 16/32/64/128/256** ("Canvas must be size 256x256, 128x128, 64x64, 32x32 or 16x16") — non-square characters are padded (centered horizontally, bottom-aligned to preserve the baseline) and every returned frame is cropped back.
- Each call takes an **exact pose count determined by the canvas** (e.g. **3 poses at 64×64** — "Expected 3 pose images"); longer clips are batched automatically, short tails padded with the last pose and trimmed.
- `z_index` must be an **integer** — `/estimate-skeleton` itself returns fractional values (-3.5, -0.5); the script rounds them.

Raw shape for reference:

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
- `--palette '#aabbcc' ...` builds a swatch for exploration; if you pass hexes in the prompt text instead of a `color_image`, the palette is **not** enforced. Live verification 2026-07-01: a pixflux golden conditioned on a 22-color swatch came back **100% exact-membership** — `color_image` behaved as a hard lock in practice. Keep `validate_sprite.py --palette` as the backstop anyway (single sample). Exact-membership QA must check against the **swatch PNG's pixels** (what generation actually conditioned on), not the spec hex lists — the swatch legitimately carries the outline black that no ramp lists.

## Style-reference batching (web app only)

PixelLab Pro's "Create images from style references" batch tool has **no API endpoint**, and the API's `style_image` param is broken (noise — see above). Treat batch style-referencing as a manual web-app step; scripted pipelines loop bitforge **`init_image`** calls against the golden anchor instead.

## Image size

`image_size` is `{width, height}`. Generate at the **final pixel canvas**, derived from the spec's tiles (`craft.tile_size` × `craft.char_tiles`; typical `16`/`32`/`48`/`64`/`128`). Do not generate a 1024px illustration and downscale. Canvas caveats:

- **bitforge `skeleton_keypoints`** (pose-guided stills) works best at **16/32/64** canvases — that is where the spec attaches its quality warning.
- **animate-with-skeleton supports up to 256** — a 48×48 skeleton animation is fully supported.
- The web app's style-reference tool caps at **80×80 (plan tier 1) / 140×140 (tier 2+)**; the API init-conditioning path is verified at 32–64 canvases — see the large-canvas escape hatch in SKILL.md for 128+ set pieces.

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
3. **Author per-frame poses.** `skeleton_keypoints` is a list of frames; the LIVE API wants each frame as a **bare keypoint list** `[{"x", "y", "label", "z_index"}, ...]` (the script also accepts the friendlier `{"keypoints": [...]}` and normalizes). Labels are fixed: `NOSE, NECK, RIGHT/LEFT SHOULDER|ELBOW|ARM, RIGHT/LEFT HIP|KNEE|LEG, RIGHT/LEFT EYE|EAR`. `x`/`y` are **normalized 0–1** on the canvas (estimate-skeleton output is already normalized); `z_index` integer. Start from the game's skeleton template and move joints per frame (a walk = legs/arms swinging across ~4–8 frames).
   **Attacks:** labels are the SUBJECT's anatomical sides — author the strike on the FRONT (facing-direction) limb (facing east: larger rest x); mirroring a pose set = negate x AND swap all LEFT/RIGHT label pairs. Author phases (windup/strike-smear/follow-through/recover), with wrist travel ≥0.25 normalized between windup and strike and whole-body deltas (nose/neck lean 0.04–0.07, hips 0.02–0.03). There is no weapon keypoint — the wrist path is the weapon-arc control; shift all keypoints ~20–25% toward the trailing edge so the model has empty canvas on the strike side for effect pixels (per PixelLab's skeleton-animation docs). Assert `--view`/`--direction` equals the reference anchor's stored facing before calling. Sanity-check estimate-skeleton output on stylized/armored sprites (limb-length symmetry, L/R ordering) before reusing it as a template.
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
   For attack strips, do not rely on the generated frames to carry the slash — the model animates the body; the slash arc ships as a separate `pixflux` VFX overlay sprite (SKILL.md attack doctrine). Keep `fixed head` OFF for attacks.
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
4. Generate ONE golden/anchor, QA it, then derive everything else from it (bitforge `init_image_strength` 250–400 same-asset / 75–150 cross-subject, rotate, animate-skeleton) instead of best-of-N rerolls — except tiles/seamless textures, where seams vary per roll and best-of-N on `tile.edge_wrap` is correct.
5. Repair single bad frames (`inpaint`, `--init-images` freeze) instead of re-rolling strips.
6. Batch only after the anchor passes QA.
