from django import forms
from .models import SystemSetting


class SystemSettingForm(forms.Form):
    org_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Acme University"}), label="Organization Name", help_text="Displayed in the sidebar and login page.")
    org_tagline = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Office of the President"}), label="Organization Tagline", help_text="Optional subtitle shown below the org name.")
    archive_threshold_days = forms.IntegerField(min_value=30, max_value=3650, widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "365"}), label="Auto-Archive After (days)", help_text="Memorandums older than this many days are automatically archived. Default: 365.")
    allow_staff_to_view_sender = forms.BooleanField(required=False, label="Show Sender Name to Staff", help_text="If enabled, staff can see who created the memo.")
    memos_per_page = forms.IntegerField(min_value=5, max_value=100, widget=forms.NumberInput(attrs={"class": "form-control"}), label="Memos Per Page", help_text="Number of memos to display per page in list views.")

    def load_from_db(self):
        self.fields["org_name"].initial = SystemSetting.get("org_name", "M.I.N.D.S")
        self.fields["org_tagline"].initial = SystemSetting.get("org_tagline", "Memo Distribution")
        self.fields["archive_threshold_days"].initial = int(SystemSetting.get("archive_threshold_days", "365"))
        self.fields["allow_staff_to_view_sender"].initial = SystemSetting.get("allow_staff_to_view_sender", "true") == "true"
        self.fields["memos_per_page"].initial = int(SystemSetting.get("memos_per_page", "10"))

    def save_to_db(self):
        cd = self.cleaned_data
        SystemSetting.set("org_name", cd["org_name"], "Organization display name")
        SystemSetting.set("org_tagline", cd.get("org_tagline", ""), "Sidebar tagline")
        SystemSetting.set("archive_threshold_days", str(cd["archive_threshold_days"]), "Days before auto-archive")
        SystemSetting.set("allow_staff_to_view_sender", "true" if cd.get("allow_staff_to_view_sender") else "false", "Show sender name to staff")
        SystemSetting.set("memos_per_page", str(cd["memos_per_page"]), "Memos per page in list views")
