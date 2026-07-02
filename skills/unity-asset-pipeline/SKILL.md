---
name: unity-asset-pipeline
description: "Turn generated source art (Gemini images, PixelLab pixel sprites, Tripo meshes) into APPROVED, runtime-ready Unity asset packages with a machine-readable contract, enforced import settings, a generated prefab, validation gates, and an approved-asset registry. Use whenever assets must move from 'a file was generated' to 'an approved prefab that belongs in THIS game': per-asset asset-contract.yaml (id, family, role, style_id, source, runtime prefab/pivot/PPU/collider/material, camera_contract, qa flags), the asset manifest + validation gate (alpha/scale/palette/import/screenshot), the prefab factory (apply contract -> import settings -> prefab), the BeautyCell visual-regression gate, and the approved-asset registry that scene-building agents must use instead of dragging raw generated files into gameplay scenes. Triggers on: asset contract, asset manifest, runtime asset package, import validator, import contract, prefab factory, apply asset contract, generate prefab from contract, asset registry, approved asset, beauty cell, visual regression, golden screen, sprite bake, pre-render to atlas, 'why do my assets fall apart when assembled', game-ready import. Pairs with unity-art-direction (art-spec.yaml SSOT + families), unity-pixel-art (pixel-native final sprites/sheets), unity-image-generator (Gemini concept/static non-pixel source + sprite QA), unity-3d-generator (3D source + non-pixel pre-render), unity-scene-composition (placement contract), and unity-graphics (URP render lock)."
---

# Unity asset pipeline

Generators produce **source art**. This skill produces **approved runtime asset packages**. The boundary between the two is the single most important thing to enforce: an image or mesh existing on disk is NOT an asset that belongs in the game. An asset belongs in the game only when it has a contract, passes validation, ships as a prefab, and is entered into the registry.

> **The hard rule.** Scene-building agents may only instantiate prefabs listed in the **approved-asset registry**. They must NEVER drag a freshly generated file directly into a gameplay scene. Generators feed `Assets/<Game>/Art/Source/`; only this pipeline writes to `Assets/<Game>/Art/Approved/` and the registry.

This skill is downstream of `unity-art-direction` (which owns the locked `art-spec.yaml`, style presets, mobile budgets, and the family strategy) and upstream of `unity-scene-composition` (which owns placement). It turns the art-direction *process* into *enforceable data*.

## The pipeline (each asset)

```
art contract (art-spec.yaml + AssetBrief, owned by unity-art-direction)
  → family reference pack          (golden asset first; see "Families" below)
  → source generation              (PixelLab pixel sprite / Gemini image / Tripo mesh)
  → cleanup / alpha / mesh normalize (sprite QA or mesh-cleanup checklist)
  → asset-contract.yaml            (the machine-readable runtime contract)
  → Unity import validation        (ApplyAssetContract + import validator)
  → runtime prefab                 (GeneratePrefabFromContract)
  → BeautyCell screenshot test     (visual-regression gate)
  → approved-asset registry        (the ONLY source scene-builders may use)
```

Never skip forward. A "good-looking" source image with no contract, no import validation, and no screenshot is **not** an approved asset and must not enter a scene.

## The asset contract (machine-readable, per asset)

Every approved asset ships with `Assets/<Game>/Art/Approved/<id>/asset-contract.yaml`. This is what stops each agent from improvising scale, pivot, material, silhouette size, and camera assumptions. Full annotated template: `references/asset-contract-template.yaml`. Minimum shape:

```yaml
schema: unity-game-skills.asset-contract.v1   # REQUIRED — validator fails loudly without it
id: meadow_tree_a
family: meadow_vegetation
role: midground_obstacle
style_id: cozy_toy_diorama_v1        # MUST match art-spec.yaml style_id
art_spec: Assets/<Game>/Art/_ArtDirection/art-spec.yaml   # validator resolves the spec from here
source:
  generator: gemini                  # pixellab | tripo | gemini | authored | kitbash | vendor | elevenlabs
  source_art: Assets/<Game>/Art/Source/meadow_tree_a.png  # required to compute palette/scale checks
  prompt_hash: "sha256:..."
  reference_pack:                    # resolvable file paths (anchors, palette swatch, sheets)
    - Assets/<Game>/Art/_ArtDirection/palettes/master-palette.png
runtime:
  type: sprite                       # REQUIRED — sprite | model | ui | texture | vfx | audio; sprite checks key off this
  prefab: Assets/<Game>/Art/Prefabs/Environment/MeadowTreeA.prefab
  pivot: bottom_center
  pixels_per_unit: 100               # MUST equal art-spec craft.pixels_per_unit (project PPU SSOT)
  scale_meters: [1.2, 1.8, 1.2]      # world-space bounds target; drives computed scale_valid
  collider: capsule
  material_profile: World_Stylized_v1
  shadow_profile: soft_blob_v1
camera_contract:                     # must agree with scene-composition camera profile
  projection: orthographic
  yaw: 45
  pitch: 35
  target_screen_height_percent: 18
qa:
  alpha_valid: true
  scale_valid: true
  palette_valid: true
  scene_test_valid: true
```

