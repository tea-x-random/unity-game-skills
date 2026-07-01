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
padding, oversized textures, palette drift, over-rendered flat/cel targets,
and non-square/non-seamless ground tiles.

Examples:
  python3 validate_sprite.py Assets/<Game>/Art/Source/SourceImages/tree.png --require-alpha --json-report tree.qa.json
  python3 validate_sprite.py coin.png --require-alpha --min-padding 4 --max-padding-variance 12 --no-art-spec
  python3 validate_sprite.py icon.png --art-spec Assets/MyGame/Art/_ArtDirection/art-spec.yaml
  python3 validate_sprite.py sprite.png --palette-mode exact --max-distinct-colors 16   # pixel-art-strict
  python3 validate_sprite.py tile_grass.png --tile --square --power-of-two --expected-finish flat

Production calls resolve the governing art-spec.yaml (--art-spec, $UNITY_ART_SPEC,
or canonical Assets paths) and default --palette / --expected-finish from it;
spec-less exploratory checks must pass --no-art-spec explicitly.
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

import art_spec as artspec

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


def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def quantize_distinct_colors(rgba, alpha, width, height, threshold, bits=4):
    """Count distinct quantized colors among opaque pixels (flatness proxy).

    A flat/cel asset uses few distinct tones; a glossy/gradient/painterly asset
    uses many. Returned as a ratio of distinct buckets to a fixed cap so it is
    comparable across image sizes.
    """
    shift = 8 - bits
    seen = set()
    sampled = 0
    stride = max(1, int(math.sqrt(max(1, (width * height)) / 20000)))
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            if alpha[x, y] > threshold:
                r, g, b, _ = rgba[x, y]
                seen.add(((r >> shift), (g >> shift), (b >> shift)))
                sampled += 1
    return len(seen), sampled


def mean_local_gradient(rgba, alpha, width, height, threshold):
    """Average per-channel neighbor delta on the interior of the silhouette.

    Low for flat fills, high for soft gradients / glossy rendering. Normalized
    to 0..1 (delta/255).
    """
    total = 0.0
    count = 0
    stride = max(1, int(math.sqrt(max(1, (width * height)) / 20000)))
    for y in range(0, height - 1, stride):
        for x in range(0, width - 1, stride):
            if alpha[x, y] <= threshold or alpha[x + 1, y] <= threshold or alpha[x, y + 1] <= threshold:
                continue
            r, g, b, _ = rgba[x, y]
            r1, g1, b1, _ = rgba[x + 1, y]
            r2, g2, b2, _ = rgba[x, y + 1]
            total += (abs(r - r1) + abs(g - g1) + abs(b - b1) + abs(r - r2) + abs(g - g2) + abs(b - b2)) / 6.0
            count += 1
    return (total / count / 255.0) if count else 0.0


