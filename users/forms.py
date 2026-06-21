from django import forms
from accounts.models import User
from departments.models import Department


class UserFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by name, username, or email..."}))
    role = forms.ChoiceField(required=False, choices=[("", "All Roles")] + list(User.Role.choices), widget=forms.Select(attrs={"class": "form-control"}))
    department = forms.ModelChoiceField(required=False, queryset=Department.objects.all().order_by("name"), empty_label="All Departments", widget=forms.Select(attrs={"class": "form-control"}))
    status = forms.ChoiceField(required=False, choices=[("", "All Statuses"), ("active", "Active"), ("inactive", "Inactive")], widget=forms.Select(attrs={"class": "form-control"}))
