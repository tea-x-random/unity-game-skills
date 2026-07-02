# Attack/Interaction Animation Readability — Research Synthesis & Skill Updates

## 1. Load-bearing findings (ranked)

1. **Player attacks get ~zero anticipation; enemy attacks get long, held anticipation.** saint11 (Celeste/TowerFall): the player attack's hitbox area must be visually filled on frame 1 — windup on player-initiated actions reads as input lag. GDKeys: enemy tells must hold the windup ≥ player reaction time (~250–400ms = one windup sprite held 300ms+ in the clip). Our pipeline currently authors symmetric idle→windup→strike for everyone; that is wrong for the player. (https://www.patreon.com/posts/simple-attack-6837623, https://gdkeys.com/keys-to-combat-design-1-anatomy-of-an-attack/)
2. **Timing is asymmetric per frame, never uniform fps — and weapon weight lives entirely in hold durations.** Slynyrd Pixelblog 56 gives exact tables: sword 100/50/50/50/100/50ms, spear 200/…, hammer 250/…/300/100 — strike frames stay ~50ms for every weapon; only windup/follow-through holds change. Our flat 3-frames-at-0.2s clips are the timing half of the shipped bug. Unity `.anim` keyframes must carry per-frame durations. (https://www.slynyrd.com/blog/2025/5/23/pixelblog-56-top-down-character-attack-animation)
3. **Pose-to-pose with maximally distinct extremes, never in-betweens** — Dead Cells: "the least amount of frames possible… I add interpolation frames before or after the key frames. Never in-between," with VFX carrying motion/impact. The near-identical-frames bug is a direct violation: frames were authored as small deltas toward an end pose instead of four distinct extremes. (https://www.gamedeveloper.com/production/art-design-deep-dive-using-a-3d-pipeline-for-2d-animation-in-i-dead-cells-i-)
4. **Poses and timing are separate artifacts with separate iteration costs.** Dead Cells retimed attacks "dozens of times in minutes" by moving keyframes without touching art. Doctrine: PixelLab owns poses (regenerate only when a pose is wrong); Unity keyframe times own feel (retune freely). "Regenerate because it feels slow" must be forbidden. (same source as #3)
5. **The slash arc is a separate overlay asset, not character frames** — canonical since SNES (ALttP's sword is a separate sprite with per-frame offsets; SNES color-math rendered effects additively over characters) and standard commercially today (jasontomlee SlashFX, Unity Asset Store slash VFX packs). Retro Diffusion's API even ships VFX as a separate model from character animation. Confirms and generalizes our lunge fix: small body strips + overlay VFX, never more frames. (https://www.zeldix.net/t1877-link-s-sword-animation-technical-data, https://jasontomlee.itch.io/slashfx, https://github.com/Retro-Diffusion/api-examples)
6. **One smear frame does the work of all missing in-betweens** — Slynyrd: "usually a single smear frame can get the job done"; elongate arm/weapon past anatomical reach at max extent; smears only on the strike frame, never in anticipation/recovery; angular smears read stronger than curves; ~2px minimum trail width to survive 32–64px. (https://www.slynyrd.com/blog/2018/9/8/pixelblog-9-melee-attacks, https://www.sprite-ai.art/guides/how-to-animate-pixel-art)
7. **Left/right keypoint labels are subject-anatomical (COCO convention); horizontal mirroring requires swapping every L/R label pair, not just negating x.** This is the systematic form of our front-arm/back-arm root cause (b); standard tooling encodes it as `flip_pairs`. Also: direction/view passed to `/animate-with-skeleton` must equal the anchor's stored facing — a mismatched skeleton silently degrades pose adherence instead of erroring. (https://docs.ultralytics.com/datasets/pose/coco/, https://www.pixellab.ai/docs/tools/animate-with-skeleton)
8. **The 18-keypoint schema has no weapon joint — wrist travel IS the weapon-arc control**, and PixelLab's own docs say to move the character to the side of the canvas so the model has room to draw effects on the strike side. Weapon rendering per frame is a QA-checkable output, not an input. (https://api.pixellab.ai/v1/openapi.json, https://www.pixellab.ai/docs/tools/skeleton-animation)
9. **"Minimal variation" is a documented failure mode of pose-conditioned sprite diffusion** (regression toward the reference image) — so the inter-frame-motion gate is a correct permanent control, not a temporary patch, and estimate-skeleton output on stylized sprites needs a sanity check before reuse. (https://arxiv.org/html/2412.03685v1)
10. **The correct machine test is silhouette change, not raw pixel change** — Cooper: staging = the idea "completely and unmistakably clear" via silhouette; speed = distance/time, so the windup→strike gap must be the LARGEST inter-frame delta in the strip. A recolored same-silhouette frame passes pixel-diff yet fails readability; the front/back-arm bug is exactly the class silhouette-delta catches. Anticipation poses must also move the whole body (torso counter-twist, weight shift), because at 32–48px the arm alone is 2px wide — silhouette delta is what survives small sizes. (https://www.gameanim.com/2019/05/15/the-12-principles-of-animation-in-video-games/, http://www.petesqbsite.com/sections/tutorials/tuts/tsugumo/chapter11.htm)
11. **Impact is a mandatory three-channel code stack, with shipped numbers**: empirical study of Steam action games found hit-stop, sound coherence, and camera response each individually make-or-break perceived impact; Capcom shipped 67–183ms per-entity hitstop with the victim frozen ~2 frames longer than the attacker; Smash scales hitlag by damage with a cap and jitters the victim during the freeze. At 10–15fps that envelope is 1–2 whole strip frames of free perceived attack time. (https://arxiv.org/abs/2208.06155, https://shane-sicienski.com/blog/blog-post-title-one-55pmn, https://www.ssbwiki.com/Hitlag)
12. **Weight without lag: sell it in follow-through and return control early.** Cooper: too little anticipation = weightless, too much = unresponsive; resolve by spending frames AFTER contact and returning control mid-animation (Animator exit time < 1.0 / early CanAct event). Swink: input-to-visible-response must stay under ~100ms — the first strip frame must already differ visibly from idle, and lunge/SFX start on the input frame. (https://www.gameanim.com/2019/05/15/the-12-principles-of-animation-in-video-games/, https://lizengland.com/blog/review-game-feel-by-steve-swink/)

Supporting confirmations: 3–6 frames is a sufficient budget when keys are strong (Cartwright, GDC Skullgirls, https://gdcvault.com/play/1020575/Animation-Bootcamp-Fluid-and-Powerful); simplify detail on fast frames — legibility of movement beats detail parity (https://www.slynyrd.com/blog/2024/11/25/pixelblog-53-punches-and-kicks); repair strips by freeze+regen of single frames, and turn `fixed head` OFF for attacks since the head must lean into the strike (https://www.pixellab.ai/docs/tools/animate-with-skeleton); enemy windups must be silhouette-distinct across an enemy's different attacks (https://www.gamedeveloper.com/design/enemy-attacks-and-telegraphing).

---

## 2. The attack-animation recipe (pipeline doctrine)

### Frame structure (phase grammar, not evenly-spaced swing positions)

| Budget | Player (light) | Player (heavy) | Enemy |
|---|---|---|---|
| 3 frames | strike-smear / follow-through / recover (NO windup) | — (heavies need 4) | windup(held) / strike / recover |
| 4 frames | windup / strike-smear / follow-through / recover | load / strike-smear / follow-through(long) / recover | windup(held ≥300ms) / strike-smear / follow-through / recover |

### Unity keyframe timing (per-keyframe ms — never uniform fps for attacks)

| Weapon class | 4-frame timing (ms) | Total |
|---|---|---|
| sword / light | 100 / 60 / 170 / 70 | 400 |
| spear / medium | 200 / 60 / 220 / 70 | 550 |
| hammer / heavy | 300 / 60 / 330 / 110 | 800 |

Rules: strike-smear frame stays 50–70ms for EVERY weapon (weight = hold durations only); the follow-through gets the longest post-contact hold; player windup ≤100ms, enemy windup ≥300ms (held as one long keyframe, no extra generated frames); Animator exit time < 1.0 (or a `CanAct` event at the follow-through start) so input returns before the settle finishes. Retiming = editing keyframe times, never a PixelLab regeneration.

### Pose-delta magnitudes (normalized keypoint units; px at 64px canvas)

- **Striking wrist (weapon-arc control — there is no weapon keypoint):** windup→strike travel ≥0.25 normalized (≥16px), typically 90–180° rotation about the shoulder; strike-frame wrist at ~0.95–1.0 forward extent, elbow ~0.85 — deliberately PAST anatomical reach (exaggeration is doctrine).
- **Whole-body, not arm-only:** NOSE/NECK lean +0.04–0.07 (3–4px) into the strike, both HIPs shift 0.02–0.03 (1–2px), shoulders counter-rotate vs hips; windup displaces the wrist OPPOSITE the strike direction (a mild strike pose is not anticipation — that is the shipped bug).
- **Canvas offset for effects:** shift all keypoints ~20–25% toward the trailing edge so the strike-direction half of the canvas is empty (PixelLab's own docs) — the model can then draw effect pixels; compensate in the import pivot.
- **Front-limb rule:** L/R labels are the CHARACTER's sides. Facing east, the front limb has the larger rest-pose x — verify before authoring. Mirroring a pose = negate x AND swap every LEFT/RIGHT label pair (`flip_pairs`). Direction/view passed to the API must equal the anchor's stored facing (pre-flight assertion vs asset-contract).
- **`fixed head`:** OFF (or "sometimes") for attack strips; ON for idle/walk.

### Gate upgrades (keep 0.35; add three checks)

1. **Silhouette delta**: alpha-mask XOR percentage between frames, not just pixel change (catches recolor-only "motion" and the back-arm bug).
2. **Monotonicity**: the max inter-frame delta must land on the windup→strike pair.
3. **Keypoint pre-flight** (free, before spending credits): striking wrist displacement ≥0.25 normalized between windup and strike, or refuse to call the API.
Tolerate/expect detail loss on the smear frame — detail parity with the anchor is not the goal on 50ms frames.

### Slash-VFX overlay (when + how)

**Every weapon/contact attack gets one** — the overlay carries the read; the body strip supports it. Generate as a standalone PixelLab `pixflux` asset (role `vfx`, free-sized, transparent): "curved crescent slash trail, angular motion smear, motion effect only, no character", `--outline lineless --shading "flat shading" --no-background`, arc stroke ≥2px at 64px, 1–3 frames or a single sprite. Runtime: child `AttackVFX` GameObject, own SpriteRenderer sorted above the body, **additive material** (alpha-blended gray smears vanish at 32px), spawned by the same strike-frame AnimationEvent that deals damage, code-animated 0.15s (scale 0.7→1.15, slight rotate, fade). One VFX strip is reusable across the cast per weapon family.

### Code-side juice stack (mandatory defaults, fired on the strike-frame event)

| Layer | Default | Notes |
|---|---|---|
| Hitstop | light 0.08s / heavy 0.15s; victim +0.03s; kill-shot 0.20s + zoom punch | per-entity (`animator.speed=0` + cached rb velocity on the two combatants), not global timescale; ~0 for rapid multihits/DoT |
| Victim jitter | ±1px pixel-grid steps during hitstop | on the visual child |
| Attacker lunge | 0.2s, 4–6px forward on visual child, starts on INPUT frame | existing fix, kept |
| Defender knockback | 2–4px in attack direction | |
| Defender squash | scale (1.2, 0.8), spring back 0.1s, EaseOutBack, unscaled time | composes with lunge (position) + flash (shader) |
| Hit flash | shader lerp to white 0.05–0.10s via MaterialPropertyBlock | `SpriteRenderer.color` is multiplicative — white does NOTHING |
| Screen shake | trauma scalar, amplitude = trauma², Perlin, max 2–4 texels, quantized to whole texels | |
| SFX | impact SFX on the same event | one of the three make-or-break channels |

**Acceptance gate:** an attack FAILS QA if it lacks (a) hitstop, (b) contact-frame SFX, (c) any camera response — regardless of strip quality.

---

## 3. Exact skill-file updates

### A. `/Users/xtdev/Desktop/unity-game-skills/skills/unity-animation/SKILL.md`

**A1 — Replace step 6 of "Sheet procedure"** ("Build Animation Clips (one per state), set frame rate (10–14 fps reads well for casual)…") with:

```markdown
6. **Build Animation Clips** (one per state). Loop idle/walk at uniform 10–14 fps. **Attack/hit clips NEVER use uniform spacing** — author per-keyframe times (weight lives in holds, strike frames stay 50–70ms for every weapon): sword 100/60/170/70ms, spear 200/60/220/70, hammer 300/60/330/110 (windup/strike-smear/follow-through/recover). Player windup ≤100ms (anticipation on player input reads as lag); enemy windup held ≥300ms (the tell). "Feels too slow/fast" is ALWAYS a keyframe-time edit here, never a PixelLab regeneration — poses are PixelLab's artifact, timing is Unity's.
```

**A2 — Add after the "Animation Events" section:**

```markdown
## Attack timing doctrine (player vs enemy are OPPOSITES)

- **Player attacks: near-zero anticipation.** The strike must visually fill the hitbox area by
  frame 1–2 (saint11); at 3 frames the phase list is strike-smear/follow-through/recover — no
  windup frame at all. Weight is sold AFTER contact: the follow-through gets the longest hold,
  and the Animator returns control early (exit time < 1.0 or a `CanAct` event at follow-through
  start) so the settle plays while input is already accepted. Input-to-visible-motion must stay
  under ~100ms: start the code-side lunge/SFX on the input frame, attack transitions get
  duration 0 + Has Exit Time off.
- **Enemy attacks: the windup IS the gameplay.** Hold the windup pose ≥0.3s (one windup sprite
  with a 300ms+ keyframe is cheaper than generating frames); the active strike phase is
  near-instant. Enemies with multiple attacks need silhouette-DISTINCT windups per attack
  (different direction/height), checkable with the same silhouette-diff machinery as the
  intra-clip motion gate.
- **Heavy vs light = hold durations, not more frames.** Strike frames stay 50–70ms regardless
  of weapon; only windup/follow-through holds grow (sword 400ms total, spear 550, hammer 800).
```

**A3 — In "Animation quality bar / scorecard", replace the "Anticipation & follow-through" bullet with:**

```markdown
- **Anticipation & follow-through match the actor** — enemy attacks: held ≥0.3s windup tell;
  player attacks: ≤100ms windup (strike by frame 1–2) with weight sold in a held follow-through.
  A symmetric evenly-progressing swing fails for BOTH.
```

**A4 — In "Verification: playing ≠ visible", replace item 2's last sentence and extend:**

```markdown
2. **Visible-motion gate** (content correctness): action strips (attack/hit/death) must pass
   `compare_frames_to_anchor.py --action` (≥0.35 inter-frame pixel change; a real run cycle
   measures ~0.78, a too-subtle slash that shipped broken measured 0.27). Pixel change alone is
   gameable (AA shimmer passes, a recolored same-silhouette frame passes): also require the
   SILHOUETTE (alpha-mask) delta to move, and the largest inter-frame delta to land on the
   windup→strike pair — a strip whose biggest change is the recover frame is mis-authored.
   Selling a fast action also needs the code-side impact stack (lunge, hitstop, overlay VFX —
   see unity-gameplay-systems combat-impact defaults); frames alone at 3 frames/0.2s under-read.
```

**A5 — In the final "Weapon attacks are a COMPOSITE" paragraph, replace `(4 frames windup/strike/follow/recover @ ~14fps, FRONT-limb authored — see unity-pixel-art)` with:**

```markdown
(4 frames windup/strike/follow/recover with NON-uniform keyframe times — strike 50–70ms,
follow-through held longest, per-weapon totals sword 400/spear 550/hammer 800ms; FRONT-limb
authored — see unity-pixel-art)
```
and replace `~0.05s hitstop on contact + a small lunge on the attacker` with `the combat-impact stack from unity-gameplay-systems (hitstop 0.08–0.15s per-entity, lunge, defender knockback+squash, shader flash, trauma shake, contact SFX)`.

---

### B. `/Users/xtdev/Desktop/unity-game-skills/skills/unity-pixel-art/SKILL.md`

**B1 — In "Attack/action animation doctrine (field-verified 2026-07-01)", replace the "Animate the FRONT limb" bullet with:**

```markdown
- **Animate the FRONT limb — and mirror correctly.** Keypoint LEFT/RIGHT labels are the
  CHARACTER's anatomical sides (COCO convention), not the viewer's: facing east, the character's
  LEFT limbs are the camera-front/travel side (rest-pose x tells you — the front limb has the
  larger x when facing east). A slash authored on the back arm plays "correctly" and reads as
  NOTHING. Check rest-pose x before authoring. **Deriving a mirrored facing = negate x AND swap
  every LEFT/RIGHT label pair** (shoulder/elbow/arm, hip/knee/leg, eye/ear) — mirroring x alone
  silently attacks with the back arm. Pre-flight: the `--view`/`--direction` passed to
  animate-skeleton MUST equal the reference anchor's stored facing (asset-contract) — a
  mismatched skeleton degrades pose adherence without erroring.
```

**B2 — Replace the "Use ABSOLUTE strike poses" bullet with:**

```markdown
- **Use ABSOLUTE extreme poses, not small offsets — phase grammar, not evenly-spaced swing
  positions.** ±0.05 normalized offsets read as nothing at 32–64px. Frames are DISTINCT phases
  (Dead Cells: keys first, "never in-between"): 4-frame attack = windup (wrist pulled back
  OPPOSITE the strike, torso counter-twisted) → strike-smear → follow-through (forward-down) →
  recover; 3-frame player attack DROPS the windup (strike/follow/recover — player anticipation
  reads as input lag; enemies instead HOLD the windup ≥0.3s in clip timing). Magnitudes at a
  64px canvas: striking wrist travels ≥0.25 normalized (≥16px, ~90–180° about the shoulder)
  between windup and strike, ending PAST anatomical reach (~0.95–1.0 forward extent, elbow
  ~0.85 — elongation/exaggeration is doctrine); NOSE/NECK lean +0.04–0.07; both HIPs shift
  0.02–0.03; front knee lunges. The whole SILHOUETTE must change — at this size the arm alone
  is 2px wide. On the strike frame prompt for the smear ("angular motion smear on the weapon
  arc") and accept detail loss — legibility of movement beats detail parity. Offset all
  keypoints ~20–25% toward the trailing canvas edge so the strike side has empty space for the
  model to draw effect pixels (PixelLab's own attack guidance); compensate at the import pivot.
  Set fixed-head OFF for attack strips (the head must lean); ON for idle/walk. Wrist travel IS
  the weapon-arc control — the 18-keypoint schema has no weapon joint.
```

**B3 — Append one bullet to the same doctrine list:**

```markdown
- **Poses vs timing are separate artifacts.** PixelLab owns POSES; Unity clip keyframe times own
  TIMING (attack clips are non-uniform — strike 50–70ms, holds carry the weight; table in
  unity-animation). Never regenerate a strip because it "feels slow/fast" — that is a free
  keyframe edit. Near-identical frames from a correct-looking pose set is a KNOWN
  pose-conditioned-diffusion failure mode (regression to the reference), which is why the
  motion gate is permanent; pre-flight the keypoints (wrist delta ≥0.25 normalized) before
  spending credits, and repair failing frames with `--init-images` freeze, not rerolls.
```

**B4 — In "QA gates", extend the `--action` sentence (after "a real run cycle 0.78)."):**

```markdown
Two additional required checks for attack strips: the LARGEST inter-frame delta must land on
the windup→strike pair (a strip peaking on the recover frame is mis-authored), and the
silhouette (alpha-mask) must change between frames — raw pixel change passes recolor/AA
shimmer that reads as nothing.
```

---

### C. `/Users/xtdev/Desktop/unity-game-skills/skills/unity-pixel-art/references/pixellab-api.md`

**C1 — In "Consistent animated character — the skeleton workflow", append to step 3 (after "a walk = legs/arms swinging across ~4–8 frames)."):**

```markdown
   **Attacks:** labels are the SUBJECT's anatomical sides — author the strike on the FRONT
   (facing-direction) limb (facing east: larger rest x); mirroring a pose set = negate x AND
   swap all LEFT/RIGHT label pairs. Author phases (windup/strike-smear/follow-through/recover),
   with wrist travel ≥0.25 normalized between windup and strike and whole-body deltas
   (nose/neck lean 0.04–0.07, hips 0.02–0.03). There is no weapon keypoint — the wrist path is
   the weapon-arc control; shift all keypoints ~20–25% toward the trailing edge so the model
   has empty canvas on the strike side for effect pixels (per PixelLab's skeleton-animation
   docs). Assert `--view`/`--direction` equals the reference anchor's stored facing before
   calling. Sanity-check estimate-skeleton output on stylized/armored sprites (limb-length
   symmetry, L/R ordering) before reusing it as a template.
```

**C2 — Append to step 4 (after the code block):**

```markdown
   For attack strips, do not rely on the generated frames to carry the slash — the model
   animates the body; the slash arc ships as a separate `pixflux` VFX overlay sprite (SKILL.md
   attack doctrine). Keep `fixed head` OFF for attacks.
```

---

### D. `/Users/xtdev/Desktop/unity-game-skills/skills/unity-gameplay-systems/SKILL.md`

**D1 — In "Game feel / juice (casual)", replace the bullet** `- **Squash & stretch** on land/hit; **screen shake** on impact (offset the camera, decay back); **hit-stop** (brief `Time.timeScale` dip on big hits).` **with:**

```markdown
- **Squash & stretch** on land/hit; **screen shake** on impact; **hit-stop** on hits — defaults
  and the mandatory combat stack below.
- **Combat impact stack (MANDATORY for every attack — shipped-game defaults).** Empirically,
  hit-stop + contact SFX + camera response are each individually make-or-break for perceived
  impact; an attack missing any of the three fails QA regardless of how good the animation strip
  is. All fired from the strike-frame Animation Event (damage event), all on the VISUAL child /
  unscaled time so they compose:
  - **Hit-stop:** light 0.08s, heavy 0.15s, kill-shot 0.20s + a slight camera zoom punch;
    victim frozen +0.03s longer than attacker; ~0 for rapid multihits/DoT ticks. Prefer
    **per-entity** stop (`animator.speed = 0` + cache/zero rigidbody velocity on the two
    combatants only) over a global `Time.timeScale` dip so multi-enemy scenes don't stutter.
    During the freeze, jitter the victim's visual child ±1px in pixel-grid steps.
  - **Attacker lunge:** 0.2s, 4–6 world-pixels forward on the visual child, starting on the
    INPUT frame (input-to-visible must stay <100ms). **Defender knockback:** 2–4px in the
    attack direction. **Defender squash:** scale (1.2, 0.8) springing back over ~0.1s
    (EaseOutBack, unscaledDeltaTime) — composes with lunge (localPosition) and flash (shader).
  - **Hit flash:** shader-level `lerp(c.rgb, _FlashColor, _FlashAmount)` driven via
    MaterialPropertyBlock, 0.05–0.10s. `SpriteRenderer.color` is a multiplicative tint — setting
    it white does NOTHING; renderer.color "flash" is the invisible-feedback bug in another channel.
  - **Screen shake:** a trauma scalar in [0,1] accumulating per hit, decaying linearly;
    amplitude = trauma² driven by Perlin noise. Pixel-art caveat: quantize offsets to whole
    texels (or shake before the pixel-perfect snap) and cap at 2–4 world-pixels or it aliases
    into shimmer.
  - **Slash/impact VFX overlay + SFX** on the same event (overlay generation/wiring:
    unity-pixel-art + unity-animation).
```

---

**Files referenced:**
- /Users/xtdev/Desktop/unity-game-skills/skills/unity-animation/SKILL.md
- /Users/xtdev/Desktop/unity-game-skills/skills/unity-pixel-art/SKILL.md
- /Users/xtdev/Desktop/unity-game-skills/skills/unity-pixel-art/references/pixellab-api.md
- /Users/xtdev/Desktop/unity-game-skills/skills/unity-gameplay-systems/SKILL.md