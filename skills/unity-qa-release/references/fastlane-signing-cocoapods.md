# fastlane / iOS signing / TestFlight / CocoaPods gotchas

Automating the **manual macOS step** (signing → archive → `.ipa` → TestFlight) with fastlane and an
App Store Connect API key. These are hard-won from a real release session — each one cost hours and
is reproduced from the project's own `fastlane/Fastfile`. They do **not** change the doctrine: a green
fastlane run with a `MyGame.ipa` artifact + an upload confirmation is the evidence; a passing lane
message alone is not "shipped" (TestFlight still processes the build, and external review is separate).

Reference implementation: `fastlane/Fastfile` (lanes `create_app`, `unity_export`, `build_ipa`,
`upload`, `beta`) and `fastlane/.env.example` in a project that already uses this.

## App Store Connect API key auth (no Apple-ID / 2FA)

Use `app_store_connect_api_key` (key_id + issuer_id + the `.p8`) for every lane. Three gotchas bite:

1. **Token duration must be ≤ 1200s — Apple's hard ceiling — and you must NOT sit on exactly 1200.**
   `1201` is rejected outright; `1200` is rejected *intermittently* because any sub-second clock skew
   where your machine's clock is ahead of Apple's pushes `exp` past the ceiling. Symptom: flaky 401
   **"Authentication credentials are missing or invalid" (NOT_AUTHORIZED)** that comes and goes
   between runs. Fix: `duration: 1000` for margin.

   ```ruby
   app_store_connect_api_key(
     key_id:       ENV.fetch("MYGAME_ASC_KEY_ID"),
     issuer_id:    ENV.fetch("MYGAME_ASC_ISSUER_ID"),
     key_filepath: key_path,
     duration:     1000,   # NOT 1200 — leave margin under Apple's hard ceiling
     in_house:     false
   )
   ```

2. **Env-var shadowing produces a SILENT wrong-key 401.** fastlane reads `ENV`, and dotenv
   (`fastlane/.env`) **does not overwrite an already-set env var**. If the user's shell exports
   `ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_KEY_PATH` for a *different* key, fastlane uses the shell's
   values, not your `.env` — so the JWT is stamped with the wrong `kid` while signed with your key's
   private material, and Apple rejects it as the same generic "credentials missing or invalid" 401.
   It looks like an auth bug; it's a name collision. **Fix: give the lane's vars a unique prefix**
   (`MYGAME_ASC_KEY_ID`, etc.) so the shell can't shadow them, and read with `ENV.fetch` so a missing
   one fails loudly. **To confirm the `kid`,** base64url-decode the generated JWT header and check it
   matches your key id:

   ```bash
   # The header is the first dot-segment; its "kid" must be YOUR key id.
   echo "<jwt>" | cut -d. -f1 | base64 --decode 2>/dev/null; echo
   ```

3. **You cannot create the App Store Connect app *record* via an API key.** Apple only allows the app
   record to be made in the web UI (or legacy Apple-ID auth). The API key *can* register the App ID +
   capabilities in the Developer Portal (see Game Center below). So `create_app` registers the App ID
   and then **detects + instructs** for the record rather than trying to create it. Don't claim the app
   exists in App Store Connect until the human made the record.

## Build-number collisions

`latest_testflight_build_number` only counts **fully-processed** builds. Upload a new build while a
prior one is still processing and Apple rejects it: **"bundle version … already used."** Auto-increment
is `latest + 1`, but that floor is stale during processing. Provide an **override floor env**:

```ruby
next_build = latest_testflight_build_number(api_key: api_key, app_identifier: APP_ID,
                                            version: marketing, initial_build_number: 0).to_i + 1
override = ENV["MYGAME_BUILD_OVERRIDE"].to_i        # force a higher CFBundleVersion when a build is still processing
next_build = override if override > next_build
set_info_plist_value(path: plist, key: "CFBundleVersion", value: next_build.to_s)
```

(Unity bakes a literal `CFBundleVersion` into `Build/iOS/Info.plist`; write the number straight there.)

## Signing — Game Center / App Attest entitlements

The Unity-generated pbxproj leaves `DEVELOPMENT_TEAM` empty and ships **two** signable targets
(`Unity-iPhone` app + the embedded `UnityFramework`). The entitlements make automatic signing fail:

