---
name: app-store-release-kit
description: "Audit an Apple-platform app repository and produce a complete App Store release kit: original app icon, product README, localized iPhone/iPad/Mac screenshots, optional app previews, App Store Connect metadata, App Privacy answers, privacy policy, review notes, demo-account path, TestFlight notes, age-rating and export-compliance checklist, release notes, and build-upload readiness report. Use when a user asks to prepare, redesign, validate, submit, review, upload, release, or publish an iOS, iPadOS, macOS, tvOS, visionOS, or watchOS app from a local folder or Git repository."
---

# App Store Release Kit

Turn an Apple-platform app repository into a source-ready, product-page-ready, privacy-ready, and review-ready delivery. Treat source behavior and the uploaded build as truth. Preserve user changes and involve the user in brand decisions.

## Start here

1. Identify the implementation: Xcode/Swift, React Native, Flutter, Capacitor/Cordova, Expo, Unity, or another framework.
2. Locate `.xcodeproj`, `.xcworkspace`, targets, bundle identifiers, schemes, `Info.plist`, entitlements, asset catalogs, `PrivacyInfo.xcprivacy`, dependency manifests, and build commands.
3. Read [references/apple-official-spec.md](references/apple-official-spec.md). Recheck the linked official pages and current App Store Connect fields before a live submission.
4. Run:

   ```bash
   python3 scripts/audit_app_store.py /absolute/path/to/repository
   ```

5. Inspect Git status, real user flows, supported devices and orientations, SDKs, data collection, permissions, login, purchases, account deletion, backend availability, localization, and existing brand assets.
6. State proposed files before material visual or compliance changes. Do not upload a build, add testers, submit for review, release, change pricing/availability, publish privacy answers, or expose credentials without explicit authorization.

## Keep three delivery layers separate

### Repository

Keep these with source:

- application source, tests, Xcode/framework configuration, asset catalogs, and in-product icons
- valid `Info.plist`, entitlements, and target-linked `PrivacyInfo.xcprivacy`
- `README.md`, `PRIVACY_POLICY.md`, support and license information
- `.gitignore` rules for archives, DerivedData, signing files, API keys, local environment, and credentials

Never commit App Store Connect `.p8` keys, signing certificates, provisioning profiles, passwords, session cookies, production secrets, or personal review/test data.

### Release-assets package

Default to `<repository>/release-assets/`:

```text
release-assets/
├── source/
├── brand/
│   └── app-icon-master.png
├── screenshots/
│   ├── zh-Hans/iphone-6.9/
│   └── zh-Hans/ipad-13/
├── previews/
├── metadata/
│   └── zh-Hans/metadata.json
├── review/
│   ├── review-notes.md
│   └── reviewer-test-paths.md
├── privacy/
│   ├── app-privacy-matrix.md
│   └── PRIVACY_POLICY.md
├── testflight/
│   └── test-information.md
├── release/
│   └── release-notes.md
├── asset-spec.json
└── submission-checklist.md
```

Initialize without overwriting existing files:

```bash
python3 scripts/init_release_assets.py /absolute/path/to/repository
```

### Build and platform state

App Store Connect receives a signed build, not the repository or release-assets folder.

- Build the exact Release configuration intended for distribution.
- Associate the uploaded build by bundle ID, version, and build string.
- Upload only through an authorized Apple workflow such as Xcode, Transporter, `altool`, Xcode Cloud, or App Store Connect API tooling.
- Keep signing and API credentials outside Git.
- Treat build upload, TestFlight distribution, Add for Review, Submit for Review, and release as separate consequential actions.

## Workflow

### 1. Establish product truth

- Identify target users, core task, inputs, processing, outputs, supported platforms, minimum OS, and device classes.
- Map every screenshot and claim to a working state in the target build.
- Record login, account creation, subscriptions, IAP, ads, tracking, UGC, health, finance, location, camera, microphone, Bluetooth, background modes, extensions, and hardware dependencies.
- Do not advertise unfinished behavior, fake prices, unconfigured IAP, or unavailable backend features.

### 2. Audit source and distribution configuration

Read [references/privacy-and-review.md](references/privacy-and-review.md).

- Reconcile bundle IDs, marketing versions, build numbers, deployment targets, schemes, signing entitlements, and App Store Connect records.
- Verify permission usage descriptions match the visible user-triggered purpose.
- Inspect all first- and third-party SDKs, privacy manifests, required-reason API categories, tracking domains, analytics, ads, crash reporting, and data recipients.
- Flag ATS exceptions, insecure URLs, private keys, hardcoded secrets, production personal data, undocumented URL schemes, private API risk, and missing target membership.
- Check account deletion, Sign in with Apple where applicable, StoreKit products, restore purchases, subscription management, and export-compliance answers.
- Use Xcode's generated privacy report and uploaded-build processing messages as final authorities; static scanning is only an aid.

### 3. Co-create the app icon

Read [references/visual-production.md](references/visual-production.md).

