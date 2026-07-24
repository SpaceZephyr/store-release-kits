#!/usr/bin/env python3
"""Initialize a non-destructive Mini Program release-assets directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Mini Program release-assets and reusable review templates."
    )
    parser.add_argument("repository", help="Mini Program repository root")
    parser.add_argument(
        "--output",
        help="Output directory (default: <repository>/release-assets)",
    )
    return parser.parse_args()


def copy_if_missing(source: Path, destination: Path) -> str:
    if destination.exists():
        return f"SKIP    {destination}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return f"CREATE  {destination}"


def has_project_config(repository: Path) -> bool:
    return any(
        path.is_file()
        and not any(
            part in {".git", "node_modules", "release-assets", "__pycache__"}
            for part in path.parts
        )
        for path in repository.rglob("project.config.json")
    )


def main() -> int:
    args = parse_args()
    repository = Path(args.repository).expanduser().resolve()
    if not repository.is_dir() or not has_project_config(repository):
        print(
            f"No project.config.json found under repository: {repository}",
            file=sys.stderr,
        )
        return 2

    skill_root = Path(__file__).resolve().parent.parent
    templates = skill_root / "assets"
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else repository / "release-assets"
    )
    for directory in (
        output / "source",
        output / "brand",
        output / "screenshots",
        output / "promotion",
        output / "review",
        output / "privacy",
        output / "release",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    operations = [
        (templates / "miniprogram-readme-template.md", repository / "README.md"),
        (templates / "privacy-policy-template.md", repository / "PRIVACY_POLICY.md"),
        (templates / "submission-template.md", output / "review/submission.md"),
        (
            templates / "privacy-declaration-matrix-template.md",
            output / "review/privacy-declaration-matrix.md",
        ),
        (
            templates / "reviewer-test-paths-template.md",
            output / "review/reviewer-test-paths.md",
        ),
        (
            templates / "privacy-policy-template.md",
            output / "privacy/PRIVACY_POLICY.md",
        ),
        (
            templates / "release-notes-template.md",
            output / "release/release-notes.md",
        ),
        (
            templates / "submission-checklist-template.md",
            output / "submission-checklist.md",
        ),
        (templates / "asset-spec.template.json", output / "asset-spec.json"),
        (
            templates / "gitignore-snippet.txt",
            output / "review/gitignore-snippet.txt",
        ),
    ]
    for source, destination in operations:
        print(copy_if_missing(source, destination))
    print(f"READY   {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
