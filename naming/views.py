from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from naming.forms import (
    HypervisorOSForm,
    NamingRequestStatusConfirmForm,
    ServerManagementIpFormSet,
    Step1GenerateForm,
    build_network_configuration_formset,
    build_virtual_machine_formset,
)
from naming.models import (
    DataCenter,
    HypervisorOS,
    NetworkConfiguration,
    NamingRequest,
    VirtualMachine,
)
from naming.services.approval import approve_naming_request, reject_naming_request
from naming.services.reservation import preview_server_block, reserve_server_block
from naming.services.steps import (
    assert_final_submission_allowed,
    assert_step_accessible,
    assert_step_submission_allowed,
)
from naming.services.workflow import (
    complete_step1_management_ips,
    complete_step2_hypervisors,
    final_submit_to_admin,
    replace_step3_vms,
    replace_step4_network,
)


STEP1_PREVIEW_SESSION_KEY = "naming_step1_preview"


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        return bool(self.request.user and self.request.user.is_staff)

    def handle_no_permission(self):
        raise PermissionDenied("Admin access is required.")


class NamingRequestStartView(LoginRequiredMixin, View):
    """
    Step 1 start + submission (also creates NamingRequest).

    UX:
    - POST action=generate => compute a preview contiguous block and store it in session.
    - POST action=submit_step1 => validate management IPs, reserve server numbers, create request.
    """

    template_name = "naming/requests/step1_start.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        preview = request.session.get(STEP1_PREVIEW_SESSION_KEY)
        form = Step1GenerateForm(initial={})

        if preview:
            form = Step1GenerateForm(
                initial={
                    "data_center": DataCenter.objects.get(id=preview["data_center_id"]),
                    "count": preview["count"],
                }
            )
            server_initial = []
            for n in preview["server_numbers"]:
                server_initial.append(
                    {
                        "server_number": n,
                        "server_name": preview["server_names"][str(n)],
                        "management_ip": "",
                    }
                )
            server_formset = ServerManagementIpFormSet(initial=server_initial, prefix="servers")
        else:
            server_formset = ServerManagementIpFormSet(initial=[], prefix="servers")

        return render(
            request,
            self.template_name,
            {"form": form, "server_formset": server_formset, "preview": preview},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action")
        preview = request.session.get(STEP1_PREVIEW_SESSION_KEY)

        if action == "generate":
            form = Step1GenerateForm(request.POST)
            if not form.is_valid():
                server_formset = ServerManagementIpFormSet(initial=[], prefix="servers")
                return render(
                    request,
                    self.template_name,
                    {"form": form, "server_formset": server_formset, "preview": None},
                )

            data_center: DataCenter = form.cleaned_data["data_center"]
            count: int = form.cleaned_data["count"]
            server_numbers = preview_server_block(data_center=data_center, count=count)

            server_names = {
                str(n): f"{data_center.start_name}-SR{n}C-{data_center.end_name}"
                for n in server_numbers
            }

            request.session[STEP1_PREVIEW_SESSION_KEY] = {
                "data_center_id": data_center.id,
                "count": count,
                "server_numbers": server_numbers,
                "server_names": server_names,
            }
            request.session.modified = True
            return redirect(reverse("naming_requests_start"))

        if action == "submit_step1":
            if not preview:
                raise ValidationError("Preview not found. Generate servers again.")

            data_center = get_object_or_404(DataCenter, id=preview["data_center_id"])
            count = int(preview["count"])
            server_numbers = preview["server_numbers"]

            server_formset = ServerManagementIpFormSet(request.POST, prefix="servers")
            if not server_formset.is_valid():
                return render(
                    request,
                    self.template_name,
                    {"form": Step1GenerateForm(initial={}), "server_formset": server_formset, "preview": preview},
                )

            management_ips = [form.cleaned_data["management_ip"] for form in server_formset]

            try:
                with transaction.atomic():
                    naming_request = NamingRequest.objects.create(
                        created_by=request.user,
                        data_center=data_center,
                        status=NamingRequest.Status.DRAFT,
                        requested_server_count=count,
                    )

                    reserve_server_block(
                        naming_request=naming_request,
                        data_center=data_center,
                        count=count,
                        management_ips=management_ips,
                        server_numbers=server_numbers,
                    )

                    naming_request.step1_completed = True
                    naming_request.save(update_fields=["step1_completed", "updated_at"])
            except ValidationError as e:
                request.session.pop(STEP1_PREVIEW_SESSION_KEY, None)
                request.session.modified = True
                messages.error(request, str(e))
                return redirect(reverse("naming_requests_start"))

            request.session.pop(STEP1_PREVIEW_SESSION_KEY, None)
            request.session.modified = True
            return redirect("naming_request_step2", pk=naming_request.pk)

        raise ValidationError("Invalid action.")


class NamingRequestStep1EditView(LoginRequiredMixin, View):
    """
    Optional edit view for Step 1 management IPs (normal user while DRAFT).
    """

    template_name = "naming/requests/step1_edit.html"

    def get_naming_request(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, created_by=request.user)
        assert_step_accessible(naming_request=naming_request, step=1)
        return naming_request

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_naming_request(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")

        initial = []
        for s in servers:
            initial.append(
                {
                    "server_number": s.server_number,
                    "server_name": s.server_name,
                    "management_ip": s.management_ip or "",
                }
            )

        server_formset = ServerManagementIpFormSet(initial=initial, prefix="servers")
        return render(request, self.template_name, {"naming_request": naming_request, "server_formset": server_formset})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_naming_request(request, pk)
        assert_step_submission_allowed(naming_request=naming_request, step=1)

        servers = list(naming_request.server_allocations.all().order_by("server_number"))
        server_formset = ServerManagementIpFormSet(request.POST, prefix="servers")
        if not server_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "server_formset": server_formset})

        management_ips = [form.cleaned_data["management_ip"] for form in server_formset.forms]
        complete_step1_management_ips(
            naming_request=naming_request,
            servers=servers,
            management_ips=management_ips,
        )

        return redirect("naming_request_step2", pk=naming_request.pk)


