# Approved asset registry schema

`Assets/<Game>/Art/Approved/registry.yaml` is the only source scene-building agents may use. If a prefab is not listed here, it is not approved for gameplay scene assembly.

```yaml
schema: unity-game-skills.approved-asset-registry.v1
game: ExampleGame
art_spec: Assets/<Game>/Art/_ArtDirection/art-spec.yaml
composition_profile: Assets/<Game>/Art/_ArtDirection/composition.yaml
updated_at: 2026-06-28T00:00:00Z
assets:
  - id: meadow_tree_a
    contract: Assets/<Game>/Art/Approved/meadow_tree_a/asset-contract.yaml
    prefab: Assets/<Game>/Art/Prefabs/Environment/MeadowTreeA.prefab
    family: meadow_vegetation
    role: midground_obstacle
    style_id: cozy_toy_diorama_v1
    composition_layer: midground
    visual_weight: medium
    atlas_group: environment_midground_v1
    sprite_atlas: Assets/<Game>/Art/Atlases/Environment_Midground.spriteatlas
    addressables:
      address: art/environment/meadow_tree_a
      group: Art_Environment
      labels: [art, environment, meadow_vegetation]
    qa:
      alpha_valid: true
      import_valid: true
      scale_valid: true            # sprites: computed by validate_asset_manifest.py (dims/PPU vs scale_meters).
                                   # 3D models: satisfied by the Editor-side bounds gate — unity-3d-generator/
                                   # references/unity-import.md Step 2b (measured renderer bounds vs the
                                   # art-spec scale block); the Python validator does NOT compute it for models.
      material_valid: true
      secondary_textures_valid: true
      palette_valid: true
      pixel_native_valid: true
      atlas_valid: true
      addressables_valid: true
      scene_test_valid: true
      visual_regression_valid: true
    screenshots:
      beauty_cell: Assets/<Game>/Art/Approved/meadow_tree_a/BeautyCell_01.png
      art_validation: Assets/<Game>/Art/Approved/meadow_tree_a/ArtValidationScene.png
  - id: sfx_coin_pickup            # audio entries: clip instead of prefab
    contract: Assets/<Game>/Art/Approved/sfx_coin_pickup/asset-contract.yaml
    clip: Assets/<Game>/Audio/SFX/sfx_coin_pickup.wav
    family: sfx_feedback
    role: sfx
    style_id: cozy_toy_diorama_v1
    qa:
      import_valid: true           # AudioImporter matches contract runtime.audio (load type, Vorbis quality, mono)
      loudness_valid: true         # measured loudness within tolerance of runtime.audio.target_lufs
      loop_seamless: true          # loop clips only — true only after the crossfade post-process ran + was verified
```

## Registry rules

1. Do not add an entry until `qa.approved: true` in the contract.
2. Registry `style_id` must match `art-spec.yaml`.
3. Registry `prefab` must exist and must match `runtime.prefab` in the contract.
4. Scene builders instantiate only registry prefabs, never raw source files, textures, models, or generated PNGs.
5. Removing a registry entry should break scene-generation references loudly; do not silently substitute a visually similar asset.
6. Run `validate_asset_manifest.py --registry Assets/<Game>/Art/Approved/registry.yaml` before any automated scene build (the art-spec resolves from the registry's `art_spec:` key; validation FAILS if it can't).
7. Audio entries reference the imported AudioClip via `clip:` instead of `prefab:`; their import QA is the AudioImporter-vs-`runtime.audio` check, and `loop_seamless` may only be true after the crossfade post-process.
