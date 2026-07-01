# Definition of Done — First Playable Slice

Do not claim a new game or first playable slice is complete until all pass. Each line needs evidence from the live Editor, not assertion.

- [ ] **Compiles clean.** `read_console(types=["error"])` is empty after the last `create_script` / edit (domain reload settled, `editor/state` ready).
- [ ] **Input works.** A real touch path (tap / swipe / drag via the Input System) actually moves or affects the player — exercised in the Game view, not just bound. Legacy `Input` is NOT used if the project is set to the Input System.
- [ ] **Core loop reachable.** verb → objective → feedback chain runs end to end with one input.
- [ ] **Win/lose or restart exists.** The player can reach game-over and restart, or reach a win and continue. No dead ends.
- [ ] **Runs in Play Mode with a screenshot.** `manage_editor(action="play")` → `read_console` clean → `manage_scene(action="screenshot")` shows the controllable object on screen → `stop`. Not a blank/black scene.
- [ ] **Basic feel present.** At least one piece of juice on the core action (pop, squash, shake, sound hook, or haptic) so the input feels responsive, not dead.
- [ ] **No per-frame allocation hotspots.** No `Instantiate`/`Destroy`, `Find`, `GetComponent`, or LINQ in `Update`/`FixedUpdate`; repeated spawns are pooled.
- [ ] **Scene/prefabs went through MCP.** Scenes, GameObjects, components, and prefabs created via `manage_scene` / `manage_gameobject` / `manage_components` / `manage_prefabs` — no hand-edited YAML.
- [ ] **Visible art registry-sourced or flagged.** Primary visible surfaces use approved-registry assets (`unity-asset-pipeline`) and pass the `unity-aaa-graphics` scorecard, **or** every remaining primitive is explicitly flagged as a placeholder in the ledger. No raw generator files wired directly into gameplay prefabs.
- [ ] **(Recommended) PlayMode test green.** `run_tests(mode="PlayMode")` + `get_test_job` asserts the loop (e.g. input raises score, hazard triggers respawn).

If any box is unchecked, the slice is not done — report which and why.
