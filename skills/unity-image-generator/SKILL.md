---
name: unity-image-generator
description: "Generate and edit STATIC 2D image assets for Unity casual games using Google's Gemini image API, then import them as sprites/textures/UI. Use for 2D casual games (match-3, puzzle, hyper-casual): static sprites, character/prop art, backgrounds, tile/ground art, tiling textures, UI panels, buttons, icons, logos, title/menu art, particle textures, and material/texture references. For ANIMATED/motion assets (characters, animated actors, multi-angle/turnaround, anything that needs smooth animation) prefer Tripo (unity-3d-generator) to rig + animate, and for 2D pre-render the rig to sprite frames — this skill's role there is producing the high-quality concept/reference images that condition those Tripo models (image-to-3D). Covers Unity 2D import: Sprite mode, pixels-per-unit, filtering, sprite atlas, and ASTC for iOS."
---

# Unity Image Generator

Generate **static** 2D art with Gemini, then import it into Unity correctly for sprites, UI, or textures. This is the skill for **static 2D art, textures/grounds, backgrounds, UI/icons, and reference/concept images**. Anything that **moves** — characters, animated actors, multi-angle/turnaround assets, anything needing smooth animation — should be produced with **Tripo** (`unity-3d-generator`: rig + animate; for 2D, **pre-render the rig to sprite frames**), with Gemini providing the high-quality reference images that condition those Tripo models.

## Gemini vs Tripo — pick the right tool (library-wide rule)

> **Motion → Tripo, static → Gemini.** This is the canonical, library-wide policy.

- **Anything that needs motion, smooth animation, multiple poses, or turnaround consistency → Tripo** (`unity-3d-generator`): rig + animate, and for **2D games render the rig to sprite frames** (see `unity-3d-generator` → "Use Tripo for 2D games too" + `../unity-3d-generator/references/prerender-2d.md`, then `unity-animation`). One rigged, rendered model gives consistent identity across frames and angles and drift-free animation.
- **Gemini (this skill) → static art:** concepts, tiling ground/textures, backgrounds, UI, icons, logos, and 2D art that doesn't move or need multiple angles — plus the **reference images that condition Tripo** (image-to-3D).
- **Gemini frame-by-frame animation DRIFTS** (each independently generated frame loses identity) and is a **FALLBACK ONLY** — reach for it only when `TRIPO_API_KEY` is **MISSING**/quota-blocked, or when the motion is trivial.

## API key & script

Key resolution: `--api-key`, then `GEMINI_API_KEY`. Probe first:
```bash
bash ~/.claude/skills/unity-game-director/scripts/probe_asset_credentials.sh   # GEMINI_API_KEY=SET|MISSING
```
```bash
python3 ~/.claude/skills/unity-image-generator/scripts/generate_image.py \
  --prompt "..." --filename Assets/Art/Sprites/coin.png --resolution 2K
```
Flags: `--prompt/-p`, `--filename/-f` (write under `Assets/`), `--input-image/-i` (edit an existing image), `--resolution/-r {1K,2K,4K}`, `--api-key/-k`.

## Dependencies & quota gotchas (check these FIRST)

The script needs `google-genai` and `pillow`. On modern macOS the system Python is
externally-managed (PEP 668), so install into a venv rather than `pip install --user`:

```bash
python3 -m venv .artvenv && ./.artvenv/bin/pip install google-genai pillow
# run the script with .artvenv/bin/python ...
```

`ModuleNotFoundError: No module named 'google'` means this step was skipped.

**Image gen needs billing on; once it is, the pipeline works.** The script calls
`gemini-3-pro-image-preview` (`scripts/generate_image.py --prompt "..." --filename out.png --resolution 1K|2K|4K`).
One-time setup: `python3 -m venv .artvenv && .artvenv/bin/pip install google-genai pillow`. With
billing **enabled** on the Google AI / Gemini API project, generation succeeds and PNGs import via the
project's ArtImporter (Sprite + iOS ASTC). On a **free-tier** key it (and `gemini-2.5-flash-image`)
returns `429 RESOURCE_EXHAUSTED ... limit: 0` — NOT transient rate-limiting; retrying and
model-swapping both fail. If the probe shows a key but every image 429s with `limit: 0`, report it as a
billing blocker (an allowed asset-sourcing skip) and fall back to procedural/placeholder art — do not
loop on retries.

**Exporting an interactive-only key to a non-interactive tool process.** If `GEMINI_API_KEY` lives in
`~/.zshrc` (sourced only for interactive shells), a tool/agent shell won't have it. macOS has no
`timeout`, and `zsh -lc` does NOT source `~/.zshrc` — you must use `-i`:
```bash
export GEMINI_API_KEY="$(zsh -ic 'printf %s "$GEMINI_API_KEY"' | tail -1)"
```

## What to generate for casual games

