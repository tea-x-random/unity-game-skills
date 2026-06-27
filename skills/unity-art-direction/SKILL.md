---
name: unity-art-direction
description: "Establish and enforce a single, locked art-direction SYSTEM for a Unity casual/midcore iOS game so you ship an art-directed GAME, not a folder of individually-pretty AI assets. Use to choose a named style preset, write and approve a machine-readable art-spec.yaml single-source-of-truth (style_id, camera, shape language, palette, materials, lighting, rendering, scale, mobile art budgets, acceptance gates), write per-asset AssetBriefs, run the disciplined production pipeline (Gemini concept → approved turnaround/multi-view → Tripo 3D → mesh cleanup/ingest → Unity prefab with shared stylized shader → ArtValidationScene screenshots → 0–2 quality-gate scoring), and generate by FAMILIES (golden asset first, then 80/20 variants) rather than object-by-object. Triggers on: art direction, art spec, art-spec.yaml, style preset, style_id, art bible as code, mobile art budget, triangle/texture budget, asset family, golden asset, variant strategy, mesh cleanup, art validation scene, shared shader, quality gate, choose a visual style, what style should this game be. Owns the structured spec + style-preset library (references/style-presets.md) + spec/budget templates (references/art-spec-template.yaml). Pairs with unity-asset-designer (reference/turnaround sheets), unity-aaa-graphics (per-surface sourcing, AAA prompt library, visual scorecard), unity-image-generator + unity-3d-generator (generation), and unity-graphics (URP render lock)."
---

# Unity art direction

Produce an **art-directed game**, not a folder of individually attractive AI assets. Every generated asset is a member of **one visual language**, defined once in `art-spec.yaml` and obeyed by every image, mesh, material, VFX, UI element, and screenshot.

> **AAA quality means** a coherent hierarchy, strong silhouettes, controlled materials, polished lighting, readable gameplay, and deliberate composition. It does **NOT** mean ultra-dense meshes, photoreal textures, or expensive post. A solo iOS team hits "premium" through *coherence and discipline*, not scope.

This skill is the **system**: the locked spec, the style-preset catalog, the mobile budgets, and the production discipline. It complements the other art skills:
- **`unity-art-direction`** (here) — the `art-spec.yaml` SSOT, style presets, budgets, the golden-asset/family pipeline, quality gates.
- **`unity-asset-designer`** — the on-model reference/turnaround/icon sheets craft that this pipeline's "approved multi-view" step calls for.
- **`unity-aaa-graphics`** — per-surface "generate everything" sourcing, the AAA prompt library/genre kits, and the visual scorecard that fails amateur scenes.
- **`unity-graphics`** — the URP render lock (lighting/material/post) that produces the final on-device look.

## Non-negotiable rules

1. **Never generate a production asset without an approved `art-spec.yaml` and a chosen `style_id`.**
2. **References are broad direction, never clones.** Never request a direct copy of a specific living artist, game, character, or proprietary asset — translate intent into the project's own shape/palette/material/lighting rules.
3. **Keep style ≠ genre ≠ camera distinct.** (Style: painterly cel fantasy. Genre: cozy puzzle. Camera: orthographic 3/4.)
4. **One asset, one primary material language.** Don't mix glossy realism, flat toon, hand-painted gradient, and noisy PBR arbitrarily.
5. **The Unity screenshot is the acceptance test.** A gorgeous source image that fails in the real camera, lighting, or device budget is **rejected** — capture it in `ArtValidationScene` and score it.
6. **Use 3D only where it earns its cost.** On iOS, prefer 2D cards/decals/billboards/baked backgrounds unless parallax, animation, interactivity, silhouette, or depth materially improves the game.

## The art spec — single source of truth

Before the first production asset, write and approve `Assets/GameArt/_ArtDirection/art-spec.yaml`. It captures `style_id`, `camera`, `shape_language`, `palette` (dominant/neutrals/accent + max high-chroma accents per asset), `materials`, `lighting`, `rendering` (shared shader family + post), `scale` (metric), `mobile_budget` (triangle/texture/material caps per tier + target fps), and `acceptance` gates. **Make intentional choices, then lock them** — don't leave values generic. Full template + an `AssetBrief` template + recommended mobile budgets: `references/art-spec-template.yaml`.

## Choose a style preset

Pick **exactly one** primary `style_id` (optionally one named secondary influence) from the 12-preset library in `references/style-presets.md`, which lists each preset's reference language, best camera, visual grammar, good-fit genres, and per-style generation do/don'ts. For a typical casual iOS project, start with one of:
- **`cozy_toy_diorama`** — puzzles, idle, social, broadly-appealing (rounded forms, matte materials, soft bevels).
- **`heroic_handpainted_fantasy`** — an approachable "premium game" feel with strong collectible/UI potential.
- **`clean_graphic_casual`** — premium mobile puzzle/word/match (near-flat materials, 2–4 dominant colors, maximum readability).

Avoid `cinematic_pbr_realism` on a solo iOS team unless the game is intentionally sparse — it carries the highest asset, lighting, texture-memory, and animation burden.

