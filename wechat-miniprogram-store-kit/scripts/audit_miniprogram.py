#!/usr/bin/env python3
"""Audit a WeChat Mini Program repository for release readiness."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse


SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".cache",
    "__pycache__",
    "node_modules",
    "release-assets",
    "coverage",
}

SOURCE_SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".wxml", ".json"}

PRIVACY_PATTERNS = {
    "location": re.compile(
        r"\bwx\.(?:getLocation|getFuzzyLocation|chooseLocation|choosePoi|startLocationUpdate|startLocationUpdateBackground)\b"
    ),
    "address": re.compile(r"\bwx\.chooseAddress\b"),
    "media": re.compile(
        r"\bwx\.(?:chooseMedia|chooseImage|chooseVideo|saveImageToPhotosAlbum|saveVideoToPhotosAlbum)\b"
    ),
    "camera": re.compile(r"\bwx\.createCameraContext\b|<camera\b", re.IGNORECASE),
    "microphone": re.compile(
        r"\bwx\.(?:getRecorderManager|startRecord)\b|<live-pusher\b", re.IGNORECASE
    ),
    "phone-number": re.compile(
        r"open-type\s*=\s*['\"]getPhoneNumber['\"]", re.IGNORECASE
    ),
    "profile-or-avatar": re.compile(
        r"\bwx\.getUserProfile\b|open-type\s*=\s*['\"]chooseAvatar['\"]",
        re.IGNORECASE,
    ),
    "werun": re.compile(r"\bwx\.getWeRunData\b"),
    "invoice": re.compile(r"\bwx\.(?:chooseInvoice|chooseInvoiceTitle)\b"),
    "bluetooth": re.compile(r"\bwx\.(?:openBluetoothAdapter|startBluetoothDevicesDiscovery)\b"),
    "privacy-flow": re.compile(
        r"\bwx\.(?:getPrivacySetting|openPrivacyContract|requirePrivacyAuthorize|onNeedPrivacyAuthorization)\b|agreePrivacyAuthorization",
        re.IGNORECASE,
    ),
}

NETWORK_PATTERNS = {
    "request": re.compile(r"\bwx\.request\b"),
    "upload": re.compile(r"\bwx\.uploadFile\b"),
    "download": re.compile(r"\bwx\.downloadFile\b"),
    "websocket": re.compile(r"\bwx\.(?:connectSocket|sendSocketMessage)\b"),
    "cloud-call": re.compile(r"\bwx\.cloud\.(?:callFunction|callContainer)\b"),
}

DATA_PATTERNS = {
    "storage": re.compile(r"\bwx\.(?:setStorage|setStorageSync|getStorage|getStorageSync)\b"),
    "login": re.compile(r"\bwx\.login\b"),
    "payment": re.compile(r"\bwx\.requestPayment\b"),
    "clipboard": re.compile(r"\bwx\.(?:setClipboardData|getClipboardData)\b"),
}

SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    "hardcoded-appsecret": re.compile(
        r"(?:app[_-]?secret|appsecret)\s*[:=]\s*['\"][A-Za-z0-9_-]{16,}['\"]",
        re.IGNORECASE,
    ),
    "hardcoded-access-token": re.compile(
        r"(?:access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_.-]{24,}['\"]",
        re.IGNORECASE,
    ),
}

URL_PATTERN = re.compile(r"https?://[^\s'\"<>`]+", re.IGNORECASE)
KEY_FILE_PATTERN = re.compile(
    r"(?:private|upload|secret).*\.(?:key|pem)$|private\..*\.key$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a WeChat Mini Program repository before review and release."
    )
    parser.add_argument("repository", help="Repository root or project directory")
    parser.add_argument("--project-config", help="Explicit project.config.json path")
    parser.add_argument(
        "--main-package-limit-mib",
        type=float,
        default=2.0,
        help="Operational warning/error limit for main package (default: 2 MiB)",
    )
    parser.add_argument(
        "--subpackage-limit-mib",
        type=float,
        default=2.0,
        help="Operational warning/error limit per subpackage (default: 2 MiB)",
    )
    parser.add_argument(
        "--total-limit-mib",
        type=float,
        default=20.0,
        help="Operational warning/error limit for total package (default: 20 MiB)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--output", help="Write report to a file")
    return parser.parse_args()


def locate_project_config(root: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Project config not found: {candidate}")
        return candidate
    direct = root / "project.config.json"
    if direct.is_file():
        return direct
    candidates = [
        path
        for path in root.rglob("project.config.json")
        if not any(part in SKIP_DIRS for part in path.parts)
    ]
    if not candidates:
        raise FileNotFoundError(f"No project.config.json found under {root}")
    if len(candidates) > 1:
        joined = "\n  - ".join(str(path) for path in candidates)
        raise RuntimeError(
            "Multiple project configs found; pass --project-config:\n  - " + joined
        )
    return candidates[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def iter_source_files(root: Path):
    for path in iter_files(root):
        if path.suffix.lower() in SOURCE_SUFFIXES:
            yield path


def scan_source(root: Path) -> dict[str, Any]:
    signals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    urls: set[str] = set()
    domains: set[str] = set()
    combined = {
        **{f"privacy:{key}": value for key, value in PRIVACY_PATTERNS.items()},
        **{f"network:{key}": value for key, value in NETWORK_PATTERNS.items()},
        **{f"data:{key}": value for key, value in DATA_PATTERNS.items()},
        **{f"secret:{key}": value for key, value in SECRET_PATTERNS.items()},
    }
    for path in iter_source_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
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
            for url in URL_PATTERN.findall(line):
                cleaned = url.rstrip(").,;]")
                urls.add(cleaned)
                parsed = urlparse(cleaned)
                if parsed.hostname:
                    domains.add(parsed.hostname)
    return {
        "signals": dict(signals),
        "urls": sorted(urls),
        "domains": sorted(domains),
    }


def page_paths(app_config: dict[str, Any]) -> list[str]:
    pages = list(app_config.get("pages") or [])
    for subpackage in app_config.get("subPackages") or app_config.get("subpackages") or []:
        root = str(subpackage.get("root") or "").strip("/")
        for page in subpackage.get("pages") or []:
            pages.append(f"{root}/{str(page).lstrip('/')}")
    return pages


def missing_page_files(app_root: Path, pages: list[str]) -> list[str]:
    missing: list[str] = []
    for page in pages:
        base = app_root / page
        has_logic = any(base.with_suffix(suffix).is_file() for suffix in (".js", ".ts"))
        has_view = base.with_suffix(".wxml").is_file()
        if not has_logic or not has_view:
            missing.append(page)
    return missing


def declared_assets(app_config: dict[str, Any]) -> list[str]:
    assets: list[str] = []
    tab_bar = app_config.get("tabBar") or {}
    for item in tab_bar.get("list") or []:
        for key in ("iconPath", "selectedIconPath"):
            value = item.get(key)
            if isinstance(value, str) and value:
                assets.append(value)
    return sorted(set(assets))


def package_sizes(app_root: Path, app_config: dict[str, Any]) -> dict[str, Any]:
    files = list(iter_files(app_root))
    subpackages = app_config.get("subPackages") or app_config.get("subpackages") or []
    roots = [str(item.get("root") or "").strip("/") for item in subpackages]
    root_sizes = {root: 0 for root in roots if root}
    main_size = 0
    total_size = 0

    for path in files:
        size = path.stat().st_size
        total_size += size
        relative = path.relative_to(app_root).as_posix()
        matched_root = None
        for root in sorted(root_sizes, key=len, reverse=True):
            if relative == root or relative.startswith(root + "/"):
                matched_root = root
                break
        if matched_root:
            root_sizes[matched_root] += size
        else:
            main_size += size

    return {
        "main_bytes": main_size,
        "total_bytes": total_size,
        "subpackages": root_sizes,
        "file_count": len(files),
    }


def audit(root: Path, project_config_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    project = load_json(project_config_path)
    project_root = project_config_path.parent
    miniprogram_root = str(project.get("miniprogramRoot") or "").strip()
    app_root = (project_root / miniprogram_root).resolve()
    app_config_path = app_root / "app.json"
    if not app_config_path.is_file():
        raise FileNotFoundError(
            f"app.json not found at resolved miniprogramRoot: {app_config_path}"
        )
    app_config = load_json(app_config_path)

    pages = page_paths(app_config)
    missing_pages = missing_page_files(app_root, pages)
    errors.extend(
        f"Page is missing compiled logic or WXML at upload root: {page}"
        for page in missing_pages
    )

    assets = declared_assets(app_config)
    missing_assets = [asset for asset in assets if not (app_root / asset).is_file()]
    errors.extend(f"Missing app.json asset: {asset}" for asset in missing_assets)

    source = scan_source(app_root)
    secret_hits = {
        label: hits
        for label, hits in source["signals"].items()
        if label.startswith("secret:")
    }
    if secret_hits:
        errors.append("Potential hardcoded secret or private key found in upload source.")

    key_files = [
        path.relative_to(root).as_posix()
        for path in iter_files(root)
        if KEY_FILE_PATTERN.search(path.name)
    ]
    if key_files:
        errors.append("Potential upload/private key files found: " + ", ".join(key_files))

    insecure_urls = [url for url in source["urls"] if url.startswith("http://")]
    if insecure_urls:
        warnings.append("HTTP URLs found; production Mini Program networking requires HTTPS.")
    if "api.weixin.qq.com" in source["domains"]:
        errors.append(
            "Client source references api.weixin.qq.com; call WeChat server APIs from a backend."
        )
    local_domains = [
        domain
        for domain in source["domains"]
        if domain in {"localhost", "127.0.0.1"} or re.fullmatch(r"\d+\.\d+\.\d+\.\d+", domain)
    ]
    if local_domains:
        warnings.append(
            "Localhost or direct-IP endpoints found: " + ", ".join(local_domains)
        )

    private_config = project_root / "project.private.config.json"
    if private_config.is_file():
        warnings.append(
            "project.private.config.json exists; confirm it is ignored and contains no credentials."
        )

    privacy_hits = {
        label: hits
        for label, hits in source["signals"].items()
        if label.startswith("privacy:") and label != "privacy:privacy-flow"
    }
    has_privacy_flow = bool(source["signals"].get("privacy:privacy-flow"))
    if privacy_hits and not has_privacy_flow:
        warnings.append(
            "Privacy-sensitive APIs/components found without a detected privacy authorization flow."
        )

    required_private_infos = list(app_config.get("requiredPrivateInfos") or [])
    if privacy_hits:
        warnings.append(
            "Reconcile all detected privacy APIs/components with the dashboard privacy guide; app.json alone is not sufficient."
        )

    sizes = package_sizes(app_root, app_config)
    mib = 1024 * 1024
    if sizes["main_bytes"] > args.main_package_limit_mib * mib:
        errors.append(
            f"Main package source is {sizes['main_bytes'] / mib:.2f} MiB, above the operational {args.main_package_limit_mib:.2f} MiB guardrail."
        )
    if sizes["total_bytes"] > args.total_limit_mib * mib:
        errors.append(
            f"Total upload source is {sizes['total_bytes'] / mib:.2f} MiB, above the operational {args.total_limit_mib:.2f} MiB guardrail."
        )
    for name, size in sizes["subpackages"].items():
        if size > args.subpackage_limit_mib * mib:
            errors.append(
                f"Subpackage {name!r} is {size / mib:.2f} MiB, above the operational {args.subpackage_limit_mib:.2f} MiB guardrail."
            )

    if not project.get("appid"):
        warnings.append("AppID is missing from project.config.json.")

    return {
        "repository": str(root),
        "project_config": str(project_config_path),
        "project_root": str(project_root),
        "miniprogram_root": str(app_root),
        "app_config": str(app_config_path),
        "appid": project.get("appid"),
        "compile_type": project.get("compileType"),
        "pages": pages,
        "subpackages": app_config.get("subPackages")
        or app_config.get("subpackages")
        or [],
        "plugins": app_config.get("plugins") or {},
        "permissions": app_config.get("permission") or {},
        "required_private_infos": required_private_infos,
        "tabbar_assets": assets,
        "package_sizes": sizes,
        "network_urls": source["urls"],
        "network_domains": source["domains"],
        "signals": source["signals"],
        "key_files": key_files,
        "errors": errors,
        "warnings": warnings,
    }


def markdown_report(report: dict[str, Any]) -> str:
    sizes = report["package_sizes"]
    mib = 1024 * 1024
    lines = [
        "# WeChat Mini Program release audit",
        "",
        f"- Repository: `{report['repository']}`",
        f"- Project config: `{report['project_config']}`",
        f"- Upload root: `{report['miniprogram_root']}`",
        f"- AppID: `{report.get('appid') or '(missing)'}`",
        f"- Compile type: `{report.get('compile_type') or '(missing)'}`",
        f"- Pages: {len(report['pages'])}",
        f"- Main package source: {sizes['main_bytes'] / mib:.2f} MiB",
        f"- Total upload source: {sizes['total_bytes'] / mib:.2f} MiB",
        "",
        "## Findings",
        "",
    ]
    if not report["errors"] and not report["warnings"]:
        lines.append("- No structural errors or heuristic warnings found.")
    lines.extend(f"- ERROR: {item}" for item in report["errors"])
    lines.extend(f"- WARNING: {item}" for item in report["warnings"])

    lines += ["", "## Subpackages", ""]
    if sizes["subpackages"]:
        for name, size in sizes["subpackages"].items():
            lines.append(f"- `{name}`: {size / mib:.2f} MiB")
    else:
        lines.append("- No subpackages declared.")

    lines += ["", "## Platform declarations", ""]
    lines.append(
        "- `requiredPrivateInfos`: "
        + (
            ", ".join(f"`{item}`" for item in report["required_private_infos"])
            if report["required_private_infos"]
            else "(none)"
        )
    )
    lines.append(
        "- permissions: "
        + (
            ", ".join(f"`{item}`" for item in report["permissions"])
            if report["permissions"]
            else "(none)"
        )
    )
    lines.append(
        "- plugins: "
        + (
            ", ".join(f"`{item}`" for item in report["plugins"])
            if report["plugins"]
            else "(none)"
        )
    )

    lines += ["", "## Network domains", ""]
    if report["network_domains"]:
        lines.extend(f"- `{domain}`" for domain in report["network_domains"])
    else:
        lines.append("- No literal HTTP(S) domains found in upload source.")

    lines += ["", "## Code and privacy signals", ""]
    if not report["signals"]:
        lines.append("- No heuristic signals found.")
    for label, hits in sorted(report["signals"].items()):
        lines.append(f"### {label} ({len(hits)})")
        lines.append("")
        for hit in hits[:10]:
            excerpt = hit["excerpt"].replace("`", "ˋ")
            lines.append(f"- `{hit['file']}:{hit['line']}` — `{excerpt}`")
        if len(hits) > 10:
            lines.append(f"- … {len(hits) - 10} more")
        lines.append("")

    lines += [
        "## Next steps",
        "",
        "- Compare detected domains with the management-dashboard server-domain list.",
        "- Compare every privacy API/component with 《小程序用户隐私保护指引》.",
        "- Confirm package sizes using the exact DevTools or miniprogram-ci upload build.",
        "- Preview on a real device with legal-domain validation enabled.",
        "- Verify service category, qualifications, filing, reviewer path, and release authorization.",
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
        project_config = locate_project_config(root, args.project_config)
        report = audit(root, project_config, args)
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

