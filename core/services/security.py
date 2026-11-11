from datetime import timedelta
import ipaddress
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac, constant_time_compare
from core.models import SubmissionWindow


def client_address(request):
    try:
        remote = ipaddress.ip_address(request.META.get('REMOTE_ADDR', ''))
    except ValueError:
        return 'unknown'
    trusted = [ipaddress.ip_network(value) for value in settings.REFOUND_TRUSTED_PROXY_CIDRS]
    if not any(remote in network for network in trusted):
        return str(remote)
    # Walk from our trusted edge, stopping at the first untrusted hop.
    hops = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') + [str(remote)]
    for value in reversed(hops):
        try:
            address = ipaddress.ip_address(value.strip())
        except ValueError:
            return str(remote)
        if not any(address in network for network in trusted):
            return str(address)
    return str(remote)


def allow_submission(request, scope='public'):
    now = timezone.now()
    key = salted_hmac('refound-rate', scope + ':' + client_address(request), algorithm='sha256').hexdigest()
    # Separate short autocommit statements avoid SQLite read-to-write transaction upgrades.
    # Reset and consume are conditional atomic UPDATEs, safe across worker threads.
    SubmissionWindow.objects.filter(started_at__lt=now - timedelta(days=1)).delete()
    SubmissionWindow.objects.get_or_create(key=key)
    SubmissionWindow.objects.filter(pk=key, started_at__lte=now - timedelta(minutes=10)).update(started_at=now, count=0)
    return bool(SubmissionWindow.objects.filter(pk=key, count__lt=settings.REFOUND_RATE_LIMIT).update(count=F('count') + 1))


def fingerprint(report):
    return salted_hmac('report-management', report.management_hash, algorithm='sha256').hexdigest()


def grant_access(request, report):
    request.session.cycle_key()
    request.session['manage_' + str(report.pk)] = {'fingerprint': fingerprint(report), 'expires': int(timezone.now().timestamp()) + 3600}
    request.session.set_expiry(3600)


def has_access(request, report):
    if report.owner_id:
        return request.device.pk == report.owner_id
    grant = request.session.get('manage_' + str(report.pk))
    return isinstance(grant, dict) and grant.get('expires', 0) > timezone.now().timestamp() and constant_time_compare(grant.get('fingerprint', ''), fingerprint(report))
