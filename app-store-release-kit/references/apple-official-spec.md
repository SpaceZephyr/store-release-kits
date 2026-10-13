# Apple App Store release reference

Last checked: 2026-07-24. Recheck these official pages and the target App Store Connect record before every live submission.

## Official sources

- [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [App information fields](https://developer.apple.com/help/app-store-connect/reference/app-information/app-information)
- [Platform version information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information)
- [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)
- [Upload previews and screenshots](https://developer.apple.com/help/app-store-connect/manage-app-information/upload-app-previews-and-screenshots/)
- [App preview specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/app-preview-specifications/)
- [App icon guidance](https://developer.apple.com/design/human-interface-guidelines/app-icons)
- [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy)
- [App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/)
- [Privacy manifest files](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files)
- [Required-reason APIs](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api)
- [Third-party SDK requirements](https://developer.apple.com/support/third-party-SDK-requirements/)
- [Account deletion](https://developer.apple.com/support/offering-account-deletion-in-your-app/)
- [Age-rating values](https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions/)
- [Upcoming requirements](https://developer.apple.com/news/upcoming-requirements/)
- [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/)
- [TestFlight overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview)
- [Submit an app](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app/)

## Product-page fields

Current stable limits:

| Field | Limit / rule |
| --- | --- |
| Name | 2–30 characters |
| Subtitle | Up to 30 characters |
| Promotional text | Up to 170 characters |
| Description | Up to 4,000 characters, plain text |
| Keywords | Up to 100 bytes; don't repeat app/company names or use other brands |
| Screenshots | 1–10 per required device set and localization |
| App previews | Optional, up to 3 per device size and language |

The Support URL must provide a genuine way to contact the developer. A Privacy Policy URL is required. Conditional fields, localization behavior, status editability, and regional fields remain governed by the live record.

## Current screenshot baseline

Screenshots accept `.jpeg`, `.jpg`, and `.png`. They cannot contain alpha channels or transparency.

Common current primary sets:

- iPhone 6.9": one of 1260×2736, 1290×2796, or 1320×2868 portrait; landscape is the reverse
- iPhone 6.5" fallback: 1284×2778 or 1242×2688 portrait; landscape is the reverse
- iPad 13": 2064×2752 or 2048×2732 portrait; landscape is the reverse
- Mac: 1280×800, 1440×900, 2560×1600, or 2880×1800
- Apple TV: 1920×1080 or 3840×2160
- Apple Vision Pro: 3840×2160

Apple can change supported models and accepted sizes. Copy exact values from the current specification into `release-assets/asset-spec.json`.

## App icon

For iOS, iPadOS, and macOS, the current Human Interface Guidelines specify a 1024×1024 square layout. The system applies its mask. Use Icon Composer or an asset catalog and validate supported appearances. Other platforms use different layouts, including tvOS parallax, visionOS circular 3D treatment, and watchOS circular presentation.

## App Preview

Current App Preview rules include:

- 15–30 seconds
- maximum 500 MB
- H.264 or ProRes 422 HQ
- up to 30 fps
- accepted extensions depend on codec (`.mov`, `.m4v`, `.mp4`)
- video should primarily be captured app behavior, with narration or overlays only to clarify

## Privacy

App privacy answers apply at the app level across platforms and must include the practices of integrated third parties. A privacy policy URL is required. A privacy choices URL is optional.

`PrivacyInfo.xcprivacy` describes collected data, tracking domains, and required-reason API categories. Xcode combines app and SDK manifests into a privacy report. Every executable or dynamic library using a required-reason API needs an accurate declaration in its own bundle. Never invent an approved reason code; choose only the current official value matching actual use.

If the app supports account creation, it must let users initiate deletion of the complete account inside the app. Temporary deactivation alone is insufficient.

## Review and release

Apple's pre-submission guidance requires:

- a tested final build with complete and accurate metadata
- full reviewer access through an active demo account or complete demo mode
- live and accessible backend services
- specific notes for non-obvious features and IAP

Upload processing, TestFlight distribution, Add for Review, Submit for Review, approval, and release are separate states/actions. App versions are submitted separately by platform.

## Toolchain

As of the last check, Apple's Upcoming Requirements page states that uploads since 2026-04-28 must use Xcode 26 or later with the corresponding 26-series platform SDK. Never freeze this in automation without rechecking the official page.

## Regional and business checks

Verify current agreements, roles, tax/banking, pricing, territories, trader status, encryption/export questions, content rights, regulated services, and filing requirements. For mainland China distribution, reconcile the required filing/qualification information with App Store Connect and the app's legal entity.

