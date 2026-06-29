---
name: unity-asset-pipeline
description: "Turn generated source art (Gemini images, Tripo meshes) into APPROVED, runtime-ready Unity asset packages with a machine-readable contract, enforced import settings, a generated prefab, validation gates, and an approved-asset registry. Use whenever assets must move from 'a file was generated' to 'an approved prefab that belongs in THIS game': per-asset asset-contract.yaml (id, family, role, style_id, source, runtime prefab/pivot/PPU/collider/material, camera_contract, qa flags), the asset manifest + validation gate (alpha/scale/palette/import/screenshot), the prefab factory (apply contract -> import settings -> prefab), the BeautyCell visual-regression gate, and the approved-asset registry that scene-building agents must use instead of dragging raw generated files into gameplay scenes. Triggers on: asset contract, asset manifest, runtime asset package, import validator, import contract, prefab factory, apply asset contract, generate prefab from contract, asset registry, approved asset, beauty cell, visual regression, golden screen, sprite bake, pre-render to atlas, 'why do my assets fall apart when assembled', game-ready import. Pairs with unity-art-direction (art-spec.yaml SSOT + families), unity-image-generator (2D source + sprite QA), unity-3d-generator (3D source + pre-render), unity-scene-composition (placement contract), and unity-graphics (URP render lock)."
---

# Unity asset pipeline

Generators produce **source art**. This skill produces **approved runtime asset packages**. The boundary between the two is the single most important thing to enforce: an image or mesh existing on disk is NOT an asset that belongs in the game. An asset belongs in the game only when it has a contract, passes validation, ships as a prefab, and is entered into the registry.

> **The hard rule.** Scene-building agents may only instantiate prefabs listed in the **approved-asset registry**. They must NEVER drag a freshly generated file directly into a gameplay scene. Generators feed `Assets/Art/Source/`; only this pipeline writes to `Assets/Art/Approved/` and the registry.

This skill is downstream of `unity-art-direction` (which owns the locked `art-spec.yaml`, style presets, mobile budgets, and the family strategy) and upstream of `unity-scene-composition` (which owns placement). It turns the art-direction *process* into *enforceable data*.

## The pipeline (each asset)

```
art contract (art-spec.yaml + AssetBrief, owned by unity-art-direction)
  → family reference pack          (golden asset first; see "Families" below)
  → source generation              (Gemini image / Tripo mesh)
  → cleanup / alpha / mesh normalize (sprite QA or mesh-cleanup checklist)
  → asset-contract.yaml            (the machine-readable runtime contract)
  → Unity import validation        (ApplyAssetContract + import validator)
  → runtime prefab                 (GeneratePrefabFromContract)
  → BeautyCell screenshot test     (visual-regression gate)
  → approved-asset registry        (the ONLY source scene-builders may use)
```

Never skip forward. A "good-looking" source image with no contract, no import validation, and no screenshot is **not** an approved asset and must not enter a scene.

## The asset contract (machine-readable, per asset)

Every approved asset ships with `Assets/Art/Approved/<id>/asset-contract.yaml`. This is what stops each agent from improvising scale, pivot, material, silhouette size, and camera assumptions. Full annotated template: `references/asset-contract-template.yaml`. Minimum shape:

```yaml
id: meadow_tree_a
family: meadow_vegetation
role: midground_obstacle
style_id: cozy_toy_diorama_v1        # MUST match art-spec.yaml style_id
source:
  generator: tripo                   # tripo | gemini | authored
  prompt_hash: "sha256:..."
  reference_pack: meadow_family_v1
runtime:
  prefab: Prefabs/Environment/MeadowTreeA
  pivot: bottom_center
  pixels_per_unit: 100               # 2D
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

Run before importing. It checks the contract is well-formed, that `style_id` matches the project `art-spec.yaml`, that the `camera_contract` agrees with the scene composition profile, and (for 2D) ingests both the pixel QA report from `unity-image-generator/scripts/validate_sprite.py` and the vision critique report from `unity-image-generator/scripts/critique_image.py` so alpha/halo/palette/finish failures AND wrong-subject/role-fit failures block approval:

```bash
python3 ~/.claude/skills/unity-asset-pipeline/scripts/validate_asset_manifest.py \
  Assets/Art/Approved/meadow_tree_a/asset-contract.yaml \
  --art-spec Assets/GameArt/_ArtDirection/art-spec.yaml \
  --sprite-qa Assets/Art/QA/meadow_tree_a.sprite-qa.json \
  --image-critique Assets/Art/QA/meadow_tree_a.critique.json \
  --composition Assets/GameArt/_ArtDirection/composition.yaml
