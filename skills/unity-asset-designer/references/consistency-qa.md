# Consistency QA — the reject-and-regenerate gate

Run this on every asset BEFORE accepting it. It is a **gate**, not a glance: a fail means re-prompt (sharper style pin / tighter crop of the reference / reuse the seed) and regenerate — do not accept drift "to move on." Reference-conditioned models still vary across edits, so this catches what the conditioning missed.

## Per-asset rubric (score 1–10; gate at the project bar, e.g. ≥8)

| Axis | Pass test | Fail signal |
|---|---|---|
| **Silhouette** | Fill solid black, remove interior detail → still recognizable & distinct in <~0.5s | Reads as a blob; confusable with another asset |
| **At-size readability** | View at REAL in-game size (token ~6–9 cells, icon ~24–44px, app-icon thumbnail), not zoomed | Detail mush, illegible, or noisy below ~20px |
| **On-model — palette** | Uses ONLY the style-guide palette colors | A stray hue not in the palette |
| **On-model — line/shape** | Same outline weight + shape language as the sheet | Thicker/thinner line; sharp where the guide says round |
| **On-model — shading** | Same shading model (flat/cel/etc.) — no rogue gradients/gloss | Mixed finish (a common recurring slip) |
| **On-model — lighting** | Same single named light direction as the sheet | Light from the wrong side / added rim light |
| **Contrast** | Subject reads on its ACTUAL ground (per palette contrast intent) | Low contrast on its real background |
| **Do/Don't** | Honors the sheet's do/don't notes | Violates a stated rule (added detail, wrong proportion) |
| **Cohesion** | A stranger would name the agreed reference style from this asset | Looks like it's from a different game |

## Set-uniformity check (item/icon sheets — run on the WHOLE set)

Lay every item side-by-side at display size:

- [ ] Same **optical scale** in each cell (not just same px — visually balanced)
- [ ] Same **stroke weight** across all items
- [ ] Same **corner rounding** / shape language
- [ ] Same **palette** and same **flat lighting**
- [ ] Same **perspective** (all front-on, or all the same angle)

**One outlier → regenerate the whole sheet, not the outlier.** A single replacement icon generated separately will not match the set's lighting/scale — that's the icon-by-icon drift this skill exists to prevent.

## Automated checks (run these first — self-grading misses drift)

- **On-model (identity + style):** `unity-image-generator/scripts/critique_image.py <asset> --reference <canon_sheet> --art-spec <spec>` — the vision judge sees the canon and scores `on_model_vs_reference` (0–3).
- **Palette (deterministic):** `validate_sprite.py <asset> --art-spec <spec>` (average distance) or `--palette-mode exact` + `--max-distinct-colors N` for hard palette locks.

## Reject loop

1. Identify the failing axis (above).
2. Re-prompt: tighten the **style token** (add the missing constraint verbatim), or pass a **tighter crop** of the canon sheet as the reference image, or **reuse the seed** for a minimal re-roll.
3. Regenerate via `unity-image-generator`.
4. Re-run the rubric. Repeat until it passes the bar. Only then hand off for import.

## Cross-skill checks before "done"

- [ ] **Palette == UI tokens == art-spec.** `art-spec.yaml:palette.roles` is the SSOT; the style guide, `GameTheme.cs` color hexes, and `unity-ui-designer`'s tokens are runtime views DERIVED from it. On mismatch, regenerate the derived views from the spec — never hand-edit either side into agreement.
- [ ] **Recurring character is one character.** All its forms (e.g. token / mascot / app-icon) trace to the SAME model sheet and pass on-model. Side-by-side them: would a stranger call them the same character?
- [ ] **Handoff is concrete.** The exact prompt + reference image went to `unity-image-generator` (2D) or the turnaround to `unity-3d-generator` (image-to-3D); generation + Unity import (Sprite/PPU/ASTC/atlas, or ModelImporter) is THEIR job, not asserted here.

## Sources

Silhouette/readability: [Disney — silhouette test](https://www.waltdisney.org/sites/default/files/2020-05/T&T_Silhouette-final2.pdf), [Inviox — recognition timing](https://www.invioxstudios.com/blog/how-long-it-takes-for-players-to-recognize-a-character-silhouette), [bigredillustration](https://bigredillustration.com/articles/importance-of-silhouette-in-character-design/). At-size icon legibility: [Material icons — style](https://m1.material.io/style/icons.html), [uxplanet — practical icon design](https://uxplanet.org/practical-guide-to-icon-design-794baf5624c8), [Flaticon — visual consistency](https://www.flaticon.com/blog/visual-consistency/). On-model / drift: [21-draw — character sheet](https://www.21-draw.com/how-to-make-a-character-design-sheet/), [aeno art bible](https://www.aeno.nl/uploads/Art-bible.pdf).
</content>
