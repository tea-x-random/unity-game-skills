#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using Google's Gemini image API.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K] [--api-key KEY]

Production calls run under the game's art-spec (docs/PIPELINE_CONVENTIONS.md):
the script resolves art-spec.yaml (--art-spec, $UNITY_ART_SPEC, or canonical
paths), injects its verbatim style paragraph + light direction into the prompt,
and attaches its style-anchor images as reference inputs. Spec-less exploratory
work must pass --no-art-spec explicitly.

Multi-reference conditioning: --input-image/-i is repeatable; pair each with an
--input-role ("character identity", "art style", ...). Roles are sent as
interleaved text parts ("Image 1 = character identity.") — the Gemini API has
no native role parameter.
"""

import argparse
import os
import sys
from pathlib import Path

import art_spec as artspec


# Default solid background used when asking the model for a keyable matte.
# Magenta is the safe default; switch to cyan when the subject itself is pink/red.
CHROMA_DEFAULTS = {
    "magenta": (255, 0, 255),
    "cyan": (0, 255, 255),
}


def _parse_color(text):
    """Parse 'r,g,b' or a named chroma key into an (r, g, b) tuple."""
    if text in CHROMA_DEFAULTS:
        return CHROMA_DEFAULTS[text]
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Invalid color '{text}'. Use 'r,g,b' or one of {list(CHROMA_DEFAULTS)}."
        )
    return tuple(max(0, min(255, int(p))) for p in parts)


def chroma_key(image, key_color, threshold=60, autocrop=True, pad=4, defringe=1):
    """Cut a solid chroma background to real alpha.

    Samples within ``threshold`` (Euclidean RGB distance) of ``key_color`` are
    made transparent. Optionally autocrops to the opaque bounding box and adds
    uniform transparent padding so every sprite in a family trims consistently.

    ``defringe`` erodes the alpha mask by N pixels so the anti-aliased outer
    ring (which still carries key-color spill) is dropped — this removes the
    magenta/cyan/white halo that otherwise survives a distance-threshold key.
    """
    from PIL import Image as PILImage, ImageFilter

    rgba = image.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    kr, kg, kb = key_color
    thr_sq = threshold * threshold
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            dr, dg, db = r - kr, g - kg, b - kb
            if dr * dr + dg * dg + db * db <= thr_sq:
                px[x, y] = (r, g, b, 0)
    if defringe and defringe > 0:
        alpha = rgba.getchannel("A")
        for _ in range(defringe):
            alpha = alpha.filter(ImageFilter.MinFilter(3))
        rgba.putalpha(alpha)
    if autocrop:
        bbox = rgba.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
            if pad > 0:
                padded = PILImage.new("RGBA", (rgba.width + 2 * pad, rgba.height + 2 * pad), (0, 0, 0, 0))
                padded.paste(rgba, (pad, pad))
                rgba = padded
    return rgba


def save_image(image, output_path, alpha_mode, key_color, threshold, defringe=1):
    """Persist a generated PIL image as PNG under the chosen alpha policy.

    alpha_mode:
      - preserve   : keep the model's RGBA alpha verbatim (default).
      - chroma-key : key out a solid chroma background to real alpha.
      - opaque     : flatten onto white (legacy behavior; app icons, full-bleed bg).
    """
    from PIL import Image as PILImage

    if alpha_mode == "chroma-key":
        out = chroma_key(image, key_color, threshold=threshold, defringe=defringe)
        out.save(str(output_path), "PNG")
        return "chroma-key"

    if alpha_mode == "opaque":
        if image.mode == "RGBA":
            flat = PILImage.new("RGB", image.size, (255, 255, 255))
            flat.paste(image, mask=image.split()[3])
            flat.save(str(output_path), "PNG")
        else:
            image.convert("RGB").save(str(output_path), "PNG")
        return "opaque"

    # preserve (default): never flatten alpha onto white.
    if image.mode == "RGBA":
        image.save(str(output_path), "PNG")
    elif image.mode in ("LA", "PA", "P"):
        image.convert("RGBA").save(str(output_path), "PNG")
    else:
        image.convert("RGB").save(str(output_path), "PNG")
    return "preserve"


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Google's Gemini image API"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        default=None,
        help="Input image path for editing/reference conditioning; repeatable (canon sheet + style anchor + ...)"
    )
    parser.add_argument(
        "--input-role",
        action="append",
        default=None,
        help="Role label for the input image at the same position (e.g. 'character identity', 'art style'); repeatable"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default=None,
        help="Output resolution: 1K, 2K, or 4K. Default: auto from largest input image, else 1K. An explicit value always wins."
    )
    parser.add_argument(
        "--art-spec",
        help="Path to the governing art-spec.yaml (default: $UNITY_ART_SPEC or canonical Assets paths)"
    )
    parser.add_argument(
        "--no-art-spec",
        action="store_true",
        help="Explicit override: run without an art-spec (exploratory/concept work only)"
    )
    parser.add_argument(
        "--no-spec-anchors",
        action="store_true",
        help="Do not auto-attach the art-spec's conditioning.style_anchor_images"
    )
    parser.add_argument(
        "--character",
        help="Character id in the art-spec characters block: attaches its canon_sheet and injects its identity_string verbatim"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API key (overrides GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--alpha-mode",
        choices=["preserve", "chroma-key", "opaque"],
        default="preserve",
        help=(
            "PNG alpha handling. preserve keeps generated RGBA alpha (default); "
            "chroma-key removes a solid key background; opaque flattens to white."
        ),
    )
    parser.add_argument(
        "--chroma-key-color",
        type=_parse_color,
        default=CHROMA_DEFAULTS["magenta"],
        help="Color for --alpha-mode chroma-key: 'magenta', 'cyan', or 'r,g,b' (default: magenta).",
    )
    parser.add_argument(
        "--chroma-key-threshold",
        type=int,
        default=60,
        help="RGB distance threshold for --alpha-mode chroma-key (default: 60).",
    )
    parser.add_argument(
        "--chroma-key-defringe",
        type=int,
        default=1,
        help="Alpha erosion pixels after chroma-key to remove matte-color edge spill (default: 1; use 0 to disable).",
    )

    args = parser.parse_args()

    # Resolve the governing art-spec (fail-unless---no-art-spec; see PIPELINE_CONVENTIONS.md).
    spec, spec_path = artspec.resolve_or_fail(args.art_spec, args.no_art_spec)
    if spec_path:
        print(f"Using art-spec: {spec_path}")

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Import here after checking API key to avoid slow import on error
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    # Initialise client
    client = genai.Client(api_key=api_key)

    # Set up output path
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Assemble the reference-input list: explicit --input-image paths (with
    # their --input-role labels), the --character canon sheet, then the
    # art-spec's style anchors (unless --no-spec-anchors).
    input_specs: list[tuple[str, str | None]] = []
    roles = args.input_role or []
    for idx, path in enumerate(args.input_image or []):
        input_specs.append((path, roles[idx] if idx < len(roles) else None))

    identity_string = None
    if args.character:
        if spec is None:
            print("Error: --character requires a resolvable art-spec (characters block).", file=sys.stderr)
            sys.exit(1)
        entry = artspec.character_entry(spec, args.character)
        if entry is None:
            print(f"Error: character '{args.character}' not found in art-spec characters block.", file=sys.stderr)
            sys.exit(1)
        identity_string = entry.get("identity_string")
        canon_sheet = entry.get("canon_sheet")
        if canon_sheet:
            resolved_sheet = artspec.resolve_project_path(str(canon_sheet), spec_path)
            if not resolved_sheet.is_file():
                # --character demands canon conditioning; a silently canon-less
                # production call is invalid (see SKILL.md hard rule).
                print(
                    f"Error: canon_sheet for character '{args.character}' is declared in the "
                    f"art-spec but missing on disk: {canon_sheet} (resolved: {resolved_sheet}). "
                    "Regenerate/sync the canon sheet or fix the spec path before generating.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if str(resolved_sheet) not in [p for p, _ in input_specs]:
                input_specs.append((str(resolved_sheet), f"character identity canon sheet for {args.character}"))

    if spec is not None and not args.no_spec_anchors:
        declared_anchors = artspec.declared_style_anchors(spec)
        resolved_anchors = artspec.style_anchor_images(spec, spec_path)
        if declared_anchors and not resolved_anchors:
            print(
                "WARNING: the art-spec declares conditioning.style_anchor_images but NONE "
                f"resolve to files on disk ({declared_anchors}). This call will attach ZERO "
                "style-anchor conditioning images — production art generated without its "
                "anchors is invalid. Fix the paths / regenerate the anchors, or pass "
                "--no-spec-anchors to acknowledge explicitly.",
                file=sys.stderr,
            )
        for anchor in resolved_anchors:
            if anchor not in [p for p, _ in input_specs]:
                input_specs.append((anchor, "art style anchor"))

    input_images: list[tuple[object, str | None]] = []
    for path, role in input_specs:
        try:
            img = PILImage.open(path)
            input_images.append((img, role))
            print(f"Loaded input image: {path}" + (f" (role: {role})" if role else ""))
        except Exception as e:
            print(f"Error loading input image {path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Resolution: explicit -r always wins; otherwise auto-detect from the
    # largest input image; otherwise 1K. (The old code used '1K' as both the
    # default and a legal explicit value, so an explicit '-r 1K' was
    # indistinguishable from the default and hi-res inputs inflated output.)
    if args.resolution is not None:
        output_resolution = args.resolution
    elif input_images:
        max_dim = max(max(img.size) for img, _ in input_images)
        if max_dim >= 3000:
            output_resolution = "4K"
        elif max_dim >= 1500:
            output_resolution = "2K"
        else:
            output_resolution = "1K"
        print(f"Auto-detected resolution: {output_resolution} (from largest input dim {max_dim})")
    else:
        output_resolution = "1K"

    # Build the final prompt: user prompt + verbatim identity string + the
    # art-spec's verbatim style paragraph (values transmitted, never invented).
    prompt = args.prompt
    if identity_string:
        prompt += f"\n\nCHARACTER IDENTITY (frozen — copy exactly, vary only pose/action): {identity_string}"
    if spec is not None:
        prompt += "\n\n" + artspec.style_paragraph(spec)

    # Build contents. Multiple inputs get role-interleaved text parts
    # ("Image 1 = character identity.") — Gemini has no native role parameter.
    if len(input_images) > 1:
        contents = []
        for n, (img, role) in enumerate(input_images, start=1):
            contents.append(f"Image {n} = {role or 'reference'}.")
            contents.append(img)
        contents.append(prompt)
        print(f"Editing with {len(input_images)} reference images at resolution {output_resolution}...")
    elif input_images:
        img, role = input_images[0]
        contents = ([f"Image 1 = {role}.", img, prompt] if role else [img, prompt])
        print(f"Editing image with resolution {output_resolution}...")
    else:
        contents = prompt
        print(f"Generating image with resolution {output_resolution}...")

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    image_size=output_resolution
                )
            )
        )
        
        # Process response and save to PNG.
        # IMPORTANT: preserve alpha by default. The previous implementation
        # composited RGBA onto white, creating white-matted sprites and edge
        # halos after Unity import.
        image_saved = False
        for part in response.parts:
            if part.text is not None:
                print(f"Model response: {part.text}")
            elif part.inline_data is not None:
                # Convert inline data to PIL Image and save as PNG.
                from io import BytesIO

                # inline_data.data is already bytes, not base64
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    # If it's a string, it might be base64
                    import base64
                    image_data = base64.b64decode(image_data)

                image = PILImage.open(BytesIO(image_data))
                saved_mode = save_image(
                    image=image,
                    output_path=output_path,
                    alpha_mode=args.alpha_mode,
                    key_color=args.chroma_key_color,
                    threshold=args.chroma_key_threshold,
                    defringe=args.chroma_key_defringe,
                )
                print(f"Saved PNG with alpha-mode: {saved_mode}")
                image_saved = True
        
        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
        else:
            print("Error: No image was generated in the response.", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
