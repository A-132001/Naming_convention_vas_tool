from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    AdminUserCreateView,
    AdminUserDeleteView,
    AdminUserListView,
    AdminUserUpdateView,
    AdminUserPasswordChangeView,
    CustomLoginView,
    home_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    path("manage/users/", AdminUserListView.as_view(), name="admin_users_list"),
    path("manage/users/new/", AdminUserCreateView.as_view(), name="admin_users_create"),
    path("manage/users/<int:pk>/edit/", AdminUserUpdateView.as_view(), name="admin_users_edit"),
    path("manage/users/<int:pk>/delete/", AdminUserDeleteView.as_view(), name="admin_users_delete"),
    path("manage/users/<int:pk>/change-password/", AdminUserPasswordChangeView.as_view(), name="admin_users_change_password"),
]
