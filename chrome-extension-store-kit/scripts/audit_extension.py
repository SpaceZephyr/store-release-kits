#!/usr/bin/env python3
"""Audit a Chrome extension repository before producing store materials."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any

from image_utils import read_image_info


SKIP_DIRS = {
    ".git",
    ".next",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "coverage",
    "store-assets",
}

REMOTE_CODE_PATTERNS = {
    "eval": re.compile(r"\beval\s*\("),
    "new Function": re.compile(r"\bnew\s+Function\s*\("),
    "remote importScripts": re.compile(
        r"\bimportScripts\s*\(\s*['\"]https?://", re.IGNORECASE
    ),
    "remote dynamic import": re.compile(
        r"\bimport\s*\(\s*['\"]https?://", re.IGNORECASE
    ),
    "remote script tag": re.compile(
        r"<script[^>]+src\s*=\s*['\"]https?://", re.IGNORECASE
    ),
}

NETWORK_PATTERNS = {
    "fetch": re.compile(r"\bfetch\s*\("),
    "XMLHttpRequest": re.compile(r"\bXMLHttpRequest\b"),
    "WebSocket": re.compile(r"\bWebSocket\s*\("),
    "remote URL": re.compile(r"https?://[^\s'\"<>]+"),
}

DATA_API_PATTERNS = {
    "Chrome storage": re.compile(r"\bchrome\.storage\b"),
    "clipboard": re.compile(r"\b(?:navigator\.)?clipboard\b|\bClipboardItem\b"),
    "downloads": re.compile(r"\bchrome\.downloads\b"),
    "cookies": re.compile(r"\bchrome\.cookies\b"),
    "identity": re.compile(r"\bchrome\.identity\b"),
    "history": re.compile(r"\bchrome\.history\b"),
    "tabs": re.compile(r"\bchrome\.tabs\b"),
}

BROAD_HOSTS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a Chrome extension repository and print a review-oriented report."
    )
    parser.add_argument("repository", help="Extension repository or unpacked build directory")
    parser.add_argument("--manifest", help="Explicit manifest.json path")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--output", help="Write the report to this file")
    return parser.parse_args()


def locate_manifest(root: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Manifest not found: {candidate}")
        return candidate
    direct = root / "manifest.json"
    if direct.is_file():
        return direct
    candidates = [
        path
        for path in root.rglob("manifest.json")
        if not any(part in SKIP_DIRS for part in path.parts)
    ]
    if not candidates:
        raise FileNotFoundError(f"No manifest.json found under {root}")
    if len(candidates) > 1:
        joined = "\n  - ".join(str(path) for path in candidates)
        raise RuntimeError(
            "Multiple manifests found; pass --manifest with the upload target:\n  - "
            + joined
        )
    return candidates[0]


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in {".js", ".mjs", ".cjs", ".html", ".htm"}:
            yield path


def collect_manifest_paths(manifest: dict[str, Any]) -> set[str]:
    paths: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and value and not value.startswith(("http://", "https://")):
            paths.add(value)

    for value in (manifest.get("icons") or {}).values():
        add(value)
    action = manifest.get("action") or manifest.get("browser_action") or {}
    add(action.get("default_popup"))
    default_icon = action.get("default_icon")
    if isinstance(default_icon, dict):
        for value in default_icon.values():
            add(value)
    else:
        add(default_icon)
    background = manifest.get("background") or {}
    add(background.get("service_worker"))
    for value in background.get("scripts") or []:
        add(value)
    add(manifest.get("options_page"))
    add((manifest.get("options_ui") or {}).get("page"))
    add(manifest.get("devtools_page"))
    add((manifest.get("side_panel") or {}).get("default_path"))
    for value in (manifest.get("chrome_url_overrides") or {}).values():
        add(value)
    for script in manifest.get("content_scripts") or []:
        for value in (script.get("js") or []) + (script.get("css") or []):
            add(value)
    for value in (manifest.get("sandbox") or {}).get("pages") or []:
        add(value)
    return paths


def source_signals(root: Path) -> dict[str, list[dict[str, Any]]]:
    signals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    combined = {
        **{f"remote-code:{name}": pattern for name, pattern in REMOTE_CODE_PATTERNS.items()},
        **{f"network:{name}": pattern for name, pattern in NETWORK_PATTERNS.items()},
        **{f"api:{name}": pattern for name, pattern in DATA_API_PATTERNS.items()},
    }
    for path in iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in combined.items():
                if pattern.search(line):
                    signals[label].append(
                        {
                            "file": relative,
                            "line": line_number,
                            "excerpt": line.strip()[:180],
                        }
                    )
    return dict(signals)


def audit(root: Path, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_root = manifest_path.parent

    if manifest.get("manifest_version") != 3:
        warnings.append(
            f"Manifest version is {manifest.get('manifest_version')!r}; Chrome Web Store normally expects Manifest V3."
        )

    declared_icons = manifest.get("icons") or {}
    icon_report: dict[str, Any] = {}
    for size in ("16", "32", "48", "128"):
        icon_path = declared_icons.get(size)
        if not icon_path:
            warnings.append(f"Manifest icon {size}x{size} is not declared.")
            continue
        full_path = package_root / icon_path
        if not full_path.is_file():
            errors.append(f"Missing manifest icon: {icon_path}")
            continue
        try:
            info = read_image_info(full_path)
            icon_report[size] = {"path": icon_path, **info.to_dict()}
            if (info.width, info.height) != (int(size), int(size)):
                errors.append(
                    f"Icon {icon_path} is {info.width}x{info.height}, expected {size}x{size}."
                )
        except ValueError as exc:
            errors.append(str(exc))

    referenced_paths = sorted(collect_manifest_paths(manifest))
    missing_paths = [
        path
        for path in referenced_paths
        if "*" not in path and not (package_root / path).is_file()
    ]
    errors.extend(f"Manifest references missing file: {path}" for path in missing_paths)

    permissions = list(manifest.get("permissions") or [])
    optional_permissions = list(manifest.get("optional_permissions") or [])
    host_permissions = list(manifest.get("host_permissions") or [])
    optional_host_permissions = list(manifest.get("optional_host_permissions") or [])
    content_script_matches = sorted(
        {
            match
            for script in manifest.get("content_scripts") or []
            for match in script.get("matches") or []
        }
    )
    broad_hosts = sorted(
        set(host_permissions + optional_host_permissions + content_script_matches)
        & BROAD_HOSTS
    )
    if broad_hosts:
        warnings.append(
            "Broad host access detected: "
            + ", ".join(broad_hosts)
            + ". Confirm it is essential to the single purpose."
        )

    signals = source_signals(package_root)
    remote_code_hits = {
        key: value for key, value in signals.items() if key.startswith("remote-code:")
    }
    if remote_code_hits:
        warnings.append(
            "Potential remote-code execution patterns found. Review every hit before submission."
        )

    csp = manifest.get("content_security_policy")
    csp_text = json.dumps(csp, ensure_ascii=False) if csp else ""
    if re.search(r"https?://", csp_text):
        warnings.append("Content security policy contains a remote HTTP(S) source.")

    return {
        "root": str(root),
        "manifest": str(manifest_path),
        "name": manifest.get("name"),
        "version": manifest.get("version"),
        "description": manifest.get("description"),
        "manifest_version": manifest.get("manifest_version"),
        "permissions": permissions,
        "optional_permissions": optional_permissions,
        "host_permissions": host_permissions,
        "optional_host_permissions": optional_host_permissions,
        "content_script_matches": content_script_matches,
        "icons": icon_report,
        "manifest_references": referenced_paths,
        "signals": signals,
        "errors": errors,
        "warnings": warnings,
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Chrome extension audit",
        "",
        f"- Root: `{report['root']}`",
        f"- Manifest: `{report['manifest']}`",
        f"- Name: {report.get('name') or '(missing)'}",
        f"- Version: {report.get('version') or '(missing)'}",
        f"- Manifest version: {report.get('manifest_version')}",
        f"- Description: {report.get('description') or '(missing)'}",
        "",
        "## Findings",
        "",
    ]
    if not report["errors"] and not report["warnings"]:
        lines.append("- No structural errors or heuristic warnings found.")
    for message in report["errors"]:
        lines.append(f"- ERROR: {message}")
    for message in report["warnings"]:
        lines.append(f"- WARNING: {message}")

    lines += ["", "## Permissions", ""]
    for key in (
        "permissions",
        "optional_permissions",
        "host_permissions",
        "optional_host_permissions",
        "content_script_matches",
    ):
        values = report[key]
        lines.append(f"- {key}: {', '.join(f'`{value}`' for value in values) or '(none)'}")

    lines += ["", "## Icons", ""]
    if report["icons"]:
        for size, info in report["icons"].items():
            alpha = "alpha" if info["has_alpha"] else "opaque"
            lines.append(
                f"- {size}px: `{info['path']}` — {info['width']}x{info['height']} {info['format']} ({alpha})"
            )
    else:
        lines.append("- No readable manifest icons found.")

    lines += ["", "## Code and data-flow signals", ""]
    if not report["signals"]:
        lines.append("- No heuristic signals found.")
    for label, hits in sorted(report["signals"].items()):
        lines.append(f"### {label} ({len(hits)})")
        lines.append("")
        for hit in hits[:12]:
            lines.append(
                f"- `{hit['file']}:{hit['line']}` — `{hit['excerpt'].replace('`', 'ˋ')}`"
            )
        if len(hits) > 12:
            lines.append(f"- … {len(hits) - 12} more")
        lines.append("")

    lines += [
        "## Next review steps",
        "",
        "- Confirm every permission is exercised by submitted code.",
        "- Distinguish remote data requests from remote executable code.",
        "- Map website content, identifiers, communications, and stored preferences to dashboard disclosures.",
        "- Test the exact unpacked directory and final ZIP in Chrome.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.repository).expanduser().resolve()
    if not root.is_dir():
        print(f"Repository is not a directory: {root}", file=sys.stderr)
        return 2
    try:
        manifest_path = locate_manifest(root, args.manifest)
        report = audit(root, manifest_path)
    except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 2

    output = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json
        else markdown_report(report)
    )
    if args.output:
        Path(args.output).expanduser().write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
