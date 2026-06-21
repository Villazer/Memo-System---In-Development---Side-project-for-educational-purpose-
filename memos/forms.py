from django import forms
from django.core.exceptions import ValidationError

from .models import Memorandum
from accounts.models import User
from departments.models import Department


class MemoForm(forms.ModelForm):
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Target Departments",
    )
    individual_recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "last_name"),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Individual Recipients",
    )

    class Meta:
        model = Memorandum
        fields = ["title", "body", "priority", "attachment"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter memorandum title",
            }),
            "body": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Write the memorandum content...",
                "rows": 10,
            }),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "attachment": forms.FileInput(attrs={"class": "hidden", "accept": ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif,.webp,.bmp"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["departments"].initial = (
                self.instance.departments.values_list("pk", flat=True)
            )
        if self.user and self.user.is_admin:
            self.fields["individual_recipients"].queryset = (
                User.objects.filter(
                    is_active=True, department=self.user.department
                ).order_by("first_name", "last_name")
            )

    ALLOWED_ATTACHMENT_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
    }

    ALLOWED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
    }

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment and hasattr(attachment, "size"):
            if attachment.size > Memorandum.MAX_ATTACHMENT_SIZE:
                raise ValidationError("Attachment must not exceed 100MB.")
            import os
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f"Invalid file type '{ext}'. Allowed: "
                    "PDF, Word, Excel, PowerPoint, images (JPG, PNG, GIF, WebP), TXT."
                )
        return attachment

    def clean(self):
        cleaned = super().clean()
        action = self.data.get("action")
        if action == "send":
            if not cleaned.get("departments") and not cleaned.get("individual_recipients"):
                raise ValidationError(
                    "Select at least one department or individual recipient before sending."
                )
        return cleaned

    def save_recipients(self, memo):
        depts = self.cleaned_data.get("departments") or []
        memo.departments.set(depts)

    def get_individual_recipients(self):
        return list(self.cleaned_data.get("individual_recipients") or [])


class RejectionForm(forms.Form):
    rejection_comments = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 5,
            "placeholder": (
                "Explain the reason for rejection and what corrections are needed. "
                "This feedback is visible to the memo creator."
            ),
        }),
        label="Rejection Comments",
        min_length=10,
        error_messages={
            "required": "You must provide rejection comments.",
            "min_length": "Please provide at least 10 characters of feedback.",
        },
    )
