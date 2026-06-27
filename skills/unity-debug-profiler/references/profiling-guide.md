# Unity Profiling Guide (casual iOS, via MCP)

Profile from real numbers, not intuition. Enable the group, capture a baseline, change one thing, re-measure the same scenario.

## Enable + read via MCP

```text
manage_tools(action="enable_group", group="profiling")   # gives manage_profiler
manage_profiler(...)        # CPU/GPU timings, GC alloc, memory by category
manage_graphics(...)        # render stats: draw calls, batches, SetPass, triangles, verts
```

Order of operations: be in the right mode (Play Mode, ideally a development build; Editor-only numbers under-report mobile cost), reproduce the heavy scenario, sample a steady window (not the first frame — JIT/load spikes), then read.

## Frame-budget math (60fps)

- 60fps → **16.6 ms** total CPU+GPU budget per frame. 30fps → 33.3 ms.
- The frame is gated by the **slower** of CPU main thread and GPU. If main-thread script+physics ≈ 14 ms, you have ~2.6 ms of headroom regardless of GPU.
- Decide CPU-bound vs GPU-bound first: if main-thread time tracks frame time, optimize scripts/physics/GC; if GPU time dominates, optimize draw calls/overdraw/shaders/fill.
- On mobile, leave headroom — a 16.6 ms cold frame becomes a dropped frame once the device throttles.

## Baseline to capture

FPS / frame time (CPU + GPU split), draw calls, batches, SetPass calls, triangles, verts, GC alloc per frame, total memory, texture memory. Record before any change so "faster" is provable.

## Draw-call / batching reduction (GPU/CPU)

- **SetPass calls** are the real cost driver — each material/shader-state switch is a SetPass. Fewer materials = fewer SetPass.
- **Texture atlasing / Sprite Atlas (2D):** combine many textures into one atlas so many sprites share one material and batch together.
- **Material sharing:** reuse one material instance across objects; touching `.material` clones it (breaks batching) — use `.sharedMaterial` or MaterialPropertyBlocks.
- **GPU instancing:** enable on the material for many copies of the same mesh+material (obstacles, coins, crowd) — one draw call for the batch.
- **Static batching:** mark non-moving geometry **Static**; Unity combines it (costs memory, saves draw calls).
- **SRP Batcher (URP):** keep it enabled and use SRP-Batcher-compatible shaders (URP/Lit, URP/Unlit) so per-object setup is cheap; avoid per-object material variants that break it.
- **Culling / fewer objects:** smaller frustum/far clip, occlusion, LOD, and merging tiny meshes all cut both draw calls and triangles.

## GC-allocation hunting (CPU hitches)

Target **zero allocations per frame in steady state**. Per-frame GC causes spikes that show as frame hitches. Common offenders:

- `new` in `Update`/`FixedUpdate`/`OnGUI` (lists, arrays, classes, `Vector3[]`).
- LINQ (`Where`/`Select`/`ToList`), `foreach` over some collections, closures capturing variables.
- Boxing (value type → `object`, e.g. into non-generic APIs), string concatenation, `string`-keyed lookups built per frame.
- Uncached `GetComponent`/`FindObjectOfType`/`Camera.main` in hot paths.
- Allocating delegates/lambdas per frame; `params` arrays.

Fixes: cache references in `Awake`; pool objects instead of Instantiate/Destroy; pre-size and reuse collections; avoid LINQ in hot paths; use `StringBuilder`/cached strings; pass structs by `in`/`ref`. Re-read the profiler GC Alloc column to confirm it dropped to ~0.

## Mobile memory & texture budgets

- iOS terminates apps over the device memory budget — watch total + texture memory in `manage_profiler`.
- Textures: **ASTC** compression for iOS, sensible max sizes, mipmaps for 3D, no needless RGBA32 atlases. (Build pipeline has a known wrong-compression bug — set/verify ASTC yourself via `execute_code`/`TextureImporter`.)
- Audio, large meshes, and uncompressed render targets also eat the budget; prefer streaming/Addressables for big content.
- **Overdraw**: stacked transparent/UI/particle layers re-shade the same pixels — a top mobile GPU cost. Reduce transparent overlap and particle fill.

## Thermal throttling (sustained-load)

The device downclocks CPU/GPU after minutes of sustained load, so peak-fps numbers lie. Profile a **sustained** session, leave frame-budget headroom, cap effects, and reduce steady-state CPU/GPU so the throttled clock still holds 60 (or a stable 30).

## On-device profiling

For numbers that match shipping reality, build a **development / autoconnect-profiler** player to the iOS target and connect the Unity Profiler to the device over USB/Wi-Fi. Editor profiling is directional only; thermal, memory ceilings, and ASTC effects are device-real.
