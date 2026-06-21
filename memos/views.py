from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.permissions import AdminOrSuperadminRequiredMixin
from notifications.services import (
    notify_submitted_for_approval,
    notify_memo_approved,
    notify_memo_rejected,
    notify_memo_resubmitted,
)
from .forms import MemoForm, RejectionForm
from .models import Memorandum, MemoRecipient, ApprovalHistory


class MemoCreateView(LoginRequiredMixin, View):
    template_name = "memos/memo_form.html"

    def get(self, request):
        return render(request, self.template_name, self._ctx(MemoForm(user=request.user)))

    def post(self, request):
        form = MemoForm(request.POST, request.FILES, user=request.user)
        action = request.POST.get("action", "draft")
        if not form.is_valid():
            return render(request, self.template_name, self._ctx(form))
        memo = form.save(commit=False)
        memo.created_by = request.user
        memo.save()
        form.save_recipients(memo)
        return self._handle_action(request, memo, form, action)

    def _ctx(self, form, memo=None):
        return {
            "form": form,
            "memo": memo,
            "title": "Create Memorandum",
            "subtitle": "Fill in the details to draft or submit a memorandum.",
            "breadcrumbs": [
                {"label": "My Memos", "url": reverse("memos:my_memos")},
                {"label": "Create"},
            ],
        }

    @staticmethod
    def _handle_action(request, memo, form, action):
        user = request.user

        if action == "submit":
            was_rejected = memo.status == Memorandum.Status.REJECTED
            memo.submit_for_approval()
            ApprovalHistory.objects.create(
                memo=memo, actor=user,
                action=(
                    ApprovalHistory.Action.RESUBMITTED
                    if was_rejected else ApprovalHistory.Action.SUBMITTED
                ),
            )
            if was_rejected:
                notify_memo_resubmitted(memo)
            else:
                notify_submitted_for_approval(memo)
            messages.success(request, "Memorandum submitted for approval.")
            return redirect("memos:my_memos")

        if action == "send" and user.can_send_directly():
            recipients = form.get_individual_recipients() if form else []
            memo.mark_sent(individual_recipients=recipients)
            messages.success(
                request,
                f"Memorandum sent to {memo.total_recipients} recipient(s).",
            )
            return redirect("memos:sent")

        messages.success(request, "Memorandum saved as draft.")
        return redirect("memos:my_memos")


class MemoEditView(LoginRequiredMixin, View):
    template_name = "memos/memo_form.html"

    def _get_memo(self, user, pk):
        memo = get_object_or_404(Memorandum, pk=pk)
        if not memo.can_be_edited_by(user):
            return None
        return memo

    def get(self, request, pk):
        memo = self._get_memo(request.user, pk)
        if not memo:
            messages.error(request, "You cannot edit this memorandum.")
            return redirect("memos:my_memos")
        form = MemoForm(instance=memo, user=request.user)
        existing_ids = list(memo.recipients.values_list("recipient_id", flat=True))
        form.fields["individual_recipients"].initial = existing_ids
        return render(request, self.template_name, self._ctx(form, memo))

    def post(self, request, pk):
        memo = self._get_memo(request.user, pk)
        if not memo:
            messages.error(request, "You cannot edit this memorandum.")
            return redirect("memos:my_memos")
        form = MemoForm(request.POST, request.FILES, instance=memo, user=request.user)
        action = request.POST.get("action", "draft")
        if not form.is_valid():
            return render(request, self.template_name, self._ctx(form, memo))
        memo = form.save()
        form.save_recipients(memo)
        return MemoCreateView._handle_action(request, memo, form, action)

    def _ctx(self, form, memo):
        return {
            "form": form,
            "memo": memo,
            "title": "Edit Memorandum",
            "subtitle": "Update the details then save, submit, or send.",
            "breadcrumbs": [
                {"label": "My Memos", "url": reverse("memos:my_memos")},
                {"label": memo.title, "url": reverse("memos:detail", args=[memo.pk])},
                {"label": "Edit"},
            ],
        }


class BaseMemoListView(LoginRequiredMixin, ListView):
    model = Memorandum
    template_name = "memos/memo_list.html"
    context_object_name = "memos"
    paginate_by = 10

    def get_queryset(self):
        qs = self.base_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(title__icontains=q)
        priority = self.request.GET.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        return qs.select_related("created_by")

    def base_queryset(self):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.list_context())
        return ctx

    def list_context(self):
        return {}