- **Sprites / characters / props:** request transparent background, single centered subject, consistent style, clean edges. For pixel art, ask for crisp pixels and a fixed palette.
- **Sprite sheets:** request an evenly-spaced grid of frames on transparent background; slice in Unity (Sprite Editor / Grid By Cell). For **animated assets, produce frames via Tripo rig + pre-render by DEFAULT** (`unity-3d-generator` pre-render → `unity-animation`) — one rigged model gives drift-free, consistent frames across states/angles. Direct Gemini per-state frame strips (idle/walk/attack) sliced by `unity-animation` are the **FALLBACK** only when Tripo is unavailable (`TRIPO_API_KEY` missing/quota-blocked) or the motion is trivial.
- **Backgrounds / parallax layers:** request seamless or full-bleed layers sized to portrait phone aspect (e.g. 1080×1920 framing).
- **UI:** buttons, panels, frames, progress bars, currency/HUD icons, settings glyphs — flat, high-contrast, readable at small size, transparent background. Keep a consistent icon family.
- **Logos / title art / app icon:** bold silhouette, legible at thumbnail size, no tiny text. The iOS app icon must be square with no transparency.
- **Texture/material references and image-to-3D concepts:** front/side/back T-pose sheets, tiling material swatches — these feed `unity-3d-generator`. **When the concept will be rigged/animated via Tripo, generate a clean full-body T-pose (or A-pose)** — arms away from the torso, legs apart, no props crossing the body — because auto-rigging fails on action poses; generate the action (e.g. a bow-draw) later as animation clips, not in the static concept (see `../unity-3d-generator/SKILL.md` → "Riggable characters need a clean full-body T-pose").

## Style is the user's, never the skill's (READ FIRST)

This skill is a **neutral pipeline**. Every style token — line weight, outline color, palette, shading model, fidelity, finish — comes from the **user's stated aesthetic** or a **user-provided reference**. The skill must **never inject a house style**: no default "cozy", "storybook", "cute", "AAA", "painterly", "thick ink", "high-detail". There is **no such thing as a default look** here, and **flat/minimal is exactly as valid a target as high-detail rendered** — neither is "better".

