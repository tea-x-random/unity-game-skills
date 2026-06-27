#!/usr/bin/env bash
# Deterministic Unity-project detection + capability probe.
# Prints SET/MISSING-style markers only; never edits anything.
set -uo pipefail

ROOT="${1:-$PWD}"

say() { printf '%s\n' "$1"; }

# --- Is this a Unity project? ---
if [[ -d "$ROOT/Assets" && -d "$ROOT/ProjectSettings" && -f "$ROOT/Packages/manifest.json" ]]; then
  say "UNITY_PROJECT=YES"
else
  # Search one level down in case we're a repo root with the project nested.
  found=""
  while IFS= read -r d; do
    base="$(dirname "$d")"
    if [[ -d "$base/Assets" && -f "$base/Packages/manifest.json" ]]; then found="$base"; break; fi
  done < <(find "$ROOT" -maxdepth 3 -type d -name ProjectSettings 2>/dev/null)
  if [[ -n "$found" ]]; then
    say "UNITY_PROJECT=YES"
    say "UNITY_PROJECT_ROOT=$found"
    ROOT="$found"
  else
    say "UNITY_PROJECT=NO"
    exit 0
  fi
fi

# --- Editor version ---
PV="$ROOT/ProjectSettings/ProjectVersion.txt"
if [[ -f "$PV" ]]; then
  ver="$(grep -E '^m_EditorVersion:' "$PV" | head -1 | awk '{print $2}')"
  say "UNITY_VERSION=${ver:-UNKNOWN}"
  case "$ver" in
    6000.*) say "UNITY_MAJOR=6 (knowledge-gap: verify Input System / UI Toolkit / RenderGraph / Build Profiles against the live Editor, not memory)";;
    2022.*|2021.*) say "UNITY_MAJOR=${ver%%.*} (close to model default knowledge)";;
    *) say "UNITY_MAJOR=${ver%%.*}";;
  esac
else
  say "UNITY_VERSION=UNKNOWN"
fi

# --- Packages of interest ---
MAN="$ROOT/Packages/manifest.json"
check_pkg() { # $1=pretty $2=package-id
  if grep -q "\"$2\"" "$MAN" 2>/dev/null; then say "PKG_$1=YES"; else say "PKG_$1=NO"; fi
}
check_pkg INPUT_SYSTEM   "com.unity.inputsystem"
check_pkg ADDRESSABLES   "com.unity.addressables"
check_pkg URP            "com.unity.render-pipelines.universal"
check_pkg HDRP           "com.unity.render-pipelines.high-definition"
check_pkg CINEMACHINE    "com.unity.cinemachine"
check_pkg GLTFAST        "com.unity.cloud.gltfast"
check_pkg TEST_FRAMEWORK "com.unity.test-framework"
check_pkg UNITY_MCP      "com.coplaydev.unity-mcp"
check_pkg PROBUILDER     "com.unity.probuilder"

# --- Render pipeline (best-effort, from GraphicsSettings) ---
GS="$ROOT/ProjectSettings/GraphicsSettings.asset"
if [[ -f "$GS" ]] && grep -qE 'm_CustomRenderPipeline: *\{fileID: *0\}' "$GS"; then
  say "RENDER_PIPELINE=BUILTIN"
elif [[ -f "$GS" ]] && grep -q 'm_CustomRenderPipeline' "$GS"; then
  say "RENDER_PIPELINE=SRP (URP/HDRP asset assigned)"
else
  say "RENDER_PIPELINE=UNKNOWN"
fi

# --- iOS build target presence ---
PS="$ROOT/ProjectSettings/ProjectSettings.asset"
if [[ -f "$PS" ]] && grep -qiE 'iPhone|iOS' "$PS"; then
  say "IOS_SETTINGS_PRESENT=YES"
else
  say "IOS_SETTINGS_PRESENT=NO (configure iOS target before release)"
fi
