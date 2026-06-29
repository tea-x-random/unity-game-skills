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

> **"Flat" here means *placeholder*, not a style.** The failure above is unintentional flatness — solid-color *fills standing in for surfaces*, primitives standing in for art, and **no cohesion**. It is NOT a verdict on flat/minimal *art direction*. A cohesive flat-design or minimal-vector look (think a polished cozy puzzle game) is **premium**, and this skill must elevate it, not "fix" it into gloss. The enemy is *placeholder + incoherent + unintentional*, never "low gradient count." Likewise "AAA" in this skill = *intentional, cohesive, on-model*, not "high-detail." Before diagnosing a scene as amateur, ask whether the flatness is the **intended target**; if so, the work is to make it cohesive and well-composed at that fidelity, not to add rendering the user never asked for.

## Pipeline (art-first, heavy on generation)

### 1. Art direction first (load `unity-asset-designer`)
Pin a concrete north-star (reference style + 4–7 color palette with roles + line weight + shading model + fidelity + finish + mood/anti-mood) BEFORE generating anything, and build the style-guide / reference sheets so every asset is on-model. **The north-star comes from the user (their stated aesthetic or a reference they provide), never from a house default — and the fidelity/finish are whatever THEY want, flat or rendered.** If the user gave no direction, ASK before generating. See `unity-game-director` Step 2.6 and `unity-asset-designer`. Without this, generated assets drift and you get the one-hero-mismatch problem — or, worse, a confidently-wrong style the skill invented.

### 2. Enumerate EVERY visible surface, then decide source per surface (mandatory)
List the full visible surface set for the genre (see genre kits in `references/prompt-library.md`), and for **each** make an explicit generate-vs-procedural decision. **Default to generate.** Procedural only if: key `MISSING`/quota-blocked (show the probe output), or a genuinely low-value repeated element better done by atlas/instancing.

The per-surface source choice is **Gemini vs Tripo-pre-render**, not just generate-vs-procedural. **Decision rule: if the surface MOVES (character, enemy, tower/unit, any animated actor, or needs multiple angles) → Tripo (rig + animate; for 2D, render the rigged cycles to sprite frames).** If it's static (tiling grounds, backgrounds, UI, icons, single-angle props) → Gemini. A pre-rendered Tripo 3D model holds identity across frames and angles and animates without drift, where independently generated sprites diverge (see `unity-3d-generator` pre-render pipeline). Gemini frame-by-frame drifts, so it is a fallback for motion **only when the Tripo key is `MISSING`** — Gemini's job is static art plus the high-quality reference images that condition Tripo.

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

**Generate per layer, not one intensity for everything.** The same "bold saturated thick black outline" tokens that make a hero asset readable can destroy a ground tile: the ground becomes a noisy foreground subject and the characters stop popping. Background/ground prompts should usually say: low contrast, lower saturation, sparse subtle detail, thin/no outline, recessive surface, NOT busy, NOT focal. Validate with `unity-image-generator/scripts/validate_sprite.py --tile --square --power-of-two` and `critique_image.py --role background_tile --must-recede`.

**Run subject-correctness QA.** A generated image can be attractive and still semantically wrong (e.g. "mossy rock" rendered as a planet/globe). Use `critique_image.py --subject "<exact intended subject>"`; any subject score ≤1 blocks import. Pixel/alpha QA cannot catch this.

### 4. Light, finish, and compose the scene (load `unity-graphics`)
Apply the render pipeline — this is what turns flat sprites into a lit scene: URP set up, a real lighting setup (not uniform flat), soft shadows/AO where it reads, a designed backdrop or gradient (not a hard oval), mobile-safe post (subtle bloom/vignette/color grade), and depth cues (fog/parallax/scale). Build forms + palette + lighting first; add post last.

**Ground every object.** Foreground props/characters need one shared contact-shadow/blob-shadow treatment. Do not accept cutouts floating on the ground, and do not bake inconsistent shadows into each PNG.

### 5. Add juice (load `unity-gameplay-systems`)
Short, additive particle/feedback bursts (place, hit, wave-clear, win) lift perceived quality cheaply.

### 6. Gate on the visual scorecard (below) — do not call visuals "done" until it passes.

## Visual scorecard gate

Capture a real device-resolution screenshot via MCP and score 1–10 on each axis. **Any axis ≤ 4 is an automatic fail → fix and re-shoot.** Target an ~8/10 average before "done." **Every axis is judged against the TARGET style, not against "more rendering."** For a flat/minimal target, "passing" means *intentional and cohesive at that fidelity* — gradients and AO are not required and may be wrong.

