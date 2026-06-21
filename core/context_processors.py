from notifications.models import Notification
from memos.models import Memorandum


def global_counts(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    data = {
        "unread_notif_count": Notification.objects.for_user(user).unread().count(),
        "recent_notifications": (
            Notification.objects.for_user(user).select_related("memo")[:6]
        ),
    }

    if user.can_send_directly():
        data["pending_count"] = Memorandum.objects.visible_to(user).pending_approval().count()
        data["draft_count"] = (
            Memorandum.objects.filter(created_by=user, status="draft").count()
        )
    else:
        data["unread_count"] = (
            user.received_memos.filter(read_at__isnull=True).count()
        )
        data["my_pending_count"] = (
            Memorandum.objects.filter(created_by=user, status="pending").count()
        )
        data["my_rejected_count"] = (
            Memorandum.objects.filter(created_by=user, status="rejected").count()
        )

    return data
