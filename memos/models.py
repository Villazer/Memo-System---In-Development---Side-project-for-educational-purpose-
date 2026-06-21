import os
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def memo_attachment_path(instance, filename):
    return f"memo_attachments/{instance.created_by_id}/{filename}"


class MemoQuerySet(models.QuerySet):

    def visible_to(self, user):
        from django.db.models import Q
        if user.is_superadmin:
            return self
        if user.is_admin:
                return self.filter(
                    Q(created_by=user) |                        # own memos
                    Q(departments__members=user) |              # memos targeting admin's dept
                    Q(created_by__department=user.department)  # memos made by dept members
                ).distinct()
        return self.filter(
            Q(created_by=user) | Q(recipients__recipient=user)
        ).distinct()

    def pending_approval(self):
        return self.filter(status=Memorandum.Status.PENDING)

    def drafts(self):
        return self.filter(status=Memorandum.Status.DRAFT)

    def sent(self):
        return self.filter(status=Memorandum.Status.SENT)

    def archived(self):
        return self.filter(status=Memorandum.Status.ARCHIVED)

    def approved(self):
        return self.filter(status=Memorandum.Status.APPROVED)

    def rejected(self):
        return self.filter(status=Memorandum.Status.REJECTED)


class MemoManager(models.Manager.from_queryset(MemoQuerySet)):
    pass


class Memorandum(models.Model):

    class Status(models.TextChoices):
        DRAFT    = "draft",    "Draft"
        PENDING  = "pending",  "Pending Approval"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"
        SENT     = "sent",     "Sent"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        NORMAL    = "normal",    "Normal"
        IMPORTANT = "important", "Important"
        URGENT    = "urgent",    "Urgent"

    title      = models.CharField(max_length=255)
    body       = models.TextField()
    status     = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority   = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    attachment = models.FileField(upload_to=memo_attachment_path, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_memos",
    )
    departments = models.ManyToManyField(
        "departments.Department", blank=True, related_name="memorandums",
    )

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    sent_at      = models.DateTimeField(null=True, blank=True)
    archived_at  = models.DateTimeField(null=True, blank=True)

    approved_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_memos",
    )
    approved_at        = models.DateTimeField(null=True, blank=True)
    rejected_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="rejected_memos",
    )
    rejected_at        = models.DateTimeField(null=True, blank=True)
    rejection_comments = models.TextField(blank=True)

    objects = MemoManager()

    class Meta:
        ordering = ["-created_at"]
        indexes  = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return self.title

    MAX_ATTACHMENT_SIZE = 100 * 1024 * 1024

    def submit_for_approval(self):
        self.status = self.Status.PENDING
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at"])

    def approve(self, approver):
        self.status = self.Status.APPROVED
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.rejection_comments = ""
        self.rejected_by = None
        self.rejected_at = None
        self.save(update_fields=[
            "status", "approved_by", "approved_at",
            "rejection_comments", "rejected_by", "rejected_at",
        ])
        ApprovalHistory.objects.create(
            memo=self, actor=approver, action=ApprovalHistory.Action.APPROVED,
        )

    def reject(self, rejector, comments):
        self.status = self.Status.REJECTED
        self.rejected_by = rejector
        self.rejected_at = timezone.now()
        self.rejection_comments = comments
        self.save(update_fields=[
            "status", "rejected_by", "rejected_at", "rejection_comments",
        ])
        ApprovalHistory.objects.create(
            memo=self, actor=rejector,
            action=ApprovalHistory.Action.REJECTED, comments=comments,
        )

    def mark_sent(self, individual_recipients=None):
        from notifications.services import notify_memo_sent
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])
        recipients = self._resolve_recipients(individual_recipients)
        if recipients:
            MemoRecipient.objects.bulk_create(
                [MemoRecipient(memo=self, recipient=u) for u in recipients],
                ignore_conflicts=True,
            )
            notify_memo_sent(self, recipients)

    def _resolve_recipients(self, individual_recipients=None):
        recipient_set = set()
        for dept in self.departments.all():
            recipient_set.update(dept.members.filter(is_active=True))
        if individual_recipients:
            recipient_set.update(individual_recipients)
        recipient_set.discard(self.created_by)
        return list(recipient_set)

    def archive(self):
        self.status = self.Status.ARCHIVED
        self.archived_at = timezone.now()
        self.save(update_fields=["status", "archived_at"])

    def get_archive_url(self):
        return reverse("memos:archive", args=[self.pk])

    def can_be_edited_by(self, user):
        if user.is_superadmin:
            return True
        if self.created_by_id != user.id:
            return False
        return self.status in (self.Status.DRAFT, self.Status.REJECTED)

    def can_be_submitted_by(self, user):
        return (
            self.created_by_id == user.id
            and self.status in (self.Status.DRAFT, self.Status.REJECTED)
        )

    def can_be_sent_by(self, user):
        if user.is_superadmin:
            return self.status in (self.Status.APPROVED, self.Status.DRAFT)
        if user.is_admin:
            return self.status == self.Status.APPROVED
        return False

    def can_be_approved_by(self, user):
        return (
            user.role in ("superadmin", "admin")
            and self.status == self.Status.PENDING
        )

    @property
    def attachment_filename(self):
        return os.path.basename(self.attachment.name) if self.attachment else None

    @property
    def total_recipients(self):
        return self.recipients.count()

    @property
    def read_count(self):
        return self.recipients.filter(read_at__isnull=False).count()

    @property
    def read_rate(self):
        total = self.total_recipients
        return round((self.read_count / total) * 100) if total else 0

    @property
    def department_names(self):
        return ", ".join(self.departments.values_list("name", flat=True))

    @property
    def is_overdue_for_archive(self):
        if self.status == self.Status.ARCHIVED:
            return False
        return self.created_at < timezone.now() - timezone.timedelta(days=365)


class MemoRecipient(models.Model):
    memo      = models.ForeignKey(Memorandum, on_delete=models.CASCADE, related_name="recipients")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_memos"
    )
    read_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("memo", "recipient")
        indexes = [models.Index(fields=["recipient", "read_at"])]

    def __str__(self):
        return f"{self.memo.title} → {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class ApprovalHistory(models.Model):

    class Action(models.TextChoices):
        SUBMITTED   = "submitted",   "Submitted for Approval"
        APPROVED    = "approved",    "Approved"
        REJECTED    = "rejected",    "Rejected"
        RESUBMITTED = "resubmitted", "Resubmitted"

    memo       = models.ForeignKey(Memorandum, on_delete=models.CASCADE, related_name="approval_history")
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=20, choices=Action.choices)
    comments   = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.memo.title} — {self.action} by {self.actor}"
