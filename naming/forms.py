from __future__ import annotations

from django import forms
from django.forms import formset_factory

from naming.models import (
    DataCenter,
    HypervisorOS,
    NetworkConfiguration,
    NamingRequest,
    ServerAllocation,
    VirtualMachine,
)


class Step1GenerateForm(forms.Form):
    """
    Step 1 entry: select DataCenter block + number of servers.

    After "Generate", we show the server-name rows and collect management IPs
    before persisting anything.
    """

    data_center = forms.ModelChoiceField(
        queryset=DataCenter.objects.filter(is_active=True),
        empty_label=None,
        to_field_name="start_name",
        help_text="Select the DataCenter naming block.",
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
            }
        ),
    )
    count = forms.IntegerField(
        min_value=1,
        max_value=100000,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                "placeholder": "e.g., 5",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        dc: DataCenter = cleaned.get("data_center")
        count = cleaned.get("count")
        if dc and count:
            if count > dc.count_of_servers:
                raise forms.ValidationError("Requested count exceeds DataCenter capacity.")
        return cleaned


class ServerManagementIpForm(forms.Form):
    server_number = forms.IntegerField(widget=forms.HiddenInput())
    server_name = forms.CharField(widget=forms.HiddenInput())
    management_ip = forms.GenericIPAddressField(
        protocol="IPv4",
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                "placeholder": "e.g., 10.38.136.220",
            }
        ),
    )


class HypervisorOSForm(forms.ModelForm):
    class Meta:
        model = HypervisorOS
        fields = [
            "hv_os_name",
            "hypervisor_type_os_type",
            "management_ip",
            "ports",
            "version_build_number",
            "license_key_status",
            "expiration_date",
        ]
        widgets = {
            "hv_os_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "hypervisor_type_os_type": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "management_ip": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "ports": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "version_build_number": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "license_key_status": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "expiration_date": forms.DateInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "type": "date",
                }
            ),
        }


class VirtualMachineForm(forms.ModelForm):
    class Meta:
        model = VirtualMachine
        exclude = ["hypervisor", "created_at", "updated_at"]
        widgets = {
            "vm_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "management_ip": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "sub_function_other": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "software_vendor": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "os": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "activation_status": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "license_subscription_status": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "license_expiration_date": forms.DateInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "type": "date",
                }
            ),
            "application_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "vcpu_worker": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "vramsize_gb": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "storage_size_gb": forms.NumberInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
        }


class NetworkConfigurationForm(forms.ModelForm):
    class Meta:
        model = NetworkConfiguration
        exclude = ["server", "created_at", "updated_at"]
        widgets = {
            "server_port_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "connection_type": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "network_role": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "uplink_hostname": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "uplink_interface": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                    "rows": 2,
                }
            ),
            "lacp_group_port_channel_id": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
            "server": forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
        }


ServerManagementIpFormSet = formset_factory(
    ServerManagementIpForm,
    extra=0,
)


class NamingRequestStatusConfirmForm(forms.Form):
    """
    A small UX helper for the final submit action.
    """

    confirm = forms.BooleanField(required=True)


def build_virtual_machine_formset(*, hypervisors, data=None, prefix="vm"):
    """
    Build a dynamic formset for creating/updating VMs.

    For MVP: VM formset uses a hypervisor selector at each row, so users can
    create multiple VMs per hypervisor.
    """

    class VMRowForm(VirtualMachineForm):
        hypervisor = forms.ModelChoiceField(
            queryset=hypervisors,
            required=False,
            label="Hypervisor",
            empty_label="Select hypervisor",
            widget=forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
        )

        class Meta(VirtualMachineForm.Meta):
            fields = [
                "hypervisor",
                "vm_name",
                "management_ip",
                "sub_function_other",
                "software_vendor",
                "os",
                "activation_status",
                "license_subscription_status",
                "license_expiration_date",
                "application_name",
                "vcpu_worker",
                "vramsize_gb",
                "storage_size_gb",
            ]

    # Determine how many rows to render from POST if this is a submission.
    if data is not None:
        # Don't pass an initial list sized to TOTAL_FORMS.
        # This keeps Django's `empty_permitted` behavior working for blank extra rows.
        return formset_factory(VMRowForm, extra=0, min_num=0, validate_min=False)(
            data=data,
            prefix=prefix,
        )

    existing = VirtualMachine.objects.filter(hypervisor__in=hypervisors).order_by(
        "hypervisor_id", "vm_name"
    )
    initial: list[dict] = []
    for vm in existing:
        initial.append(
            {
                "hypervisor": vm.hypervisor_id,
                "vm_name": vm.vm_name,
                "management_ip": vm.management_ip,
                "sub_function_other": vm.sub_function_other,
                "software_vendor": vm.software_vendor,
                "os": vm.os,
                "activation_status": vm.activation_status,
                "license_subscription_status": vm.license_subscription_status,
                "license_expiration_date": vm.license_expiration_date,
                "application_name": vm.application_name,
                "vcpu_worker": vm.vcpu_worker,
                "vramsize_gb": vm.vramsize_gb,
                "storage_size_gb": vm.storage_size_gb,
            }
        )

    return formset_factory(VMRowForm, extra=1, min_num=0, validate_min=False)(
        data=data,
        prefix=prefix,
        initial=initial,
    )


def build_network_configuration_formset(*, servers, data=None, prefix="net"):
    """
    Build a formset for creating/updating NetworkConfiguration rows.

    MVP: each row lets user pick the target server.
    """

    class NetRowForm(NetworkConfigurationForm):
        server = forms.ModelChoiceField(
            queryset=servers,
            required=False,
            label="Server",
            empty_label="Select server",
            widget=forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm focus:border-violet-500 focus:outline-none focus:ring-4 focus:ring-violet-200",
                }
            ),
        )

        class Meta(NetworkConfigurationForm.Meta):
            fields = [
                "server",
                "server_port_name",
                "connection_type",
                "network_role",
                "uplink_hostname",
                "uplink_interface",
                "description",
                "lacp_group_port_channel_id",
            ]

    if data is not None:
        return formset_factory(NetRowForm, extra=0, min_num=0, validate_min=False)(
            data=data,
            prefix=prefix,
        )

    existing = NetworkConfiguration.objects.filter(server__in=servers).order_by(
        "server_id", "server_port_name"
    )
    initial: list[dict] = []
    for net in existing:
        initial.append(
            {
                "server": net.server_id,
                "server_port_name": net.server_port_name,
                "connection_type": net.connection_type,
                "network_role": net.network_role,
                "uplink_hostname": net.uplink_hostname,
                "uplink_interface": net.uplink_interface,
                "description": net.description,
                "lacp_group_port_channel_id": net.lacp_group_port_channel_id,
            }
        )

    return formset_factory(NetRowForm, extra=1, min_num=0, validate_min=False)(
        data=data,
        prefix=prefix,
        initial=initial,
    )

