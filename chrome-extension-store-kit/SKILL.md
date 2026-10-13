---
name: chrome-extension-store-kit
description: "Audit a Chrome browser extension repository and produce a complete Chrome Web Store submission kit: original multi-size icons, product README, 3–5 screenshots, 440x280 and 1400x560 promotional tiles, store listing copy, permission and host-access justifications, privacy policy, release package, and submission checklist. Use when a user asks to prepare, redesign, validate, package, or publish a Chrome extension or browser plugin from a local folder or Git repository."
---

# Chrome Extension Store Kit

Turn an extension repository into a review-ready source package, store-assets package, and release ZIP. Preserve existing work, use real product behavior as the source of truth, and involve the user in visual identity decisions.

## Start here

1. Locate the extension root and `manifest.json`. If several manifests exist, identify development and built variants; ask only when the intended upload target remains ambiguous.
2. Read [references/chrome-web-store-spec.md](references/chrome-web-store-spec.md). Recheck the linked official documentation when the user is actively submitting because Store requirements can change.
3. Run:

   ```bash
   python3 scripts/audit_extension.py /absolute/path/to/extension
   ```

4. Inspect the extension UI, purpose, permissions, host matches, data flows, existing brand assets, README, tests, build process, and Git status.
5. State the proposed deliverables and where they will be written. Do not push, publish, change repository visibility, or overwrite approved branding unless the user requests it.

## Separate the three deliverable layers

### Repository files

Keep these with the source repository:

- `manifest.json` and runtime source
- `icons/icon16.png`, `icon32.png`, `icon48.png`, and `icon128.png`
- editable master icon or design source outside the upload ZIP
- `README.md`
- `PRIVACY_POLICY.md`
- license and support information when applicable

### Store-assets package

Default to `<extension-root>/store-assets/` unless the repository already has a convention:

```text
store-assets/
├── source/                         # Editable masters and design sources
├── icons/
│   └── store-icon-128.png
├── screenshots/
│   ├── screenshot-01-overview-1280x800.png
│   ├── screenshot-02-core-action-1280x800.png
│   └── screenshot-03-result-1280x800.png
├── promo/
│   ├── small-promo-440x280.png
│   └── marquee-promo-1400x560.png
├── listing/
│   ├── store-listing-zh-CN.md
│   ├── permission-justifications.md
│   └── release-notes.md
├── privacy/
│   └── PRIVACY_POLICY.md
└── submission-checklist.md
```

Initialize the structure and templates when useful:

```bash
python3 scripts/init_store_assets.py /absolute/path/to/extension
```

### Upload package

Create a clean ZIP containing only runtime files needed by the extension. Exclude Git data, `node_modules`, tests, caches, raw design files, screenshots, store promotional assets, secrets, and development-only material. Validate the unpacked directory in Chrome before zipping. Do not assume the repository root is the runtime package when a build step exists.

## Workflow

### 1. Establish product truth

- Derive the single purpose from actual behavior, not marketing wishes.
- Identify the primary user, trigger action, input, transformation, and output.
- Record unsupported or unfinished features; do not depict them in screenshots or copy.
- Minimize permissions before writing justifications. Remove a permission only after confirming it is unused and testing the extension.

### 2. Co-create the icon

Read [references/visual-production.md](references/visual-production.md).

- Audit existing icons, product motifs, color palette, and trademark risks.
- Present three clearly different original directions with motif, palette, personality, and small-size behavior.
- Ask the user to choose or combine a direction before replacing plugin icons.
- Prefer an image-generation tool for original exploration when available; do not copy a third-party logo or recognizable brand mark.
- Test the selected design at 16, 32, 48, and 128 px. Simplify details that disappear or blur.
- Export consistent PNGs and update `manifest.json` paths. Preserve an editable high-resolution source separately.

Any icon approval pauses the replacement step, not the rest of the audit or copy preparation.

### 3. Write the README

Use the repository's established documentation style. If none exists, start from [assets/extension-readme-template.md](assets/extension-readme-template.md) and produce a polished product page with:

- concise value proposition
- feature list grounded in the code
- install from Chrome Web Store and local unpacked-install instructions
- usage flow
- permission explanation
- privacy-policy and support links
- development/build instructions when present
- license status

Do not claim a public store URL before one exists.

### 4. Capture 3–5 screenshots

Use real extension UI and representative synthetic data. Never expose private tabs, accounts, tokens, personal documents, or browser chrome that is irrelevant to the product.

Recommended sequence:

1. overview and value proposition
2. primary action or configuration
3. generated result or completed workflow
4. secondary feature or customization
5. export/share state when genuinely supported

Use 1280x800 by default. Promotional framing may add concise captions and branding, but the represented UI must remain accurate. Use browser or Chrome control tools to exercise the real extension before capture.

### 5. Produce promotional tiles

- Small tile: 440x280, one visual idea, recognizable icon, minimal copy.
- Marquee tile: 1400x560, spacious composition, primary benefit, consistent brand.
- Export JPEG or non-alpha 24-bit PNG.
- Flatten transparency and verify exact dimensions.
- Do not use ratings, unsupported awards, misleading controls, excessive text, or trademarked browser/product logos without permission.

### 6. Prepare store copy and review fields

Start from [assets/store-listing-template.md](assets/store-listing-template.md). Provide copy that can be pasted directly into the Developer Dashboard:

- package title and summary review
- detailed description
- category and language recommendation
- single-purpose statement
- one justification per requested permission
- host-permission justification
- remote-code declaration and explanation
- data-use disclosures and Limited Use confirmation
- homepage, support, privacy-policy, and repository URLs
- reviewer test instructions if login or setup is required
- release notes

Read [references/review-and-privacy.md](references/review-and-privacy.md) before writing compliance text.

### 7. Write and host the privacy policy

Start from [assets/privacy-policy-template.md](assets/privacy-policy-template.md), then make every statement match the code audit.

- Cover collected/accessed data, purpose, processing location, storage, retention, deletion, sharing, third parties, security, permissions, host access, remote code, policy changes, and contact.
- Add `PRIVACY_POLICY.md` to the repository for maintenance.
- Provide a stable public HTTPS URL for the Store. Verify it without authentication.
- Never make a repository public or deploy a site without user authorization.

### 8. Validate

Run:

```bash
python3 scripts/validate_store_assets.py /absolute/path/to/extension/store-assets
```

Also:

- parse `manifest.json`
- syntax-check JavaScript or run the repository's test/build commands
- load the unpacked build in Chrome and exercise core flows
- scan for secrets and remote executable code
- confirm requested permissions match actual use
- verify all images, copy, and privacy statements agree
- inspect the final ZIP contents before upload
- check Git diff and avoid unrelated files

## Additional deliverables

Offer these when relevant:

- version bump and clean release ZIP
- localized listing copy and localized screenshots
- changelog or Store release notes
- homepage/support page and issue-reporting route
- reviewer credentials or test instructions handled securely
- license, font, image, and trademark provenance review
- optional YouTube promo-video storyboard
- migration notes for other browser stores; do not reuse Chrome-specific claims without checking their rules

## Completion standard

Finish only when:

- all required files exist at exact dimensions and formats
- icons are approved and readable at 16 px
- at least three accurate screenshots are ready
- store fields are paste-ready
- privacy claims match permissions and data flows
- the runtime package passes validation and contains no store-only assets
- the user receives clickable local paths plus any verified public policy/support URLs
