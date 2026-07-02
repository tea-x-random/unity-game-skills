---
name: unity-animation
description: "Make game assets MOVE — AAA-quality, gameplay-synced animation for casual iOS games in Unity, via 2D sprite animation OR 3D skeletal animation. Use whenever an asset that acts in the game is static or stiff: a tower/archer with no aim/shoot cycle, an enemy that slides instead of walks, a character with no idle/move/hit/death, a collectible that doesn't bob, a boss with no attack tells. Covers the per-role animation requirement catalog (idle/move/attack/hit/death/spawn for units & enemies; idle/aim/fire/reload for towers; idle/run/jump/action/hurt/die for players; bob/spin/collect for pickups), the production tracks — PIXEL ART motion uses unity-pixel-art/PixelLab anchor-first sprite sheets; non-pixel/high-res 2D motion may use Tripo auto-rig + pre-render via unity-3d-generator; runtime 3D uses skeletal animation; generating per-state frame strips frame-by-frame with Gemini/unity-image-generator is concept/fallback only because image-model frames drift — Unity Animator Controllers/state machines/blend trees/parameters & triggers, and crucially ANIMATION EVENTS that fire gameplay at the right frame (release the arrow on the bowstring-release frame, deal damage on the contact frame). Also covers easing/anticipation/follow-through, seamless loops, mobile animation performance (sprite atlases, bone counts, animation compression, GPU skinning, don't animate offscreen), and an animation quality bar/scorecard. Triggers on: animation, animated, sprite animation, sprite sheet, frame animation, animation clip, animator controller, state machine, blend tree, animation event, skeletal/rigged animation, rig, Tripo animation, walk/run/idle/attack/shoot/death cycle, projectile timing, shooting animation, juice/anticipation/follow-through, AAA animation. Pairs with unity-pixel-art (pixel-native sprite sheets), unity-3d-generator (rig/anim generation), unity-image-generator (concept/non-pixel fallback frames), unity-gameplay-systems (procedural game-feel juice), unity-aaa-graphics (visual+animation scorecard), and unity-art-direction (the AssetBrief's animation field)."
---

# Unity animation

Static art reads as a prototype. AAA games are defined by **motion** — an archer that draws, holds, and looses; an enemy that walks with weight and flinches when hit; a coin that bobs and pops on pickup. **Animation is a first-class deliverable for every asset that acts, not optional polish.** A perfectly-rendered but static archer fails the bar exactly like a flat-fill background does.

> **Core rule: every asset that *acts* in the game must be animated, and any action that has a gameplay effect must fire that effect on the correct animation frame.** A shoot animation that doesn't release the projectile on the release frame is broken, not decorative.

> **Pixel-art motion → PixelLab anchor-first. Non-pixel motion → Tripo/Animator. Gemini → concept/reference.** Pixel art must be generated at native canvas with `unity-pixel-art`; do not render Tripo/3D and downscale into pixel sprites. For non-pixel/high-res 2D, Tripo3D rig + pre-render still holds identity across frames. Gemini frame-by-frame generation drifts and is fallback/concept only.

## When to use which track

- **Pixel-art sprite animation (PixelLab via `unity-pixel-art`) — the DEFAULT for pixel-art games.** Lock one anchor/base sprite, then drive motion with PixelLab's **skeleton animation** (`estimate-skeleton` → author per-frame poses → `animate-skeleton`), `rotate` for directions, and `inpaint` for fixes — then slice/build Animation Clips here. **Every PixelLab call carries the palette lock** (`color_image`: master palette for anchors, the anchor's extracted sub-palette for derived frames) — a call without it is invalid. Skeleton-driven frames stay structurally consistent (identity, clusters, palette, baseline, silhouette); PixelLab `animate-text` and image-model frame strips drift and are fallback only.
- **3D skeletal animation (Tripo) — the DEFAULT for runtime 3D and non-pixel/high-res 2D pre-render.** Tripo auto-rigs the model and generates animation cycles; for 3D/2.5D assets import the rig and drive it with an Animator, and for non-pixel 2D/top-down/side games pre-render the rigged + animated model to sprite frames (`../unity-3d-generator/references/prerender-2d.md`).
- **Frame-by-frame 2D sprite authoring (Gemini frame strips) — FALLBACK only.** Use it when Tripo is unavailable (`TRIPO_API_KEY` MISSING/quota-blocked) or the motion is trivial (a simple bob/tween). Independently generating each frame with an image model **drifts** — identity changes between frames — so it is never the first choice for real motion.
- **Procedural / tween motion** — squash-stretch, bob, anticipation, screen-shake, hit-stop — layered on TOP of (or instead of, for simple props) authored animation. Owned by `unity-gameplay-systems` game-feel; use it for pickups, button presses, and juice.

Pick per asset: a bobbing coin needs only a tween; a pixel-art archer needs PixelLab anchor-first idle + aim + fire sheets with frame events; a non-pixel/3D archer needs authored idle + aim + fire from Tripo/Animator (pre-rendered to a strip only for non-pixel 2D).

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

For **pixel-art** games, the default way to get animation frames is `unity-pixel-art`: create one approved PixelLab anchor sprite, then derive each clip/direction from that anchor at the native pixel canvas. Do **not** use 3D renders/downscales as pixel-art frames.

For **non-pixel/high-res 2D**, the default remains Tripo rig + pre-render (`../unity-3d-generator/references/prerender-2d.md`) when consistency/angles matter.

