# Ad cadence as a pure, testable policy

The recommended structure for ad-frequency capping: a **pure injectable-time policy** + a **thin SDK
shell**. Decide WHEN to show in an engine-free class that takes time as an argument; let the MonoBehaviour
own the real clock and the SDK. Shipped in the reference project as `Assets/<YourGame>/Scripts/Core/AdCadence.cs` (in the
engine-free `YourGame.Core` assembly) with 19 green EditMode tests in
`Tests/EditMode/AdCadenceTests.cs`. Generalizes to rewarded/banner cadence too.

## Dual OR trigger

Show when **(games-since-last-ad ≥ N)** OR **(seconds-since-last-ad-or-app-open ≥ T)**. The count trigger
monetizes quick back-to-back sessions; the time trigger monetizes a single long session. The reference project ships
`GamesPerAd = 2`, `MinSessionGapSeconds = 300` (5 min). The time boundary is **inclusive** (`>=`).

```csharp
public bool ShouldShow(double now)                // pure read, no mutation
{
    bool countTrigger = _gamesSinceAd >= GamesPerAd;
    bool timeTrigger  = (now - _baselineTime) >= MinSessionGapSeconds;
    return countTrigger || timeTrigger;
}
```

## Injected time, deterministic

The policy never reads a clock — `now` (seconds) is passed in. The MonoBehaviour supplies
`Time.realtimeSinceStartupAsDouble`. That makes every case a plain unit test (no Play Mode, no SDK).

## Separate the DECISION from the COMMIT (the "owed ad")

- `RegisterGameFinishedAndShouldShow(now)` increments the counter and returns whether to show.
- `MarkShown(now)` resets both triggers — call it **only when an ad actually displays**.

If the ad isn't loaded yet, you take the decision but **don't** `MarkShown`, so the counter keeps climbing
and the "owed ad" fires as soon as one is ready. A not-yet-loaded ad must never reset the counters.

```csharp
bool shouldShow = _cadence.RegisterGameFinishedAndShouldShow(now);
if (shouldShow && _interstitial != null && _interstitial.CanShowAd())
{
    _cadence.MarkShown(now);    // commit ONLY on real display
    _interstitial.Show();
}
else if (_interstitial == null) LoadAd(); // owed — queue one for next time
```

`MarkAppOpen(now)` resets only the time baseline (return-to-foreground restarts the idle clock) and keeps
the count.

## What the 19 tests cover

Ctor validation (GamesPerAd ≥ 1, gap ≥ 0); count trigger (incl. custom N); time trigger (single long game,
inclusive 300s boundary, just-under, measured-from-app-open-not-zero); resets after `MarkShown` (count and
time independently); the **owed-ad** (decision true but not shown → still owed, counter climbs);
`ShouldShow` is a pure non-mutating read; `MarkAppOpen` resets time but keeps count; both triggers at once
shows once; and three realistic sessions (quick games → ad every 2; one 7-min solve → exactly one;
leisurely ~4-min games → time trigger carries it). All green.
