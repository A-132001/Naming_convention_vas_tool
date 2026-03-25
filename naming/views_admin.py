from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from naming.forms_admin import DataCenterForm
from naming.models import DataCenter


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_staff)

    def handle_no_permission(self):
        raise PermissionDenied("Admin access is required.")


class AdminDataCenterListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = DataCenter
    template_name = "naming/admin/datacenters_list.html"
    context_object_name = "datacenters"
    ordering = ["start_name"]


class AdminDataCenterCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = DataCenter
    form_class = DataCenterForm
    template_name = "naming/admin/datacenter_form.html"
    success_url = reverse_lazy("admin_datacenters_list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = False
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Data Center created successfully.")
        return super().form_valid(form)


class AdminDataCenterUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = DataCenter
    form_class = DataCenterForm
    template_name = "naming/admin/datacenter_form.html"
    success_url = reverse_lazy("admin_datacenters_list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Data Center updated successfully.")
        return super().form_valid(form)


class AdminDataCenterDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = DataCenter
    template_name = "naming/admin/datacenter_confirm_delete.html"
    success_url = reverse_lazy("admin_datacenters_list")

    def delete(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            return super().delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "Cannot delete this Data Center because it is referenced by naming requests/servers.",
            )
            return redirect(self.success_url)

