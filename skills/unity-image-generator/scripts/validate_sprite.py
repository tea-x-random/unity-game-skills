#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=10.0.0",
# ]
# ///
"""Validate a generated Unity sprite PNG before import.

This is a production gate, not a subjective art critique. It catches the
common failures that make AI-generated sprites look cheap once assembled in
Unity: missing alpha, white/chroma edge halos, loose trimming, inconsistent
padding, oversized textures, and palette drift.

Examples:
  python3 validate_sprite.py Assets/Art/Sprites/tree.png --require-alpha --json-report tree.qa.json
  python3 validate_sprite.py coin.png --require-alpha --min-padding 4 --max-padding-variance 12
  python3 validate_sprite.py icon.png --palette '#E54B4B,#FFD166,#2A9D8F' --max-palette-distance 85
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from PIL import Image

MATTE_COLORS = {
    "white": (255, 255, 255),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
}


@dataclass
class Check:
    id: str
    status: str  # pass | fail | warn
    message: str
    value: object | None = None
    threshold: object | None = None


def dist_rgb(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((int(a[i]) - int(b[i])) ** 2 for i in range(3)))


def parse_hex_color(text: str) -> tuple[int, int, int]:
    text = text.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise argparse.ArgumentTypeError(f"Invalid hex color: {text!r}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def parse_palette(text: str | None) -> list[tuple[int, int, int]]:
    if not text:
        return []
    return [parse_hex_color(part) for part in text.split(",") if part.strip()]


def alpha_bbox(alpha, width: int, height: int, threshold: int) -> tuple[int, int, int, int] | None:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            if alpha[x, y] > threshold:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def is_edge_pixel(alpha, x: int, y: int, width: int, height: int, edge_alpha: int) -> bool:
    if alpha[x, y] <= edge_alpha:
        return False
    for ny in range(max(0, y - 1), min(height, y + 2)):
        for nx in range(max(0, x - 1), min(width, x + 2)):
            if nx == x and ny == y:
                continue
            if alpha[nx, ny] <= edge_alpha:
                return True
    return False


def sample_opaque_pixels(rgba, alpha, width: int, height: int, threshold: int, max_samples: int) -> list[tuple[int, int, int]]:
    points: list[tuple[int, int, int]] = []
    total_opaque = sum(1 for y in range(height) for x in range(width) if alpha[x, y] > threshold)
    if total_opaque == 0:
        return points
    stride = max(1, int(math.sqrt(total_opaque / max_samples)))
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            if alpha[x, y] > threshold:
                r, g, b, _ = rgba[x, y]
                points.append((r, g, b))
                if len(points) >= max_samples:
                    return points
    return points


def validate(args: argparse.Namespace) -> dict:
    path = Path(args.image)
    checks: list[Check] = []
    with Image.open(path) as img:
        original_mode = img.mode
        rgba_img = img.convert("RGBA")
    width, height = rgba_img.size
    rgba = rgba_img.load()
    alpha = rgba_img.getchannel("A").load()
    total = width * height

    if args.max_width or args.max_height:
        max_w = args.max_width or width
        max_h = args.max_height or height
        ok = width <= max_w and height <= max_h
        checks.append(Check(
            "resolution.max",
            "pass" if ok else "fail",
            f"Texture size is {width}x{height}; max allowed is {max_w}x{max_h}.",
            {"width": width, "height": height},
            {"max_width": max_w, "max_height": max_h},
        ))

    if args.power_of_two:
        ok = width & (width - 1) == 0 and height & (height - 1) == 0
        checks.append(Check(
            "resolution.power_of_two",
            "pass" if ok else "fail",
            "Texture dimensions are power-of-two." if ok else "Texture dimensions are not power-of-two.",
            {"width": width, "height": height},
        ))

    has_alpha_channel = original_mode in ("RGBA", "LA") or (original_mode == "P" and "transparency" in rgba_img.info)
    transparent_pixels = sum(1 for y in range(height) for x in range(width) if alpha[x, y] <= args.alpha_threshold)
    opaque_pixels = total - transparent_pixels
    coverage = opaque_pixels / total if total else 0

    if args.require_alpha:
        ok = has_alpha_channel and transparent_pixels > 0
        checks.append(Check(
            "alpha.present",
            "pass" if ok else "fail",
            "Sprite contains usable transparency." if ok else "Sprite requires transparency but appears fully opaque or lacks alpha.",
            {"mode": original_mode, "transparent_pixels": transparent_pixels},
        ))

        corners = [alpha[0, 0], alpha[width - 1, 0], alpha[0, height - 1], alpha[width - 1, height - 1]]
        ok = all(a <= args.max_corner_alpha for a in corners)
        checks.append(Check(
            "alpha.corners",
            "pass" if ok else "fail",
            "All image corners are transparent." if ok else "One or more corners are not transparent; likely fake/painted background.",
            {"corner_alpha": corners},
            {"max_corner_alpha": args.max_corner_alpha},
        ))

    checks.append(Check(
        "silhouette.coverage",
        "pass" if args.min_coverage <= coverage <= args.max_coverage else "fail",
        f"Opaque coverage is {coverage:.3f}; expected {args.min_coverage:.3f}..{args.max_coverage:.3f}.",
        coverage,
        {"min": args.min_coverage, "max": args.max_coverage},
    ))

    bbox = alpha_bbox(alpha, width, height, args.alpha_threshold)
    padding = None
    if bbox:
        left, top, right, bottom = bbox
        padding = {
            "left": left,
            "top": top,
            "right": width - right,
            "bottom": height - bottom,
        }
        bbox_area = (right - left) * (bottom - top)
        bbox_coverage = bbox_area / total
        checks.append(Check("alpha.bbox", "pass", "Computed opaque alpha bounding box.", {"bbox": bbox, "padding": padding, "bbox_coverage": bbox_coverage}))

        min_pad = min(padding.values())
        max_pad = max(padding.values())
        variance = max_pad - min_pad
        if args.min_padding is not None:
            ok = min_pad >= args.min_padding
            checks.append(Check(
                "padding.minimum",
                "pass" if ok else "fail",
                f"Minimum transparent padding is {min_pad}px; expected at least {args.min_padding}px.",
                padding,
                {"min_padding": args.min_padding},
            ))
        ok = variance <= args.max_padding_variance
        checks.append(Check(
            "padding.variance",
            "pass" if ok else "fail",
            f"Padding variance is {variance}px; max allowed is {args.max_padding_variance}px.",
            padding,
            {"max_padding_variance": args.max_padding_variance},
        ))

        loose_x = (padding["left"] + padding["right"]) / width
        loose_y = (padding["top"] + padding["bottom"]) / height
        loose = max(loose_x, loose_y)
        ok = loose <= args.max_loose_padding_ratio
        checks.append(Check(
            "padding.loose_bbox",
            "pass" if ok else "fail",
            f"Transparent padding ratio is {loose:.3f}; max allowed is {args.max_loose_padding_ratio:.3f}.",
            {"x_ratio": loose_x, "y_ratio": loose_y, "padding": padding},
            {"max_loose_padding_ratio": args.max_loose_padding_ratio},
        ))
    else:
        checks.append(Check("alpha.bbox", "fail", "No opaque silhouette found."))

    # Edge halo detection: matte-colored RGB values on the silhouette edge almost
    # always mean the PNG was flattened or chroma-keyed poorly before Unity import.
    edge_count = 0
    halo_count = 0
    halo_by_color = {name: 0 for name in MATTE_COLORS}
    for y in range(height):
        for x in range(width):
            if not is_edge_pixel(alpha, x, y, width, height, args.edge_alpha_threshold):
                continue
            edge_count += 1
            r, g, b, _ = rgba[x, y]
            for name, color in MATTE_COLORS.items():
                if dist_rgb((r, g, b), color) <= args.halo_distance:
                    halo_count += 1
                    halo_by_color[name] += 1
                    break
    halo_ratio = halo_count / edge_count if edge_count else 0
    ok = halo_count <= args.max_halo_pixels and halo_ratio <= args.max_halo_ratio
    checks.append(Check(
        "alpha.edge_halo",
        "pass" if ok else "fail",
        f"Detected {halo_count} matte-colored edge pixels ({halo_ratio:.3%} of edge).",
        {"edge_pixels": edge_count, "halo_pixels": halo_count, "halo_ratio": halo_ratio, "by_color": halo_by_color},
        {"max_halo_pixels": args.max_halo_pixels, "max_halo_ratio": args.max_halo_ratio, "halo_distance": args.halo_distance},
    ))

    if args.palette:
        palette = parse_palette(args.palette)
        samples = sample_opaque_pixels(rgba, alpha, width, height, args.alpha_threshold, args.palette_samples)
        if samples and palette:
            distances = [min(dist_rgb(sample, p) for p in palette) for sample in samples]
            avg_distance = sum(distances) / len(distances)
            p95 = sorted(distances)[int(0.95 * (len(distances) - 1))]
            ok = avg_distance <= args.max_palette_distance
            checks.append(Check(
                "palette.distance",
                "pass" if ok else "fail",
                f"Average palette distance is {avg_distance:.1f}; max allowed is {args.max_palette_distance:.1f}.",
                {"avg": avg_distance, "p95": p95, "samples": len(samples)},
                {"max_avg": args.max_palette_distance, "palette": args.palette},
            ))

    fail_count = sum(1 for c in checks if c.status == "fail")
    warn_count = sum(1 for c in checks if c.status == "warn")
    report = {
        "schema": "unity-game-skills.sprite_qa.v1",
        "image": str(path),
        "dimensions": {"width": width, "height": height},
        "mode": original_mode,
        "coverage": coverage,
        "padding": padding,
        "result": "pass" if fail_count == 0 else "fail",
        "summary": {"checks": len(checks), "failures": fail_count, "warnings": warn_count},
        "checks": [asdict(c) for c in checks],
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate a generated Unity sprite PNG before import.")
    p.add_argument("image", help="PNG to validate")
    p.add_argument("--json-report", help="Write machine-readable QA report to this path")
    p.add_argument("--require-alpha", action="store_true", help="Fail if image lacks real transparent background")
    p.add_argument("--alpha-threshold", type=int, default=8, help="Alpha <= this is treated as transparent (default: 8)")
    p.add_argument("--max-corner-alpha", type=int, default=8, help="Max allowed alpha in four corners when --require-alpha is set")
    p.add_argument("--min-coverage", type=float, default=0.05, help="Min opaque coverage of whole image (default: 0.05)")
    p.add_argument("--max-coverage", type=float, default=0.90, help="Max opaque coverage of whole image (default: 0.90)")
    p.add_argument("--min-padding", type=int, default=None, help="Optional min transparent padding around silhouette, in pixels")
    p.add_argument("--max-padding-variance", type=int, default=24, help="Max difference between largest/smallest padding edge (default: 24)")
    p.add_argument("--max-loose-padding-ratio", type=float, default=0.70, help="Fail very loose alpha boxes (default: 0.70)")
    p.add_argument("--edge-alpha-threshold", type=int, default=16, help="Neighbor alpha threshold for edge detection")
    p.add_argument("--halo-distance", type=float, default=38, help="RGB distance to white/green/blue/magenta/cyan matte that counts as halo")
    p.add_argument("--max-halo-pixels", type=int, default=20, help="Max allowed matte-colored edge pixels (default: 20)")
    p.add_argument("--max-halo-ratio", type=float, default=0.01, help="Max halo pixels as fraction of edge pixels (default: 0.01)")
    p.add_argument("--max-width", type=int, help="Max texture width")
    p.add_argument("--max-height", type=int, help="Max texture height")
    p.add_argument("--power-of-two", action="store_true", help="Require power-of-two dimensions")
    p.add_argument("--palette", help="Comma-separated project palette hexes, e.g. '#E54B4B,#FFD166,#2A9D8F'")
    p.add_argument("--max-palette-distance", type=float, default=95, help="Max average RGB distance from palette (default: 95)")
    p.add_argument("--palette-samples", type=int, default=5000, help="Max opaque pixels sampled for palette check")
    return p


def main() -> int:
    args = build_parser().parse_args()
    report = validate(args)
    text = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
