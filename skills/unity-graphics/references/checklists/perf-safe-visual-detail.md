# Checklist — Perf-Safe Visual Detail (cheap but premium)

Techniques that raise perceived quality without breaking the mobile frame budget. Confirm cost with `manage_graphics(action="stats_get")` after each.

- [ ] **Stylized flat-color / gradient palette** (URP/Unlit or flat URP/Lit) instead of PBR realism — reads as designed, batches well.
- [ ] **Baked AO** into textures or vertex colors so shading looks grounded at zero runtime cost.
- [ ] **Vertex colors** for per-object tint/gradients without extra materials.
- [ ] **Fog** (linear/exponential) for depth and to hide draw distance — near-free mood.
- [ ] **Skybox / gradient backdrop** giving the frame a deliberate background, not empty void.
- [ ] **Billboards / impostors** for distant detail (trees, clouds, crowds) instead of real geometry.
- [ ] **Particle pops / juice** on gameplay events (collect, land, win) — small, short-lived, additive.
- [ ] **Shared atlas + single material** across many objects to keep SetPass calls flat.
- [ ] **Blob / contact shadows** instead of full realtime shadow casters where acceptable.
- [ ] **Bloom only on emissive accents**, low intensity — added last, after forms and palette.
- [ ] **Forms and palette built first**; glow/effects added last. (Glow on primitives is not premium.)