class NamingRequestStep2View(LoginRequiredMixin, View):
    template_name = "naming/requests/step2_hypervisor.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, created_by=request.user)
        assert_step_accessible(naming_request=naming_request, step=2)
        return naming_request

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")

        server_forms = []
        for server in servers:
            instance = getattr(server, "hypervisor_os", None)
            server_forms.append((server, HypervisorOSForm(instance=instance, prefix=f"hv-{server.pk}")))

        return render(request, self.template_name, {"naming_request": naming_request, "server_forms": server_forms})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        assert_step_submission_allowed(naming_request=naming_request, step=2)

        servers = naming_request.server_allocations.all().order_by("server_number")
        server_forms = []
        all_valid = True

        for server in servers:
            instance = getattr(server, "hypervisor_os", None)
            form = HypervisorOSForm(request.POST, instance=instance, prefix=f"hv-{server.pk}")
            server_forms.append((server, form))
            if not form.is_valid():
                all_valid = False

        if not all_valid:
            return render(request, self.template_name, {"naming_request": naming_request, "server_forms": server_forms})

        server_forms_data = [(server, form.cleaned_data) for server, form in server_forms]
        complete_step2_hypervisors(naming_request=naming_request, server_forms_data=server_forms_data)

        return redirect("naming_request_step3", pk=naming_request.pk)


class NamingRequestStep3View(LoginRequiredMixin, View):
    template_name = "naming/requests/step3_vms.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, created_by=request.user)
        assert_step_accessible(naming_request=naming_request, step=3)
        return naming_request

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all()
        hypervisors = HypervisorOS.objects.filter(server__in=servers).order_by("server__server_number")
        vm_formset = build_virtual_machine_formset(hypervisors=hypervisors, data=None, prefix="vm")
        return render(request, self.template_name, {"naming_request": naming_request, "vm_formset": vm_formset})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        assert_step_submission_allowed(naming_request=naming_request, step=3)

        servers = naming_request.server_allocations.all()
        hypervisors = HypervisorOS.objects.filter(server__in=servers).order_by("server__server_number")
        vm_formset = build_virtual_machine_formset(hypervisors=hypervisors, data=request.POST, prefix="vm")

        if not vm_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "vm_formset": vm_formset})

        vm_rows = []
        for form in vm_formset:
            cleaned = form.cleaned_data
            if not cleaned or not cleaned.get("vm_name"):
                continue
            if not cleaned.get("hypervisor"):
                vm_formset.non_form_errors = [
                    "Hypervisor is required for rows where VM Name is provided."
                ]  # type: ignore[attr-defined]
                return render(
                    request,
                    self.template_name,
                    {"naming_request": naming_request, "vm_formset": vm_formset},
                )

            vm_rows.append(dict(cleaned))

        saved_count = replace_step3_vms(
            naming_request=naming_request,
            hypervisors=hypervisors,
            vm_rows=vm_rows,
        )

        if saved_count == 0:
            vm_formset.non_form_errors = ["Please add at least one VM."]  # type: ignore[attr-defined]
            return render(
                request, self.template_name, {"naming_request": naming_request, "vm_formset": vm_formset}
            )

        return redirect("naming_request_step4", pk=naming_request.pk)


