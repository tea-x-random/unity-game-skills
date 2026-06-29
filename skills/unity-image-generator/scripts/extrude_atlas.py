#!/usr/bin/env python3
"""Add extruded borders/padding around each cell in a sprite/tile sheet.

Unity atlases can bleed neighboring pixels during filtering/mipmapping. This
script repacks a regular grid sheet so each frame has duplicated edge pixels
("extrude") plus transparent padding, and emits a JSON manifest with frame rects
that exclude the extruded border.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image


def extrude_cell(cell: Image.Image, e: int) -> Image.Image:
    cell = cell.convert("RGBA")
    if e <= 0:
        return cell
    w, h = cell.size
    out = Image.new("RGBA", (w + 2 * e, h + 2 * e), (0, 0, 0, 0))
    out.paste(cell, (e, e))
    # sides
    left = cell.crop((0, 0, 1, h)).resize((e, h))
    right = cell.crop((w - 1, 0, w, h)).resize((e, h))
    top = cell.crop((0, 0, w, 1)).resize((w, e))
    bottom = cell.crop((0, h - 1, w, h)).resize((w, e))
    out.paste(left, (0, e))
    out.paste(right, (e + w, e))
    out.paste(top, (e, 0))
    out.paste(bottom, (e, e + h))
    # corners
    out.paste(cell.crop((0, 0, 1, 1)).resize((e, e)), (0, 0))
    out.paste(cell.crop((w - 1, 0, w, 1)).resize((e, e)), (e + w, 0))
    out.paste(cell.crop((0, h - 1, 1, h)).resize((e, e)), (0, e + h))
    out.paste(cell.crop((w - 1, h - 1, w, h)).resize((e, e)), (e + w, e + h))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Extrude/pad regular-grid sprite or tile sheet.")
    p.add_argument("--input", required=True, help="Input sprite/tile sheet")
    p.add_argument("--rows", type=int, required=True)
    p.add_argument("--cols", type=int, required=True)
    p.add_argument("--extrude", type=int, default=2, help="Duplicated edge pixels per frame (default: 2)")
    p.add_argument("--padding", type=int, default=2, help="Transparent padding around extruded frame (default: 2)")
    p.add_argument("--output", required=True, help="Output PNG")
    p.add_argument("--manifest", help="Output JSON manifest")
    args = p.parse_args()

    src = Image.open(args.input).convert("RGBA")
    sw, sh = src.size
    if sw % args.cols or sh % args.rows:
        raise SystemExit(f"Input size {sw}x{sh} is not divisible by grid {args.cols}x{args.rows}")
    cw, ch = sw // args.cols, sh // args.rows
    e, pad = args.extrude, args.padding
    packed_w = cw + 2 * e + 2 * pad
    packed_h = ch + 2 * e + 2 * pad
    out = Image.new("RGBA", (args.cols * packed_w, args.rows * packed_h), (0, 0, 0, 0))
    frames = []

    for r in range(args.rows):
        for c in range(args.cols):
            name = f"frame_{r}_{c}"
            cell = src.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            ext = extrude_cell(cell, e)
            ox, oy = c * packed_w + pad, r * packed_h + pad
            out.paste(ext, (ox, oy), ext)
            frames.append({
                "name": name,
                "source_rect": [c * cw, r * ch, cw, ch],
                "atlas_rect": [ox + e, oy + e, cw, ch],
                "extruded_rect": [ox, oy, cw + 2 * e, ch + 2 * e],
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output, "PNG")
    manifest = {
        "schema": "unity-game-skills.extruded-atlas.v1",
        "input": args.input,
        "output": args.output,
        "rows": args.rows,
        "cols": args.cols,
        "cell_size": [cw, ch],
        "extrude": e,
        "padding": pad,
        "frames": frames,
    }
    if args.manifest:
        Path(args.manifest).parent.mkdir(parents=True, exist_ok=True)
        Path(args.manifest).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
