# Checklist — broken / blank / black scene

Read the console first. Then walk this list. Drive all checks/edits through MCP, not raw YAML.

- [ ] **Console clean?** `read_console(types=["error"])` — compile errors block everything; nothing renders correctly until clean. Then `["warning"]`.
- [ ] **Right scene active?** Confirm the loaded/active scene is the one you expect (not an empty/default scene).
- [ ] **Camera exists and enabled?** At least one active `Camera` tagged correctly; GameObject not disabled.
- [ ] **Camera framing?** Position/rotation points at content; near/far clip not excluding it; orthographic size sane (2D).
- [ ] **Culling mask / clear flags?** Culling mask includes the object layers; clear flags not hiding everything (solid color over content).
- [ ] **Lighting?** URP/Lit looks black with no light — add/enable a Directional Light; check environment/ambient lighting; bake if needed.
- [ ] **Materials valid?** No pink/magenta (Built-in shader in URP) — confirm `renderPipeline`, convert to URP / set `Universal Render Pipeline/Lit`.
- [ ] **Objects present and visible?** Renderers enabled, not scaled to 0, not far outside the frustum, MeshRenderer/SpriteRenderer has a mesh/sprite.
- [ ] **Runtime exception on enter?** Won't enter Play Mode or wipes the scene → exception in `Awake`/`OnEnable` (read console).
- [ ] **References intact?** No `MissingReferenceException` / *Missing* fields from moved/renamed assets or broken prefab links.
- [ ] **Verify:** `manage_editor(action="play")` → `read_console` clean → `manage_scene(action="screenshot")` shows real content → `stop`.