- **If the user gave an aesthetic, transmit it faithfully.** Build the prompt from THEIR words, not your priors.
- **If the user gave a reference, MEASURE it (don't vibe it)** — see "Match a reference" below.
- **If neither was given, ASK** for one (a sentence of direction or one example image) before generating. A guessed style is the #1 cause of "looks nothing like what I wanted" churn — and the failure is silent, because self-graded art always "looks fine."

> Real failure this codifies: a flat, muted, thin-line puzzle game (Pup Champs) was generated from injected adjectives ("cozy storybook thick-ink, warm palette"). Result: gorgeous but *completely wrong* — heavy black ink, saturated, painterly, dominant background, invisible grid. The skill, not the user, had supplied the style.

## Prompt engineering (match the TARGET fidelity — high or flat)

One-line prompts produce one-line art. A production prompt names, in order: **subject**; **view/framing** (top-down, 3/4, side, centered); **art style** (from the brief/reference — name touchstones only if the user did); **shape language** (chunky, rounded, angular); **palette** with explicit tokens (hex or named, sampled from the reference); **shading model** *as the target dictates* — flat single-tone, cel, soft-gradient, or fully rendered with AO — these are CHOICES, not a ladder; **fidelity/detail density** *as the target dictates* (minimal-and-clean is a legitimate target, not a failure); **output spec** (transparent OR seamless tiling, single subject, no text/UI); and a **negative prompt built from the axes where the target differs from the generator's default** (next paragraph).

**Counter-steer the generator's defaults — but ONLY on the axes where your MEASURED target differs.** Gemini (and most image models) bias toward over-rendering: gradient/glossy shading, busy detail, and sometimes muddy or washed color. Negate an axis **only when your measured target sits opposite the model's drift on THAT axis** — never paste a blanket list, and never negate an axis your reference actually has. Worked examples on the same flat reference:
- Its **fill** is flat but its **outline is bold** and **palette saturated** and pieces have **drop shadows** → negate `NOT gradient shading, NOT glossy, NOT busy` (to hold flatness/cleanness) but DO NOT negate outline, saturation, or shadow — prompt FOR a "bold dark outline", "saturated", "soft drop shadow" instead. (Negating `NOT saturated`/`NOT drop shadow` here — as a naive "it's flat so make everything light" would — actively breaks the match.)
- A high-detail painterly target → steer the other way: `NOT flat single-color fill, NOT MS-Paint, NOT jagged edges`.

The list is built **per measured axis**, every time. (The old fixed `NOT: flat single-color fill` sabotaged a flat target; a naive `NOT saturated, NOT drop shadow` sabotaged the *corrected* attempt at the SAME target. Both came from a blanket list instead of per-axis measurement.)

For template scaffolding and per-genre exemplars see `../unity-aaa-graphics/references/prompt-library.md` — but treat its high-fidelity examples as ONE point on the spectrum, and rewrite its negatives to your target.

## Match a reference (measure INDEPENDENT axes — never slide one "heavy/light" knob)

The biggest, most expensive mistake here: collapsing a reference into a single gestalt vibe ("heavy storybook" / "soft flat-minimal") and dialing that one knob. **Style is multi-dimensional, and the axes are INDEPENDENT.** A reference can be *flat-filled* **and** *bold-outlined* **and** *saturated* **and** *drop-shadowed* all at once — sliding one knob can never reach that mix. "Flat" describes ONLY the fill; it implies nothing about outline weight, color, shadows, or saturation. Two real misses on the SAME game (Pup Champs): pass 1 over-heavy (thick black ink, painterly), pass 2 over-corrected to light on *every* axis (thin outline, muted, no shadow, no grid) — when the truth was flat-fill + **bold** dark outline + **saturated** palette + **drop shadows** + **visible grid**.

When given a reference image (or a named shipped game), do NOT describe it from memory. **Open it, zoom in (crop the key pieces 3×), and SAMPLE PIXELS.** Measure each axis SEPARATELY and write each as its own explicit token. Do not let any axis inherit a value from your overall impression:

1. **Fill / shading:** flat single-tone · cel (1 shadow) · soft-gradient · fully-rendered. (Many cozy mobile games are **flat** — measure, don't assume rendered.)
2. **Outline weight:** none · thin · **bold**. Measure it in px relative to the asset, on a zoomed crop. This is independent of fill.
3. **Outline color:** true-black · dark-tinted (e.g. dark brown) · colored.
4. **Character treatment:** plain · **sticker-halo** (a thick white/cream border around characters — a very common mobile signature; easy to miss, defines the look).
5. **Grounding:** none · **drop shadow** · contact AO. (If the reference has soft shadows under every piece, you MUST add them — do NOT negative-prompt "drop shadow" away.)
6. **Saturation & contrast:** sample 4–7 actual hexes off the pixels. Muted-grey vs **saturated** is a measurement, not a feeling — getting this from memory is how a saturated reference becomes a washed-out copy.
7. **Detail density:** minimal/iconic vs busy.
8. **Perspective/framing + focal hierarchy:** in a board/puzzle game **the grid/board is the hero** and the background is subordinate (generate the bg low-contrast so it recedes). If the reference shows a **grid**, the grid is a first-class element — see the engine note below.

Reuse ONE measured token-set across the whole asset family. **Then validate PER-AXIS against the reference, not gestalt:** chroma-key the pieces, composite onto the bg in the reference's own layout, place it **side-by-side with the actual reference**, and check EACH axis explicitly — "is my outline as bold? is my red as saturated? do my pieces have the shadow? the halo? the grid?" A gestalt "looks close" is exactly how both wrong passes shipped. (This out-of-engine check is also immune to a flaky MCP bridge.)

> **What you mock must be what the ENGINE renders.** A Pup Champs miss: the grid was drawn in the PIL validation mock but never built into the Unity scene, so the "validated" layout didn't exist in-game. If a feature appears in your validation composite (grid lines, shadows, halos), it must be produced by the scene builder / shaders too — otherwise the mock is validating a lie. Either build it in-engine or don't put it in the mock.

## Transparency: Gemini fakes it — chroma-key instead

Asking Gemini for a "transparent background" often yields a painted **checkerboard** (fully opaque) or a colored fill, not real alpha. Reliable path: generate the subject **alone on a solid chroma background** — magenta `RGB(255,0,255)` (use cyan if the subject itself is pink/red/magenta) — then key it out: sample the corner color, drop pixels within a distance threshold, cut alpha, and autocrop. (A reusable keyer pattern lives in the field notes / scratch scripts.)

## Environment & terrain textures (most-missed assets)

Top-down and side games need **real ground and paths that read as a surface, not a single flat fill** — this removes most of the "amateur" look in tower-defense / top-down maps. Generate **seamlessly tiling** ground / path / tileset textures. The `<STYLE>` and `<PALETTE>` slots below are filled **from the user's brief / measured reference** — the example uses a painterly fill only to show the shape; swap it for whatever the target style is (flat-cel, pixel, painterly, …):

```
seamless tiling <STYLE> grass ground texture, top-down, <PALETTE e.g. #6Fae5a / #4f8a3e>,
subtle variation and clumps, even soft lighting, clean edges, no seams, no subject, no text
— <NEG built for the target style>
```

Import tiling textures with `wrapMode = TextureWrapMode.Repeat` and **mipmaps ON** for material/3D use (the opposite of UI sprites). Apply to a material's albedo and set tiling so the pattern repeats across the surface.

## Refine loop (regenerate, don't just reroll)

Generate at **1K** first to check composition. If framing/subject is wrong, **rewrite the prompt** (don't just reroll the same one). Once composition is right, refine at **2K** via `--input-image`, reusing **verbatim style tokens** (style name, touchstones, palette) to avoid drift across passes. Use the prompt-library's per-asset rubric to judge each pass. Iterating via `--input-image` also handles recolors, edge cleanup, and variants.

## Import into Unity (via unity-mcp-bridge)

After writing the PNG under `Assets/`, `refresh_unity(scope="assets", wait_for_ready=true)`, then set import settings with `execute_code` (`TextureImporter`) — Unity's default `textureType` may not match intent:

```csharp
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath("Assets/Art/Sprites/coin.png");
ti.textureType = UnityEditor.TextureImporterType.Sprite;     // Sprite (2D and UI)
ti.spritePixelsPerUnit = 100;                                // match your world scale
ti.spriteImportMode = UnityEditor.SpriteImportMode.Single;   // or .Multiple for sheets, then slice
ti.filterMode = UnityEngine.FilterMode.Bilinear;             // Point for pixel art
ti.mipmapEnabled = false;                                    // off for UI/2D sprites
// iOS compression
var s = new UnityEditor.TextureImporterPlatformSettings {
    name="iPhone", overridden=true,
    format=UnityEditor.TextureImporterFormat.ASTC_6x6, maxTextureSize=2048, compressionQuality=100 };
ti.SetPlatformTextureSettings(s);
ti.SaveAndReimport();
return "imported sprite";
```

Then:
- **Sprites in scene:** `manage_gameobject` with a `SpriteRenderer`, assign the sprite.
- **UI:** UI Toolkit (background-image in USS) via `manage_ui`, or uGUI `Image` via `manage_gameobject`+`manage_components`. See `unity-ui-designer`.
- **Atlas:** group related sprites into a **Sprite Atlas** to cut draw calls (big win on mobile). Create the atlas asset and add the folder.

## Quality & mobile rules

- **Real generated art is the default for primary visible surfaces** (characters, props, ground, paths, backgrounds, UI). Procedural placeholder art is a *fallback only* when the key is MISSING or quota-blocked (see the billing-blocker note above) — not a first choice.
- Keep a consistent art-direction across a family (same lighting, outline, palette).
- Pack sprites into atlases; power-of-two max sizes; mipmaps off for crisp 2D, on for 3D textures.
- Use ASTC on iOS; cap max texture size to the smallest that still looks sharp on device.
- **Non-Latin text needs a font that covers the script.** Unity's default LiberationSans SDF has no glyphs for many scripts (CJK, Cyrillic, Arabic, etc.), so those labels render as blank "tofu" boxes. Import a TMP font asset that covers your target script (e.g. an appropriate Noto family font); until it exists, fall back to a supported script. (Also relevant to `unity-ui-designer`.)
- Report prompts, output paths, import settings applied, and where each asset is used.

## Field notes & lessons

- **Policy: Motion → Tripo, static → Gemini.** Anything that moves or needs multiple poses/turnaround consistency goes through Tripo (rig + animate; pre-render to sprites for 2D) with Gemini supplying the reference images that condition it. Gemini is for static art, textures, grounds, backgrounds, UI/icons, and concept/reference images; its frame-by-frame animation drifts and is a fallback only when `TRIPO_API_KEY` is missing/quota-blocked.
- Gemini image pipeline confirmed working once billing is on (`gemini-3-pro-image-preview` via `generate_image.py`, `.artvenv` with google-genai+pillow); added the interactive-only key export trick for non-interactive tool shells (`zsh -ic`, not `-lc`; no `timeout` on macOS); noted non-Latin text needs a matching TMP font (default LiberationSans has no glyphs for many scripts) — fall back to a supported script until imported.
- **Style-neutrality + per-axis measurement is the law here (learned the hard way, TWICE on one game).** Pass 1: a flat puzzle game generated from *injected* adjectives ("cozy storybook thick-ink, warm") → beautiful but wrong (heavy ink, painterly, dominant bg). Pass 2 *over-corrected* by sliding every axis to "light" (thin outline, muted, no shadow, no grid) → still wrong. Truth (measured): flat fill + **bold** dark-brown outline + white **sticker-halo** + **drop shadows** + **saturated** palette + **visible grid**. The lesson: (1) all style tokens come from the user/reference, never the skill's priors; (2) **style is multi-axis and the axes are INDEPENDENT — measure each separately by zooming + sampling pixels; never collapse to one "heavy/light" knob** ("flat" constrains only the fill); (3) counter-steer the model only on axes where the measured target differs; (4) validate **per-axis** side-by-side with the actual reference; (5) what the mock shows, the engine must render (the grid was mocked but never built). See "Match a reference" above.
