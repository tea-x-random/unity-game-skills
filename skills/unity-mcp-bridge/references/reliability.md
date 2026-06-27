# MCP for Unity — Reliability & Recovery

Load before any sequence that creates/edits scripts, adds/removes packages, changes the scripting backend, or runs a build. These are the failure modes that actually bite, distilled from the CoplayDev/unity-mcp issue tracker (issue numbers cited). Connection instability around domain reloads is the dominant pain point — design every multi-step flow to survive a mid-sequence drop.

## The domain-reload rule (most important)

Any of these triggers a Unity **domain reload**: compiling a new/edited C# script, adding/removing a package, changing the scripting backend, some asset imports. A domain reload:
- drops the MCP connection for ~5 seconds,
- invalidates any in-flight tool call,
- pauses tool readiness until the Editor finishes reloading.

Pattern to survive it:
1. Issue the change (e.g. `create_script`). Do **not** also call `refresh_unity` — create/edit already import+compile.
2. Poll `mcpforunity://editor/state` until `is_compiling==false`, `is_domain_reload_pending==false`, `ready_for_tools==true`. Expect the first poll(s) to fail/timeout during the drop — retry with backoff for ~10s.
3. `read_console(types=["error"])`. Only continue (e.g. AddComponent that references the new type) if clean.
4. If you held a file SHA, re-fetch with `get_sha` before `apply_text_edits` — the file may have been reimported (`stale_file`).

## Editor-state preconditions

- Read `mcpforunity://editor/state` before complex ops; `blocking_reasons` tells you why it's not ready.
- The Editor must be running and able to process. A modal "reload scripts?" / reimport dialog requiring a manual click will **stall the bridge** until clicked (#891). If a sequence hangs, ask the user to check the Editor for a dialog.
- Agents can appear to "sleep" after script changes (#814) — that's the reload drop; resume by re-polling editor/state.

## Connection / transport issues

- Prefer **HTTP** transport (`http://localhost:8080/mcp`). stdio is single-agent and degraded: custom tools not discovered (#837), tool-group visibility doesn't sync, stale workers across updates (#1090), repeated NetworkStream errors on macOS (#1187).
- macOS + HTTP can still drop the WebSocket (close 1005) on reload/test boundaries → `no_unity_session` (#1207). Reconnect and re-poll. Heavy **main-thread** work also stalls the session ("WebSocket is not initialised" / "Unexpected receive error"): a synchronous `BuildPipeline.BuildPlayer`, or an OpenUPM/EDM4U package import/resolve. Try `refresh_unity` first (it can report "Refresh recovered after Unity disconnect/retry"); if it times out, have the user **focus the Editor**. See `ios-build-and-device-diagnostics.md` §2.
- **A backgrounded Editor won't resolve a `manifest.json` edit.** Adding a scoped registry / package by editing `Packages/manifest.json` is not processed until the Editor is **focused** — the package never lands in `Library/PackageCache` and `packages-lock.json` stays unchanged until then. Confirm resolution before relying on the package.
- Orphaned python server / port collision after a domain reload (#1164); server shuts down when Unity closes (#1210). If `Connected` won't return, restart the Editor's MCP from the status panel.
- Multiple Editors open can cross-talk and act on the wrong project (#1023) — call `set_active_instance(instance="Name@hash")`.

## Known broken / not-implemented (don't rely on these)

- `manage_asset(action="import")` does **not** configure importer properties — "modifying importer properties before reimport is not fully implemented." Use `execute_code` driving `ModelImporter`/`AssetImporter` to set scale, rig type, material extraction, read/write, compression.
- iOS/Android `manage_build` forces wrong texture compression (Android PVRTC bug #1212; verify the iOS path too). Set **ASTC for iOS** explicitly via `execute_code` rather than trusting build defaults.
- ProBuilder `set_pivot` (doesn't persist) and `convert_to_probuilder` (throws) are documented broken.
- `execute_code` fails if the code arg has a BOM (U+FEFF) (#1186) — send clean UTF-8.
- Disabling the Physics module (#1172) or screencapture module (#1176) breaks compilation. Keep required modules enabled: physics, physics2d, animation, uielements, screencapture, imageconversion, unitywebrequest, newtonsoft-json, test-framework.

## Performance / token hygiene

- `manage_asset(action="search")` can hang Unity on large/whole-project searches (#1177). Always paginate small (`page_size≈25`) and `generate_preview=false`.
- `find_gameobjects` returns instance IDs only and is paginated — fetch details per-object as needed rather than dumping the hierarchy.
- Use `batch_execute` (≤25 commands) to cut round-trips 10–100×, but it's not transactional — `fail_fast=true` for dependent steps, and verify with a screenshot/console read after.

## Client note

Claude Code is the best-supported client. Codex/VS Code on Windows have tool-call/name-mismatch failures (#1215, #1193, #1019) — not your concern on macOS+Claude Code, but relevant if the user switches clients.