Generating per-state frame strips directly with Gemini is a **FALLBACK** — reach for it only when `PIXEL_LABS_API_KEY` / `TRIPO_API_KEY` are missing or quota-blocked for the chosen final route, or the motion is trivial (a simple bob). Independently generating each frame with an image model causes **identity drift** (the character changes between frames), so it is not the first choice for real motion.

**Sheet procedure:**

1. **Lock an anchor frame first**, then derive the strip. For pixel art, the anchor is a PixelLab native-canvas sprite from `unity-pixel-art`; for non-pixel fallback strips, use an approved reference frame. Run `validate_sprite.py` + `critique_image.py` (both with `--art-spec <spec>` — they FAIL without a resolvable spec; `--no-art-spec` is exploratory-only) where applicable before expansion.
2. **Generate per-state frame strips** with `unity-pixel-art` for pixel-art projects (master palette / anchor sub-palette as `color_image` on every call), or with `unity-image-generator` only for non-pixel fallback/concept strips: request an evenly-spaced horizontal strip of N frames on transparent background, consistent pivot/scale/baseline across frames, one clip per state. Reuse verbatim style tokens and anchor/reference images so frames stay on-model.
   - Frame-count guidance: idle/bob 2–6, walk 6–8, attack/fire 5–10. More frames = smoother but heavier; ease the in-betweens, don't just linearly tween.
3. **Gate pixel strips with the frame-vs-anchor diff (MANDATORY before slicing):** `unity-pixel-art/scripts/compare_frames_to_anchor.py --anchor <approved_anchor.png> --strip <clip_strip.png> --cols <N>` — deterministic palette-membership + baseline/bbox-height + loose silhouette-IoU checks. Exit 1 = repair the failing frame (`inpaint` / `--init-images` freeze via `unity-pixel-art`), never re-roll the whole strip. Eyeballing does not replace this gate.
4. **Extrude/pad the sheet** before import to prevent texture bleed: `unity-image-generator/scripts/extrude_atlas.py --rows 1 --cols <N> --extrude 2 --padding 2 ...`; slice using the manifest's frame rects.
5. **Slice** in Unity (Sprite Editor → Grid by Cell Count / Sequence or manifest rects) with a consistent pivot/baseline. Reject sheets where the character visibly changes size or feet/ground contact drift.
6. **Build Animation Clips** (one per state), set frame rate (10–14 fps reads well for casual), loop idle/walk, one-shot attack/death.
7. **Animator Controller** with states + transitions driven by parameters/triggers (`Speed` float, `Fire` trigger, `IsDead` bool).
8. **Pack frames into a Sprite Atlas** to keep draw calls down.

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
- **`unity-pixel-art`** — produces pixel-native anchors, sheets, rotations, and frame strips for pixel-art animation.
- **`unity-image-generator`** — produces non-pixel 2D frame strips only when appropriate, plus concepts/references and validators.
- **`unity-art-direction`** — the AssetBrief's `animation` field declares required clips per asset; budgets bound bone/frame counts.
- **`unity-asset-pipeline`** — finished sprite sheets, Animation Clips, and Animator Controllers ship through the asset contract + approved registry exactly like static art (contract lists sheet/clip/controller paths; the BeautyCell scores a designated key pose). Scene builders take animated prefabs from the registry, never from raw generated strips.
- **`unity-aaa-graphics`** — its visual scorecard includes an animation axis; a static asset where motion is expected fails the gate.
- **`unity-gameplay-systems`** — procedural game-feel/juice that layers on top.

## Field notes & lessons

- **Pixel-art motion → PixelLab; non-pixel/3D motion → Tripo; Gemini → concept/static reference.** Generating animation frames frame-by-frame with Gemini drifts (identity changes between frames) and is fallback/concept only.
- The #1 "looks like a prototype" tell after flat art is **static assets that should move** — an archer with no draw, an enemy that slides. Animate every actor.
- The arrow must leave the bow on the **release frame**, not on the input — always wire an Animation Event; firing on button-press instead of on-frame is the most common amateur mistake.
- Author the few high-impact clips (idle/move/attack/hit/death) first; reuse and retarget shared motion rather than generating per-character.
- Procedural juice (squash-stretch, shake, hit-stop) is a force-multiplier ON TOP of authored animation, not a substitute for it.
- Seamless loops matter: a popping idle/walk loop cheapens an otherwise good asset — match first/last frames.

## Verification: playing ≠ visible (both are gates)

Field bug class: the Animator graph is mechanically perfect (trigger fires, state enters, exits
on time) yet the player reports "the animation doesn't work" — because the clip's frames are
near-identical. Two REQUIRED checks for every gameplay-triggered clip:

1. **State-entry PlayMode assertion** (machine correctness): after simulating the input, assert
   the Animator actually enters the state and returns —
   `animator.GetCurrentAnimatorStateInfo(0).shortNameHash == Animator.StringToHash("slash")`
   within N frames, then back to the default state. One test per input-reachable state.
2. **Visible-motion gate** (content correctness): action strips (attack/hit/death) must pass
   `compare_frames_to_anchor.py --action` (≥0.35 inter-frame pixel change; a real run cycle
   measures ~0.78, a too-subtle slash that shipped broken measured 0.27). Selling a fast action
   also usually needs code-side motion (a 0.2s lunge/recoil on the visual child) — animation
   frames alone at 3 frames/0.2s under-read.

Death/kill feedback is part of the animation bar: enemies never "pop out of existence" — if no
death strip exists yet, code-driven feedback (flash + squash + fade + particles) is the minimum
and must be named in the asset contract's `animation_waiver`.