```

Exit code 0 = contract valid and all referenced QA passed; non-zero = rejected (do not import).

## Apply the contract in Unity + build the prefab

Run inside Unity via `unity-mcp-bridge` `execute_code` or promoted Editor scripts. Key steps live in `references/editor-asset-pipeline.md`:
1. **ApplyAssetContract** — set TextureImporter/ModelImporter to the contract's PPU, pivot, sprite mode, filter, mipmaps, max size, ASTC, material profile, and optional secondary textures, then validate the realized import matches the contract (the **import validator** — pivot, PPU, sprite mesh mode, compression, max texture size, mipmaps, material/shader assignment).
2. **GeneratePrefabFromContract** — instantiate, attach the contract's collider + shared material + shadow profile, set pivot, save the prefab to `runtime.prefab`, and stamp the contract path on a small `AssetContractTag` component.
3. **Atlas/Addressables gates** — if the asset is a sprite, put it in its contract's `sprite_atlas`/`atlas_group`; if the project uses Addressables, assign the contract address/group/labels.
4. **Import automation** — for real projects, use Unity Import Presets + `AssetPostprocessor` so correct settings are defaults, not manual reminders; validation still verifies the result.

The import validator is a **gate**, not a reminder: if the realized import settings do not match the contract, fail and do not produce a prefab.

## BeautyCell — the screenshot gate (required before approval)

"Verify visually in Unity" becomes an automated gate with a recorded screenshot. Render the prefab in the standard validation scenes and compare against an approved reference frame. C# in `references/editor-asset-pipeline.md` (`RenderBeautyCell`, `CompareReferenceFrames`); scene list and acceptance in `references/beauty-cell.md`. An asset is approved only when it passes in:

- `ArtValidationScene` (gameplay camera + four standard framings)
- `BeautyCell_01` (the polished hero screen — see "Beauty cell first" below)
- `CameraScaleTest`, `LightingTest`, `MaterialTest`, `MobileDeviceTest`

A candidate fails automatically if it cannot pass all of these. The screenshot is stored next to the contract as evidence.

## The approved-asset registry

The registry (`Assets/Art/Approved/registry.yaml`) is the **only** index scene-building agents read. Schema and the "no raw files in scenes" rule: `references/registry-schema.md`. Each entry references a contract + prefab + passing QA/screenshot. `validate_asset_manifest.py --registry` re-validates every entry. If an asset is not in the registry, it does not exist for level assembly.

## Beauty cell first — build one screen before a level

Before generating dozens of assets, require ONE polished, screen-sized test scene (`BeautyCell_01`) containing: one hero/gameplay object, two supporting prop families, one environment kit, one lighting profile, one UI card, one effect layer, captured at one target-device resolution. **Nothing else expands until this scene is approved.** This catches the real failures early: assets too similarly sized, no contrast between interactable and decoration, over-detailed background, props with incompatible camera angles, mismatched shadow direction, UI unrelated to the world. Details: `references/beauty-cell.md`.

## Families, not one-off objects (bounded variation)

`unity-art-direction` owns family strategy; this skill enforces it as data. Each family has: a canonical silhouette, 3 approved variants, 2 approved palette variants, 1 approved damaged/alternate state, a shared `material_profile`, a shared scale range, and shared pivot rules — all recorded in the family's contracts. Generate a **family sheet** first, approve the canonical member, then derive variants from that locked source. Do not ask the model for "another tree / rock / cow" in isolation — that produces a visual flea market.

## Generators are source-art suppliers, not final-asset suppliers

Use **Gemini** (`unity-image-generator`) primarily for: concept boards, background paintings, decals, UI illustrations/icons, texture/source references, and whole-pack family sheets with shared visual DNA. Avoid using it as the default source for independent gameplay-facing foreground props.

Use **Tripo** (`unity-3d-generator`) or deliberately simple authored geometry for: characters, props that cast shadows, interactables, scenery needing consistent perspective, and anything near the player camera. For a 2D look, render those 3D assets through ONE shared Unity lighting/material pipeline into sprite atlases (**sprite bake** / pre-render — see `unity-3d-generator` pre-render pipeline and `references/sprite-bake.md`). This is what gives consistent light, perspective, and shadow direction across a 2D scene.

## What this skill does NOT do

- It does not pick the style or write `art-spec.yaml` → `unity-art-direction`.
- It does not generate source art → `unity-image-generator` / `unity-3d-generator`.
- It does not lay out scenes / decide focal points & density → `unity-scene-composition`.
- It does not own the final URP render lock → `unity-graphics`.

It owns the contract, the validators, the prefab factory, atlas/addressables metadata, the beauty-cell gate, and the registry — the bridge from "AI-generated assets in Unity" to "a coherent game art pipeline".

## Keep this skill current

When the user asks to benchmark or improve the skills from popular Unity/game-art workflows, use `docs/EXTERNAL_BENCHMARK_WORKFLOW.md`. Promote only high-signal findings into contract fields, validators, Editor snippets, or skill rules. Current benchmark-derived gates here include SpriteAtlas groups, Import Presets/AssetPostprocessor, Addressables labels, and optional 2D secondary textures.
