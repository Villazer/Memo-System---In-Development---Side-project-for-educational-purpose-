from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.permissions import SuperadminRequiredMixin
from .forms import DepartmentForm, DepartmentMemberForm
from .models import Department


class DepartmentListView(LoginRequiredMixin, SuperadminRequiredMixin, ListView):
    model = Department
    template_name = "departments/department_list.html"
    context_object_name = "departments"
    paginate_by = 15

    def get_queryset(self):
        qs = Department.objects.all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import User
        context.update({
            "page_title": "Departments",
            "page_subtitle": "Manage organizational departments and their members.",
            "breadcrumbs": [{"label": "Departments"}],
            "total_departments": Department.objects.count(),
            "total_members": User.objects.filter(department__isnull=False, is_active=True).count(),
        })
        return context


class DepartmentCreateView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": DepartmentForm(),
            "title": "Create Department",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": "Create"},
            ],
        })

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' created successfully.")
            return redirect("departments:detail", pk=dept.pk)
        return render(request, self.template_name, {
            "form": form, "title": "Create Department",
            "breadcrumbs": [{"label": "Departments", "url": reverse("departments:list")}, {"label": "Create"}],
        })


class DepartmentDetailView(LoginRequiredMixin, SuperadminRequiredMixin, DetailView):
    model = Department
    template_name = "departments/department_detail.html"
    context_object_name = "department"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dept = self.object
        members = dept.members.filter(is_active=True).order_by("first_name", "last_name")
        context.update({
            "breadcrumbs": [{"label": "Departments", "url": reverse("departments:list")}, {"label": dept.name}],
            "members": members,
            "recent_memos": dept.memorandums.select_related("created_by").order_by("-created_at")[:5],
            "member_count": members.count(),
            "memo_count": dept.memorandums.count(),
            "sent_memo_count": dept.memorandums.filter(status="sent").count(),
        })
        return context


class DepartmentEditView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_form.html"

    def get(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        return render(request, self.template_name, {
            "form": DepartmentForm(instance=dept), "department": dept,
            "title": f"Edit Department — {dept.name}",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Edit"},
            ],
        })

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            dept = form.save()
            messages.success(request, f"Department '{dept.name}' updated.")
            return redirect("departments:detail", pk=dept.pk)
        return render(request, self.template_name, {
            "form": form, "department": dept, "title": f"Edit Department — {dept.name}",
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Edit"},
            ],
        })


class DepartmentMembersView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    template_name = "departments/department_members.html"

    def _ctx(self, dept, form, **extra):
        from accounts.models import User as UserModel
        all_users = (
            UserModel.objects
            .filter(is_active=True)
            .select_related("department")
            .order_by("department__name", "first_name", "last_name")
        )
        ctx = {
            "form": form,
            "department": dept,
            "all_users": all_users,
            "current_members": (
                dept.members.filter(is_active=True)
                .select_related("department")
                .order_by("first_name")
            ),
            "breadcrumbs": [
                {"label": "Departments", "url": reverse("departments:list")},
                {"label": dept.name, "url": reverse("departments:detail", args=[dept.pk])},
                {"label": "Manage Members"},
            ],
        }
        ctx.update(extra)
        return ctx

    def get(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        return render(request, self.template_name,
                      self._ctx(dept, DepartmentMemberForm(department=dept)))

    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)

        # Confirmed conflict override submitted
        if request.POST.get("confirmed") == "1":
            from accounts.models import User as UserModel
            selected_ids = request.POST.getlist("confirmed_users")
            selected_users = UserModel.objects.filter(pk__in=selected_ids)
            with transaction.atomic():
                dept.members.update(department=None)
                selected_users.update(department=dept)
            messages.success(
                request,
                f"Members updated. {selected_users.count()} member(s) assigned to {dept.name}.",
            )
            return redirect("departments:detail", pk=dept.pk)

        form = DepartmentMemberForm(request.POST, department=dept)
        if not form.is_valid():
            return render(request, self.template_name, self._ctx(dept, form))

        selected_users = list(form.cleaned_data.get("users") or [])
        conflicts = [
            u for u in selected_users
            if u.department and u.department_id != dept.pk
        ]

        if conflicts:
            return render(request, self.template_name, self._ctx(
                dept, form,
                conflicts=conflicts,
                selected_user_ids=[u.pk for u in selected_users],
                show_conflict_modal=True,
            ))

        with transaction.atomic():
            dept.members.update(department=None)
            for u in selected_users:
                u.department = dept
                u.save(update_fields=["department"])
        messages.success(
            request,
            f"Members updated. {len(selected_users)} member(s) assigned to {dept.name}.",
        )
        return redirect("departments:detail", pk=dept.pk)




class DepartmentDeleteView(LoginRequiredMixin, SuperadminRequiredMixin, View):
    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        if dept.members.exists():
            messages.error(request, f"Cannot delete '{dept.name}' — it still has {dept.member_count} member(s). Reassign members first.")
            return redirect("departments:detail", pk=dept.pk)
        name = dept.name
        dept.delete()
        messages.success(request, f"Department '{name}' deleted.")
        return redirect("departments:list")
