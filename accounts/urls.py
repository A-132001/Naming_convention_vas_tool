from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import CustomLoginView, home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
]
