---
name: wechat-miniprogram-store-kit
description: "Audit a WeChat Mini Program repository and produce a complete release kit: original app icon, product README, 3–5 real screenshots, optional share cards and Mini Program code posters, platform profile and review copy, privacy declaration matrix, privacy policy, server-domain and qualification checklist, reviewer test paths, release notes, and upload-readiness report. Use when a user asks to prepare, redesign, validate, submit, review, upload, release, or publish a 微信小程序 from a local folder or Git repository."
---

# WeChat Mini Program Store Kit

Turn a Mini Program repository into a source-ready, review-ready, and release-ready delivery. Use actual behavior as the source of truth, preserve user changes, and involve the user in brand decisions.

## Start here

1. Locate `project.config.json`, determine `miniprogramRoot`, and locate the corresponding `app.json`.
2. Distinguish native Mini Program source from generated output such as `dist/`, `miniprogram/`, or framework builds.
3. Read [references/wechat-official-spec.md](references/wechat-official-spec.md). Recheck the linked official documents and the current management dashboard before a live submission.
4. Run:

   ```bash
   python3 scripts/audit_miniprogram.py /absolute/path/to/repository
   ```

5. Inspect Git status, build commands, real user flows, network calls, privacy APIs, service categories, plugins, cloud functions, tab bar icons, CI settings, and current README.
6. State the proposed files and locations before making material visual or compliance changes. Do not upload code, submit review, release, change account settings, or expose credentials without explicit authorization.

## Separate the three deliverable layers

### Repository files

Keep these with the source repository:

- Mini Program source and build configuration
- `project.config.json`, `app.json`, pages, components, and runtime assets
- tab bar and in-product icons referenced by `app.json`
- `README.md`
- `PRIVACY_POLICY.md`
- `.gitignore` entries for upload keys, local private config, logs, and secrets
- license and support information when applicable

Never commit AppSecret, access tokens, CI upload private keys, personal test data, or production credentials.

### Release-assets package

Default to `<repository>/release-assets/`:

```text
release-assets/
├── source/                          # Editable brand and layout masters
├── brand/
│   └── app-icon.png
├── screenshots/
│   ├── screenshot-01-home.png
│   ├── screenshot-02-core-flow.png
│   └── screenshot-03-result.png
├── promotion/
│   ├── share-card.png               # Optional; use live platform ratio
│   └── miniprogram-code-poster.png  # Optional after code is available
├── review/
│   ├── submission.md
│   ├── privacy-declaration-matrix.md
│   └── reviewer-test-paths.md
├── privacy/
│   └── PRIVACY_POLICY.md
├── release/
│   └── release-notes.md
├── asset-spec.json
└── submission-checklist.md
```

Initialize it without overwriting existing files:

```bash
python3 scripts/init_release_assets.py /absolute/path/to/repository
```

### Upload target

WeChat uploads the compiled Mini Program project through WeChat DevTools or `miniprogram-ci`; it is not normally a manually assembled store ZIP.

- Use the exact directory containing the upload `app.json`.
- Run the repository build first when `miniprogramRoot` points to generated output.
- Preview the exact build on a real device before upload.
- Keep the code-upload private key outside the repository.
- Record version and release notes separately from source versioning.

## Workflow

### 1. Establish product truth

- Identify the target user, main entry, primary task, input, processing, and visible result.
- Map every screenshot and review statement to an implemented page.
- Record login, payment, membership, location, camera, media, Bluetooth, health, UGC, and other gated flows.
- Do not depict unfinished functions or production data.

### 2. Audit code and platform dependencies

- Parse project configuration and resolve `miniprogramRoot`.
- Check all declared pages, subpackages, plugins, permissions, tab bar assets, workers, and required private information.
- Measure main-package, subpackage, and total source sizes; use DevTools or CI output as the final package-size authority.
- List network domains and reconcile them with configured request, upload, download, and WebSocket domains.
- Flag HTTP, localhost, direct IP, `api.weixin.qq.com` client calls, hardcoded AppSecret, access tokens, upload private keys, and private test credentials.
- Identify third-party SDKs, plugins, analytics, cloud functions, storage, payment, and content moderation.

### 3. Co-create the app icon

Read [references/visual-production.md](references/visual-production.md).

- Audit existing brand assets and trademark risks.
- Present three original directions with motif, palette, personality, and small-size behavior.
- Ask the user to select or combine a direction before replacing approved assets.
- Prefer original image generation when available; never copy the WeChat logo or another Mini Program's icon.
- Export a high-resolution master plus the exact format and dimensions requested by the current management dashboard.
- Keep tab bar icons visually related but optimized separately for active/inactive states.

Icon approval pauses replacement, not auditing, copywriting, or compliance preparation.

