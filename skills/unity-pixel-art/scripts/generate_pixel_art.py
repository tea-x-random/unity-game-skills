#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pixellab>=0.1.0",
#     "pillow>=10.0.0",
# ]
# ///
"""Generate pixel-native sprites with PixelLab.

Key resolution: --api-key, then PIXEL_LABS_API_KEY.

The script intentionally exposes only the stable text-to-image and image-conditioned
paths. It supports both older SDK method names (`generate_image_*`) and newer
API/SDK names (`create_image_*`). Use --dry-run before paid calls.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate pixel-native art with PixelLab")
    parser.add_argument("--api-key", "-k", default=os.getenv("PIXEL_LABS_API_KEY"), help="PixelLab API key; defaults to PIXEL_LABS_API_KEY")
    parser.add_argument("--dry-run", action="store_true", help="Print request manifest without calling PixelLab")
    sub = parser.add_subparsers(dest="command", required=True)

    common_help = "Final image output path (PNG)"

    balance = sub.add_parser("balance", help="Check PixelLab account balance/credits")
    balance.add_argument("--manifest", help="Optional JSON balance report")

    pixflux = sub.add_parser("pixflux", help="Text-to-pixel anchor generation")
    pixflux.add_argument("--description", "-d", required=True)
    pixflux.add_argument("--width", type=_positive_int, required=True)
    pixflux.add_argument("--height", type=_positive_int, required=True)
    pixflux.add_argument("--output", "-o", required=True, help=common_help)
    pixflux.add_argument("--no-background", action="store_true", help="Request transparent/no-background output when supported")
    pixflux.add_argument("--seed", type=int, help="Optional deterministic seed when supported")
    pixflux.add_argument("--palette", nargs="*", help="Optional target palette hex colors; passed when SDK supports it and recorded in manifest")
    pixflux.add_argument("--manifest", help="Optional JSON provenance manifest")

    bitforge = sub.add_parser("bitforge", help="Image/style-conditioned pixel generation")
    bitforge.add_argument("--description", "-d", required=True)
    bitforge.add_argument("--width", type=_positive_int, required=True)
    bitforge.add_argument("--height", type=_positive_int, required=True)
    bitforge.add_argument("--style-image", help="Anchor/style reference PNG")
    bitforge.add_argument("--init-image", help="Initial image to edit/condition from")
    bitforge.add_argument("--style-strength", type=float, default=0.85)
    bitforge.add_argument("--no-background", action="store_true", help="Request transparent/no-background output when supported")
    bitforge.add_argument("--seed", type=int, help="Optional deterministic seed when supported")
    bitforge.add_argument("--palette", nargs="*", help="Optional target palette hex colors; passed when SDK supports it and recorded in manifest")
    bitforge.add_argument("--output", "-o", required=True, help=common_help)
    bitforge.add_argument("--manifest", help="Optional JSON provenance manifest")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.api_key and not args.dry_run:
        parser.error("PixelLab key missing. Pass --api-key or export PIXEL_LABS_API_KEY.")

    request: dict[str, Any] = {
        "tool": "unity-pixel-art/scripts/generate_pixel_art.py",
        "provider": "pixellab",
        "command": args.command,
        "description": getattr(args, "description", None),
        "image_size": {"width": getattr(args, "width", None), "height": getattr(args, "height", None)},
        "output": getattr(args, "output", None),
        "no_background": bool(getattr(args, "no_background", False)),
        "seed": getattr(args, "seed", None),
        "palette": getattr(args, "palette", None),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if args.command == "balance":
        for key in ("description", "image_size", "output", "no_background", "seed", "palette"):
            request.pop(key, None)
    if args.command == "bitforge":
        request.update(
            {
                "style_image": args.style_image,
                "init_image": args.init_image,
                "style_strength": args.style_strength,
                "no_background": bool(args.no_background),
                "seed": args.seed,
                "palette": args.palette,
            }
        )

    if args.dry_run:
        print(json.dumps(request, indent=2, sort_keys=True))
        _write_manifest(getattr(args, "manifest", None), {**request, "dry_run": True})
        return 0

    client = _client(args.api_key)
    skipped: list[str] = []

    if args.command == "balance":
        method, method_name = _get_method(client, "get_balance", "balance")
        result = method()
        balance_data = {
            "tool": "unity-pixel-art/scripts/generate_pixel_art.py",
            "provider": "pixellab",
            "command": "balance",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sdk_method": method_name,
            "result_repr": repr(result),
        }
        # Best-effort extraction for SDK objects.
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

    if args.command == "pixflux":
        method, method_name = _get_method(client, "create_image_pixflux", "generate_image_pixflux")
        kwargs = {
            "description": args.description,
            "image_size": {"width": args.width, "height": args.height},
            "no_background": bool(args.no_background),
            "seed": args.seed,
            "target_palette": args.palette,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        call_kwargs, skipped = _accepted_kwargs(method, kwargs)
        result = method(**call_kwargs)
    elif args.command == "bitforge":
        method, method_name = _get_method(client, "create_image_bitforge", "generate_image_bitforge")
        kwargs = {
            "description": args.description,
            "image_size": {"width": args.width, "height": args.height},
            "style_image": _load_pil(args.style_image),
            "style_strength": args.style_strength,
            "no_background": bool(args.no_background),
            "init_image": _load_pil(args.init_image),
            "seed": args.seed,
            "target_palette": args.palette,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        call_kwargs, skipped = _accepted_kwargs(method, kwargs)
        result = method(**call_kwargs)
    else:  # pragma: no cover
        parser.error(f"Unsupported command: {args.command}")

    image = _extract_pil(result)
    _save_image(image, args.output)
    manifest = {
        **request,
        "sdk_skipped_kwargs": skipped,
        "sdk_method": method_name,
        "result_type": type(result).__name__,
        "image_mode": image.mode,
        "image_size_actual": list(image.size),
    }
    _write_manifest(getattr(args, "manifest", None), manifest)
    print(json.dumps({"ok": True, "output": args.output, "manifest": getattr(args, "manifest", None), "skipped_kwargs": skipped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
