#!/usr/bin/env python3
"""Validate Chrome Web Store image dimensions and transparency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from image_utils import read_image_info


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
SKIP_DIRS = {"source"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Chrome Web Store graphic assets.")
    parser.add_argument("assets", help="Store-assets directory")
    parser.add_argument(
        "--minimum-screenshots",
        type=int,
        default=3,
        help="Recommended minimum screenshot count (default: 3)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser.parse_args()


def validate(root: Path, minimum_screenshots: int) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    images: list[dict[str, object]] = []

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or path.suffix.lower() not in IMAGE_SUFFIXES
            or any(part in SKIP_DIRS for part in relative.parts)
        ):
            continue
        try:
            info = read_image_info(path)
            images.append({"path": relative.as_posix(), **info.to_dict()})
        except ValueError as exc:
            errors.append(str(exc))

    def at_size(width: int, height: int) -> list[dict[str, object]]:
        return [
            image
            for image in images
            if image["width"] == width and image["height"] == height
        ]

    store_icons = at_size(128, 128)
    screenshots = at_size(1280, 800) + at_size(640, 400)
    small_tiles = at_size(440, 280)
    marquee_tiles = at_size(1400, 560)

    if not store_icons:
        errors.append("Missing 128x128 store icon.")
    elif not any(image["format"] == "PNG" for image in store_icons):
        warnings.append("A PNG store icon is recommended.")

    if len(screenshots) < minimum_screenshots:
        errors.append(
            f"Found {len(screenshots)} valid screenshots; expected at least {minimum_screenshots}."
        )
    if len(screenshots) > 5:
        errors.append(f"Found {len(screenshots)} screenshots; Chrome accepts at most 5.")
    if screenshots and not any(
        image["width"] == 1280 and image["height"] == 800 for image in screenshots
    ):
        warnings.append("All screenshots are 640x400; 1280x800 is preferred.")

    if not small_tiles:
        errors.append("Missing 440x280 small promotional tile.")
    if not marquee_tiles:
        errors.append("Missing 1400x560 marquee promotional tile.")

    for label, candidates in (
        ("small promotional tile", small_tiles),
        ("marquee promotional tile", marquee_tiles),
    ):
        for image in candidates:
            if image["format"] == "PNG":
                if image["has_alpha"]:
                    errors.append(f"{image['path']}: {label} PNG has alpha transparency.")
                if image["bit_depth"] != 8 or image["color_type"] != 2:
                    errors.append(
                        f"{image['path']}: {label} must be a 24-bit RGB PNG or JPEG."
                    )

    recognized = {
        image["path"]
        for image in store_icons + screenshots + small_tiles + marquee_tiles
    }
    unrecognized = [image["path"] for image in images if image["path"] not in recognized]
    if unrecognized:
        warnings.append(
            "Images with non-store dimensions found (acceptable as editable sources): "
            + ", ".join(unrecognized)
        )

    return {
        "root": str(root),
        "images": images,
        "store_icons": [image["path"] for image in store_icons],
        "screenshots": [image["path"] for image in screenshots],
        "small_tiles": [image["path"] for image in small_tiles],
        "marquee_tiles": [image["path"] for image in marquee_tiles],
        "errors": errors,
        "warnings": warnings,
    }


def markdown(report: dict[str, object]) -> str:
    lines = [
        "# Chrome Web Store asset validation",
        "",
        f"- Root: `{report['root']}`",
        f"- Store icons: {len(report['store_icons'])}",
        f"- Screenshots: {len(report['screenshots'])}",
        f"- Small promo tiles: {len(report['small_tiles'])}",
        f"- Marquee promo tiles: {len(report['marquee_tiles'])}",
        "",
        "## Findings",
        "",
    ]
    if not report["errors"] and not report["warnings"]:
        lines.append("- All checks passed.")
    lines.extend(f"- ERROR: {message}" for message in report["errors"])
    lines.extend(f"- WARNING: {message}" for message in report["warnings"])
    lines += ["", "## Recognized files", ""]
    for category in ("store_icons", "screenshots", "small_tiles", "marquee_tiles"):
        lines.append(f"- {category}: {', '.join(report[category]) or '(none)'}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.assets).expanduser().resolve()
    if not root.is_dir():
        print(f"Asset directory not found: {root}", file=sys.stderr)
        return 2
    report = validate(root, args.minimum_screenshots)
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else markdown(report)
    )
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
