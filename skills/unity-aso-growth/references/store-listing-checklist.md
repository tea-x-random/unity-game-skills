# Store Listing & ASO Checklist

Pre-submission ASO pass for a casual iOS game. Run this alongside `unity-qa-release` › App Store Readiness (which owns the build/privacy/submission mechanics). This checklist owns *what the listing says and shows*. Items requiring App Store Connect are **manual** — mark them not-done until a human completes them.

## Gate: retention before spend
- [ ] Soft-launch D1/D7 retention + ARPDAU read and clear your bar (`unity-analytics-liveops`) BEFORE committing UA spend.
- [ ] Biggest onboarding / first-session funnel drop fixed.

## App icon
- [ ] Legible at thumbnail/search size (test it shrunk down, not just full-res).
- [ ] One strong focal shape, high contrast, minimal-to-no text.
- [ ] On-brand / on-model with the in-game art (`unity-aaa-graphics` / `unity-asset-designer`).
- [ ] Square, no alpha channel, all required sizes (defer mechanics to `unity-qa-release`).
- [ ] Queued as an A/B variant if testing the icon (Product Page Optimization).

## Title, subtitle & keywords
- [ ] Title leads with the real app name; highest-value keyword worked in, still readable.
- [ ] Subtitle uses prime keyword + value-proposition real estate.
- [ ] Keyword field (100 chars) filled: comma-separated, no spaces, no repeats of title/subtitle words, no competitor brand names.
- [ ] No wasted characters in the keyword field.

## Screenshots
- [ ] First 2–3 screenshots lead with the value/benefit (these matter most; many users never scroll).
- [ ] Each screenshot captioned with a short, benefit-driven line.
- [ ] Consistent visual template across the set; readable at gallery scale.
- [ ] Correct device sizes provided (sizes/mechanics per `unity-qa-release`).
- [ ] Show the actual game (no fake/decoy gameplay).

## App preview video
- [ ] Shows the core loop + the satisfying moment in the first few seconds.
- [ ] Reads without sound (autoplays muted).
- [ ] Real gameplay, not a cinematic; matches what the ads promise.

## Description
- [ ] Hook in the first lines (before the "more" fold).
- [ ] Reinforces the value proposition.

## Localization (target markets)
- [ ] Title, subtitle, and keyword field localized per locale (localized, not just translated — search terms differ).
- [ ] Screenshot captions and preview localized for major target markets.
- [ ] In-app language consistent with the localized listing (`unity-localization`).

## A/B test plan (Product Page Optimization)
- [ ] One variable per treatment cell (icon OR screenshots OR preview — not bundled).
- [ ] Plan to let each test reach statistical significance before promoting a winner.
- [ ] Custom Product Pages mapped to specific ad campaigns/audiences where applicable.

## UA & creatives (if running paid acquisition)
- [ ] Creative concepts match the actual game (no misleading ads).
- [ ] Video-first concepts produced, multiple variants in rotation.
- [ ] Small soft-launch UA test (limited budget/geo) run and read before scaling.

## Measurement (ATT / SKAdNetwork)
- [ ] Attribution via SKAdNetwork / AdAttributionKit (not IDFA) — SDK wired (`unity-analytics-liveops`).
- [ ] Conversion values set to capture early-funnel signal (tutorial complete, level N, first purchase).
- [ ] ATT (`NSUserTrackingUsageDescription`) + `SKAdNetworkItems` present in the build (`unity-monetization` / `unity-qa-release`).

## Ratings & reviews
- [ ] `SKStoreReviewController` prompt wired to a positive moment (not first launch, not during friction).
- [ ] No begging, bribing, or gating gameplay behind a rating.

## Privacy & age rating (defer mechanics to unity-qa-release)
- [ ] Age rating completed in App Store Connect.
- [ ] App Privacy questionnaire matches the privacy manifest.
- [ ] Support URL + marketing/metadata fields complete.

## Featuring readiness
- [ ] Stable, polished, crash-free build (`unity-qa-release`).
- [ ] Follows the Human Interface Guidelines (safe area, native conventions).
- [ ] Adopts a current/new iOS feature where it fits the game.
- [ ] Clean, complete, localized listing ready; editorial nomination submitted to Apple if desired.
