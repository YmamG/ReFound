# ReFound

An account-free Django lost-and-found board, ready for supervised user testing. Report belongings, explore the board, send private messages and manage reports using a secret key. The interface uses Django templates, original SVG illustrations, local CSS and small progressive JavaScript enhancements. No frontend framework, external fonts or analytics are required.

**AI research is frozen. AI matching is experimental and is not active in the live application.** MiniLM, CLIP and other research packages are not imported by Django or included in application requirements. Existing `experiments/` work is separate and is not needed to run or deploy the MVP.

## Local setup — Windows PowerShell

Run these commands inside the repository folder that contains **manage.py**, not a parent folder. `Get-ChildItem -Force -Name` should show `manage.py`, `requirements.txt`, `core` and `ReFound`.

Python 3.12+ is required. Tested with Python 3.12 and Django 6.1.3.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Create .env ONLY if it does not already exist; existing configuration is preserved.
python -c "from pathlib import Path; import secrets; p=Path('.env'); p.exists() or p.write_text('DJANGO_SECRET_KEY='+secrets.token_hex(48)+'\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n', encoding='utf-8')"
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` directly in the commands instead of changing machine-wide execution policy.

For macOS/Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
if not p.exists():
    p.write_text('DJANGO_SECRET_KEY=' + secrets.token_hex(48) + '\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n')
    p.chmod(0o600)
PY
python manage.py migrate
python manage.py runserver
```

An existing SQLite database and media directory are reused. Back up both before upgrades. New migration `0002` only adds moderation flags; it does not replace existing reports. Environment variables override checkout `.env`, which takes precedence over legacy parent-folder `.env`. See `.env.example` for supported settings. The prepared cloud workspace has an existing application interpreter at `/workspace/.venvs/refound/bin/python` and development variables in `/workspace/.refound/dev.env`; do not publish that file.

## Implemented workflows

- **Lost / found reports:** no user account; validated descriptions, categories, optional color, approximate location, date, private email/phone and optional photo. Invalid forms retain text and show linked error summaries. Successful POST refreshes redirect to management instead of submitting the same form again. Pending forms are session-bound; reload an expired form before retrying.
- **Photos:** still JPEG/PNG only, 5 MB / 12 million pixels maximum. Upload streams are bounded before saving. Images are oriented, resized to fit 1600×1600, flattened onto white when transparent, re-encoded as JPEG, and given random filenames. Metadata and appended payloads are discarded. No photo is required.
- **Board:** `/reports/` supports keyword search and combined category, general area, status and lost/found filters, sorting and pagination. Empty, invalid-filter and missing-image states are handled.
- **Matches:** `/reports/<uuid>/matches/` preserves the Phase 2 rule scorer: category 30, shared keywords 25, color 15, area 20, dates within seven days 10; threshold 40/100, at most 20 candidates. Opposite report types only. Resolved and moderator-hidden reports are excluded. Shared-detail points are not probabilities or proof of ownership. Suggestions never change report status automatically.
- **Private contact:** message forms save a private message and reply email in the owner's inbox. A redirect prevents refresh from repeating the submission. Public pages never disclose stored contact information or inbox contents. **Messages are not emailed, and there are no automatic notifications.** The owner checks the inbox and replies using the sender's email outside the app.
- **Management:** a random 256-bit management key is shown once, with copy/download controls. Only its password hash is saved; the raw key is never stored in session data or URLs. Save the key and report ID. `/manage/` accepts a report link/ID plus key. Each report grant expires after one hour, rotates the session ID on unlock and is invalidated if the stored hash changes. Owners can read paginated messages, change status, lock access or permanently delete with explicit confirmation. GET never mutates a report. Resolved reports stop accepting messages.
- **Moderation:** report abuse privately from each report page. Administrators can mark concerns reviewed, hide/restore reports and delete inappropriate content. Hidden reports disappear from public details, browsing, home, matching and public image access; their owners retain private management access. Deleting through either owner management or admin removes related messages and schedules photo deletion after database commit.
- **Interface:** responsive mobile navigation, accessible labels/focus/error summaries, RTL direction for item text, original brand assets, image previews, copy/download feedback, reduced-motion support and no dependency on JavaScript for core workflows. Interface copy is English; full Arabic localization remains future work.

## Moderation and practical testing

```bash
python manage.py createsuperuser
```

Use `/admin/` with a strong unique password. Give moderators only the required report/claim/abuse permissions; private contact information is visible to authorized administrators. Inspect **Abuse reports → unreviewed**, investigate, hide a report when appropriate, then mark the concern reviewed. Hiding and marking reviewed are separate actions. The app does not automatically remove a report just because someone flags it.

For a testing session, try two separate browser profiles: submit a lost report in one and a similar found report in the other; save both keys; browse/filter; check rule suggestions; send a private message; verify the original owner sees it; mark resolved; confirm new messages are rejected; test deletion. Do not use real sensitive belongings or contact details until the operator has agreed on privacy and support arrangements. No demonstration records are automatically inserted into the real database.

