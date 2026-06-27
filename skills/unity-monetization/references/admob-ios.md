# Google AdMob (iOS) via OpenUPM — what we shipped

Replaced Unity Ads direct with **Google AdMob** (GMA `com.google.ads.mobile` **11.2.0**) on Unity
6000.5.0f1, built-in render pipeline. Clean compile + archived/uploaded TestFlight build. The shipped
files: `Assets/<YourGame>/Scripts/Game/Net/Ads.cs` (facade), `.../Net/AdsManager.cs` (AdMob backend),
`Assets/<YourGame>/Scripts/Core/AdCadence.cs` (pure cadence) + `Tests/EditMode/AdCadenceTests.cs` (19 tests).

## Install via OpenUPM scoped registry

`Packages/manifest.json` — add the registry **and** the two deps:

```jsonc
"dependencies": {
  "com.google.ads.mobile": "11.2.0",
  "com.google.external-dependency-manager": "1.2.187"
},
"scopedRegistries": [
  {
    "name": "package.openupm.com",
    "url": "https://package.openupm.com",
    "scopes": [ "com.google.ads.mobile", "com.google.external-dependency-manager" ]
  }
]
```

- Package resolution requires the **Editor to be focused** to process the manifest change. Resolution can
  drop/timeout the MCP bridge — reconnect by clicking the Editor (`no_unity_session` → focus; see
  `unity-mcp-bridge`).

## The GMA runtime is PRECOMPILED DLLs — do NOT asmdef-reference it

The package ships `GoogleMobileAds.dll`, `GoogleMobileAds.Core.dll`, `GoogleMobileAds.Common.dll`,
`GoogleMobileAds.iOS.dll`, … as auto-referenced DLLs. The **only** asmdef in the package is
`GoogleMobileAds.Editor.asmdef` (editor code). Consequence:

- You **cannot** list `"GoogleMobileAds"` in your asmdef's `references` array — that array is for *other
  asmdefs* only, so it produces an unresolved-reference warning.
- With `overrideReferences: false` (the default — confirmed in `YourGame.Game.asmdef`), the auto-referenced
  DLLs resolve automatically. **The fix is to simply remove the bad reference.** `using GoogleMobileAds.Api;`
  then compiles. (YourGame.Game.asmdef references only `YourGame.Core` + `Unity.TextMeshPro`.)

## v11 callbacks: marshal to the main thread yourself

`MobileAds.RaiseAdEventsOnUnityMainThread` is **obsolete** in v11 (still works, but warns). Replacement:
wrap each SDK callback body in `GoogleMobileAds.Common.MobileAdsEventExecutor.ExecuteInUpdate(() => { ... })`.
SDK callbacks (Load completion, `OnAdFullScreenContentClosed`, `OnAdFullScreenContentFailed`) arrive on a
**background thread**; anything touching Unity APIs must be marshalled. The executor is initialized during
`MobileAds.Initialize`, so do the marshalling inside the Initialize callback too.

## App ID + ATT string via the settings asset (post-processor writes the plist)

`Assets/GoogleMobileAds/Resources/GoogleMobileAdsSettings.asset` is a
`GoogleMobileAds.Editor.GoogleMobileAdsSettings` ScriptableObject. Set:

- `GoogleMobileAdsIOSAppId` (serialized field `adMobIOSAppId`), e.g. `ca-app-pub-XXXX~YYYY`.
- `UserTrackingUsageDescription` (serialized field `userTrackingUsageDescription`) — **leave empty** for the
  non-personalized posture below.

The GMA iOS post-processor then writes `GADApplicationIdentifier`, `NSUserTrackingUsageDescription` (only if
set), and **~50 `SKAdNetworkItems`** into the built Info.plist automatically. **Your own
`[PostProcessBuild]` must NOT touch those keys** — GMA owns them, so there's no collision (contrast the
Unity-Ads path, where you wrote SKAdNetwork yourself).

