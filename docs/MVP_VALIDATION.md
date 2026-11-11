# MVP validation record

Validated 2026-11-11. No deployment, GitHub push or AI integration was performed.

## Actual results

| Check | Result |
| --- | --- |
| `python manage.py test --verbosity 1` | **52 tests passed**, 17.688 seconds in the prepared environment |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| Dependency compatibility (`uv pip check`) | All eight installed packages compatible |
| JavaScript syntax (`node --check static/js/main.js`) | Passed |
| `git diff --check` | Passed |
| Chromium/Playwright browser regression | **38 checks passed**, including 28 page/viewport combinations; zero unexpected browser errors |
| Production settings and collected static files | HTTPS redirect, secure cookies, HSTS, versioned CSS/JS/SVG assets, immutable cache headers and protected media passed |
| Local Gunicorn startup and HTTP smoke | One worker / four threads started; home, assets, proxy scheme and protected media passed; eight concurrent read requests returned 200 |
| Runtime imports | No torch, transformers, sentence-transformers or OpenCLIP imports |

The Django suite includes all 21 original tests, updated to follow session-bound report forms, message redirects and explicit deletion confirmation, plus 31 launch/security regression tests. Browser widths: **375, 390, 768 and 1440 pixels**; pages: home, browse, new report, detail, about, contact and owner lookup. Browser checks also covered photo preview/validation, lost and found submission, private key download, cross-session privacy and messaging, invalid-key feedback, management, status changes, private abuse reporting, a 100-point rule match, combined filters, mobile menu/Escape, deletion and core forms/navigation without JavaScript.

Production-profile browser validation used disposable storage and HTTP-only testing cookie overrides. Secure production cookies and HTTPS behavior were checked separately. The actual Gunicorn smoke simulated a trusted TLS ingress on loopback; real hosting/TLS/provider configuration still requires acceptance testing. This is a functional/security regression check, not a load test, penetration test, accessibility certification or hosting capacity benchmark.

## Confirmed defects addressed

- Oversized optional image streams could be discarded before form validation, permitting a photo-less report to be saved before a late 413 response. Multipart bounds are now enforced before views execute; tests confirm no report, message or abuse entry is saved.
- Refreshing successful submissions/messages could duplicate content. Report forms now have a session replay guard, and messaging/abuse/status actions redirect after success.
- Moderation lacked a public visibility action. Hidden reports are now excluded consistently from public pages and image access while owner/moderator access remains available.
- Photos could survive deletion through admin/querysets. Commit-aware model cleanup covers all database deletion paths and preserves files when a transaction rolls back.
- Owner sessions did not independently expire per report or reflect management-hash changes. Time-bounded fingerprinted grants now enforce both.
- Invalid/expired requests and private owner access lacked useful, consistent feedback. Branded error pages and accessible forms cover these paths without exposing private contents.
- A development mail backend prevented Django production checks from passing. The unused production mail backend now follows Django's SMTP default; no notification feature was added or activated.

## Deployment checks and boundaries

With conservative HSTS defaults, `check --deploy` reports **only W005 and W021** for subdomain/preload flags. These are deliberate operator decisions, documented in README; no warnings are suppressed. A separate test profile with both explicitly enabled passed deployment checks without warnings. Do not enable these flags on a real domain until every affected subdomain supports HTTPS and preload consequences are understood.

The existing local SQLite database was backed up outside the checkout before applying additive migration `0002`. Browser data, synthetic item illustrations and production smoke storage were isolated from the real database. Existing research artifacts were preserved and left inactive. No ML runtime packages were installed.

## Before inviting real users

The application is ready for a small supervised functional test after local setup. Before public hosting, choose the host/domain, configure HTTPS/proxy trust and persistent SQLite/media, test backups/restore, create restricted moderator accounts, configure a real support address and establish privacy/retention and abuse-review responsibilities. Validate the documented end-to-end workflow on the actual HTTPS host and after a restart.

Known product limits: no automatic messages/notifications, account/email verification or key recovery; no editing public report text; English interface with user text supporting either direction; baseline shared-IP throttling; ordinary replay protection does not guarantee deduplication of concurrent independent POSTs; rule matching scans candidates and can miss multilingual paraphrases. No AI ranking was enabled.
