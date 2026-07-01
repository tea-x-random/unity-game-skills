#!/usr/bin/env python3
"""Scene-walk registry-resolution checker (deterministic, zero-dependency).

Enforces the assembly rule (docs/PIPELINE_CONVENTIONS.md gate order): scenes place
REGISTRY assets only — every art reference in a .unity scene (prefab instances,
sprites, meshes, materials) must resolve to an approved-registry entry (the
registry prefab itself, or a file inside a registered asset's approved folder).
Anything else is an assembly-time bypass. The gray-box escape hatch is
narrow and precise: engine-builtin primitives (builtin meshes/default
sprites) never fail, and placeholder NAMES (GameObject names containing the
marker, default "PLACEHOLDER") are reported for visibility — but any
FILE-based art reference must resolve to the registry regardless of object
naming. Never wire raw generated files into a scene, even as placeholders.
An EMPTY registry (no entries yet — legal during gray-box prototyping) is
reported as registry_empty, not failed; only unregistered art references or
a missing/malformed registry fail the gate.

This is the scripted version of unity-game-director's Verification instruction
("walk the scene and cross-check every visible sprite/mesh/material against
registry.yaml"). It parses Unity YAML textually — no Unity or PyYAML required —
by reading `guid:` references out of the scene file and resolving them through
the project's .meta files.

Examples:
  python3 check_scene_registry.py Assets/Scenes/Gameplay.unity \
    --registry Assets/MyGame/Art/Approved/registry.yaml

  python3 check_scene_registry.py Assets/Scenes/*.unity \
    --registry Assets/MyGame/Art/Approved/registry.yaml \
    --json-report Assets/MyGame/Art/QA/scene-registry.json

Exit codes: 0 = every file-based art reference resolves to the registry
(engine builtins exempt), 2 = bypasses found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GUID_RE = re.compile(r"\{fileID:\s*-?\d+,\s*guid:\s*([0-9a-f]{32})\s*,")
META_GUID_RE = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)
NAME_RE = re.compile(r"^\s*m_Name:\s*(.+)$", re.MULTILINE)

# Reference keys that carry ART (visible) assets. Script/logic references are ignored.
ART_KEYS = ("m_SourcePrefab", "m_Sprite", "m_Mesh", "m_Materials", "m_Material", "m_Texture")
ART_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".psd", ".tga", ".gif", ".exr", ".tif", ".tiff",  # textures/sprites
    ".fbx", ".obj", ".glb", ".gltf", ".dae", ".blend",                           # models
    ".mat", ".spriteatlas", ".spriteatlasv2",                                    # materials/atlases
    ".prefab",                                                                    # prefab instances
}
UNITY_BUILTIN_GUID = "0000000000000000f000000000000000"  # builtin extra resources (engine primitives)


def project_root_for(anchor: Path) -> Path:
    p = anchor.resolve()
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "Assets" and i > 0:
            return Path(*parts[:i])
    return Path.cwd()


def meta_guid(asset_path: Path) -> str | None:
    meta = Path(str(asset_path) + ".meta")
    if not meta.exists():
        return None
    m = META_GUID_RE.search(meta.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def build_guid_index(root: Path) -> dict[str, str]:
    """guid -> Assets-relative path, for every .meta under Assets/."""
    index: dict[str, str] = {}
    assets = root / "Assets"
    if not assets.is_dir():
        return index
    for meta in assets.rglob("*.meta"):
        try:
            m = META_GUID_RE.search(meta.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if m:
            index[m.group(1)] = str(meta.relative_to(root))[: -len(".meta")]
    return index


def load_registry_allowlist(registry_path: Path, root: Path) -> tuple[set[str], list[str], bool]:
    """Allowed GUIDs: each registry entry's prefab + every asset in its approved folder
    (contract directory). Returns (guids, problems, registry_empty).

    A registry with ZERO entries is the legal gray-box state (primitives-only
    scenes, R10) — it is reported as registry_empty, never a problem/failure."""
    allowed: set[str] = set()
    problems: list[str] = []
    text = registry_path.read_text(encoding="utf-8", errors="replace")
    # Textual extraction keeps this zero-dep: prefab:/contract: path values.
    refs = re.findall(r"^\s*(?:prefab|contract):\s*(\S+)\s*$", text, re.MULTILINE)
    for ref in refs:
        ref = ref.strip("'\"")
        p = root / ref
        if ref.endswith(".yaml"):  # contract -> allow everything in its directory
            cdir = p.parent
            if not cdir.is_dir():
                problems.append(f"contract directory missing: {cdir}")
                continue
            for f in cdir.rglob("*"):
                if f.is_file() and not f.name.endswith(".meta"):
                    g = meta_guid(f)
                    if g:
                        allowed.add(g)
        else:  # prefab (allow with or without .prefab extension recorded)
            cand = p if p.exists() else Path(str(p) + ".prefab")
            g = meta_guid(cand)
            if g:
                allowed.add(g)
            else:
                problems.append(f"registry prefab has no .meta/guid: {ref}")
    return allowed, problems, not refs


def scan_scene(scene_path: Path, allowed: set[str], guid_index: dict[str, str],
               placeholder_marker: str) -> dict:
    text = scene_path.read_text(encoding="utf-8", errors="replace")
    placeholder_names = {n.strip() for n in NAME_RE.findall(text)
                         if placeholder_marker.lower() in n.lower()}
    art_refs: dict[str, str] = {}  # guid -> the key it appeared under
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(ART_KEYS) and not stripped.startswith("- "):
            continue
        for m in GUID_RE.finditer(line):
            key = stripped.split(":", 1)[0].lstrip("- ").strip()
            art_refs.setdefault(m.group(1), key)

    unresolved = []
    builtin = []
    external = []
    resolved = 0
    for guid, key in sorted(art_refs.items()):
        if guid == UNITY_BUILTIN_GUID:
            builtin.append({"guid": guid, "via": key, "note": "engine builtin resource (primitive/default sprite)"})
            continue
        path = guid_index.get(guid)
        if path is None:
            # Not under Assets/ -> a Packages/ or engine asset; informational only.
            external.append({"guid": guid, "via": key, "note": "not under Assets/ (package/engine asset)"})
            continue
        # Only art files count; scripts/scriptable objects/etc. are out of scope.
        if Path(path).suffix.lower() not in ART_EXTENSIONS:
            continue
        if guid in allowed:
            resolved += 1
            continue
        unresolved.append({"guid": guid, "via": key, "path": path})
    return {
        "scene": str(scene_path),
        "art_references": len(art_refs),
        "resolved_to_registry": resolved,
        "unregistered": unresolved,
        "package_or_engine": external,
        "engine_builtins": builtin,
        "placeholder_flagged_names": sorted(placeholder_names),
        "pass": not unresolved,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Check that a Unity scene places only approved-registry art.")
    p.add_argument("scenes", nargs="+", help="Path(s) to .unity scene files")
    p.add_argument("--registry", required=True, help="Path to Art/Approved/registry.yaml")
    p.add_argument("--placeholder-marker", default="PLACEHOLDER",
                   help="GameObject-name substring that marks intentional gray-box placeholders (default: PLACEHOLDER)")
    p.add_argument("--json-report", help="Write the JSON report to this path")
    args = p.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Error: registry not found: {registry_path}", file=sys.stderr)
        return 2
    root = project_root_for(registry_path)
    allowed, problems, registry_empty = load_registry_allowlist(registry_path, root)
    guid_index = build_guid_index(root)

    scenes = []
    for scene in args.scenes:
        sp = Path(scene)
        if not sp.exists():
            problems.append(f"scene not found: {scene}")
            continue
        scenes.append(scan_scene(sp, allowed, guid_index, args.placeholder_marker))

    ok = bool(scenes) and all(s["pass"] for s in scenes) and not problems
    report = {
        "schema": "unity-game-skills.scene-registry-check.v1",
        "registry": str(registry_path),
        "registry_empty": registry_empty,  # legal gray-box state (warning only, never a failure)
        "allowed_guids": len(allowed),
        "problems": problems,
        "scenes": scenes,
        "result": "pass" if ok else "fail",
    }
    out = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