def edge_wrap_difference(rgba, width, height):
    """Mean absolute RGB difference between opposite edges (seamless-tile proxy).

    0 = edges match perfectly (tiles cleanly); higher = visible seam.
    """
    def col(x):
        return [rgba[x, y][:3] for y in range(height)]

    def row(y):
        return [rgba[x, y][:3] for x in range(width)]

    def mad(a, b):
        s = 0
        for pa, pb in zip(a, b):
            s += abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])
        return s / (len(a) * 3 * 255.0)

    lr = mad(col(0), col(width - 1))
    tb = mad(row(0), row(height - 1))
    return {"left_right": lr, "top_bottom": tb, "max": max(lr, tb)}


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

    if args.square:
        ok = width == height
        checks.append(Check(
            "resolution.square",
            "pass" if ok else "fail",
            f"Tile/atlas texture is square ({width}x{height})." if ok else f"Expected a square texture, got {width}x{height}.",
            {"width": width, "height": height},
        ))

    if args.power_of_two:
        ok = is_power_of_two(width) and is_power_of_two(height)
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

    # Coverage / bbox / padding / halo only apply to transparent foreground sprites.
    # Full-bleed tiles and backgrounds are intentionally opaque edge-to-edge.
    bbox = None
    padding = None
    if not args.tile:
        checks.append(Check(
            "silhouette.coverage",
            "pass" if args.min_coverage <= coverage <= args.max_coverage else "fail",
            f"Opaque coverage is {coverage:.3f}; expected {args.min_coverage:.3f}..{args.max_coverage:.3f}.",
            coverage,
            {"min": args.min_coverage, "max": args.max_coverage},
        ))
        bbox = alpha_bbox(alpha, width, height, args.alpha_threshold)
    if not args.tile and bbox:
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
    elif not args.tile:
        checks.append(Check("alpha.bbox", "fail", "No opaque silhouette found."))

    # Edge halo detection: matte-colored RGB values on the silhouette edge almost
    # always mean the PNG was flattened or chroma-keyed poorly before Unity import.
    if not args.tile:
        # An exact member of the locked palette is never a halo: near-white/near-black
        # ramp ends (e.g. a cream ramp top) legally sit on the silhouette edge and
        # would otherwise false-fail small sprites where 1-3 pixels trip the ratio.
        palette_members = set(parse_palette(args.palette)) if args.palette else set()
        edge_count = 0
        halo_count = 0
        halo_by_color = {name: 0 for name in MATTE_COLORS}
        for y in range(height):
            for x in range(width):
                if not is_edge_pixel(alpha, x, y, width, height, args.edge_alpha_threshold):
                    continue
                edge_count += 1
                r, g, b, _ = rgba[x, y]
                if (r, g, b) in palette_members:
                    continue
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
            if args.palette_mode == "exact":
                # Deterministic membership check (pixel art / hard palette locks):
                # every sampled opaque pixel must BE a palette color (within a
                # small tolerance for AA edges), not merely near the palette.
                off = [d for d in distances if d > args.palette_tolerance]
                off_ratio = len(off) / len(distances)
                ok = off_ratio <= args.max_offpalette_ratio
                checks.append(Check(
                    "palette.exact_membership",
                    "pass" if ok else "fail",
                    f"{off_ratio:.3%} of sampled opaque pixels are off-palette (tolerance {args.palette_tolerance}); max allowed is {args.max_offpalette_ratio:.3%}.",
                    {"off_palette_ratio": off_ratio, "off_palette_samples": len(off), "samples": len(distances), "avg_distance": avg_distance, "p95": p95},
                    {"palette_tolerance": args.palette_tolerance, "max_offpalette_ratio": args.max_offpalette_ratio, "palette": args.palette},
                ))
            else:
                ok = avg_distance <= args.max_palette_distance
                checks.append(Check(
                    "palette.distance",
                    "pass" if ok else "fail",
                    f"Average palette distance is {avg_distance:.1f}; max allowed is {args.max_palette_distance:.1f}.",
                    {"avg": avg_distance, "p95": p95, "samples": len(samples)},
                    {"max_avg": args.max_palette_distance, "palette": args.palette},
                ))

    if args.max_distinct_colors is not None:
        # Deterministic color-count histogram (pixel art / hard palette locks):
        # exact distinct RGB values among sampled opaque pixels.
        samples = sample_opaque_pixels(rgba, alpha, width, height, args.alpha_threshold, args.palette_samples)
        distinct_exact = len(set(samples))
        ok = distinct_exact <= args.max_distinct_colors
        checks.append(Check(
            "palette.max_distinct_colors",
            "pass" if ok else "fail",
            f"Found {distinct_exact} distinct opaque colors; max allowed is {args.max_distinct_colors}.",
            {"distinct_colors": distinct_exact, "samples": len(samples)},
            {"max_distinct_colors": args.max_distinct_colors},
        ))

    if args.expected_finish in {"flat", "cel"}:
        distinct, sampled = quantize_distinct_colors(rgba, alpha, width, height, args.alpha_threshold)
        # This is a heuristic warning by default; fail only if user asks with --fail-over-render.
        ok = distinct <= args.max_quantized_colors
        status = "pass" if ok else ("fail" if args.fail_over_render else "warn")
        checks.append(Check(
            "finish.quantized_color_count",
            status,
            f"Detected {distinct} quantized color buckets in {sampled} sampled opaque pixels; target finish is {args.expected_finish}.",
            {"distinct_buckets": distinct, "samples": sampled},
            {"max_quantized_colors": args.max_quantized_colors},
        ))
        grad = mean_local_gradient(rgba, alpha, width, height, args.alpha_threshold)
        ok = grad <= args.max_local_gradient
        status = "pass" if ok else ("fail" if args.fail_over_render else "warn")
        checks.append(Check(
            "finish.local_gradient",
            status,
            f"Mean local RGB gradient is {grad:.4f}; target finish is {args.expected_finish}.",
            grad,
            {"max_local_gradient": args.max_local_gradient},
        ))

    if args.tile:
        wrap = edge_wrap_difference(rgba, width, height)
        ok = wrap["max"] <= args.max_wrap_difference
        checks.append(Check(
            "tile.edge_wrap",
            "pass" if ok else "fail",
            f"Opposite-edge color difference max is {wrap['max']:.4f}; lower is more seamless.",
            wrap,
            {"max_wrap_difference": args.max_wrap_difference},
        ))

    fail_count = sum(1 for c in checks if c.status == "fail")
    warn_count = sum(1 for c in checks if c.status == "warn")
    report = {
        "schema": "unity-game-skills.sprite_qa.v1",
        "image": str(path),
        "art_spec": getattr(args, "art_spec_path", None),
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
    p.add_argument("--square", action="store_true", help="Require square dimensions (tiles/icons/atlases)")
    p.add_argument("--power-of-two", action="store_true", help="Require power-of-two dimensions")
    p.add_argument("--tile", action="store_true", help="Enable seamless-tile checks (edge wrap difference)")
    p.add_argument("--max-wrap-difference", type=float, default=0.08, help="Max opposite-edge RGB difference for --tile (default: 0.08)")
    p.add_argument("--art-spec", help="Path to the governing art-spec.yaml (default: $UNITY_ART_SPEC or canonical Assets paths); fills --palette/--expected-finish defaults")
    p.add_argument("--no-art-spec", action="store_true", help="Explicit override: validate without an art-spec (exploratory work only)")
    p.add_argument("--palette", help="Comma-separated project palette hexes (default: from art-spec palette), e.g. '#E54B4B,#FFD166,#2A9D8F'")
    p.add_argument("--palette-mode", choices=["distance", "exact"], default=None, help="distance = average-distance heuristic (default for non-pixel finishes); exact = per-pixel palette membership (auto-default when the resolved art-spec has craft.finish: pixel)")
    p.add_argument("--palette-tolerance", type=float, default=0, help="Max RGB distance that still counts as a palette member in --palette-mode exact (default: 0)")
    p.add_argument("--max-offpalette-ratio", type=float, default=0.02, help="Max fraction of sampled opaque pixels allowed off-palette in --palette-mode exact (default: 0.02, tolerates AA edges)")
    p.add_argument("--max-distinct-colors", type=int, default=None, help="Fail if sampled opaque pixels contain more than N exact distinct colors (deterministic pixel-art color-count gate)")
    p.add_argument("--max-palette-distance", type=float, default=95, help="Max average RGB distance from palette (default: 95)")
    p.add_argument("--palette-samples", type=int, default=5000, help="Max opaque pixels sampled for palette check")
    p.add_argument("--expected-finish", choices=["any", "flat", "cel"], default=None, help="Warn/fail if a flat/cel target appears over-rendered (default: from art-spec craft.finish, else any)")
    p.add_argument("--max-quantized-colors", type=int, default=180, help="Max quantized color buckets for flat/cel finish heuristic")
    p.add_argument("--max-local-gradient", type=float, default=0.035, help="Max local gradient for flat/cel finish heuristic")
    p.add_argument("--fail-over-render", action="store_true", help="Make finish heuristics fail instead of warn")
    return p


def main() -> int:
    args = build_parser().parse_args()

    # Resolve the governing art-spec (fail-unless---no-art-spec) and default
    # unset flags from it; explicit CLI values always win.
    spec, spec_path = artspec.resolve_or_fail(args.art_spec, args.no_art_spec)
    args.art_spec_path = spec_path
    if spec is not None:
        if not args.palette:
            # Exact-membership QA must check against the SAME artifact generation
            # conditioned on: the master-palette.png swatch (color_image). The spec
            # hex lists are the fallback only — they can legally differ from the
            # swatch (e.g. outline black), which reads as false off-palette fails.
            hexes = artspec.master_palette_colors(spec, spec_path) or artspec.palette_hexes(spec)
            args.palette = ",".join(hexes) if hexes else None
        if args.expected_finish is None:
            args.expected_finish = artspec.spec_finish(spec)
        if args.palette_mode is None and artspec.get_path(spec, "craft.finish") == "pixel":
            # Pixel finish is palette-strict by default: per-pixel membership,
            # not the permissive average-distance heuristic.
            args.palette_mode = "exact"
    args.expected_finish = args.expected_finish or "any"
    args.palette_mode = args.palette_mode or "distance"

    report = validate(args)
    text = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
