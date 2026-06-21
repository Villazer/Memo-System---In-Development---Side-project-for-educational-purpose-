from django.urls import path
from . import views

app_name = "memos"

urlpatterns = [
    path("create/",           views.MemoCreateView.as_view(),         name="create"),
    path("<int:pk>/",         views.MemoDetailView.as_view(),          name="detail"),
    path("<int:pk>/edit/",    views.MemoEditView.as_view(),            name="edit"),
    path("<int:pk>/archive/", views.MemoArchiveView.as_view(),         name="archive"),
    path("<int:pk>/delete/",  views.MemoDeleteView.as_view(),          name="delete"),
    path("<int:pk>/approve/", views.MemoApproveView.as_view(),         name="approve"),
    path("<int:pk>/reject/",  views.MemoRejectView.as_view(),          name="reject"),
    path("<int:pk>/send/",    views.MemoSendView.as_view(),            name="send"),
    path("mine/",             views.MyMemoListView.as_view(),          name="my_memos"),
    path("pending/",          views.PendingApprovalListView.as_view(), name="pending"),
    path("sent/",             views.SentListView.as_view(),            name="sent"),
    path("archived/",         views.ArchivedListView.as_view(),        name="archived"),
    path("assigned/",         views.AssignedListView.as_view(),        name="assigned"),
]
