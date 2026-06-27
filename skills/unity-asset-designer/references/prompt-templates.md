# Prompt templates — copy, paste, fill the [BRACKETS]

These produce the reference artifacts and the conditioned production assets. They are **inputs for `unity-image-generator`** — run them through its `scripts/generate_image.py` (`--prompt/-p`, `--filename/-f`, `--input-image/-i` for reference conditioning, `--resolution/-r {1K,2K,4K}`). That skill owns API mechanics, billing/quota gotchas, and Unity import — see its SKILL.md. The point of these templates is the **wording that pins the look**; keep a single "STYLE TOKEN" string in your style guide and paste it **verbatim** into every prompt (re-describing the look in new words is the #1 cause of drift).

Reusable building block — define once in `style-guide.md`, paste everywhere:

```
STYLE TOKEN = "[your shading model, e.g. flat/cel/painterly], [your palette] palette, uniform [Npx] [your outline color] outline,
single soft light from [top-left] with no rim light, round friendly shape language,
clean edges, transparent background, [your mood words] mood —
NOT busy, NOT glossy, NOT desaturated, NOT cluttered"
```

---

## 1. STYLE-GUIDE / STYLE-TILE prompt (the visual DNA, made visible)

One small image that shows the locked palette + shape + shading + lighting on a sample object. Use it later as the literal reference image for derivation.

```
A single style tile establishing the art direction for a casual mobile game.
Show, in ONE image: a 5-swatch color palette strip (ground, panel, ink/text, accent-1,
accent-2) with hex-like swatches; and one sample object (a [simple rounded house / the
mascot's head] ) rendered in the target style.
Style: [STYLE TOKEN].
Palette (use ONLY these): ground [#hex], panel [#hex], ink [#hex], accent1 [#hex], accent2 [#hex].
Shading: [flat cel, no gradients]. Outline: [uniform 4px dark]. Light: [single soft top-left].
Flat 2D, front-on, generous negative space, no photographic texture, no text labels.
```

---

## 2. CHARACTER MODEL / TURNAROUND SHEET prompt (canon — generate FIRST)

One sheet, multiple aligned views + expressions + color callouts. This becomes the single source of truth and the image-to-3D input.

```
A character model / turnaround reference sheet for [CHARACTER — e.g. a friendly mascot],
laid out as ONE image on a plain light background.
Top row: orthographic turnaround — FRONT, 3/4, SIDE (profile), BACK views, all the SAME
character, aligned on shared horizontal guide lines (top of head, eye line, shoulder), identical
proportions and details across every view.
Bottom-left: an expression set — [neutral, happy, thinking, celebrating].
Bottom-right: a color-callout swatch key labeling each color used [list the character's color regions].
Proportion note: [~2.5 heads tall], chunky rounded body.
Style: [STYLE TOKEN].
Consistent lighting and palette across the whole sheet. Clean line art, flat fills, no background
scenery, no text other than the small color labels.
```

For 3D handoff, also request a clean **T-pose, symmetrical, line-art, no color** variant — `unity-3d-generator`'s image-to-3D wants exactly orthographic front/side/back.

**Mascot sheet add-on (token + mascot + icon on one sheet):**

```
Also include three USE-SIZE crops of the same character, on-model and identical in style:
(a) a tiny BOARD TOKEN version simplified to read clearly at ~8px (bold silhouette, minimal
interior detail); (b) a MASCOT bust framed for a circular menu header; (c) an APP-ICON crop
(character centered, fills a rounded square, no transparency).
All three must share the same palette, outline weight, shading, and lighting as the turnaround
above — this sheet is the canon all three forms conform to.
```

---

## 3. ITEM / ICON SHEET prompt (one pass — uniform set, THEN slice)

Generate the whole set as one grid so scale, stroke, palette, lighting, and perspective are identical. Slice in Unity afterward (`unity-image-generator`).

```
An icon set sheet: a single evenly-spaced [3x2] grid of UI icons, ALL drawn in one consistent
style for a casual mobile game. Icons, left-to-right: [hint lightbulb], [clear / trash], [menu /
home], [leaderboard / podium], [settings / gear], [heart].
Every icon: SAME optical size within its cell, SAME [3px] stroke weight, SAME corner rounding,
SAME palette, SAME flat lighting, SAME front-on perspective. Centered in each cell, even padding,
transparent background.
Style: [STYLE TOKEN]. [your line color on your fill]. Simple, legible at ~24-44px — minimal
interior detail (these are read small, not zoomed). No text, no labels, no drop shadows.
```

After generation: judge the grid **at size**, side-by-side. One mismatched cell → regenerate the **whole sheet** (a single replacement icon will never match the set's lighting/scale).

---

## 4. DERIVE-ONE-ASSET prompt (condition on the sheet — the everyday path)

Pass the canon sheet / style tile as the reference image (`-i`) and pin style verbatim. This is how every production asset is made — never from scratch.

```
[run with: generate_image.py -i Assets/<YourGame>/Art/Refs/character_model_sheet.png -p "<below>" -f Assets/.../character_token.png -r 2K]

Using the attached reference sheet as the canonical character and art style, produce [ONE board
token of the character, facing front, simplified to read at ~8px]. Keep the SAME character identity,
SAME palette, SAME [Npx outline] outline, SAME shading model, SAME single top-left light as the
reference — do not restyle, do not add detail not on the sheet. [STYLE TOKEN].
Single centered subject, transparent background, clean edges.
```

Reference-conditioning rules (Gemini / "nano-banana" family):
- **Role-tag multiple inputs** when you pass more than one: "use Image A for the character identity, Image B for the art style, Image C for the background." ([Google — Nano Banana Pro prompting](https://blog.google/products-and-platforms/products/gemini/prompting-tips-nano-banana-pro/))
- **Reuse exact tokens** every time ("emerald eyes," not "green eyes"; "flat cel," not "cartoon shading").
- **Identity reminder** for multi-turn edits: "use the same character identity / same art style as the previous image."
- **Reuse the seed** when exposed for near-identical re-rolls.
- Consistency can still vary across edits even with a reference — that's why the QA gate (`consistency-qa.md`) is mandatory, not optional.

---

## 5. APP-ICON prompt (derive from the mascot sheet, square, opaque)

```
[run with: -i <mascot_sheet.png>]
Using the attached mascot sheet as canon, produce an iOS app icon: the [character] centered, bold and
legible at thumbnail size, filling a rounded-square 1024x1024, SOLID background (NO transparency),
same palette/outline/shading/lighting as the sheet. Strong silhouette, no small text. [STYLE TOKEN].
```

Then hand to `unity-image-generator` for import; the app-icon slot wiring / build step is the project's icon builder / `unity-qa-release`'s job.
</content>
