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
  --wait --download --out-dir Assets/Art/Models/coin

# Image-to-3D from a concept made with unity-image-generator
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py image \
  --image Assets/Art/Concepts/hero-front.png --model-version v3.1-20260211 \
  --enable-image-autofix --texture-alignment original_image --texture-quality detailed \
  --wait --download --out-dir Assets/Art/Models/hero

# Full animated character (gen -> prerig check -> validated rig -> retargets -> download)
python3 ~/.claude/skills/unity-3d-generator/scripts/unity_3d_asset.py character-pipeline \
  --prompt "stylized runner character, T-pose, full body, arms away from body, game-ready, readable silhouette" \
  --animations preset:idle,preset:walk,preset:run,preset:jump \
  --out-dir Assets/Art/Models/runner
```

Postprocess (texture / rig / animate / convert / stylize), rigging reliability rules (T/A-pose, prerigcheck-first, rig version by body plan, never `--animate-in-place`), and creature stance rules are unchanged from the proven pipeline — load `references/api-notes.md` before any postprocess/rig/animation work.

## Prompt quality (game-ready, on-model)

A premium, on-model model starts with a premium prompt — generic prompts give blobs. Name, in order: **subject**; **art style + 1–2 named touchstones**; **shape language / silhouette readability**; **material & palette**; and **detail/fidelity** ("clean low-poly, readable silhouette, game-ready, PBR, centered pivot, no text"). Always include negatives — **NOT: blobby, off-model, jagged, low-detail**.

For best on-model results, prefer **image-to-3D conditioned on a turnaround/concept sheet from `unity-asset-designer`** over bare text-to-3D — the sheet locks proportions, palette, and silhouette so the mesh matches canon. See `../unity-aaa-graphics/references/prompt-library.md` for the full AAA template and per-genre art kits/exemplars.

Refine: if the silhouette is wrong, regenerate the prompt (not just re-roll the seed); reuse the verbatim style tokens that already produced on-model results.

## Import into Unity (the part that is Unity-specific)

After download, the file is in `Assets/`. **Refresh and configure import settings — do not trust defaults.** Load `references/unity-import.md` for the full recipe. Short version, driven through `unity-mcp-bridge`:

1. `refresh_unity(scope="assets", wait_for_ready=true)` so Unity imports the new file.
2. `manage_asset(action="import")` only reimports — it **cannot set import settings**. Configure via `execute_code` driving `ModelImporter`: scale factor, `Read/Write` off (saves memory) unless mesh is read at runtime, mesh compression on for mobile, import materials/textures as needed, and for characters set the rig (`AnimationType.Humanoid` for biped Mixamo-style, `Generic` for creatures).
3. For **GLB**, ensure the **glTFast** package (`com.unity.cloud.gltfast`) is installed, or convert to FBX. FBX imports natively.
4. Set texture compression to **ASTC** for iOS (platform override) — the default can be wrong on mobile.
5. Instantiate: `manage_gameobject(action="create", prefab_path="Assets/Art/Models/hero/hero.fbx")`, then save as a prefab via `manage_prefabs(action="create_from_gameobject")`.
6. Animated characters use Unity's **Animator/Mecanim**: create an Animator Controller, add the imported clips as states. Verify motion in Play Mode + a screenshot.

## Quality & mobile rules

- Improve prompts with material, silhouette, scale, camera readability, and game-use constraints.
- Casual iOS is triangle/draw-call/memory bound: favor `smart_low_poly`, `--face-limit`, low-poly postprocess, shared atlased materials, and GPU instancing for repeated props.
- Use generated models for hero/high-fidelity content; build repeated background props procedurally or via instancing.
- Always download immediately; report Tripo task IDs, output paths, model version, import settings applied, and a Play Mode screenshot as evidence.
