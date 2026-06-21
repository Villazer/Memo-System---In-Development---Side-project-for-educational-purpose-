from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        ADMIN      = "admin",      "Admin"
        STAFF      = "staff",      "Staff"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="members",
    )

    @property
    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff_role(self):
        return self.role == self.Role.STAFF

    def can_create_memos(self):
        """All authenticated users can create memos."""
        return True

    def can_send_directly(self):
        """Only admins and superadmins can send without approval."""
        return self.role in (self.Role.SUPERADMIN, self.Role.ADMIN)

    def can_manage_users(self):
        return self.role == self.Role.SUPERADMIN

    def can_manage_departments(self):
        return self.role == self.Role.SUPERADMIN

    def can_view_all_memos(self):
        return self.role == self.Role.SUPERADMIN

    def __str__(self):
        return self.get_full_name() or self.username
