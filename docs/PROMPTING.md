# Prompting Guide

How to get the best results from the Unity Game Skills. These skills are
**model-invoked** — you describe outcomes in natural language and Claude pulls in
the right skill(s). You rarely need to name a skill. The quality of what you get
back tracks closely with the quality of your prompt.

---

## The 60-second version

1. **Genre + one core mechanic.** "Hyper-casual stacker," "one-tap flappy runner,"
   "match-3 with cascades."
2. **Constraints up front.** Device, orientation, art style, keys-or-no-keys,
   prototype-vs-release.
3. **Demand a verified slice.** "Make it actually playable and show me screenshots."
4. **Give an aesthetic north-star.** Reference style + palette + one font + flat/glossy.
5. **Batch your decisions** so Claude doesn't stall on questions.

---

## 1. Describe the outcome, not the skill

Good:

> Build a one-tap endless runner: a low-poly fox auto-runs and the player taps to
> jump over obstacles. Add a score counter and a game-over screen. Portrait, iOS.

Claude routes this through `unity-game-director`, which loads gameplay, UI,
graphics, and QA skills as needed.

If you *want* a specific skill, just say so:

> Use the monetization skill to add a rewarded "continue" ad after game over.

> Use the QA/release skill to do a full iOS build readiness check.

---

## 2. Pin scope tightly

Casual games live or die on a tight first slice. Help Claude scope:

- **One mechanic, fully working** beats five half-built ones.
- Say "**prototype**" for a rough playable, or "**release-ready slice**" for tests +
  polish + iOS readiness.
- Call out what to *skip*: "no meta-progression yet," "placeholder art is fine."

---

## 3. Set an aesthetic north-star early

This is the single biggest lever on visual quality. Without a target, every pass
re-guesses "what looks good" and you get churn. Provide:

- **Reference style / touchstones** — "clean flat vector," "soft 3D claymation,"
  "Japanese minimalist / zen."
- **Palette** — 4–7 colors with roles (background, panels, text/ink, 1–3 accents).
- **One font family** + the mood it carries.
- **Finish** — flat *or* glossy, decided once (mixing them is the #1 cheap-looking tell).

Example:

> Aesthetic: warm flat vector, rounded shapes. Palette: cream background, soft
> terracotta panels, dark-brown ink text, one teal accent. Font: a rounded sans,
> "friendly and calm." Flat finish, no gloss.

---

## 4. Be explicit about assets and API keys

- **No keys?** Say "use procedural / placeholder art" — the graphics and UI skills
  can build a surprisingly polished look with no external assets.
- **Have keys?** Name what to generate: "generate the fox and 3 obstacle props as
  low-poly 3D," "generate the title screen background and button icons as 2D."
- For a **consistent look** across many assets, ask for the asset-designer's
  art-bible / turnaround-sheet pass *before* mass-generating.

---

## 5. Push for evidence

By default, ask Claude to prove it works rather than describe it:

> Run it in Play Mode and show me a screenshot of the actual game.

> Run the Play Mode tests and paste the results.

This routes through `unity-debug-profiler` / `unity-qa-release` and avoids
"design-doc" answers that were never run in the Editor.

---

## 6. Batch decisions and answer forks

When Claude surfaces a genuine branching question (board size, rule variant, art
direction), answer all of them in one message. One well-batched round of answers
is far cheaper than building the wrong thing and tearing it out.

---

## 7. Make sure the environment is ready

The skills need a live Unity 6 Editor with MCP for Unity **Connected**, and any
API keys exported in the shell that launched Claude. If something seems stuck:

- Confirm the Unity Editor is open and focused (MCP drops briefly after each
  compile's domain reload — that's normal).
- Ask Claude to "probe the asset credentials" to check which keys are `SET`.

See the main [README](../README.md) for setup and troubleshooting.

---

## Example prompts

**Prototype, no keys:**
> Build a playable hyper-casual "stack the blocks" prototype with procedural art.
> Tap to drop, mis-stacks trim the block, miss entirely = game over. Portrait iOS.
> Show me a Play Mode screenshot.

**Polished slice with assets:**
> Vertical slice of a cozy match-3. Generate 6 candy-style 2D tile sprites and a
> soft gradient background. Warm pastel palette, rounded font, flat finish. Add a
> HUD with score + moves and a win screen. Run it and screenshot it.

**Release prep:**
> Do an iOS release-readiness pass: Play Mode + EditMode tests, safe-area UI check,
> IL2CPP + ASTC build settings, privacy manifest, and a release-risk report.

**Monetization:**
> Add frequency-capped interstitials between levels and a rewarded "double coins"
> ad, using the SDK-agnostic ads facade so I can swap networks later. Use test ad
> units for now.
