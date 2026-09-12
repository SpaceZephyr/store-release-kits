# Privacy and review guide

## Build the evidence map

| Evidence | Inspect |
|---|---|
| `project.config.json` | AppID, upload root, compile type, plugins, private local settings |
| `app.json` | pages, subpackages, `permission`, `requiredPrivateInfos`, plugins, tab bar |
| source | privacy APIs/components, network calls, storage, login, payment, SDKs |
| backend/cloud | personal data, recipients, storage region, retention, deletion |
| dashboard | privacy guide, service category, domains, qualifications, reviewer fields |

## Privacy declaration matrix

For each API, component, SDK, or backend flow, record:

1. personal information handled
2. user-visible trigger
3. purpose and necessity
4. whether data leaves the device
5. backend or third-party recipient
6. retention period
7. deletion/account-cancellation route
8. dashboard declaration
9. privacy-policy section
10. test result for consent denied and accepted

Do not infer dashboard state from `app.json`; some declarations exist only in the management platform.

## Sensitive feature examples

Review, when present:

- location and address
- camera, microphone, album, media, and files
- phone number, profile, identity, and authentication
- contacts and personal communications
- health, sports, device, Bluetooth, and nearby-device data
- orders, payment, invoices, financial information
- clipboard, calendar, and device storage
- analytics identifiers and advertising
- user-generated content, comments, chat, and customer service
- cloud functions, maps, OCR, AI, analytics, and other third-party processors

## Reviewer instructions

Make the shortest reproducible path:

- starting page or deep link
- role and account prerequisites
- safe test account delivery method
- test data
- exact taps and expected result
- payment or hardware simulation
- region or time restrictions
- privacy authorization step
- customer-service contact

Never put passwords or production credentials in public repository files. Deliver reviewer credentials through the platform's secure field or another user-approved secure channel.

## Honest rejection prevention

- Do not hide core functionality behind an unavailable account.
- Do not submit empty, placeholder, broken, or webview-only pages without required justification.
- Do not declare a service category that does not match the actual product.
- Do not ask for personal information before it is needed.
- Do not make consent the only path when a non-sensitive core experience can work without it.
- Do not show screenshots that differ materially from the submitted version.
- Do not claim no data handling when cloud functions, plugins, analytics, payment, or customer-service systems receive data.

