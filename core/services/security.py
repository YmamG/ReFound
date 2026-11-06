from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from core.models import SubmissionWindow


def allow_submission(request):
    """Shared DB-backed limit: 10 attempts per IP per ten minutes, including invalid attempts.

    Trust REMOTE_ADDR only. Deployments behind a proxy must configure trusted client
    address handling at the web server; never trust arbitrary forwarding headers.
    """
    now = timezone.now()
    key = salted_hmac("refound-rate", request.META.get("REMOTE_ADDR", "unknown"), algorithm="sha256").hexdigest()
    with transaction.atomic():
        SubmissionWindow.objects.filter(started_at__lt=now - timedelta(days=1)).delete()
        window, _ = SubmissionWindow.objects.get_or_create(key=key)
        # Conditional UPDATE makes consumption atomic across worker processes.
        SubmissionWindow.objects.filter(pk=key, started_at__lte=now - timedelta(minutes=10)).update(started_at=now, count=0)
        from django.db.models import F
        return bool(SubmissionWindow.objects.filter(pk=key, count__lt=10).update(count=F("count") + 1))
