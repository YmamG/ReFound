import secrets
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from .forms import ReportForm, ClaimForm, AbuseForm, ManagementForm, StatusForm
from .models import Report
from .services.matching import potential_matches
from .services.security import allow_submission


def home(request):
    return render(request, 'core/home.html')


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    return render(request, 'core/contact.html')


def browse(request):
    reports = Report.objects.all()
    for field in ("kind", "category", "status"):
        value = request.GET.get(field, "")
        if value:
            reports = reports.filter(**{field: value})
    query = request.GET.get("q", "").strip()[:200]
    if query:
        reports = reports.filter(Q(title__icontains=query) | Q(description__icontains=query))
    location = request.GET.get("location", "").strip()[:120]
    if location:
        reports = reports.filter(location__icontains=location)
    reports = reports.order_by("created_at", "id") if request.GET.get("sort") == "oldest" else reports.order_by("-created_at", "-id")
    page = Paginator(reports, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "core/browse.html", {"page_obj": page, "querystring": params.urlencode(), "kinds": Report.Kind.choices, "categories": Report.Category.choices, "statuses": Report.Status.choices})


@never_cache
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("contact_info")
def submit(request, kind):
    if kind not in Report.Kind.values:
        raise Http404
    if request.method == "POST" and not allow_submission(request):
        return HttpResponse("Too many attempts. Please try again in ten minutes.", status=429)
    form = ReportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        token = secrets.token_urlsafe(32)
        report = form.save(commit=False)
        report.kind = kind
        report.management_hash = make_password(token)
        report.save()
        # Display only in this response; never persist the raw key, even in sessions.
        return render(request, "core/confirmation.html", {"id": str(report.pk), "token": token})
    return render(request, "core/submit.html", {"form": form, "kind": kind})


@never_cache
def confirmation(request):
    return redirect("core:browse")


def detail(request, pk):
    return render(request, "core/detail.html", {"report": get_object_or_404(Report, pk=pk)})


def matches(request, pk):
    report = get_object_or_404(Report, pk=pk)
    return render(request, "core/matches.html", {"report": report, "matches": potential_matches(report)})


def image(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if not report.image:
        raise Http404
    try:
        response = FileResponse(report.image.open("rb"), content_type="image/jpeg")
    except FileNotFoundError:
        raise Http404
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@never_cache
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("reply_email", "message")
def claim(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if report.status == Report.Status.RESOLVED:
        return HttpResponse("This report is resolved.", status=410)
    if request.method == "POST" and not allow_submission(request):
        return HttpResponse("Too many attempts. Please try again in ten minutes.", status=429)
    form = ClaimForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.report = report
        entry.save()
        return render(request, "core/message_sent.html", {"report": report})
    return render(request, "core/action_form.html", {"form": form, "report": report, "heading": "Send a private message", "explanation": "Your message and reply email will be available in the owner's management inbox. The owner must check that inbox; automatic notifications are not sent."})


@never_cache
@require_http_methods(["GET", "POST"])
def abuse(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if request.method == "POST" and not allow_submission(request):
        return HttpResponse("Too many attempts. Please try again in ten minutes.", status=429)
    form = AbuseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.report = report
        entry.save()
        return render(request, "core/abuse_sent.html")
    return render(request, "core/action_form.html", {"form": form, "report": report, "heading": "Report abuse", "explanation": "Describe the concern for review by site administrators."})


@never_cache
@require_http_methods(["GET", "POST"])
@sensitive_post_parameters("token")
def manage(request, pk):
    report = get_object_or_404(Report, pk=pk)
    authorized = request.session.get("manage_" + str(pk), False)
    form = ManagementForm(request.POST or None)
    if request.method == "POST":
        if not allow_submission(request):
            return HttpResponse("Too many attempts. Please try again in ten minutes.", status=429)
        action = request.POST.get("action")
        if action == "unlock":
            if form.is_valid() and check_password(form.cleaned_data["token"], report.management_hash):
                request.session.cycle_key()
                request.session["manage_" + str(pk)] = True
                request.session.set_expiry(3600)
                return redirect("core:manage", pk=pk)
            form.add_error(None, "Invalid management key.")
        elif not authorized:
            return HttpResponse("Management key required.", status=403)
        elif action == "lock":
            request.session.pop("manage_" + str(pk), None)
            return redirect("core:manage", pk=pk)
        elif action == "delete":
            # Delete the sanitized upload too; never accept a client-supplied path.
            if report.image:
                report.image.delete(save=False)
            report.delete()
            request.session.pop("manage_" + str(pk), None)
            return redirect("core:browse")
        elif action == "status":
            status_form = StatusForm(request.POST, instance=report)
            if status_form.is_valid():
                status_form.save()
                return redirect("core:manage", pk=pk)
            return render(request, "core/manage.html", {"report": report, "authorized": True, "status_form": status_form})
        else:
            return HttpResponse("Unknown action.", status=400)
    return render(request, "core/manage.html", {"report": report, "form": form, "authorized": authorized, "status_form": StatusForm(instance=report)})
