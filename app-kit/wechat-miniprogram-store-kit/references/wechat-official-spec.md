# WeChat Mini Program release reference

Last checked: 2026-07-24. Recheck the live management dashboard before submission because profile fields, media dimensions, qualifications, and policy requirements can change.

## Official sources

- [Mini Program collaboration and release](https://developers.weixin.qq.com/miniprogram/dev/framework/quickstart/release.html)
- [Mini Program privacy authorization development guide](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)
- [User privacy protection guide](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/)
- [Network and server-domain configuration](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)
- [Subpackages](https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages/basic.html)
- [`miniprogram-ci`](https://developers.weixin.qq.com/miniprogram/dev/devtools/ci.html)
- [WeChat Mini Program platform](https://mp.weixin.qq.com/)

## Verified workflow

The official release flow is:

1. preview the project
2. upload code with a version and project note
3. find the development version in the management dashboard
4. optionally set an experience version
5. submit the tested version for review
6. after approval, use full or staged release

Only one version can be under review at a time. Treat upload, submit-review, and release as separate actions.

## Privacy

Mini Programs that handle personal information must configure 《小程序用户隐私保护指引》 in the management dashboard. Only information types declared in that guide may use corresponding restricted APIs or components.

The official guide documents:

- `wx.getPrivacySetting` to query whether authorization is needed
- `wx.openPrivacyContract` to open the configured guide
- `<button open-type="agreePrivacyAuthorization">` to synchronize consent
- privacy authorization before calling declared restricted APIs/components

Actual code, the dashboard guide, product prompts, privacy policy, and data retention/deletion behavior must agree.

## Network and secrets

The official network guide states:

- a Mini Program may communicate only with configured server domains
- request/upload/download use HTTPS; WebSocket uses WSS
- direct IP and localhost are not accepted as normal server domains
- server domains require appropriate ICP filing
- `api.weixin.qq.com` must not be configured or called directly from the Mini Program
- AppSecret belongs on a backend server
- test again with domain/TLS validation enabled

## CI

`miniprogram-ci` supports project compilation, preview, and upload. The code-upload private key has preview/upload authority and must be protected. Configure the management-dashboard IP allowlist and keep the key in local or CI secret storage, not Git.

CI output can report the full package, main package, subpackages, and plugins. Use that output or DevTools as the final package-size authority.

## Package size

The audit script uses widely deployed operational warning defaults of 2 MiB for the main package and each subpackage, and 20 MiB for total code. These are guardrails, not a promise of current acceptance. Confirm the current limits in the exact DevTools/CI version and management dashboard used for submission.

## Visual and profile fields

The public documentation does not provide one stable universal specification for every management-dashboard image field. Before producing final assets:

1. open the current account's profile and submission pages
2. record exact dimensions, formats, size limits, counts, and text limits
3. enter the image constraints in `release-assets/asset-spec.json`
4. validate the exported assets

Do not reuse Chrome Web Store promotional-tile sizes.

## Account and qualifications

Check the live account for:

- subject and administrator status
- certification
- service category
- category-specific licenses or qualifications
- applicable Mini Program filing status
- payment, customer service, content safety, and user complaint requirements

Do not make legal or eligibility guarantees from source code alone.

