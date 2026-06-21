from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = []

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role in self.allowed_roles

    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this page.")


class SuperadminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["superadmin"]


class AdminOrSuperadminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ["superadmin", "admin"]


class MemoOwnerOrSuperadminMixin(UserPassesTestMixin):
    def test_func(self):
        memo = self.get_object()
        user = self.request.user
        return user.is_superadmin or memo.created_by_id == user.id

    def handle_no_permission(self):
        raise PermissionDenied("You cannot modify this memorandum.")
