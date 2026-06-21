from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("M.I.N.D.S Info", {"fields": ("role", "department")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("M.I.N.D.S Info", {"fields": ("role", "department")}),
    )
