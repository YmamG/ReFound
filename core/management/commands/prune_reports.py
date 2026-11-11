from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Report


class Command(BaseCommand):
    help = 'Preview expired reports; use --execute to permanently delete reports and related data.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true')

    def handle(self, *args, **options):
        queryset = Report.objects.filter(created_at__lte=timezone.now() - timedelta(days=settings.REFOUND_DELETE_DAYS))
        count = queryset.count()
        if options['execute']:
            queryset.delete()
            self.stdout.write(f'Deleted {count} expired reports. Images are removed after commit.')
        else:
            self.stdout.write(f'Dry run: {count} reports exceed {settings.REFOUND_DELETE_DAYS} days. No data deleted.')
