# BeautyCell visual gate

A BeautyCell is one screen that proves the game's visual system before scale-out. It is not a level; it is the gold-standard composition cell used to catch camera, lighting, scale, material, UI, and density mismatches early.

## Required scene set

Create these scenes under `Assets/Scenes/ArtValidation/`:

- `ArtValidationScene.unity` — candidate asset under gameplay camera plus neutral studio, bright outdoor, dim indoor, thumbnail/reward-card framings.
- `BeautyCell_01.unity` — one polished screen with one hero/gameplay object, two supporting prop families, one environment kit, one lighting profile, one UI card, one effect layer, one target-device screenshot.
- `CameraScaleTest.unity` — validates expected screen-height percentages and camera angle contracts.
- `LightingTest.unity` — validates shadow direction, contact darkening, material response.
- `MaterialTest.unity` — validates shared shader/material profile, palette, roughness/specular rules.
- `MobileDeviceTest.unity` — validates target resolution, safe area, texture memory, overdraw, draw calls.

## Acceptance gates

Fail the candidate if any are true:

- silhouette is unreadable at gameplay camera size;
- contact shadow or light direction disagrees with the family/reference assets;
- interactable/decor hierarchy is ambiguous;
- UI card feels unrelated to world palette/material language;
- background detail competes with gameplay path;
- candidate violates composition density or occlusion budget;
- screenshot differs materially from the reference frame beyond accepted tolerance.

## Suggested screenshot paths

```
Assets/Art/Approved/<id>/Screenshots/ArtValidationScene.png
Assets/Art/Approved/<id>/Screenshots/BeautyCell_01.png
Assets/Art/Approved/<id>/Screenshots/CameraScaleTest.png
Assets/Art/Approved/<id>/Screenshots/LightingTest.png
Assets/Art/Approved/<id>/Screenshots/MaterialTest.png
Assets/Art/Approved/<id>/Screenshots/MobileDeviceTest.png
```

Record these paths in `qa.*_screenshot` or the registry. A passing validator without recorded screenshot evidence is not a pass.
