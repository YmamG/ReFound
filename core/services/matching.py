from django.utils.translation import gettext as _
"""Explainable matching; no external APIs or image processing required."""
import re
from dataclasses import dataclass
from core.models import Report
from .item_search import item_tokens, color_similarity, room_key


@dataclass(frozen=True)
class Match:
    report: Report
    score: int
    reasons: tuple[str, ...]


def words(value):
    stopwords = {"the", "and", "with", "for", "this", "that", "from", "has", "was", "are", "item", "lost", "found", "على", "هذا", "هذه", "التي", "الذي"}
    return set(re.findall(r"[^\W_]{3,}", value.casefold())) - stopwords


def score_pair(report, candidate):
    if report.building != candidate.building or report.is_archived or candidate.is_archived or report.kind == candidate.kind or Report.Status.RESOLVED in (report.status, candidate.status):
        return 0, ()
    score, reasons = 0, []
    if report.category == candidate.category:
        score += 30
        reasons.append(_("Same category"))
    if item_tokens(report.title + " " + report.description) & item_tokens(candidate.title + " " + candidate.description):
        score += 25
        reasons.append(_("Shared description keywords"))
    if color_similarity(report.color, candidate.color) == 1:
        score += 15
        reasons.append(_("Same color"))
    if report.classroom.strip() and room_key(report.classroom) == room_key(candidate.classroom):
        score += 20
        reasons.append(_("Same classroom"))
    elif words(report.location) & words(candidate.location):
        score += 20
        reasons.append(_("Similar general area"))
    if abs((report.event_date - candidate.event_date).days) <= 7:
        score += 10
        reasons.append(_("Dates within seven days"))
    return score, tuple(reasons)


def potential_matches(report, limit=20):
    if report.status == Report.Status.RESOLVED or report.is_hidden or report.is_archived:
        return []
    candidates = Report.objects.filter(is_hidden=False, building=report.building).exclude(kind=report.kind).exclude(status=Report.Status.RESOLVED)
    matches = []
    for candidate in candidates.iterator():
        score, reasons = score_pair(report, candidate)
        if score >= 40:
            matches.append(Match(candidate, score, reasons))
    return sorted(matches, key=lambda m: (-m.score, -m.report.created_at.timestamp(), str(m.report.id)))[:limit]
