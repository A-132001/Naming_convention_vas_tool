from django.contrib.auth.views import LoginView
from django.shortcuts import render,redirect

from .forms import (
    CustomAuthenticationForm,
    StaffUserCreateForm,
    StaffUserEditForm,
    StaffUserSetPasswordForm,
)

from naming.models import (
    NamingRequest,
    ServerAllocation,
    HypervisorOS,
)

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import HttpRequest, HttpResponse


def home_view(request):
    context = {}

    if request.user.is_authenticated:
        approved_status = NamingRequest.Status.APPROVED

        approved_servers = (
            ServerAllocation.objects.filter(naming_request__status=approved_status)
            .select_related("hypervisor_os", "data_center", "naming_request")
            .prefetch_related(
                "network_configurations",
                "storage_configurations",
                "hypervisor_os__virtual_machines",
            )
            .order_by("server_number")
        )

        physical_headers = [
            "Server Name",
            "Management IP",
            "Ports",
            "Firewall",
            "Server Type",
            "HW Vendor",
            "HW Model",
            "Serial Number",
            "Firmware / BIOS Version",
            "Management System Name",
            "Domain",
            "Function",
            "Service",
            "Activation Status",
            "Activation Date",
            "Exchange Name",
            "Hall Name",
            "Rack No",
            "Rack Side",
            "Server Position",
            "CPU count - Sockets",
            "Cores per CPU",
            "RAM Size (GB)",
            "Storage Size (GB)",
            "PO Number",
            "Support End Date",
        ]

        hypervisor_headers = [
            "Server Name",
            "HV/OS Name",
            "Hypervisor Type / OS Type",
            "Management IP",
            "Ports",
            "Version / Build Number",
            "License Key / Status",
            "Expiration date",
        ]

        vm_headers = [
            "Hypervisor Name",
            "VM Name",
            "Management IP",
            "Sub Function/Other",
            "Software Vendor",
            "OS",
            "Activation Status",
            "License / Subscription Status",
            "License Expiration date",
            "Application Name",
            "vCPU-worker",
            "vRAM Size (GB)",
            "Storage size (GB)",
        ]

        network_headers = [
            "Server Name",
            "Server Port Name",
            "Connection Type",
            "Network Role",
            "Uplink Hostname",
            "Uplink Interface",
            "Description",
            "LACP Group / Port-Channel ID",
        ]

        storage_headers = [
            "Server Name",
            "Disk Type",
            "Disk Slot No",
            "Disk Size (GB)",
            "RAID Level / Configuration",
            "Usage Purpose",
        ]

        # Each row is a list of values in the exact Excel header order.
        physical_rows = []
        hypervisor_rows = []
        vm_rows = []
        network_rows = []
        storage_rows = []

        for server in approved_servers:
            hv: HypervisorOS | None = getattr(server, "hypervisor_os", None)
            server_networks = list(server.network_configurations.all())
            server_storages = list(server.storage_configurations.all())

            physical_row = {h: "" for h in physical_headers}
            physical_row["Server Name"] = server.server_name
            physical_row["Management IP"] = server.management_ip or ""
            physical_row["Ports"] = str(hv.ports) if hv and hv.ports is not None else ""
            # Remaining Physical Hardware columns are not modeled in MVP yet.
            physical_rows.append([physical_row[h] for h in physical_headers])

            if hv:
                hypervisor_row = {h: "" for h in hypervisor_headers}
                hypervisor_row["Server Name"] = server.server_name
                hypervisor_row["HV/OS Name"] = hv.hv_os_name
                hypervisor_row["Hypervisor Type / OS Type"] = hv.hypervisor_type_os_type
                hypervisor_row["Management IP"] = hv.management_ip or ""
                hypervisor_row["Ports"] = str(hv.ports) if hv.ports is not None else ""
                hypervisor_row["Version / Build Number"] = hv.version_build_number
                hypervisor_row["License Key / Status"] = hv.license_key_status or ""
                hypervisor_row["Expiration date"] = hv.expiration_date or ""
                hypervisor_rows.append([hypervisor_row[h] for h in hypervisor_headers])

                for vm in hv.virtual_machines.all():
                    vm_row = {h: "" for h in vm_headers}
                    vm_row["Hypervisor Name"] = hv.hv_os_name
                    vm_row["VM Name"] = vm.vm_name
                    vm_row["Management IP"] = vm.management_ip or ""
                    vm_row["Sub Function/Other"] = vm.sub_function_other or ""
                    vm_row["Software Vendor"] = vm.software_vendor or ""
                    vm_row["OS"] = vm.os or ""
                    vm_row["Activation Status"] = vm.activation_status or ""
                    vm_row["License / Subscription Status"] = vm.license_subscription_status or ""
                    vm_row["License Expiration date"] = vm.license_expiration_date or ""
                    vm_row["Application Name"] = vm.application_name or ""
                    vm_row["vCPU-worker"] = vm.vcpu_worker or ""
                    vm_row["vRAM Size (GB)"] = str(vm.vramsize_gb) if vm.vramsize_gb is not None else ""
                    vm_row["Storage size (GB)"] = (
                        str(vm.storage_size_gb) if vm.storage_size_gb is not None else ""
                    )
                    vm_rows.append([vm_row[h] for h in vm_headers])

            for net in server_networks:
                net_row = {h: "" for h in network_headers}
                net_row["Server Name"] = server.server_name
                net_row["Server Port Name"] = net.server_port_name
                net_row["Connection Type"] = net.connection_type
                net_row["Network Role"] = net.network_role
                net_row["Uplink Hostname"] = net.uplink_hostname or ""
                net_row["Uplink Interface"] = net.uplink_interface or ""
                net_row["Description"] = net.description or ""
                net_row["LACP Group / Port-Channel ID"] = net.lacp_group_port_channel_id or ""
                network_rows.append([net_row[h] for h in network_headers])

            for st in server_storages:
                st_row = {h: "" for h in storage_headers}
                st_row["Server Name"] = server.server_name
                st_row["Disk Type"] = st.disk_type or ""
                st_row["Disk Slot No"] = str(st.disk_slot_no) if st.disk_slot_no is not None else ""
                st_row["Disk Size (GB)"] = str(st.disk_size_gb) if st.disk_size_gb is not None else ""
                st_row["RAID Level / Configuration"] = st.raid_level_configuration or ""
                st_row["Usage Purpose"] = st.usage_purpose or ""
                storage_rows.append([st_row[h] for h in storage_headers])

        context.update(
            {
                "physical_headers": physical_headers,
                "physical_rows": physical_rows,
                "hypervisor_headers": hypervisor_headers,
                "hypervisor_rows": hypervisor_rows,
                "vm_headers": vm_headers,
                "vm_rows": vm_rows,
                "network_headers": network_headers,
                "network_rows": network_rows,
                "storage_headers": storage_headers,
                "storage_rows": storage_rows,
            }
        )

    return render(request, "home.html", context)


