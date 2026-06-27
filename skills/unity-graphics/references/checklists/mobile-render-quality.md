# Checklist — Mobile Render Quality (casual iOS)

Run before claiming a scene is premium / polished / less-basic. Verify each with MCP, not assumption.

- [ ] **URP confirmed** active in `mcpforunity://project/info` (`renderPipeline` = URP; not HDRP/Built-in).
- [ ] **Lights ≤ 1–2 realtime**, ideally a single directional sun; everything else Baked or Mixed.
- [ ] **Baked where possible** — static geometry contributes GI, lightmaps baked (`bake_lighting`), Light Probe Group covers movers, reflection probes used sparingly/baked.
- [ ] **GPU Instancing ON** on shared materials (`enableInstancing`).
- [ ] **SRP Batcher compatible** — URP shaders / proper `UnityPerMaterial` CBUFFER; few unique materials.
- [ ] **Post conservative** — one global Volume: tonemapping + color + vignette + low bloom only; no SSAO/DoF/motion blur on the low/old-device tier; post enabled on renderer + camera.
- [ ] **Textures compressed** (ASTC for iOS), variant count low.
- [ ] **Quality tiers** defined (old vs new device): render scale / MSAA / shadows / post gated per tier.
- [ ] **Draw calls / batches / SetPass in budget** via `manage_graphics(action="stats_get")`; overdraw controlled.
- [ ] **60fps target** holding on the intended device tier.
- [ ] **Screenshot looks intentional, not primitive** — `manage_scene(action="screenshot", include_image=true)` shows a designed palette/lighting, not flat planes or default-grey primitives.
