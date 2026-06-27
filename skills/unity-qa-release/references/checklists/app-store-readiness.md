# App Store Readiness Checklist

For submitting a casual iOS game. Items past the build are **manual macOS / App Store Connect** steps — name them as not-done until a human completes them.

## App assets
- [ ] App icon: **square, no alpha channel**, all required sizes provided.
- [ ] Launch screen configured (storyboard / Unity launch screen); not the default Unity splash if Pro license.
- [ ] Orientation **locked to portrait** (Player Settings) for most casual games.
- [ ] **iPhone-only** unless you truly support iPad: `PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPhoneOnly` (→ `TARGETED_DEVICE_FAMILY=1`). Pin BOTH the app target and the **UnityFramework** target in `[PostProcessBuild]` (Unity can leave the framework at `"1,2"`). Verify with `GetBuildPropertyForAnyConfig` and/or `PlistBuddy -c "Print UIDeviceFamily"` on the `.ipa`'s `Info.plist` (→ `{ 1 }`). Otherwise App Store Connect demands 13-inch iPad screenshots.

## Player / build settings
- [ ] Deployment target >= **iOS 13** (Unity 6 minimum).
- [ ] **IL2CPP** backend confirmed.
- [ ] Managed stripping on **+ `link.xml`** preserving reflection/serialization types; tested on the stripped build.

## Privacy / tracking
- [ ] `PrivacyInfo.xcprivacy` privacy manifest included if collecting data or using required-reason APIs.
- [ ] **ATT** prompt shown before tracking **if** using ads / analytics / IDFA. For **non-personalized** ads (`npa=1`): no ATT, and post-build **removes** any `NSUserTrackingUsageDescription` the ad plugin injected.
- [ ] Third-party SDK privacy manifests present (ad/analytics SDKs) — these declare the SDK's own collection; Apple merges them with yours.
- [ ] Non-tracking game with a Game Center leaderboard: `NSPrivacyTracking=false`, empty domains, and three collected-data entries — `…UserID` + `…Name` + `…OtherDataTypes`, each `Linked=true`, `Tracking=false`, purpose `…AppFunctionality`. Keep the `NSUserDefaults` CA92.1 entry.
- [ ] **App Privacy questionnaire matches the manifest** (tracking = No; same data types + purposes).

## Submission (App Store Connect)
- [ ] Export compliance declared (most casual games: standard/exempt; `ITSAppUsesNonExemptEncryption=false` via post-build skips the per-upload prompt).
- [ ] Age rating completed.
- [ ] Screenshots: **6.9" = 1320×2868** (iPhone 16 Pro Max) + **6.5" = 1242×2688**; no iPad sizes once iPhone-only. Capture via `ScreenCapture.CaptureScreenshot` at a Fixed Resolution Game View size (NOT `manage_camera` — it drops Overlay UI), or on-device. Verify with `sips -g pixelWidth -g pixelHeight`.
- [ ] Metadata (name, description, keywords, support URL) complete.
- [ ] **Game Center: first leaderboard added to the v1.0 version's Game Center section and Submitted WITH the app version** (it's a versioned item; must be "Ready to Submit").
- [ ] **Real-ad rebuild attached** — flipped `UseTestAds=false`, rebuilt, uploaded; that build (not a test-ad build) is the one attached for review.
- [ ] Deliverable docs generated: SUBMISSION_CHECKLIST + APP_STORE (listing + App Privacy answers) + PRIVACY_POLICY (user hosts at a public URL).

## Signing & delivery (MANUAL — macOS / Xcode, not MCP)
- [ ] Signing team + provisioning profile set in Xcode.
- [ ] `xcodebuild archive` → `-exportArchive` produces the `.ipa`.
- [ ] Uploaded to **TestFlight / App Store Connect**.
- [ ] Do NOT claim "shipped/on TestFlight" until this section is actually done by a human.
