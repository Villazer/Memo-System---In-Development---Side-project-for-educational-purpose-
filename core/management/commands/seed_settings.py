from django.core.management.base import BaseCommand
from settings_app.models import SystemSetting

DEFAULTS = [
    ("org_name", "M.I.N.D.S", "Organization display name"),
    ("org_tagline", "Memo Distribution", "Sidebar tagline"),
    ("archive_threshold_days", "365", "Days before auto-archive"),
    ("allow_staff_to_view_sender", "true", "Show sender name to staff"),
    ("memos_per_page", "10", "Memos per page in list views"),
]


class Command(BaseCommand):
    help = "Seed default system settings into the database."

    def handle(self, *args, **options):
        created = 0
        for key, value, description in DEFAULTS:
            _, was_created = SystemSetting.objects.get_or_create(key=key, defaults={"value": value, "description": description})
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new setting(s). {len(DEFAULTS) - created} already existed."))
