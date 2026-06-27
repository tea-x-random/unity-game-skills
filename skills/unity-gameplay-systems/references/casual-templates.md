# Casual Build Recipes (MCP + scripts)

Two ordered slice recipes. Every Editor action is an MCP call (`unity-mcp-bridge`); scripts are created via `create_script` and must compile clean (`read_console(types=["error"])`) before they are used. Confirm `mcpforunity://editor/state` is ready before each batch, and expect a ~5s domain-reload drop after every compile — wait and retry.

Primitives prove the loop; swap in real sprites/models (`unity-image-generator` / `unity-3d-generator`) before claiming premium.

---

## Recipe A — 2D tapper / puzzle slice

**Loop:** *Tap a falling/placed piece → it reacts (pop/match/score) → miss or fill the board → restart.*

### 1. Project / scene
```text
manage_scene(action="create", name="Game2D", path="Assets/Scenes/Game2D.unity")
manage_scene(action="load", path="Assets/Scenes/Game2D.unity")
# set the main camera orthographic, sized to the board:
manage_components(action="set", target="Main Camera",
  component="Camera", properties={ orthographic:true, orthographicSize:5 })
manage_physics(action="get_settings")          # confirm 2D gravity if using Dynamic bodies
```

### 2. Scripts (create + compile-check each)
```text
create_script(name="TileSpawner",   path="Assets/Scripts/")
create_script(name="Tile",          path="Assets/Scripts/")
create_script(name="BoardState",    path="Assets/Scripts/")   # small state machine
create_script(name="TapInput",      path="Assets/Scripts/")   # Input System / EnhancedTouch
create_script(name="ScoreManager",  path="Assets/Scripts/")   # singleton + GameEvents
-> after each: poll editor/state, read_console(types=["error"])  # only proceed if clean
```

`TapInput`: read `Touch.activeTouches`, on `Began` convert `screenPosition` →
`Camera.main.ScreenToWorldPoint`, then `Physics2D.OverlapPoint(worldPos)` to pick the tile.
`Tile`: `SpriteRenderer` + `Collider2D` (and `Rigidbody2D` if it falls). On tap → squash, particle pop, `GameEvents.RaiseScore(...)`, return to pool.
`BoardState`: `Idle → Selecting → Resolving → Spawning`.

### 3. Build the tile prefab (batch)
```text
batch_execute(commands=[
  { manage_gameobject(action="create", name="Tile") },
  { manage_components(action="add", target="Tile", component="SpriteRenderer") },
  { manage_components(action="add", target="Tile", component="BoxCollider2D") },
  { manage_components(action="add", target="Tile", component="Tile") },
], fail_fast=true)
manage_prefabs(action="create", target="Tile", path="Assets/Prefabs/Tile.prefab")
```
Assign a sprite from a **Sprite Atlas** (one draw call). Atlas/import via `unity-image-generator`.

### 4. Wire the scene
```text
manage_gameobject(action="create", name="Systems")
manage_components(action="add", target="Systems", component="TileSpawner")  # set pooled Tile prefab + count
manage_components(action="add", target="Systems", component="ScoreManager")
manage_components(action="add", target="Systems", component="TapInput")
```
Pool the tiles (see `csharp-patterns.md`); spawner pulls from the pool, never `Instantiate` per spawn.

### 5. Verify
```text
manage_editor(action="play")
read_console(types=["error"])                 # clean
manage_scene(action="screenshot", include_image=true, max_resolution=512)   # tiles visible
# tap a tile in the Game view -> score changes -> restart works
manage_editor(action="stop")
```
HUD (score/restart) via `unity-ui-designer`. Optional `run_tests(mode="PlayMode")` asserting a tap raises a score event.

---

## Recipe B — 3D endless-runner slice

**Loop:** *Auto-run forward, swipe to switch lane / tap to jump → dodge obstacles, grab coins → hit hazard → respawn / restart.*