User = get_user_model()


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_staff)

    def handle_no_permission(self):
        raise PermissionDenied("Admin access is required.")


class AdminUserListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = User
    template_name = "accounts/admin/users_list.html"
    context_object_name = "users"
    ordering = ["id"]


class AdminUserCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = User
    form_class = StaffUserCreateForm
    template_name = "accounts/admin/user_form.html"
    success_url = reverse_lazy("admin_users_list")
    context_object_name = "managed_user"

    def form_valid(self, form):
        messages.success(self.request, "User created successfully.")
        return super().form_valid(form)


class AdminUserUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = User
    form_class = StaffUserEditForm
    template_name = "accounts/admin/user_form.html"
    success_url = reverse_lazy("admin_users_list")
    context_object_name = "managed_user"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = True
        return ctx

    def form_valid(self, form):
        target: User = form.instance
        changed_fields = set(form.changed_data or [])

        # Save first (super handles form.save()).
        response = super().form_valid(form)

        # If the admin edited themselves, re-auth is safer after identity/permission changes.
        if target.pk == self.request.user.pk:
            if changed_fields.intersection({"username", "email", "is_staff", "is_active"}):
                messages.warning(
                    self.request,
                    "You updated your own account identity/permissions. Please log in again.",
                )
                logout(self.request)
                return redirect("login")

        messages.success(self.request, "User updated successfully.")
        return response


class AdminUserDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/admin/user_confirm_delete.html"
    success_url = reverse_lazy("admin_users_list")
    context_object_name = "managed_user"

    def delete(self, request, *args, **kwargs):
        target: User = self.get_object()

        # Prevent deleting yourself.
        if target.pk == request.user.pk:
            raise PermissionDenied("You cannot delete yourself.")

        # Prevent deleting the last admin.
        remaining_staff = User.objects.filter(is_staff=True).exclude(pk=target.pk).count()
        if remaining_staff == 0:
            raise PermissionDenied("You cannot delete the last admin user.")

        messages.info(request, "User deleted successfully.")
        return super().delete(request, *args, **kwargs)


class AdminUserPasswordChangeView(LoginRequiredMixin, StaffRequiredMixin, View):
    """
    Staff-only password reset for a selected user.
    """

    template_name = "accounts/admin/user_change_password.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        target = get_object_or_404(User, pk=pk)
        form = StaffUserSetPasswordForm(user=target)
        return render(request, self.template_name, {"managed_user": target, "form": form, "is_edit": True})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        target = get_object_or_404(User, pk=pk)
        form = StaffUserSetPasswordForm(user=target, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password updated successfully.")
            return redirect("admin_users_list")

        return render(request, self.template_name, {"managed_user": target, "form": form, "is_edit": True})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True
    next_page = "home"
