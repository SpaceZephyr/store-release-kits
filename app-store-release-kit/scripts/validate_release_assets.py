#!/usr/bin/env python3
"""Validate App Store screenshots and icon exports against asset-spec.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from image_utils import read_image_info


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", help="release-assets directory")
    parser.add_argument("--spec", help="Explicit asset-spec.json path")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    return parser.parse_args()


def normalize_sizes(values: Any) -> set[tuple[int, int]]:
    sizes: set[tuple[int, int]] = set()
    for value in values or []:
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
        paths = [
            path for path in sorted(root.glob(pattern))
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]
        infos: list[dict[str, Any]] = []
        for path in paths:
            try:
                image = read_image_info(path)
                infos.append({
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    **image.to_dict(),
                })
            except ValueError as exc:
                errors.append(str(exc))
        categories[category] = infos

        required = bool(rules.get("required"))
        minimum = int(rules.get("min_count", 1 if required else 0))
        maximum = rules.get("max_count")
        if len(infos) < minimum:
            errors.append(f"{category}: found {len(infos)}, expected at least {minimum}.")
        if maximum is not None and len(infos) > int(maximum):
            errors.append(f"{category}: found {len(infos)}, expected at most {maximum}.")

        allowed = {str(item).upper() for item in rules.get("formats") or []}
        sizes = normalize_sizes(rules.get("sizes"))
        for info in infos:
            if allowed and info["format"].upper() not in allowed:
                errors.append(f"{info['path']}: {info['format']} is not allowed.")
            if sizes and (info["width"], info["height"]) not in sizes:
                expected = ", ".join(f"{w}x{h}" for w, h in sorted(sizes))
                errors.append(
                    f"{info['path']}: {info['width']}x{info['height']}; expected {expected}."
                )
            if rules.get("square") and info["width"] != info["height"]:
                errors.append(f"{info['path']}: must be square.")
            if rules.get("no_alpha") and info["has_alpha"]:
                errors.append(f"{info['path']}: alpha/transparency is not allowed.")
            maximum_bytes = rules.get("max_bytes")
            if maximum_bytes is not None and info["bytes"] > int(maximum_bytes):
                errors.append(f"{info['path']}: exceeds {int(maximum_bytes)} bytes.")

        if rules.get("same_dimensions") and infos:
            dimensions = {(item["width"], item["height"]) for item in infos}
            if len(dimensions) > 1:
                errors.append(
                    f"{category}: inconsistent dimensions: "
                    + ", ".join(f"{w}x{h}" for w, h in sorted(dimensions))
                )
        if not sizes and (required or minimum > 0):
            warnings.append(f"{category}: live accepted sizes are not recorded.")

    return {
        "root": str(root),
        "categories": categories,
        "errors": errors,
        "warnings": warnings,
    }


def as_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# App Store release-asset validation",
        "",
        f"- Root: `{report['root']}`",
        "",
        "## Categories",
        "",
    ]
    for category, images in report["categories"].items():
        lines.append(f"- {category}: {len(images)}")
        for image in images:
            alpha = "alpha" if image["has_alpha"] else "opaque"
            lines.append(
                f"  - `{image['path']}` — {image['width']}x{image['height']} "
                f"{image['format']} ({alpha})"
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
    spec_path = (
        Path(args.spec).expanduser().resolve()
        if args.spec else root / "asset-spec.json"
    )
    if not root.is_dir() or not spec_path.is_file():
        print(f"Missing release-assets or spec: {root} / {spec_path}", file=sys.stderr)
        return 2
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid asset spec: {exc}", file=sys.stderr)
        return 2
    report = validate(root, spec)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else as_markdown(report))
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

