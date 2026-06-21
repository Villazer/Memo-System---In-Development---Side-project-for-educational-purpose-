from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from memos.models import Memorandum
from settings_app.models import SystemSetting


class Command(BaseCommand):
    help = "Archives sent memorandums older than the configured threshold (default 365 days)."

    def handle(self, *args, **options):
        days = int(SystemSetting.get("archive_threshold_days", "365"))
        threshold = timezone.now() - timedelta(days=days)
        qs = Memorandum.objects.filter(
            status=Memorandum.Status.SENT,
            created_at__lt=threshold,
        )
        count = qs.count()
        for memo in qs:
            memo.archive()
        self.stdout.write(
            self.style.SUCCESS(f"Archived {count} memo(s) older than {days} days.")
        )
