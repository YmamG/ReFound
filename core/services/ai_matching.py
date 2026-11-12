"""Optional public preview on the experimental branch. Offline local MiniLM; never imports ML when disabled."""
import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from threading import Lock

from django.conf import settings
from django.utils import timezone
from .matching import potential_matches, score_pair
from core.models import Report

logger = logging.getLogger(__name__)
_MODEL_LOCK = Lock()


@dataclass(frozen=True)
class PreviewMatch:
    report: Report
    score: float
    rule_score: int
    cosine: float


@lru_cache(maxsize=1)
def model():
    path = Path(settings.REFOUND_AI_MODEL_PATH)
    if not settings.REFOUND_AI_MODEL_PATH or not (path / 'modules.json').is_file():
        raise RuntimeError('Local model directory is unavailable')
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(2)
    encoder = SentenceTransformer(str(path), device='cpu', local_files_only=True, trust_remote_code=False)
    if encoder.get_sentence_embedding_dimension() != 384 or encoder.max_seq_length != 128:
        raise ValueError('Unexpected model dimensions or token limit')
    return encoder


def preview_matches(report, limit=20):
    """Return explicit mode + candidates. No inferred ownership or status changes."""
    fallback = lambda: {'mode': 'rules', 'matches': potential_matches(report, limit), 'truncated': False}
    if not settings.REFOUND_AI_PREVIEW_ENABLED:
        return fallback()
    if report.is_hidden or report.is_archived or report.status == Report.Status.RESOLVED:
        return {'mode': 'ai', 'matches': [], 'truncated': False}
    candidates = list(Report.objects.filter(building=report.building, is_hidden=False,
        created_at__gt=timezone.now()-timedelta(days=settings.REFOUND_ARCHIVE_DAYS))
        .exclude(kind=report.kind).exclude(status=Report.Status.RESOLVED)
        .only('id','title','description','category','color','location','classroom',
              'event_date','building','status','kind','created_at','image')
        .order_by('-created_at','id')[:201])
    truncated = len(candidates) > 200
    candidates = candidates[:200]
    if not candidates:
        return {'mode': 'ai', 'matches': [], 'truncated': False}
    # Public item text only: never contact information, private claims or credentials.
    text = lambda r: f'{r.title}. {r.description}'.strip()[:1200]
    try:
        # One CPU inference at a time per worker, including lazy model startup.
        if not _MODEL_LOCK.acquire(blocking=False):
            return fallback()
        try:
            encoder = model()
            vectors = encoder.encode([text(report), *[text(r) for r in candidates]],
                normalize_embeddings=True, show_progress_bar=False, batch_size=16)
        finally:
            _MODEL_LOCK.release()
        matches = []
        for candidate, vector in zip(candidates, vectors[1:]):
            cosine = max(-1.0, min(1.0, float(vectors[0] @ vector)))
            rule_score, _ = score_pair(report, candidate)
            # Initial experimental blend, not calibrated against prior held-out tests.
            score = .65 * rule_score + .35 * max(0.0, cosine) * 100
            matches.append(PreviewMatch(candidate, round(score, 1), rule_score, round(cosine, 4)))
        matches.sort(key=lambda m: (-m.score, -m.report.created_at.timestamp(), str(m.report.pk)))
        return {'mode': 'ai', 'matches': matches[:limit], 'truncated': truncated}
    except Exception as exc:
        logger.warning('AI preview unavailable (%s); using rules', type(exc).__name__)
        return fallback()
