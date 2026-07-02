#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pixellab>=0.1.0",
#     "pillow>=10.0.0",
#     "pyyaml>=6.0",
#     "requests>=2.31",
# ]
# ///
"""Generate pixel-native sprites and animations with PixelLab.

Key resolution: --api-key, then PIXEL_LABS_API_KEY.

Art-spec resolution (production SSOT): --art-spec, then $UNITY_ART_SPEC, then probe
Assets/*/Art/_ArtDirection/art-spec.yaml plus the legacy roots Assets/GameArt/ and
Assets/Art/. Production (paid generation) commands FAIL without a resolved spec
unless --no-art-spec is passed (exploratory/concept work). When a spec resolves,
the script auto-fills: master palette swatch (conditioning.master_palette_png ->
color_image), golden anchor (conditioning.golden_assets.<--family|game> ->
bitforge style_image), outline enum (craft.outline_style), per-game default view/
shading enums (craft.view / craft.shading), canvas via --canvas
tile|character (craft.tile_size / craft.char_tiles), and records style_id / PPU /
light_direction / dithering_policy in the manifest. Explicit CLI flags override
spec values per call. light_direction/dithering_policy have NO API params — put
them in --description yourself; they are recorded for QA only.

This wraps the official PixelLab SDK (https://api.pixellab.ai/v1) and exposes the
full sprite + animation surface. Parameter names, ranges, and enums match the SDK:

  pixflux            text -> pixel image (PixFlux)
  bitforge           style/image-conditioned pixel image (BitForge); optional skeleton pose
  rotate             turn an existing sprite to a new direction/view
  estimate-skeleton  detect rest-pose keypoints from a base character (-> JSON)
  animate-skeleton   pose-driven animation frames; STRUCTURALLY CONSISTENT (preferred)
  animate-text       text/action animation frames conditioned on a reference (drifts more)
  inpaint            local edit inside a mask (fix weapon/eye/outline/frame detail)
  balance            account credit balance

Enums (from pixellab.types):
  view        : side | low top-down | high top-down
  direction   : south, south-east, east, north-east, north, north-west, west, south-west
  outline     : single color black outline | single color outline | selective outline | lineless
  shading     : flat shading | basic shading | medium shading | detailed shading | highly detailed shading
  detail      : low detail | medium detail | highly detailed

Palette lock uses a `color_image` (a forced-palette swatch), NOT a hex list. Pass
--color-image PNG, or --palette '#aabbcc' ... and this script builds the swatch for you.

Use --dry-run before any paid call. Run `balance` before batches.
"""

from __future__ import annotations

import argparse
import glob
import inspect
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.pixellab.ai/v1"

# Paid endpoints that must run under an art-spec (docs/PIPELINE_CONVENTIONS.md:
# production paths fail-unless-overridden via --no-art-spec).
PRODUCTION_COMMANDS = {
    "pixflux", "bitforge", "rotate", "animate-skeleton", "animate-text", "inpaint",
}

# Canonical + reserved legacy roots (docs/PIPELINE_CONVENTIONS.md).
# LOCKSTEP: this resolver intentionally duplicates unity-image-generator/scripts/
# art_spec.py ($UNITY_ART_SPEC + identical probe globs + fail-unless---no-art-spec)
# because cross-skill imports aren't established. Change BOTH together, and the
# conventions doc first (see PIPELINE_CONVENTIONS.md "Art-spec resolver lockstep").
ART_SPEC_PROBE_PATTERNS = [
    "Assets/*/Art/_ArtDirection/art-spec.yaml",
    "Assets/GameArt/_ArtDirection/art-spec.yaml",
    "Assets/Art/_ArtDirection/art-spec.yaml",
]

VIEWS = ["side", "low top-down", "high top-down"]
DIRECTIONS = [
    "south", "south-east", "east", "north-east",
    "north", "north-west", "west", "south-west",
]
OUTLINES = [
    "single color black outline", "single color outline",
    "selective outline", "lineless",
]
SHADINGS = [
    "flat shading", "basic shading", "medium shading",
    "detailed shading", "highly detailed shading",
]
DETAILS = ["low detail", "medium detail", "highly detailed"]


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _load_pil(path: str | None):
    if not path:
        return None
    from PIL import Image

    return Image.open(path).convert("RGBA")


