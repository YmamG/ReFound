from django.conf import settings
from django.shortcuts import render
from .services.security import allow_submission


def error_response(request, status, heading, explanation):
    response = render(request, 'core/error.html', {'status': status, 'heading': heading, 'explanation': explanation}, status=status)
    if status == 429:
        response['Retry-After'] = '600'
    return response


class RequestSafetyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            size = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            size = 0
        if size > settings.REFOUND_MAX_REQUEST_BYTES:
            response = error_response(request, 413, 'That upload is a little too large', 'Choose a JPEG or PNG up to 5 MB, then try again.')
        else:
            response = self.get_response(request)
            if getattr(request, 'refound_upload_too_large', False):
                response = error_response(request, 413, 'That photo is too large', 'Choose a JPEG or PNG up to 5 MB. Your report has not been submitted.')
        if not request.path.startswith('/admin/'):
            response.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")
        response['Permissions-Policy'] = 'geolocation=(), microphone=()'
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Parse bounded multipart streams before any view can write to the database.
        # A discarded oversized optional image must never become a photo-less report.
        if request.method == 'POST' and request.content_type == 'multipart/form-data':
            request.FILES
            if getattr(request, 'refound_upload_too_large', False):
                return error_response(request, 413, 'That photo is too large', 'Choose a JPEG or PNG up to 5 MB. Nothing was submitted.')
        if request.method == 'POST' and request.path == '/admin/login/' and not allow_submission(request, scope='admin-login'):
            return error_response(request, 429, 'Please take a short break', 'Too many sign-in attempts. Try again in ten minutes.')
