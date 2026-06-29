# Approved asset registry schema

`Assets/Art/Approved/registry.yaml` is the only source scene-building agents may use. If a prefab is not listed here, it is not approved for gameplay scene assembly.

```yaml
schema: unity-game-skills.approved-asset-registry.v1
game: ExampleGame
art_spec: Assets/GameArt/_ArtDirection/art-spec.yaml
composition_profile: Assets/GameArt/_ArtDirection/composition.yaml
updated_at: 2026-06-28T00:00:00Z
assets:
  - id: meadow_tree_a
    contract: Assets/Art/Approved/meadow_tree_a/asset-contract.yaml
    prefab: Assets/Prefabs/Environment/MeadowTreeA.prefab
    family: meadow_vegetation
    role: midground_obstacle
    style_id: cozy_toy_diorama_v1
    composition_layer: midground
    visual_weight: medium
    atlas_group: environment_midground_v1
    sprite_atlas: Assets/Art/Atlases/Environment_Midground.spriteatlas
    addressables:
      address: art/environment/meadow_tree_a
      group: Art_Environment
      labels: [art, environment, meadow_vegetation]
    qa:
      alpha_valid: true
      import_valid: true
      scale_valid: true
      material_valid: true
      secondary_textures_valid: true
      palette_valid: true
      pixel_native_valid: true
      atlas_valid: true
      addressables_valid: true
      scene_test_valid: true
      visual_regression_valid: true
    screenshots:
      beauty_cell: Assets/Art/Approved/meadow_tree_a/BeautyCell_01.png
      art_validation: Assets/Art/Approved/meadow_tree_a/ArtValidationScene.png
```

## Registry rules

1. Do not add an entry until `qa.approved: true` in the contract.
2. Registry `style_id` must match `art-spec.yaml`.
3. Registry `prefab` must exist and must match `runtime.prefab` in the contract.
4. Scene builders instantiate only registry prefabs, never raw source files, textures, models, or generated PNGs.
5. Removing a registry entry should break scene-generation references loudly; do not silently substitute a visually similar asset.
6. Run `validate_asset_manifest.py --registry Assets/Art/Approved/registry.yaml --art-spec ...` before any automated scene build.
