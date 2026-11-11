import secrets
from datetime import timedelta
from django.conf import settings

from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from .forms import ReportForm, ClaimForm, AbuseForm, ManagementForm, StatusForm, BrowseForm, OwnerLookupForm
from .models import Report
from .services.matching import potential_matches
from .services.security import allow_submission, grant_access, has_access
from .middleware import error_response


def public_report(pk):
    return get_object_or_404(Report, pk=pk, is_hidden=False)


def throttled(request):
    return error_response(request, 429, 'A little breathing room', 'Too many attempts. Please try again in ten minutes. Your information has not been submitted.')


@require_safe
def home(request):
    recent = Report.objects.filter(is_hidden=False, status=Report.Status.ACTIVE, created_at__gt=timezone.now() - timedelta(days=settings.REFOUND_ARCHIVE_DAYS))
    building = request.session.get('building')
    if building in Report.Building.values:
        recent = recent.filter(building=building)
    recent = recent.order_by('-created_at', '-id')[:4]
    return render(request, 'core/home.html', {'recent_reports': recent})


@require_safe
def about(request):
    return render(request, 'core/about.html')


@require_safe
def contact(request):
    return render(request, 'core/contact.html')


@require_safe
def browse(request, archived=False):
    params = request.GET.copy()
    if 'building' not in params and request.session.get('building'):
        params['building'] = request.session['building']
    form = BrowseForm(params)
    reports = Report.objects.filter(is_hidden=False)
    cutoff = timezone.now() - timedelta(days=settings.REFOUND_ARCHIVE_DAYS)
    reports = reports.filter(created_at__lte=cutoff) if archived else reports.filter(created_at__gt=cutoff)
    if form.is_valid():
        data = form.cleaned_data
        for field in ('kind', 'category', 'status', 'building'):
            if data.get(field):
                reports = reports.filter(**{field: data[field]})
        if data.get('q'):
            reports = reports.filter(Q(title__icontains=data['q']) | Q(description__icontains=data['q']) | Q(color__icontains=data['q']))
        if data.get('location'):
            reports = reports.filter(Q(location__icontains=data['location']) | Q(classroom__icontains=data['location']))
        if data.get('color'):
            reports = reports.filter(color__iexact=data['color'])
        reports = reports.order_by('created_at', 'id') if data.get('sort') == 'oldest' else reports.order_by('-created_at', '-id')
    else:
        reports = reports.none()
    page = Paginator(reports, 12).get_page(request.GET.get('page'))
    params.pop('page', None)
    for key in list(params):
        if key not in form.fields:
            params.pop(key)
    return render(request, 'core/browse.html', {'form': form, 'page_obj': page, 'querystring': params.urlencode(), 'archived': archived})


def new_intent(request):
    intents = request.session.get('report_forms', {})
    if not isinstance(intents, dict):
        intents = {}
    while len(intents) >= 12:
        intents.pop(next(iter(intents)))
    nonce = secrets.token_urlsafe(20)
    intents[nonce] = None
    request.session['report_forms'] = intents
    return nonce


@never_cache
@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters('contact_info')
def submit(request, kind):
    if kind not in Report.Kind.values:
        raise Http404
    if getattr(request, 'refound_upload_too_large', False):
        return error_response(request, 413, 'That photo is too large', 'Choose a still JPEG or PNG up to 5 MB, then try again.')
    form = ReportForm(request.POST if request.method == 'POST' else None, request.FILES or None, initial={'building': request.session.get('building', '')})
    if request.method == 'GET':
        nonce = new_intent(request)
    else:
        nonce = request.POST.get('submission_id', '')
        intents = request.session.get('report_forms', {})
        if nonce and intents.get(nonce):
            # A refresh/retry of the successful POST must not create another report.
            return redirect('core:manage', pk=intents[nonce])
        if not allow_submission(request):
            return throttled(request)
        if not nonce or nonce not in intents:
            form.add_error(None, 'This form has expired. Review your details, select your photo again if needed, and submit once more.')
            return render(request, 'core/submit.html', {'form': form, 'kind': kind, 'kind_label': Report.Kind(kind).label, 'submission_id': new_intent(request)}, status=400)
        if form.is_valid():
            report = form.save(commit=False)
            report.kind = kind
            report.owner = request.device
            report.management_hash = make_password(None)
            report.save()
            intents[nonce] = str(report.pk)
            request.session['report_forms'] = intents
            messages.success(request, 'Your report is published and saved in this browser’s My reports.')
            return redirect('core:manage', pk=report.pk)
    return render(request, 'core/submit.html', {'form': form, 'kind': kind, 'kind_label': Report.Kind(kind).label, 'submission_id': nonce})


@never_cache
@require_safe
def confirmation(request):
    return redirect('core:browse')


@require_safe
def detail(request, pk):
    return render(request, 'core/detail.html', {'report': public_report(pk)})


@require_safe
def matches(request, pk):
    report = public_report(pk)
    return render(request, 'core/matches.html', {'report': report, 'matches': potential_matches(report)})


