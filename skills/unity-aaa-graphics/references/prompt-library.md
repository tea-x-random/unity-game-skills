# AAA prompt library — exemplar prompts & genre art kits

One-line prompts produce one-line art. This library gives a reusable **prompt template**, **negative prompts**, a **refine loop**, and **genre art kits** with full exemplar prompts you can adapt as starting points. Use with `unity-image-generator` (2D/textures/tilesets/UI) and `unity-3d-generator` (models). Always condition on the project's style sheet from `unity-asset-designer` so assets stay on-model.

> Replace every `[BRACKET]` with your project's own art-direction tokens (from the style guide). Keep the *structure*; vary the *tokens*.

> **Style comes from the project, never from this library.** The tokens — including fidelity and finish — are the user's/style-guide's. "AAA" here means *intentional and cohesive*, **not** "high-detail." A flat, minimal, muted look done cohesively is premium; this library must serve it as readily as a glossy one. Do not let the examples below push a target toward more rendering than it wants.

> **Source rule:** motion / animated / multi-angle assets → Tripo (rig + animate; for 2D, pre-render the cycles to sprite frames — see `unity-3d-generator` pre-render + `../../unity-animation/SKILL.md`). Gemini → static art, textures, UI, and the reference images that condition Tripo. Gemini frame-by-frame drifts and is a fallback only when the Tripo key is `MISSING`.

## The prompt template (anatomy)

A production-quality prompt names all of these, in roughly this order:

```
[SUBJECT — what it is, one clear focal thing]
[VIEW/FRAMING — e.g. top-down 45° orthographic, side view, centered, full-bleed]
[ART STYLE — named style + 1–2 touchstones, e.g. "stylized hand-painted, à la Clash Royale"]
[FORM/SHAPE LANGUAGE — round/soft vs sharp; proportions; silhouette readability]
[MATERIAL & COLOR — palette tokens + surface (matte/glossy/metal/fabric/foliage)]
[LIGHTING — direction + quality, e.g. "soft key light from top-left, gentle ambient, soft contact shadow"]
[RENDER FIDELITY — TARGET-RELATIVE, from the style guide. A spectrum, not a ladder: "flat single-tone
  cel, no gradients" is as valid a target as "high-detail, gradient shading, ambient occlusion, polished".
  Name the target's point on it; do NOT assume high-detail.]
[OUTPUT SPEC — transparent background OR seamless tiling; resolution framing; single centered subject; no text]
[NEGATIVES — TARGET-RELATIVE; see below]
```

### Negative prompt — build it from your target, it is NOT universal
The model's prior is to **over-render** (saturated, glossy, gradient-shaded, heavy outlines, busy). Your negatives are the axes where your target *differs* from that prior, so they **depend on the target style**:

- **High-fidelity / painterly target:**
  ```
  NOT: flat single-color fill, MS-Paint look, programmer art, hard jagged edges, muddy colors,
  low detail, blurry, watermark, text, drop-shadow box, off-model, inconsistent lighting, cluttered.
  ```
- **Flat / minimal / muted target** (cozy-vector, flat-design puzzle — a *premium* look, not amateur):
  ```
  NOT: thick outline, black outline, glossy, gradient, painterly, volumetric shading, saturated,
  high-contrast, busy/over-detailed, drop shadow, photo, 3D render, watermark, text.
  ```

Never paste a fixed "universal" list — `NOT: flat single-color fill` will actively sabotage a flat target.

## The refine loop (don't accept the first generation)

1. Generate at 1K to check composition; regenerate the prompt (not just reroll) if the silhouette/framing is wrong.
2. Once composition is right, generate at 2K and pass the previous image via `--input-image` to refine: fix edges, recolor to palette, increase detail, enforce light direction.
3. Score against the per-asset rubric below; iterate until it passes. Reuse **verbatim style tokens** every pass — paraphrasing causes drift.

### Per-asset rubric (pass before importing)
- Reads at gameplay size (silhouette clear at the on-screen scale)?
- On-palette and on-model with the style sheet?
- Consistent light direction with the rest of the set?
- Clean alpha edges (sprites) or seamless tiling (textures)?
- Detail/material present — not a flat fill?

## Material & environment textures (the most-missed assets)

Top-down and side-scrolling games live or die on **textured ground**, not flat color. Generate **seamlessly tiling** textures and tilesets:

```
Seamless tiling [grass / sand / stone / dirt] ground texture, top-down, [hand-painted stylized] style,
[palette tokens], subtle natural variation and detail (blades/grain/cracks), soft even lighting,
high-detail game texture, seamless on all edges, no seams, no centered subject, no text.
NOT: flat single color, visible seams, repeating obvious motifs, MS-Paint fill.
```

