# Chrome Web Store submission specification

Last checked: 2026-07-24. Treat this as a working checklist, not a substitute for the live Developer Dashboard.

## Official sources

- [Complete your listing information](https://developer.chrome.com/docs/webstore/cws-dashboard-listing)
- [Supplying images](https://developer.chrome.com/docs/webstore/images)
- [Creating a great listing page](https://developer.chrome.com/docs/webstore/best-listing)
- [Fill out the privacy fields](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy)
- [Privacy policies](https://developer.chrome.com/docs/webstore/program-policies/privacy)
- [Limited Use policy](https://developer.chrome.com/docs/webstore/program-policies/limited-use)
- [Chrome Web Store program policies](https://developer.chrome.com/docs/webstore/program-policies/policies)

Re-open the official pages when producing a live submission. Record any changed requirement in the delivery report rather than silently relying on this file.

## Graphic assets

| Asset | Requirement | Skill default |
|---|---|---|
| Store icon | 128x128 px | PNG, visually consistent with manifest icons |
| Screenshots | At least 1 and at most 5; 1280x800 preferred, 640x400 accepted | Produce 3–5 at 1280x800 |
| Small promo tile | 440x280 px; PNG or JPEG | Required; non-alpha 24-bit PNG or JPEG |
| Marquee promo tile | 1400x560 px; PNG or JPEG | Optional in the Store, but produce it for a complete kit |
| Promo video | YouTube URL | Optional/recommended when it materially explains the workflow |

The small and marquee tiles cannot be localized. Localized descriptions, screenshots, and promotional videos can be supplied for supported locales.

For safe uploads, flatten alpha in screenshots and promotional tiles. Keep editable masters in `store-assets/source/`, not in the runtime ZIP.

## Listing content

The package title and short summary originate from `manifest.json`. The dashboard additionally requests:

- detailed description
- primary category
- language
- screenshots and promotional media
- homepage and support URLs when available
- mature-content declaration
- privacy-practices fields
- distribution settings

Detailed copy must accurately describe implemented behavior. Avoid keyword stuffing, misleading comparisons, unverifiable claims, fake ratings, and features that are not visible in the submitted build.

## Privacy and review

Prepare:

- a single-purpose explanation
- a justification for every requested permission
- a host-access justification
- a declaration about remote code
- data-use disclosures
- public privacy-policy URL when user data is handled
- confirmation of compliance with the Chrome Web Store user-data and Limited Use policies

Permissions and disclosures must match the submitted ZIP, not merely the source branch.

## Runtime package

- Use Manifest V3 unless an officially supported exception applies.
- Include all runtime dependencies locally.
- Do not download or execute remote JavaScript, WebAssembly, or other executable code.
- Do not ship secrets, private keys, source credentials, test data, `.git`, development caches, or store-only creative assets.
- Use the narrowest permissions and host patterns that support the single purpose.
- Load and test the exact unpacked directory that will be zipped.

