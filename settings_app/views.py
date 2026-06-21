from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View

from core.permissions import SuperadminRequiredMixin
from accounts.models import User
from departments.models import Department
from memos.models import Memorandum
from notifications.models import Notification
from .forms import SystemSettingForm
from .models import SystemSetting


class SettingsIndexView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "settings_app/settings.html"

    def get(self, request):
        form = SystemSettingForm()
        form.load_from_db()
        return render(request, self.template_name, {
            "form": form,
            "breadcrumbs": [{"label": "Settings"}],
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "total_departments": Department.objects.count(),
            "total_memos": Memorandum.objects.count(),
            "total_notifications": Notification.objects.count(),
            "current_settings": {k: SystemSetting.get(k, "—") for k in ["org_name", "org_tagline", "archive_threshold_days", "allow_staff_to_view_sender", "memos_per_page"]},
        })

    def post(self, request):
        form = SystemSettingForm(request.POST)
        if form.is_valid():
            form.save_to_db()
            messages.success(request, "System settings saved successfully.")
            return redirect("settings_app:index")
        return render(request, self.template_name, {
            "form": form, "breadcrumbs": [{"label": "Settings"}],
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "total_departments": Department.objects.count(),
            "total_memos": Memorandum.objects.count(),
            "total_notifications": Notification.objects.count(),
            "current_settings": {k: SystemSetting.get(k, "—") for k in ["org_name", "org_tagline", "archive_threshold_days", "allow_staff_to_view_sender", "memos_per_page"]},
        })
