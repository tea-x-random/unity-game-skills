# Pipeline Conventions (SSOT reference — obey verbatim)

Canonical names, paths, and rules for all unity-* skills. When a SKILL.md and this doc disagree, this doc wins until the SKILL.md is updated. Source schemas: `skills/unity-art-direction/references/art-spec-template.yaml`, `skills/unity-asset-pipeline/references/asset-contract-template.yaml`.

## Canonical filesystem layout (R15 decision)

Everything nests under project-setup's single game root — never invent a new root:

```
Assets/<Game>/Art/
  _ArtDirection/    art-spec.yaml, style-guide.md, palettes/master-palette.png, references/, sheets/
  Approved/         registry.yaml, <asset_id>/ (asset-contract.yaml + approved art + QA reports)
  Source/           raw generated staging: SourceImages/, TripoRaw/, CleanupQueue/, QA/
  Characters/  Environment/  Props/  VFX/  UI/  Materials/  Shaders/  Prefabs/
Assets/<Game>/Audio/
  SFX/  Music/  VO/  Ambience/    generated clips (unity-audio-generator); registry audio entries point here via clip:
```

- Canonical spec path: `Assets/<Game>/Art/_ArtDirection/art-spec.yaml`.
- Canonical registry path: `Assets/<Game>/Art/Approved/registry.yaml`.
- Canon sheets: `Assets/<Game>/Art/_ArtDirection/sheets/<char_id>_canon.png`; skeleton templates `*.skeleton.json` beside them.
- **Cheap v1 / legacy:** existing docs use `Assets/GameArt/` and `Assets/Art/` consistently; both roots stay **reserved aliases**. Discovery (detect scripts, session resume) MUST probe all three roots; NEW artifacts are written to the canonical layout only. Unification of legacy references is follow-up polish, not a blocker.

## Canonical style_id

- Form: `<preset>_v<N>`, e.g. **`cozy_toy_diorama_v1`** (preset names in `style-presets.md` are unversioned; the per-game `style_id` adds `_v<N>`).
- The exact same string appears in `art-spec.yaml:style_id`, every `asset-contract.yaml:style_id`, and `composition.yaml:style_id`. String inequality = validation failure.

## art-spec.yaml — exact keys (new blocks)

