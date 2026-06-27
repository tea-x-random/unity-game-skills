---
name: unity-aaa-graphics
description: "Upgrade a basic, flat, or 'programmer-art / MS-Paint'-looking Unity casual iOS scene to premium, intentional, store-quality visuals. The visual-quality ENFORCEMENT layer above the asset generators and unity-graphics — use it whenever a scene looks flat/primitive, uses solid-color fills or procedural placeholder shapes for primary surfaces, mixes one generated 'hero' asset with untextured everything-else, or the user asks for premium, polished, AAA, high-fidelity, juicy, 'make it look good', or 'less basic' visuals. Drives a heavy, art-first pipeline: an art-direction critique, a MANDATORY per-surface asset-sourcing decision (generate real art for every primary visible surface — terrain/ground, path/track, player, enemies, towers, signature props, key UI — procedural only as a true fallback), genre art kits, AAA prompt engineering with a refine loop, render polish (URP lighting/material/post via unity-graphics), and a visual scorecard gate that FAILS amateur output. Triggers on: looks flat, looks basic, looks like Microsoft Paint, programmer art, placeholder art, premium, AAA, polished, high-fidelity, juicy, art direction, visual quality, make it look good, upgrade the visuals, tower defense art, runner art, environment art, terrain texture, tileset. Loads unity-asset-designer (style guide/sheets), unity-image-generator (2D/textures/tilesets), unity-3d-generator (models), and unity-graphics (render pipeline)."
---

# Unity AAA graphics

Visuals are the first thing a player sees and the biggest driver of "is this a real game or a toy." This skill exists to stop the most common failure mode: a scene where the gameplay works but the art is **flat solid-color fills + procedural placeholder shapes + one lonely generated sprite**, which reads as amateur ("made in MS Paint") no matter how good the mechanics are.

The fix is not "add bloom." It is an **art-first pipeline**: decide a direction, generate real art for **every** primary visible surface, light and finish the scene, and gate on a concrete visual scorecard.

> **Core rule: real generated art is the DEFAULT for every primary visible surface, not an optional upgrade for one hero asset.** Procedural/runtime shapes are a *fallback* for when a generator key is `MISSING`/quota-blocked, or for genuinely low-value repeated props — never the plan for the things a player stares at.

## The amateur-look failure modes (what makes a scene read as "MS Paint")

Diagnose against this list — each one is a fixable cause:

- **Flat solid-color fills** for ground/background/regions (no texture, gradient, or material variation).
- **Procedural primitive shapes** (plain rects/blobs) standing in for terrain, paths, towers, props.
- **One generated "hero" asset on top of untextured everything-else** — the mismatch screams placeholder.
- **No lighting/shadow/depth** — everything is uniformly lit and flat (no URP, no shadows, no ambient occlusion, no real vignette/gradient).
- **No cohesive art direction** — assets don't share palette, light direction, line weight, or finish.
- **Crude vignette/overlay hacks** (a hard dark oval) instead of real lighting or a designed backdrop.
- **Empty negative space** with no environmental detail, scatter, or framing.

If two or more apply, the scene fails the bar — run the full pipeline below.

## Pipeline (art-first, heavy on generation)

### 1. Art direction first (load `unity-asset-designer`)
Pin a concrete north-star (reference style + 4–7 color palette with roles + light direction + finish + mood/anti-mood) BEFORE generating anything, and build the style-guide / reference sheets so every asset is on-model. See `unity-game-director` Step 2.6 and `unity-asset-designer`. Without this, generated assets drift and you get the one-hero-mismatch problem.

### 2. Enumerate EVERY visible surface, then decide source per surface (mandatory)
List the full visible surface set for the genre (see genre kits in `references/prompt-library.md`), and for **each** make an explicit generate-vs-procedural decision. **Default to generate.** Procedural only if: key `MISSING`/quota-blocked (show the probe output), or a genuinely low-value repeated element better done by atlas/instancing.

