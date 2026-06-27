# Headless iOS build via MCP + on-device diagnostics

Companion to the SKILL.md section of the same name. Covers (1) kicking off a full iOS Xcode-project build through MCP via a static build method and polling for completion, (2) surviving the `no_unity_session` drop that back-to-back builds cause, and (3) the temporary on-device IMGUI debug HUD pattern for failures that have no Editor console.

Grounded in a reference project: `Assets/<YourGame>/Editor/BuildScript.cs` and `Assets/<YourGame>/Scripts/Game/Net/DebugHud.cs`.

---

## 1. Trigger an iOS build through a static method, not the `build` tool

For a CI-shaped, fully-scripted iOS build, author one Editor entry point that does the whole sequence (target switch, signing, scenes, `BuildPipeline.BuildPlayer`) and invoke it from `execute_code`. This is the same method `Unity -batchmode -executeMethod ...` uses on CI, so the MCP path and the CI path stay identical.

### The build entry point

`Assets/<YourGame>/Editor/BuildScript.cs` exposes `public static void YourGame.EditorTools.BuildScript.PerformiOSBuild()`. It:

- reads optional env vars (`TEAM_ID` → automatic signing, `BUILD_NUMBER` → `PlayerSettings.iOS.buildNumber`, `BUILD_PATH` → output folder, default `Build/iOS`);
- switches the active build target to iOS if needed (`EditorUserBuildSettings.SwitchActiveBuildTarget` — itself a domain-reload trigger);
- collects enabled scenes from `EditorBuildSettings.scenes`;
- calls `UnityEditor.BuildPipeline.BuildPlayer(options)`;
- logs a single result line and, on non-`Succeeded`, calls `EditorApplication.Exit(1)` (so fastlane/CI fails the lane):

```text
[BuildScript] iOS build Succeeded -> Build/iOS (0 errors, 12 warnings, 48271360 bytes)
```

It also has a `[MenuItem("<YourGame>/Build iOS Xcode Project")]` wrapper so a human can run it from the Editor menu when MCP is down.

### Invoke it from MCP

```text
manage_tools(action="enable_group", group="scripting_ext")   # execute_code lives here
execute_code(code="YourGame.EditorTools.BuildScript.PerformiOSBuild();")
```

`execute_code` here is **C# 6 / CodeDom** — fully-qualified names only, no `using`, no C#7+ syntax, no JS-isms (`Date.now`, `Math.random`). A bare static call like the above is fine. (Same constraints documented in SKILL.md › "`execute_code` is a C# 6 method body via CodeDom".)

### Why you must POLL, not read the return value

`BuildPipeline.BuildPlayer` runs **synchronously on the Editor main thread** and blocks it for the duration of the build. The MCP request can't get a response while the main thread is busy, so:

> The `execute_code` call **times out / returns no result (`success:false, data:null`) even when the build ultimately succeeds.** The build keeps running on the main thread after the tool has given up.

Scope note: Unity's iOS "build" here is **only the Xcode-project generation** — it's fast (~10–20s for an incremental export, longer on a clean export). The heavy native compile/link happens **later in Xcode / fastlane**, not in this step. So the blocking window is short; the point is just that you can't read the result from the tool return.

**Call it synchronously — don't defer via `EditorApplication.delayCall`.** It's tempting to schedule the build off the MCP call so the call returns cleanly, but `delayCall` is unreliable here: a domain reload from a concurrent asset import / recompile can clear the pending `delayCall` before it fires, and the build silently never happens. A direct synchronous call (`PerformiOSBuild();`) is more deterministic — accept the timed-out return and poll for completion instead.

Do not interpret a timed-out / empty `execute_code` result as failure, and do not interpret any return as success. Treat the call as fire-and-forget, then poll two independent signals:

1. **Output `Info.plist` mtime.** The generated Xcode project writes `<output>/Info.plist` (e.g. `Build/iOS/Info.plist`). A *fresh* mtime (newer than when you launched the build) means the build finished writing the Xcode project. You have filesystem access, so `stat`/`ls -l` it directly, or before launching record the old mtime and wait for it to change.
2. **`read_console` for the result line.** Once the bridge is responsive again, `read_console(types=["log","error"])` and look for the `[BuildScript] iOS build <result> -> ...` line. This is the source of truth for success vs failure — in an **open** Editor a failed build only logs `Failed`/`Cancelled` (the `EditorApplication.Exit(1)` path is a batchmode/CI behavior), so a failure will *not* crash the Editor; you must read the result string.

Suggested loop: after firing `execute_code`, wait, then alternate (a) `stat` the output plist and (b) `read_console`, until either the plist mtime advances + console shows `Succeeded`, or console shows `Failed`/`Cancelled` (then `read_console(types=["error"])` for the build errors).

---

## 2. `no_unity_session` under back-to-back builds — focus the Editor to recover

The bridge drops during long compiles, domain reloads, and **especially under heavy/repeated iOS builds + package resolution.** Any heavy *main-thread* work — the synchronous `BuildPipeline.BuildPlayer`, or an **OpenUPM / EDM4U package import or resolve** — makes the bridge unresponsive; you'll see errors like "WebSocket is not initialised" / "Unexpected receive error". The Editor process stays alive, but MCP tools begin returning:

```text
no_unity_session   ("Unity session not available")
```

This is distinct from the ~5s domain-reload connection blip in the main reliability list — under repeated builds and package resolution it recurs and lingers. The Python/WebSocket session to the live Editor has gone stale.

