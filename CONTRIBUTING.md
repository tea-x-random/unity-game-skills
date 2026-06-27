# Contributing to Unity Game Skills

Thanks for your interest! These skills get better with real-world battle scars —
bug fixes, new recipes, and hard-won checklist items are all welcome.

## Ground rules

1. **Never commit secrets or private identifiers.** No API keys, no real
   bundle/app/game IDs, no private repo commit hashes, no personal paths
   (`/Users/<you>/...`), no internal project names. Use placeholders like
   `<YOUR_IOS_GAME_ID>`, `Assets/<YourGame>/...`, or `the example game`. See the
   [sanitization checklist](#sanitization-checklist) below.
2. **Stay evidence-driven.** Skills should describe what *actually works* against
   a real Unity 6 project, verified in the Editor — not aspirational steps.
   Prefer "verified against X" over "should work."
3. **Keep it concise.** `SKILL.md` is loaded into the model's context. Put deep
   detail in `references/` and link to it; keep the main file tight and skimmable.
4. **Match the house style.** Mirror the tone, structure, and density of the
   surrounding skills. Lessons learned go under `## Field notes & lessons`.

## How a skill is structured

```
skills/<skill-name>/
├── SKILL.md          # required: YAML frontmatter (name + description) + the playbook
├── references/       # optional: deep docs loaded on demand
└── scripts/          # optional: helper scripts the skill can run
```

The frontmatter `description` is how Claude decides when to load the skill — make
it specific and trigger-rich (mention the symptoms, APIs, and tasks it covers).

## Workflow

1. Fork and branch (`fix/...` or `feat/...`).
2. Make your change. If you add a script, keep dependencies minimal (the existing
   scripts use the Python standard library where possible).
3. **Test against a real Unity 6 project** with MCP for Unity connected. Note what
   you verified in the PR description.
4. Run the sanitization checklist.
5. Open a PR describing the change, what you tested, and the Unity version used.

## Sanitization checklist

Before opening a PR, run these from the repo root and confirm they're clean:

```bash
# No secrets
grep -rniE 'sk-[a-z0-9]{20}|ghp_[a-z0-9]{30}|AKIA[0-9A-Z]{16}|-----BEGIN' skills/

# No personal paths or emails
grep -rniE '/Users/(?!<|dev|you)|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}' skills/

# No private commit hashes referenced as "commit <hash>"
grep -rniE 'commit [`'"'"']?[0-9a-f]{6,10}' skills/

# Real ad/game IDs (Google's test ID 3940256099942544 is fine)
grep -rnoiE 'ca-app-pub-[0-9]+~[0-9]+|\b[0-9]{8,10}\b' skills/ | grep -v 3940256099942544
```

(Standalone 8–10 digit numbers that are clearly public API model-version dates,
e.g. Tripo's `v3.1-20260211`, are fine — use judgment.)

## Reporting issues

Bugs, unclear steps, or skills that no longer match current Unity/SDK behavior:
open an issue with the Unity version, the skill, and what you observed vs expected.

By contributing, you agree your contributions are licensed under the
[MIT License](LICENSE).
