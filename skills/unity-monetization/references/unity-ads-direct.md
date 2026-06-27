# Unity Ads direct (`com.unity.ads` 4.17) — listener lifecycle

The annotated shape we shipped in `Assets/<YourGame>/Scripts/Game/Net/AdsManager.cs`. One sealed
`MonoBehaviour` implements all three listener interfaces; nothing else in the game references the ad SDK.

## Package + asmdef

- `Packages/manifest.json`: `"com.unity.ads": "4.17.0"` ("Advertisement Legacy" in Package Manager).
- Namespace: `using UnityEngine.Advertisements;`
- The asmdef of the code that calls it must reference `UnityEngine.Advertisements` (add it to your
  gameplay asmdef, e.g. `YourGame.Game.asmdef`).

## The class

```csharp
public sealed class AdsManager : MonoBehaviour,
    IUnityAdsInitializationListener, IUnityAdsLoadListener, IUnityAdsShowListener
{
    private const string IosGameId           = "<YOUR_IOS_GAME_ID>"; // dashboard -> Monetization -> iOS Game ID (per-platform!)
    private const string InterstitialPlacement = "Interstitial_iOS"; // default iOS interstitial placement
    private const bool   TestMode            = true;        // test ads until launch (works on TestFlight)

    private const int    GamesPerAd          = 2;           // show on every Nth finished game
    private const float  MinSecondsBetweenAds = 45f;        // ...and never closer than this

    public static AdsManager Instance { get; private set; }
    public static string Status = "not started"; // piped to the on-device debug HUD

    private static bool Configured => !IosGameId.StartsWith("REPLACE"); // no-op until a real id is pasted
```

## Bootstrap: device-only, no-op until configured

```csharp
[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
private static void Bootstrap()
{
    if (Application.platform != RuntimePlatform.IPhonePlayer &&
        Application.platform != RuntimePlatform.Android) return;   // device only
    if (!Configured || Instance != null) return;                   // and only when a real Game ID is set

    var go = new GameObject("Ads");
    DontDestroyOnLoad(go);
    Instance = go.AddComponent<AdsManager>();
}
```

This is the key safety property: in the Editor, in tests, and in an unconfigured build, the SDK is never
touched and no other code path depends on it.

## Init → Load → Show

```csharp
private void Start()
{
    if (!Advertisement.isInitialized && Advertisement.isSupported)
        Advertisement.Initialize(IosGameId, TestMode, this);   // (gameId, testMode, initListener)
}

public void OnInitializationComplete()                  => LoadInterstitial();
public void OnInitializationFailed(UnityAdsInitializationError e, string m) { Status = "INIT FAIL: " + e + " " + m; }

private void LoadInterstitial() => Advertisement.Load(InterstitialPlacement, this); // (adUnitId, loadListener)

public void OnUnityAdsAdLoaded(string adUnitId) { /* ready */ }
public void OnUnityAdsFailedToLoad(string adUnitId, UnityAdsLoadError e, string m)
{
    Status = "LOAD FAIL: " + e + " " + m;   // e == INTERNAL_ERROR with valid id => project setup, see SKILL.md
}

public void ShowInterstitial()
{
    if (loaded) Advertisement.Show(InterstitialPlacement, this); // (adUnitId, showListener)
}

// show listener — preload the next one on complete OR failure
public void OnUnityAdsShowComplete(string adUnitId, UnityAdsShowCompletionState s) => LoadInterstitial();
public void OnUnityAdsShowFailure(string adUnitId, UnityAdsShowError e, string m)  => LoadInterstitial();
public void OnUnityAdsShowStart(string adUnitId) { }
public void OnUnityAdsShowClick(string adUnitId) { }
```

## Frequency cap (counts even when no ad is ready)

```csharp
public void OnGameFinished()
{
    _gamesSinceAd++;
    if (_gamesSinceAd < GamesPerAd) return;                                    // not Nth yet
    if (Time.realtimeSinceStartup - _lastAdTime < MinSecondsBetweenAds) return; // too soon
    if (!_interstitialLoaded) return;                                          // nothing ready (but count stays)
    _gamesSinceAd = 0;
    _lastAdTime = Time.realtimeSinceStartup;
    Advertisement.Show(InterstitialPlacement, this);
}

public static void NotifyGameFinished() => Instance?.OnGameFinished(); // null off-device -> no-op
```

## Trigger site (never over the result UI)

In `ResultOverlay.StartDifficulty` (the replay tap), only when replaying after a finished game:

```csharp
if (_cameFromResult) YourGame.Net.AdsManager.NotifyGameFinished();
```

`_cameFromResult` is set true in `Show(GameResult)` (win/lose card) and false in `ShowMenu()` (cold start),
so the interstitial fires on replay — at the natural break — and never from the launch menu or mid-puzzle.

## Rewarded ads (same shape)

Rewarded uses the identical `Load`/`Show` listener flow with a rewarded placement; grant the reward in
`OnUnityAdsShowComplete` **only** when `showCompletionState == UnityAdsShowCompletionState.COMPLETED`
(the player watched to the end), not on `SKIPPED`.
