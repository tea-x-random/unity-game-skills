# Unity Common Errors — symptom → cause → fix

Read the actual console (`read_console(types=["error"])`, then `["warning"]`) and the stack trace. Compile errors block everything — fix them before any scene/Play Mode work. Verify any Unity 6 (6000.x) API you write with `unity_reflect` / `unity_docs` (memory is ~2022.3).

## Compile / build

| Symptom | Likely cause | Fix |
|---|---|---|
| `CS####` compile error in console | Syntax error, wrong/changed API, missing `using`, asmdef reference missing | Open the named script+line; on Unity 6 verify the API via `unity_reflect`. Add the assembly reference in the `.asmdef`. Nothing else runs until clean. |
| "All compiler errors must be fixed before you can enter Play Mode" | Any compile error | Fix every error in console; Unity runs the **last good** build until then, so stale behavior is misleading. |
| Type exists in Editor, missing at runtime on device | IL2CPP managed-code **stripping** removed a reflection/serialization-only type | Add `Assets/link.xml` preserving the assembly/type, `[Preserve]` the member, or lower stripping level. (Route build steps to `unity-qa-release`.) |
| `ExecutionEngineException` / AOT error on iOS only | AOT can't JIT a runtime-only generic instantiation | Avoid runtime `MakeGenericType`/value-type generic surprises; reference the closed generic somewhere, or use AOT-friendly serialization. |

## Runtime null / missing references

| Symptom | Likely cause | Fix |
|---|---|---|
| `NullReferenceException` on a `[SerializeField]` field | Field never assigned in Inspector/prefab | Assign it in the Inspector (via MCP component edit), or guard with a null-check + clear error. |
| `NullReferenceException` after `GetComponent<T>()` | Component not on the object, or called before it exists | Cache in `Awake`, consume in `Start`; use `TryGetComponent`; add `[RequireComponent(typeof(T))]`. |
| `NullReferenceException` only sometimes / on first frame | **Script execution order** — dependency's `Awake` hasn't run yet | Set up self in `Awake`, read others in `Start`, or set Project Settings → Script Execution Order. |
| `MissingReferenceException: object has been destroyed` | Using a reference to a `Destroy`d GameObject/Component | Null-check after destroy; stop coroutines on destroy; **pool** instead of destroy/instantiate. |
| `MissingReferenceException` / "broken prefab" / field shows *Missing* | Prefab or script GUID changed (asset moved/renamed/deleted), broken prefab link | Re-link the reference; restore the script/asset; avoid hand-editing `.meta`/`.prefab` YAML (corrupts GUIDs) — go through MCP. |

## Materials / shaders / render

| Symptom | Likely cause | Fix |
|---|---|---|
| Pink / magenta materials | Shader didn't compile for active pipeline — Built-in/`Standard` shader in a URP project | Confirm `renderPipeline` (project/info); Edit → Rendering → Materials → Convert to URP, or set `Universal Render Pipeline/Lit`. |
| Objects black / unlit | URP Lit with no light, wrong lightmap, or missing main light | Add/enable a Directional Light; check ambient/environment lighting; bake if needed. |
| Shader warning / fallback in console | Variant stripped or unsupported keyword on mobile | Use a mobile-appropriate URP shader; check shader stripping settings. |

## Scene / camera

| Symptom | Likely cause | Fix |
|---|---|---|
| Blank / black scene | No camera, camera disabled, wrong culling mask, clear flags, or camera transform off-screen | Run `references/checklists/scene-debugging.md`. |
| Game runs but nothing visible | Wrong scene active/loaded, or objects far outside camera frustum (near/far clip) | Confirm active scene; check object positions vs camera. |
| Won't enter Play Mode (no compile error) | Exception thrown in `Awake`/`OnEnable` aborts entry | Read console for the runtime exception; fix it. |
| State leaks between Play sessions | "Enter Play Mode without Domain Reload" leaves stale statics | Reset statics in `OnEnable`/`RuntimeInitializeOnLoadMethod`, or re-enable domain reload. |

## Serialization / prefabs (subtle)

| Symptom | Likely cause | Fix |
|---|---|---|
| Serialized field **reset to default** after renaming it | Unity keys serialization by field name; rename loses the value | Add `[FormerlySerializedAs("oldName")]`, or rename via the field's old name preserved, then re-assign. |
| Prefab **override lost** after editing the prefab asset | Instance override conflicted/was reverted, or applied wrong direction | Use Overrides dropdown deliberately (Apply vs Revert); avoid editing prefab YAML by hand. |
| Inspector value differs from prefab unexpectedly | Unapplied instance override or nested-prefab override | Inspect Overrides; apply or revert intentionally through the Editor. |

## Asset loading

| Symptom | Likely cause | Fix |
|---|---|---|
| `Resources.Load<T>(path)` returns null | Asset not under a `Resources/` folder, wrong path/case, or no type match | Place under `Resources/`, use path without extension, exact case; prefer Addressables for mobile. |
| Addressables load returns null / `InvalidKeyException` | Address/label wrong, group not built into the player content, or catalog stale | Verify the address/label; build Addressables content; check the catalog; handle async completion before use. |
| `null` from async load used immediately | Read before the async op completed | `await` / yield on the handle; null-check the result. |
