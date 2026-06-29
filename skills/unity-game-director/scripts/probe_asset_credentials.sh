#!/usr/bin/env bash
set -euo pipefail

if command -v zsh >/dev/null 2>&1; then
  zsh -lc '
    source "$HOME/.zprofile" >/dev/null 2>&1 || true
    source "$HOME/.zshrc" >/dev/null 2>&1 || true
    for name in TRIPO_API_KEY GEMINI_API_KEY PIXEL_LABS_API_KEY ELEVENLABS_API_KEY; do
      value="${(P)name:-}"
      if [ -n "$value" ]; then printf "%s=SET\n" "$name"; else printf "%s=MISSING\n" "$name"; fi
    done
  '
else
  bash -lc '
    source "$HOME/.bash_profile" >/dev/null 2>&1 || true
    source "$HOME/.bashrc" >/dev/null 2>&1 || true
    for name in TRIPO_API_KEY GEMINI_API_KEY PIXEL_LABS_API_KEY ELEVENLABS_API_KEY; do
      value=${!name:-}
      if [ -n "$value" ]; then printf "%s=SET\n" "$name"; else printf "%s=MISSING\n" "$name"; fi
    done
  '
fi