class NamingRequestStep4View(LoginRequiredMixin, View):
    template_name = "naming/requests/step4_network.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, created_by=request.user)
        assert_step_accessible(naming_request=naming_request, step=4)
        return naming_request

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")
        net_formset = build_network_configuration_formset(servers=servers, data=None, prefix="net")
        return render(request, self.template_name, {"naming_request": naming_request, "net_formset": net_formset})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        assert_step_submission_allowed(naming_request=naming_request, step=4)

        servers = naming_request.server_allocations.all().order_by("server_number")
        net_formset = build_network_configuration_formset(servers=servers, data=request.POST, prefix="net")

        if not net_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "net_formset": net_formset})

        net_rows = []
        for form in net_formset:
            cleaned = form.cleaned_data
            if not cleaned or not cleaned.get("server_port_name"):
                continue
            if not cleaned.get("server"):
                net_formset.non_form_errors = [
                    "Server is required for rows where Port Name is provided."
                ]  # type: ignore[attr-defined]
                return render(
                    request,
                    self.template_name,
                    {"naming_request": naming_request, "net_formset": net_formset},
                )

            net_rows.append(dict(cleaned))

        saved_count = replace_step4_network(
            naming_request=naming_request,
            servers=servers,
            net_rows=net_rows,
        )

        if saved_count == 0:
            net_formset.non_form_errors = ["Please add at least one network row."]  # type: ignore[attr-defined]
            return render(
                request,
                self.template_name,
                {"naming_request": naming_request, "net_formset": net_formset},
            )

        return redirect("naming_request_final_submit", pk=naming_request.pk)


class NamingRequestFinalSubmitView(LoginRequiredMixin, View):
    template_name = "naming/requests/final_submit.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, created_by=request.user)
        assert_step_accessible(naming_request=naming_request, step=4)
        return naming_request

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        confirm_form = NamingRequestStatusConfirmForm()
        return render(request, self.template_name, {"naming_request": naming_request, "confirm_form": confirm_form})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        confirm_form = NamingRequestStatusConfirmForm(request.POST)
        if not confirm_form.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "confirm_form": confirm_form})

        assert_final_submission_allowed(naming_request=naming_request)
        final_submit_to_admin(naming_request=naming_request)

        messages.success(request, "Request submitted to admin successfully.")
        return redirect("naming_requests_start")


class AdminNamingRequestListView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "naming/admin/request_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        pending = NamingRequest.objects.filter(status=NamingRequest.Status.PENDING).order_by("-created_at")
        return render(request, self.template_name, {"pending_requests": pending})


class AdminNamingRequestDetailView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "naming/admin/request_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)
        return render(request, self.template_name, {"naming_request": naming_request})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)
        action = request.POST.get("action")

        if action == "approve":
            approve_naming_request(admin_user=request.user, naming_request=naming_request)
            messages.success(request, "Request approved and finalized.")
            return redirect("admin_naming_request_list")
        if action == "reject":
            reject_naming_request(admin_user=request.user, naming_request=naming_request)
            messages.info(request, "Request rejected and reservations released.")
            return redirect("admin_naming_request_list")

        raise ValidationError("Invalid action.")


class AdminNamingRequestStep1View(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "naming/requests/step1_edit_admin.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        return get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")
        initial = [
            {"server_number": s.server_number, "server_name": s.server_name, "management_ip": s.management_ip or ""}
            for s in servers
        ]
        server_formset = ServerManagementIpFormSet(initial=initial, prefix="servers")
        return render(request, self.template_name, {"naming_request": naming_request, "server_formset": server_formset})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = list(naming_request.server_allocations.all().order_by("server_number"))
        server_formset = ServerManagementIpFormSet(request.POST, prefix="servers")
        if not server_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "server_formset": server_formset})
        management_ips = [form.cleaned_data["management_ip"] for form in server_formset.forms]
        complete_step1_management_ips(
            naming_request=naming_request,
            servers=servers,
            management_ips=management_ips,
        )

        return redirect("admin_naming_request_detail", pk=naming_request.pk)


