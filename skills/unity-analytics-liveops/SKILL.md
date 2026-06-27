---
name: unity-analytics-liveops
description: "Instrument, measure, and live-tune casual iOS games built in Unity so 'playable' becomes 'retentive and monetizable.' Use for analytics and retention instrumentation (D1/D7/D30 retention funnels, session length/count, ARPDAU, ad-ARPDAU, IAP conversion, rewarded-ad engagement, onboarding/first-session funnels), choosing and wiring an analytics SDK (Unity Gaming Services Analytics, GameAnalytics, Firebase Analytics), crash reporting (Crashlytics, Unity Cloud Diagnostics), remote config + server-driven A/B testing (tune difficulty, ad cadence, onboarding and paywall variants WITHOUT resubmitting to the App Store), soft-launch measurement (validate retention/ARPDAU in a small geo before global UA), and iOS-specific measurement (ATT prompt timing, SKAdNetwork/AdAttributionKit conversion values, privacy-manifest data-collection disclosures for analytics SDKs). Triggers on: analytics, retention, D1/D7/D30, ARPDAU, KPIs, funnel, onboarding metrics, remote config, A/B test, experiment, feature flag, crash reporting, Crashlytics, GameAnalytics, Unity Gaming Services, Firebase, soft launch, liveops, attribution, SKAdNetwork, AdAttributionKit, conversion value, paywall test, difficulty tuning. Pairs with unity-monetization (tune ad frequency by measured ARPDAU/retention, not a fixed number), unity-gameplay-systems (onboarding/find-the-fun instrumentation), and unity-qa-release (privacy manifest, ATT, soft-launch readiness)."
---

# Unity analytics & liveops

The levers that turn a *playable* casual game into a *retentive and monetizable* one are mostly **measurement and iteration**, not more features. A game ships, you watch D1/D7/D30 retention and ARPDAU, and you tune the difficulty curve, onboarding, and ad cadence against real numbers. This skill covers how to instrument that loop in a Unity casual iOS game and how to act on it.

