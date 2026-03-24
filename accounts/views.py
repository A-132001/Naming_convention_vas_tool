from django.contrib.auth.views import LoginView
from django.shortcuts import render

from .forms import CustomAuthenticationForm


def home_view(request):
    return render(request, "home.html")


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True
    next_page = "home"