@never_cache
@require_safe
def image(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if report.is_hidden and not (has_access(request, report) or request.user.has_perm('core.view_report')):
        raise Http404
    if not report.image:
        raise Http404
    try:
        response = FileResponse(report.image.open('rb'), content_type='image/jpeg')
    except FileNotFoundError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response


@never_cache
@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters('reply_email', 'message')
def claim(request, pk):
    report = public_report(pk)
    if report.is_archived:
        return error_response(request, 410, "This report is archived", "Archived reports no longer accept new messages.")
    if report.status == Report.Status.RESOLVED:
        return error_response(request, 410, 'This story has a happy ending', 'This report is resolved and is no longer accepting messages.')
    if request.method == 'POST' and not allow_submission(request):
        return throttled(request)
    form = ClaimForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.report = report
        entry.save()
        messages.success(request, 'Message saved privately. The owner can read it in their inbox and reply using your email. No automatic notification is sent.')
        return redirect('core:detail', pk=pk)
    return render(request, 'core/action_form.html', {'form': form, 'report': report, 'heading': 'Make a connection', 'action_kind': 'message', 'explanation': 'Describe what makes the item yours, or share a helpful lead. Only the report owner and authorized moderators can read your message.'})


@never_cache
@require_http_methods(['GET', 'POST'])
def abuse(request, pk):
    report = public_report(pk)
    if request.method == 'POST' and not allow_submission(request):
        return throttled(request)
    form = AbuseForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.report = report
        entry.save()
        messages.success(request, 'Your concern has been saved for moderator review. Thank you for helping keep ReFound safe.')
        return redirect('core:detail', pk=pk)
    return render(request, 'core/action_form.html', {'form': form, 'report': report, 'heading': 'Help keep this space safe', 'action_kind': 'abuse', 'explanation': 'Tell our moderators about inappropriate content, a misleading report, or a privacy concern. Your concern is not shown publicly.'})


@never_cache
@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters('token')
def owner_lookup(request):
    form = OwnerLookupForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if not allow_submission(request):
            return throttled(request)
        if form.is_valid():
            report = Report.objects.filter(pk=form.cleaned_data['report_link']).first()
            if report and not report.owner_id and check_password(form.cleaned_data['token'], report.management_hash):
                grant_access(request, report)
                return redirect('core:manage', pk=report.pk)
            form.add_error(None, 'We could not unlock that report. Check the report link and management key.')
    return render(request, 'core/owner_lookup.html', {'form': form})


@never_cache
@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters('token')
def manage(request, pk):
    report = get_object_or_404(Report, pk=pk)
    authorized = has_access(request, report)
    form = ManagementForm(request.POST if request.method == 'POST' else None)
    status_form = StatusForm(instance=report)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'unlock':
            if not allow_submission(request):
                return throttled(request)
            if not report.owner_id and form.is_valid() and check_password(form.cleaned_data['token'], report.management_hash):
                grant_access(request, report)
                return redirect('core:manage', pk=pk)
            form.add_error(None, 'Invalid management key.')
        elif not authorized:
            return error_response(request, 403, 'Use the original browser', 'Only the browser that created this report can manage it. The displayed device number does not grant access.')
        elif action == 'lock':
            request.session.pop('manage_' + str(pk), None)
            return redirect('core:manage', pk=pk)
        elif action == 'delete':
            if request.POST.get('confirm_delete') != 'yes':
                return error_response(request, 400, 'Please confirm deletion', 'Check the confirmation box before permanently deleting your report.')
            report.delete()
            request.session.pop('manage_' + str(pk), None)
            messages.success(request, 'Your report and private messages have been deleted.')
            return redirect('core:browse')
        elif action == 'status':
            status_form = StatusForm(request.POST, instance=report)
            if status_form.is_valid():
                status_form.save()
                messages.success(request, 'Your report status has been updated.')
                return redirect('core:manage', pk=pk)
        else:
            return error_response(request, 400, 'That action is not available', 'Use one of the controls on your management page.')
    inbox = Paginator(report.claims.order_by('-created_at', '-pk'), 10).get_page(request.GET.get('page')) if authorized else None
    return render(request, 'core/manage.html', {'report': report, 'form': form, 'authorized': authorized, 'status_form': status_form, 'inbox': inbox})


def bad_request(request, exception=None):
    return error_response(request, 400, 'Something did not look right', 'Check the link or form and try again.')


def permission_denied(request, exception=None):
    return error_response(request, 403, 'This page needs permission', 'Use your management key to access your private report inbox.')


def not_found(request, exception=None):
    return error_response(request, 404, 'A little lost?', 'This report may have been removed, or the link may be incomplete. Let’s get you back to the board.')


def server_error(request):
    return error_response(request, 500, 'We hit a small detour', 'Please try again shortly. If this keeps happening, use the help page.')


def csrf_failure(request, reason=''):
    return error_response(request, 403, 'Let’s refresh that page', 'Your secure form session could not be verified. Reload the form and try again. Nothing was submitted.')

@never_cache
@require_safe
def my_reports(request):
    reports = request.device.reports.order_by('-created_at', '-id')
    return render(request, 'core/my_reports.html', {'page_obj': Paginator(reports, 12).get_page(request.GET.get('page'))})


@require_http_methods(['POST'])
def select_building(request):
    building = request.POST.get('building')
    if building not in Report.Building.values:
        return error_response(request, 400, 'Choose a building', 'Choose the men’s or women’s building at the College of Computing.')
    request.session['building'] = building
    return redirect('core:home')


@never_cache
@require_http_methods(['GET', 'POST'])
@sensitive_post_parameters('token')
def import_legacy(request):
    form = OwnerLookupForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if not allow_submission(request):
            return throttled(request)
        if form.is_valid():
            report = Report.objects.filter(pk=form.cleaned_data['report_link'], owner__isnull=True).first()
            if report and check_password(form.cleaned_data['token'], report.management_hash):
                updated = Report.objects.filter(pk=report.pk, owner__isnull=True).update(owner=request.device, management_hash=make_password(None))
                if updated:
                    request.session.pop('manage_' + str(report.pk), None)
                    messages.success(request, 'The old report is now linked to this browser. Its old key no longer works.')
                    return redirect('core:manage', pk=report.pk)
            form.add_error(None, 'We could not link that report. Check its ID and old management key.')
    return render(request, 'core/import_legacy.html', {'form': form})


@require_safe
def add_report(request):
    return render(request, 'core/add_report.html')