`qa.*` flags are **set by the validators**, not hand-authored. An asset with any `qa.*` false (or missing) is not approved.

## Validate the contract + source: `validate_asset_manifest.py`

Run before importing. Coherence checks are **default-on and FAIL when their inputs are absent** — no silent skips:

- Resolves the art-spec from `--art-spec` or the contract's `art_spec:` path (registry mode: the registry's `art_spec:` key); unresolvable spec = FAIL. `--no-art-spec` is the ONLY escape hatch and is for exploratory/concept contracts, never approval.
- Resolves `composition.yaml` from `--composition` or as a sibling of the art-spec (registry mode: `composition_profile:`); checks `camera_contract` against it (`--no-composition` only when no profile exists yet).
- Checks `style_id` equality and, for sprites, `runtime.pixels_per_unit` == art-spec `craft.pixels_per_unit` (plus PPU **uniformity across the whole registry** in `--registry` mode — one game = one PPU).
- **Computes** `palette_valid` by running `unity-image-generator/scripts/validate_sprite.py` as a subprocess against the art-spec palette (exact per-pixel membership for `craft.finish: pixel`; average-distance heuristic otherwise). If the tool can't run, that is a FAIL, not a skip.
- **Computes** `scale_valid` for sprites from source PNG dims: world height (`height_px / PPU`) vs `runtime.scale_meters[1]`, plus canvas-is-a-tile-multiple for pixel finish. 3D `scale_valid` stays with the Editor import validator.
- Ingests the pixel QA report (`--sprite-qa`), vision critique report (`--image-critique`), and frame-vs-anchor diff report(s) (`--frame-diff`, or the contract's `qa.frame_diff_report`) so alpha/halo/finish, wrong-subject/role-fit, AND animation-identity failures block approval. A contract with a frame-based 2D `animation:` block (`runtime.type: sprite` or `animation.sheet` set) and no frame-diff report FAILS (sets `qa.frame_diff_valid`); 3D skeletal clips (`sheet: null`) pass this check as N/A — they are validated by unity-3d-generator's validate-animation instead.
- Checks `composition.yaml:shadow_and_contact.key_light_direction` == art-spec `craft.light_direction` (one global light direction; string inequality = failure).
- Checks the **GameTheme.cs derived view**: every color hex in the file at `derived_artifacts.game_theme_cs` (or `--game-theme`) must exist in the art-spec palette subtree (roles + arrays + ramps) — colors only, typography/spacing/radii are GameTheme-native.

```bash
python3 ~/.claude/skills/unity-asset-pipeline/scripts/validate_asset_manifest.py \
  Assets/<Game>/Art/Approved/meadow_tree_a/asset-contract.yaml \
  --sprite-qa Assets/<Game>/Art/Source/QA/meadow_tree_a.sprite-qa.json \
  --image-critique Assets/<Game>/Art/Source/QA/meadow_tree_a.critique.json
```

Exit code 0 = contract valid and all referenced QA passed; non-zero = rejected (do not import).

## Scene-walk registry resolution: `check_scene_registry.py`

The assembly-time bypass detector — the scripted half of `unity-game-director`'s Verification rule ("every placed asset resolves to a registry entry"). It parses `.unity` scene files directly (no Unity/PyYAML needed), collects every ART reference (prefab instances, sprites, meshes, materials by guid), and fails any that don't resolve to the approved registry (a registry prefab, or a file inside a registered asset's approved folder). An EMPTY registry (no entries yet) is the legal gray-box state — reported as `registry_empty`, not failed. Engine-builtin primitives never fail, and GameObject names containing `PLACEHOLDER` (configurable) are reported for visibility — but any FILE-based art reference must resolve to the registry regardless of object naming; never wire raw generated files into a scene, even as placeholders. The prototype-first doctrine stays intact: gray-box = flagged primitives.

```bash
python3 ~/.claude/skills/unity-asset-pipeline/scripts/check_scene_registry.py \
  Assets/Scenes/Gameplay.unity \
  --registry Assets/<Game>/Art/Approved/registry.yaml \
  --json-report Assets/<Game>/Art/QA/scene-registry.json
```

Exit 0 = every file-based scene art reference is registry-approved (engine builtins exempt); exit 2 = assembly-time bypass — fix before "done". (An MCP scene-walk cross-check remains valid for live/unsaved scenes; this script covers saved scenes deterministically.)

## Bounded re-roll policy (when a candidate fails QA)

Re-rolls are bounded, targeted, and route-scoped — never a blind loop:

- Auto-re-roll ONLY when the critique overall score is below **~2.25/3** (the quality ceiling); candidates above it gain nothing from re-rolls — fix the brief or accept.
- Each re-roll must target the **two worst-scoring axes** in the revised prompt; keep the **best-seen** candidate across iterations, never just the latest.
- Hard cap: **2 re-roll iterations**, then stop and escalate (revise the AssetBrief or get a human call).
- Scope: the **Gemini route only**. Pixel assets are never blanket re-rolled — repair the broken region with PixelLab `inpaint` ("fix, don't reroll", see `unity-pixel-art`).

## Apply the contract in Unity + build the prefab

Run inside Unity via `unity-mcp-bridge` `execute_code` or promoted Editor scripts. Key steps live in `references/editor-asset-pipeline.md`:
1. **ApplyAssetContract** — set TextureImporter/ModelImporter to the contract's PPU, pivot, sprite mode, filter, mipmaps, max size, ASTC, material profile, optional secondary textures, and sheet/atlas slicing data, then validate the realized import matches the contract (the **import validator** — pivot, PPU, sprite mesh mode, compression, max texture size, mipmaps, material/shader assignment).
2. **GeneratePrefabFromContract** — instantiate, attach the contract's collider + shared material + shadow profile, set pivot, save the prefab to `runtime.prefab`, and stamp the contract path on a small `AssetContractTag` component.
3. **Best-candidate provenance** — verify `best_candidate_report` points to the selected candidate and that rejected candidates did not enter the registry.
4. **Atlas/Addressables gates** — if the asset is a sprite, put it in its contract's `sprite_atlas`/`atlas_group`; if the project uses Addressables, assign the contract address/group/labels. For sheets, use `extruded_atlas_manifest` so slicing excludes duplicated edge pixels.
5. **Import automation** — for real projects, use Unity Import Presets + `AssetPostprocessor` so correct settings are defaults, not manual reminders; validation still verifies the result.

The import validator is a **gate**, not a reminder: if the realized import settings do not match the contract, fail and do not produce a prefab.

## BeautyCell — the screenshot gate (required before approval)

"Verify visually in Unity" becomes an automated gate with a recorded screenshot. Render the prefab in the standard validation scenes and compare against an approved reference frame. C# in `references/editor-asset-pipeline.md` (`RenderBeautyCell`, `CompareReferenceFrames`); scene list and acceptance in `references/beauty-cell.md`. An asset is approved only when it passes in:

- `ArtValidationScene` (gameplay camera + four standard framings)
- `BeautyCell_01` (the polished hero screen — see "Beauty cell first" below)
- `CameraScaleTest`, `LightingTest`, `MaterialTest`, `MobileDeviceTest`

A candidate fails automatically if it cannot pass all of these. The screenshot is stored next to the contract as evidence.

## The approved-asset registry

The registry (`Assets/<Game>/Art/Approved/registry.yaml`) is the **only** index scene-building agents read. Schema and the "no raw files in scenes" rule: `references/registry-schema.md`. Each entry references a contract + prefab + passing QA/screenshot. `validate_asset_manifest.py --registry` re-validates every entry. If an asset is not in the registry, it does not exist for level assembly.

Two shape requirements the validator enforces (not optional):

- **Every registry entry REQUIRES a `qa:` block** — an entry without one fails validation outright; `qa.*` flags come from the validators, never hand-authored (same rule as contracts).
- **The registry-level `composition_profile:` key is effectively REQUIRED** — coherence checks are default-on, and registry mode resolves `composition.yaml` from this key; omitting it fails the camera-contract coherence pass rather than skipping it.

Scene assembly must reference registry art only **through prefab instances** (plain-value instance overrides like tiled `drawMode`/`size` are fine); direct scene-object references to project-local `.mat`/`.png` fail `check_scene_registry.py` — details in `references/editor-asset-pipeline.md` §13.

## Beauty cell first — build one screen before a level

Before generating dozens of assets, require ONE polished, screen-sized test scene (`BeautyCell_01`) containing: one hero/gameplay object, two supporting prop families, one environment kit, one lighting profile, one UI card, one effect layer, captured at one target-device resolution. **Nothing else expands until this scene is approved.** This catches the real failures early: assets too similarly sized, no contrast between interactable and decoration, over-detailed background, props with incompatible camera angles, mismatched shadow direction, UI unrelated to the world. Details: `references/beauty-cell.md`.

## Families, not one-off objects (bounded variation)

`unity-art-direction` owns family strategy; this skill enforces it as data. Each family has: a canonical silhouette, 3 approved variants, 2 approved palette variants, 1 approved damaged/alternate state, a shared `material_profile`, a shared scale range, and shared pivot rules — all recorded in the family's contracts. Generate a **family sheet** first, approve the canonical member, then derive variants from that locked source. Do not ask the model for "another tree / rock / cow" in isolation — that produces a visual flea market.

## Generators are source-art suppliers, not final-asset suppliers

Use **PixelLab** (`unity-pixel-art`) for final **pixel-art** sprites, tilesets, icons, directional sheets, and animation strips. Gemini can explore silhouettes/style boards, but approved pixel assets must be generated at native canvas with anchor-first consistency and pixel import settings. Do not make pixel art by Tripo/3D downscale.

Use **Gemini** (`unity-image-generator`) primarily for: concept boards, background paintings, decals, UI illustrations/icons, texture/source references, non-pixel static art, and whole-pack family sheets with shared visual DNA. Avoid using it as the default source for independent gameplay-facing foreground props when a pixel or 3D route is more appropriate.

Use **Tripo** (`unity-3d-generator`) or deliberately simple authored geometry for: runtime 3D characters/props, non-pixel props that cast shadows, interactables, scenery needing consistent perspective, and anything near the player camera. For a non-pixel 2D look, render those 3D assets through ONE shared Unity lighting/material pipeline into sprite atlases (**sprite bake** / pre-render — see `unity-3d-generator` pre-render pipeline and `references/sprite-bake.md`).

**Animated assets go through the same gate.** Finished sprite sheets, clips, and Animator Controllers (`unity-animation`) ship via contract + registry like statics: record them in the contract's `animation:` block (clip list, controller path, designated `key_pose`), and BeautyCell scores the key pose (see `references/beauty-cell.md`).

**Audio clips are assets too.** ElevenLabs clips (`unity-audio-generator`) enter production via a per-clip contract with `runtime.type: audio` + the `runtime.audio:` section (load type, Vorbis quality, force-to-mono, loop flag, target LUFS) and a registry entry. A `loop: true` contract requires the seamless-loop crossfade post-process to have run — it is not an ElevenLabs feature.

## What this skill does NOT do

- It does not pick the style or write `art-spec.yaml` → `unity-art-direction`.
- It does not generate source art → `unity-pixel-art` / `unity-image-generator` / `unity-3d-generator`.
- It does not lay out scenes / decide focal points & density → `unity-scene-composition`.
- It does not own the final URP render lock → `unity-graphics`.

It owns the contract, the validators, the prefab factory, atlas/addressables metadata, the beauty-cell gate, and the registry — the bridge from "AI-generated assets in Unity" to "a coherent game art pipeline".

## Keep this skill current

When the user asks to benchmark or improve the skills from popular Unity/game-art workflows, use `docs/EXTERNAL_BENCHMARK_WORKFLOW.md`. Promote only high-signal findings into contract fields, validators, Editor snippets, or skill rules. Current benchmark-derived gates here include SpriteAtlas groups, Import Presets/AssetPostprocessor, Addressables labels, and optional 2D secondary textures.