- Audit existing brand assets and trademark/copycat risk.
- Present three original directions with motif, palette, personality, small-size behavior, and light/dark/tinted appearance strategy.
- Ask the user to select or combine a direction before replacing approved icon assets.
- Produce a 1024×1024 master for iOS/iPadOS/macOS, then integrate through Icon Composer or the target asset catalog as the project requires.
- Do not pre-round the master or copy Apple/third-party product marks.
- Validate the icon in Home Screen, Settings, Spotlight, notification, TestFlight, and App Store contexts.

Icon approval pauses replacement, not auditing, metadata, privacy work, or screenshot planning.

### 4. Write the README

Use `$readme-header-hook` when available. Use [assets/app-store-readme-template.md](assets/app-store-readme-template.md) only when the repository has no established style.

Include value proposition, representative screenshots, supported platforms, prerequisites, build/test steps, configuration without secrets, privacy/permission notes, IAP or backend setup where relevant, limitations, support, and license.

### 5. Produce localized screenshots

- Capture real app states using representative synthetic data.
- Default to 3–5 strong frames per required device class and localization; Apple accepts 1–10.
- Lead with product value, then primary action, result, and differentiators.
- Use the actual UI as the visual evidence. Overlays may explain real functionality but must not imply unsupported behavior.
- Avoid a set made only of splash, login, title art, or decorative posters.
- Keep orientation and dimensions consistent within each device set.
- Remove alpha/transparency from screenshot PNGs.
- If the app runs on iPad, provide the required current iPad screenshot class rather than stretching iPhone artwork.
- Record current accepted pixel sizes in `asset-spec.json`; never rely solely on remembered device names.

Validate with:

```bash
python3 scripts/validate_release_assets.py \
  /absolute/path/to/repository/release-assets
```

### 6. Prepare App Store Connect metadata

Start from [assets/metadata.template.json](assets/metadata.template.json) and [assets/review-notes-template.md](assets/review-notes-template.md).

Prepare per localization:

- name, subtitle, promotional text, description, keywords, What's New
- support URL, marketing URL, privacy policy URL, and privacy choices URL
- primary/secondary category and content-rights notes
- age-rating questionnaire evidence
- pricing/availability assumptions
- copyright, version, and release option
- App Review contact, notes, attachments, login/demo account, hardware, QR/sample content, and feature paths

Validate stable text limits:

```bash
python3 scripts/validate_metadata.py \
  /absolute/path/to/repository/release-assets/metadata/zh-Hans/metadata.json
```

The live platform remains authoritative for conditional fields and limits.

### 7. Align privacy across code, manifests, labels, and policy

- Build the matrix in [assets/app-privacy-matrix-template.md](assets/app-privacy-matrix-template.md).
- Include data collected by the app and every third-party partner.
- For each data type record purpose, linked/not linked, tracking/not tracking, recipient, retention, deletion, user trigger, permission, and corresponding App Store Connect response.
- Reconcile the matrix with `PrivacyInfo.xcprivacy`, Xcode's privacy report, ATT behavior, permission prompts, backend logs, analytics dashboards, and the hosted privacy policy.
- Do not claim “data not collected” merely because an SDK or processor receives it.
- If accounts can be created, verify users can initiate full account deletion inside the app and understand subscription consequences.
- Host the final privacy policy at a public HTTPS URL; a repository file alone does not satisfy the App Store field.

### 8. Prepare TestFlight and review access

- Use [assets/testflight-template.md](assets/testflight-template.md) for beta description, feedback email, and What to Test.
- Use [assets/reviewer-test-paths-template.md](assets/reviewer-test-paths-template.md) for deterministic review steps.
- Provide an active demo account or a complete demo mode for gated features.
- Keep the backend, sample content, review account, IAP, and external hardware available throughout review.
- Explain non-obvious features and every new or changed capability specifically.
- Test clean install, upgrade, offline/error paths, denied permissions, account deletion, purchase/restore, and all supported device classes.

### 9. Verify submission readiness

Confirm:

- active Apple Developer Program membership, agreements, banking/tax where applicable, App Store Connect roles, certificates, identifiers, profiles, and capabilities
- current Xcode/SDK minimum from Apple's Upcoming Requirements page
- build archive and validation with no unresolved upload warnings
- complete screenshots, metadata, privacy answers, age rating, export compliance, content rights, support/privacy URLs, and build selection
- functional review credentials and reachable services
- IAP/subscriptions or other review items added to the correct submission
- manual, automatic, phased, or scheduled release choice
- territory-specific filings or qualifications, including mainland China information when applicable

### 10. Finish only after validation

Run repository lint, unit/UI tests, production archive, device tests, Xcode privacy report, asset validation, metadata validation, secret scan, and Git diff review. Finish when the user receives clickable local paths, remaining dashboard-only actions, and clear separation between prepared, uploaded, submitted, approved, and released states.

## Additional deliverables

Offer when relevant:

- App Preview video and poster-frame plan
- custom product page and product page optimization variants
- In-App Event or promoted IAP artwork/copy
- accessibility nutrition-label evidence
- localization QA and screenshot sets
- privacy-policy/support website
- App Store Connect API or Fastlane metadata automation
- TestFlight rollout plan, phased release, rollback, and incident checklist
- reviewer walkthrough diagram and rejection-response draft

