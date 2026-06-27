# iOS ATT + SKAdNetwork via PostProcessBuild

The Unity iOS Xcode project is **regenerated every build**, so any Info.plist key you'd set by hand in
Xcode is gone next build. Re-apply them from a `[PostProcessBuild]` editor script wrapped in `#if UNITY_IOS`
(the `UnityEditor.iOS.Xcode` namespace only exists with the iOS Build Support module + iOS target active —
an unguarded script breaks compilation on other platforms).

This project already has such a script at `Assets/<YourGame>/Editor/PostBuild.cs` (it injects the
privacy manifest, export-compliance flag, and entitlements). Add the ad keys to the same callback.

## Why each key

- **`NSUserTrackingUsageDescription`** (string) — the human-readable reason shown in the **ATT** prompt.
  Required by App Review if you present ATT; present the prompt **before** any IDFA-based tracking. Even ad
  SDKs that can run in a limited/non-tracking mode want this when you intend to request tracking.
- **`SKAdNetworkItems`** (array of dicts, each `{ SKAdNetworkIdentifier = "<id>.skadnetwork" }`) — the ad
  networks allowed to attribute installs via SKAdNetwork. Get the current ID list from your ad source
  (Unity Ads / your mediator publishes it) and write one dict per network ID. Stale/missing IDs silently
  cost attribution; refresh when the network updates the list.

## Snippet (inside the existing `OnPostprocessBuild`, after `plist.ReadFromFile`)

```csharp
// --- ATT prompt copy ---
plist.root.SetString(
    "NSUserTrackingUsageDescription",
    "We use your data to show you more relevant ads.");

// --- SKAdNetwork attribution IDs (get the current list from your ad network) ---
var skan = plist.root.CreateArray("SKAdNetworkItems");
foreach (var id in new[] {
    "4dzt52r2t5.skadnetwork", // Unity Ads — example; pull the live list from the dashboard
    // ...add the rest the network publishes...
})
{
    var item = skan.AddDict();
    item.SetString("SKAdNetworkIdentifier", id);
}

plist.WriteToFile(plistPath); // the existing script already reads/writes Info.plist here
```

`PlistDocument`, `CreateArray`, `AddDict` are all `UnityEditor.iOS.Xcode` — already imported by the guarded
script. No hand-editing of the generated project; this runs on every iOS build so the keys always survive.

## Presenting the ATT prompt at runtime

Plist copy alone doesn't show the prompt. Call Apple's `ATTrackingManager.requestTrackingAuthorization`
(via Unity's iOS ATT support / `Unity.Advertisement.IosSupport.ATTrackingStatusBinding`, or a small native
plugin) once, before initializing tracking-dependent ad behavior. Respect the result — if the user denies,
the IDFA is zeroed and you fall back to SKAdNetwork attribution only.

## Where the rest lives

- **CocoaPods / `pod install` / build the `.xcworkspace`** (Unity Ads 4.17 ships the `UnityAds` pod via
  EDM4U) → `unity-qa-release` › fastlane/CocoaPods.
- **`PrivacyInfo.xcprivacy`** (required-reason APIs, IDFA/tracking declaration once ads are live) →
  `unity-qa-release` › App Store readiness. With ads, `NSPrivacyTracking` and the collected-data section
  are no longer trivially "false/empty" — revisit that checklist when a real ad path ships.
- **On-device HUD** to see ATT/ad SDK state on the device → `unity-mcp-bridge` (OnGUI diagnostics).
