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
"""

import argparse
import os
import sys
from pathlib import Path


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


def chroma_key(image, key_color, threshold=60, autocrop=True, pad=4):
    """Cut a solid chroma background to real alpha.

    Samples within ``threshold`` (Euclidean RGB distance) of ``key_color`` are
    made transparent. Optionally autocrops to the opaque bounding box and adds
    uniform transparent padding so every sprite in a family trims consistently.
    """
    from PIL import Image as PILImage

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
    if autocrop:
        bbox = rgba.getbbox()
        if bbox:
            rgba = rgba.crop(bbox)
            if pad > 0:
                padded = PILImage.new("RGBA", (rgba.width + 2 * pad, rgba.height + 2 * pad), (0, 0, 0, 0))
                padded.paste(rgba, (pad, pad))
                rgba = padded
    return rgba


def save_image(image, output_path, alpha_mode, key_color, threshold):
    """Persist a generated PIL image as PNG under the chosen alpha policy.

    alpha_mode:
      - preserve   : keep the model's RGBA alpha verbatim (default).
      - chroma-key : key out a solid chroma background to real alpha.
      - opaque     : flatten onto white (legacy behavior; app icons, full-bleed bg).
    """
    from PIL import Image as PILImage

    if alpha_mode == "chroma-key":
        out = chroma_key(image, key_color, threshold=threshold)
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
        help="Optional input image path for editing/modification"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K"
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

    args = parser.parse_args()

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

    # Load input image if provided
    input_image = None
    output_resolution = args.resolution
    if args.input_image:
        try:
            input_image = PILImage.open(args.input_image)
            print(f"Loaded input image: {args.input_image}")

            # Auto-detect resolution if not explicitly set by user
            if args.resolution == "1K":  # Default value
                # Map input image size to resolution
                width, height = input_image.size
                max_dim = max(width, height)
                if max_dim >= 3000:
                    output_resolution = "4K"
                elif max_dim >= 1500:
                    output_resolution = "2K"
                else:
                    output_resolution = "1K"
                print(f"Auto-detected resolution: {output_resolution} (from input {width}x{height})")
        except Exception as e:
            print(f"Error loading input image: {e}", file=sys.stderr)
            sys.exit(1)

    # Build contents (image first if editing, prompt only if generating)
    if input_image:
        contents = [input_image, args.prompt]
        print(f"Editing image with resolution {output_resolution}...")
    else:
        contents = args.prompt
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
