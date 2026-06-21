from django.contrib import admin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "member_count", "active_memo_count", "created_at")
    search_fields = ("name", "code")
    readonly_fields = ("created_at",)
    ordering = ("name",)
