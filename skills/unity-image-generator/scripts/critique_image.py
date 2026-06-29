#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""Automated vision QA for generated game art using Gemini.

Self-grading by the generating agent is unreliable ("looks fine" passes
broken art). This closes the loop: it shows the rendered image back to a
vision model and scores it against the STATED intent, catching failures that
pixel metrics miss — wrong subject (a "rock" rendered as planet Earth),
over-rendered shading vs a flat brief, outline-weight drift, palette drift,
floating objects with no grounding, busy backgrounds that should recede, and
edge halos.

It returns strict JSON and a non-zero exit code on fail, so it can gate import.

Examples:
  python3 critique_image.py concept-art/transparent/prop_rock.png \
    --subject "a cute mossy grey rock boulder" \
    --role foreground_prop --finish flat --outline bold \
    --palette '#1A1A2E,#4CD964,#9aa0a6' --json-report rock.critique.json

  python3 critique_image.py environment/tile_grass.png \
    --subject "seamless grass ground tile" --role background_tile \
    --finish flat --outline none --must-recede

  # Inspect the exact request without calling the API:
  python3 critique_image.py x.png --subject "..." --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def get_api_key(provided: str | None) -> str | None:
    return provided or os.environ.get("GEMINI_API_KEY")


RUBRIC_AXES = [
    "subject_correct",
    "style_finish_match",
    "outline_match",
    "palette_adherence",
    "silhouette_readability",
    "grounding",
    "edge_cleanliness",
    "layer_role_fit",
]


def build_instruction(args: argparse.Namespace) -> str:
    intent = {
        "subject": args.subject,
        "composition_role": args.role,
        "target_finish": args.finish,
        "target_outline": args.outline,
        "target_palette_hex": [c.strip() for c in args.palette.split(",")] if args.palette else None,
        "must_recede": bool(args.must_recede),
        "requires_transparency": bool(args.require_alpha),
        "extra_intent": args.intent or None,
    }
    return f"""You are a strict technical art director reviewing a SINGLE generated game-art asset for a mobile game. Judge ONLY against the stated intent, not your personal taste, and NOT toward "more rendering". Flat/minimal is a valid target.

INTENT (the asset must match this):
{json.dumps(intent, indent=2)}

Score each axis 0-3 (0 broken, 1 weak, 2 acceptable, 3 excellent). Axes:
- subject_correct: does the image unambiguously depict the stated subject (e.g. a plain rock, NOT a planet/globe)?
- style_finish_match: shading matches target_finish (flat/cel vs soft-gradient/rendered). If target is flat and the asset is glossy/gradient-heavy, score low.
- outline_match: outline weight/color matches target_outline (none/thin/bold).
- palette_adherence: colors stay within target_palette_hex if provided (else N/A -> 3).
- silhouette_readability: clear, readable shape at small mobile size.
- grounding: if a foreground prop/character, does it read as sitting in a world (or is it a clean cutout suitable for a separate contact shadow)? Penalize a fake/baked ground shadow on a cutout. For tiles/backgrounds, N/A -> 3.
- edge_cleanliness: no chroma/white halo or fringe on the silhouette edge.
- layer_role_fit: if must_recede is true, the asset must be LOW contrast / LOW detail / desaturated so it sits behind gameplay; if it is busy/high-contrast, score low. If must_recede is false, judge that it is readable as a focal asset.

Return STRICT JSON only, no prose, with this shape:
{{
  "scores": {{ {", ".join(f'"{a}": <0-3>' for a in RUBRIC_AXES)} }},
  "overall": <0-3 float>,
  "verdict": "pass" | "fail",
  "blocking_issues": ["short concrete issue", ...],
  "top_fixes": ["concrete prompt or pipeline fix", ...]
}}
Set verdict to "fail" if subject_correct <= 1 or any axis == 0 or overall < {args.pass_threshold}."""


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in model response: {text[:200]}")
    return json.loads(text[start : end + 1])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Vision QA for a generated game-art asset using Gemini.")
    p.add_argument("image", help="Image to critique")
    p.add_argument("--subject", required=True, help="What the asset is supposed to be")
    p.add_argument("--role", default="foreground_prop", help="Composition role (foreground_prop, character, background_tile, ui_icon, ...)")
    p.add_argument("--finish", default="any", choices=["any", "flat", "cel", "soft-gradient", "rendered"], help="Target shading finish")
    p.add_argument("--outline", default="any", choices=["any", "none", "thin", "bold"], help="Target outline weight")
    p.add_argument("--palette", help="Comma-separated target palette hexes")
    p.add_argument("--must-recede", action="store_true", help="Asset must be a recessive background/ground layer")
    p.add_argument("--require-alpha", action="store_true", help="Asset is expected to have transparency")
    p.add_argument("--intent", help="Extra free-form intent notes")
    p.add_argument("--pass-threshold", type=float, default=2.0, help="Min overall score to pass (default: 2.0)")
    p.add_argument("--model", default="gemini-2.5-flash", help="Vision model (default: gemini-2.5-flash)")
    p.add_argument("--api-key", "-k", help="Gemini API key (overrides GEMINI_API_KEY)")
    p.add_argument("--json-report", help="Write critique JSON to this path")
    p.add_argument("--dry-run", action="store_true", help="Print the assembled request and exit without calling the API")
    return p


def main() -> int:
    args = build_parser().parse_args()
    instruction = build_instruction(args)

    if args.dry_run:
        print(json.dumps({"model": args.model, "image": args.image, "instruction": instruction}, indent=2))
        return 0

    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No GEMINI_API_KEY provided (use --api-key or env).", file=sys.stderr)
        return 1

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    img = PILImage.open(args.image)
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[img, instruction],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )
    except Exception as e:  # network/billing/etc.
        print(f"Error calling vision model: {e}", file=sys.stderr)
        return 1

    text = "".join(getattr(p, "text", "") or "" for p in response.parts)
    try:
        critique = extract_json(text)
    except Exception as e:
        print(f"Could not parse model response as JSON: {e}", file=sys.stderr)
        print(text, file=sys.stderr)
        return 1

    report = {
        "schema": "unity-game-skills.image-critique.v1",
        "image": args.image,
        "subject": args.subject,
        "role": args.role,
        "critique": critique,
    }
    out = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0 if critique.get("verdict") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
