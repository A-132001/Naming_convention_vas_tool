from __future__ import annotations

from django import forms

from naming.models import DataCenter


class DataCenterForm(forms.ModelForm):
    class Meta:
        model = DataCenter
        fields = [
            "start_name",
            "end_name",
            "count_of_servers",
            "start_numbers",
            "end_numbers",
            "is_active",
        ]
        widgets = {
            "start_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "end_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "count_of_servers": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "min": 1,
                }
            ),
            "start_numbers": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "min": 1,
                }
            ),
            "end_numbers": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "min": 1,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Consistent checkbox styling.
        if "is_active" in self.fields:
            self.fields["is_active"].widget.attrs.update({"class": "h-4 w-4 rounded border-violet-300"})

