from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("<int:pk>/read/", views.MarkNotificationReadView.as_view(), name="mark_read"),
    path("mark-all-read/", views.MarkAllReadView.as_view(), name="mark_all_read"),
    path("<int:pk>/delete/", views.DeleteNotificationView.as_view(), name="delete"),
    path("unread-count/", views.UnreadCountView.as_view(), name="unread_count"),
]
