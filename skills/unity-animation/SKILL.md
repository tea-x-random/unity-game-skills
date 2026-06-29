---
name: unity-animation
description: "Make game assets MOVE — AAA-quality, gameplay-synced animation for casual iOS games in Unity, via 2D sprite animation OR 3D skeletal animation. Use whenever an asset that acts in the game is static or stiff: a tower/archer with no aim/shoot cycle, an enemy that slides instead of walks, a character with no idle/move/hit/death, a collectible that doesn't bob, a boss with no attack tells. Covers the per-role animation requirement catalog (idle/move/attack/hit/death/spawn for units & enemies; idle/aim/fire/reload for towers; idle/run/jump/action/hurt/die for players; bob/spin/collect for pickups), the production tracks — for ALL motion the DEFAULT is 3D skeletal animation (Tripo auto-rig + animation via unity-3d-generator, humanoid/generic rig, retargeting), and for 2D games pre-render that rig to sprite frames so identity holds; generating per-state frame strips frame-by-frame with Gemini/unity-image-generator (slice, build Animation Clips + Animator Controller) is the FALLBACK only when the Tripo key is missing/quota-blocked or motion is trivial, since image-model frames drift — Unity Animator Controllers/state machines/blend trees/parameters & triggers, and crucially ANIMATION EVENTS that fire gameplay at the right frame (release the arrow on the bowstring-release frame, deal damage on the contact frame). Also covers easing/anticipation/follow-through, seamless loops, mobile animation performance (sprite atlases, bone counts, animation compression, GPU skinning, don't animate offscreen), and an animation quality bar/scorecard. Triggers on: animation, animated, sprite animation, sprite sheet, frame animation, animation clip, animator controller, state machine, blend tree, animation event, skeletal/rigged animation, rig, Tripo animation, walk/run/idle/attack/shoot/death cycle, projectile timing, shooting animation, juice/anticipation/follow-through, AAA animation. Pairs with unity-3d-generator (rig/anim generation), unity-image-generator (sprite-sheet frames), unity-gameplay-systems (procedural game-feel juice), unity-aaa-graphics (visual+animation scorecard), and unity-art-direction (the AssetBrief's animation field)."
---

# Unity animation

Static art reads as a prototype. AAA games are defined by **motion** — an archer that draws, holds, and looses; an enemy that walks with weight and flinches when hit; a coin that bobs and pops on pickup. **Animation is a first-class deliverable for every asset that acts, not optional polish.** A perfectly-rendered but static archer fails the bar exactly like a flat-fill background does.

> **Core rule: every asset that *acts* in the game must be animated, and any action that has a gameplay effect must fire that effect on the correct animation frame.** A shoot animation that doesn't release the projectile on the release frame is broken, not decorative.

> **Motion → Tripo, static → Gemini.** Produce anything that moves with **Tripo3D** — rig + animate, and for 2D games **pre-render the rig to sprite frames** (`../unity-3d-generator/references/prerender-2d.md`) so identity holds across every frame. Use **Gemini** only for static art and for high-quality **reference images** that condition the Tripo model. Generating frames frame-by-frame with an image model **drifts** and is a fallback only when `TRIPO_API_KEY` is MISSING/quota-blocked.

## When to use which track

- **3D skeletal animation (Tripo) — the DEFAULT producer of motion for BOTH 2D and 3D games.** Tripo auto-rigs the model and generates animation cycles; for 3D/2.5D assets import the rig and drive it with an Animator, and for 2D/top-down/side games **pre-render the rigged + animated model to sprite frames** (`../unity-3d-generator/references/prerender-2d.md`) so one model holds identity across every frame. This is how you get drift-free motion either way.
- **Frame-by-frame 2D sprite authoring (Gemini frame strips) — FALLBACK only.** Use it when Tripo is unavailable (`TRIPO_API_KEY` MISSING/quota-blocked) or the motion is trivial (a simple bob/tween). Independently generating each frame with an image model **drifts** — identity changes between frames — so it is never the first choice for real motion.
- **Procedural / tween motion** — squash-stretch, bob, anticipation, screen-shake, hit-stop — layered on TOP of (or instead of, for simple props) authored animation. Owned by `unity-gameplay-systems` game-feel; use it for pickups, button presses, and juice.

