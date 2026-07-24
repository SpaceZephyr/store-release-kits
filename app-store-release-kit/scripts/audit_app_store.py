#!/usr/bin/env python3
"""Statically audit an Apple-platform app repository for App Store readiness."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import plistlib
import re
import sys
from typing import Any
from urllib.parse import urlparse


SKIP_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules", "Pods",
    "Carthage", ".build", "build", "DerivedData", "release-assets", "coverage",
}
TEXT_SUFFIXES = {
    ".swift", ".m", ".mm", ".h", ".hpp", ".c", ".cc", ".cpp",
    ".js", ".jsx", ".ts", ".tsx", ".dart", ".json", ".xml", ".plist",
    ".xcconfig", ".pbxproj", ".strings", ".gradle", ".properties", ".yaml", ".yml",
}
PROJECT_MARKERS = {
    "Package.swift": "Swift Package",
    "Podfile": "CocoaPods",
    "pubspec.yaml": "Flutter",
    "capacitor.config.ts": "Capacitor",
    "capacitor.config.json": "Capacitor",
    "config.xml": "Cordova",
    "eas.json": "Expo/EAS",
    "project.pbxproj": "Xcode",
}
USAGE_KEYS = {
    "camera": ("NSCameraUsageDescription",),
    "photos-read": ("NSPhotoLibraryUsageDescription",),
    "photos-add": ("NSPhotoLibraryAddUsageDescription",),
    "microphone": ("NSMicrophoneUsageDescription",),
    "location": (
        "NSLocationWhenInUseUsageDescription",
        "NSLocationAlwaysAndWhenInUseUsageDescription",
    ),
    "contacts": ("NSContactsUsageDescription",),
    "calendar": (
        "NSCalendarsUsageDescription",
        "NSCalendarsFullAccessUsageDescription",
        "NSCalendarsWriteOnlyAccessUsageDescription",
    ),
    "bluetooth": ("NSBluetoothAlwaysUsageDescription", "NSBluetoothPeripheralUsageDescription"),
    "local-network": ("NSLocalNetworkUsageDescription",),
    "motion": ("NSMotionUsageDescription",),
    "speech": ("NSSpeechRecognitionUsageDescription",),
    "face-id": ("NSFaceIDUsageDescription",),
    "health": ("NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"),
    "homekit": ("NSHomeKitUsageDescription",),
    "media-library": ("NSAppleMusicUsageDescription",),
    "tracking": ("NSUserTrackingUsageDescription",),
}
PRIVACY_PATTERNS = {
    "camera": re.compile(r"\b(?:AVCaptureSession|UIImagePickerController|PHPickerViewController)\b"),
    "photos-read": re.compile(r"\b(?:PHPhotoLibrary|PHPickerViewController)\b"),
    "photos-add": re.compile(r"\b(?:performChanges|UIImageWriteToSavedPhotosAlbum)\b"),
    "microphone": re.compile(r"\b(?:AVAudioRecorder|AVAudioEngine|requestRecordPermission)\b"),
    "location": re.compile(r"\b(?:CLLocationManager|requestWhenInUseAuthorization|requestAlwaysAuthorization)\b"),
    "contacts": re.compile(r"\b(?:CNContactStore|requestAccess.*contacts)\b", re.IGNORECASE),
    "calendar": re.compile(
        r"\b(?:EKEventStore|requestFullAccessToEvents|requestWriteOnlyAccessToEvents|requestAccessToEntityType)\b"
    ),
    "bluetooth": re.compile(r"\b(?:CBCentralManager|CBPeripheralManager)\b"),
    "local-network": re.compile(r"\b(?:NWBrowser|NetServiceBrowser)\b"),
    "motion": re.compile(r"\b(?:CMMotionManager|CMPedometer)\b"),
    "speech": re.compile(r"\b(?:SFSpeechRecognizer|SFSpeechRecognizer\.requestAuthorization)\b"),
    "face-id": re.compile(r"\b(?:LAPolicyDeviceOwnerAuthenticationWithBiometrics|faceID)\b"),
    "health": re.compile(r"\b(?:HKHealthStore|HealthKit)\b"),
    "homekit": re.compile(r"\b(?:HMHomeManager|HomeKit)\b"),
    "media-library": re.compile(r"\b(?:MPMediaLibrary|MPMediaLibrary\.requestAuthorization)\b"),
    "tracking": re.compile(r"\b(?:ATTrackingManager|ASIdentifierManager|advertisingIdentifier)\b"),
}
REQUIRED_REASON_PATTERNS = {
    "NSPrivacyAccessedAPICategoryUserDefaults": re.compile(r"\b(?:UserDefaults|NSUserDefaults)\b"),
    "NSPrivacyAccessedAPICategoryFileTimestamp": re.compile(
        r"\b(?:attributesOfItem|contentModificationDate|creationDate|stat|fstat|getattrlist)\b"
    ),
    "NSPrivacyAccessedAPICategorySystemBootTime": re.compile(
        r"\b(?:systemUptime|mach_absolute_time|kern\.boottime)\b"
    ),
    "NSPrivacyAccessedAPICategoryDiskSpace": re.compile(
        r"\b(?:volumeAvailableCapacity|systemFreeSize|systemSize|statfs|statvfs)\b"
    ),
    "NSPrivacyAccessedAPICategoryActiveKeyboards": re.compile(r"\bactiveInputModes\b"),
}
FEATURE_PATTERNS = {
    "network": re.compile(r"\b(?:URLSession|Alamofire|fetch\s*\(|axios\.|http\.)\b"),
    "analytics": re.compile(r"\b(?:FirebaseAnalytics|Analytics\.logEvent|Mixpanel|Amplitude|PostHog)\b"),
    "crash-reporting": re.compile(r"\b(?:Crashlytics|SentrySDK|Bugsnag)\b"),
    "advertising": re.compile(r"\b(?:GoogleMobileAds|GADBannerView|AppLovin|IronSource|UnityAds)\b"),
    "push": re.compile(r"\b(?:registerForRemoteNotifications|UNUserNotificationCenter)\b"),
    "keychain": re.compile(r"\b(?:SecItemAdd|SecItemCopyMatching|Keychain)\b"),
    "storekit": re.compile(r"\b(?:StoreKit|Product\.products|SKPaymentQueue|purchase\s*\()\b"),
    "sign-in-with-apple": re.compile(r"\b(?:ASAuthorizationAppleIDProvider|SignInWithAppleButton)\b"),
    "webview": re.compile(r"\bWKWebView\b"),
    "account-creation": re.compile(
        r"\b(?:createAccount|signUp|registerAccount|注册账号|创建账号)\b", re.IGNORECASE
    ),
    "account-deletion": re.compile(
        r"\b(?:deleteAccount|removeAccount|账号删除|删除账号|注销账号)\b", re.IGNORECASE
    ),
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "hardcoded-secret": re.compile(
        r"(?:api[_-]?secret|client[_-]?secret|app[_-]?secret)\s*[:=]\s*['\"][^'\"]{12,}['\"]",
        re.IGNORECASE,
    ),
    "hardcoded-token": re.compile(
        r"(?:access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_.-]{20,}['\"]",
        re.IGNORECASE,
    ),
}
SECRET_FILE_RE = re.compile(
    r"AuthKey_.*\.p8$|.*\.(?:p8|p12)$|"
    r"(?:private|secret|signing).*\.(?:key|pem)$",
    re.IGNORECASE,
)
SIGNING_ARTIFACT_RE = re.compile(r".*\.(?:mobileprovision|cer)$", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s'\"<>`\\]+", re.IGNORECASE)
BUILD_SETTING_RE = re.compile(
    r"^\s*(PRODUCT_BUNDLE_IDENTIFIER|MARKETING_VERSION|CURRENT_PROJECT_VERSION|"
    r"IPHONEOS_DEPLOYMENT_TARGET|MACOSX_DEPLOYMENT_TARGET|"
    r"CODE_SIGN_ENTITLEMENTS|ASSETCATALOG_COMPILER_APPICON_NAME)\s*=\s*([^;]+);",
    re.MULTILINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--output", help="Write report to file")
    return parser.parse_args()


def relative_parts(path: Path, root: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(root).parts
    except ValueError:
        return path.parts


def skipped(path: Path, root: Path) -> bool:
    return any(part in SKIP_DIRS for part in relative_parts(path, root))


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not skipped(path, root):
            yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_plist(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("rb") as handle:
            value = plistlib.load(handle)
        return value if isinstance(value, dict) else None
    except (OSError, plistlib.InvalidFileException, ValueError):
        return None


def find_projects(root: Path) -> dict[str, list[str]]:
    projects: dict[str, list[str]] = defaultdict(list)
    for path in root.rglob("*"):
        if skipped(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_dir() and path.suffix == ".xcodeproj":
            projects["Xcode projects"].append(relative)
        elif path.is_dir() and path.suffix == ".xcworkspace":
            projects["Xcode workspaces"].append(relative)
        elif path.is_file() and path.name in PROJECT_MARKERS:
            projects[PROJECT_MARKERS[path.name]].append(relative)
        elif path.is_file() and path.name == "package.json":
            text = read_text(path)
            if any(item in text for item in ("react-native", "expo", "@capacitor", "cordova")):
                projects["JavaScript mobile"].append(relative)
        elif path.is_file() and path.name == "ProjectVersion.txt" and "ProjectSettings" in path.parts:
            projects["Unity"].append(relative)
    return {key: sorted(set(values)) for key, values in projects.items()}


def collect_plists(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    info: list[dict[str, Any]] = []
    entitlements: list[dict[str, Any]] = []
    privacy: list[dict[str, Any]] = []
    for path in iter_files(root):
        if path.suffix not in {".plist", ".entitlements", ".xcprivacy"}:
            continue
        value = load_plist(path)
        if value is None:
            continue
        item = {"path": path.relative_to(root).as_posix(), "data": value}
        if path.suffix == ".entitlements":
            entitlements.append(item)
        elif path.suffix == ".xcprivacy":
            privacy.append(item)
        elif path.name == "Info.plist" or any(key in value for key in ("CFBundleIdentifier", "CFBundleDisplayName")):
            info.append(item)
    return info, entitlements, privacy


def collect_usage_descriptions(info_plists: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in info_plists:
        for key, value in item["data"].items():
            if key.startswith("NS") and key.endswith("UsageDescription") and str(value).strip():
                result[key].append({"path": item["path"], "value": str(value)})
    return dict(result)


def collect_build_settings(root: Path) -> dict[str, list[str]]:
    settings: dict[str, set[str]] = defaultdict(set)
    for path in iter_files(root):
        if path.name != "project.pbxproj":
            continue
        for key, value in BUILD_SETTING_RE.findall(read_text(path)):
            settings[key].add(value.strip().strip('"'))
    return {key: sorted(values) for key, values in settings.items()}


def collect_dependencies(root: Path) -> dict[str, list[str]]:
    dependencies: dict[str, set[str]] = defaultdict(set)
    for path in iter_files(root):
        if path.name == "Podfile.lock":
            for line in read_text(path).splitlines():
                match = re.match(r"\s{2}- ([A-Za-z0-9_+./-]+)(?:\s|\()", line)
                if match:
                    dependencies["CocoaPods"].add(match.group(1).split("/")[0])
        elif path.name == "Package.resolved":
            try:
                data = json.loads(read_text(path))
                pins = data.get("pins") or data.get("object", {}).get("pins") or []
                for pin in pins:
                    identity = pin.get("identity") or pin.get("package")
                    if identity:
                        dependencies["Swift Package Manager"].add(str(identity))
            except json.JSONDecodeError:
                pass
        elif path.name == "package.json":
            try:
                data = json.loads(read_text(path))
                for section in ("dependencies", "devDependencies"):
                    dependencies["JavaScript"].update((data.get(section) or {}).keys())
            except json.JSONDecodeError:
                pass
        elif path.name == "pubspec.lock":
            for line in read_text(path).splitlines():
                match = re.match(r"^  ([A-Za-z0-9_-]+):$", line)
                if match:
                    dependencies["Flutter"].add(match.group(1))
    return {key: sorted(values) for key, values in dependencies.items()}


def scan_source(root: Path) -> dict[str, Any]:
    signals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    urls: set[str] = set()
    domains: set[str] = set()
    patterns = {
        **{f"privacy:{key}": value for key, value in PRIVACY_PATTERNS.items()},
        **{f"required-reason-candidate:{key}": value for key, value in REQUIRED_REASON_PATTERNS.items()},
        **{f"feature:{key}": value for key, value in FEATURE_PATTERNS.items()},
        **{f"secret:{key}": value for key, value in SECRET_PATTERNS.items()},
    }
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        text = read_text(path)
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in patterns.items():
                if pattern.search(line):
                    signals[label].append({
                        "file": relative,
                        "line": number,
                        "excerpt": line.strip()[:180],
                    })
            for url in URL_RE.findall(line):
                cleaned = url.rstrip(").,;]")
                if "apple.com/DTDs/PropertyList" in cleaned:
                    continue
                urls.add(cleaned)
                parsed = urlparse(cleaned)
                if parsed.hostname:
                    domains.add(parsed.hostname)
    return {"signals": dict(signals), "urls": sorted(urls), "domains": sorted(domains)}


def privacy_manifest_summary(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in items:
        data = item["data"]
        summaries.append({
            "path": item["path"],
            "tracking": bool(data.get("NSPrivacyTracking")),
            "tracking_domains": data.get("NSPrivacyTrackingDomains") or [],
            "collected_data_count": len(data.get("NSPrivacyCollectedDataTypes") or []),
            "accessed_api_categories": [
                entry.get("NSPrivacyAccessedAPIType")
                for entry in data.get("NSPrivacyAccessedAPITypes") or []
                if isinstance(entry, dict) and entry.get("NSPrivacyAccessedAPIType")
            ],
        })
    return summaries


def audit(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    projects = find_projects(root)
    if not projects:
        errors.append("No Xcode or recognized cross-platform Apple app project was found.")

    info_plists, entitlements, privacy_manifests = collect_plists(root)
    usage = collect_usage_descriptions(info_plists)
    build_settings = collect_build_settings(root)
    dependencies = collect_dependencies(root)
    scan = scan_source(root)
    signals = scan["signals"]

    for feature, accepted_keys in USAGE_KEYS.items():
        if signals.get(f"privacy:{feature}") and not any(
            key in usage for key in accepted_keys
        ):
            errors.append(
                f"{feature}: code signal found but no parsed usage-description value "
                f"({', '.join(accepted_keys)}). "
                "Confirm generated Info.plist settings and target localization."
            )
    if signals.get("privacy:tracking"):
        if "NSUserTrackingUsageDescription" not in usage:
            warnings.append("Tracking/IDFA signal found without parsed NSUserTrackingUsageDescription.")
        if not any(item["data"].get("NSPrivacyTracking") for item in privacy_manifests):
            warnings.append("Tracking signal found but no privacy manifest declares NSPrivacyTracking=true.")

    reason_candidates = {
        label.split(":", 1)[1]
        for label in signals
        if label.startswith("required-reason-candidate:")
    }
    declared_reasons = {
        category
        for summary in privacy_manifest_summary(privacy_manifests)
        for category in summary["accessed_api_categories"]
    }
    missing_reason_categories = sorted(reason_candidates - declared_reasons)
    if missing_reason_categories:
        warnings.append(
            "Required-reason API candidates lack a matching parsed declaration: "
            + ", ".join(missing_reason_categories)
            + ". Confirm with Xcode's privacy report; do not guess reason codes."
        )

    if signals.get("feature:account-creation") and not signals.get("feature:account-deletion"):
        warnings.append("Account-creation signal found without an obvious in-app account-deletion path.")
    if signals.get("feature:storekit"):
        warnings.append("StoreKit signal found; verify products, restore flow, review assets, and agreements.")
    if any(url.startswith("http://") for url in scan["urls"]):
        warnings.append("Insecure HTTP URL found; verify ATS behavior and production transport security.")

    secret_files = [
        path.relative_to(root).as_posix()
        for path in iter_files(root)
        if SECRET_FILE_RE.search(path.name)
    ]
    if secret_files:
        errors.append("Private signing/key files found in repository scope: " + ", ".join(secret_files))
    signing_artifacts = [
        path.relative_to(root).as_posix()
        for path in iter_files(root)
        if SIGNING_ARTIFACT_RE.search(path.name)
    ]
    if signing_artifacts:
        warnings.append(
            "Signing/provisioning artifacts found; verify they belong outside Git: "
            + ", ".join(signing_artifacts)
        )
    secret_labels = sorted(label for label in signals if label.startswith("secret:"))
    if secret_labels:
        errors.append("Potential hardcoded secrets found: " + ", ".join(secret_labels))

    if reason_candidates and not privacy_manifests:
        warnings.append("Required-reason candidates found but no PrivacyInfo.xcprivacy was parsed.")
    if not privacy_manifests:
        warnings.append("No PrivacyInfo.xcprivacy was parsed; confirm whether every target/SDK is compliant.")
    if not info_plists:
        warnings.append("No parseable Info.plist found; modern generated settings require Xcode build inspection.")

    entitlement_summary = [
        {"path": item["path"], "keys": sorted(item["data"].keys())}
        for item in entitlements
    ]
    info_summary = [
        {
            "path": item["path"],
            "display_name": item["data"].get("CFBundleDisplayName"),
            "bundle_id": item["data"].get("CFBundleIdentifier"),
            "short_version": item["data"].get("CFBundleShortVersionString"),
            "build": item["data"].get("CFBundleVersion"),
            "non_exempt_encryption": item["data"].get("ITSAppUsesNonExemptEncryption"),
        }
        for item in info_plists
    ]
    return {
        "repository": str(root),
        "projects": projects,
        "build_settings": build_settings,
        "info_plists": info_summary,
        "usage_descriptions": usage,
        "entitlements": entitlement_summary,
        "privacy_manifests": privacy_manifest_summary(privacy_manifests),
        "dependencies": dependencies,
        "domains": scan["domains"],
        "signals": signals,
        "errors": errors,
        "warnings": warnings,
    }


def as_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# App Store repository audit",
        "",
        f"- Repository: `{report['repository']}`",
        "",
        "## Findings",
        "",
    ]
    if not report["errors"] and not report["warnings"]:
        lines.append("- No static findings.")
    lines.extend(f"- ERROR: {item}" for item in report["errors"])
    lines.extend(f"- WARNING: {item}" for item in report["warnings"])

    lines += ["", "## Project types", ""]
    if report["projects"]:
        for kind, paths in report["projects"].items():
            lines.append(f"- {kind}: " + ", ".join(f"`{path}`" for path in paths))
    else:
        lines.append("- None detected.")

    lines += ["", "## Build settings", ""]
    for key, values in report["build_settings"].items():
        lines.append(f"- `{key}`: " + ", ".join(f"`{value}`" for value in values))
    if not report["build_settings"]:
        lines.append("- No static Xcode build settings parsed.")

    lines += ["", "## Privacy manifests and permissions", ""]
    for manifest in report["privacy_manifests"]:
        lines.append(
            f"- `{manifest['path']}`: tracking={manifest['tracking']}, "
            f"collected-data entries={manifest['collected_data_count']}, "
            f"required-reason categories={len(manifest['accessed_api_categories'])}"
        )
    for key, entries in report["usage_descriptions"].items():
        for entry in entries:
            lines.append(f"- `{key}` in `{entry['path']}`: {entry['value']}")
    if not report["privacy_manifests"] and not report["usage_descriptions"]:
        lines.append("- No parsed privacy manifest or usage description.")

    lines += ["", "## Dependencies", ""]
    for manager, values in report["dependencies"].items():
        lines.append(f"- {manager}: " + ", ".join(f"`{value}`" for value in values))
    if not report["dependencies"]:
        lines.append("- None parsed from supported lock/manifests.")

    lines += ["", "## Network domains", ""]
    lines.extend(f"- `{domain}`" for domain in report["domains"])
    if not report["domains"]:
        lines.append("- None detected statically.")

    lines += ["", "## Code signals", ""]
    for label, matches in sorted(report["signals"].items()):
        lines.append(f"### {label} ({len(matches)})")
        lines.append("")
        for match in matches[:12]:
            lines.append(
                f"- `{match['file']}:{match['line']}` — `{match['excerpt']}`"
            )
        if len(matches) > 12:
            lines.append(f"- … {len(matches) - 12} more")
        lines.append("")

    lines += [
        "## Next steps",
        "",
        "- Generate an Xcode privacy report from the exact Release archive.",
        "- Compare every dependency and backend recipient with App Privacy answers.",
        "- Verify current Xcode/SDK upload requirements and process the target build.",
        "- Test review credentials, permissions, purchases, restore, and account deletion.",
        "- Validate screenshots, metadata, support/privacy URLs, age rating, and export compliance.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.repository).expanduser().resolve()
    if not root.is_dir():
        print(f"Repository not found: {root}", file=sys.stderr)
        return 2
    report = audit(root)
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.json else as_markdown(report)
    )
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
