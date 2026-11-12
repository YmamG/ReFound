# ReFound reference lock

Target: the user-supplied MindMarket Style Reference (12 November 2026), supplied recording, and existing ReFound product constraints. Live MindMarket/Inspora access was blocked; no live-source CSS inspection is claimed. Refero MCP tools are unavailable; use the installed Refero methodology and bundled craft guidance.

| Decision | Evidence | Role and adaptation |
| --- | --- | --- |
| Cream canvas, floating white pill navigation | Supplied style reference | Cream remains dominant; white elevates navigation and content without shadows. |
| Oversized centered Inter heading | Supplied reference typography | 140px desktop target, fluid mobile scale; Arabic uses local Noto Arabic, normal tracking and generous leading. |
| Unframed illustrated people | Supplied recording and reference | Original generated test illustrations, transparent WebP, fully visible rather than clipped. Real report photographs remain supported. |
| Light pill actions with colored icon circles | Supplied component guide | Two primary homepage actions: search and add a report. Clear hover/focus and reduced motion. |
| White rounded editorial content panels | Supplied reference | Alternating artwork and useful product explanations; do not invent usage statistics. |
| Yellow closing band | Supplied reference | Footer only. Green is a structural accent, not a large hero surface. |
| Progressive optional filters, ranked card deck | User's explicit product brief; Refero craft details | Two required inputs, native details for extras; no-JS ordered list and accessible previous/next enhancement. |
| Existing browse layout | User's explicit constraint | Keep its template and filtering behavior unchanged. |

Reject: gradients, heavy shadows, clipped characters, random floating objects, fabricated matches, ownership probabilities, ML integration.

Implementation QA: capture English/Arabic desktop and mobile, inspect overflow, artwork crop, navigation, focus and match-card states. Run Django and browser workflow checks before handoff.

The first mobile pass found decorative overflow and a selected-building control that widened the English 320px hero. Both are corrected at their source (contained decoration and a bounded two-column building selector), rather than hiding horizontal overflow on the whole document.

## Validation — 12 November 2026

- Django: **83 tests passed** (72 existing workflow tests plus 11 new search regressions).
- Existing browser suite: **101 checks passed**, no unexpected browser errors or external requests.
- Guided search/design suite: **42 checks passed**, including 320/375/768/1024/1440 widths, both languages, optional disclosure, actual ranked results, multi-card previous/next and directional keyboard navigation, invalid dates, no results, safe public output and no-JavaScript rendering.
- Production smoke: passed HTTPS/cookie/HSTS, hashed/immutable assets (including new artwork and page assets), protected media, absence of ML imports and no missing migrations. Existing W005/W021 remain intentional until the hosting operator enables subdomain/preload HSTS after verifying the real domain.
- Visual QA: inspected actual English/Arabic desktop and mobile captures against the supplied reference lock. Cream canvas, floating pill, giant centered display, full illustrations, white rounded story panels and yellow closing band retained. No unresolved overflow at tested widths.
- Browse template and the existing report matching service have no changes. No packages, migrations, deployment or GitHub push are part of this redesign.

Screenshots from an isolated fixture (fictional objects, no live user data) are in `/workspace/.refound/artifacts/final-design/`.
