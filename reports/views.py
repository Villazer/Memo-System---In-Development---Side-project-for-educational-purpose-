from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView
from datetime import timedelta
import json

from core.permissions import AdminOrSuperadminRequiredMixin
from departments.models import Department
from memos.models import Memorandum, MemoRecipient


class ReportsDashboardView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, TemplateView):
    template_name = "reports/report_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        memo_qs   = Memorandum.objects.visible_to(user)
        sent_memos = memo_qs.sent()
        total_sent     = sent_memos.count()
        total_draft    = memo_qs.drafts().count()
        total_archived = memo_qs.archived().count()
        total_pending  = memo_qs.pending_approval().count()
        total_approved = memo_qs.approved().count()

        all_recipients = MemoRecipient.objects.filter(memo__in=sent_memos)
        total_recs  = all_recipients.count()
        total_read  = all_recipients.filter(read_at__isnull=False).count()
        overall_read_rate = round((total_read / total_recs) * 100) if total_recs else 0

        status_data = {
            "labels": ["Sent", "Draft", "Pending", "Approved", "Archived"],
            "values": [total_sent, total_draft, total_pending, total_approved, total_archived],
            "colors": ["#16a34a", "#64748b", "#d97706", "#1d4ed8", "#94a3b8"],
        }

        priority_counts = {
            p["priority"]: p["count"]
            for p in sent_memos.values("priority").annotate(count=Count("id"))
        }
        priority_data = {
            "labels": ["Normal", "Important", "Urgent"],
            "values": [
                priority_counts.get("normal", 0),
                priority_counts.get("important", 0),
                priority_counts.get("urgent", 0),
            ],
            "colors": ["#64748b", "#d97706", "#dc2626"],
        }

        six_months_ago = now - timedelta(days=180)
        monthly = (
            memo_qs.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        departments = (
            Department.objects.all()
            if user.is_superadmin
            else Department.objects.filter(id=user.department_id)
        )
        dept_stats = []
        for dept in departments:
            dept_sent = memo_qs.filter(departments=dept, status="sent")
            dr    = MemoRecipient.objects.filter(memo__in=dept_sent)
            drt   = dr.count()
            drr   = dr.filter(read_at__isnull=False).count()
            dept_stats.append({
                "department": dept,
                "total": memo_qs.filter(departments=dept).count(),
                "sent":  dept_sent.count(),
                "draft": memo_qs.filter(departments=dept, status="draft").count(),
                "read_rate": round((drr / drt) * 100) if drt else 0,
            })

        all_sent_list = list(sent_memos.prefetch_related("recipients")[:30])
        memo_rates = [
            {"memo": m, "read_rate": m.read_rate,
             "read_count": m.read_count, "total": m.total_recipients}
            for m in all_sent_list if m.total_recipients > 0
        ]
        most_read  = sorted(memo_rates, key=lambda x: x["read_rate"], reverse=True)[:5]
        least_read = sorted(
            [m for m in memo_rates if m["read_rate"] < 100],
            key=lambda x: x["read_rate"]
        )[:5]

        top_unread = (
            MemoRecipient.objects.filter(read_at__isnull=True)
            .values("recipient__id", "recipient__first_name",
                    "recipient__last_name", "recipient__username",
                    "recipient__department__name")
            .annotate(unread_count=Count("id"))
            .order_by("-unread_count")[:8]
        )
        top_senders = (
            sent_memos
            .values("created_by__id", "created_by__first_name",
                    "created_by__last_name", "created_by__username")
            .annotate(sent_count=Count("id"))
            .order_by("-sent_count")[:8]
        )

        context.update({
            "breadcrumbs": [{"label": "Reports"}],
            "total_memos":    memo_qs.count(),
            "total_sent":     total_sent,
            "total_draft":    total_draft,
            "total_archived": total_archived,
            "overall_read_rate": overall_read_rate,
            "sent_last_30": sent_memos.filter(sent_at__gte=now - timedelta(days=30)).count(),
            "sent_last_7":  sent_memos.filter(sent_at__gte=now - timedelta(days=7)).count(),
            "status_data_json":      json.dumps(status_data),
            "priority_data_json":    json.dumps(priority_data),
            "monthly_labels_json":   json.dumps([m["month"].strftime("%b %Y") for m in monthly]),
            "monthly_values_json":   json.dumps([m["count"] for m in monthly]),
            "dept_stats":   dept_stats,
            "top_unread":   top_unread,
            "top_senders":  top_senders,
            "most_read":    most_read,
            "least_read":   least_read,
            "has_data":     total_sent > 0,
        })
        return context
