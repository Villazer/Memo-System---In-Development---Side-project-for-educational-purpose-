from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        qs = Notification.objects.for_user(self.request.user).select_related("memo")
        f = self.request.GET.get("filter", "all")
        if f == "unread":
            qs = qs.unread()
        elif f == "read":
            qs = qs.filter(is_read=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update({
            "breadcrumbs": [{"label": "Notifications"}],
            "active_filter": self.request.GET.get("filter", "all"),
            "total_count": Notification.objects.for_user(user).count(),
            "unread_count_all": Notification.objects.for_user(user).unread().count(),
        })
        return context


class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.mark_read()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok"})
        return redirect(request.POST.get("next") or reverse("notifications:list"))


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        updated = Notification.objects.for_user(request.user).unread().update(is_read=True)
        messages.success(request, f"{updated} notification(s) marked as read.")
        return redirect(request.POST.get("next") or reverse("notifications:list"))


class DeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.delete()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "deleted"})
        messages.success(request, "Notification dismissed.")
        return redirect(reverse("notifications:list"))


class UnreadCountView(LoginRequiredMixin, View):
    def get(self, request):
        count = Notification.objects.for_user(request.user).unread().count()
        return JsonResponse({"unread_count": count})