class MyMemoListView(BaseMemoListView):
    def base_queryset(self):
        qs = Memorandum.objects.filter(created_by=self.request.user)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def list_context(self):
        user = self.request.user
        qs = Memorandum.objects.filter(created_by=user)
        return {
            "page_title": "My Memorandums",
            "page_subtitle": "All memorandums you have created.",
            "list_type": "my_memos",
            "breadcrumbs": [{"label": "My Memos"}],
            "empty_icon": "file-pen",
            "empty_title": "No memorandums yet",
            "empty_message": "Create your first memorandum to get started.",
            "memo_create_url": reverse("memos:create"),
            "status_counts": {
                "draft":    qs.filter(status="draft").count(),
                "pending":  qs.filter(status="pending").count(),
                "rejected": qs.filter(status="rejected").count(),
                "approved": qs.filter(status="approved").count(),
                "sent":     qs.filter(status="sent").count(),
            },
        }


class PendingApprovalListView(AdminOrSuperadminRequiredMixin, BaseMemoListView):
    def base_queryset(self): # now scoped by department
        return (
            Memorandum.objects
            .visible_to(self.request.user)
            .pending_approval()
            .select_related("created_by", "created_by__department")
            .prefetch_related("departments")
        )

    def list_context(self):
        return {
            "page_title": "Pending Approval",
            "page_subtitle": "Memorandums awaiting your review.",
            "list_type": "pending",
            "breadcrumbs": [{"label": "Pending Approval"}],
            "empty_icon": "clock",
            "empty_title": "Nothing to review",
            "empty_message": "All caught up — no memorandums are pending approval.",
        }


class SentListView(AdminOrSuperadminRequiredMixin, BaseMemoListView):
    def base_queryset(self):
        return Memorandum.objects.visible_to(self.request.user).sent()

    def list_context(self):
        return {
            "page_title": "Sent Memorandums",
            "page_subtitle": "Memorandums that have been distributed.",
            "list_type": "sent",
            "breadcrumbs": [{"label": "Sent"}],
            "empty_icon": "paper-plane",
            "empty_title": "No sent memorandums",
            "empty_message": "Sent memorandums will appear here.",
            "memo_create_url": reverse("memos:create"),
        }


class AssignedListView(BaseMemoListView):
    def base_queryset(self):
        return (
            Memorandum.objects
            .filter(recipients__recipient=self.request.user, status=Memorandum.Status.SENT)
            .distinct()
            .order_by("-sent_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        read_ids = set(
            MemoRecipient.objects
            .filter(recipient=user, read_at__isnull=False)
            .values_list("memo_id", flat=True)
        )
        for memo in ctx["memos"]:
            memo.is_unread_for_user = memo.id not in read_ids
        ctx.update({
            "page_title": "Assigned to Me",
            "page_subtitle": "Memorandums distributed to you.",
            "list_type": "assigned",
            "breadcrumbs": [{"label": "Assigned to Me"}],
            "empty_icon": "inbox",
            "empty_title": "Nothing assigned",
            "empty_message": "Memorandums sent to you will appear here.",
        })
        return ctx


class ArchivedListView(BaseMemoListView):
    def base_queryset(self):
        return Memorandum.objects.visible_to(self.request.user).archived()

    def list_context(self):
        return {
            "page_title": "Archived Memorandums",
            "page_subtitle": "Memorandums moved to the archive.",
            "list_type": "archived",
            "breadcrumbs": [{"label": "Archived"}],
            "empty_icon": "box-archive",
            "empty_title": "No archived memorandums",
            "empty_message": "Archived memorandums will appear here.",
        }


class MemoDetailView(LoginRequiredMixin, DetailView):
    model = Memorandum
    template_name = "memos/memo_detail.html"
    context_object_name = "memo"

    def get_queryset(self):
        return Memorandum.objects.visible_to(self.request.user).select_related(
            "created_by", "approved_by", "rejected_by"
        ).prefetch_related("departments")

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        memo = self.object
        if memo.status == Memorandum.Status.SENT:
            rec, _ = MemoRecipient.objects.get_or_create(memo=memo, recipient=request.user)
            rec.mark_read()
            request.user.notifications.filter(memo=memo, is_read=False).update(is_read=True)
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        memo = self.object
        user = self.request.user
        ctx.update({
            "breadcrumbs": [
                {"label": "Memorandums", "url": self._back_url()},
                {"label": memo.title},
            ],
            "can_edit":    memo.can_be_edited_by(user),
            "can_submit":  memo.can_be_submitted_by(user),
            "can_send":    memo.can_be_sent_by(user),
            "can_approve": memo.can_be_approved_by(user),
            "can_delete":  (
                memo.status in (Memorandum.Status.DRAFT, Memorandum.Status.REJECTED)
                and (user.is_superadmin or memo.created_by_id == user.id)
            ),
            "can_archive": (
                user.is_superadmin or memo.created_by_id == user.id
            ) and memo.status != Memorandum.Status.ARCHIVED,
            "approval_history": memo.approval_history.select_related("actor")[:10],
            "rejection_form": RejectionForm(),
            "recipients_list": (
                memo.recipients.select_related("recipient").order_by("-read_at")
                if user.can_send_directly() else []
            ),
            "send_form_users": (
                user.department.members.filter(is_active=True).order_by("first_name")
                if user.department else []
            ),
        })
        return ctx

    def _back_url(self):
        memo = self.object
        user = self.request.user
        if not user.can_send_directly():
            return reverse("memos:assigned")
        if memo.status == Memorandum.Status.PENDING:
            return reverse("memos:pending")
        if memo.status == Memorandum.Status.ARCHIVED:
            return reverse("memos:archived")
        if memo.status == Memorandum.Status.SENT:
            return reverse("memos:sent")
        return reverse("memos:my_memos")


class MemoApproveView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, View):
    def post(self, request, pk):
        memo = get_object_or_404(Memorandum, pk=pk)
        if not memo.can_be_approved_by(request.user):
            messages.error(request, "This memorandum cannot be approved.")
            return redirect("memos:detail", pk=pk)
        memo.approve(request.user)
        notify_memo_approved(memo)
        messages.success(request, "Memorandum approved. The creator has been notified.")
        return redirect("memos:detail", pk=pk)


