from django.contrib import admin
from .models import Report, Claim, AbuseReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "category", "status", "created_at")
    list_filter = ("kind", "category", "status")
    search_fields = ("title", "description")
    exclude = ("management_hash",)

    def has_add_permission(self, request):
        return False  # Owner keys must be issued through the submission workflow.


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("report", "created_at")


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ("report", "created_at")
