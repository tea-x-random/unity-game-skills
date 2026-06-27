# Roadmap & research notes

This file captures the research that shaped the skill set and the prioritized improvements still open. It exists so contributors understand *why* the skills emphasize what they do, and where to push next.

> **Caveat:** monetization and market figures are perishable (ATT/AdAttributionKit, eCPMs, and mediation shares move every quarter) and several come from single-vendor reports scoped to their own traffic. Treat the numbers below as directional, re-verify before quoting, and prefer measuring your own game.

## What the research said (verified findings)

**Skill-library design.** The strongest agent-skill libraries (anthropics/skills, obra/superpowers, IvanMurzak/Unity-MCP) converge on: self-contained skill folders, each a `SKILL.md` with YAML frontmatter (`name` + a trigger-rich `description`), designed to **auto-trigger contextually** and **compose**, with examples and a contribution model. Unity-MCP additionally exposes 70+ Editor tools and auto-generates skills from project config.

**Quality / retention (casual iOS, 2025–2026).**
- Retention is largely set **before** acquisition — by whether players find the fun, get guided to it, and hit low onboarding friction.
- Hybrid-casual benchmarks: **D7 ~20%, D30 ~10%** (hypercasual D30 ≈ 0). Use as quality targets, not guarantees.

**Monetization.**
- **Hybrid (IAP + ads) is the default** — 72%+ of developers — because only **~1.8%** of F2P players ever buy IAP. Typical mix ~40–50% IAP / ~50–60% ads.
- **AppLovin MAX dominates mediation** (~73% of top-downloaded, ~55% of top-grossing). LevelPlay/ironSource stronger on grossing; AdMob ~11–13%.
- **Rewarded video is the core casual format** (highest eCPM); design natural opt-in placements.
- **Over-serving ads hurts BOTH retention and eCPM** — tune frequency by measuring ARPDAU/retention, not a fixed cadence.
- **ATT shifted ad revenue toward Android** (iOS ~43% vs Android ~57%); iOS measurement must use **SKAdNetwork/AdAttributionKit**, not IDFA.

**Refuted in verification — deliberately NOT in the skills** (do not reintroduce): specific eCPM dollar ranges; "rewarded = 62% of ad revenue"; fixed interstitial cadence numbers; "D1 50%+ is the new standard"; difficulty-curve preference percentages; specific hybrid D90 ROAS figures.

## Shipped from this research

- **New `unity-analytics-liveops`** — analytics/retention instrumentation (D1/D7/D30, ARPDAU funnels), remote config + A/B testing, crash/analytics SDKs, soft-launch measurement, iOS ATT/SKAdNetwork + privacy-manifest coordination.
- **New `unity-aaa-graphics`** — visual-quality enforcement: per-surface "generate everything" sourcing, an AAA prompt library + genre art kits, render polish, and a visual scorecard that fails amateur/"MS-Paint" output.
- **New `unity-art-direction`** — the structured art system: a locked `art-spec.yaml` SSOT, a 12-preset style library, mobile art budgets, and a golden-asset/family production pipeline with quality gates.
- **Updated `unity-monetization`** — a "2025–2026 hybrid-by-default" strategy section (hybrid mix, mediation reality, rewarded-core, measure-don't-overserve, ATT/SKAdNetwork), cross-linked to analytics for cadence tuning.
- **Updated `unity-game-director`** — the asset gate is now a **Visual Quality Gate** (real art is the default for every primary surface; procedural is fallback-only; amateur-look auto-fails), with routing to the new skills and a stronger screenshot acceptance check.
- **Updated `unity-graphics`, `unity-image-generator`, `unity-3d-generator`** — procedural reframed as fallback (not "premium"); AAA prompt engineering + environment/terrain texture generation + a refine loop added to the generators.

## Shipped from the studio-POV audit

A studio-point-of-view audit (what a real casual-game team needs beyond the playable slice) shipped four new skills:

- **New `unity-project-setup`** — project foundation for a team: Unity `.gitignore` + Git LFS + meta-file/serialization discipline, `Assets/<Game>/` structure, asmdef architecture (engine-free Core/Game/Editor/Tests), package management, versioning, secrets-per-environment, and CI/CD basics.
- **New `unity-game-economy`** — economy & meta-progression design: soft/hard currencies, balanced sources & sinks, progression pacing, reward schedules, session design, and IAP-catalog/pricing design. Complements `unity-monetization` (wiring) and `unity-analytics-liveops` (measuring).
- **New `unity-localization`** — globally-localizable game via the Unity Localization package: String/Asset Tables, locale selection, Smart Strings (plurals/variables), per-script fonts + RTL, pseudolocalization, text-expansion layout, and localized App Store metadata.
- **New `unity-aso-growth`** — App Store Optimization & growth (resolves the ASO/store-listing recommendation below): icon/title/keywords/screenshots/preview-video, Apple Product Page A/B testing, creatives & soft-launch UA, SKAdNetwork/AdAttributionKit measurement, and ratings prompts.

## Open recommendations (prioritized)

1. ~~**ASO / store-listing skill or checklist**~~ — **shipped as `unity-aso-growth`** (listing optimization, Product Page A/B, soft-launch UA, SKAdNetwork measurement, ratings prompts).
2. **Save / persistence & cloud-save patterns** — local save (atomic writes, schema migration, corruption recovery) and cloud-save/sync; fold into `unity-gameplay-systems` or `unity-project-setup`.
3. **Accessibility** — colorblind-safe palettes, dynamic text size, reduce-motion, and audio cues; fold into `unity-ui-designer`.
4. **Onboarding / first-session "find-the-fun" gate** — make first-session design and its instrumentation a first-class step in `unity-gameplay-systems` + `unity-game-director` (retention's top lever).
5. **Concrete SDK integration recipes** — per-provider analytics wiring notes (Unity Gaming Services, GameAnalytics, Firebase Crashlytics, AppsFlyer/Adjust/Tenjin) in `unity-analytics-liveops/references/`.

## Sources

- anthropics/skills — https://github.com/anthropics/skills
- obra/superpowers — https://github.com/obra/superpowers
- IvanMurzak/Unity-MCP — https://github.com/IvanMurzak/Unity-MCP
- Solsten — D1/D7/D30 retention — https://solsten.io/blog/d1-d7-d30-retention-in-gaming
- Gamigion — 2025 hybrid-casual overview — https://www.gamigion.com/2025-hybridcasual-market-overview-with-real-data/
- Tap-Nation — hybrid-casual KPIs — https://www.tap-nation.io/blog/kpis-that-matter-metrics-to-track-in-hybrid-casual-games/
- Game Growth Advisor — F2P monetization 2026 — https://gamegrowthadvisor.com/blog/2026-04-02-f2p-monetization-models-comparison-2026/
- GameBiz Consulting — mediation share — https://www.gamebizconsulting.com/newsletter/newsletter-may25
- Tenjin — ad monetization 2026 — https://tenjin.com/blog/ad-mon-gaming-2026/
- TopOn — Global Mobile Games Monetization H1 2025 — https://mores.toponad.com/reports/
