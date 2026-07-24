# Privacy and review workflow

## Evidence sources

Build one evidence table from:

- source code and configuration
- `Info.plist`, entitlements, `PrivacyInfo.xcprivacy`, and Xcode privacy report
- dependency locks and third-party SDK documentation
- network endpoints, backend processing, logs, analytics, ads, and customer-support systems
- App Store Connect privacy answers
- permission prompts, consent/ATT flow, privacy policy, and deletion behavior

Static code scanning cannot prove the absence of collection or tracking.

## App Privacy matrix

For every collected data type, record:

| Evidence | Data type | Collected by | Purpose | Linked | Tracking | Retention | Deletion | Store answer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

“Collected by” must cover the developer and each third-party partner. “Linked” and “tracking” use Apple's definitions, not informal product language.

Check at least:

- contact information, health/fitness, financial information, location, sensitive information
- contacts, user content, browsing/search history, identifiers, purchases
- usage data, diagnostics, environment scanning, hands/head, other data

Purposes may include third-party advertising, developer advertising/marketing, analytics, personalization, app functionality, and other purposes.

## Permission descriptions

Every protected-resource prompt must:

- describe the concrete user benefit
- appear immediately before or during a user-triggered flow
- match the actual API and data use
- avoid vague text such as “needed for better experience”
- be localized where the app is localized

Check camera, photos, microphone, location, contacts, calendars/reminders, Bluetooth, local network, motion, speech, Face ID, health, HomeKit, media library, tracking, and other platform-specific resources.

## Required-reason APIs

Treat static matches as candidates. Confirm in Xcode's privacy report and official API-category documentation.

Common categories include file timestamps, system boot time, disk space, active keyboards, and user defaults. For each category:

1. identify the exact first- or third-party caller
2. verify the feature and on/off-device behavior
3. choose only a currently approved reason that exactly matches
4. add it to the correct target/framework `PrivacyInfo.xcprivacy`
5. rebuild the privacy report

Do not use a reason code merely because another app or template used it.

## Tracking and ATT

- Determine whether app or third-party data is linked with third-party data for targeted ads/measurement or shared with a data broker.
- If tracking occurs, reconcile App Store Connect answers, `NSPrivacyTracking`, tracking domains, `NSUserTrackingUsageDescription`, and the ATT request.
- Do not gate unrelated functionality on tracking permission.
- Do not fingerprint, even with user tracking permission.

## Accounts and Sign in with Apple

If users can create accounts:

- provide an easy-to-find in-app path to initiate full account deletion
- describe timing, retained legal records, UGC deletion, and confirmation
- clarify subscription cancellation and billing
- revoke Sign in with Apple tokens where used

If a third-party/social login is used for the primary account, evaluate current Sign in with Apple requirements and exceptions.

## Purchases and subscriptions

- Use supported Apple purchase mechanisms when required.
- Configure products, pricing, localization, review screenshots, and agreements.
- Make paywalls and screenshots clear about paid content.
- Test purchase, pending, failure, restore, upgrade/downgrade, cancellation, refund, expiration, and family sharing as applicable.
- Keep review products visible and explain any conditional availability.

## Review notes

Write deterministic steps:

1. launch state and prerequisite
2. demo credentials or demo mode
3. exact taps/navigation
4. expected result
5. permission, purchase, hardware, region, QR, or sample-data needs
6. contact who can answer quickly

Disclose significant changes, non-obvious features, background behavior, regulated content, and reasons for unusual entitlements. Never put production credentials or customer data in notes.

## Common rejection prevention

- final build, no placeholders or dead links
- no crashes, hidden/dormant behavior, copycat assets, or misleading metadata
- screenshots show real use, not only title/login/splash
- complete reviewer access and live backend
- correct privacy labels, permission strings, manifests, SDK signatures, and account deletion
- functional IAP and restore behavior
- adequate native functionality rather than a thin website wrapper
- accurate age rating, content rights, moderation/report/block flows for UGC
- support and privacy URLs load publicly over HTTPS

