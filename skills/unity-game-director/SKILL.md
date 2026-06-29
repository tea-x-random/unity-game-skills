---
name: unity-game-director
description: "Primary entrypoint for building casual iOS games in Unity. Use by default for any Unity work: build-a-game, prototype, vertical slice, upgrade, polish, premium, 2D or 3D casual, hyper-casual, puzzle, runner, arcade, release-ready, or App Store requests. Triggers when the working directory is a Unity project (Assets/, ProjectSettings/, Packages/manifest.json present). Detects the Unity version, drives the Unity Editor through the unity-mcp-bridge skill, routes through gameplay/graphics/UI/audio/3D/2D-asset/debug/QA phases, and verifies a real playable slice with Play Mode tests and screenshots instead of producing only design docs. Loads sibling unity-* skills so the user does not pick skills manually."
---

# Unity Game Director

Own the end-to-end outcome of a casual iOS game built in Unity. Build a verified playable loop, route the right phases, drive the Editor through MCP, and never call a design document or a primitive-only scene a finished game.

## Core Doctrine (learned from real Claude+Unity projects)

These three rules override convenience. They are why this skill set exists.

1. **Ship a verified playable slice early, not documents.** The most common failure of AI game studios is generating epics, ADRs, and specs for days with no running game. Get a controllable character / interactable on screen in the first working session, verify it runs, then iterate. Planning is in service of a playable build, never a substitute for one.
2. **Keep gates lean for a solo dev.** Do not stack a confirmation prompt at every micro-step. Ask the user at genuine branch points (game concept, art direction, scope, irreversible/billable actions) and otherwise proceed with sensible defaults. Batch decisions.
3. **Edit Unity through the Editor, not raw YAML.** `.unity` scenes, `.prefab`, `.asset`, and `.meta` files are GUID/fileID-linked YAML — hand-editing corrupts references. All scene/prefab/component changes go through the `unity-mcp-bridge` (CoplayDev unity-mcp tools) or generated Editor scripts. C# scripts are plain text and safe to edit, but are not "done" until they compile clean in the Editor.

## Step 0 — Confirm this is a Unity project and pin the version

Run the detection probe before planning. Branch all engine guidance on the detected version.

```bash
bash ~/.claude/skills/unity-game-director/scripts/detect_unity_project.sh
```

It reports: Unity project yes/no, `m_EditorVersion` from `ProjectSettings/ProjectVersion.txt`, render pipeline, key packages (Input System, Addressables, URP, Cinemachine, glTFast, Test Framework), and iOS build target presence.

**Version gate (critical):** the model's built-in Unity knowledge is roughly Unity 2022.3 / early Unity 6.0. For Unity 6 (6000.x) the Input System, UI Toolkit, DOTS, RenderGraph, and Build Profiles differ, and the **6.1–6.5 tech-stream** (6000.1–6000.5) moves further: hard-obsoleted APIs (e.g. IMGUI `TreeView` became generic in 6.5), new core packages (Serialization is core in 6.5), expanded 2D physics worlds, etc. So when on Unity 6.x:

- **Pin packages to the EDITOR's own recommendations, not memory.** Read `<EditorPath>/Unity.app/Contents/Resources/PackageManager/Editor/manifest.json` for the exact versions this Editor ships, and align `Packages/manifest.json` to them. A package version that predates the Editor can fail to compile and throw the project into Safe Mode (see `unity-debug-profiler`). Delete `packages-lock.json` after manifest edits to force a clean re-resolve.
- **Verify APIs against the matching docs / live Editor** before writing C#, shaders, or UI — `unity_reflect`/`unity_docs` (MCP) or `https://docs.unity3d.com/<version>/Documentation/` (e.g. `.../6000.5/...`). Do not write from memory.
- Record the exact version in the ledger and state which knowledge gap applies.

This skill set was validated on Unity 6.5 (6000.5). Keep its guidance current with the installed Editor's version — when a newer point release changes an API or package baseline, update the relevant `unity-*` skill rather than working around it silently.

## Step 1 — Stand up the execution layer (MCP)

Load `unity-mcp-bridge/SKILL.md` and confirm the Editor is reachable before any build work:

- The Unity Editor must be **open and running** with the `com.coplaydev.unity-mcp` package installed; MCP talks to a live Editor, not files on disk.
- Confirm the MCP status reads **Connected** and the `mcpforunity://editor/state` resource shows `ready_for_tools=true`, `is_compiling=false`, `is_domain_reload_pending=false` before issuing commands.
- Enable the tool groups the work needs — only `core` is on by default. Enable `vfx`, `animation`, `ui`, `testing`, `scripting_ext`, `docs` via `manage_tools(action="enable_group", ...)` as phases require.
- Expect a ~5s connection drop after every script compile / package change (domain reload); build in wait-and-retry. See `unity-mcp-bridge/references/reliability.md`.

**MCP-awareness (applies to every unity-* phase):** the bridge and all sibling skills are MCP-aware — they prefer driving the live Editor through `unity-mcp-bridge` when it's connected. First **check availability**: `claude mcp list | grep -i unity` must show `✔ Connected` and the `manage_scene`/`read_console`/… tools must actually appear in tool search. "Registered" ≠ "connected." If the MCP is **absent or "✘ Failed to connect,"** do one of:

1. **Give the user setup instructions** to bring it up (see `unity-mcp-bridge` › Availability check & troubleshooting): install the `com.coplaydev.unity-mcp` package, `claude mcp add … http://127.0.0.1:8080/mcp`, then Unity **Window → MCP for Unity → Start/Connect** until it reads Connected (needs `uv`/Python 3.10+).
2. **Use the no-MCP fallback** (author C# + a `[MenuItem]` builder, then headless `Unity -batchmode -runTests`/`-executeMethod` and grep logs) so you still make verified progress.

Either way, say explicitly which path you used; never claim live-Editor actions (scene edits, screenshots, Play Mode) that did not happen.

## No-Editor fallback — bootstrap a project on disk

When Unity is not installed and/or no live MCP is available (common in headless/CI/agent runs), you
can still author a complete, openable project from files alone — do this instead of stalling:

- **Create a valid project skeleton:** `Packages/manifest.json` (URP/2D, Input System, TMP, Test
  Framework, `com.coplaydev.unity-mcp`, …), `ProjectSettings/ProjectVersion.txt` (pin a Unity 6 LTS;
  Hub tolerates a near patch), and an `Assets/` tree. Unity regenerates the rest of ProjectSettings
  on first open. Use asmdefs (a `noEngineReferences` Core for pure logic that unit-tests fast).
- **Author all C# and EditMode tests directly** — these are plain text and safe to write.
- **Assemble the scene with a `[MenuItem]` Editor scene-builder**, not by hand-editing `.unity`/
  `.prefab` YAML (which is GUID/fileID-linked and corrupts easily). Build the canvas, prefabs,
  ScriptableObjects and wire private `[SerializeField]` refs via `SerializedObject` in code. The user
  opens the project once and clicks the menu item to get a wired, playable scene.
- **Generate assets to disk** (image/audio/3D) into `Assets/`, with an "Import Generated Art" menu
  that sets mobile import settings (Sprite, iOS ASTC) and wires the theme.
- **State the boundary honestly:** report that the project is code-complete but **not yet compiled or
  run**, and list the one-time manual steps (install Unity, open, run the build menu, Play). Never
  claim scene work, a clean compile, or screenshots that did not happen.

## Step 2 — Decide 2D vs 3D and load the right sibling skills

Casual iOS games split into two asset pipelines. Route on the concept:

- **2D casual** (match-3, puzzle, tappers, hyper-casual): lean on `unity-image-generator` (sprites, UI, backgrounds), Unity 2D (Sprite Renderer / Sprite Atlas), UI Toolkit or uGUI. The 3D generator is usually not needed.
- **3D casual** (runner, stacking, .io, physics toys): lean on `unity-3d-generator` (Tripo text/image→3D, rigging, animation), URP mobile rendering.
- **Mixed** projects load both.

Load these sibling `SKILL.md` files before implementation for broad/premium work (try `../<name>/SKILL.md`, then `~/.claude/skills/<name>/SKILL.md`, then `~/.codex/skills/...`, then `~/.agents/skills/...`):

- `unity-mcp-bridge/SKILL.md` — always, it is the execution layer.
- `unity-gameplay-systems/SKILL.md` — architecture, C#, Input System, scene/prefab assembly, 2D + 3D casual templates, game feel.
- `unity-game-layout/SKILL.md` — **board/grid coordinate systems**: load whenever a game has a grid/board, pieces on tiles, tap-to-cell picking, isometric/2.5D/faux-perspective layout, depth sorting, or camera-fit/safe-area concerns. It owns the single-source-of-truth `CellToWorld`↔picking discipline; route any "pieces don't sit on tiles / taps hit the wrong cell / board misaligned" bug here.
- `unity-graphics/SKILL.md` — URP mobile rendering, lighting, materials, perf-safe visuals.
- `unity-ui-designer/SKILL.md` — UI Toolkit / uGUI, safe areas/notch, touch controls.
- `unity-debug-profiler/SKILL.md` — console errors, domain-reload recovery, profiler, mobile perf.
- `unity-qa-release/SKILL.md` — Play Mode tests, iOS build (IL2CPP/ASTC/Xcode), App Store readiness.

Load the asset generators before deciding "assets not needed" when the game has characters, enemies, props, sprites, backgrounds, icons, UI art, music, or SFX:

- `unity-3d-generator/SKILL.md`, `unity-image-generator/SKILL.md`, `unity-audio-generator/SKILL.md`.

**Phase ordering for foundations & design.** For a new or team project, establish `unity-project-setup` **first** — source control (.gitignore/LFS/meta-file discipline), folder + asmdef architecture, package management, versioning, secrets-per-env, and CI/CD basics — before scaffolding gameplay, so the engine-free Core asmdef and clean git history exist from day one. And route `unity-game-economy` in at **design/concept time alongside Step 2.x** (with the aesthetic north-star and novel-mechanic scoping): the economy & meta-progression — currencies, sources/sinks, progression pacing, reward schedules, IAP catalog — shape the core loop, so design them up front rather than bolting them on after a slice exists.

## Step 2.5 — Scope a novel or ambiguous mechanic BEFORE building it

Trigger this whenever a request names a mechanic you cannot fully simulate in your head — anything "unusual," "new," a twist on a known genre, or where you'd be guessing at the rules (a reference puzzle game's cross-face "Cube" mechanic is the canonical example: the director jumped to building, and the first rule designs were so under-constrained the puzzle had ~14,000 solutions — only *measured* after building). Do NOT start art/UX/scene work until this gate passes. The cost of skipping it was multiple full rule redesigns plus repeated rendering reworks.