**Recovery: try `refresh_unity` first, then fall back to the user focusing the Editor.** `refresh_unity` often reconnects on its own — it reports "Refresh recovered after Unity disconnect/retry". When `refresh_unity` itself times out, the user must **click/focus the Unity Editor window** to let it re-pump and re-establish the session.

Operational rules:
- When you get `no_unity_session`, **don't hammer retries**. Pause. Try one `refresh_unity`.
- If `refresh_unity` doesn't recover, **explicitly tell the user you need them to click / focus the Unity Editor window**, then wait.
- After recovery, re-read `mcpforunity://editor/state` and require `ready_for_tools == true`, `is_compiling == false`, `is_domain_reload_pending == false` before resuming.
- Budget for several of these reconnect waits across a session of back-to-back iOS builds; it is expected, not a bug to fix.

### A backgrounded Editor won't resolve a `manifest.json` change

Editing `Packages/manifest.json` directly (adding a scoped registry, e.g. OpenUPM, or a new package) is **not resolved until the Editor is focused.** A backgrounded Editor won't process the manifest change: the package never appears in `Library/PackageCache`, and `packages-lock.json` stays unchanged until focus. After writing to the manifest, tell the user to focus the Editor, then confirm the package actually resolved (inspect `packages-lock.json`, or `manage_packages`) before depending on the new package — don't assume the edit took effect.

---

## 3. On-device debug HUD (temporary IMGUI) for device-only failures

Things that only break **on the physical device** — native iOS plugins, Game Center sign-in, App Attest, ad SDK lifecycle — produce **no Editor console**, so MCP `read_console` is blind to them. Surface the state on the device screen itself with a temporary IMGUI HUD.

Pattern (from `Assets/<YourGame>/Scripts/Game/Net/DebugHud.cs`):

- **A `MonoBehaviour` with `OnGUI`** that renders **static diagnostic strings**: auth state, display name, last native error, SDK status. The example game shows `GameCenter.IsAuthenticated`, `GameCenter.DisplayName`, `GameCenter.LastIdentityError`, `RemoteScoreClient.LastClientHash`, `RemoteScoreClient.LastSubmitMsg`, `AdsManager.Status`, and App Attest support.
- **Self-bootstrap on device only.** `[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]` creates a `DontDestroyOnLoad` GameObject and adds the component — but early-returns unless `Application.platform == RuntimePlatform.IPhonePlayer`, so it never shows in the Editor or on other platforms.
- **Offset below the safe area.** The notch / Dynamic Island clips the top of a top-anchored HUD. Compute the top inset from `Screen.safeArea`:
  ```csharp
  float top = (Screen.height - Screen.safeArea.yMax) + 8f; // safe-area top inset + pad
  ```
  (This was a real follow-up fix — the first version was cut off by the notch and had to be re-positioned.)
- **Tap to hide.** Hit-test the band against `Event.current.mousePosition` on `EventType.MouseDown`, toggle a `_visible` flag, and call `Event.current.Use()`. When hidden, draw a thin "▼ debug (tap)" strip so it can be brought back.
- **Plumb native error strings all the way through.** The HUD is only as useful as the data behind it: have the Swift/ObjC++ bridge write its failure text into a C# static (e.g. `GameCenter.LastIdentityError`) so the HUD shows the *actual* native error, not just a bool. (A follow-up fix also presented the Game Center login from the topmost view controller so the in-app sign-in button wasn't a no-op — the kind of thing you only catch once the HUD makes the state visible.)
- **It is TEMPORARY — remove it before release.** Document it as such in the file header.

### Minimal skeleton

```csharp
using UnityEngine;

public sealed class DebugHud : MonoBehaviour
{
    private bool _visible = true;
    private GUIStyle _style;
    private Texture2D _bg;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void Bootstrap()
    {
        if (Application.platform != RuntimePlatform.IPhonePlayer) return; // device only
        var go = new GameObject("DebugHud");
        DontDestroyOnLoad(go);
        go.AddComponent<DebugHud>();
    }

    private void OnGUI()
    {
        int fs = Mathf.Max(24, Mathf.RoundToInt(Screen.height * 0.018f));
        float top = (Screen.height - Screen.safeArea.yMax) + 8f; // below notch / Dynamic Island
        float h = Screen.height * 0.32f;
        if (_style == null)
        {
            _style = new GUIStyle(GUI.skin.label) { fontSize = fs, wordWrap = true,
                padding = new RectOffset(16, 16, 12, 12) };
            _style.normal.textColor = Color.white;
            _bg = Texture2D.whiteTexture;
        }

        var band = new Rect(0, top, Screen.width, _visible ? h : fs * 2f);
        if (Event.current.type == EventType.MouseDown && band.Contains(Event.current.mousePosition))
        { _visible = !_visible; Event.current.Use(); }

        GUI.color = new Color(0, 0, 0, _visible ? 0.7f : 0.4f);
        GUI.DrawTexture(band, _bg);
        GUI.color = Color.white;
        // Replace with your own static diagnostic strings (auth state, last native error, SDK status):
        GUI.Label(band, _visible ? "...diagnostics...\n(tap to hide)" : "▼ debug (tap)", _style);
    }
}
```

Swap the placeholder `GUI.Label` text for your real static fields, gate native-side writes into C# statics, and delete the whole file once the device behavior is verified.
