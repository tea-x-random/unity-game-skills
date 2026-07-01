# Deep-Research Report: Why the Unity Game Skills Produce Splintered, Inconsistent Art — and How to Fix It

**Repo:** `unity-game-skills` · **Date:** 2026-07-01 · **Scope:** all 26 skills + `~/.claude/skills/unity-2d-sprite-games` · **Goal:** AAA-studio-quality, cohesive game art from a multi-skill agent pipeline

---

## 1. Executive Summary

Your three complaints — character inconsistency, art that doesn't cohere, and skills that splinter when combined — trace back to **three root causes**:

### Root cause 1: The style contract exists, but nothing is mechanically bound to it
The repo has the *right idea* (art-spec.yaml as a machine-readable single source of truth), but it competes with a second style stack (unity-asset-designer's `style-guide.md` + `GameTheme.cs`), and the two are cross-referenced in prose only — there is no derivation rule, no equality check, and no script that actually *reads* the spec. Every generation and QA invocation re-types palette, view, outline, and PPU as hand-assembled CLI flags. The only automated cross-check in the entire repo compares a `style_id` **string**. Palette, lighting, proportions, and finish can legally diverge between the artifact that *conditions* generation and the artifact that *validates* it. This is the architectural root of "art doesn't cohere." Every shipped-game pipeline studied — InnoGames/Scenario ([innogames.com](https://blog.innogames.com/innogames-x-scenario-streamlining-our-game-production/)), OpenAI's gpt-image guidance ([platform.openai.com](https://platform.openai.com/docs/guides/image-generation?image-generation-model=gpt-image-1)), Google's consistent-imagery codelab ([codelabs.developers.google.com](https://codelabs.developers.google.com/gemini-consistent-imagery-notebook)) — centers on ONE locked per-game style artifact that every generation call flows through.

### Root cause 2: Consistency mechanisms scope to a single asset, never to the game
unity-pixel-art's anchor-first rule is correct — *within one asset*. Character #2 starts from a fresh text-only pixflux prompt, so your knight and goblin are independent dice rolls sharing at most a prose style phrase. That is the literal mechanism behind "characters vary in style/proportions/palette across generations." Industry consensus (2025-2026) is that identity is carried by **persistent artifacts** — anchor images, palette swatch images, skeleton templates, frozen identity strings, canon sheets — conditioned into *every* call, not by prompts or seeds ([pixellab.ai/docs/tools/consistent-style](https://www.pixellab.ai/docs/tools/consistent-style), [Scenario character models](https://help.scenario.com/en/articles/train-a-consistent-character-model/), [Retro Diffusion](https://runware.ai/blog/retro-diffusion-creating-authentic-pixel-art-with-ai-at-scale)). The repo has none of these artifacts in its schema: no reference-image fields, no per-character canon records, no golden-asset paths, no game-level palette file.

### Root cause 3: The enforcement layer is broken and the orchestrator doesn't order the pipeline
The one gate meant to hold everything together — `validate_asset_manifest.py` — **rejects every PixelLab asset** (the `pixellab` generator is missing from its allowlist), runs all coherence checks as opt-in flags, and trusts QA booleans no tool computes. Two Editor snippets hardcode `FilterMode.Bilinear`, blurring pixel art the pixel skill's own rejection list forbids. Identity QA is entirely eyeball-based (`critique_image.py` can only see one image, so it can never compare against a canon sheet). And unity-game-director's Phase Routing is a flat catalog with no ordering, no gates, no ledger entry for the art-spec, and no cross-session rediscovery — session N+1 re-derives style from scratch. The scene-assembling skill (unity-gameplay-systems) never mentions the registry at all. Published agentic pipelines (GameUIAgent [arxiv.org/html/2603.14724v1](https://arxiv.org/html/2603.14724v1), Schomay [blog.jeffschomay.com](https://blog.jeffschomay.com/lost-in-an-infinite-maze-building-a-real-time-generative-ai-game-assets-pipeline)) are ordered, gated architectures where deterministic validation runs before expensive generation — the opposite of a flat catalog with silent-pass gates.

**The good news:** the repo's architecture is directionally right (spec → contract → registry → scene). The fixes are mostly wiring, schema fields, and bug repairs — not a rebuild. Four fixes are small-effort/high-impact and can land this week (R3, R4, R7, R10).

---

## 2. State of the Repo

| Skill cluster | What it does well | Where it breaks |
|---|---|---|
| **unity-pixel-art + unity-animation** | Anchor-first within-asset production; skeleton-driven animation as the anti-drift path; palette lock implemented in the script (`color_image` swatch); mandated `validate_sprite.py` gate + rejection list; correct Unity pixel import contract; provenance manifests per generation. | Anchor scopes to ONE asset — "golden" appears nowhere; art-spec consumed via one unenforced sentence; script can't read any spec/contract; every SKILL.md generation example omits `--palette`; API docs drifted from live PixelLab schema (guidance params); no frame-vs-anchor identity check. |
| **unity-image-generator + unity-asset-designer** | Real automated QA stack (validate_sprite.py, critique_image.py vision judge); style-neutrality doctrine; best-of-N selection; solid chroma-key transparency pipeline; asset-designer encodes correct studio methodology (art bible, frozen turnaround sheets, single-pass icon sets). | Handoff is one-directional — image-generator has **zero** references to asset-designer or canon sheets; no script reads a style contract; `generate_image.py` takes exactly one `--input-image` so the documented multi-reference technique cannot run; critique gate can't see the reference; prompt-templates hardcode a house style, violating image-generator's own doctrine. |
| **unity-3d-generator + unity-aaa-graphics + unity-graphics** | aaa-graphics has the strongest cohesion scorecard (asset-cohesion / finish-consistency axes, auto-fails); art-direction-first mandate; Tripo rig/animation structural validation; prerender-2d.md is the only file that consumes art-spec lighting. | 3D main flow consumes NO style contract (style tokens live in conversation memory); scale treatment is `globalScale = 1.0f // fix if needed`; PBR Tripo finish never unified with flat/cel 2D; SKILL.md:97 bypasses contract/registry; unity-graphics references neither style system; scorecard is fully self-graded. |
| **unity-art-direction + unity-scene-composition** | Genuine machine-readable SSOT (art-spec.yaml) with hard "never generate without it" rule; golden-asset + 80/20 family strategy; composition.yaml numeric screen contract (layer contrast, density budgets, shadow profile); in-engine screenshot acceptance. | Spec template has no fields for the things consistency needs: no pixel/craft block (SKILL.md branches on a `finish` field that doesn't exist), no reference-image/golden-asset/seed/identity-string/canon fields, no PPU; composition budgets are numbers nothing measures; scene-composition has zero scripts. |
| **unity-asset-pipeline + unity-audio-generator** | The repo's best coherence design on paper: per-asset contract with style_id/camera/provenance, approved registry, BeautyCell vertical-slice discipline, import-settings-as-gate. | Validator **rejects all PixelLab contracts** (allowlist bug); all cross-checks opt-in; `palette_valid`/`scale_valid` are phantom booleans; ApplySpriteImport hardcodes Bilinear and never validates filter/compression; PPU checked for existence only; template style_ids disagree with each other; audio fully outside the pipeline (script is still an unmodified Three.js port). |
| **Orchestration (game-director, gameplay-systems, game-layout, project-setup)** | North-star as first-class early deliverable; real Visual Quality Gate with anti-patterns; evidence-based verification; layout skill's one-PPU law and pivot discipline; LFS + committed .meta persistence substrate. | Phase Routing is a flat, unordered catalog; art-spec phrased as optional; ledger never tracks it; gameplay-systems (the skill that actually builds scenes) has ZERO mentions of registry/contract/art-spec and creates competing primitive prefabs; detect script never probes for existing art artifacts, so sessions re-derive style; project-setup provisions none of the pipeline paths; three conflicting filesystem root conventions. |
| **Orphans** | unity-2d-sprite-games owns the crucial generation-side one-pixel-density law and a good chroma-key recipe. | Lives only in `~/.claude/skills`, referenced by zero repo skills, routes pixel sprites to Gemini (contradicting PixelLab-final doctrine), and cites a phantom aaa-graphics scorecard axis. |

---

## 3. Root-Cause Analysis

### Complaint 1: "Characters vary in style/proportions/palette across generations"

Traced to five specific missing mechanisms:

1. **No game-level anchor conditioning.** BitForge `--style-image` conditioning is prescribed only for variants of the *same* asset (unity-pixel-art/SKILL.md:34,60). New characters are fresh text rolls. PixelLab's own docs describe style-reference generation as "perfect for creating characters, items, and objects that fit together in your game" ([pixellab.ai/docs/tools/consistent-style](https://www.pixellab.ai/docs/tools/consistent-style)) — the vendor's documented fix for exactly this, unused. → **R3**
2. **No per-character canon in any machine-readable artifact.** Turnaround sheets exist as prose deliverables with no path convention, no contract field, no frozen identity string. Retro Diffusion's documented identity technique is a frozen verbatim description varying only pose clauses ([runware.ai](https://runware.ai/blog/retro-diffusion-creating-authentic-pixel-art-with-ai-at-scale)); Google's codelab formalizes a persistent asset graph of canon sheets ([codelabs](https://codelabs.developers.google.com/gemini-consistent-imagery-notebook)). → **R2, R13**
3. **Palette enforced nowhere by default.** The `color_image` hard lock is implemented in the script but absent from every documented invocation; the post-hoc palette check runs only `if args.palette:`. Even purpose-trained pixel models cannot self-limit colors — hard constraints must be supplied ([runware.ai](https://runware.ai/blog/retro-diffusion-creating-authentic-pixel-art-with-ai-at-scale)). → **R4, R5**
4. **Proportions have no shared skeleton or tile-derived sizing.** Each character gets estimate-skeleton fresh; canvas sizes are picked ad hoc instead of derived from tile size (1×2 tile ratio per [Slynyrd](https://www.slynyrd.com/blog/2019/10/21/pixelblog-22-top-down-character-sprites)). → **R2, R12**
5. **Identity QA is eyeball-only.** The vision gate sends exactly one image; no frame-vs-anchor diff, no family-similarity metric. VLMs are weak precisely on subtle palette/proportion drift ([VIEScore, arxiv.org/html/2312.14867v1](https://arxiv.org/html/2312.14867v1)). → **R8**

### Complaint 2: "Characters, terrain, and environments don't look like the same game"

1. **Two unsynchronized style stacks** — cross-aware in prose, but with competing SSOT declarations for the palette (GameTheme.cs at asset-designer:31, ui-designer:100, director:136 vs art-spec.yaml at art-direction:8) and no derivation or equality rule. Generation conditions on one artifact; validation keys off the other. → **R1**
2. **No cross-model bridge.** Gemini backgrounds, PixelLab characters, and Tripo meshes share no palette file, no pixel-density rule, no light direction, no finish unification. The one-pixel-density "mixels" law — the top practitioner-cited cause of "assets look pasted together" ([saint11.art/blog/consistency](https://saint11.art/blog/consistency/)) — lives only in the orphaned skill. → **R4, R10, R11, R16**
3. **Import-time drift.** Two Editor snippets hardcode Bilinear; PPU defaults diverge three ways (100 vs 32 vs "pick one") with nothing recording the authoritative value. The same sprite family imports half-crisp, half-blurry depending on which skill imported it. → **R7, R10**
4. **Scene-level coherence is never measured.** composition.yaml's numeric budgets have no measuring tool; the composed-scene screenshot — the exact place cross-skill incoherence becomes visible — is never run through the critique script. → **R14**

### Complaint 3: "Skills work in isolation but fail combined"

1. **No ordered pipeline.** The director's Phase Routing has no sequencing, no handoff artifacts, no entry/exit gates; asset-designer is invisible to it entirely. Published agentic pipelines are all ordered, gated DAGs ([GameUIAgent](https://arxiv.org/html/2603.14724v1), [AutoUE](https://arxiv.org/pdf/2603.07106), [Schomay](https://blog.jeffschomay.com/lost-in-an-infinite-maze-building-a-real-time-generative-ai-game-assets-pipeline)). → **R9**
2. **The central gate is broken**, so even skills that *try* to comply get rejected (pixellab allowlist bug) or silently pass (opt-in checks, phantom booleans). Agents route around a broken gate — silently disabling the whole consistency system. → **R6**
3. **Assembly-time bypass.** The skill that places assets into scenes names raw generators directly and never touches the registry; registry-schema.md's own rule ("scene builders instantiate only registry prefabs") is unenforceable because the scene builder never loads it. → **R10**
4. **No cross-session persistence.** Nothing probes for an existing art-spec/registry, no canonical paths are provisioned at setup, and three root conventions coexist — so session 2 regenerates style from scratch. → **R9, R15**

---

## 4. Recommendations

Ordered by leverage (impact ÷ effort), with verification amendments applied. **Sequencing note:** R2 (schema extension) is a prerequisite for parts of R3, R5, R6, R10, and R11 — land it early even though the quick wins below can start immediately.

---

### Tier 1 — Quick wins (high impact, small effort): land these first

#### R3. Golden-anchor-first at the GAME level, not per-asset — *highest-leverage single fix for character inconsistency*
**Change:** `skills/unity-pixel-art/SKILL.md` (after line 35) — add a hard rule: only the first asset of a game (or an explicitly approved golden-anchor reroll) may use pixflux text-only; every subsequent character/prop/tile MUST be bitforge conditioned on the appropriate golden anchor via `--style-image`. Align with unity-art-direction's per-family golden model: the game golden seeds family goldens; family members condition on their family golden. Add a `golden_assets` field to the art-spec (does not exist today — R2 provides it).
**Mechanism:** turns each new character from an independent roll into a style-transferred derivation of an approved artifact — PixelLab's own documented consistency workflow ([pixellab.ai/docs/tools/consistent-style](https://www.pixellab.ai/docs/tools/consistent-style), [/docs/tools/style](https://www.pixellab.ai/docs/tools/style)).
**Amendments applied:** (a) PixelLab's Pro "Create images from style references" batch tool has **no API endpoint** (verified against `api.pixellab.ai/v1/openapi.json` — bitforge takes a *single* `style_image`); document it in `references/pixellab-api.md` only as a manual web-app step. (b) For cross-subject conditioning (goblin from knight's anchor) start at `--style-strength` ~50-70, not the 60-100 same-asset range — very high strength transfers *identity*, not just style; also document `extra_guidance_scale` and add a QA check for anchor-subject bleed. (c) Add an escape hatch for large canvases: style-referenced generation caps at 80×80 (tier 1) / 140×140 (tier 2+), while the skill permits 128+ boss canvases.
**Fixes:** CHARACTER INCONSISTENCY.

#### R4. One master palette, forced as `color_image` on every PixelLab call
**Change:** Add a build-master-palette step to unity-art-direction (emit `Assets/GameArt/_ArtDirection/master-palette.png` from art-spec ramps; record its path per R2). Rewrite ALL generation examples in `unity-pixel-art/SKILL.md:53-96` **and** `references/pixellab-api.md:56-85` to include the palette flag, add the rejection rule "any PixelLab call without the palette is invalid," and mirror in unity-animation's pixel track.
**Mechanism:** the live PixelLab OpenAPI accepts `color_image` on pixflux, bitforge, rotate, animate-with-skeleton, animate-with-text, and inpaint ([api.pixellab.ai/v1/openapi.json](https://api.pixellab.ai/v1/openapi.json)) — one swatch enforced end-to-end. Prompted palettes are not enforced; hard constraints must be supplied ([runware.ai](https://runware.ai/blog/retro-diffusion-creating-authentic-pixel-art-with-ai-at-scale)).
**Amendments applied:** (a) **The script plumbing already exists** — `generate_pixel_art.py` already threads `--palette`/`--color-image` through rotate (310-311, 502), animate-skeleton (335-336, 543), animate-text (354-355, 559), and inpaint (523); the remaining work is documentation, the master-palette artifact, and default-from-spec behavior. Effort is smaller than originally stated. (b) For derived frames/rotations, prefer the anchor's extracted sub-palette (subset of master) — forcing the full game palette on a 5-color coin's frames permits cross-asset color borrowing. (c) Make `_accepted_kwargs` (lines 126-139) fail loudly when the SDK silently drops `color_image` rather than just recording it in `sdk_skipped_kwargs`. (d) Keep `validate_sprite.py --palette` as the backstop — the strictness of `color_image` as a hard lock vs strong guidance wasn't empirically tested.
**Fixes:** CHARACTER INCONSISTENCY + ART DOESN'T COHERE (palette drift).

#### R7. Fix the hardcoded-Bilinear import snippets that blur pixel art
**Change:** `unity-asset-pipeline/references/editor-asset-pipeline.md` — ApplySpriteImport already accepts a `settingsFromContract` parameter it never uses; apply it (`ti.SetTextureSettings`) instead of the hardcoded `FilterMode.Bilinear` (line 47), set default-platform `textureCompression` (currently only the iOS override), and extend ValidateSpriteImport (63-72) to assert filterMode/compression/format against the contract — using `TextureImporter.GetAutomaticFormat(platform)` or the imported `Texture2D.format` for realized-format checks (GetPlatformTextureSettings returns the *requested* format). Parameterize the AssetPostprocessor's hardcoded PPU 100 (line 227) from the project PPU once R2 adds it (note: the hardcode currently applies only under `/Sprites/`/`/Approved/` paths; tiles/backgrounds get no PPU at all — a second gap to close). `unity-animation/references/animation-recipes.md:15` — read filterMode from the contract with Point shown as the pixel-track value (don't just swap one hardcode for another).
**Mechanism:** Unity's AssetPostprocessor + Presets are designed to enforce import settings automatically so they can't drift per-asset or per-skill ([docs.unity3d.com/ScriptReference/AssetPostprocessor.html](https://docs.unity3d.com/ScriptReference/AssetPostprocessor.html)).
**Fixes:** ART DOESN'T COHERE (same sprite family half-crisp, half-blurry).

#### R10. Bind scene-building skills to the registry and the spec's PPU
**Change:** `unity-gameplay-systems/SKILL.md:48` and `references/casual-templates.md` (line 5, the generator-direct handoff at 39-48, primitive prefabs at 79 and 96-112): replace generator-direct handoffs with *"all visible sprites/meshes/materials on gameplay prefabs must come from registry assets (unity-asset-pipeline); logic prefabs may wrap them; primitives allowed only while the registry is empty and flagged as placeholders in the ledger."* Add to the definition-of-done: primary visible surfaces use registry assets and pass the aaa-graphics scorecard, **or** remaining primitives are explicitly flagged as placeholders (keeps the "prove the loop with primitives" doctrine intact). `unity-game-layout/SKILL.md:106-111`: change the PPU law to "read the project PPU from art-spec.yaml (R2); never pick a local value" — with asset-contract's `pixels_per_unit` as fallback until R2 lands. Also redirect the other hardcoded PPU-100 defaults (unity-asset-pipeline/SKILL.md:46, editor-asset-pipeline.md:227, unity-image-generator/SKILL.md:274) to the spec value, or the divergence survives.
**Mechanism:** closes the assembly-time bypass and enforces saint11's one-pixel-density rule at the grid/PPU level ([saint11.art/blog/consistency](https://saint11.art/blog/consistency/)).
**Fixes:** ART DOESN'T COHERE + SPLINTERED SKILLS (assembly-time bypass).

---

### Tier 2 — Structural fixes (high impact, medium effort)

#### R1. Collapse the two style stacks into one SSOT: art-spec.yaml
**Change:**
- `unity-art-direction/SKILL.md`: declare art-spec.yaml the single style SSOT; style-guide.md, GameTheme.cs, and UI tokens are DERIVED views (add a `derived_artifacts` section to `references/art-spec-template.yaml`).
- `unity-asset-designer/SKILL.md` steps 1-2: read/write art-spec fields instead of owning an independent style-guide palette.
- `unity-game-director/SKILL.md` Step 2.6: change "For a structured way…" (line 119) to *mandatory before any production asset*; add a unity-asset-designer entry to Phase Routing (169-188); add "art-spec.yaml path + approval status" to the Ledger (205-216).
- `unity-ui-designer/SKILL.md` + `unity-graphics/SKILL.md`: add explicit input — read palette/lighting/post from art-spec; GameTheme.cs **color hexes** must equal art-spec hexes.
- **Reword the three existing contradictory SSOT declarations** or you end up with dueling SSOTs: unity-game-director/SKILL.md:136, unity-ui-designer/SKILL.md:100, unity-asset-designer/SKILL.md:19,31 → "runtime SSOT *derived from* art-spec.yaml."
**Amendments applied:** (a) Scope the equality rule to color hexes only — GameTheme.cs also carries typography/spacing/radii that have no art-spec source. (b) Extend the art-spec palette schema with **named semantic roles** (ground, panel, ink/text, accents), not just dominant/neutrals/accent arrays, or GameTheme/UI tokens aren't genuinely derivable. (c) Accurate framing: the stacks are *cross-referenced but not mechanically synchronized* (asset-designer:16 already acknowledges art-direction owns the spec; director line 179 does route to art-direction) — the fix tightens one-directional prose into derivation rules and gates. (d) For machine enforcement, extend `validate_asset_manifest.py` to compare GameTheme/contract hexes against the art-spec palette (today it checks only `style_id`).
**Mechanism:** one locked per-game style artifact all generation flows through — the invariant of every shipped-game pipeline ([InnoGames×Scenario](https://blog.innogames.com/innogames-x-scenario-streamlining-our-game-production/), [OpenAI](https://platform.openai.com/docs/guides/image-generation?image-generation-model=gpt-image-1), [Google](https://codelabs.developers.google.com/gemini-consistent-imagery-notebook)).
**Fixes:** SPLINTERED SKILLS (root cause) + ART DOESN'T COHERE.

#### R2. Extend the art-spec schema with the fields consistency actually needs — *prerequisite for R3/R5/R6/R10/R11*
**Change to `unity-art-direction/references/art-spec-template.yaml`:**
- **Pixel/craft block** (conditional on `finish`, nullable for non-tile games): `finish` (SKILL.md:48 already branches on it but it doesn't exist), `pixels_per_unit`, `base_render_resolution` (integer-scaling, e.g. 320×180 — [notkey.studio](https://notkey.studio/en/tutorials/choosing-the-right-render-resolution-for-a-pixel-art-game/)), `tile_size`, `char_tiles` ratio ([Slynyrd PB22](https://www.slynyrd.com/blog/2019/10/21/pixelblog-22-top-down-character-sprites)), `outline_style` using **PixelLab's exact enum strings** (`"single color black outline"` | `"single color outline"` | `"selective outline"` | `"lineless"` — never invented shorthands, per the project memory warning), `light_direction` and `dithering_policy` **marked as prompt-level tokens + vision-QA criteria** (no PixelLab API parameter exists for them), and palette extended to hue-shifted ramps ([Slynyrd PB1](https://www.slynyrd.com/blog/2018/1/10/pixelblog-1-color-palettes)) within the *existing* palette block.
- **Conditioning block:** `style_anchor_images: [paths]` (consumed one at a time by bitforge), `golden_assets: {family: path}`, `master_palette_png` specified as a PixelLab `color_image`-compatible swatch.
- **Characters block** (the ONE authoritative canon index — other files reference it): per character `canon_sheet`, `anchor_sprite`, `identity_string` (frozen verbatim description — [Retro Diffusion technique](https://runware.ai/blog/retro-diffusion-creating-authentic-pixel-art-with-ai-at-scale)), `skeleton_template` path, optional `seed`.
- **AssetBrief template** (lines 69-86): add matching `canon_sheet`/`identity_string`/reference fields.
- **asset-contract-template.yaml:** extend the *existing* provenance block (it already has `source.seed`, `prompt_hash`, `reference_pack`, `pixels_per_unit`) — add `canon_sheet`/`identity_string` and make `reference_pack` a list of resolvable file paths, don't duplicate fields.
**Amendments applied:** template is 94 lines; `rendering.outline` exists (what's missing is the pixel-specific enum); `tile_size` is a new proposed field, not an existing consumer expectation; seeds are weak identity in this toolchain (no seed param in pixellab-api.md, none in Gemini) — keep as optional provenance, emphasis on anchor paths + identity strings.
**Mechanism:** each practitioner craft rule (one density, tile-derived sizing, one outline, one light direction, ramped palette — [saint11](https://saint11.art/blog/consistency/), [Slynyrd catalogue](https://www.slynyrd.com/pixelblog-catalogue), [Lospec outlines](https://lospec.com/articles/pixel-art-outlines-part-2-using-color/)) becomes a machine-encodable field instead of a per-generation decision.
**Fixes:** CHARACTER INCONSISTENCY + ART DOESN'T COHERE.

#### R5. `--art-spec` consumption in all generation/QA scripts
**Change:** Add a shared `--art-spec PATH` flag (env-var + default-path fallback) to `unity-pixel-art/scripts/generate_pixel_art.py` (auto-fill palette swatch, canvas, view, outline/shading enums, style-image, PPU), `unity-image-generator/scripts/generate_image.py` (inject verbatim style-token paragraph + light_direction, attach anchor images — requires the multi-image support from R13), `validate_sprite.py`, and `critique_image.py` (load palette + finish). Update the invocations that actually hardcode palettes: `unity-pixel-art/SKILL.md:113-126`, `unity-image-generator/SKILL.md:138-143, 160, 174-178` (the asset-pipeline SKILL.md block already uses `--art-spec`).
**Amendments applied:** (a) Depends on R2 — the current template lacks most fields these scripts would read; effort is the high end of medium. (b) Canvas/view/palette are per-asset-family: spec supplies defaults, CLI can override per call. (c) Missing-spec behavior: **fail-unless-explicit-override** (`--no-art-spec`), not interactive confirmation (these are agent-run CLIs); apply strictness to production paths only — spec-less exploratory concepting stays legal. (d) Add `pyyaml` to the PEP 723 block or reuse the fallback parser from validate_asset_manifest.py. (e) Scope claim accurately: no *generation or per-image QA* script reads the contract today (validate_asset_manifest.py does accept `--art-spec` but checks only style_id).
**Mechanism:** contract as script input, not documentation — the pattern of production pipelines ([agent-sprite-forge provenance](https://github.com/0x0funky/agent-sprite-forge), [Schomay](https://blog.jeffschomay.com/lost-in-an-infinite-maze-building-a-real-time-generative-ai-game-assets-pipeline)). Kills the "one typo and the gate silently disappears" drift channel.
**Fixes:** SPLINTERED SKILLS + CHARACTER INCONSISTENCY (global-look half; per-character identity needs R8/R13).

#### R6. Fix the asset-pipeline validator so the gate actually gates
**Change to `skills/unity-asset-pipeline/scripts/validate_asset_manifest.py`:**
1. Add `"pixellab"` to the allowlist at line 207 (today **every pixel-art contract exits 2 "rejected"** while the skill's own template uses `generator: pixellab`); also sync SKILL.md:40's inline comment, which disagrees with the code in both directions (omits kitbash/vendor).
2. Make coherence checks default-on: resolve art-spec/composition from the contract (per-contract new fields; in registry mode use the existing `art_spec:`/`composition_profile:` keys) and FAIL when absent instead of skipping.
3. Validate `runtime.pixels_per_unit` against the spec's project PPU + uniformity across registry entries (**depends on R2** defining the field).
4. Compute `palette_valid` by invoking validate_sprite.py **as a subprocess** (it needs Pillow; this script is deliberately zero-dep) and fail loudly if it can't run; note its palette check is an average-distance heuristic — add an exact-membership/max-distinct-colors mode for pixel art. Compute `scale_valid` from sprite dims vs tile fields only when `runtime.type == sprite`; 3D scale_valid stays with the Editor import validator.
5. Fix registry path resolution by deriving project root from the registry path (the segment before `Assets/`) — the double-prefix bug manifests when cwd ≠ project root.
6. Align style_ids across `art-spec-template.yaml:7`, `composition-template.yaml:2`, `unity-asset-pipeline/SKILL.md:38` (`cozy_toy_diorama` vs `cozy_toy_diorama_v1` — following the shipped templates verbatim currently fails the gate), and add `schema` + `runtime.type` to the SKILL.md:34-59 minimum example (missing `schema` fails loudly; missing `runtime.type` silently skips all sprite checks).
**Mechanism:** deterministic schema/constraint validation before expensive generation/VLM review ([GameUIAgent](https://arxiv.org/html/2603.14724v1), [Schomay](https://blog.jeffschomay.com/lost-in-an-infinite-maze-building-a-real-time-generative-ai-game-assets-pipeline)); a gate that silently passes on omitted flags is the anti-pattern.
**Fixes:** SPLINTERED SKILLS + ART DOESN'T COHERE (the enforcement layer).

#### R9. Ordered art pipeline in unity-game-director + cross-session rediscovery
**Change:** Replace Phase Routing (`unity-game-director/SKILL.md:169-188`) with an ordered DAG with per-phase required input/output artifacts and gates (see §5). Extend `scripts/detect_unity_project.sh` to probe for `art-spec.yaml`, `composition.yaml`, `registry.yaml`, and canon sheets, and instruct the director to **RESUME** from found artifacts instead of re-deriving style. Add to Verification (~line 195): "every placed asset resolves to a registry entry; art-spec exists and all contracts validate."
**Amendments applied:** (a) **Preserve Core Doctrine #1/#2** ("ship a verified playable slice early"; "lean gates for a solo dev"): the DAG gates ART production and scene ART assembly only — gray-box gameplay/prototyping proceeds in parallel, and a prototype is never blocked on art-spec approval. Otherwise this reintroduces the documents-before-playable failure the skill exists to prevent. (b) Canon sheets need an on-disk convention before the detect script can probe for them — R2's characters block / a fixed `_ArtDirection/sheets/` path provides it. (c) "Every placed asset resolves to a registry entry" has no automated checker today; implement as an agent instruction (walk the scene via MCP, cross-check against registry.yaml) with a small scene-walk script as follow-up. (d) The canon gate must be track-aware: on the pixel track the canon artifact is the PixelLab anchor/reference sheet, not a Gemini turnaround.
**Mechanism:** all published agentic pipelines are ordered, gated architectures ([GameUIAgent](https://arxiv.org/html/2603.14724v1), [AutoUE](https://arxiv.org/pdf/2603.07106)); industry locks the style artifact FIRST and threads it through every call.
**Fixes:** SPLINTERED SKILLS (orchestration root cause) + cross-session CHARACTER INCONSISTENCY.

#### R11. Bind the 3D path to the style contract
**Change to `skills/unity-3d-generator/SKILL.md`:**
1. Hard input rule: image-to-3D MUST use a turnaround generated under the game's 2D style lock (canon sheet from R2's characters block — the field doesn't exist in the template today), never a fresh unconditioned concept; prompts embed the spec's verbatim style tokens. Tripo's 3D style is inherited from the 2D input — the 2D lock is the upstream root, and no major 3D generator offers trained style locks ([Rodin Gen-2.5 analysis, 80.lv](https://80.lv/articles/how-hyper3d-rodin-gen-2-5-is-bringing-production-level-control-to-ai-3d-generation)).
2. Scale: **consume the existing art-spec scale block** (`scale.unit_rule`, `character_height_m: 1.5`, `standard_door_height_m` — already in the template; don't add a duplicate `player_height_units`) — the gap is enforcement: add a post-import bounds-measurement step to `references/unity-import.md` that fails when a model's height is outside its role's range (today's entire scale treatment is `globalScale = 1.0f // fix Tripo scale if needed`).
3. Re-shade step: convert imported materials to the spec's `materials`/`rendering.shader_family` values (name the actual fields — no `material_profile` field exists in art-spec) using **Tripo's existing `texture_model` postprocess** (api-notes.md:40) or Unity-side conversion. Drop Meshy `image_style_url` or flag it as an optional new vendor integration — Meshy appears nowhere in the repo and a second 3D vendor worsens splintering.
4. Replace the SKILL.md:97 example (which prefab-wraps a raw FBX but bypasses contract/validation/registry) with the asset-contract → prefab-factory → registry flow.
5. unity-graphics: consume art-spec lighting/post; for machine-readable light direction, point at composition-template's `key_light_direction` or add a direction field to art-spec — don't create a second source of truth.
**Fixes:** ART DOESN'T COHERE (3D vs 2D) + SPLINTERED SKILLS.

#### R13. Make the designer→generator chain executable: multi-reference input, bidirectional handoff, remove hardcoded style
**Change:**
1. `unity-image-generator/scripts/generate_image.py`: accept repeated `--input-image`; implement "roles" as interleaved text parts ("Image 1 = character identity: …") — the Gemini API has no native role parameter. Fix the auto-resolution inflation at lines 210-221 by changing the default to a `None` sentinel (an explicitly passed `-r 1K` is currently indistinguishable from the default, so hi-res input sheets still inflate output). Nano Banana Pro supports blending up to ~6-14 input images with multi-subject consistency ([Google prompting docs](https://codelabs.developers.google.com/gemini-consistent-imagery-notebook)).
2. `unity-image-generator/SKILL.md`: mandatory input rule — production 2D assets for a project with canon sheets/style boards MUST attach them as references; concepts may skip. Make it enforceable via a discovery step (check art-spec conditioning block / registry / `Assets/**/Art/Refs`) — today the generator has zero references to asset-designer, so an agent loading only it produces canon-less production art.
3. `unity-asset-designer/references/prompt-templates.md:8-11`: bracket the remaining hardcoded fragments ("round friendly shape language," the blanket NOT-list) as placeholders filled from art-spec — resolving the doctrine conflict with image-generator's "never inject a house style" rule (SKILL.md:79,91) in the generator's favor. Update asset-designer SKILL.md:64 (singular `--input-image`) when multi-input lands.
**Fixes:** CHARACTER INCONSISTENCY + SPLINTERED SKILLS.

---

### Tier 3 — Consolidation (medium impact)

#### R12. Re-verify PixelLab docs against the live OpenAPI; adopt vendor consistency features *(small effort)*
**Change:** `unity-pixel-art/references/pixellab-api.md` + `generate_pixel_art.py`:
- The live spec (fetched 2026-07-01) has a **single `guidance_scale` (default 4.0)** on animate-with-skeleton — not `reference_guidance_scale` 1.1 / `pose_guidance_scale` 3.0 as documented (pixellab-api.md:38-39); `extra_guidance_scale` is deprecated ([api.pixellab.ai/v1/openapi.json](https://api.pixellab.ai/v1/openapi.json)). **SDK caveat:** PyPI pixellab 1.0.5 (latest, and the installed version) still only sends the legacy param names — so the fix requires a raw `requests.post` to `/animate-with-skeleton` (trivial), not a kwarg rename; document that tuning the old flags through the SDK is likely a no-op (server default governs). Also sync other drifted defaults found: bitforge `text_guidance_scale` live default 8.0 (docs say 3.0); animate-with-text `image_guidance_scale` 1.4 vs 1.5.
- **Update the project memory file** `~/.claude/projects/.../memory/pixellab-skill-corrections.md` in the same pass — it enshrines the stale 1.1/3.0 values as ground truth and will re-poison future sessions.
- Scope the 16/32/64 canvas-quality warning to **bitforge's `skeleton_keypoints`** (where the spec attaches it; animate-with-skeleton explicitly supports up to 256), and reconcile the skill's 48×48 skeleton example with it.
- Skeleton-template library: one client-authored biped keypoint JSON per game reused for every humanoid (uniform proportions across the cast; path stored in R2's characters block) — a local workflow, per PixelLab's "a skeleton can be saved and reused for other characters" ([pixellab.ai/docs/tools/animate-with-skeleton](https://www.pixellab.ai/docs/tools/animate-with-skeleton)). Drop "fixed-head" from the API-facing fix — it appears nowhere in the v1 OpenAPI (web-tool only).
- Document the freeze-frames/`init_images`/inpaint repair loop for single bad frames instead of full-strip re-rolls (needs small script additions: per-frame `init_images`/`mask_images` support). Document `--seed` as reproducibility metadata only — never a cross-pose consistency mechanism.
**Fixes:** CHARACTER INCONSISTENCY (cast proportions, frame drift).

#### R15. Canonical artifact paths in unity-project-setup; reconcile the filesystem roots *(small effort)*
**Change:** `unity-project-setup/SKILL.md`: reserve the pipeline paths at setup (`_ArtDirection/` with art-spec.yaml + palettes/ + references/ — reuse the names already sketched in art-spec-template.yaml:91-93, don't invent a fourth convention; `Approved/` with registry + contracts; `Source/` staging), with `.gitkeep` files so empty dirs survive git; add unity-art-direction + unity-asset-pipeline to "Where this sits."
**Amendment applied (important):** the split is **three-way**, not two — project-setup's own doctrine prescribes everything under a single `Assets/<Game>/` root (SKILL.md:55,70), which both `Assets/GameArt/` and `Assets/Art/*` violate. Either nest the art tree under `Assets/<Game>/Art/{_ArtDirection,Approved,Source}` or explicitly amend the one-root rationale to carve out a generated-art exception — do not silently pick a root that breaks the doctrine of the skill being edited. Note the sweep is bigger than five files (`Assets/Art` appears ~100 times across 17 files); the cheap v1 is documenting both existing roots as reserved (they're used consistently today), with unification as follow-up polish. Fold unity-pixel-art's `Assets/Art/Pixel/` and unity-3d-generator's output paths into the staging convention.
**Mechanism:** R9's cross-session rediscovery only works with deterministic paths ([agent-sprite-forge](https://github.com/0x0funky/agent-sprite-forge), [Schomay](https://blog.jeffschomay.com/lost-in-an-infinite-maze-building-a-real-time-generative-ai-game-assets-pipeline) both rely on fixed artifact locations for resumability).
**Fixes:** SPLINTERED SKILLS + cross-session CHARACTER INCONSISTENCY.

#### R14. One scorecard hierarchy + scene-level automated coherence scoring; animation through the pipeline gate *(medium effort)*
**Change:**
1. Declare precedence in unity-game-director + unity-aaa-graphics: aaa-graphics scorecard = final whole-screen gate; art-direction 0-2 gates = per-asset gate feeding it; director's Step 2.6 rubric superseded once art-spec exists. Add a "characters on-model vs canon sheet" axis (uses R8's `--reference`).
2. `unity-scene-composition/SKILL.md:42`: mandatory automated pass on every composed-scene screenshot — **split the checklist**: numeric budgets (density cost vs 24, occlusion vs 8%, screen-height %) are measured **deterministically from Unity scene data via MCP** (sum contract `density_cost` in frustum, renderer bounds vs camera), not by the VLM; the VLM scores only qualitative dimensions (focal read, layer contrast, grounding, cohesion) via a scene-mode rubric (a sibling `critique_scene.py` or scene-mode in critique_image.py — the current axes are per-asset). Sequence after R8 (needs `--reference`). Calibration period: low scene scores trigger re-roll/review, not hard-block.
3. `unity-animation/SKILL.md:95-102`: add unity-asset-pipeline to "Where this sits" — finished sheets/clips/controllers ship via contract + registry like statics (needs minor contract-template extensions for clip lists/controller paths, and a BeautyCell policy for animated assets, e.g. score a designated key pose).
**Mechanism:** fixed-rubric VLM scoring with bounded re-rolls ([GameUIAgent](https://arxiv.org/html/2603.14724v1)); VLMs are reliable for gross whole-scene coherence judgments ([VIEScore](https://arxiv.org/html/2312.14867v1)).
**Fixes:** ART DOESN'T COHERE + AAA-QUALITY (the on-screen gate).

#### R16. Fold in the orphans: unity-2d-sprite-games + audio *(medium effort)*
**Change:**
1. Migrate the orphan's genuinely unique content into the repo: the generation-side texel-density/chunkiness law (Rule 0 — ground texel size matches sprite pixel size, unified light model across sprites and 3D ground, which appears nowhere in the repo), Y-axis-only billboarding, quarter-view framing, and the valuable chroma-key/corner-sample/autocrop recipe → into unity-scene-composition + R2's pixel block + pixel-import.md. Fork its sprite routing by style: pixel → PixelLab; painterly/HD-2D/Don't Starve → Gemini + chroma-key (don't blanket-route everything to PixelLab — it's pixel-native only). Add the actual pixel-density axis to the aaa-graphics scorecard so the orphan's citation stops being phantom. **Then update or delete the stale `~/.claude/skills` copy** — a repo-only change can't fix it; it will keep matching "pixel art game" triggers and routing pixel finals to Gemini.
2. Audio: add an audio-direction block to art-spec (shared prompt prefix/instrument palette/mood tokens keyed to style_id; pinned voice — note a pinned voice applies only to TTS; SFX identity rests entirely on the shared prompt tokens); per-clip contract + registry entries with a **new audio-specific runtime section** (load type, Vorbis quality, force-to-mono, loop flag, target LUFS — the current runtime block is sprite/model-shaped); seamless-loop check as a **local crossfade post-process**, not an assumed ElevenLabs feature; fix the leftover Three.js strings in `unity_audio_asset.py`.
**Fixes:** SPLINTERED SKILLS + ART DOESN'T COHERE (genre- and audio-level).

---

### Tier 4 — The automated identity QA layer (high impact, large effort — descope option noted)

#### R8. Reference-comparison critique, family-similarity gate, frame-vs-anchor diff
**Change:**
- **(a)** `critique_image.py`: add `--reference PATH(s)` (contents become [candidate, reference(s), instruction]) and an `on_model_vs_reference` axis **on the existing 0-3 scale** — `palette_adherence` already exists (line 53), and rescaling to 1-10 would break `select_best_candidate.py`'s hardcoded assumptions (`subject_correct > 1`, default 2.0, `--pass-threshold 2.0`). This closes the critical gap that the vision gate literally cannot see the canon sheet (lines 149-152 send exactly one image).
- **(b)** *Optional/demotable:* `check_family_coherence.py` — CLIP embeddings with per-family centroids over registry-approved assets. Caveats: needs a new local torch/open_clip or ONNX dependency (~1-2GB); vanilla CLIP is semantics-dominated and noisy on 32-64px sprites; a *global* centroid across characters+tiles+icons is near-meaningless — restrict to per-family/per-role, and treat the ~0.85 floor ([SCS, arxiv.org/pdf/2404.08799](https://arxiv.org/pdf/2404.08799)) as uncalibrated until tuned on real accept/reject pairs. Prefer deterministic palette-histogram/outline-weight metrics first. Demoting (b) shrinks R8 to medium effort.
- **(c)** `unity-pixel-art/scripts/compare_frames_to_anchor.py`: deterministic palette-membership, bbox/baseline, and silhouette-IoU diff of each animation frame vs the anchor — with a **loose** IoU floor (an identity-swap detector; correct-but-different poses legitimately score low) weighting palette/baseline/bbox-height more heavily. Mandate in unity-pixel-art/SKILL.md:134-136 and unity-animation/SKILL.md:50-53 (today's frame rejection is manual eyeballing with no tool).
- **(d)** Re-roll policy in unity-asset-pipeline: auto-re-roll only below the quality ceiling, expressed **scale-agnostically** (≈2.25/3 on the existing scale, equivalent to GameUIAgent's 7.5/10 finding — assets above it gain ~0 from re-rolls, r=-0.96 [arxiv.org/html/2603.14724v1](https://arxiv.org/html/2603.14724v1)); target the two worst dimensions; keep best-seen; cap at 2 iterations. Scope auto-rerolls to the Gemini route; for pixel assets prefer inpaint repair ("fix, don't reroll," pixellab-api.md:86,101).
**Mechanism:** deterministic pixel checks first, VLM second — VLMs are near-human on gross judgments but weak on subtle palette/proportion drift ([VIEScore](https://arxiv.org/html/2312.14867v1)).
**Fixes:** CHARACTER INCONSISTENCY + AAA-QUALITY (QA that actually catches drift).

---

### Optional escalation (not in the verified set, flagged by research): per-game style fine-tune tier
Once ~12-15 golden assets pass the gates, the approved registry is exactly a LoRA training dataset: Scenario-style custom style models train on 10-15 curated images ([help.scenario.com](https://help.scenario.com/en/articles/train-a-style-model/)); FLUX klein LoRAs train in ~1 hour for under a few dollars via hosted APIs ([huggingface.co/blog/black-forest-labs/flux-2-klein-lora](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora)). This is the weights-level lock shipped studios use ([InnoGames](https://blog.innogames.com/innogames-x-scenario-streamlining-our-game-production/)) and survives hundreds of assets where per-call reference conditioning eventually drifts. Worth a new skill *after* the contract system above is solid — it depends on the registry being trustworthy.

---

## 5. Proposed Target Pipeline

The end-to-end "make me a game" flow the director should enforce. **Gates apply to ART production and scene ART assembly only** — gray-box gameplay proceeds in parallel from step 0, per the ship-a-playable-slice-early doctrine.

```
0. unity-project-setup
   └─ provisions reserved paths (R15): _ArtDirection/ (art-spec.yaml, palettes/,
      references/, sheets/), Approved/ (registry.yaml, contracts/), Source/
   └─ detect_unity_project.sh probes for existing art-spec/registry/composition/
      canon sheets → RESUME, never re-derive (R9)

1. unity-game-director: north-star (Step 2.6)
   └─ [parallel track: unity-gameplay-systems gray-boxes the loop with
      flagged placeholder primitives — never blocked on art]

2. unity-art-direction  ──────────────── GATE: art-spec.yaml approved (R1)
   └─ writes art-spec.yaml (extended schema per R2: semantic palette roles,
      pixel/craft block, conditioning block, characters block, scale)
   └─ emits master-palette.png (R4)
   └─ derived views generated FROM it: style-guide.md, GameTheme.cs hexes,
      UI tokens (R1)

3. unity-asset-designer ──────────────── GATE: canon per recurring character
   └─ per character: canon sheet (pixel track: PixelLab anchor sheet;
      non-pixel: Gemini turnaround) + frozen identity_string + skeleton
      template, registered in art-spec characters block (R2, R9, R12)
   └─ game golden anchor approved → family goldens derived from it (R3)

4. unity-scene-composition
   └─ composition.yaml (camera, layers, budgets, key_light_direction)
      agreeing with art-spec

5. Generators — every call reads --art-spec (R5), no hand-typed style:
   ├─ unity-pixel-art: bitforge conditioned on golden anchor (R3),
   │  master palette as color_image on EVERY call (R4), shared skeleton
   │  template per humanoid (R12)
   ├─ unity-image-generator: canon sheet + style board attached as
   │  multi-reference input (R13), verbatim style tokens from spec
   ├─ unity-3d-generator: image-to-3D from style-locked turnaround only;
   │  post-import bounds check vs spec scale; re-shade to spec
   │  materials (R11)
   └─ unity-audio-generator: audio-direction block prompt prefix (R16)

6. QA — deterministic first, VLM second (R8):
   validate_sprite.py --art-spec → compare_frames_to_anchor.py (animation)
   → critique_image.py --reference <canon/golden> → bounded re-roll
   (worst 2 axes, keep best, cap 2; inpaint-repair for pixel)

7. unity-asset-pipeline ──────────────── GATE: validator exit 0 (R6)
   └─ contract (canon_sheet, identity_string, resolvable reference paths)
   → prefab factory (contract-driven import: filter/compression/PPU
     asserted post-apply, R7) → approved registry → BeautyCell

8. Scene assembly (unity-gameplay-systems / unity-scene-composition)
   └─ visible sprites/meshes/materials from REGISTRY ONLY; logic prefabs
      may wrap them; PPU from art-spec (R10)

9. Whole-screen gate (R14): numeric budgets measured from scene data via
   MCP + scene-mode VLM rubric vs golden screen → aaa-graphics scorecard
   (final authority; includes on-model-vs-canon and pixel-density axes)

Ledger (every session): art-spec path + approval status, golden anchors,
canon sheets, registry state, latest scorecard — so session N+1 resumes.
```

**Suggested implementation order:** R2 (schema) → R6 + R4 + R7 (fix the broken gate + quick wins; R4 is mostly docs) → R3 + R10 → R1 + R5 → R9 + R15 → R12 + R13 → R11 → R14 + R16 → R8 (with the CLIP gate demoted to optional).

---

## 6. Appendix

### A. Rejected recommendations
**None.** All 16 recommendations survived 3-lens adversarial verification with zero refutations. Every recommendation did, however, accumulate amendments — the most consequential (folded into §4 above):

- **Already-implemented work removed from scope:** R4's script plumbing (`--palette`/`--color-image` already threaded through rotate/animate/inpaint in generate_pixel_art.py) — the gap is docs and workflow, not code. R2/R11: art-spec already has a metric scale block; asset contracts already carry seed/prompt_hash/reference_pack — extend, don't duplicate.
- **Vendor-reality corrections:** PixelLab's Pro batch style-reference tool has no API endpoint (single `style_image` per bitforge call only); "fixed-head" is web-tool-only; the PyPI SDK (1.0.5) lags the live API's `guidance_scale` schema, so R12 needs a raw HTTP call, not a flag rename; Meshy is a net-new vendor dependency and was replaced with Tripo's existing `texture_model`.
- **Overstatement corrections:** the two style stacks are cross-referenced (just not mechanically synchronized); the director does route to art-direction (just optionally, ungated, unledgered); unity-animation has manual rejection rules (just no automated frame gate); SKILL.md:97 does create a prefab (it bypasses contract/validation/registry, not prefab creation).
- **Doctrine-protection amendments:** R9/R10's gates must not block gray-box prototyping (ship-playable-early doctrine); R15 must not silently break project-setup's single-root doctrine; R13/R5 must keep spec-less exploratory concepting legal.
- **Feasibility downgrades:** R8's CLIP family gate is the weakest verified component (heavy dependency, out-of-distribution for small sprites, uncalibrated threshold) — recommended demotion to optional, with deterministic palette/silhouette metrics as the primary automated identity check.

### B. Evidence caveats
- Internal "Audit N gap M" citations reference workflow-internal artifacts not present in the repo; however, every repo-checkable fact they assert was independently verified against the files (grep/line-level).
- Two research claims are plausible-but-unconfirmed as direct sourcing: the Retro Diffusion founder quote on palette limits (product tooling is consistent with it) and Schomay's validate-before-generate ordering (confirmed for agent-sprite-forge, snippet-level only for Schomay). Neither is load-bearing for any recommendation.
- Whether PixelLab's `color_image` is a strict hard lock vs very strong guidance was not empirically tested (no paid call made); `validate_sprite.py --palette` is retained as the backstop regardless.
- Live-API claims (guidance_scale schema, deprecations, `color_image` endpoint coverage, canvas caps) were verified against `api.pixellab.ai/v1/openapi.json` fetched 2026-07-01.
