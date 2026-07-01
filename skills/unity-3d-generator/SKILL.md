---
name: unity-3d-generator
description: "Generate, texture, rig, animate, stylize, convert, and import 3D assets for Unity casual games using the Tripo API, then import them correctly into a Unity project. Use for text-to-3D, image-to-3D, game-ready GLB/FBX, characters, creatures, props, vehicles, weapons, obstacles, collectibles, auto-rigging, animation, low-poly/mobile-optimized assets, and the write-to-Assets + ModelImporter import pipeline. Best for 3D casual iOS games (runner, stacking, .io, physics). Pair with unity-image-generator for concept/texture references before image-to-3D."
---

# Unity 3D Generator

Create production 3D assets with Tripo, then import them into Unity with mobile-correct settings. The generation engine (Tripo OpenAPI) is the same proven pipeline used elsewhere; what is Unity-specific is the **import step** — covered here and in `references/unity-import.md`.

## API key & script

Key resolution: `--api-key`, then `TRIPO_API_KEY`. Probe first (some keys live only in interactive shells):
```bash
bash ~/.claude/skills/unity-game-director/scripts/probe_asset_credentials.sh   # TRIPO_API_KEY=SET|MISSING
```
If SET but the script reports missing, wrap with the user's profile:
```bash
zsh -c 'source "$HOME/.zprofile" 2>/dev/null; source "$HOME/.zshrc" 2>/dev/null; python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py ...'
```
Download URLs expire fast — always `--download` immediately on success.

```bash
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py --help
```
Subcommands: `text`, `image`, `status`, `download`, `postprocess`, `validate-rig`, `validate-animation`, `character-pipeline`.

## Generate (download straight into the Unity project)

Write outputs under `Assets/` so Unity auto-imports them. Prefer GLB for static props, FBX for rigged/animated characters.

```bash
# Static prop / obstacle / collectible (mobile budget)
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py text \
  --prompt "game-ready stylized coin pickup, bold readable silhouette, clean low-poly, PBR, centered pivot, no text" \
  --model-version v3.1-20260211 --texture-quality detailed --geometry-quality standard \
  --wait --download --out-dir Assets/<Game>/Art/Source/TripoRaw/coin

# Image-to-3D from a style-locked turnaround (canon sheet for characters — see Style lock below)
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py image \
  --image "Assets/<Game>/Art/_ArtDirection/sheets/hero_knight_canon.png" --model-version v3.1-20260211 \
  --enable-image-autofix --texture-alignment original_image --texture-quality detailed \
  --wait --download --out-dir Assets/<Game>/Art/Source/TripoRaw/hero

# Full animated character (gen -> prerig check -> validated rig -> retargets -> download)
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py character-pipeline \
  --prompt "stylized runner character, T-pose, full body, arms away from body, game-ready, readable silhouette" \
  --animations preset:idle,preset:walk,preset:run,preset:jump \
  --out-dir Assets/<Game>/Art/Source/TripoRaw/runner
```

Postprocess (texture / rig / animate / convert / stylize), rigging reliability rules (T/A-pose, prerigcheck-first, rig version by body plan, never `--animate-in-place`), and creature stance rules are unchanged from the proven pipeline — load `references/api-notes.md` before any postprocess/rig/animation work.

## Style lock — production inputs come from the art-spec

Tripo inherits its 3D style entirely from the 2D input — the game's 2D style lock is the upstream root (no major 3D generator offers trained style locks). Hard rules for **production** assets (see `docs/PIPELINE_CONVENTIONS.md` for paths and missing-spec behavior):

