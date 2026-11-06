"""Explainable matching; no external APIs or image processing required."""
import re
from dataclasses import dataclass
from core.models import Report


@dataclass(frozen=True)
class Match:
    report: Report
    score: int
    reasons: tuple[str, ...]


def words(value):
    stopwords = {"the", "and", "with", "for", "this", "that", "from", "has", "was", "are", "item", "lost", "found", "على", "هذا", "هذه", "التي", "الذي"}
    return set(re.findall(r"[^\W_]{3,}", value.casefold())) - stopwords


def score_pair(report, candidate):
    if report.kind == candidate.kind or Report.Status.RESOLVED in (report.status, candidate.status):
        return 0, ()
    score, reasons = 0, []
    if report.category == candidate.category:
        score += 30
        reasons.append("Same category")
    if words(report.title + " " + report.description) & words(candidate.title + " " + candidate.description):
        score += 25
        reasons.append("Shared description keywords")
    if report.color.strip() and report.color.strip().casefold() == candidate.color.strip().casefold():
        score += 15
        reasons.append("Same color")
    if words(report.location) & words(candidate.location):
        score += 20
        reasons.append("Similar general area")
    if abs((report.event_date - candidate.event_date).days) <= 7:
        score += 10
        reasons.append("Dates within seven days")
    return score, tuple(reasons)


def potential_matches(report, limit=20):
    if report.status == Report.Status.RESOLVED:
        return []
    candidates = Report.objects.exclude(kind=report.kind).exclude(status=Report.Status.RESOLVED)
    matches = []
    for candidate in candidates.iterator():
        score, reasons = score_pair(report, candidate)
        if score >= 40:
            matches.append(Match(candidate, score, reasons))
    return sorted(matches, key=lambda m: (-m.score, -m.report.created_at.timestamp(), str(m.report.id)))[:limit]