def _adapt_style_image(path: str | None, width: int, height: int):
    """Load a bitforge style reference, adapted to the target canvas size.

    The live bitforge endpoint 500s when `image_size` differs from the style
    image's dimensions (verified empirically 2026-07-01), so a 32x64 character
    golden cannot directly condition a 32x32 tile. Adapt WITHOUT resampling
    (pixel art must never be scaled): per axis, center-crop when the style
    image is larger than the target, center-pad onto transparency when smaller.
    The adaptation is provenance-logged by the caller via style_image_adapted.
    """
    img = _load_pil(path)
    if img is None or img.size == (width, height):
        return img
    from PIL import Image

    src_w, src_h = img.size
    # Crop axes where the source exceeds the target (centered).
    left = max(0, (src_w - width) // 2)
    top = max(0, (src_h - height) // 2)
    img = img.crop((left, top, min(src_w, left + width), min(src_h, top + height)))
    # Pad axes where the source is smaller (centered on transparency).
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(img, ((width - img.width) // 2, (height - img.height) // 2))
    print(
        f"style image {path} is {src_w}x{src_h}; adapted (crop/pad, no resample) "
        f"to match the {width}x{height} canvas — bitforge rejects size mismatches.",
        file=sys.stderr,
    )
    return canvas


def _palette_to_color_image(hexes: list[str] | None):
    """Build a forced-palette swatch image from hex colors.

    PixelLab takes a `color_image` whose pixels define the allowed palette, not a
    list of hex strings. Each color becomes a 16x16 block in a single row.
    """
    if not hexes:
        return None
    from PIL import Image

    def _rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    cell = 16
    img = Image.new("RGB", (cell * len(hexes), cell), (0, 0, 0))
    for i, h in enumerate(hexes):
        for x in range(i * cell, (i + 1) * cell):
            for y in range(cell):
                img.putpixel((x, y), _rgb(h))
    return img


def _fallback_yaml_load(text: str) -> Any:
    """Minimal YAML mapping/list parser (PyYAML unavailable). Covers art-spec.yaml:
    nested mappings by 2-space indent, inline [a, b] lists, block lists of scalars."""

    def scalar(s: str) -> Any:
        s = s.strip()
        if s in ("", "null", "~", "Null", "NULL"):
            return None
        if s in ("true", "True"):
            return True
        if s in ("false", "False"):
            return False
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            return [scalar(p) for p in inner.split(",")] if inner else []
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def strip_comment(line: str) -> str:
        in_s = in_d = False
        for i, ch in enumerate(line):
            if ch == "'" and not in_d:
                in_s = not in_s
            elif ch == '"' and not in_s:
                in_d = not in_d
            elif ch == "#" and not in_s and not in_d:
                return line[:i]
        return line

    rows = []
    for line in text.splitlines():
        clean = strip_comment(line).rstrip()
        if not clean.strip() or clean.strip() == "---":
            continue
        rows.append((len(clean) - len(clean.lstrip(" ")), clean.strip()))

    def block(i: int, indent: int):
        if i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
            items = []
            while i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
                items.append(scalar(rows[i][1][2:]))
                i += 1
            return items, i
        result: dict[str, Any] = {}
        while i < len(rows):
            row_indent, content = rows[i]
            if row_indent != indent or ":" not in content:
                break
            key, _, val = content.partition(":")
            i += 1
            if val.strip():
                result[key.strip()] = scalar(val)
            elif i < len(rows) and rows[i][0] > indent:
                child, i = block(i, rows[i][0])
                result[key.strip()] = child
            else:
                result[key.strip()] = None
        return result, i

    parsed, _ = block(0, rows[0][0] if rows else 0)
    return parsed


def _load_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _fallback_yaml_load(text) or {}


def _spec_get(spec: Any, *keys: str, default: Any = None) -> Any:
    node = spec
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node if node is not None else default


def _resolve_art_spec(args) -> tuple[Any, str | None]:
    """Resolve the governing art-spec.yaml: --art-spec > $UNITY_ART_SPEC > probed roots."""
    if getattr(args, "no_art_spec", False):
        return None, None
    if getattr(args, "art_spec", None):
        p = Path(args.art_spec)
        if not p.is_file():
            raise SystemExit(f"--art-spec not found: {p}")
        return _load_yaml(p), str(p)
    env = os.getenv("UNITY_ART_SPEC")
    if env:
        p = Path(env)
        if not p.is_file():
            raise SystemExit(f"$UNITY_ART_SPEC points to a missing file: {p}")
        return _load_yaml(p), str(p)
    for pattern in ART_SPEC_PROBE_PATTERNS:
        for hit in sorted(glob.glob(pattern)):
            return _load_yaml(Path(hit)), hit
    return None, None


def _project_root_for(anchor: str | Path) -> Path:
    """Derive the Unity project root from any path containing an Assets/ segment
    (same logic as unity-asset-pipeline/scripts/validate_asset_manifest.py and
    unity-image-generator/scripts/art_spec.py — lockstep)."""
    p = Path(anchor).resolve()
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "Assets" and i > 0:
            return Path(*parts[:i])
    return Path.cwd()


def _resolve_spec_ref(ref: str, spec_path: str | None) -> Path:
    """Resolve a spec-internal Assets/-relative path (master palette, goldens,
    anchors) against the project root derived from the RESOLVED spec path, then
    cwd, then the spec's directory — never cwd alone, so conditioning artifacts
    resolve from any working directory."""
    rp = Path(ref)
    if rp.is_absolute():
        return rp
    bases: list[Path] = []
    if spec_path:
        bases.append(_project_root_for(spec_path))
    bases.append(Path.cwd())
    if spec_path:
        bases.append(Path(spec_path).parent)
    for base in bases:
        cand = base / rp
        if cand.exists():
            return cand
    return bases[0] / rp


def _apply_spec_defaults(args, spec: Any, spec_path: str) -> None:
    """Fill unset CLI values from the art-spec. Explicit CLI flags always win."""
    # Palette lock: master swatch unless --palette/--color-image given.
    if getattr(args, "color_image", None) is None and not getattr(args, "palette", None):
        master = _spec_get(spec, "conditioning", "master_palette_png")
        if master:
            resolved = _resolve_spec_ref(str(master), spec_path)
            if not resolved.is_file():
                raise SystemExit(
                    f"conditioning.master_palette_png missing on disk: {master} "
                    f"(resolved: {resolved}; spec: {spec_path}). Emit it via unity-art-direction before generating."
                )
            args.color_image = str(resolved)
    # Outline enum (PixelLab exact string).
    if hasattr(args, "outline") and args.outline is None:
        outline = _spec_get(spec, "craft", "outline_style")
        if outline in OUTLINES:
            args.outline = outline
    # Per-game default view/shading enums (PixelLab exact strings; CLI overrides).
    if hasattr(args, "view") and getattr(args, "view", None) is None:
        view = _spec_get(spec, "craft", "view")
        if view in VIEWS:
            args.view = view
    if hasattr(args, "shading") and getattr(args, "shading", None) is None:
        shading = _spec_get(spec, "craft", "shading")
        if shading in SHADINGS:
            args.shading = shading
    # Golden anchor conditioning for bitforge (R3 hard rule: every production
    # bitforge call is conditioned on its golden anchor — a declared-but-missing
    # golden fails LOUDLY, exactly like a missing master palette; it never
    # silently degrades to an unconditioned text roll).
    #
    # IMPORTANT (verified live 2026-07-01): the bitforge `style_image` pathway
    # produces structured NOISE at every strength (20/60/100, square and
    # rectangular canvases, opaque and transparent refs, SDK and raw HTTP).
    # The working conditioning channel on the live API is `init_image` +
    # `init_image_strength` (1-999): the golden acts as a structural/style init
    # and the description re-subjects it. Calibration from live probes:
    # cross-subject derivation ~75-150 (100 = clean new subject, same
    # proportions/baseline/palette; 175+ bleeds the anchor's identity);
    # same-asset variants/recolors 250-400.
    # Autofill is bitforge-only: pixflux is the text-only golden roll (no anchor
    # conditioning), and rotate/animate/inpaint take their reference/init images
    # explicitly per the derived-frames workflow.
    if getattr(args, "command", None) == "bitforge" and getattr(args, "init_image", None) is None and getattr(args, "style_image", None) is None:
        goldens = _spec_get(spec, "conditioning", "golden_assets", default={}) or {}
        family = getattr(args, "family", None)
        anchor = goldens.get(family) if family else None
        anchor = anchor or goldens.get("game")
        if not anchor:
            anchors = _spec_get(spec, "conditioning", "style_anchor_images", default=[]) or []
            anchor = anchors[0] if anchors else None
        if anchor:
            resolved = _resolve_spec_ref(str(anchor), spec_path)
            if not resolved.is_file():
                raise SystemExit(
                    f"golden anchor missing on disk: {anchor} (resolved: {resolved}; spec: {spec_path}). "
                    "Regenerate/approve it, or pass --init-image / --no-art-spec explicitly."
                )
            args.init_image = str(resolved)
            args.golden_autofilled = True
        elif getattr(args, "command", None) == "bitforge":
            raise SystemExit(
                "No conditioning source for production bitforge: the art-spec declares no "
                "conditioning.golden_assets (family/game) and no conditioning.style_anchor_images. "
                "Approve a golden anchor first (pixflux is the only text-only roll), or pass "
                "--init-image / --no-art-spec explicitly."
            )
    if getattr(args, "style_image", None) is not None:
        print(
            "WARNING: bitforge style_image produced structured noise at ALL strengths on the "
            "live API (verified 2026-07-01). Golden conditioning should use --init-image with "
            "--init-image-strength (cross-subject ~75-150, same-asset 250-400). Proceeding "
            "with style_image as explicitly requested.",
            file=sys.stderr,
        )
    # Canvas derived from tiles (never ad hoc): --canvas tile|character.
    if getattr(args, "canvas", None) and not (getattr(args, "width", None) and getattr(args, "height", None)):
        tile = _spec_get(spec, "craft", "tile_size")
        char_tiles = _spec_get(spec, "craft", "char_tiles")
        if args.canvas == "tile" and tile:
            args.width, args.height = int(tile), int(tile)
        elif args.canvas == "character" and tile and isinstance(char_tiles, list) and len(char_tiles) == 2:
            args.width, args.height = int(tile) * int(char_tiles[0]), int(tile) * int(char_tiles[1])
        else:
            raise SystemExit(
                f"--canvas {args.canvas} needs craft.tile_size (+ craft.char_tiles for character) in {spec_path}."
            )


def _resolve_canvas_fallback(args) -> None:
    """Default width/height from the source/reference image when omitted."""
    if getattr(args, "width", None) and getattr(args, "height", None):
        return
    for attr in ("from_image", "reference_image", "inpainting_image"):
        source = getattr(args, attr, None)
        if source:
            img = _load_pil(source)
            args.width, args.height = img.width, img.height
            return
    if hasattr(args, "width"):
        raise SystemExit(
            "Cannot resolve canvas: pass --width/--height, or --canvas tile|character with an art-spec."
        )


def _b64_image_payload(image: Any) -> dict[str, str]:
    import base64
    import io

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return {"type": "base64", "base64": base64.b64encode(buf.getvalue()).decode("ascii")}


def _raw_animate_with_skeleton(api_key: str, kwargs: dict[str, Any]) -> list[Any]:
    """Raw POST /animate-with-skeleton. Needed because pixellab SDK 1.0.5 still sends
    the legacy reference/pose guidance params and cannot send the live API's single
    `guidance_scale` (default 4.0)."""
    import base64
    import io

    import requests
    from PIL import Image

    payload: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        if key in ("reference_image", "color_image"):
            payload[key] = _b64_image_payload(value)
        elif key in ("init_images", "mask_images"):
            payload[key] = [_b64_image_payload(v) for v in value if v is not None]
        elif key == "skeleton_keypoints":
            # The live validator requires integer z_index, but /estimate-skeleton
            # itself returns fractional ones (-3.5, -0.5) — round defensively.
            payload[key] = [
                [
                    {**kp, "z_index": int(round(kp.get("z_index", 0)))}
                    for kp in (frame["keypoints"] if isinstance(frame, dict) and "keypoints" in frame else frame)
                ]
                for frame in value
            ]
        else:
            payload[key] = value
    resp = requests.post(
        f"{API_BASE}/animate-with-skeleton",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=600,
    )
    if resp.status_code != 200:
        raise SystemExit(f"PixelLab /animate-with-skeleton failed ({resp.status_code}): {resp.text[:500]}")
    data = resp.json()
    frames = []
    for img in data.get("images", []):
        b64 = img.get("base64") if isinstance(img, dict) else None
        if not b64:
            raise SystemExit(f"Unexpected /animate-with-skeleton image entry: {img!r:.200}")
        frames.append(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA"))
    if not frames:
        raise SystemExit(f"PixelLab /animate-with-skeleton returned no images: {str(data)[:500]}")
    return frames


def _client(api_key: str):
    try:
        import pixellab  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise SystemExit(
            "Missing dependency 'pixellab'. Install with `python3 -m pip install pixellab pillow` "
            "or run this script with `uv run`."
        ) from exc
    return pixellab.Client(secret=api_key)


def _get_method(client: Any, *names: str) -> tuple[Any, str]:
    for name in names:
        method = getattr(client, name, None)
        if method is not None:
            return method, name
    raise AttributeError(f"PixelLab client missing expected methods: {', '.join(names)}")


def _accepted_kwargs(method: Any, kwargs: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Filter kwargs for SDK versions with explicit signatures.

    Some PixelLab SDK versions expose **kwargs while others list concrete
    parameters. This keeps the helper forward-compatible without passing
    unknown names to stricter versions.
    """
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        return kwargs, []
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return kwargs, []
    accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
    skipped = [k for k in kwargs if k not in accepted]
    return accepted, skipped


def _extract_pil(result: Any):
    """Extract a single PIL image from a PixelLab single-image response."""
    from PIL import Image

    if isinstance(result, Image.Image):
        return result.convert("RGBA")
    image = getattr(result, "image", None)
    if image is not None:
        pil_image = getattr(image, "pil_image", None)
        if callable(pil_image):
            return pil_image().convert("RGBA")
        if isinstance(image, Image.Image):
            return image.convert("RGBA")
    pil_image = getattr(result, "pil_image", None)
    if callable(pil_image):
        return pil_image().convert("RGBA")
    raise TypeError(
        "Could not extract a PIL image from PixelLab result. "
        f"Result type: {type(result).__name__}"
    )


def _extract_pils(result: Any) -> list[Any]:
    """Extract a list of PIL frames from a multi-image (animation) response."""
    from PIL import Image

    images = getattr(result, "images", None)
    if images is None:
        return [_extract_pil(result)]
    frames = []
    for img in images:
        pil_image = getattr(img, "pil_image", None)
        if callable(pil_image):
            frames.append(pil_image().convert("RGBA"))
        elif isinstance(img, Image.Image):
            frames.append(img.convert("RGBA"))
        else:
            raise TypeError(f"Unrecognized frame type: {type(img).__name__}")
    return frames


def _write_manifest(path: str | None, data: dict[str, Any]) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _save_image(image: Any, output: str) -> None:
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


def _save_frames(frames: list[Any], output: str, write_strip: bool = True) -> dict[str, Any]:
    """Save each frame as {stem}_NN.png and a packed horizontal {stem}_strip.png."""
    from PIL import Image

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    saved = []
    for i, frame in enumerate(frames):
        p = Path(f"{stem}_{i:02d}.png")
        frame.save(p)
        saved.append(str(p))
    strip_path = None
    if write_strip and frames:
        w = max(f.width for f in frames)
        h = max(f.height for f in frames)
        strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            strip.paste(frame, (i * w, 0))
        strip_path = str(Path(f"{stem}_strip.png"))
        strip.save(strip_path)
    return {"frames": saved, "strip": strip_path, "frame_count": len(frames)}


def _add_shared_flags(p: argparse.ArgumentParser) -> None:
    """Allow --art-spec/--no-art-spec/--family after the subcommand as well.

    default=SUPPRESS keeps subcommand-level absence from clobbering values parsed
    at the top level (argparse subparser defaults override parent values).
    """
    p.add_argument("--art-spec", default=argparse.SUPPRESS,
                   help="Path to the governing art-spec.yaml (also accepted before the subcommand)")
    p.add_argument("--no-art-spec", action="store_true", default=argparse.SUPPRESS,
                   help="Explicit exploratory override: run WITHOUT an art-spec (never on production calls)")
    p.add_argument("--family", default=argparse.SUPPRESS,
                   help="Asset family; selects conditioning.golden_assets.<family> as the default style image")


def _add_style_args(p: argparse.ArgumentParser) -> None:
    """Weakly-guiding style references shared by generation/inpaint/rotate."""
    p.add_argument("--view", choices=VIEWS, help="Camera view angle")
    p.add_argument("--direction", choices=DIRECTIONS, help="Subject facing direction")
    p.add_argument("--outline", choices=OUTLINES, help="Outline style reference")
    p.add_argument("--shading", choices=SHADINGS, help="Shading style reference")
    p.add_argument("--detail", choices=DETAILS, help="Detail style reference")
    p.add_argument("--seed", type=int, help="Provenance/reproducibility only — NEVER an identity/consistency mechanism (0 = random)")
    p.add_argument(
        "--palette", nargs="*",
        help="Palette hex colors; built into a forced color_image swatch",
    )
    p.add_argument(
        "--color-image",
        help="PNG whose pixels define the forced palette (overrides --palette)",
    )
    p.add_argument("--manifest", help="Optional JSON provenance manifest")


def _resolve_color_image(args) -> Any:
    if getattr(args, "color_image", None):
        return _load_pil(args.color_image)
    return _palette_to_color_image(getattr(args, "palette", None))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate pixel-native art + animation with PixelLab")
    parser.add_argument("--api-key", "-k", default=os.getenv("PIXEL_LABS_API_KEY"), help="PixelLab API key; defaults to PIXEL_LABS_API_KEY")
    parser.add_argument("--dry-run", action="store_true", help="Print request manifest without calling PixelLab")
    parser.add_argument("--art-spec", help="Path to the governing art-spec.yaml (default: $UNITY_ART_SPEC, then probe Assets/*/Art/_ArtDirection/, Assets/GameArt/, Assets/Art/)")
    parser.add_argument("--no-art-spec", action="store_true", help="Explicit exploratory override: run a generation command WITHOUT an art-spec (production calls must not use this)")
    parser.add_argument("--family", help="Asset family; selects conditioning.golden_assets.<family> as the default bitforge --style-image")
    sub = parser.add_subparsers(dest="command", required=True)

    out_help = "Output PNG path (animation commands also write _NN.png + _strip.png)"

    balance = sub.add_parser("balance", help="Check PixelLab account balance/credits")
    balance.add_argument("--manifest", help="Optional JSON balance report")

    # --- PixFlux: text -> pixel image ---
    pixflux = sub.add_parser("pixflux", help="Text-to-pixel anchor generation (game golden / approved rerolls only)")
    pixflux.add_argument("--description", "-d", required=True)
    pixflux.add_argument("--width", type=_positive_int, help="Pixel canvas width (or use --canvas with an art-spec)")
    pixflux.add_argument("--height", type=_positive_int, help="Pixel canvas height (or use --canvas with an art-spec)")
    pixflux.add_argument("--canvas", choices=["tile", "character"], help="Derive canvas from art-spec craft.tile_size/char_tiles")
    pixflux.add_argument("--output", "-o", required=True, help=out_help)
    pixflux.add_argument("--negative-description", default="")
    pixflux.add_argument("--no-background", action="store_true", help="Transparent background")
    pixflux.add_argument("--text-guidance-scale", type=float, default=8.0, help="1.0-20.0")
    pixflux.add_argument("--isometric", action="store_true")
    pixflux.add_argument("--coverage-percentage", type=float,
                         help="Percent of canvas the subject should cover (0-100); helps prevent duplicated/stacked subjects on tall canvases")
    pixflux.add_argument("--init-image", help="Initial image to start from")
    pixflux.add_argument("--init-image-strength", type=int, default=300, help="0-1000")
    _add_style_args(pixflux)
    _add_shared_flags(pixflux)

    # --- BitForge: style/image-conditioned pixel image ---
    bitforge = sub.add_parser("bitforge", help="Style/image-conditioned pixel generation")
    bitforge.add_argument("--description", "-d", required=True)
    bitforge.add_argument("--width", type=_positive_int, help="Pixel canvas width (or use --canvas with an art-spec)")
    bitforge.add_argument("--height", type=_positive_int, help="Pixel canvas height (or use --canvas with an art-spec)")
    bitforge.add_argument("--canvas", choices=["tile", "character"], help="Derive canvas from art-spec craft.tile_size/char_tiles")
    bitforge.add_argument("--output", "-o", required=True, help=out_help)
    bitforge.add_argument("--negative-description", default="")
    bitforge.add_argument("--style-image", help="Anchor/style reference PNG (defaults to conditioning.golden_assets.<--family|game> from the art-spec)")
    bitforge.add_argument(
        "--style-strength", type=float, default=80.0,
        help="Style transfer strength, scale 0-100 (SDK default 0). Same-asset variants: 60-100. "
             "Cross-subject derivation from a golden anchor (new character/prop): 50-70 — higher transfers "
             "the anchor's IDENTITY, not just its style.",
    )
    bitforge.add_argument("--text-guidance-scale", type=float, default=8.0, help="1.0-20.0 (live API default 8.0)")
    bitforge.add_argument("--coverage-percentage", type=float,
                         help="Percent of canvas the subject should cover (0-100); helps prevent duplicated/stacked subjects on tall canvases")
    bitforge.add_argument("--extra-guidance-scale", type=float, default=None, help="DEPRECATED in the live API — leave unset; tuning it is likely a no-op")
    bitforge.add_argument("--init-image", help="Initial image to start from (THE working golden-conditioning channel; autofilled from conditioning.golden_assets)")
    bitforge.add_argument("--init-image-strength", type=int, default=None,
                          help="1-999. Cross-subject derivation ~75-150 (higher bleeds anchor identity); same-asset variants 250-400. Defaults: 110 when the golden was autofilled, else API default 300")
    bitforge.add_argument("--inpainting-image", help="Reference image which is inpainted")
    bitforge.add_argument("--mask-image", help="Inpaint mask (white = inpaint)")
    bitforge.add_argument("--no-background", action="store_true", help="Transparent background")
    bitforge.add_argument("--isometric", action="store_true")
    _add_style_args(bitforge)
    _add_shared_flags(bitforge)

    # --- Rotate: change direction/view of an existing sprite ---
    rotate = sub.add_parser("rotate", help="Rotate a sprite to a new direction/view")
    rotate.add_argument("--from-image", required=True, help="Source sprite PNG")
    rotate.add_argument("--width", type=_positive_int, help="Defaults to the --from-image canvas")
    rotate.add_argument("--height", type=_positive_int, help="Defaults to the --from-image canvas")
    rotate.add_argument("--output", "-o", required=True, help=out_help)
    rotate.add_argument("--from-view", choices=VIEWS)
    rotate.add_argument("--to-view", choices=VIEWS)
    rotate.add_argument("--from-direction", choices=DIRECTIONS)
    rotate.add_argument("--to-direction", choices=DIRECTIONS)
    rotate.add_argument("--image-guidance-scale", type=float, default=3.0, help="1.0-20.0")
    rotate.add_argument("--isometric", action="store_true")
    rotate.add_argument("--init-image", help="Initial image to start from")
    rotate.add_argument("--init-image-strength", type=int, default=300, help="0-1000")
    rotate.add_argument("--seed", type=int)
    rotate.add_argument("--palette", nargs="*")
    rotate.add_argument("--color-image")
    rotate.add_argument("--manifest")
    _add_shared_flags(rotate)

    # --- estimate-skeleton: detect rest-pose keypoints ---
    est = sub.add_parser("estimate-skeleton", help="Detect rest-pose keypoints from a base character")
    est.add_argument("--image", required=True, help="Base character PNG (transparent background)")
    est.add_argument("--output", "-o", required=True, help="Output keypoints JSON")
    est.add_argument("--manifest")
    _add_shared_flags(est)

    # --- animate-skeleton: pose-driven, structurally consistent ---
    askel = sub.add_parser("animate-skeleton", help="Pose-driven animation (structurally consistent; PREFERRED)")
    askel.add_argument("--skeleton-json", required=True, help="JSON list of frames; each frame = {\"keypoints\": [...]}")
    askel.add_argument("--width", type=_positive_int, help="Defaults to the --reference-image canvas")
    askel.add_argument("--height", type=_positive_int, help="Defaults to the --reference-image canvas")
    askel.add_argument("--view", choices=VIEWS, required=True)
    askel.add_argument("--direction", choices=DIRECTIONS, required=True)
    askel.add_argument("--output", "-o", required=True, help=out_help)
    askel.add_argument("--reference-image", help="Base character PNG for identity/style")
    askel.add_argument("--guidance-scale", type=float, default=None,
                       help="Live API guidance (1.0-20.0, server default 4.0). Setting it uses a raw HTTP call — SDK 1.0.5 cannot send it.")
    askel.add_argument("--reference-guidance-scale", type=float, default=None,
                       help="LEGACY SDK param — replaced by --guidance-scale in the live API; sending it via SDK 1.0.5 is likely a no-op")
    askel.add_argument("--pose-guidance-scale", type=float, default=None,
                       help="LEGACY SDK param — replaced by --guidance-scale in the live API; sending it via SDK 1.0.5 is likely a no-op")
    askel.add_argument("--isometric", action="store_true")
    askel.add_argument("--init-image", help="Single init image applied to all frames")
    askel.add_argument("--init-images", nargs="*",
                       help="Per-frame init images (freeze-frame repair: pass approved frames + the repaired slot; overrides --init-image)")
    askel.add_argument("--mask-images", nargs="*", help="Per-frame inpaint masks (white = regenerate) for single-frame repair")
    askel.add_argument("--init-image-strength", type=int, default=300, help="0-1000")
    askel.add_argument("--seed", type=int, help="Provenance only — never an identity mechanism")
    askel.add_argument("--palette", nargs="*")
    askel.add_argument("--color-image")
    askel.add_argument("--manifest")
    _add_shared_flags(askel)

    # --- animate-text: text/action conditioned on a reference (drifts more) ---
    atext = sub.add_parser("animate-text", help="Text/action animation conditioned on a reference (drifts more than skeleton)")
    atext.add_argument("--description", "-d", required=True, help="Character description")
    atext.add_argument("--action", required=True, help="Action description, e.g. 'walk', 'swing sword'")
    atext.add_argument("--reference-image", required=True, help="Base character PNG for identity/style")
    atext.add_argument("--width", type=_positive_int, help="Defaults to the --reference-image canvas")
    atext.add_argument("--height", type=_positive_int, help="Defaults to the --reference-image canvas")
    atext.add_argument("--output", "-o", required=True, help=out_help)
    atext.add_argument("--view", choices=VIEWS, default="side")
    atext.add_argument("--direction", choices=DIRECTIONS, default="east")
    atext.add_argument("--n-frames", type=int, default=4, help="1-20")
    atext.add_argument("--negative-description")
    atext.add_argument("--text-guidance-scale", type=float, default=7.5, help="1.0-20.0")
    atext.add_argument("--image-guidance-scale", type=float, default=1.4, help="1.0-20.0 (live API default 1.4)")
    atext.add_argument("--seed", type=int, help="Provenance only — never an identity mechanism")
    atext.add_argument("--palette", nargs="*")
    atext.add_argument("--color-image")
    atext.add_argument("--manifest")
    _add_shared_flags(atext)

    # --- inpaint: local edit inside a mask ---
    inp = sub.add_parser("inpaint", help="Local edit inside a mask (fix detail without rerolling)")
    inp.add_argument("--description", "-d", required=True)
    inp.add_argument("--inpainting-image", required=True, help="Image to edit")
    inp.add_argument("--mask-image", required=True, help="Mask PNG (white = inpaint)")
    inp.add_argument("--width", type=_positive_int, help="Defaults to the --inpainting-image canvas")
    inp.add_argument("--height", type=_positive_int, help="Defaults to the --inpainting-image canvas")
    inp.add_argument("--output", "-o", required=True, help=out_help)
    inp.add_argument("--negative-description", default="")
    inp.add_argument("--text-guidance-scale", type=float, default=3.0, help="1.0-20.0")
    inp.add_argument("--extra-guidance-scale", type=float, default=None, help="DEPRECATED in the live API — leave unset; tuning it is likely a no-op")
    inp.add_argument("--no-background", action="store_true")
    inp.add_argument("--init-image")
    inp.add_argument("--init-image-strength", type=int, default=300, help="0-1000")
    _add_style_args(inp)
    _add_shared_flags(inp)

    return parser


def _animation_commands() -> set[str]:
    return {"animate-skeleton", "animate-text"}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.api_key and not args.dry_run:
        parser.error("PixelLab key missing. Pass --api-key or export PIXEL_LABS_API_KEY.")

    # ---- Art-spec gate (production paths fail-unless-overridden) ----
    spec, spec_path = _resolve_art_spec(args)
    if args.command in PRODUCTION_COMMANDS:
        if spec is None and not args.no_art_spec:
            raise SystemExit(
                "No art-spec resolved. Production PixelLab calls must read the governing art-spec.yaml "
                "(--art-spec PATH, $UNITY_ART_SPEC, or a probed Assets/*/Art/_ArtDirection/art-spec.yaml). "
                "For exploratory/concept work only, pass --no-art-spec explicitly."
            )
        if spec is not None:
            _apply_spec_defaults(args, spec, spec_path or "<art-spec>")
        _resolve_canvas_fallback(args)
        # Palette hard rule: any production PixelLab call without a palette lock is invalid.
        if not args.no_art_spec and not getattr(args, "color_image", None) and not getattr(args, "palette", None):
            raise SystemExit(
                "Palette lock missing: production PixelLab calls require a color_image "
                "(art-spec conditioning.master_palette_png, --color-image, or --palette). "
                "Derived frames/rotations should use the anchor's extracted sub-palette. "
                "Exploratory-only override: --no-art-spec."
            )

    request: dict[str, Any] = {
        "tool": "unity-pixel-art/scripts/generate_pixel_art.py",
        "provider": "pixellab",
        "command": args.command,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "art_spec": spec_path,
    }
    if spec is not None:
        request["style_id"] = spec.get("style_id") if isinstance(spec, dict) else None
        request["pixels_per_unit"] = _spec_get(spec, "craft", "pixels_per_unit")
        # Prompt-level tokens (NO API params) — recorded for provenance/vision-QA:
        request["light_direction"] = _spec_get(spec, "craft", "light_direction")
        request["dithering_policy"] = _spec_get(spec, "craft", "dithering_policy")
    for key in ("description", "action", "width", "height", "output", "view", "direction",
                "no_background", "seed", "palette", "color_image", "style_strength",
                "style_image", "family", "guidance_scale", "outline", "shading", "detail",
                "n_frames", "from_direction", "to_direction"):
        if hasattr(args, key):
            request[key] = getattr(args, key)

    if args.dry_run:
        print(json.dumps(request, indent=2, sort_keys=True, default=str))
        _write_manifest(getattr(args, "manifest", None), {**request, "dry_run": True})
        return 0

    client = _client(args.api_key)
    skipped: list[str] = []
    multi = args.command in _animation_commands()

    if args.command == "balance":
        method, method_name = _get_method(client, "get_balance", "balance")
        result = method()
        balance_data = {
            **request,
            "sdk_method": method_name,
            "result_repr": repr(result),
        }
        for attr in ("usd", "credits", "subscription"):
            if hasattr(result, attr):
                value = getattr(result, attr)
                try:
                    json.dumps(value)
                    balance_data[attr] = value
                except TypeError:
                    balance_data[attr] = repr(value)
        _write_manifest(getattr(args, "manifest", None), balance_data)
        print(json.dumps(balance_data, indent=2, sort_keys=True))
        return 0

    if args.command == "estimate-skeleton":
        method, method_name = _get_method(client, "estimate_skeleton")
        result = method(image=_load_pil(args.image))
        keypoints = getattr(result, "keypoints", result)
        # Wrap as a single skeleton frame so it can seed animate-skeleton directly.
        out_payload = {
            "rest_keypoints": keypoints,
            "skeleton_keypoints_template": [{"keypoints": keypoints}],
        }
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(out_payload, indent=2, default=lambda o: getattr(o, "__dict__", str(o))) + "\n", encoding="utf-8")
        _write_manifest(getattr(args, "manifest", None), {**request, "sdk_method": method_name})
        print(json.dumps({"ok": True, "output": args.output, "keypoint_count": len(keypoints)}, indent=2))
        return 0

    image_size = {"width": args.width, "height": args.height}

    if args.command == "pixflux":
        method, method_name = _get_method(client, "generate_image_pixflux", "create_image_pixflux")
        kwargs = {
            "description": args.description,
            "image_size": image_size,
            "negative_description": args.negative_description,
            "text_guidance_scale": args.text_guidance_scale,
            "no_background": bool(args.no_background),
            "coverage_percentage": getattr(args, "coverage_percentage", None),
            "isometric": bool(args.isometric),
            "view": args.view,
            "direction": args.direction,
            "outline": args.outline,
            "shading": args.shading,
            "detail": args.detail,
            "init_image": _load_pil(args.init_image),
            "init_image_strength": args.init_image_strength,
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
    elif args.command == "bitforge":
        method, method_name = _get_method(client, "generate_image_bitforge", "create_image_bitforge")
        kwargs = {
            "description": args.description,
            "image_size": image_size,
            "negative_description": args.negative_description,
            "text_guidance_scale": args.text_guidance_scale,
            "extra_guidance_scale": args.extra_guidance_scale,
            "style_strength": args.style_strength,
            "no_background": bool(args.no_background),
            "coverage_percentage": getattr(args, "coverage_percentage", None),
            "isometric": bool(args.isometric),
            "view": args.view,
            "direction": args.direction,
            "outline": args.outline,
            "shading": args.shading,
            "detail": args.detail,
            "style_image": _adapt_style_image(args.style_image, args.width, args.height),
            "init_image": _adapt_style_image(args.init_image, args.width, args.height),
            "init_image_strength": args.init_image_strength
            if args.init_image_strength is not None
            else (110 if getattr(args, "golden_autofilled", False) else 300),
            "inpainting_image": _load_pil(args.inpainting_image),
            "mask_image": _load_pil(args.mask_image),
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
    elif args.command == "rotate":
        method, method_name = _get_method(client, "rotate")
        kwargs = {
            "image_size": image_size,
            "from_image": _load_pil(args.from_image),
            "from_view": args.from_view,
            "to_view": args.to_view,
            "from_direction": args.from_direction,
            "to_direction": args.to_direction,
            "image_guidance_scale": args.image_guidance_scale,
            "isometric": bool(args.isometric),
            "init_image": _load_pil(args.init_image),
            "init_image_strength": args.init_image_strength,
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
    elif args.command == "inpaint":
        method, method_name = _get_method(client, "inpaint")
        kwargs = {
            "description": args.description,
            "image_size": image_size,
            "inpainting_image": _load_pil(args.inpainting_image),
            "mask_image": _load_pil(args.mask_image),
            "negative_description": args.negative_description,
            "text_guidance_scale": args.text_guidance_scale,
            "extra_guidance_scale": args.extra_guidance_scale,
            "no_background": bool(args.no_background),
            "view": args.view,
            "direction": args.direction,
            "outline": args.outline,
            "shading": args.shading,
            "detail": args.detail,
            "init_image": _load_pil(args.init_image),
            "init_image_strength": args.init_image_strength,
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
    elif args.command == "animate-skeleton":
        frames = json.loads(Path(args.skeleton_json).read_text(encoding="utf-8"))
        if isinstance(frames, dict):  # accept estimate-skeleton output directly
            frames = frames.get("skeleton_keypoints_template") or frames.get("skeleton_keypoints") or [frames]
        # Live-API frame format (verified 2026-07-01): each skeleton_keypoints entry
        # is a BARE LIST of keypoint dicts. Normalize the friendlier authored formats
        # ({"keypoints": [...]}, {"rest_keypoints": [...]}) so pose JSONs written by
        # hand or copied from estimate-skeleton output both work.
        frames = [
            f.get("keypoints") or f.get("rest_keypoints") if isinstance(f, dict) else f
            for f in frames
        ]
        bad = [i for i, f in enumerate(frames) if not isinstance(f, list) or not f]
        if bad:
            raise SystemExit(f"skeleton frames {bad} have no keypoints (expected a list, or a dict with 'keypoints').")
        ref = _load_pil(args.reference_image)
        if args.init_images:
            init_images = [_load_pil(p) for p in args.init_images]
        elif args.init_image:
            init_images = [_load_pil(args.init_image)] * len(frames)
        else:
            # Live API rejects null here ("Input should be a valid list") — the
            # SDK forwards None verbatim, so always send a list (empty = none).
            init_images = []
        mask_images = [_load_pil(p) for p in args.mask_images] if args.mask_images else []
        kwargs = {
            "image_size": image_size,
            "skeleton_keypoints": frames,
            "view": args.view,
            "direction": args.direction,
            "reference_guidance_scale": args.reference_guidance_scale,
            "pose_guidance_scale": args.pose_guidance_scale,
            "isometric": bool(args.isometric),
            "reference_image": ref,
            "init_images": init_images,
            "mask_images": mask_images,
            "init_image_strength": args.init_image_strength,
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
        # ALWAYS go raw for animate-with-skeleton: SDK 1.0.5 is incompatible with
        # the live endpoint — it serializes absent inpainting_images/mask_images as
        # null (the API 422s: "Input should be a valid list") and cannot send the
        # live single `guidance_scale` param (verified 2026-07-01).
        if args.guidance_scale is not None:
            kwargs["guidance_scale"] = args.guidance_scale
        kwargs.pop("reference_guidance_scale", None)
        kwargs.pop("pose_guidance_scale", None)
        # The live endpoint requires a SQUARE canvas from {16,32,64,128,256}
        # ("Canvas must be size 256x256, 128x128, 64x64, 32x32 or 16x16"), so a
        # 32x64 character is animated on a 64x64 canvas: pad the reference/init
        # images (centered horizontally, bottom-aligned to keep the baseline),
        # remap the normalized keypoints, and crop every returned frame back.
        w, h = args.width, args.height
        crop_box = None
        if w != h or w not in (16, 32, 64, 128, 256):
            square = next((s for s in (16, 32, 64, 128, 256) if s >= max(w, h)), 256)
            xoff, yoff = (square - w) // 2, square - h  # bottom-aligned
            from PIL import Image as _Image

            def _pad(img):
                if img is None:
                    return None
                cv = _Image.new("RGBA", (square, square), (0, 0, 0, 0))
                cv.paste(img, (xoff, yoff))
                return cv

            kwargs["reference_image"] = _pad(kwargs.get("reference_image"))
            for lk in ("init_images", "mask_images"):
                if kwargs.get(lk):
                    kwargs[lk] = [_pad(i) for i in kwargs[lk]]
            kwargs["skeleton_keypoints"] = [
                [{**kp, "x": (kp["x"] * w + xoff) / square, "y": (kp["y"] * h + yoff) / square} for kp in fr]
                for fr in kwargs["skeleton_keypoints"]
            ]
            kwargs["image_size"] = {"width": square, "height": square}
            crop_box = (xoff, yoff, xoff + w, yoff + h)
            print(
                f"canvas {w}x{h} is not a legal skeleton-animation size; animating at "
                f"{square}x{square} (baseline-preserving pad) and cropping frames back.",
                file=sys.stderr,
            )
        clean_kwargs = {k: v for k, v in kwargs.items() if v is not None and v != []}
        all_poses = clean_kwargs["skeleton_keypoints"]
        try:
            raw_frames = _raw_animate_with_skeleton(args.api_key, clean_kwargs)
        except SystemExit as err:
            # Frame count per call is canvas-dependent (e.g. 64x64 -> 3 poses +
            # the reference slot): "Expected N pose images, got M". Re-batch.
            m = re.search(r"Expected (\d+) pose images", str(err))
            if not m:
                raise
            batch = int(m.group(1))
            print(f"canvas requires exactly {batch} poses per call; batching {len(all_poses)} frames.", file=sys.stderr)
            raw_frames = []
            for i in range(0, len(all_poses), batch):
                chunk = dict(clean_kwargs)
                poses = all_poses[i : i + batch]
                real = len(poses)
                # The API wants EXACTLY `batch` poses — pad short tails by
                # repeating the last pose, then drop the padded frames.
                poses = poses + [poses[-1]] * (batch - real)
                chunk["skeleton_keypoints"] = poses
                for lk in ("init_images", "mask_images"):
                    if lk in chunk:
                        tail = chunk[lk][i : i + batch]
                        chunk[lk] = tail + [tail[-1]] * (batch - len(tail))
                raw_frames.extend(_raw_animate_with_skeleton(args.api_key, chunk)[:real])
        if crop_box:
            raw_frames = [f.crop(crop_box) for f in raw_frames]
        save_info = _save_frames(raw_frames, args.output)
        manifest = {**request, "sdk_method": "raw:POST /animate-with-skeleton",
                    "sdk_skipped_kwargs": [], **save_info}
        print(json.dumps({"ok": True, **save_info, "via": "raw HTTP"}, indent=2))
        _write_manifest(getattr(args, "manifest", None), manifest)
        return 0
    elif args.command == "animate-text":
        method, method_name = _get_method(client, "animate_with_text")
        kwargs = {
            "image_size": image_size,
            "description": args.description,
            "action": args.action,
            "reference_image": _load_pil(args.reference_image),
            "view": args.view,
            "direction": args.direction,
            "negative_description": args.negative_description,
            "text_guidance_scale": args.text_guidance_scale,
            "image_guidance_scale": args.image_guidance_scale,
            "n_frames": args.n_frames,
            "color_image": _resolve_color_image(args),
            "seed": args.seed,
        }
    else:  # pragma: no cover
        parser.error(f"Unsupported command: {args.command}")

    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    call_kwargs, skipped = _accepted_kwargs(method, kwargs)
    if "color_image" in skipped:
        raise SystemExit(
            f"FATAL: the installed pixellab SDK does not accept `color_image` on {method_name} — "
            "the palette lock would be silently dropped and the palette NOT enforced. "
            "Upgrade the pixellab package (or call the raw HTTP endpoint) before generating."
        )
    result = method(**call_kwargs)

    manifest = {**request, "sdk_method": method_name, "sdk_skipped_kwargs": skipped,
                "result_type": type(result).__name__}
    if multi:
        save_info = _save_frames(_extract_pils(result), args.output)
        manifest.update(save_info)
        print(json.dumps({"ok": True, **save_info, "skipped_kwargs": skipped}, indent=2))
    else:
        image = _extract_pil(result)
        _save_image(image, args.output)
        manifest.update({"image_mode": image.mode, "image_size_actual": list(image.size)})
        print(json.dumps({"ok": True, "output": args.output, "skipped_kwargs": skipped}, indent=2))
    _write_manifest(getattr(args, "manifest", None), manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
