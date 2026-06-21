from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.permissions import SuperadminRequiredMixin
from accounts.forms import UserCreateForm, UserUpdateForm
from accounts.models import User
from memos.models import MemoRecipient
from .forms import UserFilterForm


class UserListView(LoginRequiredMixin, SuperadminRequiredMixin, ListView):
    model = User
    template_name = "users/user_list.html"
    context_object_name = "users"
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.select_related("department").order_by("first_name", "last_name")
        q = self.request.GET.get("q")
        role = self.request.GET.get("role")
        dept = self.request.GET.get("department")
        status = self.request.GET.get("status")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q) | Q(email__icontains=q))
        if role:
            qs = qs.filter(role=role)
        if dept:
            qs = qs.filter(department_id=dept)
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "User Management",
            "page_subtitle": "Manage system users, roles, and department assignments.",
            "breadcrumbs": [{"label": "Users"}],
            "filter_form": UserFilterForm(self.request.GET),
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "inactive_users": User.objects.filter(is_active=False).count(),
        })
        return context


class UserCreateView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "users/user_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": UserCreateForm(), "title": "Create User", "subtitle": "Add a new user to the system.",
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": "Create"}],
        })

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.get_full_name() or user.username}' created successfully.")
            return redirect("users:detail", pk=user.pk)
        return render(request, self.template_name, {
            "form": form, "title": "Create User", "subtitle": "Add a new user to the system.",
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": "Create"}],
        })


class UserDetailView(LoginRequiredMixin, SuperadminRequiredMixin, DetailView):
    model = User
    template_name = "users/user_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = self.object
        received = MemoRecipient.objects.filter(recipient=target).select_related("memo").order_by("-memo__sent_at")
        total_received = received.count()
        total_read = received.filter(read_at__isnull=False).count()
        context.update({
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": target.get_full_name() or target.username}],
            "total_received": total_received, "total_read": total_read,
            "read_rate": round((total_read / total_received) * 100) if total_received else 0,
            "created_memos": target.created_memos.order_by("-created_at")[:5],
            "recent_received": received[:5],
        })
        return context


class UserEditView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "users/user_form.html"

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            "form": UserUpdateForm(instance=target), "target_user": target,
            "title": f"Edit User — {target.get_full_name() or target.username}",
            "subtitle": "Update user information, role, and department.",
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": target.get_full_name() or target.username, "url": reverse("users:detail", args=[target.pk])}, {"label": "Edit"}],
        })

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        form = UserUpdateForm(request.POST, instance=target)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.get_full_name() or user.username}' updated.")
            return redirect("users:detail", pk=user.pk)
        return render(request, self.template_name, {
            "form": form, "target_user": target,
            "title": f"Edit User — {target.get_full_name() or target.username}",
            "subtitle": "Update user information, role, and department.",
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": target.get_full_name() or target.username, "url": reverse("users:detail", args=[target.pk])}, {"label": "Edit"}],
        })


class UserToggleActiveView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("users:detail", pk=pk)
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        messages.success(request, f"User '{target.get_full_name() or target.username}' {'activated' if target.is_active else 'deactivated'}.")
        return redirect("users:detail", pk=pk)


class UserResetPasswordView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "users/user_reset_password.html"

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            "target_user": target,
            "breadcrumbs": [{"label": "Users", "url": reverse("users:list")}, {"label": target.get_full_name() or target.username, "url": reverse("users:detail", args=[target.pk])}, {"label": "Reset Password"}],
        })

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        if not new_password or len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("users:reset_password", pk=pk)
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("users:reset_password", pk=pk)
        target.set_password(new_password)
        target.save(update_fields=["password"])
        messages.success(request, f"Password for '{target.get_full_name() or target.username}' has been reset.")
        return redirect("users:detail", pk=pk)
