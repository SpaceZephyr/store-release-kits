#!/usr/bin/env python3
"""Create a non-destructive Chrome Web Store delivery structure."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize store-assets and copy reusable submission templates."
    )
    parser.add_argument("repository", help="Extension repository root")
    parser.add_argument(
        "--output",
        help="Store-assets output directory (default: <repository>/store-assets)",
    )
    return parser.parse_args()


def copy_if_missing(source: Path, destination: Path) -> str:
    if destination.exists():
        return f"SKIP    {destination}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return f"CREATE  {destination}"


def main() -> int:
    args = parse_args()
    repository = Path(args.repository).expanduser().resolve()
    if not (repository / "manifest.json").is_file():
        print(f"manifest.json not found at repository root: {repository}", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parent.parent
    assets = skill_root / "assets"
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else repository / "store-assets"
    )
    for directory in (
        output / "source",
        output / "icons",
        output / "screenshots",
        output / "promo",
        output / "listing",
        output / "privacy",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    operations = [
        (assets / "extension-readme-template.md", repository / "README.md"),
        (assets / "privacy-policy-template.md", repository / "PRIVACY_POLICY.md"),
        (assets / "store-listing-template.md", output / "listing/store-listing-zh-CN.md"),
        (
            assets / "permission-justifications-template.md",
            output / "listing/permission-justifications.md",
        ),
        (assets / "release-notes-template.md", output / "listing/release-notes.md"),
        (assets / "privacy-policy-template.md", output / "privacy/PRIVACY_POLICY.md"),
        (
            assets / "submission-checklist-template.md",
            output / "submission-checklist.md",
        ),
    ]
    for source, destination in operations:
        print(copy_if_missing(source, destination))
    print(f"READY   {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