Pick per asset: a bobbing coin needs only a tween; an archer needs authored idle + aim + fire with a frame event — rig + animate it in Tripo (and pre-render to a strip for 2D).

## Animation requirement catalog (per asset role)

Enumerate the required clips per asset BEFORE generating — a single static pose is almost never enough. Defaults:

| Asset role | Minimum clips |
|---|---|
| **Tower / turret (e.g. archer)** | `idle`, `aim`/charge, `fire`/attack (with projectile-release event), optional `upgrade` |
| **Enemy / unit** | `spawn`, `walk`/move (loop), `attack` (with hit event), `hurt`/flinch, `death` |
| **Player / hero** | `idle` (loop), `move`/run (loop), `jump` or primary `action` (with event), `hurt`, `death`/win |
| **Boss** | the enemy set + telegraphed `attack` tells (clear anticipation), `phase`/enrage |
| **Collectible / pickup** | `idle` bob/spin (loop), `collect` pop (often a tween + VFX) |
| **Projectile / VFX** | `travel` (loop or tween), `impact` |
| **UI** | button `press`, reward/`win`, screen transitions (see `unity-ui-designer`) |

For a tower-defense **archer** specifically: `idle` (subtle breathing) → `aim` (nock + draw, can hold) → `fire` (loose + recoil) with an **Animation Event on the bowstring-release frame** that calls the shooting code to spawn the arrow. That sync is what makes it read as a real game.

## Track A — 2D sprite animation

The **DEFAULT** way to get 2D animation frames is to **rig + animate a 3D model in Tripo and render each frame to a sprite strip** (`../unity-3d-generator/references/prerender-2d.md`) — one rigged model holds identity across every frame, so the motion is drift-free. Do this first.

Generating per-state frame strips directly with Gemini (the numbered procedure below) is a **FALLBACK** — reach for it only when `TRIPO_API_KEY` is MISSING/quota-blocked, or the motion is trivial (a simple bob). Independently generating each frame with an image model causes **identity drift** (the character changes between frames), so it is not the first choice for real motion.

**Fallback procedure (Gemini frame strips):**

1. **Lock an anchor frame first**, then derive the strip. Generate/approve one neutral anchor pose (same palette/outline/scale as the asset contract), run `validate_sprite.py` + `critique_image.py`, then use it as `--input-image` when asking for the strip. This template-guided flow reduces identity drift compared with a text-only strip prompt.
2. **Generate per-state frame strips** with `unity-image-generator`: request an evenly-spaced horizontal strip of N frames on a transparent background, consistent pivot/scale/baseline across frames, one clip per state. Prompt for the motion explicitly (e.g. "8-frame archer firing cycle: nock, draw, hold, loose, recoil — evenly spaced, transparent, same character identity, same body size, feet touch the same baseline"). Reuse verbatim style tokens so frames stay on-model (see `unity-aaa-graphics/references/prompt-library.md`).
   - Frame-count guidance: idle/bob 2–6, walk 6–8, attack/fire 5–10. More frames = smoother but heavier; ease the in-betweens, don't just linearly tween.
3. **Extrude/pad the sheet** before import to prevent texture bleed: `unity-image-generator/scripts/extrude_atlas.py --rows 1 --cols <N> --extrude 2 --padding 2 ...`; slice using the manifest's frame rects.
4. **Slice** in Unity (Sprite Editor → Grid by Cell Count / Sequence or manifest rects) with a consistent pivot/baseline. Reject sheets where the character visibly changes size or feet/ground contact drift.
5. **Build Animation Clips** (one per state), set frame rate (10–14 fps reads well for casual), loop idle/walk, one-shot attack/death.
6. **Animator Controller** with states + transitions driven by parameters/triggers (`Speed` float, `Fire` trigger, `IsDead` bool).
7. **Pack frames into a Sprite Atlas** to keep draw calls down.

See `references/animation-recipes.md` for the clip-build + Animation Event code.

## Track B — 3D skeletal animation

