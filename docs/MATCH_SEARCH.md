# Find the best match

`/find-match/` is separate from `/reports/` (browse) and the existing report-to-report potential matches service. The homepage search action opens it. The existing matching service and public report submission, private messaging and management workflows are unchanged.

## Interaction

Item and color are required. Optional details are in a native `details` disclosure: category, building, area, classroom, date, appearance and target report type. Found reports are the default. A selected homepage building is prefilled and shown as a scope hint. The user can change it or select both buildings in the optional section.

The server returns up to 20 actual eligible reports in stable descending order. JavaScript displays a card deck with previous/next and RTL-aware arrow keys. A single result needs no paging controls. With JavaScript disabled every card remains visible as an ordered list. No report is created, marked matched, resolved or claimed by searching. Existing detail pages handle private contact and moderation.

## Rules and limits

- Explicit small Arabic/English item/color glossary plus normalized literal word overlap; no semantic model, translation API or image analysis.
- Item evidence is mandatory. A known incompatible physical object is excluded (e.g. laptop charger versus laptop bag). Matching colors alone never qualify a report.
- Item evidence supplies up to 50 points; color up to 25; supplied category, area, room, date and appearance each add up to 5. Normalize by the maximum for the supplied criteria. Missing report fields do not earn matching points.
- Scores are **rule points, not probabilities**. Color conflicts are shown explicitly. Subtle synonym, dialect, compound-object and unknown shade handling remains limited; browse remains available.
- Same chosen building, requested type, visible, unresolved and less than the configured archive age. Classroom normalization preserves letters and digits, including Arabic/Persian digits.
- Searches scan eligible reports on CPU. This is appropriate for the current small SQLite MVP; measure real traffic before scaling. No new infrastructure or heavy dependencies.

## Assets and verification

`return-story.webp` and `search-story.webp` are original generated editorial illustrations, not photographs of actual people or matching evaluation data. Local fonts and the existing icon sprite are retained. No third-party art was scraped from the inspiration website.

Run Django tests plus `scripts/check_production.py`; use the disposable browser fixture with both `scripts/check_browser.cjs` and `scripts/check_match_game.cjs`. Scripts never seed production data or deploy.
