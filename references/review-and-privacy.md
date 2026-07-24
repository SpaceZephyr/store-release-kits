# Review and privacy writing guide

## Evidence first

Before writing, map:

| Evidence | Questions |
|---|---|
| `manifest.json` | Which permissions, hosts, content scripts, background workers, and CSP are declared? |
| Source code | Where are tabs, storage, clipboard, downloads, identity, network, and user content accessed? |
| Network calls | What endpoint is contacted, what is sent, why, and whether code is returned or executed? |
| Persistence | What is stored, where, for how long, and how is it deleted? |
| Third parties | Which processors, analytics, APIs, CDNs, or authentication providers receive data? |

Do not infer “no collection” merely because there is no developer-owned server. Third-party APIs, analytics, crash reporting, and remote image requests still require accurate explanation.

## Single-purpose statement

Use one sentence:

> This extension's single purpose is to [primary action] for [target user/context], producing [user-visible result] only when [user trigger].

Keep permissions subordinate to this purpose.

## Permission justification

Write one compact paragraph per permission:

1. name the exact user action
2. name the API capability used
3. state what data or browser surface is accessed
4. explain why a narrower alternative is insufficient
5. state any scope or timing limit

If no code uses a permission, recommend removing it instead of inventing a justification.

## Host-access justification

List exact host patterns and connect each one to a user-visible feature. Explain whether access occurs automatically through content scripts or only after user action. Broad patterns such as `<all_urls>` require exceptional evidence; prefer narrower domains or optional host permissions.

## Remote code

Distinguish remote data from remote executable code.

- Remote data: JSON, HTML content, user documents, images, API responses processed by packaged code.
- Remote code: JavaScript, WebAssembly, or instructions downloaded and executed to change extension behavior.

If there is no remote code, say that all executable code is bundled in the submitted package. Still disclose necessary network requests and third parties.

## Privacy policy minimum

Include:

- identity and effective date
- single purpose
- data accessed or collected
- purpose and user trigger
- local versus server-side processing
- storage, retention, and deletion
- sharing, sale, advertising, and human access
- third-party services
- permissions and host access
- remote code and network behavior
- security practices
- policy changes
- contact method
- Chrome Web Store user-data and Limited Use compliance

Use a stable public HTTPS URL and verify it in a logged-out request.

## Dashboard data-use declaration

Cross-check the dashboard selections against the policy and code. Common categories include personally identifiable information, health information, financial/payment information, authentication information, personal communications, location, web history, user activity, and website content.

Reading page content can count as handling website content even when it remains local. State local-only processing clearly; do not use it as a reason to omit the category if the dashboard asks what the extension handles.

