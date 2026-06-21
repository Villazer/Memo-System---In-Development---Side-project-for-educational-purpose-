from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from memos.models import Memorandum, MemoRecipient
from notifications.models import Notification
from departments.models import Department


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_superadmin:
            context.update(self._superadmin_context(user))
        elif user.is_admin:
            context.update(self._admin_context(user))
        else:
            context.update(self._staff_context(user))

        context["recent_activity"] = (
            Notification.objects.for_user(user).select_related("memo")[:5]
        )
        return context

    def _superadmin_context(self, user):
        all_memos = Memorandum.objects.all()
        pending   = all_memos.filter(status=Memorandum.Status.PENDING)
        sent      = all_memos.filter(status=Memorandum.Status.SENT)
        return {
            "role_view": "superadmin",
            "stats": [
                {"label": "Total Memos",      "value": all_memos.count(),       "icon": "envelope",    "color": "primary"},
                {"label": "Pending Approval", "value": pending.count(),          "icon": "clock",       "color": "warning"},
                {"label": "Sent",             "value": sent.count(),             "icon": "paper-plane", "color": "success"},
                {"label": "Departments",      "value": Department.objects.count(),"icon": "building",   "color": "info"},
            ],
            "pending_memos": pending.select_related("created_by").order_by("-submitted_at")[:5],
            "recent_sent":   sent.select_related("created_by").order_by("-sent_at")[:5],
            "quick_actions": [
                {"label": "Create Memo",       "url": "memos:create",     "icon": "plus",       "color": "primary"},
                {"label": "Pending Approvals", "url": "memos:pending",    "icon": "clock",      "color": "warning"},
                {"label": "Manage Users",      "url": "users:list",       "icon": "users",      "color": "info"},
                {"label": "Reports",           "url": "reports:index",    "icon": "chart-line", "color": "success"},
            ],
        }

    def _admin_context(self, user):
        my_memos = Memorandum.objects.filter(created_by=user)
        pending  = Memorandum.objects.visible_to(user).filter(status=Memorandum.Status.PENDING)  # <-- changed
        approved = my_memos.filter(status=Memorandum.Status.APPROVED)
        sent     = my_memos.filter(status=Memorandum.Status.SENT)
        sent_list = list(sent[:20])
        avg_read_rate = (
            sum(m.read_rate for m in sent_list) // len(sent_list)
            if sent_list else 0
        )
        return {
            "role_view": "admin",
            "stats": [
                {"label": "Pending Approval",  "value": pending.count(),    "icon": "clock",        "color": "warning"},
                {"label": "Approved (unsent)", "value": approved.count(),   "icon": "circle-check", "color": "info"},
                {"label": "My Sent Memos",     "value": sent.count(),       "icon": "paper-plane",  "color": "success"},
                {"label": "Avg. Read Rate",    "value": f"{avg_read_rate}%","icon": "chart-pie",    "color": "primary"},
            ],
            "pending_memos":  pending.select_related("created_by").order_by("-submitted_at")[:5],
            "approved_memos": approved.order_by("-approved_at")[:5],
            "recent_sent":    sent.order_by("-sent_at")[:5],
            "quick_actions": [
                {"label": "Create Memo",       "url": "memos:create",  "icon": "plus",       "color": "primary"},
                {"label": "Pending Approvals", "url": "memos:pending", "icon": "clock",      "color": "warning"},
                {"label": "Sent Memos",        "url": "memos:sent",    "icon": "paper-plane","color": "success"},
                {"label": "Reports",           "url": "reports:index", "icon": "chart-line", "color": "info"},
            ],
        }

    def _staff_context(self, user):
        my_memos = Memorandum.objects.filter(created_by=user)
        received = MemoRecipient.objects.filter(recipient=user)
        unread   = received.filter(read_at__isnull=True).count()
        rejected = my_memos.filter(status=Memorandum.Status.REJECTED)
        pending  = my_memos.filter(status=Memorandum.Status.PENDING)
        recent_received = (
            Memorandum.objects
            .filter(recipients__recipient=user, status=Memorandum.Status.SENT)
            .distinct().order_by("-sent_at")[:5]
        )
        read_ids = set(received.filter(read_at__isnull=False).values_list("memo_id", flat=True))
        for memo in recent_received:
            memo.is_unread_for_user = memo.id not in read_ids
        return {
            "role_view": "staff",
            "stats": [
                {"label": "Unread Memos",   "value": unread,           "icon": "envelope",     "color": "danger"},
                {"label": "My Pending",     "value": pending.count(),  "icon": "clock",        "color": "warning"},
                {"label": "Rejected",       "value": rejected.count(), "icon": "xmark-circle", "color": "danger"},
                {"label": "Total Received", "value": received.count(), "icon": "inbox",        "color": "primary"},
            ],
            "recent_received": recent_received,
            "rejected_memos":  rejected.order_by("-rejected_at")[:3],
            "pending_memos":   pending.order_by("-submitted_at")[:3],
            "quick_actions": [
                {"label": "My Memos",      "url": "memos:my_memos", "icon": "file-lines","color": "primary"},
                {"label": "Create Memo",   "url": "memos:create",   "icon": "plus",      "color": "success"},
                {"label": "Inbox",         "url": "memos:assigned", "icon": "inbox",     "color": "info"},
                {"label": "Notifications", "url": "notifications:list","icon": "bell",   "color": "warning"},
            ],
        }