## Tests and checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core --verbosity 2
```

Tests use isolated databases and temporary media. Coverage includes the original Phase 2 functionality, submission replay, owner lookup and expiration, CSRF, permissions, public/private boundaries, moderation, deletion/rollback cleanup, upload streaming and pixel limits, EXIF stripping, transparent/animated images, missing files, escaping, filters/pagination, proxy boundaries, rate limiting and error pages. Browser validation uses installed Playwright/Chromium as a separate development check; neither is a production dependency.

## Affordable production preparation — do not use runserver

Start with one Linux Django service, **one persistent filesystem**, SQLite and filesystem media. No Redis, Celery, model server or vector database is needed. A small service around 512 MB–1 GB RAM is a reasonable starting allocation for this non-ML app; this is a sizing estimate, not a measured hosting guarantee. A free ephemeral instance will lose SQLite/media on restart or redeploy and is unsuitable for real reports. Hosting prices vary; choose a low-cost plan with persistent storage and HTTPS rather than assuming a free tier includes persistence.

1. Provision persistent storage and create a writable directory, for example `/var/data/refound/`. Mount it for both `DJANGO_DB_PATH=/var/data/refound/db.sqlite3` and `DJANGO_MEDIA_ROOT=/var/data/refound/media`. Keep database, backups and media inaccessible as static directories.
2. Install `python -m pip install -r requirements-production.txt`. Production adds Gunicorn; WhiteNoise serves versioned/compressed static assets. No ML packages are installed.
3. Configure a **new secret of at least 50 characters**, `DJANGO_DEBUG=False`, exact `DJANGO_ALLOWED_HOSTS`, HTTPS `DJANGO_CSRF_TRUSTED_ORIGINS`, storage paths, timezone and a real `REFOUND_SUPPORT_EMAIL`. Use a secret manager/environment variables and never commit `.env`.
4. For a trusted TLS-terminating ingress only, enable `DJANGO_TRUST_PROXY_SSL_HEADER=True` after confirming the ingress strips user-supplied `X-Forwarded-Proto` and sets it correctly. Incorrect proxy configuration can cause redirect loops or insecure scheme detection. Configure `REFOUND_TRUSTED_PROXY_CIDRS` to the actual ingress addresses if it supplies `X-Forwarded-For`; otherwise all clients may share one rate bucket. Untrusted forwarding headers are ignored.
5. Back up database **and** media, then run:

   ```bash
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   python manage.py check --deploy
   gunicorn ReFound.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile -
   ```

   A `Procfile` supplies the same launch command for compatible hosts. Run migrations once per release before serving traffic. The one-worker/four-thread configuration limits initial overhead and SQLite contention; it is not a horizontal-scaling design. SQLite has a 20-second lock timeout. Monitor real usage before increasing concurrency or moving to PostgreSQL.
6. Terminate HTTPS at the host, enforce a **6 MB request-body limit** there and set sensible request timeouts. HTTPS redirects, secure cookies, frame denial, referrer policy and a public-page CSP are configured. HSTS starts at 3600 seconds in production. `check --deploy` intentionally warns about **W005/W021** while HSTS subdomain/preload flags are false: do not enable them merely to hide warnings. Enable only after verifying HTTPS across every affected subdomain and understanding preload commitments. Raise the duration after the domain is stable.
7. Serve `/static/` using WhiteNoise. **Do not expose `/media/` directly through the proxy or host.** Photos are intentionally served through `/reports/<uuid>/image/` so moderation hiding is enforced. A dedicated storage backend can be added later if actually needed.
8. Create the administrator, test submission → private contact → management → resolve over the real HTTPS domain, and verify image persistence after restart. Confirm missing routes are branded error pages, not debug tracebacks. Only then invite a small supervised testing group.

## Privacy, limits and launch responsibilities

The MVP is ready for functional testing; no deployment or GitHub push is performed automatically.

Before a public launch the operator must select hosting/domain/TLS, configure persistent storage and trusted proxy settings, establish backups with a tested restore, publish a support contact and retention/privacy policy, and assign someone to review abuse. Backups may retain deleted data according to the operator's retention policy. Database and private messages are not end-to-end encrypted; protect disk, backups and administrative access.

Keys cannot be recovered automatically; support must establish ownership before administrator-assisted removal. There is no account/email verification, automatic key recovery, notification delivery, two-way in-app conversation, or automatic moderation. A mistaken report can be resolved/deleted and resubmitted; editing public report content is not implemented. Concurrent duplicate submissions from separate requests are not guaranteed to deduplicate; the form replay guard and disabled submit button cover ordinary refresh/retry behavior.

The HMAC IP limiter allows ten public write/unlock attempts per ten minutes, shared across sessions and public actions. Administrator login has a separate bucket. It is baseline abuse protection: shared networks share limits, network rotation can evade them, and a site operator should monitor misuse. Raw IPs are not stored in the limiter, but hosting access logs may contain them. CSRF protects writes; keys are bearer secrets. Lost keys and accidental disclosure require operator assistance.

Search and rule matching are deliberately simple. Rule matching scans eligible reports and can miss Arabic/English paraphrases; benchmark again when real volume requires indexed candidate retrieval. Keep research datasets/weights and development virtual environments out of the production build. No AI model or external AI API is connected to public submission/search, and no additional AI work is required for this release.

The optional reproducible production smoke check uses disposable storage and does not need a host:

```bash
python scripts/check_production.py
```

For the full browser check, use **only** the isolated fixture below (it creates a temporary database, original synthetic illustrations and testing-only HTTP cookie settings). Install Playwright/Chromium in a separate development environment if not already available; they are not application requirements. In separate terminals, from this checkout:

```bash
python scripts/browser_fixture.py
node scripts/check_browser.cjs
```

The browser fixture serves loopback port 8000, cleans temporary data when stopped, and must never be deployed. Stop your ordinary development server first. `CHROMIUM_EXECUTABLE` optionally selects a browser binary; screenshots are saved to the system temporary directory under `refound-browser-artifacts` (override with `REFOUND_BROWSER_ARTIFACTS`). See [the validation record](docs/MVP_VALIDATION.md) for actual results and remaining release responsibilities.
