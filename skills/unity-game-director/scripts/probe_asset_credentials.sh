#!/usr/bin/env bash
set -euo pipefail

if command -v zsh >/dev/null 2>&1; then
  zsh -lc '
    source "$HOME/.zprofile" >/dev/null 2>&1 || true
    source "$HOME/.zshrc" >/dev/null 2>&1 || true
    printf "TRIPO_API_KEY=%s\n" "${TRIPO_API_KEY:+SET}"
    printf "GEMINI_API_KEY=%s\n" "${GEMINI_API_KEY:+SET}"
    printf "ELEVENLABS_API_KEY=%s\n" "${ELEVENLABS_API_KEY:+SET}"
  '
else
  bash -lc '
    source "$HOME/.bash_profile" >/dev/null 2>&1 || true
    source "$HOME/.bashrc" >/dev/null 2>&1 || true
    printf "TRIPO_API_KEY=%s\n" "${TRIPO_API_KEY:+SET}"
    printf "GEMINI_API_KEY=%s\n" "${GEMINI_API_KEY:+SET}"
    printf "ELEVENLABS_API_KEY=%s\n" "${ELEVENLABS_API_KEY:+SET}"
  '
fi
