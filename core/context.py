from django.conf import settings


def site(request):
    return {'support_email': settings.REFOUND_SUPPORT_EMAIL}
