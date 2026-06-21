from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("", views.UserListView.as_view(), name="list"),
    path("create/", views.UserCreateView.as_view(), name="create"),
    path("<int:pk>/", views.UserDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.UserEditView.as_view(), name="edit"),
    path("<int:pk>/toggle-active/", views.UserToggleActiveView.as_view(), name="toggle_active"),
    path("<int:pk>/reset-password/", views.UserResetPasswordView.as_view(), name="reset_password"),
]
