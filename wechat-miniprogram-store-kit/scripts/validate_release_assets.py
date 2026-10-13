#!/usr/bin/env python3
"""Validate Mini Program release images against a dashboard-derived spec."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from image_utils import read_image_info


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate release-assets using asset-spec.json."
    )
    parser.add_argument("assets", help="release-assets directory")
    parser.add_argument("--spec", help="Explicit asset spec path")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser.parse_args()


def normalize_sizes(raw_sizes: Any) -> set[tuple[int, int]]:
    sizes: set[tuple[int, int]] = set()
    for value in raw_sizes or []:
        if isinstance(value, list) and len(value) == 2:
            sizes.add((int(value[0]), int(value[1])))
        elif isinstance(value, str) and "x" in value.lower():
            width, height = value.lower().split("x", 1)
            sizes.add((int(width), int(height)))
    return sizes


def validate(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    categories: dict[str, list[dict[str, Any]]] = {}

    for category, rules in spec.items():
        pattern = str(rules.get("glob") or "")
        matches = [
            path
            for path in sorted(root.glob(pattern))
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
        infos: list[dict[str, Any]] = []
        for path in matches:
            try:
                info = read_image_info(path)
                infos.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "bytes": path.stat().st_size,
                        **info.to_dict(),
                    }
                )
            except ValueError as exc:
                errors.append(str(exc))
        categories[category] = infos

        required = bool(rules.get("required"))
        min_count = int(rules.get("min_count", 1 if required else 0))
        max_count = rules.get("max_count")
        if len(infos) < min_count:
            errors.append(
                f"{category}: found {len(infos)} assets, expected at least {min_count}."
            )
        if max_count is not None and len(infos) > int(max_count):
            errors.append(
                f"{category}: found {len(infos)} assets, expected at most {int(max_count)}."
            )

        allowed_formats = {str(value).upper() for value in rules.get("formats") or []}
        sizes = normalize_sizes(rules.get("sizes"))
        max_bytes = rules.get("max_bytes")
        for info in infos:
            if allowed_formats and info["format"].upper() not in allowed_formats:
                errors.append(
                    f"{info['path']}: format {info['format']} is not allowed for {category}."
                )
            if sizes and (info["width"], info["height"]) not in sizes:
                expected = ", ".join(f"{width}x{height}" for width, height in sorted(sizes))
                errors.append(
                    f"{info['path']}: {info['width']}x{info['height']}, expected {expected}."
                )
            if rules.get("square") and info["width"] != info["height"]:
                errors.append(f"{info['path']}: {category} must be square.")
            if max_bytes is not None and info["bytes"] > int(max_bytes):
                errors.append(
                    f"{info['path']}: {info['bytes']} bytes exceeds {int(max_bytes)}."
                )

        if rules.get("same_dimensions") and infos:
            dimensions = {(item["width"], item["height"]) for item in infos}
            if len(dimensions) > 1:
                warnings.append(
                    f"{category}: assets use inconsistent dimensions: "
                    + ", ".join(f"{width}x{height}" for width, height in sorted(dimensions))
                )

        if (required or min_count > 0) and not sizes:
            warnings.append(
                f"{category}: exact live-dashboard sizes are not recorded in asset-spec.json."
            )

    return {
        "root": str(root),
        "categories": categories,
        "errors": errors,
        "warnings": warnings,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Mini Program release-asset validation",
        "",
        f"- Root: `{report['root']}`",
        "",
        "## Categories",
        "",
    ]
    for category, images in report["categories"].items():
        lines.append(f"- {category}: {len(images)}")
        for image in images:
            lines.append(
                f"  - `{image['path']}` — {image['width']}x{image['height']} {image['format']}"
            )
    lines += ["", "## Findings", ""]
    if not report["errors"] and not report["warnings"]:
        lines.append("- All checks passed.")
    lines.extend(f"- ERROR: {item}" for item in report["errors"])
    lines.extend(f"- WARNING: {item}" for item in report["warnings"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.assets).expanduser().resolve()
    if not root.is_dir():
        print(f"release-assets directory not found: {root}", file=sys.stderr)
        return 2
    spec_path = (
        Path(args.spec).expanduser().resolve()
        if args.spec
        else root / "asset-spec.json"
    )
    if not spec_path.is_file():
        print(f"Asset spec not found: {spec_path}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid asset spec: {exc}", file=sys.stderr)
        return 2
    report = validate(root, spec)
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else markdown(report)
    )
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

