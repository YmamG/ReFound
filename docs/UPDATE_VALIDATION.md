# Optional details, bilingual rules, admin and AI preview — 12 November 2026

- Description is optional in the model, public form and admin. Supplied descriptions still require 10 characters. Migration 0004 changes validation metadata and preserves existing data.
- Submission keeps required information visible; optional description, classroom and photo controls are grouped under a native disclosure. Hidden-field validation errors open it. Browse keeps search/type visible and discloses the remaining filters; supplied filters/errors reopen it. Keyboard/no-JavaScript behavior is preserved.
- Both rule-based comparison paths and browse understand the explicit common item/color glossary. `اسود`, `أسود` and `black` agree; multiword colors retain their explicit meanings. This does not promise general translation of arbitrary text.
- Existing Django admin edits/deletes reports and handles moderation. Authorization tests cover unauthenticated users and staff without view permission. A local cloud administrator was created with a generated private password stored outside the repository; account/password/database are never uploaded. Each Windows/deployment database needs its own `createsuperuser`.
- Optional AI is isolated on feature/public-ai-matching and can be opened by visitors without login, with local multilingual MiniLM and rule fallback. It does not affect public matching; the branch defaults to enabled, with explicit fallback when dependencies/model are missing. See AI_PREVIEW.md and the recorded offline smoke JSON. No heavy dependencies were installed for this update.

## Actual validation

- **95 Django tests passed on the public AI branch** (including optional validation, bilingual browse/matching, admin edit/delete authorization, anonymous AI access, hidden-report exclusion, independent rate limiting, busy-model fallback, AI eligibility/privacy and fallback).
- **101 full browser checks passed**, without unexpected browser errors or external requests. The existing script now explicitly opens optional controls before entering those fields.
- Dedicated Arabic/English browser smoke passed: submit without description, collapsed optional fields, keyboard disclosure and both color/query filters matching Arabic to English.
- Production smoke passed, including secure cookies, static assets, no pending model changes and absence of ML imports in normal application startup. Existing documented HSTS subdomain/preload warnings remain until operator configuration.
- Actual CPU model smoke passed in an existing optional ML environment with disposable SQLite. No production report was used or changed; this small synthetic example is not an accuracy claim.

No deployment is performed by this update. GitHub upload requires valid repository authentication. Model weights, credentials and experimental datasets remain local.

Branch separation: release/mvp-refinements contains the non-AI commit (88 tests passed). feature/public-ai-matching adds public AI opt-in and optional provisioning. GitHub authentication returned `could not read Username` and `gh auth status` reported `GH_TOKEN is invalid`; remote refs have not been changed.
