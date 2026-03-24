from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Username",
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-300 bg-white/80 px-4 py-3 text-sm text-slate-800 shadow-sm transition duration-200 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                "placeholder": "Enter your email or username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-300 bg-white/80 px-4 py-3 text-sm text-slate-800 shadow-sm transition duration-200 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )
