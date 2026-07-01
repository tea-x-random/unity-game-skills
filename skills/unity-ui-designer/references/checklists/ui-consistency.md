# Checklist — UI Consistency (kill cross-screen drift)

Run AFTER the screens exist, BEFORE calling UI "done". This catches the drift that makes a menu "look cheap" and text wander between screens — separate from readability and responsiveness. Verify with code greps + side-by-side phone-resolution screenshots.

## Design tokens (single source of truth)

- [ ] **Typography scale, not literals** — labels reference a small named set (Title/Heading/Body/Caption…) on the theme. Grep the UI code for raw font-size numbers at call sites; there should be ~none. (The example game had 16 distinct magic sizes — a fail.)
- [ ] **Spacing scale** — paddings/margins/gaps come from a stepped scale (xs/s/m/l/xl), not arbitrary per-screen numbers.
- [ ] **Semantic color roles** — widgets reference roles (`textPrimary`, `panel`, `accent`, `conflict`, `success`), not raw `new Color(...)` at call sites. A re-skin is a one-place change.
- [ ] **Hexes equal art-spec** — when the project has an `art-spec.yaml`, every GameTheme/theme color hex equals an art-spec palette hex (`palette.roles` + arrays) EXACTLY; no invented UI colors. Scope: colors only — typography/spacing/radii are theme-native and have no art-spec source.
- [ ] **Radii + icon/touch sizes tokenized** — one rounded-rect language; touch-min (~88px @2x = 44pt) is a named constant.
- [ ] **Theme self-heals** — `CreateInstance` of the theme gives the real values (default fields), so a null/headless asset ref still renders; no stale `Resources` theme asset shadows the `.cs` defaults.

## Shared component library

- [ ] **One factory per widget** — Label/Button/Card/IconButton/Pill each created by ONE shared UI-kit function used by every screen.
- [ ] **No inline-styled widgets** — no screen news up a raw `TextMeshProUGUI`/`Image`/`Button` and styles it ad hoc.
- [ ] **No forked factories** — there is a single `Label`/`Button` implementation, not per-screen copies (the example game had three `Label`s → drift).
- [ ] **Restyle propagates** — changing one factory (e.g. glossy→flat) visibly updates every screen; proven by re-screenshotting after a one-line change.

## Strings (single source of truth)

- [ ] **One provider per repeated label** — every string shown on 2+ screens routes through one method/table (e.g. `DifficultyRules.DisplayName`); no duplicated user-facing literals.
- [ ] **Localization seam exists** — user-facing text is externalizable (one place to swap per locale), not scattered literals.

## Fonts / international text

- [ ] **Glyph coverage decided up front** — the chosen font covers every required script (CJK etc.); verified, not assumed.
- [ ] **Project TMP default font set** — all runtime text inherits it; no per-label font assignment drift.
- [ ] **No tofu** — a screenshot of any required non-Latin script shows real glyphs, not □ boxes.
- [ ] **Crisp SDF** — dynamic-atlas TMP asset with adequate sampling/atlas/padding (e.g. 110 / 2048² / 11, SDFAA); text is sharp at its display size on a phone-resolution capture.

## Cross-screen visual match

- [ ] **Side-by-side screenshots** of menu / HUD / overlays show identical buttons, cards, headers, radii, and type roles — they look like one product, not N screens.
- [ ] **Safe-area + touch targets hold on EVERY screen**, not just the first one built.
