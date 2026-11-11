from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Report, Claim, AbuseReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'category', 'status', 'building', 'is_hidden', 'created_at')
    list_filter = ('is_hidden', 'kind', 'category', 'status', 'building')
    search_fields = ('title', 'description', '=id')
    exclude = ('management_hash', 'image')
    readonly_fields = ('owner', 'id', 'image_preview', 'created_at', 'updated_at')
    actions = ('hide_reports', 'restore_reports')

    def has_add_permission(self, request):
        return False

    @admin.display(description='Sanitized item photo')
    def image_preview(self, obj):
        if not obj.image:
            return 'No image'
        return format_html('<a href="{}">View item image</a>', reverse('core:image', args=[obj.pk]))

    @admin.action(description='Hide selected reports from public pages')
    def hide_reports(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description='Restore selected reports to public pages')
    def restore_reports(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('report', 'created_at')
    readonly_fields = ('report', 'message', 'reply_email', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ('report', 'reviewed', 'created_at')
    list_filter = ('reviewed', 'created_at')
    readonly_fields = ('report', 'reason', 'created_at')
    actions = ('mark_reviewed',)

    @admin.action(description='Mark selected concerns as reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(reviewed=True)

    def has_add_permission(self, request):
        return False
