#!/usr/bin/env python3
"""Initialize a non-destructive App Store release-assets directory."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


SKIP_DIRS = {".git", "node_modules", "Pods", "build", "DerivedData", "release-assets"}
PROJECT_MARKERS = {
    "project.pbxproj", "Package.swift", "Podfile", "pubspec.yaml",
    "capacitor.config.ts", "capacitor.config.json", "config.xml",
    "app.config.js", "app.config.ts", "eas.json",
}


def has_app_project(repository: Path) -> bool:
    for path in repository.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir() and path.suffix in {".xcodeproj", ".xcworkspace"}:
            return True
        if path.is_file() and path.name in PROJECT_MARKERS:
            return True
    return False


def copy_if_missing(source: Path, destination: Path) -> str:
    if destination.exists():
        return f"SKIP    {destination}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return f"CREATE  {destination}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="App repository root")
    parser.add_argument("--output", help="Default: <repository>/release-assets")
    args = parser.parse_args()
    repository = Path(args.repository).expanduser().resolve()
    if not repository.is_dir() or not has_app_project(repository):
        print(f"No Apple/cross-platform app project found under: {repository}", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parent.parent
    templates = skill_root / "assets"
    output = Path(args.output).expanduser().resolve() if args.output else repository / "release-assets"
    for directory in (
        output / "source",
        output / "brand",
        output / "screenshots/zh-Hans/iphone-6.9",
        output / "screenshots/zh-Hans/ipad-13",
        output / "previews",
        output / "metadata/zh-Hans",
        output / "review",
        output / "privacy",
        output / "testflight",
        output / "release",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    operations = [
        ("app-store-readme-template.md", repository / "README.md"),
        ("privacy-policy-template.md", repository / "PRIVACY_POLICY.md"),
        ("metadata.template.json", output / "metadata/zh-Hans/metadata.json"),
        ("review-notes-template.md", output / "review/review-notes.md"),
        ("reviewer-test-paths-template.md", output / "review/reviewer-test-paths.md"),
        ("app-privacy-matrix-template.md", output / "privacy/app-privacy-matrix.md"),
        ("privacy-policy-template.md", output / "privacy/PRIVACY_POLICY.md"),
        ("testflight-template.md", output / "testflight/test-information.md"),
        ("release-notes-template.md", output / "release/release-notes.md"),
        ("submission-checklist-template.md", output / "submission-checklist.md"),
        ("asset-spec.template.json", output / "asset-spec.json"),
        ("gitignore-snippet.txt", output / "review/gitignore-snippet.txt"),
    ]
    for template_name, destination in operations:
        print(copy_if_missing(templates / template_name, destination))
    print(f"READY   {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