| Axis | Passing looks like |
|------|--------------------|
| **Surfaces intentional** | Ground/path/regions are deliberate, on-style art — textured if the style is textured, clean cohesive flat regions if the style is flat — NOT *placeholder* fills |
| **Asset cohesion** | All assets share palette, line weight, shading model, finish — no one-hero mismatch |
| **Depth & hierarchy** | The scene has clear layering and a focal hierarchy by whatever means the style uses — lighting/shadow/gradient for rendered styles, or value/overlap/scale/framing for flat styles — never an accidental uniform mush |
| **Composition** | Clear focal point, intentional framing, negative space used with intent (filled, or deliberately calm) |
| **Finish consistency** | Every element flat *or* every element rendered — never mixed |
| **Layer contrast budget** | Background/ground recedes; gameplay/interactables get the strongest contrast/saturation/outline; no busy tile competes with heroes |
| **Subject correctness** | Every asset is what the brief says it is — attractive wrong-subject generations are rejected |
| **Grounding** | Props/characters sit in the world via consistent contact shadow/AO; no floating stickers |
| **Readability** | Gameplay-critical elements (path, towers, enemies, the board/grid) pop against their ground |
| **HUD/UI quality** | Designed readouts/buttons, on-theme — not default labels on flat bars |
| **Animation** | Assets that act are animated (idle/move/attack/hit/death as needed); actions fire gameplay on the correct frame — nothing static where motion is expected |

Auto-fail anti-patterns (ship-blockers): *placeholder* solid-color ground used because no art was made (≠ an intentional flat-design fill); procedural blobs for primary surfaces; one generated asset amid untextured everything-else; busy/high-contrast ground with the same outline/saturation as heroes; attractive but wrong-subject asset; over-rendered glossy gradients when the locked finish is flat/cel; floating sticker props with no contact shadow; hard-oval vignette as the only "lighting" on a style that wanted real lighting; static asset where motion is expected (no idle/attack/death); projectile/damage firing on input instead of the animation's release/contact frame.

## Where this sits

- **`unity-art-direction`** — the locked `art-spec.yaml` single-source-of-truth + 12-preset style library + mobile art budgets + golden-asset/family production pipeline that this skill's per-surface sourcing and visual scorecard operate within. Lock the art-spec there first.
- **`unity-asset-designer`** — art bible + reference sheets (do this before generating).
- **`unity-image-generator`** — 2D sprites, **environment textures/tilesets**, UI; the AAA prompt library lives alongside it and here.
- **`unity-3d-generator`** — 3D models/props.
- **`unity-graphics`** — the URP render-pipeline mechanics (lighting/material/post) this skill requires you to actually apply.
- `unity-animation` — animates assets (2D sprite / 3D skeletal) and fires gameplay on the correct frame; static actors fail this skill's scorecard.
- **`unity-game-director`** — owns the Visual Quality Gate and routes premium/AAA requests here.

## Field notes & lessons

- The signature "made in MS Paint" look is almost always **flat-fill environment + procedural primitives + one generated hero asset**. The cure is generating real art for *every* primary surface, not better procedural shapes.
- Environment/terrain is the most-overlooked surface: a tiling textured ground + a textured path instantly removes 80% of the amateur read in top-down/TD games.
- One-line prompts produce one-line art. The prompt template (subject + style + material + lighting + render fidelity + framing + negatives) is the difference between placeholder and production — see `references/prompt-library.md`.
- Procedural-fallback guidance is for *blocked* pipelines only; never present it as "premium." If a key is `MISSING`, say so and flag bespoke art as the upgrade rather than calling the placeholder look done.
- Generated sprites still look flat until the scene is **lit and composed** — always finish with `unity-graphics` (lighting + backdrop + post), not raw sprites on a solid color. *Caveat:* this is for rendered targets — a flat-design target is finished by clean composition + cohesion, not by adding lighting it never wanted.
- **Don't confuse "flat placeholder" with "flat style," and never invent the style.** A flat/minimal/muted look (cozy-vector puzzle, flat-design) is premium when cohesive; this skill's job there is cohesion + composition at the target fidelity, not adding gloss/AO. The amateur read comes from *placeholder fills + procedural primitives + incoherence*, not from low gradient count. All fidelity/finish decisions come from the user's brief or a measured reference — if absent, ask. (Real miss: a flat thin-line puzzle game was "upgraded" toward heavy-ink painterly gloss because the pipeline equated flat with amateur.)