## Production pipeline (per asset)

1. **AssetBrief** — write the per-asset spec (type, gameplay role, importance/rarity, scale_m, required views, material slots, animation, collision, texture budget, negative constraints). Template in `references/art-spec-template.yaml`.
2. **Gemini concept** — generate a beauty concept for *reference control*, not as the final asset: isolated object, neutral background, 3/4 view, clear material separation, gameplay-readable silhouette, no environment/characters/text. (Use `unity-image-generator`; AAA prompt structure in `unity-aaa-graphics/references/prompt-library.md`.)
3. **Approved turnaround / multi-view** — produce a 5-panel (front/left/back/right/top) sheet that preserves silhouette, proportions, colors, and material blocks exactly. This is the preferred input for 3D. (Owned by `unity-asset-designer`.) **Do not make variants until the base is approved in Unity** — reference drift multiplies fast.
4. **Tripo 3D** — generate from the approved multi-view (text-to-3D only for fast exploration): one watertight object, clean silhouette, no floaters, simple readable forms, single UV set, within the tier's triangle/material budget, pivot at base center, Y-up, scaled to metric. (Use `unity-3d-generator`.)
5. **Mesh cleanup & Unity ingest** — AI geometry is never auto-production-ready (see checklist below).
6. **Prefab with shared shader** — make a named prefab using the project's shared stylized material, in the standard directory.
7. **ArtValidationScene** — render the prefab in all five standard framings (gameplay camera, neutral studio, bright outdoor, dim indoor, thumbnail/reward-card).
8. **Quality gate** — score 0–2 per dimension; needs ≥10/12 and no zeros. Only then add to a gameplay scene.

### Mesh cleanup & ingest checklist
Mesh integrity (remove floaters, non-manifold, interior faces) · silhouette preserved from the game camera · metric scale + correct pivot · topology reduced where unseen + LODs as needed · materials reduced to the project shader grammar (don't keep random generated PBR maps) · textures compressed/sized to `mobile_budget` · primitive/simplified colliders (never a raw high-poly collision mesh) · named prefab in the standard directory.

## Generate by families, not object-by-object

Approve one **golden asset** per family first, then derive variants by preserving ~80% of the golden asset's language and changing only ~20% (silhouette category, accent color, attachment, damage state, size tier). Recommended order: camera+lighting test scene → one focal object → three core props → one modular environment kit → one interactable/reward asset → UI icon/card family → VFX family → controlled variants.

## Unity visual lock

The scene — not the model — creates the final feel. Maintain **one** global visual kit: one URP renderer config, one lighting rig per biome/time-of-day, one exposure/tonemapping policy, one shared material/shader family, one camera framing rule per mode, one small VFX library (sparkle/dust/hit/reward/ambience). Expose only project-approved controls on the shared stylized shader (base color, top/bottom gradient, ramp strength, rim strength/color, AO strength, emissive color/intensity) so no asset introduces a bespoke look — a small material vocabulary is what makes a generated world look *authored*. (Render mechanics: `unity-graphics`.)

## Quality gates

Score each 0–2; a production asset needs **≥10/12 and no zeros**: **silhouette** (clear at gameplay scale) · **style compliance** (clearly belongs to this game) · **camera composition** (designed for the actual camera) · **material language** (matches the shared shader grammar) · **mobile budget** (inside caps) · **technical usability** (clean prefab/collider/LOD).

Reject immediately: near-duplicate assets that make a set feel copy-pasted · detail only visible in the source image, not in gameplay · texture noise that flickers at mobile res · mismatched outline weights · random neon emissives as decoration · high-poly collision meshes · a bespoke "special" lighting setup for a single asset.

## Agent workflow

When asked to create/modify a visual asset: (1) read `art-spec.yaml` + existing golden assets; (2) identify the family + closest approved analog; (3) write the AssetBrief; (4) Gemini concept from style anchors; (5) approved turnaround/multi-view; (6) Tripo from the multi-view; (7) cleanup + import as a prefab with the shared shader; (8) render in `ArtValidationScene`; (9) score the quality gates; (10) only then place it in gameplay. **Never silently change the project style** — if a request conflicts with `art-spec.yaml`, surface the conflict and propose either a constrained variation or an explicit spec revision.

## Field notes & lessons

- A locked `art-spec.yaml` is the single highest-leverage artifact — it turns "make nice art" into a testable contract, and is what stops the one-hero-asset-amid-flat-everything-else look.
- Generate **families** with a golden asset + 80/20 variants; object-by-object generation drifts and feels copy-pasted.
- AI meshes always need cleanup (floaters, scale, pivot, collider, material reduction) — budget for it; raw Tripo output is an input, not a prefab.
- A small shared shader vocabulary + one lighting rig makes a generated world look authored; bespoke per-asset shaders/lighting are the fastest way to look incoherent.
- The in-engine screenshot, scored against the gate, is the only acceptance test that matters — beauty renders lie about camera, lighting, and device budget.
