# ReFound — Phase 2

An account-free Django lost-and-found MVP. People can submit lost/found reports, search a directory, view explainable candidate matches, send private ownership messages, and manage their own reports with a secret key. No AI service is connected.

## Run locally

Python 3.12+ is required. The tested environment uses Python 3.12, Django 6.1.3 and the exact versions in `requirements.txt`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Create .env once; preserve an existing file and never commit its secret.
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
if not p.exists():
    p.write_text('DJANGO_SECRET_KEY=' + secrets.token_hex(48) + '\nDJANGO_DEBUG=True\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n')
    p.chmod(0o600)
PY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

In the prepared cloud machine, use `/workspace/.venvs/refound/bin/python` instead of `.venv/bin/python`, and `source /workspace/.refound/dev.env` to reuse its local development environment. Each cloud task is isolated; use the existing checkout without creating a worktree unless requested.

`.env` in the checkout and the legacy parent-directory `.env` are supported; already exported variables take precedence. SQLite defaults to `db.sqlite3`; `DJANGO_DB_PATH` and `DJANGO_MEDIA_ROOT` optionally select external storage paths. Migrations must be applied when updating the code.

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test --verbosity 2
```

The suite covers models, form validation, sanitized uploads, public/private views, combined filters/pagination, owner authorization, CSRF, rate limiting, deletion, and matching, alongside the original page tests. Tests use isolated databases and temporary media directories.

## Using the MVP

- `/reports/new/lost/` and `/reports/new/found/`: submit a report, optionally with a JPEG/PNG image. A management key is displayed in the successful response. Save it immediately and bookmark the management page. Refreshing/resubmitting the form may create another report.
- `/reports/`: combine keyword, type, category, approximate area and status filters, choose newest/oldest, and paginate while retaining filters.
- `/reports/<uuid>/`: public details without contact information. Use **Contact owner privately / claim item** to save a message and reply email in the owner's inbox.
- `/reports/<uuid>/manage/`: enter the key to unlock that report for a one-hour session, read private messages, change status, lock access, or delete the report. Read requests never modify/delete it. There is no key recovery; a lost key requires administrator assistance.
- `/reports/<uuid>/matches/`: explainable suggestions from the opposite report type. Candidates must score at least 40/100. Category contributes 30, shared keywords 25, color 15, approximate area 20, and dates within seven days 10. Common filler words are excluded. Resolved reports are excluded. Suggestions do not automatically change statuses or establish ownership.
- **Report abuse** saves a concern for administrators; it does not automatically remove content. Use `manage.py createsuperuser` and `/admin/` for authorized moderation. Raw management hashes are excluded from admin forms; reports are created through the public workflow.

Messages are stored privately, **not emailed**. Owners must check their inbox. Report contact information is available to authorized administrators only; claimants' reply emails are visible to the report owner and administrators. Confirm ownership privately and meet in a safe public place.

## Models and relationships

- `Report`: UUID; lost/found type; title/description; category; optional color; general area; event date; optional sanitized image; private contact method/value; active/potentially matched/resolved status; salted management-key hash; creation/update timestamps. Composite type/status/category/creation and date indexes support browsing and matching. Forms restrict lengths, choices, dates and contact formats.
- `Claim`: many private messages per report, each with message, reply email and timestamp. Cascades on report deletion.
- `AbuseReport`: many moderation concerns per report, each with reason and timestamp. Cascades on deletion.
- `SubmissionWindow`: shared database-backed HMAC client-IP bucket; atomically consumes up to ten POST attempts per ten minutes across submission, messaging, abuse and management. Raw IPs are not retained; old buckets are removed on new submissions.

## Structure and changed files

```text
ReFound/settings.py                 environment, upload, database, session settings
core/
  models.py                        reports, private claims, abuse, rate buckets
  forms.py                         validation, honeypot, image sanitization
  views.py                         browsing, submission, inbox/owner actions
  urls.py                          named application routes
  admin.py                         moderation
  services/
    matching.py                    rule-based matching seam for future AI
    security.py                    shared submission limiter
  migrations/0001_initial.py        schema
  tests.py                         original and MVP tests
  templates/core/
    home.html                      useful entry points
    browse.html                    combined filters and pagination
    submit.html                    lost/found form
    confirmation.html              management-key handoff
    detail.html                    public report
    matches.html                   scored explanations
    action_form.html               private message/abuse form
    message_sent.html              private-message confirmation
    abuse_sent.html                moderation confirmation
    manage.html                    private owner dashboard
templates/base.html                shared navigation
static/css/style.css               simple responsive form/page styling
requirements.txt                   UTF-8 dependency pins including Pillow
.gitignore                         secrets, environments, database/media/caches
.env.example                       non-secret configuration example
README.md                          setup, usage, design and limitations
```

The initial migration is additive. The previously tracked local SQLite database and Python bytecode are removed from Git tracking but kept on disk. A pre-migration backup for this prepared machine is outside the checkout at `/workspace/.refound/before-phase2.sqlite3`. No push is performed.

## Privacy, security and limits

- Keys contain 256 bits of randomness; only Django password hashes are stored. Raw keys are not written to sessions, logs or URLs. Sensitive responses use `Cache-Control: no-store`. Unlocking rotates the session ID; CSRF is required for writes. Treat the displayed key like a password.
- Images: JPEG/PNG only, maximum 5 MB / 12 million pixels, decoded and re-encoded as bounded JPEGs with generated names. Original metadata/filenames and appended payloads are discarded. Files are streamed through an explicit JPEG response with `nosniff`; arbitrary upload paths are never served.
- Public text and images are intentionally public. The UI asks for general areas and warns against publishing exact locations, contact details or identifying ownership evidence. Automated redaction is not implemented; moderators must review abuse. Templates escape user text.
- The honeypot and IP limiter are baseline protection, not a CAPTCHA or full anti-abuse system. Behind a reverse proxy, configure trusted client-address handling at the web server; untrusted `X-Forwarded-For` is ignored. Users sharing one address share limits. Add edge/body-size limits and stronger abuse controls before public deployment.
- Keep DEBUG off and use HTTPS in production; secure session/CSRF cookies are enabled when DEBUG is false. Configure allowed hosts, production static serving, persistent media/database storage, backups, private-data retention/deletion policy and moderator access. Django's development server is for local development.
- Rule matching currently scans eligible candidates and suits a small MVP. For larger datasets, add indexed candidate retrieval and background matching. Token-based access has no email verification or recovery. Rate limiting does not replace access controls.

## Next: AI phase

Extend `core/services/matching.py` behind its candidate/score interface with image embeddings and semantic text matching, indexed retrieval, measured ranking quality and explicit explanations. Add background jobs and consent/retention rules before sending any user data to external services. AI APIs, image recognition and optional university email verification remain unimplemented by design.
