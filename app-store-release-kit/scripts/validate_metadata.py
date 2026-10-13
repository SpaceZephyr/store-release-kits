#!/usr/bin/env python3
"""Validate stable App Store Connect text limits in a metadata JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


LIMITS = {
    "name": ("characters", 30),
    "subtitle": ("characters", 30),
    "promotional_text": ("characters", 170),
    "description": ("characters", 4000),
    "keywords": ("bytes", 100),
}
REQUIRED = {"locale", "name", "description", "keywords", "support_url", "privacy_policy_url"}
URL_FIELDS = {"support_url", "marketing_url", "privacy_policy_url", "privacy_choices_url"}


def validate(data: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for field in sorted(REQUIRED):
        if not str(data.get(field) or "").strip():
            errors.append(f"{field}: required.")
    name = str(data.get("name") or "")
    if name and len(name) < 2:
        errors.append("name: must contain at least 2 characters.")
    for field, (unit, limit) in LIMITS.items():
        value = str(data.get(field) or "")
        length = len(value.encode("utf-8")) if unit == "bytes" else len(value)
        if length > limit:
            errors.append(f"{field}: {length} {unit}, limit {limit}.")
    for field in URL_FIELDS:
        value = str(data.get(field) or "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{field}: use a public HTTPS URL.")
        if parsed.hostname in {"localhost", "127.0.0.1"}:
            errors.append(f"{field}: local URL is not publicly reachable.")
    keywords = str(data.get("keywords") or "")
    if "，" in keywords:
        warnings.append("keywords: use ASCII commas rather than Chinese commas.")
    if "<" in str(data.get("description") or "") and ">" in str(data.get("description") or ""):
        warnings.append("description: App Store description is plain text; remove HTML.")
    return {"errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", help="metadata.json path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = Path(args.metadata).expanduser().resolve()
    if not path.is_file():
        print(f"Metadata file not found: {path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    report = validate(data)
    if args.json:
        print(json.dumps({"path": str(path), **report}, ensure_ascii=False, indent=2))
    else:
        print("# App Store metadata validation\n")
        print(f"- File: `{path}`\n")
        if not report["errors"] and not report["warnings"]:
            print("- All checks passed.")
        for item in report["errors"]:
            print(f"- ERROR: {item}")
        for item in report["warnings"]:
            print(f"- WARNING: {item}")
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