There is **no `GoogleMobileAdsSettings.LoadInstance()`**. Create the asset via reflection:
`ScriptableObject.CreateInstance(type)` → `AssetDatabase.CreateAsset(...)` → set properties → save.

## iOS pods via EDM4U

The package's `GoogleMobileAdsDependencies.xml` declares `Google-Mobile-Ads-SDK ~> 13.4`; the UMP
`GoogleUmpDependencies.xml` declares `GoogleUserMessagingPlatform 3.1.0`. EDM4U writes both into the
generated `Build/iOS/Podfile`. The pipeline must run env-stripped `pod install` and build the
`.xcworkspace` → see `unity-qa-release` › fastlane/CocoaPods.

## Non-personalized ads (npa=1) — simplest privacy posture

```csharp
var req = new AdRequest();
req.Extras.Add("npa", "1");   // non-personalized: no advertising-identifier tracking
```

Do **not** request ATT; **clear** `UserTrackingUsageDescription` so `NSUserTrackingUsageDescription` isn't
written (the reference project also strips it defensively in `PostBuild.cs`). This avoids the ATT prompt entirely
and lets you declare "no tracking" in the privacy manifest + App Privacy questionnaire. Rationale: most
users decline ATT anyway, so personalization uplift is small for a casual game, and the review path is far
simpler.

## A brand-new AdMob app/unit serves NO real ads until approved + warmed up

This bit the team — set the expectation up front. Flipping `UseTestAds` true→false on a freshly created app
makes ads **disappear** (no-fill). Test ads (Google's test unit IDs, e.g. iOS interstitial
`ca-app-pub-3940256099942544/4411468910`) **always** work regardless of approval. Real ads require:

1. AdMob to **review/approve** the app — often only fully granted once the app is live on the App Store /
   linked to a store listing, and
2. the unit to **warm up** (hours to a couple days).

Pre-launch no-fill is **normal, not an integration bug**. For TestFlight QA either keep `UseTestAds=true` or
register your device as an AdMob test device (live unit serves test ads to that device only). Code must
handle no-fill gracefully — log + retry on the next opportunity, never block gameplay (the reference project's load-fail
path just `Debug.LogWarning`s and waits for the next finished game).

## The facade (network-swap = one file)

`Ads.cs` is a tiny static facade: `Ads.NotifyGameFinished()` → `Ads.GameFinishedHandler?.Invoke()`. The
`AdsManager` MonoBehaviour (added by `AppRoot`) registers the handler in `Start()` and clears it in
`OnDestroy()`. Off-device / before init the handler is null → every call is a safe no-op. Gameplay
assemblies (`YourGame.Game`) carry **zero** SDK dependency; swapping ad networks (Unity Ads → AdMob here)
was a one-file change to `AdsManager`. Trigger site is unchanged: `ResultOverlay.StartDifficulty` calls
`Ads.NotifyGameFinished()` only when `_cameFromResult` (the replay tap), never the cold-start menu.

## Interstitial lifecycle (the shipped shape)

```csharp
using GoogleMobileAds.Api;
using GoogleMobileAds.Common; // MobileAdsEventExecutor

MobileAds.Initialize(_ => MobileAdsEventExecutor.ExecuteInUpdate(() => { _initialized = true; LoadAd(); }));

InterstitialAd.Load(adUnitId, BuildRequest(), (ad, error) => MobileAdsEventExecutor.ExecuteInUpdate(() =>
{
    if (error != null || ad == null) { Debug.LogWarning($"[Ads] load failed: {error}"); return; } // retry next finish
    _interstitial = ad;
    ad.OnAdFullScreenContentClosed += OnAdClosed;   // preload the next one
    ad.OnAdFullScreenContentFailed += OnAdShowFailed;
}));

// show: guard CanShowAd(), then MarkShown ONLY here (see admob cadence in SKILL.md)
if (shouldShow && _interstitial != null && _interstitial.CanShowAd()) { _cadence.MarkShown(now); _interstitial.Show(); }
```

Always `Destroy()` the consumed ad (unsubscribe handlers first) and preload a fresh one on close/fail.
```