class AdminNamingRequestStep2View(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = "naming/requests/step2_hypervisor_admin.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        return get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")
        server_forms = []
        for server in servers:
            instance = getattr(server, "hypervisor_os", None)
            server_forms.append((server, HypervisorOSForm(instance=instance, prefix=f"hv-{server.pk}")))
        return render(request, self.template_name, {"naming_request": naming_request, "server_forms": server_forms})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")
        server_forms = []
        all_valid = True

        for server in servers:
            instance = getattr(server, "hypervisor_os", None)
            form = HypervisorOSForm(request.POST, instance=instance, prefix=f"hv-{server.pk}")
            server_forms.append((server, form))
            if not form.is_valid():
                all_valid = False

        if not all_valid:
            return render(request, self.template_name, {"naming_request": naming_request, "server_forms": server_forms})
        server_forms_data = [(server, form.cleaned_data) for server, form in server_forms]
        complete_step2_hypervisors(naming_request=naming_request, server_forms_data=server_forms_data)

        return redirect("admin_naming_request_detail", pk=naming_request.pk)


class AdminNamingRequestStep3View(StaffRequiredMixin, NamingRequestStep3View):
    template_name = "naming/requests/step3_vms_admin.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)
        return naming_request

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all()
        hypervisors = HypervisorOS.objects.filter(server__in=servers).order_by("server__server_number")

        vm_formset = build_virtual_machine_formset(hypervisors=hypervisors, data=request.POST, prefix="vm")
        if not vm_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "vm_formset": vm_formset})

        vm_rows = []
        for form in vm_formset:
            cleaned = form.cleaned_data
            if not cleaned or not cleaned.get("vm_name"):
                continue
            if not cleaned.get("hypervisor"):
                vm_formset.non_form_errors = [
                    "Hypervisor is required for rows where VM Name is provided."
                ]  # type: ignore[attr-defined]
                return render(
                    request,
                    self.template_name,
                    {"naming_request": naming_request, "vm_formset": vm_formset},
                )
            vm_rows.append(dict(cleaned))

        saved_count = replace_step3_vms(
            naming_request=naming_request,
            hypervisors=hypervisors,
            vm_rows=vm_rows,
        )

        if saved_count == 0:
            vm_formset.non_form_errors = ["Please add at least one VM."]  # type: ignore[attr-defined]
            return render(
                request, self.template_name, {"naming_request": naming_request, "vm_formset": vm_formset}
            )

        return redirect("admin_naming_request_detail", pk=naming_request.pk)


class AdminNamingRequestStep4View(StaffRequiredMixin, NamingRequestStep4View):
    template_name = "naming/requests/step4_network_admin.html"

    def get_object(self, request: HttpRequest, pk: int) -> NamingRequest:
        naming_request = get_object_or_404(NamingRequest, pk=pk, status=NamingRequest.Status.PENDING)
        return naming_request

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        naming_request = self.get_object(request, pk)
        servers = naming_request.server_allocations.all().order_by("server_number")

        net_formset = build_network_configuration_formset(servers=servers, data=request.POST, prefix="net")
        if not net_formset.is_valid():
            return render(request, self.template_name, {"naming_request": naming_request, "net_formset": net_formset})

        net_rows = []
        for form in net_formset:
            cleaned = form.cleaned_data
            if not cleaned or not cleaned.get("server_port_name"):
                continue
            if not cleaned.get("server"):
                net_formset.non_form_errors = [
                    "Server is required for rows where Port Name is provided."
                ]  # type: ignore[attr-defined]
                return render(
                    request,
                    self.template_name,
                    {"naming_request": naming_request, "net_formset": net_formset},
                )
            net_rows.append(dict(cleaned))

        saved_count = replace_step4_network(
            naming_request=naming_request,
            servers=servers,
            net_rows=net_rows,
        )

        if saved_count == 0:
            net_formset.non_form_errors = ["Please add at least one network row."]  # type: ignore[attr-defined]
            return render(
                request,
                self.template_name,
                {"naming_request": naming_request, "net_formset": net_formset},
            )

        return redirect("admin_naming_request_detail", pk=naming_request.pk)

