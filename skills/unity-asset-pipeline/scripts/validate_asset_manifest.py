#!/usr/bin/env python3
"""Validate a Unity generated-asset contract or approved-asset registry.

Designed to run before Unity import and before scene assembly. It intentionally
checks machine-readable contract data, not aesthetic quality.

Examples:
  python3 validate_asset_manifest.py Assets/Art/Approved/tree/asset-contract.yaml \
    --art-spec Assets/GameArt/_ArtDirection/art-spec.yaml \
    --sprite-qa Assets/Art/QA/tree.sprite-qa.json \
    --image-critique Assets/Art/QA/tree.critique.json

  python3 validate_asset_manifest.py --registry Assets/Art/Approved/registry.yaml \
    --art-spec Assets/GameArt/_ArtDirection/art-spec.yaml --require-approved
"""

from __future__ import annotations

import argparse
import json
import os
import re
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


# ------------------------------- validators -------------------------------

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

    required = [
        "schema", "id", "family", "role", "style_id", "source", "source.generator",
        "runtime", "runtime.prefab", "runtime.pivot", "camera_contract",
        "camera_contract.projection", "qa",
    ]
    for field in required:
        add(checks, f"required.{field}", get_path(c, field) is not None, f"Required field {field} is present.")

    asset_id = get_path(c, "id")
    if asset_id:
        add(checks, "id.format", bool(re.fullmatch(r"[a-z][a-z0-9_]*", str(asset_id))), "Asset id must be snake_case and stable.", asset_id)
        add(checks, "id.dirname", contract_path.parent.name == str(asset_id), "Contract directory name should match asset id.", {"dir": contract_path.parent.name, "id": asset_id})

    generator = get_path(c, "source.generator")
    add(checks, "source.generator", generator in {"tripo", "gemini", "authored", "kitbash", "vendor"}, "Generator/source type is allowed.", generator)

    runtime_type = get_path(c, "runtime.type")
    if runtime_type == "sprite":
        add(checks, "runtime.ppu", isinstance(get_path(c, "runtime.pixels_per_unit"), (int, float)), "Sprite contracts require runtime.pixels_per_unit.", get_path(c, "runtime.pixels_per_unit"))
        add(checks, "import.alpha", get_path(c, "import.alpha_is_transparency") is True, "Foreground sprite import should preserve alpha.", get_path(c, "import.alpha_is_transparency"))
        add(checks, "import.mipmaps", get_path(c, "import.mipmaps") is False, "2D sprites/UI should import with mipmaps off.", get_path(c, "import.mipmaps"))

    if args.art_spec:
        art = load_data(args.art_spec)
        spec_style = find_key(art, "style_id")
        add(checks, "art_spec.style_id", spec_style == get_path(c, "style_id"), "Contract style_id matches art-spec.yaml.", {"contract": get_path(c, "style_id"), "art_spec": spec_style})

    if args.composition:
        comp = load_data(args.composition)
        profile_id = find_key(comp, "profile_id") or find_key(comp, "id")
        contract_profile = get_path(c, "camera_contract.profile_id")
        if profile_id and contract_profile:
            add(checks, "composition.profile", profile_id == contract_profile, "Contract camera profile matches composition profile.", {"contract": contract_profile, "composition": profile_id})
        for field in ("projection", "yaw", "pitch"):
            comp_value = find_key(comp, field)
            contract_value = get_path(c, f"camera_contract.{field}")
            if comp_value is not None and contract_value is not None:
                add(checks, f"composition.{field}", comp_value == contract_value, f"Camera {field} matches composition profile.", {"contract": contract_value, "composition": comp_value})

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

    art_style = None
    if args.art_spec:
        art_style = find_key(load_data(args.art_spec), "style_id")

    root = registry_path.parent
    for idx, entry in enumerate(assets):
        prefix = f"asset[{idx}]"
        if not isinstance(entry, dict):
            add(checks, prefix, False, "Registry asset entry must be a mapping.")
            continue
        for field in ("id", "contract", "prefab", "family", "role", "style_id", "qa"):
            add(checks, f"{prefix}.{field}", entry.get(field) is not None, f"Registry entry has {field}.")
        if art_style is not None:
            add(checks, f"{prefix}.style_id", entry.get("style_id") == art_style, "Registry style_id matches art-spec.yaml.", {"registry": entry.get("style_id"), "art_spec": art_style})
        qa = entry.get("qa") or {}
        for flag, value in qa.items():
            if isinstance(value, bool):
                add(checks, f"{prefix}.qa.{flag}", value is True, f"Registry QA flag {flag} is true.", value)
        contract = entry.get("contract")
        if contract:
            cp = Path(contract)
            if not cp.is_absolute():
                # Try current working directory first, then registry-relative.
                cp = cp if cp.exists() else (root / contract)
            add(checks, f"{prefix}.contract.exists", cp.exists(), "Referenced contract exists.", str(cp))

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
    p.add_argument("--art-spec", help="Path to art-spec.yaml; style_id must match")
    p.add_argument("--composition", help="Path to composition.yaml; camera_contract must match when fields exist")
    p.add_argument("--sprite-qa", help="Path to validate_sprite.py JSON report; must pass")
    p.add_argument("--image-critique", help="Path to critique_image.py JSON report; verdict must pass")
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
