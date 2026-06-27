# Security Policy

## Reporting a vulnerability or sensitive disclosure

If you find a security issue — or notice a secret, API key, private project
identifier, or other sensitive value that slipped into a skill — please **do not
open a public issue**. Instead:

1. Open a [GitHub Security Advisory](https://github.com/tea-x-random/unity-game-skills/security/advisories/new), or
2. Contact the maintainer privately via the email on the GitHub profile.

We'll acknowledge, confirm, and remediate (including a history rewrite if a
secret was committed) as quickly as we can.

## Handling secrets

- These skills **never** hardcode credentials. All API keys are read from
  environment variables (`TRIPO_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`).
- The credential-probe script reports only `SET` / `MISSING` and never prints a
  key's value.
- Keys bill against *your* third-party accounts. Keep them in your shell
  environment, never in the repository. `.env` is git-ignored.

## What runs on your machine

The skills execute helper scripts (Python/Bash) and drive your local Unity
Editor through MCP for Unity. Review skill instructions and grant tool
permissions deliberately, especially in untrusted projects.