| Key path | Meaning |
|---|---|
| `craft.finish` | ALWAYS set: `pixel \| painterly_2d \| vector_flat \| stylized_3d \| realistic_3d`. Skills branch on it. |
| `craft.pixels_per_unit` | **Project-wide PPU SSOT** (see PPU rule below). |
| `craft.base_render_resolution` | Pixel only: `[320, 180]`-style internal render target for integer scaling. |
| `craft.tile_size` | Pixel only: px per tile; canvas sizes derive from tiles, never ad hoc. |
| `craft.char_tiles` | Pixel only: standard character footprint in tiles, e.g. `[1, 2]`. |
| `craft.outline_style` | Pixel only: PixelLab exact enum (below). Distinct from `rendering.outline` (runtime shader outline). |
| `craft.view` | Pixel only: per-game DEFAULT sprite camera view — PixelLab exact enum `side \| low top-down \| high top-down`. Autofilled as `--view`; CLI overrides per call. |
| `craft.shading` | Pixel only: per-game DEFAULT shading level — PixelLab exact enum (below). Autofilled as `--shading`; CLI overrides per call. |
| `craft.light_direction` | Prompt-level token + vision-QA criterion — **no PixelLab API param**. `composition.yaml:shadow_and_contact.key_light_direction` MUST equal it. |
| `craft.dithering_policy` | Prompt-level token + vision-QA criterion — no API param. |
| `palette.roles.{ground,panel,ink,accent_primary,accent_secondary}` | Semantic hexes; the ONLY colors GameTheme/UI tokens may use. |
| `palette.ramps.<name>` | Hue-shifted ramps, dark→light. Pixel track REQUIRES ramps; master-palette.png is their union. |
| `conditioning.master_palette_png` | PixelLab `color_image`-compatible swatch; passed on EVERY PixelLab call (derived frames may use the anchor's extracted sub-palette — subset only). |
| `conditioning.style_anchor_images` | List of paths; bitforge consumes ONE per call via `--style-image`. |
| `conditioning.golden_assets.<family>` | Family → approved golden source image. Key `game` = the game golden, the only text-only (pixflux) roll. |
| `characters.<id>.{canon_sheet,anchor_sprite,identity_string,skeleton_template,seed}` | THE authoritative per-character canon index. `identity_string` is frozen verbatim (vary only pose clauses). `seed` is provenance only — never identity. |
| `audio_direction.{prompt_prefix,instrument_palette,mood_tokens,voice_id}` | The sound-world contract (unity-audio-generator). Production SFX/music prompts start with `prompt_prefix` + instrument/mood tokens VERBATIM; SFX identity rests entirely on these tokens. `voice_id` pins the ElevenLabs voice for TTS/VO ONLY — never SFX. No block = exploratory clips only. |
| `derived_artifacts.{style_guide_md,game_theme_cs,ui_design_tokens}` | Paths of DERIVED views (see derivation rule). |

AssetBrief adds a commented `conditioning:` sub-block: `golden_asset`, `style_anchor_image`, `master_palette_png`, `canon_sheet`, `identity_string` — resolved paths, not prose.

## asset-contract.yaml — extended keys

- Top level: `art_spec:` — resolvable path to the governing spec (validators resolve the spec from here).
- `source.reference_pack` is now a **list of resolvable file paths** (anchors, palette swatch, sheets) — not a pack name.
- `source.canon_sheet`, `source.identity_string` — characters only; copied from the art-spec `characters` block (identity_string VERBATIM).
- `source.seed` — provenance only.

## PPU single source of truth

1. `art-spec.yaml:craft.pixels_per_unit` is THE project PPU. Every sprite import, tilemap, layout, and camera-size computation reads it.
2. Fallback (no art-spec exists): `asset-contract.yaml:runtime.pixels_per_unit`, which must be uniform across the registry.
3. Never pick a local/hardcoded PPU value. One game = one PPU (one pixel density — no mixels).

## PixelLab exact enum strings (never invent shorthands)

- `outline`: `single color black outline` | `single color outline` | `selective outline` | `lineless`
- `shading`: `flat shading` | `basic shading` | `medium shading` | `detailed shading` | `highly detailed shading`
- `detail`: `low detail` | `medium detail` | `highly detailed`
- Palette lock = `color_image` swatch (no `target_palette` param exists). `light_direction`/`dithering_policy` have NO API params — prompt tokens + vision-QA only.

## Derivation rule (one style stack)

- `art-spec.yaml` is the single style SSOT. `style-guide.md`, `GameTheme.cs`, and UI design tokens are **derived views**, regenerated FROM it — never hand-edited into divergence.
- Equality scope: `GameTheme.cs` **color hexes** MUST equal art-spec palette hexes (`palette.roles` + arrays), **colors only** — typography/spacing/radii are GameTheme-native and have no art-spec source.

## Art-spec resolver lockstep (shared conventions, duplicated implementations)

Two script-side resolvers implement the resolution order `--art-spec` → `$UNITY_ART_SPEC` → probe `Assets/*/Art/_ArtDirection/art-spec.yaml`, then legacy `Assets/GameArt/_ArtDirection/`, `Assets/Art/_ArtDirection/`:

- `skills/unity-image-generator/scripts/art_spec.py` (shared module imported by generate_image.py / validate_sprite.py / critique_image.py — MUST ship alongside them when the skill is copied/synced)
- the inline resolver in `skills/unity-pixel-art/scripts/generate_pixel_art.py`

They intentionally duplicate these conventions (cross-skill Python imports are not established). **Any change to the env var name, probe globs, or fail-unless-`--no-art-spec` behavior must be applied to BOTH, and to this doc first.**

**Spec-internal path resolution (both resolvers, lockstep):** paths declared INSIDE the spec (`conditioning.master_palette_png`, `conditioning.golden_assets.*`, `conditioning.style_anchor_images`, `characters.<id>.canon_sheet`) are `Assets/`-relative and resolve against the **project root derived from the resolved spec path** (the path segment before `Assets/` — same logic as `validate_asset_manifest.py`'s `project_root_for`), falling back to cwd, then the spec's directory. Never cwd alone. A declared-but-missing conditioning artifact on a production call FAILS loudly (master palette, golden anchor, `--character` canon sheet) or warns loudly (spec style anchors on the Gemini leg) — it is never silently dropped.

## Missing-spec behavior

- **Production paths fail-unless-overridden:** generation/QA/import tooling that cannot resolve an art-spec must FAIL, unless invoked with an explicit `--no-art-spec` override. No interactive confirmation (agent-run CLIs).
- **Exploratory/concept work stays legal:** spec-less concepting, style boards, and prototypes use `--no-art-spec` (or non-production commands) freely.
- **Never block gray-box gameplay:** art gates apply to ART production and scene ART assembly only. Gray-box prototyping with flagged placeholder primitives proceeds in parallel and is never blocked on art-spec approval.

## Deploy step (repo → live sessions)

Live sessions load skills from `~/.claude/skills`, which holds real copies (not symlinks). After changing any skill, re-sync it or stale guidance re-poisons sessions:

```bash
cd <repo>/skills && for d in unity-*/; do rsync -a --delete --exclude '__pycache__' --exclude '.DS_Store' "$d" ~/.claude/skills/"$d"; done
```

Sync whole directories — `unity-image-generator/scripts/art_spec.py` must ship alongside the scripts that import it. (`unity-2d-sprite-games` lives only in `~/.claude/skills`; never delete it from there.)

## Gate order (summary)

art-spec approved → canon per recurring character → conditioned generation (golden anchor + master palette on every call) → deterministic QA, then VLM QA → contract + validator exit 0 → registry → scenes place registry assets only.