1. **Image-to-3D input MUST be style-locked.** Characters: the approved canon sheet/turnaround from the art-spec `characters.<id>.canon_sheet`. Props: the family golden or a turnaround generated under the game's 2D style lock (art-spec conditioning via `unity-asset-designer`/`unity-image-generator`). Never feed image-to-3D a fresh, unconditioned concept.
2. **Prompts embed the art-spec's style tokens VERBATIM** (materials, shape_language, palette); characters copy their frozen `identity_string` exactly, varying only pose clauses (T-pose for rigging).
3. **Scale comes from the art-spec `scale` block** (`unit_rule`, `character_height_m`, `standard_door_height_m`; per-asset `scale_m` from the AssetBrief) — enforced by the mandatory post-import bounds gate in `references/unity-import.md`. Never ship `globalScale = 1.0` unmeasured.
4. **Re-shade to spec after import.** Converge imported materials to the spec's `materials` (roughness/metallic ranges, texture_language) and `rendering.shader_family`: Unity-side shared-material conversion by default, or a Tripo `texture_model` postprocess (`postprocess --type texture_model --original-task-id <id> --texture-prompt "<spec style tokens>"`) when the baked texture itself is off-style. Raw Tripo PBR beside flat/cel 2D fails the `unity-aaa-graphics` finish-consistency axis. Do not add other 3D/texture vendors for this.

No art-spec yet? Exploratory/concept modeling stays legal — say so and flag outputs as placeholders; production assets wait for the spec.

## Riggable characters need a clean full-body T-pose (or A-pose)

**Auto-rigging only works on a clean, full-body, limbs-separated pose.** If you feed image-to-3D a concept in an action pose (an archer mid-draw, arms crossed, a prop held across the body, a ¾ "hero" stance, or a cropped/occluded body), the rig will fail or come out broken — limbs fuse, joints land wrong, animation retargets garble. This is the single most common rig failure.

**The rule:** for any character that will be rigged/animated, the image-to-3D input must be a **T-pose** (arms straight out horizontally) or **A-pose** (arms down ~45°), **full body in frame**, **legs slightly apart**, **arms clearly away from the torso**, neutral/symmetrical, **no props or weapons occluding the limbs**, plain background. Generate that rigging-ready concept *first*, rig from it, *then* animate the action cycles (the bow-draw, the attack) as animation clips — never bake the action into the static mesh pose.

**Workflow:** generate a clean T-pose concept (`unity-image-generator`, or a T-pose turnaround from `unity-asset-designer`) → `image` to 3D → `prerigcheck` → rig → animate (preset/retarget cycles). If a rig fails, suspect the input pose first, regenerate a cleaner T-pose, and re-run — don't fight the rigger. Hold the character's *style/identity* constant (same prompt tokens) but swap the pose to neutral. (Props the character uses — bow, sword — are usually modeled/attached separately or kept to the side in the concept, not crossed over the body.)

## Use Tripo for non-pixel 2D pre-rendering — not for pixel art

**Tripo is not only for runtime 3D games.** For high-res/painterly/illustrated "2D" mobile games, generate a model with Tripo, rig/animate it, then render it from the game camera to transparent sprites. Reach for this when a **non-pixel** asset needs multiple angles, animation frames, or a consistent premium rendered finish.

**Do not use Tripo renders as the source of pixel art.** If the target finish is pixel art, route final generation to `unity-pixel-art` / PixelLab. Downscaling 3D destroys native pixel clusters, palette discipline, outline rules, and readable silhouettes.

Why pre-rendered 3D beats per-frame non-pixel image generation:
- **Consistency** — one model, lit once, renders identically every frame/angle. Generating each sprite or animation frame independently with an image model drifts; a rendered rig does not.
- **Animation for free** — rig + animate once (Tripo), then render each frame of a cycle to a sprite strip with perfect identity.
- **Any angle** — render top-down, 3/4, side, or an N-direction set from the same model.
- **Baked depth/lighting/AO** — rendered sprites carry real form and shadow for non-pixel styles.

### Pipeline
1. **Generate (and rig/animate) with Tripo** for the non-pixel asset.
2. **Import into Unity**, set up an orthographic camera + lighting matching the game's angle.
3. **Render to PNG** with transparent background — static frame, animation frames, or rotations.
4. **Import the rendered PNGs as sprites** (see `unity-image-generator` import settings: Sprite, ASTC, atlas) and animate via `unity-animation`.

