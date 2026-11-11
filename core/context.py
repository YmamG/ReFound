from django.conf import settings
from .models import Report


def site(request):
    building = getattr(request, 'session', {}).get('building', '')
    return {
        'device_number': request.device.number if hasattr(request, 'device') and not request.path.startswith('/admin/') else '',
        'support_email': settings.REFOUND_SUPPORT_EMAIL,
        'current_building': building,
        'current_building_label': dict(Report.Building.choices).get(building, ''),
        'archive_days': settings.REFOUND_ARCHIVE_DAYS,
        'delete_days': settings.REFOUND_DELETE_DAYS,
    }