### 4. Write the README

Use `$readme-header-hook` when available. Start from [assets/miniprogram-readme-template.md](assets/miniprogram-readme-template.md) only when the repository has no established style.

Include:

- concrete value proposition
- screenshots or a short result example
- prerequisites and DevTools setup
- local build, preview, and test commands
- environment-variable and domain setup without secrets
- project structure only when useful
- privacy and permission notes
- honest limitations, support, and license

Do not publish AppID-linked credentials, internal endpoints, or test accounts in a public README.

### 5. Capture 3–5 real screenshots

Use representative synthetic data and real Mini Program pages:

1. home and value proposition
2. primary user action
3. core result
4. secondary capability or customization
5. account, export, order, or completion state when genuinely supported

Prefer screenshots from DevTools or a real phone at a consistent device size. Do not expose WeChat chats, personal avatars, phone numbers, openids, addresses, orders, tokens, or production accounts.

If the management dashboard specifies exact dimensions, write them into `release-assets/asset-spec.json` and validate against them. Do not infer Chrome Web Store dimensions.

### 6. Prepare platform profile and review fields

Start from [assets/submission-template.md](assets/submission-template.md). Prepare paste-ready content for:

- Mini Program name, short introduction, detailed function description, and tags
- service-category recommendation and required qualifications
- main function pages and screenshot mapping
- version number and upload/release notes
- test entry path, test data, reviewer steps, and special instructions
- login, membership, payment, geographic, hardware, or account prerequisites
- support and customer-service routes
- content-safety and UGC moderation explanation when applicable

The live submission page is authoritative for exact fields and length limits.

### 7. Align privacy declarations with code

Read [references/privacy-and-review.md](references/privacy-and-review.md).

- Build a matrix from each privacy API/component to the personal information handled, user trigger, purpose, processing location, recipient, retention, deletion route, and management-dashboard declaration.
- Confirm the dashboard's 《小程序用户隐私保护指引》 declares every handled information type.
- Verify privacy authorization appears before restricted API/component use.
- Check `wx.getPrivacySetting`, `wx.openPrivacyContract`, `agreePrivacyAuthorization`, and related flows where applicable.
- Write `PRIVACY_POLICY.md` from [assets/privacy-policy-template.md](assets/privacy-policy-template.md).
- Cover account deletion and data deletion where user accounts or retained personal data exist.
- Make third-party SDKs, plugins, cloud services, analytics, payment, maps, and customer service explicit.

Do not claim “no data collection” merely because data is processed by a cloud provider or third-party SDK.

### 8. Verify account, domain, and release readiness

Confirm:

- account subject, administrator, developer, and experience-member access
- certification, service category, required qualifications, and applicable filing status
- HTTPS/WSS server domains and valid certificates
- privacy guide, customer service, complaint, and deletion routes
- content-security or UGC moderation when needed
- payment and merchant configuration when needed
- stable experience version and reviewer test path
- upload key and IP allowlist configuration outside Git
- version number, notes, preview, upload, review, and release authorization

Uploading, submitting review, full release, and staged release are separate consequential actions. Obtain authorization for each action the user asks Codex to perform.

### 9. Validate

Run:

```bash
python3 scripts/validate_release_assets.py \
  /absolute/path/to/repository/release-assets
```

Also:

- run repository lint, tests, and production build
- preview the exact upload target on a real device
- test privacy consent denied, accepted, and changed-policy paths
- test clean install, login/logout, network failure, empty data, and permission denial
- confirm DevTools does not depend on “不校验合法域名”
- inspect package-size output from DevTools or `miniprogram-ci`
- scan for secrets and production personal data
- verify README, review copy, privacy policy, dashboard declarations, and code agree
- inspect Git diff and avoid unrelated files

## Additional deliverables

Offer these when relevant:

- share card, launch campaign image, and Mini Program code poster
- localized copy and screenshots
- reviewer path diagram or annotated walkthrough
- experience-version QR delivery
- release/rollback plan and staged-release checklist
- accessibility, low-end-device, dark-mode, and network-degradation checks
- content-safety and user-reporting flow
- API/domain inventory and backend data-flow diagram
- privacy-policy hosting page
- automated `miniprogram-ci` preview/upload workflow with secrets kept in CI

## Completion standard

Finish only when:

- the app icon is approved and exact live-dashboard requirements are recorded
- 3–5 accurate screenshots exist
- review fields and reviewer steps are paste-ready
- privacy declarations match every sensitive API and data flow
- domains, qualifications, and account prerequisites are documented
- the exact upload build passes tests and real-device preview
- no AppSecret, upload key, access token, or personal test data is committed
- the user receives clickable local paths and a clear list of remaining dashboard-only actions

