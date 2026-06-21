from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("memos/", include("memos.urls")),
    path("notifications/", include("notifications.urls")),
    path("departments/", include("departments.urls")),
    path("users/", include("users.urls")),
    path("reports/", include("reports.urls")),
    path("settings/", include("settings_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
