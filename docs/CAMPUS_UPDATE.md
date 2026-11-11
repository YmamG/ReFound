# College of Computing revision — implementation and validation

Updated 2026-11-11. This is the current revision's validation record; `MVP_VALIDATION.md` describes the previous shipped release.

## Implemented decisions

- Homepage: two explicit primary actions, **Search lost items / Add a report**. The report chooser retains both lost/found workflows.
- College of Computing scope: men's/women's building selection, default report/browse building, optional classroom/lab number. Building, category, color, location/classroom, type, status and keyword filtering work together.
- Browser identity: an eight-digit display number and an opaque, random, HTTP-only cookie. No account/password. The displayed number cannot grant access. The cookie's credential is hashed in storage, never shown in page text/URLs/localStorage, and is Secure in production. Clearing cookies/changing browsers loses access; shared browsers share management access. No hardware fingerprinting is used.
- My reports: this browser's reports, inbox, status changes and explicit deletion. Existing reports retain legacy access; one-time legacy verification can transfer ownership to a browser and permanently revoke the old key. New reports never generate keys.
- Automatic archive at **60 days from creation**; the current board remains newest-first. Archived details remain visible, but new messages and matching stop. Permanent deletion eligibility at **365 days**, implemented by `prune_reports` (dry run by default; `--execute` permanently deletes eligible data/photos after commit). Physical cleanup requires a daily host scheduler; none was deployed/configured automatically.
- Rule matching stays active, with building separation and classroom/location points. No AI is active or required.
- Arabic/English language switch: localized navigation, forms, validation/help, choice labels, match explanations, status/feedback and error pages; RTL/LTR, locale-aware dates and automatic direction for user text. Saved preference takes priority over browser language; Arabic is the fallback. OS-native file controls follow browser/OS language.

## Design reference and adaptation

The exact Inspora URL returned network-policy **403** for `www.inspora.design`; this was reported before design changes. The supplied 26-second video was inspected directly, and the supplied DESIGN.md is preserved as `DESIGN_REFERENCE.md`.

Applied: cream `#f5f1e4`, ink `#2c2e2a`, green `#8ed462`, white floating 50px pill navigation, large sans-serif headlines, soft flat cards, generous whitespace, circular CTA accents, original paper-cut campus illustration and yellow footer. Inter and Noto Sans Arabic are served locally with included OFL licenses. The Latin system follows Inter; Arabic uses a compatible Arabic family and adjusted spacing so connected letterforms remain readable. Responsive typography/radii are adapted for small screens. No gradients, drop shadows, frontend framework or animation library were added. Item photos and a usable report grid remain because this product needs them.

Subtle entry/scroll motion respects reduced motion. Content remains visible without animation support; navigation and forms remain usable with JavaScript disabled. Reference illustrations/photos were not copied. Synthetic test images are confined to a disposable browser fixture, never inserted into real reports.

## Actual validation

| Check | Result |
| --- | --- |
| Django suite | **72 tests passed**, 19.455 seconds in the prepared environment |
| Browser suite | **85 checks passed**, including 72 responsive page/language/width combinations |
| Viewports | 375, 390, 768 and 1440 pixels, each in Arabic and English |
| Browser errors / third-party requests | Zero unexpected browser errors; zero external requests |
| Production smoke | HTTPS redirect, secure cookies, HSTS, hashed static assets and protected media passed |
| Django system checks / migrations | No issues; no missing migrations |

Browser workflows: Arabic lost submission with photo preview/invalid-type feedback, English found submission without image, no key/account/password, persistent identity on return, unauthorized browser/number denial, private messages across languages, no refresh resubmission, status changes, resolved/archived contact rejection, abuse reporting, rule-based classroom match, combined filters, language switches preserving filters, archive access, confirmed deletion, cookie-clearing loss of access, keyboard menu/Escape, no-JavaScript forms/navigation and reduced-motion behavior. The browser fixture used disposable SQLite/media and a production-style static/error configuration with testing-only HTTP cookie overrides.

Django coverage retains the original application workflows and adds device isolation/tampering, ownership transfer/revocation, building separation, classroom/color filters, archive timing, retention preview/execution, localized labels/errors/CSRF and zero-query 500 rendering. No current claim is made about the previous key-based browser suite; it was replaced by the device/bilingual suite.

Conservative HSTS defaults intentionally produce only **W005/W021** (subdomain/preload flags). A separate strict test profile with both explicitly enabled passes deployment checks without warnings. Do not enable those flags on a real domain merely to suppress warnings; verify all affected HTTPS domains and understand preload commitments first.

Migration 0003 was applied after an external backup of the existing SQLite database. It adds fields/models only. Permanent retention cleanup was run against the real local database in **dry-run mode only**, deleting nothing. Tests of actual deletion used isolated test databases. Existing research files were preserved, no ML packages installed, and no hosting deployment was performed. GitHub delivery follows the user’s earlier request to make updates available through the repository.

## Remaining release responsibilities

Configure the chosen host/domain/HTTPS, persistent SQLite/media paths, trusted ingress settings, backup/restore, daily retention command, a real support address, moderation assignments and the operator's privacy/retention policy. Test browser-cookie persistence and the full private-message workflow on the actual HTTPS host after restart before public invitations. This is functional regression testing, not a load test, penetration test or accessibility certification.

Product limits remain explicit: no automatic email notifications, two-way in-app replies, ownership verification, text editing, browser-access recovery or cross-device synchronization. Rule matching is simple and can miss multilingual paraphrases. Ordinary replay protection does not guarantee deduplication of simultaneous independent POSTs.