Compact render recipe lives in `references/prerender-2d.md`. Use Gemini (`unity-image-generator`) for concepts, textures, tiling grounds, and UI; use Tripo + render for **non-pixel** characters/props/animated actors that need consistency; use `unity-pixel-art` for final pixel sprites.

## Prompt quality (game-ready, on-model)

A premium, on-model model starts with a premium prompt — generic prompts give blobs. Name, in order: **subject**; **art style + 1–2 named touchstones**; **shape language / silhouette readability**; **material & palette**; and **detail/fidelity** ("clean low-poly, readable silhouette, game-ready, PBR, centered pivot, no text"). Always include negatives — **NOT: blobby, off-model, jagged, low-detail**.

For production assets, **image-to-3D conditioned on the style-locked turnaround/canon sheet is mandatory** (see "Style lock" above) — the sheet locks proportions, palette, and silhouette so the mesh matches canon; bare text-to-3D is for exploration only. See `../unity-aaa-graphics/references/prompt-library.md` for the full AAA template and per-genre art kits/exemplars.

Refine: if the silhouette is wrong, regenerate the prompt (not just re-roll the seed); reuse the verbatim style tokens that already produced on-model results.

## Import into Unity (the part that is Unity-specific)

After download, the file is in `Assets/`. **Refresh and configure import settings — do not trust defaults.** Load `references/unity-import.md` for the full recipe. Short version, driven through `unity-mcp-bridge`:

1. `refresh_unity(scope="assets", wait_for_ready=true)` so Unity imports the new file.
2. `manage_asset(action="import")` only reimports — it **cannot set import settings**. Configure via `execute_code` driving `ModelImporter`: scale factor, `Read/Write` off (saves memory) unless mesh is read at runtime, mesh compression on for mobile, import materials/textures as needed, and for characters set the rig (`AnimationType.Humanoid` for biped Mixamo-style, `Generic` for creatures).
3. **Scale gate (mandatory):** measure renderer bounds post-import and FAIL if the model's height is outside its role's range from the art-spec `scale` block; correct `globalScale` and re-measure. Recipe in `references/unity-import.md`.
4. For **GLB**, ensure the **glTFast** package (`com.unity.cloud.gltfast`) is installed, or convert to FBX. FBX imports natively.
5. Set texture compression to **ASTC** for iOS (platform override) — the default can be wrong on mobile. Re-shade materials to the spec (`materials` + `rendering.shader_family` — "Style lock" rule 4).
6. **Production flow — contract, not ad-hoc prefabs:** write `asset-contract.yaml`, run `validate_asset_manifest.py` (must exit 0), then ApplyAssetContract → GeneratePrefabFromContract → registry entry, all via `unity-asset-pipeline`. Scenes instantiate the REGISTRY prefab — never the raw FBX/GLB. (Standalone/exploratory only: `manage_gameobject(action="create", prefab_path=...)` + `manage_prefabs(action="create_from_gameobject")` is allowed, but the result is a flagged placeholder, not an approved asset.)
7. Animated characters use Unity's **Animator/Mecanim**: create an Animator Controller, add the imported clips as states. Verify motion in Play Mode + a screenshot. `unity-animation` owns importing the rig + clips into an Animator and wiring Animation Events, so attacks/shots fire on the right frame.

## Quality & mobile rules

- Improve prompts with material, silhouette, scale, camera readability, and game-use constraints.
- Casual iOS is triangle/draw-call/memory bound: favor `smart_low_poly`, `--face-limit`, low-poly postprocess, shared atlased materials, and GPU instancing for repeated props.
- Use generated models for hero/high-fidelity content; build repeated background props procedurally or via instancing.
- Always download immediately; report Tripo task IDs, output paths, model version, import settings applied, and a Play Mode screenshot as evidence.