### 1. Project / scene
```text
manage_scene(action="create", name="Runner", path="Assets/Scenes/Runner.unity")
manage_scene(action="load", path="Assets/Scenes/Runner.unity")
manage_gameobject(action="create", name="Ground", primitive_type="Plane")  # placeholder track
```

### 2. Scripts (create + compile-check each)
```text
create_script(name="RunnerController", path="Assets/Scripts/")  # CharacterController, lanes, jump
create_script(name="SwipeInput",       path="Assets/Scripts/")  # Input System swipe -> lane/jump
create_script(name="ChunkSpawner",     path="Assets/Scripts/")  # pooled track chunks ahead
create_script(name="Obstacle",         path="Assets/Scripts/")  # trigger -> kill
create_script(name="Coin",             path="Assets/Scripts/")  # trigger -> score, pool release
create_script(name="DifficultyManager",path="Assets/Scripts/")  # ramp speed + spawn density
create_script(name="FollowCamera",     path="Assets/Scripts/")  # SmoothDamp follow
-> after each: poll editor/state, read_console(types=["error"])
```

`RunnerController`: `CharacterController.Move(forward*speed + laneShift + gravity)`; three lane X targets; jump = vertical velocity. `SwipeInput`: threshold primary-touch delta into Left/Right/Up. `Obstacle.OnTriggerEnter` (tag `Player`) → kill → respawn / `GameOver`. `Coin.OnTriggerEnter` → `GameEvents.RaiseScore`, release to pool.

### 3. Build prefabs (batch each, save)
```text
batch_execute(commands=[
  { manage_gameobject(action="create", name="Player", primitive_type="Capsule") },
  { manage_components(action="add", target="Player", component="CharacterController") },
  { manage_components(action="add", target="Player", component="RunnerController") },
  { manage_gameobject(action="set", target="Player", properties={ tag:"Player" }) },
], fail_fast=true)

batch_execute(commands=[
  { manage_gameobject(action="create", name="Coin", primitive_type="Cylinder") },
  { manage_components(action="add", target="Coin", component="SphereCollider",
      properties={ isTrigger:true }) },
  { manage_components(action="add", target="Coin", component="Coin") },
], fail_fast=true)
manage_prefabs(action="create", target="Coin", path="Assets/Prefabs/Coin.prefab")
# repeat for Obstacle + a track Chunk prefab
```

### 4. Wire the scene
```text
manage_gameobject(action="create", name="Director")
manage_components(action="add", target="Director", component="ChunkSpawner")       # pooled chunks/coins/obstacles
manage_components(action="add", target="Director", component="DifficultyManager")
manage_components(action="add", target="Main Camera", component="FollowCamera")    # target = Player
manage_components(action="add", target="Player", component="SwipeInput")
```
Spawner recycles chunks: when the player passes one, release it and place a new one ahead. Coins/obstacles come from pools.

### 5. Verify
```text
manage_editor(action="play")
read_console(types=["error"])
manage_scene(action="screenshot", include_image=true, max_resolution=512)   # player running, track ahead
# swipe to change lane, hit an obstacle -> respawn/restart
manage_editor(action="stop")
```
URP look + lighting via `unity-graphics`; HUD/score via `unity-ui-designer`; Cinemachine follow is an optional upgrade (`manage_packages` add, then `manage_camera` Tier-2). Optional `run_tests(mode="PlayMode")` asserting an obstacle hit triggers the respawn path.

---

## Notes that bite

- After every `create_script` / package change: domain reload (~5s) — re-poll `editor/state`, re-fetch SHA before `apply_text_edits`.
- On Unity 6: verify Input System touch/swipe and `CharacterController` APIs with `unity_reflect` before writing.
- Pool everything that spawns repeatedly (tiles, coins, obstacles, chunks, popups). No `Instantiate`/`Destroy` in the run loop.
- A screenshot of only gray primitives = slice proven, not premium. Swap in generated assets before any premium claim.