1. **Rig + animate via Tripo** (`unity-3d-generator`): auto-rig the model, then generate/retarget the needed cycles (idle, walk, attack, …). Prefer rigging a clean game-ready mesh (see `unity-art-direction` budgets). Rigging requires the source model be generated from a clean **T-pose/A-pose** concept — action poses break the rig (see `unity-3d-generator` → "Riggable characters need a clean full-body T-pose"); author the action (draw/attack) as animation clips here, not baked into the rest pose.
2. **Import the rig** as Humanoid (retargetable, reuse a shared controller across characters) or Generic (non-humanoid creatures/turrets); configure the Avatar.
3. **Animator Controller** with state machine + blend trees (e.g. an idle↔move blend on `Speed`); reuse one controller across same-rig characters.
4. **Animation Events** on attack/fire clips to call gameplay (deal damage / spawn projectile) on the contact/release frame.
5. **Retarget** shared humanoid clips across characters to avoid regenerating common motion.

## Animation Events — sync motion to gameplay (the critical part)

The action must affect the game on the right frame, not on button-press. Add an **Animation Event** to the `fire`/`attack` clip at the release/contact frame that calls a method on the asset's controller (e.g. `OnFireFrame()` → spawn arrow; `OnHitFrame()` → apply damage). This applies to BOTH tracks. Without it you get the classic "the arrow leaves before the bow moves" tell. Code in `references/animation-recipes.md`.

## Game-feel layer (load `unity-gameplay-systems`)

Layer procedural juice on authored animation: squash-stretch on land/impact, anticipation dip before a jump, screen-shake + hit-stop on heavy hits, ease-out-back on UI/pickup pops, haptics. This is cheap and disproportionately lifts perceived quality — but it complements authored clips, it does not replace an archer's draw-and-loose.

## Animation quality bar / scorecard

Score each; fix any that fail before "done":

- **Nothing static that should move** — no T-pose/frozen asset where motion is expected (auto-fail).
- **Anticipation & follow-through** present on actions (wind-up before, settle after) — not a single linear pose change.
- **Smoothness** — enough frames / proper interpolation; no visible stutter at gameplay speed.
- **Loops seamless** — idle/walk/run cycle with no pop at the loop point.
- **Gameplay sync** — projectile/damage fires on the correct frame via an Animation Event.
- **Style & weight consistent** across the set (all characters share timing/weight conventions).
- **Readable at gameplay scale** — the action reads at the on-screen size and from the game camera.

## Mobile performance

- 2D: pack animation frames into **Sprite Atlases**; cap frame counts; share clips across similar enemies.
- 3D: keep bone counts modest; enable **animation compression** (Optimal/keyframe reduction); consider **GPU skinning**; reuse one Animator Controller + retargeted humanoid clips across characters.
- Don't animate offscreen — cull Animators (`cullingMode = CullCompletely` / disable when not visible).
- Prefer a few well-timed frames over many redundant ones; bake long procedural motion where possible.

## Where this sits

- **`unity-3d-generator`** — produces the rig + 3D animation clips this skill imports and wires.
- **`unity-image-generator`** — produces the 2D frame strips this skill slices into clips.
- **`unity-art-direction`** — the AssetBrief's `animation` field declares required clips per asset; budgets bound bone/frame counts.
- **`unity-aaa-graphics`** — its visual scorecard includes an animation axis; a static asset where motion is expected fails the gate.
- **`unity-gameplay-systems`** — procedural game-feel/juice that layers on top.

## Field notes & lessons

- **Motion → Tripo; static → Gemini.** Anything that moves gets rigged + animated in Tripo (pre-rendered to a strip for 2D). Gemini is for static art and reference images that condition Tripo; generating animation frames frame-by-frame with Gemini **drifts** (identity changes between frames) and is a fallback only when `TRIPO_API_KEY` is MISSING/quota-blocked.
- The #1 "looks like a prototype" tell after flat art is **static assets that should move** — an archer with no draw, an enemy that slides. Animate every actor.
- The arrow must leave the bow on the **release frame**, not on the input — always wire an Animation Event; firing on button-press instead of on-frame is the most common amateur mistake.
- Author the few high-impact clips (idle/move/attack/hit/death) first; reuse and retarget shared motion rather than generating per-character.
- Procedural juice (squash-stretch, shake, hit-stop) is a force-multiplier ON TOP of authored animation, not a substitute for it.
- Seamless loops matter: a popping idle/walk loop cheapens an otherwise good asset — match first/last frames.
