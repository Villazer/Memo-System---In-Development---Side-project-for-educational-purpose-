from django.db import models 
from .models import Notification


def notify_memo_sent(memo, recipients):
    Notification.objects.bulk_create([
        Notification(user=user, memo=memo, message=f"New memorandum: {memo.title}")
        for user in recipients
    ])


def notify_memo_updated(memo, recipients, message=None):
    message = message or f"Memorandum updated: {memo.title}"
    Notification.objects.bulk_create([
        Notification(user=user, memo=memo, message=message)
        for user in recipients
    ])


def notify_submitted_for_approval(memo):
    from accounts.models import User
    reviewers = User.objects.filter(
        role__in=("admin", "superadmin"),
        is_active=True,
    ).filter(
        models.Q(role="superadmin") |  # superadmins always notified
        models.Q(department=memo.created_by.department)  # admins only if same dept
    )
    Notification.objects.bulk_create([
        Notification(
            user=reviewer, memo=memo,
            message=f"Memo pending approval: \"{memo.title}\" by {memo.created_by}",
        )
        for reviewer in reviewers
    ])


def notify_memo_approved(memo):
    Notification.objects.create(
        user=memo.created_by, memo=memo,
        message=f"Your memorandum \"{memo.title}\" has been approved by {memo.approved_by}.",
    )


def notify_memo_rejected(memo):
    Notification.objects.create(
        user=memo.created_by, memo=memo,
        message=f"Your memorandum \"{memo.title}\" was rejected by {memo.rejected_by}. Please review the comments.",
    )


def notify_memo_resubmitted(memo):
    from accounts.models import User
    reviewers = User.objects.filter(
        role__in=("admin", "superadmin"),
        is_active=True,
    ).filter(
        models.Q(role="superadmin") |
        models.Q(department=memo.created_by.department)
    )
    Notification.objects.bulk_create([
        Notification(
            user=reviewer, memo=memo,
            message=f"Resubmitted memo: \"{memo.title}\" by {memo.created_by} — ready for re-review.",
        )
        for reviewer in reviewers
    ])
