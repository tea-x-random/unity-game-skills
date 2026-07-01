# Screenshot acceptance — measured gates + scored dimensions

Capture target-device screenshots from the actual Game View/camera, not only Scene View — at the target aspect plus at least one alternate aspect. Every composed-scene screenshot runs BOTH passes below; neither replaces the other.

## Pass 1 — MEASURED gates (deterministic, from Unity scene data via MCP)

Computed with `references/scene-measurement.md` — never eyeballed, never delegated to the VLM. Any violation is a **hard failure**: fix by moving/removing/rescaling (workflow step 9), not by re-generating art.

- **Density within budget** — sum of registry `density_cost` for renderers in the gameplay-camera frustum ≤ `density_budget.max_density_cost_per_screen`; interesting-object and family counts within their caps.
- **Occlusion within budget** — foreground renderers' projected viewport coverage of the gameplay area ≤ `occlusion_budget.gameplay_area_max_percent`; 0% over critical path and UI safe area.
- **Screen heights within role ranges** — each renderer's bounds-projected screen-height % inside `shape_rhythm.target_screen_height_percent` for its contract role.
- **Camera contract match** — active camera projection/yaw/pitch/ortho-size equal `camera_profile`; every visible asset's `camera_contract` matches (or is marked UI/background).
- **No unapproved assets** — every visible renderer resolves to a `registry.yaml` entry or is explicitly flagged as a gray-box placeholder in the ledger.
- **One pixel density** (sprite/2.5D scenes, when `pixel_density` is set) — ground `texels_per_unit` within `texel_tolerance_percent` of the project PPU (`art-spec craft.pixels_per_unit`); filter modes uniform (pixel track: Point everywhere, mipmaps off); one light model across sprites and ground.
- **UI safe area** — HUD RectTransforms inside `Screen.safeArea` at the target resolution.

## Pass 2 — SCORED dimensions (VLM, scene mode)

Run `critique_image.py <screenshot> --scene-mode --subject "<scene intent>" --reference <golden screen> --art-spec <spec>` (`unity-image-generator`). These are qualitative reads the numbers can't capture. **Calibration policy:** a low scene score triggers a bounded re-roll or manual review — it does not hard-block the scene.

- **Focal read** — first read is the gameplay objective within three seconds; first → second → third read order is clear; forbidden first reads (background detail, filler, decorative VFX) don't win.
- **Layer contrast** — interactables out-contrast decoration; background/ground spends less contrast/outline/saturation than gameplay; big/medium/small rhythm visible; ≥30% quiet area (unless genre forbids).
- **Grounding** — shadow direction/contact darkening agree across assets; no floating/pasted-on sprites; no baked-in PNG shadows disagreeing with the scene light.
- **Cohesion** — camera angle and asset perspective agree; palette zones match (quiet gameplay path, accented rewards); UI related to the world but more legible; no chunky-vs-smooth pixel mismatch, alpha fringe/halo, or obvious tiling wallpaper.

## Evidence

Record: screenshot paths, scene name, device resolution, camera profile id, the measurement JSON (pass 1), the scene-mode critique JSON (pass 2), registry commit/hash if available, and pass/fail notes. Store with the BeautyCell or scene QA artifact so session N+1 can resume from it.
