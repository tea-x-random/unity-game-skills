#!/usr/bin/env python3
"""Shared art-spec.yaml loader for the unity-image-generator scripts.

Implements the pipeline convention (docs/PIPELINE_CONVENTIONS.md):
  - Resolution order: explicit --art-spec path -> UNITY_ART_SPEC env var ->
    probe the canonical + legacy roots relative to cwd.
  - Missing-spec behavior: production tooling FAILS unless invoked with an
    explicit --no-art-spec override (agent-run CLIs; no interactive prompts).
    Spec-less exploratory/concept work stays legal via --no-art-spec.

Uses PyYAML when available; otherwise a small fallback parser sufficient for
the art-spec template (nested maps, inline lists, block lists of scalars) —
same approach as unity-asset-pipeline/scripts/validate_asset_manifest.py.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Any

try:  # Prefer PyYAML when available; fallback parser below covers the template.
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

ART_SPEC_ENV = "UNITY_ART_SPEC"

# Canonical root first, then reserved legacy roots (probe all three).
# LOCKSTEP: unity-pixel-art/scripts/generate_pixel_art.py duplicates these
# conventions inline (cross-skill imports aren't established). Change BOTH
# together, and docs/PIPELINE_CONVENTIONS.md ("Art-spec resolver lockstep") first.
# DEPLOYMENT: this module is imported as a SIBLING by generate_image.py /
# validate_sprite.py / critique_image.py — always copy the whole scripts/ dir.
DEFAULT_SPEC_GLOBS = [
    "Assets/*/Art/_ArtDirection/art-spec.yaml",
    "Assets/GameArt/_ArtDirection/art-spec.yaml",
    "Assets/Art/_ArtDirection/art-spec.yaml",
]

# craft.finish -> the finish vocabulary used by validate_sprite/critique_image.
FINISH_MAP = {
    "pixel": "flat",
    "vector_flat": "flat",
    "painterly_2d": "rendered",
    "stylized_3d": "any",
    "realistic_3d": "any",
}

HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


# ------------------------- YAML-ish fallback parser -------------------------

def _strip_comment(line: str) -> str:
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _parse_scalar(text: str) -> Any:
    text = text.strip()
    if text in ("", "null", "Null", "NULL", "~"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in re.split(r",(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", inner)]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _fallback_yaml_load(text: str) -> Any:
    raw: list[tuple[int, str]] = []
    for line in text.splitlines():
        if not line.strip() or line.strip() == "---":
            continue
        clean = _strip_comment(line).rstrip()
        if clean.strip():
            raw.append((len(clean) - len(clean.lstrip(" ")), clean.lstrip(" ")))

    def parse_block(index: int, indent: int):
        if index >= len(raw):
            return {}, index
        if raw[index][0] == indent and raw[index][1].startswith("- "):
            result_list: list[Any] = []
            while index < len(raw) and raw[index][0] == indent and raw[index][1].startswith("- "):
                item_text = raw[index][1][2:].strip()
                index += 1
                if not item_text:
                    child, index = parse_block(index, indent + 2)
                    result_list.append(child)
                elif ":" in item_text and not item_text.startswith(('"', "'")):
                    key, val = item_text.split(":", 1)
                    item = {key.strip(): _parse_scalar(val)} if val.strip() else {key.strip(): None}
                    while index < len(raw) and raw[index][0] >= indent + 2:
                        child_indent, child_text = raw[index]
                        if child_indent == indent + 2 and ":" in child_text:
                            ck, cv = child_text.split(":", 1)
                            index += 1
                            if cv.strip():
                                item[ck.strip()] = _parse_scalar(cv)
                            else:
                                child, index = parse_block(index, child_indent + 2)
                                item[ck.strip()] = child
                        else:
                            break
                    result_list.append(item)
                else:
                    result_list.append(_parse_scalar(item_text))
            return result_list, index

        result: dict[str, Any] = {}
        while index < len(raw):
            line_indent, line_text = raw[index]
            if line_indent != indent:
                break
            if ":" not in line_text:
                raise ValueError(f"Cannot parse YAML line: {line_text}")
            key, val = line_text.split(":", 1)
            key, val = key.strip(), val.strip()
            index += 1
            if val:
                result[key] = _parse_scalar(val)
            else:
                child, index = parse_block(index, indent + 2)
                result[key] = child
        return result, index

    parsed, _ = parse_block(0, raw[0][0] if raw else 0)
    return parsed


# ------------------------------- public API --------------------------------

def project_root_for(anchor: str | Path) -> Path:
    """Derive the Unity project root from any path containing an Assets/ segment
    (same logic as unity-asset-pipeline/scripts/validate_asset_manifest.py)."""
    p = Path(anchor).resolve()
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "Assets" and i > 0:
            return Path(*parts[:i])
    return Path.cwd()


def resolve_project_path(ref: str, anchor: str | Path | None) -> Path:
    """Resolve an Assets/-relative reference (a spec-internal path) against the
    project root derived from `anchor` (the RESOLVED spec path), then cwd, then
    the anchor's parent — never cwd alone, so conditioning artifacts resolve
    from any working directory."""
    rp = Path(ref)
    if rp.is_absolute():
        return rp
    bases: list[Path] = []
    if anchor is not None:
        bases.append(project_root_for(anchor))
    bases.append(Path.cwd())
    if anchor is not None:
        bases.append(Path(anchor).parent)
    for base in bases:
        cand = base / rp
        if cand.exists():
            return cand
    return bases[0] / rp


def resolve_art_spec_path(cli_path: str | None) -> str | None:
    """Resolve the governing art-spec path: CLI flag -> env var -> probe roots."""
    if cli_path:
        return cli_path
    env = os.environ.get(ART_SPEC_ENV)
    if env:
        return env
    for pattern in DEFAULT_SPEC_GLOBS:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    return None


def load_art_spec(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) if yaml is not None else _fallback_yaml_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"art-spec at {path} did not parse to a mapping")
    return data


def resolve_or_fail(cli_path: str | None, no_art_spec: bool):
    """Return (spec_dict, path) per the production fail-unless-overridden rule.

    Returns (None, None) when --no-art-spec was passed. Raises SystemExit with a
    clear message when no spec can be resolved and no override was given.
    """
    if no_art_spec:
        return None, None
    path = resolve_art_spec_path(cli_path)
    if not path or not Path(path).is_file():
        raise SystemExit(
            "Error: no art-spec.yaml resolved (tried --art-spec, $%s, %s). "
            "Production calls must run under the game's art-spec; for spec-less "
            "exploratory/concept work pass --no-art-spec explicitly."
            % (ART_SPEC_ENV, ", ".join(DEFAULT_SPEC_GLOBS))
        )
    return load_art_spec(path), path


def get_path(data: Any, dotted: str, default=None):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _collect_hexes(node: Any, out: list[str]) -> None:
    if isinstance(node, str):
        if HEX_RE.match(node.strip()):
            h = node.strip().upper()
            if not h.startswith("#"):
                h = "#" + h
            if h not in out:
                out.append(h)
    elif isinstance(node, dict):
        for v in node.values():
            _collect_hexes(v, out)
    elif isinstance(node, list):
        for v in node:
            _collect_hexes(v, out)


def palette_hexes(spec: dict) -> list[str]:
    """All locked palette hexes: roles + dominant/neutrals/accent arrays + ramps."""
    out: list[str] = []
    _collect_hexes(spec.get("palette"), out)
    return out


def spec_finish(spec: dict) -> str | None:
    """craft.finish mapped to the flat/cel/rendered/any vocabulary (None if unset)."""
    finish = get_path(spec, "craft.finish")
    if not finish:
        return None
    return FINISH_MAP.get(str(finish), "any")


def light_direction(spec: dict) -> str | None:
    return get_path(spec, "craft.light_direction")


def declared_style_anchors(spec: dict) -> list[str]:
    """conditioning.style_anchor_images entries as declared in the spec."""
    anchors = get_path(spec, "conditioning.style_anchor_images") or []
    if not isinstance(anchors, list):
        anchors = [anchors]
    return [a for a in anchors if isinstance(a, str)]


def style_anchor_images(spec: dict, spec_path: str | Path | None = None) -> list[str]:
    """conditioning.style_anchor_images resolved against the project root derived
    from the spec path (never cwd alone) and existing on disk. Callers should
    compare against declared_style_anchors() and warn/fail when declared anchors
    do not resolve — a silently unconditioned production call is invalid."""
    resolved: list[str] = []
    for a in declared_style_anchors(spec):
        p = resolve_project_path(a, spec_path)
        if p.is_file():
            resolved.append(str(p))
    return resolved


def character_entry(spec: dict, char_id: str) -> dict | None:
    entry = get_path(spec, f"characters.{char_id}")
    return entry if isinstance(entry, dict) else None


def style_paragraph(spec: dict) -> str:
    """Assemble the verbatim style-token paragraph injected into every prompt.

    Values are copied VERBATIM from the spec — the paragraph transmits the
    user's locked style, it never invents adjectives.
    """
    lines: list[str] = []
    style_id = spec.get("style_id")
    lines.append(
        f"STYLE CONTRACT (from art-spec.yaml{', style_id=' + str(style_id) if style_id else ''} — obey verbatim, do not restyle):"
    )
    finish = get_path(spec, "craft.finish")
    if finish:
        lines.append(f"- finish: {finish}")
    light = get_path(spec, "craft.light_direction")
    if light:
        lines.append(f"- single consistent light direction: {light} (no rim light unless the spec says so)")
    dither = get_path(spec, "craft.dithering_policy")
    if dither:
        lines.append(f"- dithering: {dither}")
    shape = get_path(spec, "shape_language.primary")
    if shape:
        lines.append(f"- shape language: {shape}")
    avoid = get_path(spec, "shape_language.avoid")
    if isinstance(avoid, list) and avoid:
        lines.append(f"- avoid: {', '.join(str(a) for a in avoid)}")
    hexes = palette_hexes(spec)
    if hexes:
        lines.append(f"- palette (use ONLY these hexes): {', '.join(hexes)}")
    texture = get_path(spec, "materials.texture_language")
    if texture:
        lines.append(f"- texture language: {texture}")
    key = get_path(spec, "lighting.key")
    if key:
        lines.append(f"- key light: {key}")
    return "\n".join(lines)
