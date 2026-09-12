#!/usr/bin/env python3
"""Build a conservative Chrome extension upload ZIP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile


EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "coverage",
    "node_modules",
    "store-assets",
    "test",
    "tests",
}

EXCLUDED_FILES = {
    ".DS_Store",
    ".gitignore",
    "README.md",
    "PRIVACY_POLICY.md",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}

EXCLUDED_SUFFIXES = {".map", ".log", ".pyc"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Zip an already-built, unpacked Chrome extension directory."
    )
    parser.add_argument("source", help="Directory containing manifest.json at its root")
    parser.add_argument("--output", required=True, help="Output ZIP path")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional relative path or top-level name to exclude; repeat as needed",
    )
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output ZIP"
    )
    return parser.parse_args()


def should_include(path: Path, root: Path, extra_excludes: set[str]) -> bool:
    relative = path.relative_to(root)
    relative_text = relative.as_posix()
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env"):
        return False
    if relative_text in extra_excludes or relative.parts[0] in extra_excludes:
        return False
    return True


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    manifest_path = source / "manifest.json"
    if not manifest_path.is_file():
        print(
            f"Refusing to package: manifest.json is not at ZIP root {source}",
            file=sys.stderr,
        )
        return 2
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid manifest.json: {exc}", file=sys.stderr)
        return 2
    if output.exists() and not args.force:
        print(f"Output already exists; pass --force to replace it: {output}", file=sys.stderr)
        return 2

    files = [
        path
        for path in source.rglob("*")
        if path.is_file()
        and path.resolve() != output
        and should_include(path, source, set(args.exclude))
    ]
    if manifest_path not in files:
        print("Internal error: manifest.json would not be included.", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(source).as_posix())

    print(f"Created: {output}")
    print(f"Extension: {manifest.get('name', '(unnamed)')} {manifest.get('version', '')}")
    print(f"Files: {len(files)}")
    print(f"Bytes: {output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