> **You cannot improve what you do not measure.** Retention is largely set *before* user acquisition — by whether players find the fun, get guided to it, and hit low onboarding friction ([Solsten — D1/D7/D30 retention](https://solsten.io/blog/d1-d7-d30-retention-in-gaming)). Instrument the first session first.

## Doctrine

1. **Instrument before you tune.** Don't guess at difficulty or ad frequency — wire analytics, ship a soft launch, read the funnel, then change one thing.
2. **Gate tunables behind remote config.** Difficulty constants, ad cadence, onboarding variants, and paywall copy should be server-driven so you can change them without an App Store resubmission (review takes days; a config flip is instant).
3. **Change one variable at a time (A/B).** Attribute a retention/ARPDAU move to a single change or you learn nothing.
4. **Measure ad frequency against retention + ARPDAU.** Over-serving ads hurts BOTH retention and eCPM, so "more ads ≠ more revenue" ([Tap-Nation — hybrid-casual KPIs](https://www.tap-nation.io/blog/kpis-that-matter-metrics-to-track-in-hybrid-casual-games/)). Tune cadence empirically; do not hardcode a "correct" number.
5. **Privacy is a build gate on iOS.** Every analytics/attribution SDK adds data-collection that must be declared in the privacy manifest and respect ATT. Wire this with `unity-qa-release`, not as an afterthought.

## What to measure (the casual KPI set)

Wire these events/metrics from day one. Benchmarks are *targets to converge toward*, not guarantees.

| Metric | Why it matters | Hybrid-casual reference |
|--------|----------------|--------------------------|
| **D1 / D7 / D30 retention** | The core health signal; set pre-acquisition | D7 ~20%, D30 ~10% (hypercasual D30 ≈ 0) ([Gamigion 2025](https://www.gamigion.com/2025-hybridcasual-market-overview-with-real-data/)) |
| **Onboarding / first-session funnel** | Where new players drop before "the fun" | Instrument each step; find-the-fun is the #1 D1 lever |
| **Session length & sessions/day** | Engagement depth | Track trend, not an absolute |
| **ARPDAU** (total) | Revenue health per active user | Compare across A/B arms |
| **Ad ARPDAU + impressions/DAU** | Ad-revenue intensity vs. fatigue | Watch retention as you raise frequency |
| **IAP conversion %** | Share of payers | Only ~1.8% of F2P players ever buy IAP ([Game Growth Advisor](https://gamegrowthadvisor.com/blog/2026-04-02-f2p-monetization-models-comparison-2026/)) — so hybrid (ads + IAP) is the default model |
| **Rewarded engagement** (opt-in rate, completions/DAU) | Rewarded video is the core casual format | Highest-eCPM format; design natural rewarded placements ([TopOn H1 2025](https://mores.toponad.com/reports/TopOn%20Global%20Mobile%20Games%20Monetization%20Report%20_%202025%20H1.pdf)) |

> Treat published eCPM dollar figures and "X ads per session" rules as unreliable — they vary by quarter, geo, network, and report scope. Measure your own.

## Pick your stack (one each, don't double-count)

For a Unity casual iOS game, choose **one analytics + one crash + one remote-config/A-B** provider and avoid wiring two analytics SDKs that double-count sessions.

- **Analytics:** [Unity Gaming Services Analytics](https://docs.unity.com/ugs/manual/analytics/manual/overview) (native to Unity), [GameAnalytics](https://docs.gameanalytics.com/) (free, casual-games-focused, built-in funnels), or [Firebase Analytics](https://firebase.google.com/docs/analytics) (broad ecosystem).
- **Crash/diagnostics:** [Firebase Crashlytics](https://firebase.google.com/docs/crashlytics) or [Unity Cloud Diagnostics](https://docs.unity.com/ugs/manual/cloud-diagnostics/manual/UnityCloudDiagnostics).
- **Remote config + A/B:** [Unity Remote Config](https://docs.unity.com/ugs/manual/remote-config/manual/WhatsRemoteConfig) (+ Game Overrides/A-B) or [Firebase Remote Config + A/B Testing](https://firebase.google.com/docs/remote-config).
- **Attribution (only if running paid UA):** AppsFlyer, Adjust, Singular, or Tenjin — these own the SKAdNetwork/AdAttributionKit postback handling.

See `references/sdk-integration.md` for Unity import, asmdef/EDM4U, and iOS wiring notes.

## Remote config + A/B workflow

1. **Externalize tunables.** Move difficulty constants, ad-cadence parameters (the values consumed by `unity-monetization`'s cadence policy), onboarding flags, and paywall strings out of code into remote config keys with safe in-code defaults (so the game works offline / before first fetch).
2. **Fetch early, apply safely.** Fetch on launch; fall back to the bundled defaults if the fetch fails. Never block the first session on a network call.
3. **Run one experiment at a time.** Define a hypothesis ("variant B's gentler early difficulty raises D1"), split users server-side, and read the one KPI it should move. Keep a holdout.
4. **Promote or kill.** Roll the winning arm to 100% via config; no client update needed.

## Soft-launch before global

Validate retention and ARPDAU in a small, representative geo before scaling user acquisition:

1. Ship to a limited region with full analytics wired.
2. Read D1/D7, onboarding funnel, ARPDAU, and crash-free rate.
3. Fix the biggest funnel drop and the biggest retention leak first (usually onboarding / find-the-fun), tuning via remote config where possible.
4. Only scale UA once retention clears your bar — acquiring users for a leaky funnel burns spend.

## iOS measurement specifics

- **ATT prompt timing.** Show the App Tracking Transparency prompt at a sensible moment (after the player has seen value), with a clear pre-prompt. Opt-in is low on iOS, which has shifted ad revenue toward Android — so don't depend on IDFA-based measurement ([Tenjin 2026](https://tenjin.com/blog/ad-mon-gaming-2026/)).
- **SKAdNetwork / AdAttributionKit.** Configure conversion values to encode early-funnel signal (e.g. tutorial complete, first purchase) for privacy-preserving install attribution. Your attribution SDK handles the postbacks; you choose what the conversion values mean.
- **Privacy manifest.** Each analytics/attribution SDK collects data that must be declared in `PrivacyInfo.xcprivacy` (data types + required-reason APIs). Coordinate with `unity-qa-release` › App Store readiness; a missing declaration is an App Store rejection.

## Where this sits

- **`unity-monetization`** owns ad/IAP wiring; this skill measures whether that wiring is actually earning without hurting retention, and feeds the ad-cadence policy real numbers.
- **`unity-gameplay-systems`** builds onboarding / the core loop; instrument its first-session funnel here.
- **`unity-qa-release`** owns the privacy manifest, ATT, and store submission; analytics SDKs add requirements there.
- **`unity-game-director`** sets the retention/monetization targets this skill measures against.

## Field notes & lessons

- Retention is set *before* acquisition — the first-session onboarding funnel is the highest-leverage thing to instrument; fix the biggest drop before adding features.
- "More ads ≠ more revenue": raising ad frequency past a point lowers both retention and eCPM, so the right cadence is the one your ARPDAU-vs-retention data supports, not a number copied from a blog.
- Keep every tunable that you might want to change after launch behind remote config with a safe default — App Store review latency makes client-side constants expensive to fix.
- Wire privacy-manifest disclosures the moment you add an analytics/attribution SDK, not at submission time, or the iOS build gets rejected late.
