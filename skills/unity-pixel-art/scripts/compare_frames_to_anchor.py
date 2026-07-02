#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pillow>=10.0.0",
# ]
# ///
"""Deterministic frame-vs-anchor identity diff for pixel-art animation/rotation QA.

Compares each animation frame (or rotation) against the approved anchor sprite and
FAILS frames that drift. Checks, weighted per the identity-QA doctrine (palette /
baseline / bbox-height carry the weight; silhouette IoU is a LOOSE identity-swap
detector only, because correct-but-different poses legitimately score low IoU):

  palette      opaque frame pixels must be members of the allowed palette
               (default: the anchor's own extracted sub-palette; or --palette /
               --color-image swatch)
  baseline     bottom edge (feet/ground contact) of the alpha bbox must match the
               anchor's within --baseline-tolerance-px
  bbox_height  silhouette height must match the anchor's within
               --bbox-height-tolerance (relative)
  iou          alpha-silhouette IoU vs the anchor must clear the loose --iou-floor

A frame passes only if ALL checks pass. Run BEFORE slicing/sheet packing; this is
the automated gate behind "animation frames that change identity ... are rejected".

Usage:
  python3 compare_frames_to_anchor.py --anchor knight_base.png knight_walk_00.png knight_walk_01.png ...
  python3 compare_frames_to_anchor.py --anchor knight_base.png --strip knight_walk_strip.png --cols 8

  # Emit the anchor's extracted sub-palette as a color_image-compatible swatch PNG
  # (feed it to generate_pixel_art.py --color-image on derived rotate/animate-* calls):
  python3 compare_frames_to_anchor.py --anchor knight_base.png --emit-subpalette knight_subpalette.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WEIGHTS = {"palette": 0.35, "baseline": 0.25, "bbox_height": 0.25, "iou": 0.15}


def _load_rgba(path: str):
    from PIL import Image

    return Image.open(path).convert("RGBA")


def _opaque_data(img, alpha_threshold: int):
    """Return (mask, colors): mask = set of (x,y) opaque pixels, colors = list of (r,g,b) per opaque pixel."""
    px = img.load()
    mask = set()
    colors = []
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a > alpha_threshold:
                mask.add((x, y))
                colors.append((r, g, b))
    return mask, colors


def _bbox(mask: set) -> tuple[int, int, int, int] | None:
    if not mask:
        return None
    xs = [p[0] for p in mask]
    ys = [p[1] for p in mask]
    return min(xs), min(ys), max(xs), max(ys)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _allowed_palette(args, anchor_colors) -> tuple[set, str]:
    if args.color_image:
        img = _load_rgba(args.color_image)
        _, colors = _opaque_data(img, 0)
        return set(colors), f"color-image:{args.color_image}"
    if args.palette:
        return {_hex_to_rgb(h) for h in args.palette}, "cli-hex-list"
    return set(anchor_colors), "anchor-extracted-sub-palette"


def _slice_strip(path: str, cols: int, rows: int):
    img = _load_rgba(path)
    cell_w, cell_h = img.width // cols, img.height // rows
    frames = []
    for r in range(rows):
        for c in range(cols):
            frames.append((f"{path}#r{r}c{c}", img.crop((c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h))))
    return frames


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Deterministic frame-vs-anchor identity diff (pixel art)")
    p.add_argument("frames", nargs="*", help="Frame PNGs to compare against the anchor")
    p.add_argument("--anchor", required=True, help="Approved anchor sprite PNG")
    p.add_argument("--strip", help="Packed horizontal strip to slice instead of frame files")
    p.add_argument("--cols", type=int, help="Strip columns (required with --strip)")
    p.add_argument("--rows", type=int, default=1, help="Strip rows (default 1)")
    p.add_argument("--palette", nargs="*", help="Allowed palette hexes (default: anchor's extracted sub-palette)")
    p.add_argument("--color-image", help="Swatch PNG whose opaque pixels define the allowed palette")
    p.add_argument("--alpha-threshold", type=int, default=8, help="Alpha > N counts as opaque (default 8)")
    p.add_argument("--max-nonmember-pct", type=float, default=0.5,
                   help="Max %% of opaque pixels allowed outside the palette (default 0.5)")
    p.add_argument("--baseline-tolerance-px", type=int, default=2,
                   help="Max bottom-edge (feet) drift vs the anchor in px (default 2)")
    p.add_argument("--bbox-height-tolerance", type=float, default=0.15,
                   help="Max relative silhouette-height drift vs the anchor (default 0.15)")
    p.add_argument("--iou-floor", type=float, default=0.30,
                   help="LOOSE silhouette-IoU floor — identity-swap detector, not a pose matcher (default 0.30)")
    p.add_argument("--no-baseline", action="store_true", help="Skip the baseline check (e.g. jump/death frames)")
    p.add_argument("--action", action="store_true",
                   help="This is an ACTION clip (attack/hit/death): additionally require visible inter-frame motion — near-identical frames pass identity gates but read as a broken animation in game")
    p.add_argument("--min-silhouette-motion", type=float, default=0.06,
                   help="--action: minimum alpha-mask XOR fraction between at least one frame pair — raw pixel change is gameable by recolor/AA shimmer; the silhouette changing is what reads at 32-64px (default 0.06)")
    p.add_argument("--strike-pair", type=int, default=None,
                   help="--action: index of the frame pair (0-based) that must carry the LARGEST delta — for a 4-frame windup/strike/follow/recover strip pass 0 (windup->strike); a strip peaking on recover is mis-authored")
    p.add_argument("--min-inter-frame-motion", type=float, default=0.35,
                   help="--action: minimum fraction of relevant pixels that must change between at least one consecutive frame pair (default 0.35 — calibrated live: a too-subtle slash that read as broken measured 0.27, a real run cycle 0.78; a 1px whole-body shift alone is ~0.30). PAIRED-OVERLAY EXCEPTION: when the attack ships a slash/impact VFX overlay sprite that carries the read, gate the body strip at 0.25 — the strip supports, the overlay sells")
    p.add_argument("--emit-subpalette", metavar="PATH",
                   help="Write the anchor's unique opaque colors as a color_image-compatible swatch PNG "
                        "(the derived-frame sub-palette for generate_pixel_art.py --color-image), then "
                        "continue with the diff — or exit 0 if no frames/--strip were given")
    p.add_argument("--json-report", help="Write a JSON QA report")
    args = p.parse_args(argv)

    if args.strip and not args.cols:
        p.error("--strip requires --cols")
    if not args.strip and not args.frames and not args.emit_subpalette:
        p.error("pass frame PNGs or --strip/--cols (or --emit-subpalette to only export the swatch)")

    anchor_img = _load_rgba(args.anchor)
    anchor_mask, anchor_colors = _opaque_data(anchor_img, args.alpha_threshold)
    anchor_box = _bbox(anchor_mask)
    if anchor_box is None:
        raise SystemExit(f"Anchor has no opaque pixels: {args.anchor}")
    anchor_baseline = anchor_box[3]
    anchor_height = anchor_box[3] - anchor_box[1] + 1
    allowed, palette_source = _allowed_palette(args, anchor_colors)

    if args.emit_subpalette:
        from PIL import Image

        unique: list[tuple[int, int, int]] = []
        seen: set[tuple[int, int, int]] = set()
        for c in anchor_colors:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        cell = 16
        swatch = Image.new("RGB", (cell * len(unique), cell))
        for i, c in enumerate(unique):
            for x in range(i * cell, (i + 1) * cell):
                for y in range(cell):
                    swatch.putpixel((x, y), c)
        out_path = Path(args.emit_subpalette)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        swatch.save(out_path)
        print(f"Wrote anchor sub-palette swatch ({len(unique)} colors): {out_path}")
        if not args.strip and not args.frames:
            return 0

    if args.strip:
        frames = _slice_strip(args.strip, args.cols, args.rows)
    else:
        frames = [(f, _load_rgba(f)) for f in args.frames]

    results: list[dict[str, Any]] = []
    all_pass = True
    for name, img in frames:
        mask, colors = _opaque_data(img, args.alpha_threshold)
        entry: dict[str, Any] = {"frame": name}
        if not mask:
            entry.update({"pass": False, "error": "no opaque pixels"})
            results.append(entry)
            all_pass = False
            continue

        nonmember = sum(1 for c in colors if c not in allowed)
        nonmember_pct = 100.0 * nonmember / len(colors)
        palette_pass = nonmember_pct <= args.max_nonmember_pct

        box = _bbox(mask)
        baseline_delta = abs(box[3] - anchor_baseline)
        baseline_pass = args.no_baseline or baseline_delta <= args.baseline_tolerance_px

        height = box[3] - box[1] + 1
        height_ratio = height / anchor_height
        bbox_pass = abs(1.0 - height_ratio) <= args.bbox_height_tolerance

        inter = len(mask & anchor_mask)
        union = len(mask | anchor_mask)
        iou = inter / union if union else 0.0
        iou_pass = iou >= args.iou_floor

        checks = {"palette": palette_pass, "baseline": baseline_pass, "bbox_height": bbox_pass, "iou": iou_pass}
        weighted = sum(WEIGHTS[k] for k, ok in checks.items() if ok)
        frame_pass = all(checks.values())
        all_pass = all_pass and frame_pass
        entry.update({
            "pass": frame_pass,
            "weighted_score": round(weighted, 3),
            "palette": {"pass": palette_pass, "nonmember_pct": round(nonmember_pct, 3),
                        "nonmember_pixels": nonmember, "distinct_colors": len(set(colors))},
            "baseline": {"pass": baseline_pass, "delta_px": baseline_delta, "skipped": bool(args.no_baseline)},
            "bbox_height": {"pass": bbox_pass, "height_px": height, "anchor_height_px": anchor_height,
                            "ratio": round(height_ratio, 3)},
            "iou": {"pass": iou_pass, "value": round(iou, 3),
                    "note": "loose floor — identity-swap detector, low-but-passing is normal for big poses"},
        })
        results.append(entry)

    # ---- inter-frame MOTION check (--action) ----
    # Identity gates pass strips whose frames are near-identical standing poses —
    # "the slash animation doesn't work" even though the animator plays it (field
    # bug, Knight Runner 2026-07-01). Action clips (attack/hit/death) must MOVE:
    # require a minimum fraction of pixels to change between consecutive frames.
    motion_report = None
    if args.action and len(frames) >= 2:
        import itertools
        frame_pixels = [img for _name, img in frames]
        deltas = []
        sil_deltas = []
        for a, b in itertools.pairwise(frame_pixels):
            if a is None or b is None or a.size != b.size:
                continue
            pa, pb = list(a.getdata()), list(b.getdata())
            relevant = [i for i in range(len(pa)) if pa[i][3] > args.alpha_threshold or pb[i][3] > args.alpha_threshold]
            changed = sum(1 for i in relevant if pa[i] != pb[i])
            deltas.append(changed / max(1, len(relevant)))
            # Silhouette delta: alpha-mask XOR fraction. Raw pixel change is
            # gameable (recolor/AA shimmer passes yet reads as nothing); the
            # SILHOUETTE changing is what survives at 32-64px (Cooper: staging
            # is read from the silhouette).
            sil_changed = sum(
                1 for i in relevant
                if (pa[i][3] > args.alpha_threshold) != (pb[i][3] > args.alpha_threshold)
            )
            sil_deltas.append(sil_changed / max(1, len(relevant)))
        max_delta = max(deltas) if deltas else 0.0
        max_sil = max(sil_deltas) if sil_deltas else 0.0
        motion_pass = max_delta >= args.min_inter_frame_motion
        sil_pass = max_sil >= args.min_silhouette_motion
        # Monotonicity: the biggest change must land on the windup->strike pair
        # (speed = distance/time — the strike gap must be the largest). A strip
        # peaking on the recover frame is mis-authored.
        strike_pass = True
        if args.strike_pair is not None and deltas:
            strike_pass = deltas.index(max(deltas)) == args.strike_pair
        motion_report = {
            "pass": motion_pass and sil_pass and strike_pass,
            "max_inter_frame_change": round(max_delta, 3),
            "per_pair": [round(d, 3) for d in deltas],
            "silhouette": {"pass": sil_pass, "max": round(max_sil, 3),
                           "per_pair": [round(d, 3) for d in sil_deltas],
                           "floor": args.min_silhouette_motion},
            "strike_pair": {"pass": strike_pass, "expected": args.strike_pair,
                            "actual_max_pair": deltas.index(max(deltas)) if deltas else None},
            "floor": args.min_inter_frame_motion,
            "note": "action clips must visibly move; near-identical frames read as a broken animation in game",
        }
        all_pass = all_pass and motion_report["pass"]

    report = {
        "tool": "unity-pixel-art/scripts/compare_frames_to_anchor.py",
        "anchor": args.anchor,
        "palette_source": palette_source,
        "allowed_colors": len(allowed),
        "motion": motion_report,
        "thresholds": {
            "alpha_threshold": args.alpha_threshold,
            "max_nonmember_pct": args.max_nonmember_pct,
            "baseline_tolerance_px": args.baseline_tolerance_px,
            "bbox_height_tolerance": args.bbox_height_tolerance,
            "iou_floor": args.iou_floor,
        },
        "weights": WEIGHTS,
        "frames": results,
        "pass": all_pass,
        "failed_frames": [r["frame"] for r in results if not r["pass"]],
    }
    if args.json_report:
        out = Path(args.json_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