This is the standard "prototype the riskiest thing first / find the fun before you commit to production" discipline ([Rami Ismail on prototypes vs. vertical slice](https://ltpf.ramiismail.com/prototypes-and-vertical-slice/); [Tono — vertical slice](https://tonogameconsultants.com/vertical-slice/)): a throwaway prototype answers *can this even work*, cheaply and disposably, before any fidelity is invested.

1. **Write a crisp one-paragraph spec + a worked example — get it agreed before building.** State the rules as testable constraints, not vibes. Include a concrete worked example the user can check ("a 5×5 grid has exactly one piece per row and per column; regions wrap across edges; no two pieces touch, including across an edge; here is one valid filled board: …"). A one-page spec with explicit *design pillars* is the standard filter — every later mechanic/art decision is checked against the pillars, and anything that doesn't serve them is cut ([gamedesignskills — design pillars](https://gamedesignskills.com/game-design/design-pillars/); [one-page GDD](https://gamedevbeginner.com/how-to-write-a-game-design-document-with-examples/)). If you cannot write the worked example, you do not understand the mechanic yet — go to step 4.

2. **Name the make-or-break property and MEASURE it with a throwaway prototype FIRST.** Every novel mechanic has one property that decides whether it works at all. For a logic puzzle that property is *"does every generated level have exactly one solution?"* — and the only way to know is to count, not to assume. Write a disposable solver/counter (pure C#, no engine refs, no art, no UI — runs in an EditMode test or `execute_code`) and measure before committing to anything visual:
   - Counting solutions with a backtracking solver capped at 2 is the established way to prove uniqueness before a level ships ([101computing — Sudoku generator](https://www.101computing.net/sudoku-generator-algorithm/); [thonky — solution count](https://www.thonky.com/sudoku/solution-count)). The reference project's eventual approach is exactly this: `CubeSolver.CountSolutions(regions, cap=2)`, `TrySolve`, and `FindAlternate` for uniqueness repair (`Assets/<YourGame>/Scripts/Core/CubeSolver.cs`, `CubeGenerator.cs`). Had the counter been written *first*, the 14,000-solution "ring" design would have been rejected in minutes instead of after a full build.
   - Generalize the property by mechanic type: puzzle → unique/solvable solution count; physics toy → does the core interaction feel right at one tuned instance; runner/arcade → is the moment-to-moment loop fun in a gray-box. Measure or play-prove that ONE thing in a gray-box before art, audio, or polished UI.

3. **Decompose the mechanic into independently-verifiable pieces** (the reference Cube mechanic split into: geometry/adjacency math → solver/counter → generator → board state → presentation). Build and unit-test the pure-logic pieces (the `noEngineReferences` Core asmdef) and prove the make-or-break property on them BEFORE any GameObject, shader, or tap path exists. Presentation/interaction reworks are expensive; rule reworks on pure C# are cheap — front-load the cheap ones.

4. **Surface ambiguity back to the user instead of guessing.** When the spec has a genuine fork (the reference Cube mechanic went ring → 2-pieces/face → full-Queens-per-face; board size 4×4 vs 5×5 hinged on how many distinct layouts exist — [Hertzsprung's problem / OEIS A002464]), present the 2–3 viable rule variants with their concrete trade-offs (measured solution counts, layout variety, difficulty) and let the user choose. One clarifying question at the real branch point is far cheaper than building the wrong rules and tearing them out. This is a legitimate "genuine branch point" under Core Doctrine #2 — batch the fork with the concept/art-direction questions.

**Gate to pass before art/UX:** spec + worked example agreed ✓, make-or-break property measured on a throwaway prototype (not assumed) ✓, mechanic decomposed with pure-logic pieces unit-tested ✓, ambiguous forks surfaced to the user ✓.

## Step 2.6 — Aesthetic direction is a first-class EARLY deliverable

A reference casual game's look churned through many passes (several distinct directions and multiple palette/typography reworks; glossy buttons → flat and back) because no named visual target was agreed up front — every pass was a fresh guess at "what does *pleasing* mean here." Fix: pin the aesthetic target as an explicit deliverable at concept time, the same way you pin gameplay scope, then converge in **1–2 passes** with a rubric and screenshots instead of many. Most designs converge within two iterations *when there is a target to converge toward* ([design review iteration](https://www.markup.io/blog/design-review-checklist/)). For a structured way to capture this north-star, route to `unity-art-direction`, which records it as a locked, machine-readable `art-spec.yaml` single-source-of-truth (style preset, palette, materials, lighting, scale, mobile budgets, acceptance) before any art is mass-generated.

1. **Agree a named visual north-star up front (a genuine branch point — ask the user).** Capture it in the ledger as a short, concrete art-direction statement, not an adjective:
   - **Reference style:** a named style + 1–2 real touchstones — pick what fits your game, with no single style as the default (e.g. flat-pastel à la *Two Dots* / *I Love Hue*, glossy candy à la *Royal Match*, minimal ink, or neon-retro). A mood board / reference set is the standard alignment tool — it pins tone, palette, and texture before any asset is made and prevents exactly this kind of churn ([Milanote — game design mood board](https://milanote.com/guide/game-design-moodboard); [Numberanalytics — mood boards in game art](https://www.numberanalytics.com/blog/ultimate-guide-mood-boards-game-art)).
   - **Palette:** 4–7 named colors (ground, panel, text/ink, 1–3 accents) with the contrast intent stated concretely — e.g. "a dark ink on a light ground, with a few saturated accent regions", whatever the chosen direction is.
   - **Typography:** one font family + the mood word it carries (e.g. a rounded sans for a calm/friendly mood, or a bold geometric for an energetic one — and confirm it covers any non-Latin scripts your game needs).
   - **Mood / "what pleasing means here":** 3–5 words (e.g. calm, high-contrast, minimal — or playful, bold, energetic) and an explicit anti-target ("not busy, not glossy, not desaturated") — the anti-target is what stops the next pass from drifting.
   - **Finish:** flat vs glossy vs material — decide once (the reference project flip-flopped glossy↔flat across iterations for want of this).

2. **Hold a fast screenshot-review loop against a concrete rubric.** After each visual pass, capture a real Screen-Space-Overlay screenshot via MCP (`manage_camera screenshot`) at a target portrait resolution and score it 1–10 on a fixed rubric, then list the top 2–3 concrete fixes for the next pass. Score these axes ([design review checklist](https://www.markup.io/blog/design-review-checklist/); divergent-then-convergent critique, [IxDF — design critiques](https://ixdf.org/literature/topics/design-critiques)):
   - **Palette & contrast** (matches the north-star colors; text readable on its ground)
   - **Typography** (one family, consistent sizes/weights, no tofu/missing glyphs)
   - **Hierarchy & spacing** (clear focal point, intentional negative space, aligned)
   - **Finish consistency** (every element flat *or* every element glossy — never mixed; this was the reference project's recurring slip)
   - **Cohesion with the north-star** (would a stranger name the agreed reference style from this screenshot?)
   - Gate: do not call visuals "done" below the agreed bar (the reference project used an ~8/10 average). Converge in 1–2 passes; if you're on pass 3+, the north-star wasn't concrete enough — go back to step 1, don't keep guessing.

3. **Single source of truth for the palette/theme** so passes don't regress: keep theme values in code (e.g. a `GameTheme.cs` defaults), and delete any `Resources/*Theme.asset` that would shadow them with stale serialized values (a real bug from a reference project — the asset overrode the updated `.cs` palette).

4. **Menu & text consistency** is owned by `unity-ui-designer` (recurring menu/typography drift was fixed there — display-name single-sourcing, safe-area, TMP font setup, 44pt targets). Cross-reference it from the orchestration checklist below; do not re-derive UI rules here.


## Visual Quality Gate (art is first-class)

Before claiming a generator key is unavailable, run the credential probe and paste its literal output:

```bash
bash ~/.claude/skills/unity-game-director/scripts/probe_asset_credentials.sh
# -> TRIPO_API_KEY=SET|MISSING / GEMINI_API_KEY=SET|MISSING / ELEVENLABS_API_KEY=SET|MISSING
```

"Key unavailable" is not a valid skip reason unless the probe shows `MISSING`. The probe checks **both** `GEMINI_API_KEY` and `TRIPO_API_KEY` — for premium character/prop/animated assets, consider Tripo (including **pre-rendering Tripo models to sprites for 2D games**, see `unity-3d-generator` "Use Tripo for 2D games too"), don't default to Gemini-only 2D generation. **Motion → Tripo, static → Gemini:** produce any animated/moving asset with Tripo (rig + render-to-sprite for 2D); Gemini frame-by-frame drifts and is a fallback only when `TRIPO_API_KEY` is `MISSING`/quota-blocked.

**Real generated art is the DEFAULT for EVERY primary visible surface — not one hero asset.** Each surface the player actually looks at should be a real generated/sourced asset with evidence (a Tripo task ID + imported GLB/FBX path, or a generated sprite/texture path): the background/terrain/ground, the path/track, the player, enemies/obstacles, towers/units, signature props, and the key UI. A single generated hero amid untextured everything-else is NOT a premium scene.

**Procedural / runtime shapes are a FALLBACK, not the default.** They are acceptable only when a key is `MISSING`/quota-blocked (show the literal evidence) or for genuinely low-value repeated props where an atlas / GPU instancing is the right call. A procedural placeholder is never "premium," "polished," or "AAA."

**Animation is part of the bar — assets that ACT must move.** Any asset that acts in the game (characters, enemies, towers, interactables) must be animated with the states its role requires (idle/move/attack/hit/death; towers idle/aim/fire), and any action with a gameplay effect must fire that effect on the correct animation frame (release the arrow on the loose frame, deal damage on the contact frame) — not on raw input. Route animation work to `unity-animation`.

**Amateur-look auto-fail anti-patterns.** If a screenshot shows any of these, the visuals FAIL — do not call them done:
- flat solid-color ground or background,
- procedural primitive blobs (cubes/spheres/capsules) standing in for primary surfaces,
- one generated asset surrounded by untextured everything-else,
- a hard-oval vignette used as the only "lighting,"
- a static asset where motion is expected (e.g. a tower/enemy/character with no idle/attack/death), or a projectile/damage that fires on input instead of on the animation's release/contact frame.

**Route premium visual work to `unity-aaa-graphics`.** For any premium / polished / AAA / "make it look good" / "looks basic" request, or whenever a screenshot trips the anti-patterns above, hand off to `unity-aaa-graphics`. It owns the per-surface asset-sourcing decision, the AAA prompt library + genre art kits, render polish, and the visual scorecard that fails flat/programmer-art scenes.

**Allowed skips** (the only valid reasons to ship a surface without real art): user explicitly asked offline-only, the probe shows the key `MISSING`, a real API/quota error with the command shown, or a repeated low-value prop better done procedurally / by atlas instancing.

## Phase Routing

- `unity-gameplay-systems`: first playable slice, project/scene setup, C# (cache `GetComponent` in `Awake`; Input System not legacy `Input`; pooling; no allocations in `Update`; `[SerializeField] private`; asmdefs), entity/state systems, camera, controls, scoring, difficulty, game feel. 2D and 3D casual templates.
- External asset sourcing: credential probe, generator skill loading, source decision, task IDs / output files or blocker evidence. Must complete before graphics is "done" for premium visual claims.
- `unity-3d-generator`: Tripo text/image→3D, texture, auto-rig, animation, conversion, GLB/FBX → write into `Assets/`, import, configure import settings.
- `unity-image-generator`: STATIC 2D art only — sprites, UI art, backgrounds, icons, textures, concepts, and high-quality reference images that condition Tripo (image-to-3D inputs). Anything ANIMATED / with motion routes to `unity-3d-generator` (Tripo rig + animate, pre-rendered to sprites for 2D) plus `unity-animation`, not frame-by-frame Gemini.
- `unity-audio-generator`: SFX, loops/music, UI sounds, voice/TTS → import as AudioClips.
- `unity-graphics`: basic-looking scenes → URP setup, lighting, materials, mobile-safe post, visual quality.
- `unity-aaa-graphics`: premium/AAA visual upgrades — art-direction critique, mandatory per-surface asset sourcing, AAA prompt library + genre art kits, render polish, and a visual scorecard gate that fails flat/programmer-art scenes. Route here for any "make it look good / premium / looks basic" request.
- `unity-art-direction`: the structured art-direction system — establish/approve a locked `art-spec.yaml` (style preset, palette, materials, lighting, scale, mobile budgets, acceptance), then run the golden-asset/family production pipeline with quality-gate scoring. Use at concept time to lock the visual language before mass-generating art.
- `unity-animation`: AAA gameplay-synced animation (2D sprite or 3D skeletal) — per-role clip catalog (idle/move/attack/hit/death, tower idle/aim/fire), Animator wiring, and Animation Events that fire gameplay on the correct frame. Every asset that acts must be animated.
- `unity-analytics-liveops`: analytics & retention instrumentation (D1/D7/D30, ARPDAU funnels), remote config + A/B testing, crash/analytics SDKs, soft-launch measurement, iOS ATT/SKAdNetwork/AdAttributionKit and privacy-manifest coordination — the levers that turn a playable game into a retentive, monetizable one.
- `unity-ui-designer`: HUD, menus, overlays, pause/win/lose, settings, responsive + safe-area touch UI. **Owns menu & text consistency** (label single-sourcing, TMP font setup, typography scale, no-tofu) — route all recurring menu/text-drift issues here rather than fixing them ad hoc.
- `unity-debug-profiler`: blank scene / null refs / compile errors, domain-reload recovery, profiler, draw calls, memory, mobile thermal/perf.
- `unity-qa-release`: Play Mode + EditMode tests, device-resolution checks, iOS build pipeline, App Store / privacy-manifest readiness, release risks.
- `unity-game-economy`: design the economy & meta-progression (currencies, sources/sinks, progression pacing, reward schedules, IAP catalog) that make the game retain and monetize — distinct from monetization (SDK wiring) and analytics (measurement).
- `unity-localization`: globally-localizable text/assets via the Unity Localization package (String/Asset Tables, Smart Strings, per-script fonts/RTL, pseudoloc, localized store metadata). Externalize strings early.
- `unity-aso-growth`: App Store Optimization + growth (listing, icon/screenshots/preview, Product Page A/B, soft-launch UA, SKAdNetwork measurement, ratings prompts). Retention before acquisition.
- `unity-project-setup`: project foundation — source control (.gitignore/LFS/meta files), folder + asmdef architecture, package management, versioning, secrets-per-env, CI/CD basics.

If a sibling file cannot be loaded, record the path/reason and use this director's routing as the fallback for that phase.

## Verification (a phase is done only with evidence)

- Project compiles clean: `read_console(types=["error"])` empty after the last script change.
- Play Mode runs: `manage_editor(action="play")` → `read_console` clean → `manage_scene(action="screenshot")` shows a real scene that PASSES the `unity-aaa-graphics` visual scorecard (textured primary surfaces, asset cohesion, real lighting/depth) — not merely "non-primitive" → `stop`. Confirm key acting assets are animated (idle/move/attack as the role requires), not static/T-pose, with gameplay effects firing on the correct animation frame.
- Core loop reachable: input → objective → win/lose or restart path exercised (ideally a PlayMode test via `run_tests` + `get_test_job`).
- Tests green before "done": EditMode/PlayMode via the `testing` group.
- iOS readiness for release claims: IL2CPP backend, ASTC textures, deployment target >= iOS 13, bundle id/product/version set, Xcode project builds. Signing/`.ipa` is a manual macOS+Xcode step — flag it, do not claim it done.
- Screenshots dominated by primitives, flat planes, or empty scenes = not done.

## Ledger (keep it lightweight)

Track only what proves the outcome:

```text
- Unity: detected yes/no, version, render pipeline, key packages, iOS target
- MCP: connected yes/no, tool groups enabled
- Pipeline: 2D / 3D / mixed
- Novel-mechanic scope (if any): spec+worked-example agreed / make-or-break property + measured value / decomposed+unit-tested / forks surfaced
- Aesthetic north-star: reference style / palette / type / mood + anti-target / latest rubric score
- Sibling skills loaded: gameplay / graphics / ui / debug / qa (+ 3d/image/audio if used)
- Credential probe: TRIPO / GEMINI / ELEVENLABS = SET|MISSING
- Asset sourcing: hero source + evidence (task id / file) or skip reason
- Phases: gameplay / assets / graphics / ui / debug / qa = pending|done|skipped + evidence
- Verification: compile clean / play-mode screenshot / core loop / tests / iOS readiness
- Remaining risks / manual steps (signing, store assets)
```

## Final Response

Report the ledger, files changed, scenes/prefabs touched (and that they went through MCP), how to run it in-Editor, controls, verification evidence (console clean, screenshots, test results), generated-asset evidence or blockers, iOS/App Store readiness with the manual signing step called out, and remaining risks. Be precise: "loaded" = the SKILL.md/reference was read; "executed" = the work ran in the Editor with evidence. Do not claim premium quality without a screenshot of a real, non-primitive scene.

## Field notes & lessons

- Added two front-loaded gates that real project failures exposed.
  - **Step 2.5 — Scope a novel/ambiguous mechanic before building.** The Cube level was built before its rules were nailed down; the first designs had ~14,000 solutions, discovered only by *measuring after building*, forcing multiple rule + rendering redesigns. New procedure: crisp spec + worked example agreed first; name and **measure** the make-or-break property (here puzzle uniqueness, via a throwaway capped solution-counter — mirrors the eventual `CubeSolver.CountSolutions`/`FindAlternate`) on a disposable pure-logic prototype before any art/UX; decompose into unit-tested Core pieces; surface ambiguous rule forks to the user instead of guessing. Grounded in prototype-the-riskiest-thing-first / vertical-slice practice (Rami Ismail, Tono), design-pillar filtering (gamedesignskills), and Sudoku-style uniqueness counting (101computing, thonky).
  - **Step 2.6 — Aesthetic direction as a first-class early deliverable.** The reference project's look churned through many passes (several distinct directions; glossy ↔ flat) for want of an agreed visual target. New procedure: pin a named north-star (reference style + touchstones, 4–7 color palette with contrast intent, one type family, mood + explicit anti-target, flat/glossy finish decided once) at concept time; converge in 1–2 passes via a fast MCP-screenshot review against a fixed 1–10 rubric (palette/contrast, typography, hierarchy/spacing, finish consistency, north-star cohesion); keep the theme single-sourced in code. Grounded in mood-board alignment (Milanote, Numberanalytics) and convergent design-critique/review-rubric practice (markup.io, IxDF).
  - Added a one-line cross-reference making `unity-ui-designer` the owner of menu/text consistency (failure C — fixed in depth in that sibling skill, not duplicated here), plus matching ledger lines.
