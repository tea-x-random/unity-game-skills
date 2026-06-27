# iOS Build Pipeline (full ordered recipe)

Everything up to the Xcode project is done via `unity-mcp-bridge` (`manage_build`, `execute_code`). Everything after is **manual on macOS** and cannot be done through MCP. The MCP deliverable is an **Xcode project folder, not an `.ipa`**.

## 0. Preconditions

- Editor reachable: `mcpforunity://editor/state` → `ready_for_tools==true`, `is_compiling==false`, `is_domain_reload_pending==false`.
- Console clean: `read_console(types=["error","warning"])`.
- Enable groups you need: `manage_tools(action="enable_group", group="scripting_ext")` (for `execute_code` / ASTC), and `group="docs"` if you need to verify a `manage_build` property on Unity 6.

## 1. Switch platform to iOS

```text
manage_build(action="platform", target="ios")
```

Wait for the switch (it can trigger a reimport/domain reload). Re-check editor state before continuing.

## 2. Player settings

```text
manage_build(action="settings", property="bundle_id",    value="com.you.mygame")
manage_build(action="settings", property="product_name", value="My Game")
manage_build(action="settings", property="company_name", value="You")
manage_build(action="settings", property="version",      value="1.0.0")
```

- `bundle_id` must match the App Store Connect app and the provisioning profile.
- Set the **build number** separately if your `manage_build` exposes it; otherwise it is set later in Xcode.

## 3. Scripting backend — IL2CPP (required)

iOS **requires IL2CPP**; Mono is not a valid iOS backend. Set it before building (this triggers a domain reload — expect the ~5s drop):

```text
set scripting_backend="il2cpp"     # via manage_build settings / player settings
```

Confirm it actually took before relying on it. On Unity 6 the property name/path may differ from older versions — verify via `unity_docs`/`unity_reflect` if the call is rejected.

## 4. Add scenes to the build

```text
manage_build(action="scenes", ...)    # list/add/order enabled scenes
```

The **first enabled scene is the launch scene**. Make sure every scene the loop needs is enabled, in order.

## 5. Verify ASTC texture compression (known bug — do NOT trust defaults)

There is a known build-path bug that can force the **wrong texture compression** for iOS. Set/verify **ASTC** explicitly per texture via `execute_code` driving `TextureImporter` platform overrides. Example to verify + fix all textures for the iOS platform:

```csharp
// execute_code (scripting_ext group). Reviews iOS overrides; flips non-ASTC to ASTC_6x6.
using UnityEditor;
using UnityEngine;
using System.Text;

var sb = new StringBuilder();
foreach (var guid in AssetDatabase.FindAssets("t:Texture2D"))
{
    var path = AssetDatabase.GUIDToAssetPath(guid);
    var imp = AssetImporter.GetAtPath(path) as TextureImporter;
    if (imp == null) continue;

    var ios = imp.GetPlatformTextureSettings("iPhone");
    bool isAstc = ios.format == TextureImporterFormat.ASTC_4x4
               || ios.format == TextureImporterFormat.ASTC_6x6
               || ios.format == TextureImporterFormat.ASTC_8x8;

    if (!ios.overridden || !isAstc)
    {
        ios.overridden = true;
        ios.format = TextureImporterFormat.ASTC_6x6;   // good default for casual art
        imp.SetPlatformTextureSettings(ios);
        imp.SaveAndReimport();
        sb.AppendLine("FIXED -> ASTC_6x6: " + path);
    }
}
Debug.Log(sb.Length == 0 ? "All iOS textures already ASTC." : sb.ToString());
```

Read the logged output — that log is your evidence ASTC is correct. Do not call the build good until you've seen it.

## 6. Managed stripping + link.xml

IL2CPP strips unused managed code. Anything resolved by **reflection / name / serialization** can be stripped out and fail only on device. Add an `Assets/link.xml` preserving those types, e.g.:

```xml
<linker>
  <assembly fullname="Assembly-CSharp">
    <type fullname="MyGame.SaveData" preserve="all"/>
    <type fullname="MyGame.LevelConfig" preserve="all"/>
  </assembly>
  <assembly fullname="Newtonsoft.Json" preserve="all"/>
</linker>
```

Stripping bugs do not appear in the Editor — they appear in the IL2CPP build. Test the actual build.

## 7. Build the Xcode project

```text
manage_build(action="build", target="ios", output_path="Builds/iOS/MyGame")
manage_build(action="status")     # poll until finished
```

- On Unity 6 you may use a Build Profile via the `profile` param; **Build Profiles require Unity 6+**. On older Unity, do not pass `profile` — the direct platform/settings/scenes flow above is the path.
- A returned path is **not** proof of success. Poll `action="status"` until it reports finished with no errors, and confirm the output folder exists.
- **Output = Xcode project folder, not `.ipa`.**

## 8. MANUAL — macOS / Xcode (cannot be done via MCP)

State this as a manual gate. A human on macOS must:

1. Open the generated Xcode project (`Builds/iOS/MyGame/Unity-iPhone.xcodeproj` or the workspace).
2. In **Signing & Capabilities**: select the **team**, the **provisioning profile**, confirm the **bundle id** matches App Store Connect.
3. Archive and export:
   ```bash
   xcodebuild -project Unity-iPhone.xcodeproj -scheme Unity-iPhone \
     -configuration Release -archivePath build/MyGame.xcarchive archive
   xcodebuild -exportArchive -archivePath build/MyGame.xcarchive \
     -exportPath build/ipa -exportOptionsPlist ExportOptions.plist
   ```
4. Upload to **TestFlight / App Store Connect** via Xcode Organizer or `xcrun altool` / `notarytool`.

## Truthful status language

- Done via MCP: "Xcode project generated at `<path>`, status finished, ASTC verified, IL2CPP set."
- NOT done (manual): signing, archive, `.ipa`, TestFlight upload, App Store review.
- Never say "built / signed / on TestFlight / shipped" unless a human ran step 8 and you have the output.
