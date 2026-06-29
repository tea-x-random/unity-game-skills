# Screenshot acceptance checklist

Capture target-device screenshots from the actual Game View/camera, not only Scene View. A pass must satisfy all checks below.

## Readability

- First read is the gameplay objective/interactable, not decorative background.
- Player path/grid/puzzle board is visible without zooming.
- Interactable objects have stronger contrast, outline, glow, value, or motion than decoration.
- UI is readable at device size and respects safe area.

## Composition

- Big/medium/small rhythm is visible; not every asset has equal screen weight.
- At least 30% of the screen is a quiet/rest area unless the genre intentionally forbids it.
- Prop density is within `composition.yaml` budget.
- Foreground occlusion stays below the configured budget and never covers critical path/UI.
- Focal path first → second → third read is clear within three seconds.

## Style coherence

- Camera angle and asset perspective agree.
- Shadow direction/contact-darkening agree across assets.
- Palette zones match: background quiet, rewards/interactables accented.
- UI material/color feels related to the world but remains more legible.
- No raw generated files or unapproved prefabs appear in the hierarchy.

## Evidence

Record screenshot path, scene name, device resolution, camera profile id, registry commit/hash if available, and pass/fail notes. Store the result with the BeautyCell or scene QA artifact.