4. **Cloud/automatic signing via the API key can't synthesize an App Store profile that carries the
   Game Center feature.** `-allowProvisioningUpdates` will resolve a plain profile but not one with
   Game Center, so the archive fails. Fix: mint the profile explicitly with `sigh(force: true)`
   (`force` regenerates it to include the App ID's current capabilities), then switch to
   **manual, per-target** signing with `update_code_signing_settings`:

   - **app target** (`Unity-iPhone`) → the App Store profile (`profile_name` from `SIGH_NAME`) +
     `Apple Distribution` identity.
   - **framework target** (`UnityFramework`) → the distribution **identity only**, `profile_name: ""`.
     **Frameworks take no provisioning profile**; handing one to the framework target is itself an error.

   ```ruby
   sigh(api_key: api_key, app_identifier: APP_ID, force: true)
   profile_name = lane_context[SharedValues::SIGH_NAME]

   update_code_signing_settings(path: XCODEPROJ, use_automatic_signing: false,
     team_id: ENV.fetch("MYGAME_TEAM_ID"), targets: ["Unity-iPhone"],
     bundle_identifier: APP_ID, code_sign_identity: "Apple Distribution", profile_name: profile_name)
   update_code_signing_settings(path: XCODEPROJ, use_automatic_signing: false,
     team_id: ENV.fetch("MYGAME_TEAM_ID"), targets: ["UnityFramework"],
     code_sign_identity: "Apple Distribution", profile_name: "")   # framework: identity only, NO profile
   ```

5. **Keep the App Attest *environment* entitlement OFF (opt-in).** Adding
   `com.apple.developer.devicecheck.appattest-environment` to the entitlements **breaks automatic
   signing** — pinning it requires a provisioning-profile feature that automatic/cloud signing can't
   synthesize. You do **not** need it: App Attest still works on TestFlight/App Store, defaulting to the
   **production** environment for those build types. Write only the **Game Center** entitlement
   (`com.apple.developer.game-center`) by default; gate App Attest env behind an explicit env var
   (`MYGAME_APPATTEST_ENV=development|production`) for local Xcode debug attestation only. Entitlements
   are consumed via the `CODE_SIGN_ENTITLEMENTS` build setting — **do not** add the `.entitlements` file
   to a build phase.

## CocoaPods — when ads / native pods are present (Unity Ads, mediation SDKs)

EDM4U (External Dependency Manager for Unity, vendored as `MobileDependencyResolver`) is how Unity Ads
and mediation SDKs ship their iOS native deps. Three gotchas:

6. **EDM4U generates `Build/iOS/Podfile` during the Unity iOS build but does NOT reliably run
   `pod install` headlessly.** So the lane must (a) run `pod install` itself, and (b) build the
   resulting **`Unity-iPhone.xcworkspace`**, not the bare `Unity-iPhone.xcodeproj` — gym/`xcodebuild`
   on the bare project misses the pods and fails to link. Detect the Podfile and switch gym's input:

   ```ruby
   if File.exist?(File.join(build_dir, "Podfile"))
     Dir.chdir(build_dir) { sh("env -u GEM_HOME -u GEM_PATH -u BUNDLE_GEMFILE -u BUNDLE_BIN_PATH -u RUBYOPT -u RUBYLIB pod install") }
   end
   # then: gym :workspace => Unity-iPhone.xcworkspace if it exists, else :project => the .xcodeproj
   ```

7. **`pod install` inside a fastlane lane fails with `Gem::MissingSpecError`** — fastlane's bundler /
   `GEM_PATH` env leaks into the `pod` subprocess and CocoaPods can't resolve its own gems against
   fastlane's bundle. **Run pod install with that env stripped:**

   ```bash
   env -u GEM_HOME -u GEM_PATH -u BUNDLE_GEMFILE -u BUNDLE_BIN_PATH -u RUBYOPT -u RUBYLIB pod install
   ```

8. **Leftover mediation packages inject conflicting pods.** A stray `Assets/LevelPlay/` folder (its
   ironSource `Dependencies.xml` pulls `IronSourceUnityAdsAdapter` → **UnityAds 4.18.1**) conflicts with
   `com.unity.ads`'s **UnityAds ~> 4.17** and breaks `pod install` (incompatible version requirements in
   the generated Podfile). When you've settled on a **single** ad SDK, remove the other one *fully* —
   the UPM package entry, the `packages-lock.json` line, **and** the `Assets/<mediation>/` folder with
   its `Dependencies.xml` — so the Podfile contains only the SDK you ship.

## Lane structure that worked

- `create_app` — register App ID + Game Center via the ASC API once; instruct for the web-only app record.
- `unity_export` — optional headless Unity rebuild (`-executeMethod …BuildScript.PerformiOSBuild`,
  **Editor must be CLOSED**); gated behind `FORCE_UNITY_BUILD=1`, otherwise archive the already-built `Build/iOS`.
- `build_ipa` — bump build number → `sigh(force: true)` → per-target manual signing → `pod install`
  (env-stripped) → `build_app` on the **workspace** with `signingStyle: manual`.
- `upload` / `beta` — `upload_to_testflight(api_key:, skip_submission: true, skip_waiting_for_build_processing: true)`.

Anchor every path to the **project root** — fastlane runs with its cwd set to `fastlane/`, so resolve
`ROOT = File.basename(Dir.pwd) == "fastlane" ? File.expand_path("..", Dir.pwd) : Dir.pwd` and build paths
from there; the `.p8` path in `.env` is resolved relative to ROOT too.

## Truthful status language (unchanged doctrine)

- Done: "signed `MyGame.ipa` archived + exported (gym succeeded), uploaded to TestFlight" — with the
  artifact path and the upload confirmation in hand.
- NOT done by a green lane alone: TestFlight **processing** (asynchronous), external-tester review,
  App Store submission. Don't upgrade "uploaded" to "live on TestFlight" until processing finishes.
