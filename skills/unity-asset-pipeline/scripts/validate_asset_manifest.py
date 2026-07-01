#!/usr/bin/env python3
"""Validate a Unity generated-asset contract or approved-asset registry.

Designed to run before Unity import and before scene assembly. It intentionally
checks machine-readable contract data, not aesthetic quality.

Coherence checks (art-spec resolution, style_id, PPU, computed palette/scale)
are DEFAULT-ON and FAIL when their inputs are absent. Pass --no-art-spec only
for exploratory/concept contracts; production contracts must validate against
the spec resolved from --art-spec or the contract's own `art_spec:` path.

Examples:
  python3 validate_asset_manifest.py \
    Assets/<Game>/Art/Approved/tree/asset-contract.yaml \
    --sprite-qa Assets/<Game>/Art/Source/QA/tree.sprite-qa.json \
    --image-critique Assets/<Game>/Art/Source/QA/tree.critique.json

  python3 validate_asset_manifest.py \
    --registry Assets/<Game>/Art/Approved/registry.yaml --require-approved
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:  # Prefer PyYAML when available; fallback parser below covers our templates.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - tested via fallback in this repo
    yaml = None


# ------------------------- small YAML-ish fallback -------------------------

def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def parse_scalar(text: str) -> Any:
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
        return [parse_scalar(part.strip()) for part in re.split(r",(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", inner)]
    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except Exception:
            pass
    if re.fullmatch(r"-?\d+\.\d+", text):
        try:
            return float(text)
        except Exception:
            pass
    return text


def fallback_yaml_load(text: str) -> Any:
    raw = []
    for line in text.splitlines():
        if not line.strip() or line.strip() == "---":
            continue
        clean = strip_comment(line).rstrip()
        if clean.strip():
            raw.append((len(clean) - len(clean.lstrip(" ")), clean.lstrip(" ")))

    def parse_block(index: int, indent: int):
        if index >= len(raw):
            return {}, index
        is_list = raw[index][0] == indent and raw[index][1].startswith("- ")
        if is_list:
            result = []
            while index < len(raw) and raw[index][0] == indent and raw[index][1].startswith("- "):
                item_text = raw[index][1][2:].strip()
                index += 1
                if not item_text:
                    child, index = parse_block(index, indent + 2)
                    result.append(child)
                elif ":" in item_text and not item_text.startswith(('"', "'")):
                    key, val = item_text.split(":", 1)
                    item = {key.strip(): parse_scalar(val)} if val.strip() else {key.strip(): None}
                    # Additional fields nested under this list item.
                    while index < len(raw) and raw[index][0] >= indent + 2:
                        child_indent, child_text = raw[index]
                        if child_indent == indent + 2 and ":" in child_text:
                            ck, cv = child_text.split(":", 1)
                            index += 1
                            if cv.strip():
                                item[ck.strip()] = parse_scalar(cv)
                            else:
                                child, index = parse_block(index, child_indent + 2)
                                item[ck.strip()] = child
                        else:
                            break
                    result.append(item)
                else:
                    result.append(parse_scalar(item_text))
            return result, index

        result = {}
        while index < len(raw):
            line_indent, text = raw[index]
            if line_indent < indent:
                break
            if line_indent > indent:
                break
            if ":" not in text:
                raise ValueError(f"Cannot parse YAML line: {text}")
            key, val = text.split(":", 1)
            key = key.strip()
            val = val.strip()
            index += 1
            if val:
                result[key] = parse_scalar(val)
            else:
                child, index = parse_block(index, indent + 2)
                result[key] = child
        return result, index

    parsed, _ = parse_block(0, raw[0][0] if raw else 0)
    return parsed


def load_data(path: str | Path) -> Any:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is not None:
        return yaml.safe_load(text)
    return fallback_yaml_load(text)


def get_path(data: Any, dotted: str, default=None):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def find_key(data: Any, key: str):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = find_key(value, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_key(item, key)
            if found is not None:
                return found
    return None


# --------------------------- path / spec resolution ---------------------------

def project_root_for(anchor: Path) -> Path:
    """Derive the Unity project root from any path containing an Assets/ segment."""
    p = anchor.resolve()
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "Assets" and i > 0:
            return Path(*parts[:i])
    return Path.cwd()


def resolve_project_path(ref: str, anchor: Path) -> Path:
    """Resolve an Assets/-relative reference against the project root derived
    from `anchor` (fixes the double-prefix bug when cwd != project root)."""
    rp = Path(ref)
    if rp.is_absolute():
        return rp
    for base in (project_root_for(anchor), Path.cwd(), anchor.parent):
        cand = base / rp
        if cand.exists():
            return cand
    return project_root_for(anchor) / rp


def resolve_art_spec(args: argparse.Namespace, declared_ref, anchor: Path):
    """Return (spec_data, spec_path, ref). spec_data is None when unresolved."""
    ref = args.art_spec or declared_ref
    if not ref:
        return None, None, None
    p = resolve_project_path(str(ref), anchor)
    if not p.exists():
        return None, None, str(ref)
    try:
        return load_data(p), p, str(ref)
    except Exception:
        return None, p, str(ref)


def spec_pixels_per_unit(spec: Any):
    """art-spec craft.pixels_per_unit is the project PPU SSOT."""
    ppu = get_path(spec, "craft.pixels_per_unit")
    if ppu is None:
        ppu = find_key(spec, "pixels_per_unit")
    return ppu


HEX_RE = re.compile(r"#?[0-9A-Fa-f]{6}")


def collect_palette_hexes(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        t = node.strip()
        if HEX_RE.fullmatch(t):
            out.append(t if t.startswith("#") else f"#{t}")
    elif isinstance(node, dict):
        for value in node.values():
            out.extend(collect_palette_hexes(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(collect_palette_hexes(item))
    # Dedupe, preserving order.
    seen: set[str] = set()
    unique = []
    for h in out:
        k = h.lower()
        if k not in seen:
            seen.add(k)
            unique.append(h)
    return unique


def check_game_theme_hexes(checks: list[dict], spec: Any,
                           anchor: Path, override: str | None) -> None:
    """GameTheme.cs color hexes must be a subset of the art-spec palette subtree
    (palette.roles + arrays + ramps) — colors only; typography/spacing/radii are
    GameTheme-native (docs/PIPELINE_CONVENTIONS.md derivation rule)."""
    ref = override or get_path(spec, "derived_artifacts.game_theme_cs")
    if not ref:
        return
    theme_path = resolve_project_path(str(ref), anchor)
    if not theme_path.exists():
        if override:
            add(checks, "palette.game_theme", False, "--game-theme path does not exist.", str(theme_path))
        return  # derived view not generated yet — nothing to compare
    spec_hexes = {h.lower() for h in collect_palette_hexes(spec.get("palette") if isinstance(spec, dict) else None)}
    if not spec_hexes:
        add(checks, "palette.game_theme", False, "art-spec palette block contains no hex colors; GameTheme equality cannot be computed.", str(theme_path))
        return
    text = theme_path.read_text(encoding="utf-8", errors="replace")
    theme_hexes = {f"#{m.lower()}" for m in re.findall(r"#([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?\b", text)}
    rogue = sorted(theme_hexes - spec_hexes)
    add(checks, "palette.game_theme", not rogue,
        "Every GameTheme.cs color hex exists in the art-spec palette (roles/arrays/ramps) — GameTheme is a DERIVED view; regenerate it from the spec instead of hand-editing colors.",
        {"game_theme": str(theme_path), "rogue_hexes": rogue, "theme_hexes": len(theme_hexes), "spec_hexes": len(spec_hexes)})


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """Zero-dependency PNG IHDR width/height read."""
    try:
        with open(path, "rb") as f:
            header = f.read(26)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            return None
        return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
    except Exception:
        return None


def find_validate_sprite() -> Path | None:
    env = os.environ.get("VALIDATE_SPRITE_PY")
    candidates = [Path(env)] if env else []
    here = Path(__file__).resolve()
    candidates += [
        here.parent.parent.parent / "unity-image-generator" / "scripts" / "validate_sprite.py",
        Path.home() / ".claude" / "skills" / "unity-image-generator" / "scripts" / "validate_sprite.py",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def run_sprite_palette_check(image: Path, hexes: list[str], finish, spec_path: Path | None) -> dict:
    """Compute palette_valid by running validate_sprite.py as a subprocess
    (it needs Pillow; this script stays zero-dep). Failures to RUN fail the
    gate loudly — a check that cannot execute is a failed check, not a skip."""
    tool = find_validate_sprite()
    if tool is None:
        return {"ok": False, "message": "validate_sprite.py not found (unity-image-generator skill) and VALIDATE_SPRITE_PY unset; palette_valid cannot be computed."}
    cmd = [sys.executable, str(tool), str(image), "--palette", ",".join(hexes)]
    if spec_path is not None:
        cmd += ["--art-spec", str(spec_path)]
    else:
        cmd += ["--no-art-spec"]
    if finish == "pixel":
        # Default palette check is an AVERAGE-distance heuristic; pixel art uses
        # deterministic per-pixel palette membership instead.
        cmd += ["--palette-mode", "exact"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as exc:
        return {"ok": False, "message": f"validate_sprite.py could not run: {exc}"}
    try:
        report = json.loads(proc.stdout)
    except Exception:
        return {"ok": False, "message": f"validate_sprite.py produced no JSON report (exit {proc.returncode}; likely missing Pillow): {proc.stderr.strip()[:400]}"}
    palette_checks = [ch for ch in report.get("checks", []) if str(ch.get("id", "")).startswith("palette.")]
    if not palette_checks:
        return {"ok": False, "message": "validate_sprite.py ran but reported no palette checks."}
    failed = [ch for ch in palette_checks if ch.get("status") == "fail"]
    return {
        "ok": not failed,
        "message": "palette_valid computed via validate_sprite.py against the art-spec palette (pixel finish uses exact per-pixel membership; other finishes the average-distance heuristic).",
        "value": {"tool_exit": proc.returncode, "palette_checks": palette_checks},
    }


# ------------------------------- validators -------------------------------

ALLOWED_GENERATORS = {"pixellab", "tripo", "gemini", "authored", "kitbash", "vendor", "elevenlabs"}


def add(checks: list[dict], check_id: str, ok: bool, message: str, value=None, threshold=None):
    checks.append({
        "id": check_id,
        "status": "pass" if ok else "fail",
        "message": message,
        "value": value,
        "threshold": threshold,
    })


def validate_contract(contract_path: Path, args: argparse.Namespace) -> dict:
    c = load_data(contract_path)
    checks: list[dict] = []

    runtime_type = get_path(c, "runtime.type")
    required = [
        "schema", "id", "family", "role", "style_id", "source", "source.generator",
        "runtime", "runtime.type", "qa",
    ]
    if runtime_type == "audio":
        # Audio clips have no prefab/pivot/camera; they require the audio import section.
        required += [
            "runtime.audio", "runtime.audio.load_type", "runtime.audio.force_to_mono",
            "runtime.audio.loop", "runtime.audio.target_lufs",
        ]
    else:
        required += ["runtime.prefab", "runtime.pivot", "camera_contract", "camera_contract.projection"]
    for field in required:
        add(checks, f"required.{field}", get_path(c, field) is not None, f"Required field {field} is present.")

    asset_id = get_path(c, "id")
    if asset_id:
        add(checks, "id.format", bool(re.fullmatch(r"[a-z][a-z0-9_]*", str(asset_id))), "Asset id must be snake_case and stable.", asset_id)
        add(checks, "id.dirname", contract_path.parent.name == str(asset_id), "Contract directory name should match asset id.", {"dir": contract_path.parent.name, "id": asset_id})

    generator = get_path(c, "source.generator")
    add(checks, "source.generator", generator in ALLOWED_GENERATORS, "Generator/source type is allowed.", generator)

    if runtime_type == "sprite":
        add(checks, "runtime.ppu", isinstance(get_path(c, "runtime.pixels_per_unit"), (int, float)), "Sprite contracts require runtime.pixels_per_unit.", get_path(c, "runtime.pixels_per_unit"))
        add(checks, "import.alpha", get_path(c, "import.alpha_is_transparency") is True, "Foreground sprite import should preserve alpha.", get_path(c, "import.alpha_is_transparency"))
        add(checks, "import.mipmaps", get_path(c, "import.mipmaps") is False, "2D sprites/UI should import with mipmaps off.", get_path(c, "import.mipmaps"))

    # ---- coherence: art-spec (default-on; FAIL when absent) ----
    spec = None
    spec_path = None
    if args.no_art_spec:
        add(checks, "coherence.art_spec", True, "art-spec coherence + computed palette/scale/PPU checks SKIPPED via --no-art-spec (exploratory only; never approve production assets this way).")
    else:
        spec, spec_path, ref = resolve_art_spec(args, get_path(c, "art_spec"), contract_path)
        add(checks, "coherence.art_spec", spec is not None,
            "art-spec resolved (from --art-spec or the contract's art_spec: path). Production validation FAILS without it; use --no-art-spec only for exploratory work.",
            {"ref": ref, "resolved": str(spec_path) if spec_path else None})

    if spec is not None:
        spec_style = find_key(spec, "style_id")
        add(checks, "art_spec.style_id", spec_style == get_path(c, "style_id"), "Contract style_id matches art-spec.yaml.", {"contract": get_path(c, "style_id"), "art_spec": spec_style})

        if runtime_type == "sprite":
            ppu_spec = spec_pixels_per_unit(spec)
            ppu_contract = get_path(c, "runtime.pixels_per_unit")
            add(checks, "ppu.matches_art_spec",
                isinstance(ppu_spec, (int, float)) and ppu_contract == ppu_spec,
                "runtime.pixels_per_unit equals art-spec craft.pixels_per_unit (the project PPU SSOT; one game = one PPU).",
                {"contract": ppu_contract, "art_spec": ppu_spec})

    # ---- coherence: composition (default-on; FAIL when absent; audio has no camera) ----
    comp = None
    if not args.no_art_spec and not args.no_composition and runtime_type != "audio":
        comp_path = None
        if args.composition:
            comp_path = resolve_project_path(args.composition, contract_path)
        elif spec_path is not None:
            sibling = spec_path.parent / "composition.yaml"
            comp_path = sibling if sibling.exists() else None
        if comp_path is not None and comp_path.exists():
            comp = load_data(comp_path)
        add(checks, "coherence.composition", comp is not None,
            "composition.yaml resolved (--composition or sibling of the art-spec). Camera coherence cannot be verified without it; use --no-composition only when no composition profile exists yet.",
            str(comp_path) if comp_path else args.composition)

    if comp is not None:
        profile_id = find_key(comp, "profile_id") or find_key(comp, "id")
        contract_profile = get_path(c, "camera_contract.profile_id")
        if profile_id and contract_profile:
            add(checks, "composition.profile", profile_id == contract_profile, "Contract camera profile matches composition profile.", {"contract": contract_profile, "composition": profile_id})
        for field in ("projection", "yaw", "pitch"):
            comp_value = find_key(comp, field)
            contract_value = get_path(c, f"camera_contract.{field}")
            if comp_value is not None and contract_value is not None:
                add(checks, f"composition.{field}", comp_value == contract_value, f"Camera {field} matches composition profile.", {"contract": contract_value, "composition": comp_value})
        if spec is not None:
            spec_light = get_path(spec, "craft.light_direction")
            comp_light = get_path(comp, "shadow_and_contact.key_light_direction") or find_key(comp, "key_light_direction")
            if spec_light is not None or comp_light is not None:
                add(checks, "composition.key_light_direction", spec_light == comp_light,
                    "composition.yaml shadow_and_contact.key_light_direction equals art-spec craft.light_direction (one global light direction; string inequality = failure).",
                    {"art_spec": spec_light, "composition": comp_light})

    # ---- computed palette_valid + scale_valid (sprite contracts only) ----
    if runtime_type == "sprite" and not args.no_art_spec:
        src_ref = get_path(c, "source.source_art")
        src_path = resolve_project_path(str(src_ref), contract_path) if src_ref else None
        src_ok = src_path is not None and src_path.exists()
        add(checks, "source.source_art", src_ok, "source.source_art is set and exists (required to compute palette_valid/scale_valid).", src_ref)

        if spec is not None:
            hexes = collect_palette_hexes(spec.get("palette") if isinstance(spec, dict) else None)
            if not hexes:
                add(checks, "palette.computed", False, "art-spec palette block contains no hex colors; palette_valid cannot be computed.")
            elif not src_ok:
                add(checks, "palette.computed", False, "palette_valid cannot be computed without readable source art.")
            else:
                result = run_sprite_palette_check(src_path, hexes, get_path(spec, "craft.finish"), spec_path)
                add(checks, "palette.computed", result["ok"], result["message"], result.get("value"))

        dims = png_dimensions(src_path) if src_ok else None
        ppu_contract = get_path(c, "runtime.pixels_per_unit")
        scale_m = get_path(c, "runtime.scale_meters")
        if dims and isinstance(ppu_contract, (int, float)) and ppu_contract > 0 and isinstance(scale_m, list) and len(scale_m) >= 2 and isinstance(scale_m[1], (int, float)) and scale_m[1] > 0:
            world_h = dims[1] / ppu_contract
            ok = abs(world_h - scale_m[1]) <= args.scale_tolerance * scale_m[1]
            add(checks, "scale.computed", ok,
                f"Sprite world height (height_px / PPU) within {int(args.scale_tolerance * 100)}% of runtime.scale_meters[1]. 3D scale_valid stays with the Editor import validator.",
                {"world_height": round(world_h, 3), "target": scale_m[1], "dims": list(dims)}, args.scale_tolerance)
        else:
            add(checks, "scale.computed", False, "scale_valid cannot be computed: needs readable PNG source art, runtime.pixels_per_unit, and runtime.scale_meters.", {"dims": list(dims) if dims else None, "ppu": ppu_contract, "scale_meters": scale_m})
        if spec is not None and get_path(spec, "craft.finish") == "pixel":
            tile = get_path(spec, "craft.tile_size")
            if isinstance(tile, int) and tile > 0 and dims:
                add(checks, "scale.tile_multiple", dims[0] % tile == 0 and dims[1] % tile == 0, "Pixel sprite canvas is a whole multiple of art-spec craft.tile_size.", {"dims": list(dims), "tile_size": tile})

    # ---- GameTheme.cs derived-view palette equality (colors only) ----
    if spec is not None:
        check_game_theme_hexes(checks, spec, contract_path, args.game_theme)

    # ---- animation identity gate: frame-vs-anchor diff reports ----
    animation = get_path(c, "animation")
    frame_diff_refs = list(args.frame_diff or [])
    declared_fd = get_path(c, "qa.frame_diff_report")
    if declared_fd and not frame_diff_refs:
        frame_diff_refs.append(str(declared_fd))
    frame_based_2d = bool(animation) and (runtime_type == "sprite" or get_path(c, "animation.sheet") is not None)
    if animation and not frame_diff_refs and not args.no_art_spec:
        if frame_based_2d:
            add(checks, "frame_diff.report", False,
                "Contract has a frame-based 2D animation block but no frame-diff report (--frame-diff or qa.frame_diff_report). Run unity-pixel-art/scripts/compare_frames_to_anchor.py on every shipped strip/rotation set.",
                {"animation": True, "runtime_type": runtime_type})
        else:
            add(checks, "frame_diff.report", True,
                "frame_diff N/A: 3D skeletal animation (no sprite sheet) — identity is validated by unity-3d-generator validate-animation instead of frame diffs.",
                {"animation": True, "runtime_type": runtime_type})
    for ref in frame_diff_refs:
        fd_path = resolve_project_path(str(ref), contract_path)
        if not fd_path.exists():
            add(checks, "frame_diff.report", False, "Referenced frame-diff report does not exist.", str(fd_path))
            continue
        fd = load_data(fd_path)
        ok = fd.get("pass") is True and not fd.get("failed_frames")
        add(checks, "frame_diff.report", ok,
            "Referenced compare_frames_to_anchor.py report passes (deterministic frame-vs-anchor identity gate; sets qa.frame_diff_valid).",
            {"report": str(fd_path), "pass": fd.get("pass"), "failed_frames": fd.get("failed_frames")})

    if args.sprite_qa:
        qa = load_data(args.sprite_qa)
        ok = qa.get("result") == "pass" and qa.get("summary", {}).get("failures", 0) == 0
        add(checks, "sprite_qa.result", ok, "Referenced sprite QA report passes.", {"report": args.sprite_qa, "result": qa.get("result"), "summary": qa.get("summary")})

    if args.image_critique:
        critique = load_data(args.image_critique)
        verdict = get_path(critique, "critique.verdict") or critique.get("verdict")
        overall = get_path(critique, "critique.overall") or critique.get("overall")
        if overall is None:
            overall = get_path(critique, "critique.scores.overall")
        ok = verdict == "pass"
        add(checks, "image_critique.result", ok, "Referenced vision critique passes.", {"report": args.image_critique, "verdict": verdict, "overall": overall})

    if args.require_approved:
        qa = get_path(c, "qa", {}) or {}
        bool_flags = [k for k, v in qa.items() if isinstance(v, bool) and k != "approved"]
        for flag in bool_flags:
            add(checks, f"qa.{flag}", qa.get(flag) is True, f"QA flag {flag} is true.", qa.get(flag))
        add(checks, "qa.approved", qa.get("approved") is True, "Contract is explicitly approved.", qa.get("approved"))

    failures = [x for x in checks if x["status"] == "fail"]
    return {
        "schema": "unity-game-skills.asset-manifest-validation.v1",
        "target": str(contract_path),
        "mode": "contract",
        "result": "pass" if not failures else "fail",
        "summary": {"checks": len(checks), "failures": len(failures)},
        "checks": checks,
    }


def validate_registry(registry_path: Path, args: argparse.Namespace) -> dict:
    registry = load_data(registry_path)
    checks: list[dict] = []
    assets = registry.get("assets", []) if isinstance(registry, dict) else []
    add(checks, "registry.schema", isinstance(registry, dict) and registry.get("schema") is not None, "Registry has schema.")
    add(checks, "registry.assets", isinstance(assets, list) and len(assets) > 0, "Registry has at least one asset.", len(assets))

    root = project_root_for(registry_path)

    # ---- coherence: art-spec + composition (default-on; FAIL when absent) ----
    spec = None
    if args.no_art_spec:
        add(checks, "coherence.art_spec", True, "art-spec coherence SKIPPED via --no-art-spec (exploratory only).")
    else:
        declared = registry.get("art_spec") if isinstance(registry, dict) else None
        spec, spec_path, ref = resolve_art_spec(args, declared, registry_path)
        add(checks, "coherence.art_spec", spec is not None,
            "art-spec resolved (from --art-spec or the registry's art_spec: key). Registry validation FAILS without it; use --no-art-spec only for exploratory work.",
            {"ref": ref, "resolved": str(spec_path) if spec_path else None})
    if not args.no_art_spec and not args.no_composition:
        comp_ref = args.composition or (registry.get("composition_profile") if isinstance(registry, dict) else None)
        comp_path = resolve_project_path(str(comp_ref), registry_path) if comp_ref else None
        comp_ok = comp_path is not None and comp_path.exists()
        add(checks, "coherence.composition", comp_ok, "composition profile resolved (--composition or the registry's composition_profile: key).", comp_ref)
        if comp_ok and spec is not None:
            try:
                comp = load_data(comp_path)
            except Exception:
                comp = None
            if comp is not None:
                spec_light = get_path(spec, "craft.light_direction")
                comp_light = get_path(comp, "shadow_and_contact.key_light_direction") or find_key(comp, "key_light_direction")
                if spec_light is not None or comp_light is not None:
                    add(checks, "composition.key_light_direction", spec_light == comp_light,
                        "composition.yaml shadow_and_contact.key_light_direction equals art-spec craft.light_direction.",
                        {"art_spec": spec_light, "composition": comp_light})

    if spec is not None:
        check_game_theme_hexes(checks, spec, registry_path, args.game_theme)

    art_style = find_key(spec, "style_id") if spec is not None else None
    ppu_spec = spec_pixels_per_unit(spec) if spec is not None else None

    sprite_ppus: dict[str, Any] = {}
    for idx, entry in enumerate(assets):
        prefix = f"asset[{idx}]"
        if not isinstance(entry, dict):
            add(checks, prefix, False, "Registry asset entry must be a mapping.")
            continue
        # Audio entries reference the imported AudioClip via clip:; everything
        # else ships a prefab: (registry-schema.md rule 7).
        media_field = "clip" if entry.get("clip") is not None else "prefab"
        for field in ("id", "contract", media_field, "family", "role", "style_id", "qa"):
            add(checks, f"{prefix}.{field}", entry.get(field) is not None,
                f"Registry entry has {field}." if field != media_field
                else "Registry entry has prefab (or clip: for audio entries).")
        if art_style is not None:
            add(checks, f"{prefix}.style_id", entry.get("style_id") == art_style, "Registry style_id matches art-spec.yaml.", {"registry": entry.get("style_id"), "art_spec": art_style})
        qa = entry.get("qa") or {}
        for flag, value in qa.items():
            if isinstance(value, bool):
                add(checks, f"{prefix}.qa.{flag}", value is True, f"Registry QA flag {flag} is true.", value)
        contract = entry.get("contract")
        if contract:
            # Resolve project-root-relative first (root derived from the registry
            # path, so validation works from any cwd), then cwd, then registry-relative.
            cp = Path(contract)
            if not cp.is_absolute():
                for base in (root, Path.cwd(), registry_path.parent):
                    cand = base / contract
                    if cand.exists():
                        cp = cand
                        break
                else:
                    cp = root / contract
            add(checks, f"{prefix}.contract.exists", cp.exists(), "Referenced contract exists.", str(cp))
            if cp.exists():
                try:
                    cdata = load_data(cp)
                except Exception as exc:
                    add(checks, f"{prefix}.contract.parses", False, f"Referenced contract failed to parse: {exc}")
                else:
                    if get_path(cdata, "runtime.type") == "sprite":
                        sprite_ppus[str(entry.get("id") or prefix)] = get_path(cdata, "runtime.pixels_per_unit")

    # ---- one game = one PPU (uniformity across sprite contracts + vs spec) ----
    if sprite_ppus:
        values = set(sprite_ppus.values())
        add(checks, "registry.ppu_uniform", len(values) == 1 and None not in values,
            "All sprite contracts in the registry share ONE pixels_per_unit (one game = one PPU; no mixels).", sprite_ppus)
        if ppu_spec is not None:
            add(checks, "registry.ppu_matches_art_spec", values == {ppu_spec},
                "Registry sprite PPU equals art-spec craft.pixels_per_unit (project PPU SSOT).",
                {"registry": sorted({str(v) for v in values}), "art_spec": ppu_spec})

    failures = [x for x in checks if x["status"] == "fail"]
    return {
        "schema": "unity-game-skills.asset-manifest-validation.v1",
        "target": str(registry_path),
        "mode": "registry",
        "result": "pass" if not failures else "fail",
        "summary": {"checks": len(checks), "failures": len(failures)},
        "checks": checks,
    }


def build_parser():
    p = argparse.ArgumentParser(description="Validate an asset contract or approved-asset registry.")
    p.add_argument("contract", nargs="?", help="Path to asset-contract.yaml")
    p.add_argument("--registry", help="Validate an approved-asset registry instead of one contract")
    p.add_argument("--art-spec", help="Path to art-spec.yaml (default: resolved from the contract's art_spec: / registry's art_spec: key)")
    p.add_argument("--composition", help="Path to composition.yaml (default: sibling of the resolved art-spec / registry composition_profile:)")
    p.add_argument("--no-art-spec", action="store_true", help="EXPLORATORY ONLY: skip art-spec coherence + computed palette/scale/PPU checks")
    p.add_argument("--no-composition", action="store_true", help="Skip composition coherence when no composition profile exists yet")
    p.add_argument("--scale-tolerance", type=float, default=0.35, help="Allowed relative deviation of sprite world height vs runtime.scale_meters[1] (default: 0.35)")
    p.add_argument("--sprite-qa", help="Path to validate_sprite.py JSON report; must pass")
    p.add_argument("--image-critique", help="Path to critique_image.py JSON report; verdict must pass")
    p.add_argument("--frame-diff", action="append", help="Path to a compare_frames_to_anchor.py JSON report (repeatable; animation identity gate — must pass). Defaults to the contract's qa.frame_diff_report when set")
    p.add_argument("--game-theme", help="Path to GameTheme.cs (default: art-spec derived_artifacts.game_theme_cs). Its color hexes must all exist in the art-spec palette")
    p.add_argument("--require-approved", action="store_true", help="Require all boolean qa flags and qa.approved to be true")
    p.add_argument("--json-report", help="Write validation report to this path")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.registry:
        report = validate_registry(Path(args.registry), args)
    elif args.contract:
        report = validate_contract(Path(args.contract), args)
    else:
        raise SystemExit("Provide a contract path or --registry")
    text = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
