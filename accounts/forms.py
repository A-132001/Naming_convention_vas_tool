from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import get_user_model


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


User = get_user_model()


class StaffUserCreateForm(UserCreationForm):
    """
    Staff-only create form for managing users.
    """

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tailwind focus/hover styling for consistent UI.
        for name, field in self.fields.items():
            if name in {"password1", "password2"}:
                field.widget.attrs.update(
                    {
                        "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                        "autocomplete": "new-password",
                    }
                )
            elif name in {"username", "email", "first_name", "last_name"}:
                field.widget.attrs.update(
                    {
                        "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    }
                )
            elif name in {"is_staff", "is_active"}:
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-violet-300"})


class StaffUserEditForm(forms.ModelForm):
    """
    Staff-only edit form for managing users (no password change in MVP).
    """

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"username", "email", "first_name", "last_name"}:
                field.widget.attrs.update(
                    {
                        "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    }
                )
            elif name in {"is_staff", "is_active"}:
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-violet-300"})


class StaffUserSetPasswordForm(SetPasswordForm):
    """
    Staff-only "set password" form (no old password required).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ["new_password1", "new_password2"]:
            field = self.fields.get(field_name)
            if not field:
                continue
            field.widget.attrs.update(
                {
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "autocomplete": "new-password",
                }
            )