Path/road for a TD/runner:
```
Seamless tiling [dirt path / cobblestone road] texture with subtle worn edges, top-down,
[hand-painted stylized], [palette tokens], soft top-left light, high-detail, tiles seamlessly,
no text. NOT: flat fill, hard edges, visible seams.
```

Import tiling textures with `wrapMode = Repeat`, mipmaps **on** for 3D/material use (off for crisp 2D UI), ASTC on iOS (see `unity-image-generator`).

## Genre art kits

Each kit lists the surfaces to generate (default = generate all) and an exemplar prompt for the signature asset. Adapt tokens to your direction.

### Tower defense (top-down)
Surfaces: **tiling ground texture**, **textured path/track**, **build-slot tiles**, **tower set (per tier)**, **enemy set (per type)**, **base/objective**, **environment scatter (rocks/trees/bushes)**, **projectiles/VFX**, **HUD (coins/lives/wave) + buttons**.

> The classic TD amateur look = flat green fill + flat tan path + translucent square slots + one castle. Replace the **ground, path, and slots with real textures** and add **scatter props** first — that alone removes most of the MS-Paint read.

> Acting assets need animation states, and the default is Tripo. Archer/tower: rig + idle/aim/fire cycles (for 2D, pre-render those cycles to sprite frames); a directly-generated 2D idle/aim/fire frame strip is the fallback (Tripo key `MISSING`). See `../../unity-animation/SKILL.md`. The fire clip must release the projectile on the loose frame via an Animation Event.

Exemplar — tower:
```
A stylized [stone-and-crystal] defense tower, top-down 45° orthographic view, centered,
[hand-painted painterly] style à la [Clash Royale / Kingdom Rush], chunky readable silhouette,
[palette: warm stone + glowing teal accent], matte stone with a glossy crystal, soft key light
from top-left with a soft contact shadow, high-detail clean game-ready asset, transparent background,
single centered subject, no text. NOT: flat fill, MS-Paint, jagged edges, off-model, baked UI.
```

Exemplar — build-slot tile (instead of a translucent square):
```
A stylized buildable platform tile for a tower-defense slot, top-down, [hand-painted], [palette tokens],
subtle rim/border so it reads as placeable, soft top-left light + contact shadow, high-detail,
transparent background, single tile centered, no text. NOT: flat translucent square, hard edges.
```

### Endless runner / arcade (side or 3/4 view)
Surfaces: **player character** (animated → Tripo rig with run/jump cycles, pre-rendered to sprites for 2D by default; directly-generated run/jump frames are the fallback when the Tripo key is `MISSING`), **obstacle set**, **collectibles**, **parallax background layers (3–4)**, **ground/track texture**, **VFX**, **HUD**.

Exemplar — parallax background:
```
Seamless horizontally-tiling parallax background layer, [stylized storybook] style, [palette tokens],
[mid-distance rolling hills with soft atmospheric depth], soft directional light, full-bleed,
high-detail, tiles seamlessly left-right, no centered subject, no text. NOT: flat gradient, seams, MS-Paint.
```

### Match-3 / puzzle (portrait board)
Surfaces: **gem/tile set (cohesive family)**, **board/background**, **panel/frame art**, **special-tile FX**, **HUD/buttons**, **win/lose art**.

Exemplar — gem family (generate as one sheet for uniformity, via `unity-asset-designer`):
```
A set of [6] match-3 gems on one sheet, uniform size and lighting, [glossy candy] style,
[palette: 6 distinct saturated hues], each a clear distinct shape for colorblind readability,
soft top light with glossy highlight and soft contact shadow, high-detail, transparent background,
evenly spaced grid, no text. NOT: flat fill, inconsistent sizes/lighting, muddy colors.
```

### .io / physics / casual 3D
Surfaces: **player/avatar (rigged)**, **enemy/NPC set**, **environment props/obstacles**, **ground/arena material**, **pickups**, **skybox/backdrop**, **HUD**. Use `unity-3d-generator` for rigged models; condition on a turnaround sheet from `unity-asset-designer`.

## Named visual touchstones (pick ONE per project, as a style anchor — never mix)
Casual-painterly (Clash Royale, Kingdom Rush) · clean flat-vector (Two Dots, I Love Hue) · glossy candy (Royal Match, Candy Crush) · soft 3D claymation/diorama (Monument Valley-ish) · storybook watercolor · neon-retro/synthwave · cozy pixel art. State the touchstone in every prompt; reuse it verbatim across the asset set.
