from django.contrib import admin
from .models import Memorandum, MemoRecipient, ApprovalHistory


class MemoRecipientInline(admin.TabularInline):
    model = MemoRecipient
    extra = 0
    readonly_fields = ("read_at", "created_at")


class ApprovalHistoryInline(admin.TabularInline):
    model = ApprovalHistory
    extra = 0
    readonly_fields = ("actor", "action", "comments", "created_at")
    can_delete = False


@admin.register(Memorandum)
class MemorandumAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "priority", "created_by",
        "submitted_at", "approved_by", "rejected_by", "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "body", "created_by__username")
    readonly_fields = (
        "created_at", "updated_at", "sent_at",
        "submitted_at", "approved_at", "rejected_at",
    )
    filter_horizontal = ("departments",)
    inlines = [MemoRecipientInline, ApprovalHistoryInline]


@admin.register(MemoRecipient)
class MemoRecipientAdmin(admin.ModelAdmin):
    list_display = ("memo", "recipient", "read_at", "created_at")
    list_filter  = ("read_at",)


@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ("memo", "actor", "action", "created_at")
    list_filter  = ("action",)
    readonly_fields = ("created_at",)