Example for **tower defense** — all of these are "generate," not "fill with green":
- **Ground/terrain** → a tiling textured ground (grass/sand/stone with variation), not a flat color.
- **Path/track** → a textured road/path tile or spline texture with edges/borders.
- **Towers** (each tier) → distinct on-model sprites/models.
- **Enemies** (each type) → distinct readable silhouettes.
- **Base / objective** → the hero structure.
- **Environment scatter** → rocks, trees, bushes, decals that fill negative space.
- **Build-slot / placement tiles** → designed slots, not translucent squares.
- **HUD/UI** → designed currency/lives/wave readouts and buttons (see `unity-ui-designer`).

### 3. Generate with AAA prompts (load `unity-image-generator` / `unity-3d-generator`)
Use the **prompt template and genre exemplar prompts** in `references/prompt-library.md` — not one-line prompts. Generate environment textures/tilesets and props, condition each on the style sheet, and run the refine loop until each asset clears the per-asset rubric. Import with correct settings (Sprite/Texture, ASTC, atlas) per the generator skills.

### 4. Light, finish, and compose the scene (load `unity-graphics`)
Apply the render pipeline — this is what turns flat sprites into a lit scene: URP set up, a real lighting setup (not uniform flat), soft shadows/AO where it reads, a designed backdrop or gradient (not a hard oval), mobile-safe post (subtle bloom/vignette/color grade), and depth cues (fog/parallax/scale). Build forms + palette + lighting first; add post last.

### 5. Add juice (load `unity-gameplay-systems`)
Short, additive particle/feedback bursts (place, hit, wave-clear, win) lift perceived quality cheaply.

### 6. Gate on the visual scorecard (below) — do not call visuals "done" until it passes.

## Visual scorecard gate

Capture a real device-resolution screenshot via MCP and score 1–10 on each axis. **Any axis ≤ 4 is an automatic fail → fix and re-shoot.** Target an ~8/10 average before "done."

| Axis | Passing looks like |
|------|--------------------|
| **Surfaces textured** | Ground/path/regions are real textured art, NOT flat fills |
| **Asset cohesion** | All assets share palette, light direction, finish — no one-hero mismatch |
| **Lighting & depth** | Real lighting/shadow/gradient; the scene reads 3D/layered, not uniformly flat |
| **Composition** | Clear focal point, intentional framing, negative space filled with scatter/detail |
| **Finish consistency** | Every element flat *or* every element rendered — never mixed |
| **Readability** | Gameplay-critical elements (path, towers, enemies) pop against the ground |
| **HUD/UI quality** | Designed readouts/buttons, on-theme — not default labels on flat bars |

Auto-fail anti-patterns (ship-blockers): flat solid-color ground; procedural blobs for primary surfaces; one generated asset amid untextured everything-else; hard-oval vignette as the only "lighting."

## Where this sits

- **`unity-art-direction`** — the locked `art-spec.yaml` single-source-of-truth + 12-preset style library + mobile art budgets + golden-asset/family production pipeline that this skill's per-surface sourcing and visual scorecard operate within. Lock the art-spec there first.
- **`unity-asset-designer`** — art bible + reference sheets (do this before generating).
- **`unity-image-generator`** — 2D sprites, **environment textures/tilesets**, UI; the AAA prompt library lives alongside it and here.
- **`unity-3d-generator`** — 3D models/props.
- **`unity-graphics`** — the URP render-pipeline mechanics (lighting/material/post) this skill requires you to actually apply.
- **`unity-game-director`** — owns the Visual Quality Gate and routes premium/AAA requests here.

## Field notes & lessons

- The signature "made in MS Paint" look is almost always **flat-fill environment + procedural primitives + one generated hero asset**. The cure is generating real art for *every* primary surface, not better procedural shapes.
- Environment/terrain is the most-overlooked surface: a tiling textured ground + a textured path instantly removes 80% of the amateur read in top-down/TD games.
- One-line prompts produce one-line art. The prompt template (subject + style + material + lighting + render fidelity + framing + negatives) is the difference between placeholder and production — see `references/prompt-library.md`.
- Procedural-fallback guidance is for *blocked* pipelines only; never present it as "premium." If a key is `MISSING`, say so and flag bespoke art as the upgrade rather than calling the placeholder look done.
- Generated sprites still look flat until the scene is **lit and composed** — always finish with `unity-graphics` (lighting + backdrop + post), not raw sprites on a solid color.
