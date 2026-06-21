from django.apps import AppConfig

class MemosConfig(AppConfig):
    name = "memos"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import memos.signals  # noqa
