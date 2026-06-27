# Checklist — mobile performance (casual iOS, 60fps)

Measure with `manage_profiler` + `manage_graphics` in Play Mode (dev build for real numbers). Capture a baseline, fix one thing, re-measure the same scenario.

- [ ] **60fps held** — frame time ≤ 16.6 ms in the steady, heaviest scenario (not just the first frame).
- [ ] **CPU vs GPU bound identified** — optimizing the side that actually gates the frame.
- [ ] **Draw calls / batches / SetPass in budget** — materials shared, atlas/Sprite Atlas used, GPU instancing for repeats, static batching for non-moving geometry, SRP Batcher intact.
- [ ] **Zero steady-state GC allocations** — GC Alloc/frame ≈ 0; no per-frame `new`/LINQ/boxing/string-concat/uncached `GetComponent` in hot paths; objects pooled.
- [ ] **Texture memory in budget** — ASTC compression for iOS, sensible sizes, mipmaps where needed; no stray RGBA32 atlases.
- [ ] **Total memory under the device ceiling** — no runaway growth across a session.
- [ ] **Overdraw controlled** — minimal stacked transparent/UI/particle fill.
- [ ] **No thermal throttle drop** — sustained-load session still holds the target frame rate after the device heats up.
- [ ] **No hitches** — no periodic frame spikes (GC, sync loads, Instantiate bursts, physics spikes).
- [ ] **On-device verified for release claims** — profiled on a real iOS device, not Editor-only.
