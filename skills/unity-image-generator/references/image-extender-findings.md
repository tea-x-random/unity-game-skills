# Findings adapted from boona13/image-extender

This reference distills transferable patterns from `boona13/image-extender` into Unity game-asset practice. Do not copy its app-specific prompts or UX; use the production ideas.

## Transferable patterns

### 1. Shared scene / style brief

`image-extender` uses shared style/scene text across asset categories so the painter has consistent context. In Unity terms: every generation batch must start from the locked `art-spec.yaml` + `composition.yaml` + family brief, not a standalone prompt.

**Skill rule:** generate candidates from one shared brief, then pass that same brief to `critique_image.py --intent` so QA judges against the same target.

### 2. Best-of-N + keep-best

The repo encourages generating multiple candidates and keeping the best instead of accepting the first pass. This is critical for AI art.

**Unity workflow:** generate 3–6 candidates per production asset at 1K, run pixel QA + vision critique, then use:

```bash
python3 ~/.claude/skills/unity-image-generator/scripts/select_best_candidate.py \
  --candidates Assets/<Game>/Art/Source/QA/meadow_tree_a.candidates.json \
  --json-report Assets/<Game>/Art/Source/QA/meadow_tree_a.best.json
```

Only refine the selected candidate to 2K. Do not manually cherry-pick without a written reason.

### 3. Generate packs/sheets, not isolated one-offs

`image-extender` has tile-set and sprite-sheet generation concepts. The Unity equivalent is: create family sheets/tilesets from one shared visual DNA, then slice and validate. Avoid asking for "another tree" or "another monster" in isolation.

**Gate:** family sheet first → canonical member selected → variants derived → atlas/registry entries.

### 4. Template-guided image-to-image

Template/outline-conditioned generation reduces drift. For Unity: use rough silhouettes, tile masks, orthographic guides, or family sheets as `--input-image` references. This is especially useful for:

- consistent prop variants;
- tile edge compatibility;
- character/sprite sheet pose consistency;
- icon families with fixed size/padding.

### 5. Art-director → painter split

The repo separates higher-level direction from rendering. In our skills: `unity-art-direction` writes the spec, `unity-scene-composition` writes screen constraints, `unity-image-generator` generates candidates, and `critique_image.py` judges the output. Do not let the same one-line prompt serve all roles.

### 6. Engine-safe export: atlas padding/extrude

For Unity, generated sheets need engine-safe packing: duplicated edge pixels and padding to prevent texture bleeding. Use:

```bash
python3 ~/.claude/skills/unity-image-generator/scripts/extrude_atlas.py \
  --input Assets/<Game>/Art/Source/meadow_tiles_raw.png \
  --rows 4 --cols 4 --extrude 2 --padding 2 \
  --output Assets/<Game>/Art/Source/meadow_tiles_extruded.png \
  --manifest Assets/<Game>/Art/Source/meadow_tiles_extruded.json
```

Import/slice using `atlas_rect` from the manifest (excluding extrude border), then pack into the contract's SpriteAtlas.

### 7. Anchor-frame then sheet for characters

For character/monster sprites, lock one approved anchor pose first, then derive the sheet. Validate all frames for:

- same silhouette identity;
- same palette/outline/shading;
- same baseline/floor contact;
- consistent scale;
- no frame-to-frame drift.

For anything animated, prefer Tripo rig + pre-render (the library-wide rule). Use direct image sprite sheets only for static pose families, trivial animation, or when Tripo is unavailable.

### 8. Outpaint/background extension as a tool, not the final scene

Outpainting is useful for background plates, loading screens, and parallax extension, but it is not a substitute for composition. Extended backgrounds still need `unity-scene-composition` recede rules and in-engine screenshot validation.

## Scripts added from these findings

- `scripts/select_best_candidate.py` — best-of-N selection from sprite QA + vision critique reports.
- `scripts/extrude_atlas.py` — engine-safe duplicated-edge padding for regular-grid sheets.

## Anti-patterns this prevents

- first-pass asset becomes canon;
- one-off prompts produce a visual flea market;
- a tile sheet bleeds in Unity due to no extrude/padding;
- all frames of a sprite sheet drift in scale/baseline;
- a browser concept sheet is mistaken for in-engine proof.
