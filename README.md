# Unity Game Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-22-blue.svg)](#skill-catalog)
[![Claude Code](https://img.shields.io/badge/for-Claude%20Code-8A2BE2.svg)](https://docs.claude.com/en/docs/claude-code)

A collection of **[Claude Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)** for building **casual iOS games in Unity 6** with Claude (Claude Code, the desktop app, or the Agent SDK). The skills drive a live Unity Editor through [MCP for Unity](https://github.com/CoplayDev/unity-mcp), generate 2D/3D/audio assets from text prompts, and carry battle-tested checklists for graphics, UI, gameplay, monetization, QA, and App Store release.

Think of it as a **studio-in-a-box**: one entrypoint skill (`unity-game-director`) that orchestrates a dozen specialists so you can go from *"build me a one-tap arcade game"* to a real, playable, screenshot-verified slice — without hand-picking which skill to use.

> **Scope.** These skills target **casual / hyper-casual iOS games on Unity 6 (6000.x)**. Most of the workflow knowledge generalizes to other Unity targets, but iOS build/release/monetization specifics are iOS-first.

---

## Table of contents

- [What is an Agent Skill?](#what-is-an-agent-skill)
- [Skill catalog](#skill-catalog)
- [How the skills fit together](#how-the-skills-fit-together)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment variables](#environment-variables)
- [MCP for Unity setup](#mcp-for-unity-setup)
- [Quick start](#quick-start)
- [Prompting guide](#prompting-guide)
- [Repository layout](#repository-layout)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Security](#security)
- [License & disclaimer](#license--disclaimer)

---

## What is an Agent Skill?

An [Agent Skill](https://docs.claude.com/en/docs/claude-code/skills) is a folder containing a `SKILL.md` file (plus optional `references/` and `scripts/`). The `SKILL.md` has YAML frontmatter with a `name` and a `description`; Claude reads the description to decide **when** to pull the skill into context, then follows its instructions. Skills are model-invoked — you don't call them like functions, you just describe what you want and Claude loads the relevant skill(s) automatically.

```
unity-graphics/
├── SKILL.md                 # frontmatter (name + description) + the playbook
├── references/              # deeper docs loaded on demand
│   ├── urp-mobile-recipes.md
│   └── checklists/...
└── scripts/                 # optional helper scripts the skill can run
```

These skills are plain Markdown + a little Python/Bash — no build step, no dependencies to compile. Install them and Claude does the rest.

---

## Skill catalog

### Orchestration

| Skill | What it does |
|-------|--------------|
| **unity-game-director** | Primary entrypoint. Detects your Unity version, routes work through gameplay → graphics → UI → audio → assets → debug → QA, and verifies a real playable slice (Play Mode tests + screenshots) instead of stopping at design docs. Start here. |

### Execution layer (Unity Editor control)

| Skill | What it does |
|-------|--------------|
| **unity-mcp-bridge** | The execution layer beneath everything else. Wraps [MCP for Unity](https://github.com/CoplayDev/unity-mcp) to create scenes, GameObjects, components, prefabs, materials and scripts; run Play Mode / tests; read the console; drive headless iOS builds. Covers setup and the domain-reload reconnect dance. |
| **unity-mcp-skill** | Tool/resource reference and workflow patterns for the MCP for Unity server. Complements `unity-mcp-bridge` with schemas and best practices. |

### Foundations

| Skill | What it does |
|-------|--------------|
| **unity-project-setup** | Project foundation for a team — Unity `.gitignore` + Git LFS + meta-file/serialization discipline, `Assets/<Game>/` structure, asmdef architecture (engine-free Core/Game/Editor/Tests), package management, versioning, secrets-per-environment, and CI/CD basics. |

### Design & systems

| Skill | What it does |
|-------|--------------|
| **unity-game-economy** | Designs the economy & meta-progression that make a casual game retain and monetize — soft/hard currencies, balanced sources & sinks, progression pacing, reward schedules, session design, and IAP-catalog/pricing design. Complements `unity-monetization` (wiring) and `unity-analytics-liveops` (measuring). |

### Build the game

| Skill | What it does |
|-------|--------------|
| **unity-gameplay-systems** | First-playable-slice scaffolding, C# architecture, Input System touch controls, scene/prefab assembly, scoring/spawning/pooling, difficulty curves, and game-feel juice (squash-stretch, screen shake, hit-stop, haptics). |
| **unity-graphics** | Takes a flat/primitive scene to a premium look: URP setup, mobile lighting (baked + probes), materials/shaders, post-processing, and draw-call/overdraw budgets. |
| **unity-aaa-graphics** | Visual-quality enforcement layer. Turns flat/"programmer-art" scenes into premium, store-quality visuals: art-direction critique, a mandatory per-surface asset-sourcing decision (generate real art for terrain, paths, units, props — not flat fills), an AAA prompt library with genre art kits, render polish, and a visual scorecard that fails amateur output. |
| **unity-art-direction** | The art-direction *system*: a locked machine-readable `art-spec.yaml` single-source-of-truth, a 12-preset style library (concrete starting points), mobile art budgets (tri/texture/material caps), and a disciplined golden-asset → family production pipeline (concept → turnaround → 3D → cleanup → prefab → validation-scene → quality-gate scoring) so you ship an art-directed *game*, not a folder of pretty assets. |
| **unity-asset-pipeline** | The production gate between generated source art and game-ready runtime prefabs: per-asset `asset-contract.yaml`, sprite/mesh/import QA, contract-driven Unity import, prefab factory, BeautyCell visual-regression screenshot, and an approved-asset registry that scene builders must use instead of raw generated files. |
| **unity-scene-composition** | Screen-space visual hierarchy beyond grid/layout correctness: camera profile, layers, focal path, big/medium/small shape rhythm, prop density, color zoning, occlusion budget, shadow/contact rules, and screenshot acceptance for BeautyCell/golden screens. |
| **unity-game-layout** | Board/grid/world-coordinate discipline for mechanically correct levels: coordinate systems, tile/cell sizing, path/board geometry, placement constraints, and validation of gameplay layout before visual composition. |
| **unity-animation** | Makes assets *move* — AAA, gameplay-synced animation via 2D sprite sheets or 3D skeletal (Tripo) rigs. Per-role clip catalog (idle/move/attack/hit/death; tower idle/aim/fire), Unity Animator/state-machine/blend-tree wiring, and Animation Events that fire gameplay on the right frame (release the arrow on the loose frame). A static asset where motion is expected fails the bar. |
| **unity-ui-designer** | Screenshot-proven mobile UI: HUDs, menus, pause/win/lose/settings screens, safe-area/notch handling, 44pt touch targets, TextMeshPro, uGUI and UI Toolkit. |

### Assets (generative)

| Skill | What it does | API |
|-------|--------------|-----|
| **unity-image-generator** | 2D sprites, sprite sheets, backgrounds, UI art, icons, particle/texture references → imported as Unity sprites/textures. | Google Gemini |
| **unity-3d-generator** | Text-to-3D and image-to-3D game-ready GLB/FBX (characters, props, vehicles, obstacles), auto-rig + animation, low-poly/mobile optimization → imported via ModelImporter. | Tripo |
| **unity-audio-generator** | SFX, looping ambience/music beds, UI sounds, and voice/TTS → imported as AudioClips with mobile-correct compression. | ElevenLabs |
| **unity-asset-designer** | Art-direction layer *above* the generators: style guide / art bible, character turnaround sheets, and icon sets so all generated art stays on-model. No API key of its own. |

### Ship it

| Skill | What it does |
|-------|--------------|
| **unity-debug-profiler** | Evidence-driven debugging (compile errors, NullReference, pink materials, blank scenes) and profiling (frame rate, draw calls, GC, texture memory, IL2CPP stripping). |
| **unity-monetization** | Ads integration: Google AdMob and Unity Ads direct, frequency-capped interstitials, rewarded ads, ATT + SKAdNetwork, and an SDK-agnostic ads facade. |
| **unity-analytics-liveops** | Analytics & liveops: D1/D7/D30 retention and ARPDAU funnels, remote config + A/B testing, crash/analytics SDKs (Unity Gaming Services, GameAnalytics, Firebase), soft-launch measurement, and iOS ATT/SKAdNetwork/AdAttributionKit + privacy-manifest coordination — the levers that turn a playable game into a retentive, monetizable one. |
| **unity-qa-release** | Play Mode / EditMode tests, device-resolution & safe-area checks, iOS build (IL2CPP/ASTC/Xcode), privacy manifest, TestFlight, fastlane signing, and release-risk reports. |
| **unity-ios-secure-backend** | Anti-cheat leaderboards: Apple Game Center identity verification + App Attest, verified server-side by a Node/NestJS backend. |

### Global & growth

| Skill | What it does |
|-------|--------------|
| **unity-localization** | Ship a globally-localizable game with the Unity Localization package — String/Asset Tables, locale selection, Smart Strings (plurals/variables), per-script fonts + RTL, pseudolocalization, text-expansion layout, and localized App Store metadata. |
| **unity-aso-growth** | App Store Optimization & growth — icon/title/keywords/screenshots/preview-video, Apple Product Page A/B testing, creatives & soft-launch UA, SKAdNetwork/AdAttributionKit measurement, and ratings prompts. Retention before acquisition. |

---

## How the skills fit together

```
                          ┌─────────────────────┐
   "build me a game"  ──▶ │  unity-game-director │  (orchestrator)
                          └──────────┬──────────┘
            ┌──────────────┬─────────┼─────────┬──────────────┐
            ▼              ▼         ▼          ▼              ▼
      gameplay-      graphics /   asset-     monetization   qa-release /
      systems          ui       designer                   debug-profiler
            │              │         │                          │
            │              │   ┌─────┴─────┐                    │
            ▼              ▼   ▼     ▼      ▼                    ▼
         ┌──────────────────────────────────────────┐    iOS build / tests
         │            unity-mcp-bridge               │◀──────────┘
         │   (drives the live Unity 6 Editor)        │
         └──────────────────────────────────────────┘
              ▲                              ▲
        image / 3d / audio            MCP for Unity
        generators (APIs)             (Editor package)
```

You normally only need to talk to **`unity-game-director`** — it loads the rest as needed. Every concrete change goes through **`unity-mcp-bridge`**, which talks to a live, open Unity Editor (not files on disk).

---

## Prerequisites

| Requirement | Why | Notes |
|-------------|-----|-------|
| **Claude Code** (or Claude desktop / Agent SDK) | Runs the skills | [Install Claude Code](https://docs.claude.com/en/docs/claude-code) |
| **Unity 6 (6000.x)** Editor | The game engine these skills target | 6000.5 LTS or newer recommended |
| **[MCP for Unity](https://github.com/CoplayDev/unity-mcp)** (`com.coplaydev.unity-mcp`) | Lets Claude drive the Editor | Installed as a Unity package — see [MCP setup](#mcp-for-unity-setup) |
| **Python 3.10+** and **[uv](https://github.com/astral-sh/uv)** | MCP for Unity server + asset scripts | `uv` is required by the MCP server |
| **Xcode** (macOS) | iOS builds / TestFlight | Only needed when you build for device |
| **API keys** (optional) | Generative asset skills | Only for the generator you use — see [env vars](#environment-variables) |

> The core gameplay/graphics/UI/QA skills work **without any API keys**. Keys are only needed for the generative asset skills (image / 3D / audio).

---

## Installation

These are Claude Agent Skills. Install them where Claude Code looks for skills.

### Option A — install all skills globally (recommended)

Available in every project on your machine:

```bash
git clone https://github.com/tea-x-random/unity-game-skills.git
mkdir -p ~/.claude/skills
cp -R unity-game-skills/skills/unity-* ~/.claude/skills/
```

### Option B — install into a single project

Scoped to one repo (commit them with your game, or add to `.gitignore`):

```bash
git clone https://github.com/tea-x-random/unity-game-skills.git
mkdir -p /path/to/your-game/.claude/skills
cp -R unity-game-skills/skills/unity-* /path/to/your-game/.claude/skills/
```

### Option C — symlink (stay up to date with `git pull`)

```bash
git clone https://github.com/tea-x-random/unity-game-skills.git ~/src/unity-game-skills
for d in ~/src/unity-game-skills/skills/unity-*; do
  ln -s "$d" ~/.claude/skills/"$(basename "$d")"
done
```

### Verify

Start Claude Code and ask: *"What Unity skills do you have?"* — it should list the `unity-*` skills. Or run `/help` and look for the skills section.

You don't need all 25. Copy only the ones you want (e.g. just `unity-game-director`, `unity-mcp-bridge`, `unity-gameplay-systems`, `unity-graphics`, `unity-ui-designer` for an asset-key-free workflow).

---

## Environment variables

Only the **generative asset skills** need keys. Set them in your shell profile so they're available to Claude's tools.

| Variable | Used by | Get a key | Required? |
|----------|---------|-----------|-----------|
| `TRIPO_API_KEY` | `unity-3d-generator` | [platform.tripo3d.ai](https://platform.tripo3d.ai/) | Only for 3D generation |
| `GEMINI_API_KEY` | `unity-image-generator` | [Google AI Studio](https://aistudio.google.com/apikey) | Only for 2D image generation |
| `ELEVENLABS_API_KEY` | `unity-audio-generator` | [elevenlabs.io](https://elevenlabs.io/) | Only for audio/voice generation |

Copy [`.env.example`](.env.example) and fill in what you need, then export the values. The simplest reliable approach is to add them to your shell profile (`~/.zshrc` or `~/.zprofile` on macOS):

```bash
export TRIPO_API_KEY="your-tripo-key"
export GEMINI_API_KEY="your-gemini-key"
export ELEVENLABS_API_KEY="your-elevenlabs-key"
```

Then `source ~/.zshrc` (or open a new terminal) **before** launching Claude Code.

The skills resolve keys in this order: an explicit `--api-key` flag → the environment variable above. `unity-game-director` ships a probe script that reports `SET` / `MISSING` for each key **without ever printing the value**, so Claude can check availability safely.

> **Never commit real keys.** `.env` is git-ignored. These keys bill against *your* third-party accounts — treat them like passwords.

---

## MCP for Unity setup

The skills change your project by driving a **live Unity Editor** through the [MCP for Unity](https://github.com/CoplayDev/unity-mcp) server (CoplayDev). High-level steps (the `unity-mcp-bridge` skill walks Claude through this in detail):

1. **Install the Unity package** — in Unity: *Window → Package Manager → Add package from git URL* → `https://github.com/CoplayDev/unity-mcp.git`, or via OpenUPM: `openupm add com.coplaydev.unity-mcp`.
2. **Register the MCP server with Claude Code:**
   ```bash
   claude mcp add unity --transport http http://127.0.0.1:8080/mcp
   ```
3. **Start the bridge** — in Unity: *Window → MCP for Unity → Start/Connect* until it reads **Connected** (needs `uv` / Python 3.10+ on PATH).
4. **Keep the Editor open and focused.** MCP talks to the running Editor; after every C# compile or package change Unity does a ~5s domain reload that briefly drops the connection — the skills know to wait and reconnect.

---

## Quick start

With skills installed, MCP connected, and your Unity 6 project open:

```
You: Build me a one-tap endless runner prototype — cute low-poly fox dodging
     obstacles, score counter, game-over screen. Make it a real playable slice.
```

Claude (via `unity-game-director`) will roughly:

1. Detect the Unity version and project capabilities.
2. Pin a tiny scope + aesthetic north-star, asking one batched round of questions if needed.
3. Scaffold gameplay (`unity-gameplay-systems`) through MCP — input, spawning, scoring, game loop.
4. Lock screen composition (`unity-scene-composition`) — camera, layers, focal path, density, color zones, and BeautyCell target.
5. Generate source art if you have keys (`unity-3d-generator` for the fox/obstacles, `unity-image-generator` for UI/reference), or use procedural placeholders if not.
6. Promote generated files through `unity-asset-pipeline` — asset contracts, sprite/mesh/import QA, prefab factory, BeautyCell screenshot, and approved-asset registry.
7. Build the HUD and game-over screen (`unity-ui-designer`).
8. Polish visuals (`unity-graphics`).
9. Run Play Mode and capture screenshots (`unity-qa-release` / `unity-debug-profiler`) as evidence it actually runs.

You stay in control — review each phase, redirect, or ask for changes.

See the **[Prompting guide](docs/PROMPTING.md)** for how to get the best results.

### Designing for quality, retention & monetization

- **Ask for real generated art on every surface**, not flat placeholders — terrain, paths, units, and props should be sourced art, not solid fills. The `unity-aaa-graphics` skill enforces this with a per-surface asset-sourcing decision and a visual scorecard.
- **Pin an art-direction north-star early** — palette, style, and finish (flat vs glossy) — so every asset and screen stays on-model instead of drifting.
- **Motion → Tripo, static → Gemini.** Produce anything that animates (characters, enemies, towers) with Tripo3D (rig + animate; pre-rendered to sprite frames for 2D) — Gemini is for static art, textures, UI, and reference images. Frame-by-frame image generation drifts.
- **Treat generated art as source, not final assets.** Promote source files through `unity-asset-pipeline`: preserve/validate alpha, enforce import settings, generate prefabs, record BeautyCell screenshots, and enter only approved prefabs into the registry.
- **Compose before scaling.** Use `unity-scene-composition` to build one BeautyCell/golden screen before generating dozens of assets; fix camera, scale, focal path, density, and color zoning there first.
- **Design for hybrid monetization (ads + IAP).** Only ~1.8% of players ever buy an IAP, so rewarded/interstitial ads carry most casual revenue — plan both, not one.
- **Instrument retention (D1/D7/D30) and tune via remote config / A/B testing** rather than guessing. The `unity-analytics-liveops` skill covers the funnels, SDKs, and experiments.

---

## Prompting guide

A short version (full guide in **[docs/PROMPTING.md](docs/PROMPTING.md)**):

- **State the genre and one core mechanic.** *"hyper-casual stacker"*, *"match-3 with a swap-and-cascade board"*, *"one-tap flappy-style runner."* Specific beats vague.
- **Name your constraints up front.** Target device, portrait vs landscape, art style, "no API keys / use procedural art," and whether you want a prototype or a release-ready slice.
- **Ask for a real, verified slice.** Add *"make it actually playable and show me screenshots / Play Mode results"* to push past design-doc answers.
- **Let the director pick skills.** You rarely need to name a skill; describe the outcome. If you *do* want a specific one, say e.g. *"use the monetization skill to add a rewarded ad."*
- **Provide an aesthetic north-star early** — a reference style, a 4–7 color palette, one font, flat-vs-glossy. This is the single biggest lever on visual quality and avoids endless re-guessing.
- **Batch your decisions.** Answer concept/art/scope questions in one go so Claude doesn't stall.

---

## Repository layout

```
.
├── README.md
├── LICENSE                  # MIT
├── CONTRIBUTING.md
├── SECURITY.md
├── .env.example
├── .gitignore
├── docs/
│   └── PROMPTING.md
└── skills/
    ├── unity-game-director/
    ├── unity-mcp-bridge/
    ├── unity-mcp-skill/
    ├── unity-gameplay-systems/
    ├── unity-graphics/
    ├── unity-aaa-graphics/
    ├── unity-art-direction/
    ├── unity-asset-pipeline/
    ├── unity-scene-composition/
    ├── unity-game-layout/
    ├── unity-animation/
    ├── unity-ui-designer/
    ├── unity-image-generator/
    ├── unity-3d-generator/
    ├── unity-audio-generator/
    ├── unity-asset-designer/
    ├── unity-debug-profiler/
    ├── unity-monetization/
    ├── unity-analytics-liveops/
    ├── unity-qa-release/
    ├── unity-ios-secure-backend/
    ├── unity-project-setup/
    ├── unity-game-economy/
    ├── unity-localization/
    └── unity-aso-growth/
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Claude doesn't use the skills | Not installed where Claude looks | Confirm files are in `~/.claude/skills/unity-*` or `<project>/.claude/skills/unity-*` |
| "no Unity session" / MCP not responding | Editor closed, unfocused, or mid domain-reload | Focus the Unity Editor; wait ~5s after a compile; re-check *Window → MCP for Unity* reads Connected |
| `*_API_KEY=MISSING` | Key not exported in the shell that launched Claude | Add to `~/.zshrc`/`~/.zprofile`, `source` it, relaunch Claude |
| Image script fails to import `google-genai` | macOS system Python is externally managed (PEP 668) | The skill creates a venv: `python3 -m venv .artvenv && .artvenv/bin/pip install google-genai pillow` |
| Pink/magenta materials in scene | Wrong render pipeline / missing shader | Ask `unity-debug-profiler`; usually a Built-in↔URP material mismatch |
| New AdMob/Unity Ads serves no real ads | Brand-new ad unit is pending approval (no-fill) | Expected — only the SDK's **test** unit IDs serve until approved |

---

## Contributing

Contributions are welcome — see **[CONTRIBUTING.md](CONTRIBUTING.md)**. In short: keep skills evidence-driven and concise, never commit secrets or project-specific identifiers, and test changes against a real Unity 6 project before opening a PR.

---

## Security

- These skills run scripts and drive your Unity Editor locally. Review what they do before granting broad permissions.
- API keys bill against your third-party accounts. Keep them in your environment, never in the repo.
- Found a sensitive value in a skill or a security issue? See **[SECURITY.md](SECURITY.md)**.

---

## License & disclaimer

Licensed under the **[MIT License](LICENSE)**.

This is an independent, community project. It is **not affiliated with or endorsed by** Unity Technologies, Apple, Google, Tripo, ElevenLabs, CoplayDev, or Anthropic. "Unity," "iOS," "App Store," "Game Center," "AdMob," "Gemini," and other names are trademarks of their respective owners. The generative skills call third-party APIs that have their own terms, pricing, and content policies — you are responsible for your usage and any costs incurred.
