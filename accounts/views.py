from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View

from .forms import LoginForm, ProfileForm, ChangePasswordForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard:index")

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)


class CustomLogoutView(View):
    def post(self, request):
        auth_logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("accounts:login")


class ProfileView(LoginRequiredMixin, View):
    template_name = "accounts/profile.html"

    def get(self, request):
        return render(request, self.template_name, {
            "profile_form": ProfileForm(instance=request.user),
            "password_form": ChangePasswordForm(user=request.user),
            "breadcrumbs": [{"label": "My Profile"}],
        })

    def post(self, request):
        profile_form = ProfileForm(instance=request.user)
        password_form = ChangePasswordForm(user=request.user)

        if "update_profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("accounts:profile")

        elif "change_password" in request.POST:
            password_form = ChangePasswordForm(request.POST, user=request.user)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Password changed successfully.")
                return redirect("accounts:profile")

        return render(request, self.template_name, {
            "profile_form": profile_form,
            "password_form": password_form,
            "breadcrumbs": [{"label": "My Profile"}],
        })