class MemoRejectView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, View):
    def post(self, request, pk):
        memo = get_object_or_404(Memorandum, pk=pk)
        if not memo.can_be_approved_by(request.user):
            messages.error(request, "This memorandum cannot be rejected.")
            return redirect("memos:detail", pk=pk)
        form = RejectionForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please provide rejection comments before rejecting.")
            return redirect("memos:detail", pk=pk)
        memo.reject(request.user, form.cleaned_data["rejection_comments"])
        notify_memo_rejected(memo)
        messages.success(request, "Memorandum rejected. The creator has been notified.")
        return redirect("memos:pending")


class MemoSendView(LoginRequiredMixin, AdminOrSuperadminRequiredMixin, View):
    def post(self, request, pk):
        memo = get_object_or_404(Memorandum, pk=pk)
        if not memo.can_be_sent_by(request.user):
            messages.error(request, "This memorandum cannot be sent.")
            return redirect("memos:detail", pk=pk)
        from accounts.models import User as UserModel
        recipient_ids = request.POST.getlist("individual_recipients")
        individual_recipients = list(
            UserModel.objects.filter(pk__in=recipient_ids, is_active=True)
        ) if recipient_ids else []
        memo.mark_sent(individual_recipients=individual_recipients)
        messages.success(request, f"Memorandum sent to {memo.total_recipients} recipient(s).")
        return redirect("memos:sent")


class MemoArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        memo = get_object_or_404(Memorandum.objects.visible_to(request.user), pk=pk)
        if not (request.user.is_superadmin or memo.created_by_id == request.user.id):
            messages.error(request, "You cannot archive this memorandum.")
            return redirect("memos:detail", pk=pk)
        memo.archive()
        messages.success(request, "Memorandum archived.")
        return redirect("memos:archived")


class MemoDeleteView(LoginRequiredMixin, View):
    """Permanently delete a draft memo. Only the creator or superadmin can do this."""

    def post(self, request, pk):
        memo = get_object_or_404(Memorandum, pk=pk)

        # Permission check
        if not (request.user.is_superadmin or memo.created_by_id == request.user.id):
            messages.error(request, "You cannot delete this memorandum.")
            return redirect("memos:detail", pk=pk)

        # Only drafts (and rejected) can be deleted — sent/approved memos must be archived
        if memo.status not in (Memorandum.Status.DRAFT, Memorandum.Status.REJECTED):
            messages.error(
                request,
                "Only draft or rejected memorandums can be permanently deleted. "
                "Use Archive for sent memos."
            )
            return redirect("memos:detail", pk=pk)

        title = memo.title
        memo.delete()
        messages.success(request, f"Memorandum \"{title}\" permanently deleted.")
        return redirect("memos:my_memos")
