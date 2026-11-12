# ReFound — College of Computing

A lost-and-found board for the College of Computing, with Arabic/English interfaces, separate men's/women's building views, private messages and simple rule-based suggestions. Built with Django templates and local CSS/JavaScript. No frontend framework, paid API or ML runtime is required.

**Public matching remains rule-based. AI work is isolated on a separate experimental branch.** Existing `experiments/` files are separate and are not needed to run or deploy the app.

## Design preview

[Arabic desktop](docs/screenshots/home-ar-desktop.png) · [Arabic mobile](docs/screenshots/home-ar-mobile.png) · [English desktop](docs/screenshots/home-en-desktop.png) · [English mobile](docs/screenshots/home-en-mobile.png) · [Interaction preview](docs/screenshots/interactions.gif)

These screenshots use disposable fictional browser-test data, not real reports or personal contact information.

## Run locally — Windows PowerShell

Open the actual repository directory containing **manage.py**, **requirements.txt**, **core/** and **ReFound/**. If your project was downloaded/cloned inside another ReFound folder, do not run these commands in the outer folder.

Python 3.12+ is required; tested with Python 3.12 and Django 6.1.3.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Create .env only when absent; preserve existing settings and secrets.
python -c "from pathlib import Path; import secrets; p=Path('.env'); p.exists() or p.write_text('DJANGO_SECRET_KEY='+secrets.token_hex(48)+'\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n', encoding='utf-8')"
python manage.py migrate
python manage.py runserver
```

Open **http://127.0.0.1:8000/**. If PowerShell blocks activation, run `.\.venv\Scripts\python.exe` directly instead of changing machine-wide execution policy. Stop the server with Ctrl+C.

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

Exported environment variables override checkout `.env`, which overrides legacy parent-directory `.env`. Existing SQLite/media are preserved. Back up both before upgrades. Migration `0003` adds browser identities, report ownership, building and classroom fields; existing reports are not deleted or assigned a guessed building. The prepared cloud workspace uses `/workspace/.venvs/refound/bin/python` and `/workspace/.refound/dev.env`; do not publish that development environment file.

## What users can do

- **Start clearly:** the home has two main actions, **Search lost items / Add a report**. Adding opens a lost/found type chooser.
- **Choose the building:** men's/women's building selection scopes the home, defaults the browse filter and preselects new report forms. Users can explicitly browse both buildings. This release covers the College of Computing only.
- **Report an item:** category, description, optional color, building, area and event date, private email/phone, optional classroom/lab number and optional photo. Keep passwords, door/access codes, personal documents and unique ownership evidence out of public fields.
- **Browse/search:** combine keywords, type, category, color, location/classroom, status and building, with sorting and pagination. The current board defaults to newest first; older reports have a separate archive.
- **Compare reports:** suggestions use category (30), shared description words (25), color (15), matching classroom or shared area words (20), and dates within seven days (10). Threshold 40/100, at most 20 candidates. Buildings must match; opposite report types only. Hidden, resolved and archived reports are excluded. Points are shared-detail scores, not probabilities or proof of ownership. Suggestions never change statuses automatically.
- **Contact privately:** send a message and reply email from a report. The owner reads it in **My reports** and replies using that email outside the app. **No automatic email notification is sent.** Public pages never disclose stored contact information or message contents.
- **Manage:** My reports shows this browser's reports, private inboxes, status controls and deletion with confirmation. Resolving blocks new messages. Hidden/archived reports remain manageable by their owner. Read requests never change status/delete reports.
- **Moderate:** private abuse forms save concerns for administrators. Reports can be hidden/restored and concerns marked reviewed independently. Hidden reports disappear from public details, boards, suggestions and image access; authorized owners/moderators retain access.

## Browser number — no account or password

Each browser profile gets a persistent private cookie and an eight-digit reference number. The cookie contains a random 256-bit credential; only its SHA-256 hash is stored in the database. It is HTTP-only, SameSite=Lax and Secure in production, with a rolling one-year lifetime. It is never put in URLs, page text or localStorage. Pages containing a browser identity are private to caches.

**The displayed number is not a password and cannot unlock or recover reports.** This identifies a browser profile, not physical hardware: no device fingerprinting is used. Clearing cookies, switching browsers, reinstalling, private browsing or disabling cookie storage loses access. Anyone sharing the same browser profile can manage its reports. There is no automatic recovery or cross-device synchronization. Contact the operator for a privacy/removal concern; do not send private cookies.

New reports do not generate management keys. Existing pre-device reports keep legacy access so their owners do not lose data. `/my-reports/import/` verifies an old key once, transfers that report to the current browser and permanently invalidates its old key. No other browser can take a device-owned report using the old key or public number. Reports whose legacy access was lost require operator assistance.

## Archive and permanent deletion

- After **60 days from creation**, reports leave the current board automatically and appear at `/reports/archive/`. No background job is needed for this separation. Archived details remain readable but no new messages or match suggestions are offered.
- After **365 days from creation**, reports become eligible for permanent deletion, including related messages/abuse records and image cleanup after database commit.
- Physical deletion needs a daily scheduler on the host. Merely viewing the site never runs a destructive cleanup. Configure the following command in the host scheduler after backups/retention arrangements are ready:

  ```bash
  python manage.py prune_reports --execute
  ```

  Preview safely at any time with `python manage.py prune_reports` (no deletion). For a small Linux server, schedule the command daily using cron with the absolute virtualenv interpreter, checkout working directory and production environment; no Celery/Redis is required. No hosted scheduler was configured automatically in this workspace.

`REFOUND_ARCHIVE_DAYS` and `REFOUND_DELETE_DAYS` configure the windows; startup validates `1 <= archive < delete`. Dates are measured from report creation, not the event date. Owners can delete earlier. Backups can retain removed data according to the operator's published retention policy.

## Arabic, English and design

Language follows the saved preference, then the browser preference, with Arabic as the fallback. The **العربية / English** button switches complete page direction, navigation, labels, choices, help text, validation, matching explanations and system feedback. User descriptions are displayed unchanged with automatic text direction. Full browser controls such as the OS file picker use the browser/OS locale.

The redesign adapts the supplied video and [design reference](docs/DESIGN_REFERENCE.md): cream `#f5f1e4`, ink `#2c2e2a`, green `#8ed462`, white floating pill navigation, large sans-serif titles, soft cards, a clean, original belongings illustration and a yellow closing section. Lost/found photos remain available because they are part of this product's purpose. Inter and Noto Sans Arabic are hosted locally under their included Open Font Licenses in `static/fonts/`; no font CDN is contacted by visitors. Design values are centralized in `static/css/tokens.css`, using the supplied color/type/spacing/radius tokens as ordinary CSS. The browser downloads a locally hosted, approximately 190 KB WebP hero illustration. Button hover/press/focus, submission feedback and menu transitions share consistent timings; motion respects reduced-motion preferences, and forms/navigation work without JavaScript.

Arabic translations live in `locale/ar/messages.json`. After editing:

```bash
python scripts/compile_translations.py
```

The stdlib-only compiler updates Django `.po`/`.mo` catalogs. Generated catalogs are included for Windows/deployment convenience; gettext system packages are unnecessary. Restart the process after catalog changes.

## Moderation and privacy

```bash
python manage.py createsuperuser
```

Use `/admin/` with a strong unique password. Give moderators only the report/claim/abuse permissions they need. Inspect unreviewed abuse concerns, investigate, hide a report when necessary, then mark concerns reviewed. Hiding and marking reviewed are separate actions; a flag does not automatically remove content. Private contact details and messages are visible to appropriately authorized staff.

Still JPEG/PNG only, up to 5 MB / 12 million pixels: uploads are bounded before views write data, oriented, resized to fit 1600×1600, flattened on white when transparent and re-encoded as JPEG with random names. Original names, metadata and appended payloads are discarded; animation is rejected. Public image routes use JPEG content type, nosniff and restrictive CSP. Deletion via owner/admin/queryset schedules photo cleanup after commit and preserves files on transaction rollback.

CSRF protects writes. Public text is escaped. A shared HMAC-IP limiter allows ten public write/unlock attempts per ten minutes; admin login has a separate bucket. Trusted proxy CIDRs must be explicit; untrusted forwarding headers cannot change client identity. Shared networks share limits; network rotation can evade them. This is baseline protection, not a complete anti-abuse service. Hosting logs may contain IPs; the limiter does not retain raw IPs.

## Verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core --verbosity 2
python scripts/check_production.py
```

Django tests use an isolated database and temporary media. The production smoke uses disposable storage, checks secure cookies/HTTPS/HSTS, collected versioned assets, protected media, missing routes and absence of ML imports. See [the current design validation report](docs/DESIGN_REFINEMENT.md).

For optional Playwright/Chromium checks, start the **disposable fixture**, then run the browser script in another terminal:

```bash
python scripts/browser_fixture.py
node scripts/check_browser.cjs
node scripts/check_match_game.cjs
```

Stop any ordinary local server first. The fixture serves only loopback port 8000, uses temporary SQLite/media, original synthetic test illustrations and testing-only HTTP cookie settings; never deploy it. Playwright/Chromium are development tools, not application requirements. `CHROMIUM_EXECUTABLE` can select the binary. `REFOUND_BROWSER_ARTIFACTS` selects the screenshot directory (default: system temporary directory / `refound-browser-artifacts`). Restart the fixture before each full test run. Real reports are never automatically seeded.

## Affordable production readiness

Use one Linux Django service, a persistent filesystem for SQLite and media, and host-provided HTTPS. No ML server, Redis, Celery or vector database is needed. A free ephemeral filesystem loses reports/photos on restart and is unsuitable. Hosting prices vary; choose a low-cost persistent plan. A 512 MB–1 GB starting allocation is a sizing estimate, not a measured capacity guarantee.

1. Install `python -m pip install -r requirements-production.txt` (Django/Pillow/WhiteNoise plus Gunicorn).
2. Configure a unique secret of at least 50 characters, `DJANGO_DEBUG=False`, exact allowed hosts, HTTPS CSRF trusted origins, timezone, persistent database/media paths and a real support address. See `.env.example`.
3. When a trusted TLS ingress strips client-supplied forwarding headers and sets its own, configure `DJANGO_TRUST_PROXY_SSL_HEADER=True` and the correct `REFOUND_TRUSTED_PROXY_CIDRS`. Wrong scheme configuration can cause redirect loops. Never trust all network addresses.
4. Back up database/media, then run:

   ```bash
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   python manage.py check --deploy
   gunicorn ReFound.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile -
   ```

   `Procfile` supplies this command for compatible hosts. Run migrations once before traffic. SQLite has a 20-second lock timeout; monitor contention before increasing concurrency or moving to PostgreSQL.
5. Enforce HTTPS, a 6 MB request-body limit and request timeouts at ingress. Production enables secure cookies, HTTPS redirects, frame denial, referrer policy and a public-page CSP. HSTS starts at 3600 seconds. `check --deploy` deliberately warns **W005/W021** while subdomain/preload flags are false. Enable only after verifying HTTPS for every affected subdomain and understanding preload commitments; no warnings are suppressed.
6. WhiteNoise serves `/static/`. **Never expose `/media/` directly.** Use `/reports/<uuid>/image/` so moderation hiding is enforced. Keep SQLite and backups inaccessible from public paths.
7. Configure daily retention cleanup, test backups/restore, create restricted moderators and publish support/privacy/retention arrangements. Confirm submission → private message → browser management → resolve over the real HTTPS domain and after a restart before inviting users.

No GitHub upload or deployment is performed by these setup/test commands. Existing research weights, datasets, virtual environments, secrets and local user data must stay out of the production build.

Known limits: no automatic notifications, two-way in-app replies, ownership verification, public text editing or browser-access recovery; rule matching can miss paraphrases/Arabic-English equivalents and scans eligible candidates; ordinary submission replay guards do not guarantee deduplication of simultaneous independent POSTs. This is suitable for supervised user testing after the operator completes hosting/privacy responsibilities.

## Storybook design and guided item search

The homepage follows the supplied MindMarket reference: cream paper, oversized centered typography, floating white navigation, original illustrated characters and a yellow footer. Arabic copy and mobile spacing have been refined; local fonts work without a font CDN. See [design decisions](docs/DESIGN_DECISIONS.md).

**Search lost items** opens `/find-match/`: enter item + color, optionally open extra details, then review actual reports in ranked cards. Previous/next and keyboard controls enhance an ordered list that also works without JavaScript. **Browse reports** retains the existing page and filters. See [search rules, limitations and assets](docs/MATCH_SEARCH.md).

Matching remains rule-based. AI is not active in public workflows. The ordinary application needs no ML packages. Apply all migrations when updating. Nothing in this update deploys or pushes the project.

## Optional details, bilingual comparison and administration

Descriptions are optional (if supplied, at least 10 characters). Classroom, description and photo controls are under **Show additional information**; validation errors reopen the section. Browse starts with search/type and keeps other filters in the same disclosure. Common Arabic/English colors and item aliases are compared consistently in browse and both rule-based search services, including `أسود`, `اسود` and `black`. This explicit glossary does not translate arbitrary text.

After updating, run `python manage.py migrate`. To create your **own local** administrator securely:

```powershell
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/`. The account can edit/delete reports, hide/restore them and review abuse. Passwords are prompted locally; there is no shared default password. GitHub never transfers administrator accounts, databases or passwords. To reset a local password, run `python manage.py changepassword USERNAME`.
