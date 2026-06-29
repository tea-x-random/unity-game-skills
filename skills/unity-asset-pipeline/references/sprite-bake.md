# Sprite bake / pre-rendered 3D for 2D games

Use Tripo or simple authored geometry for characters, interactables, and foreground props that need consistent perspective, cast shadows, or appear near the gameplay camera. Then bake them through one shared Unity material/lighting/camera rig into transparent sprite atlases.

## Contract

Each baked sprite contract should record:

- source model path and model contract;
- bake camera profile id (orthographic/perspective, yaw, pitch, FOV/ortho size);
- lighting rig id and material profile;
- output atlas path, frame size, PPU, pivot, padding, and sprite slicing grid;
- animation clips represented in the atlas, frame counts, fps, and loop flags;
- QA reports: sprite alpha QA, scale QA, BeautyCell screenshot.

## Bake rules

1. Use one shared bake camera + lighting prefab per game style.
2. Disable arbitrary generated PBR material response; assign the project's shared stylized material profile before baking.
3. Render with transparent background and premultiplied/straight-alpha settings tested in Unity.
4. Keep shadow/contact-darkening either baked consistently into the atlas OR produced by a shared runtime shadow profile — not both randomly.
5. Validate the output atlas with `unity-image-generator/scripts/validate_sprite.py --require-alpha`.
6. Import the atlas with `SpriteImportMode.Multiple`, PPU from contract, mipmaps off, ASTC for iOS, and a SpriteAtlas pack for the whole family.
