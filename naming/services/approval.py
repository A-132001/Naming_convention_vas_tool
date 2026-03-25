from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from naming.models import (
    HypervisorOS,
    NamingRequest,
    NetworkConfiguration,
    ServerAllocation,
    VirtualMachine,
)


User = get_user_model()


def _serialize_request_for_rejection(naming_request: NamingRequest) -> dict[str, Any]:
    """
    Minimal snapshot for audit and debugging.
    Keep it small to avoid storing full form payloads.
    """

    snapshot: dict[str, Any] = {
        "request_id": naming_request.pk,
        "data_center": naming_request.data_center_id,
        "server_allocations": [],
    }

    servers = naming_request.server_allocations.all().order_by("server_number")
    for server in servers:
        server_data: dict[str, Any] = {
            "server_number": server.server_number,
            "server_name": server.server_name,
            "management_ip": server.management_ip,
            "hypervisor_os": None,
            "vms": [],
            "network": [],
        }

        hv: HypervisorOS | None = getattr(server, "hypervisor_os", None)
        if hv:
            server_data["hypervisor_os"] = {
                "hv_os_name": hv.hv_os_name,
                "hypervisor_type_os_type": hv.hypervisor_type_os_type,
                "management_ip": hv.management_ip,
                "ports": hv.ports,
                "version_build_number": hv.version_build_number,
            }

            vms = VirtualMachine.objects.filter(hypervisor=hv).order_by("vm_name")
            for vm in vms:
                server_data["vms"].append(
                    {
                        "vm_name": vm.vm_name,
                        "management_ip": vm.management_ip,
                        "os": vm.os,
                    }
                )

        networks = NetworkConfiguration.objects.filter(server=server).order_by("server_port_name")
        for net in networks:
            server_data["network"].append(
                {
                    "server_port_name": net.server_port_name,
                    "connection_type": net.connection_type,
                    "network_role": net.network_role,
                    "uplink_interface": net.uplink_interface,
                }
            )

        snapshot["server_allocations"].append(server_data)

    return snapshot


def approve_naming_request(*, admin_user: User, naming_request: NamingRequest) -> None:
    if not getattr(admin_user, "is_staff", False):
        raise PermissionDenied("Admin access is required.")

    if naming_request.status != NamingRequest.Status.PENDING:
        raise ValidationError("Only PENDING requests can be approved.")

    with transaction.atomic():
        naming_request.status = NamingRequest.Status.APPROVED
        naming_request.approved_at = timezone.now()
        naming_request.finalized_by_admin_at = timezone.now()
        naming_request.save(
            update_fields=["status", "approved_at", "finalized_by_admin_at", "updated_at"]
        )


def reject_naming_request(*, admin_user: User, naming_request: NamingRequest) -> None:
    if not getattr(admin_user, "is_staff", False):
        raise PermissionDenied("Admin access is required.")

    if naming_request.status != NamingRequest.Status.PENDING:
        raise ValidationError("Only PENDING requests can be rejected.")

    with transaction.atomic():
        snapshot = _serialize_request_for_rejection(naming_request)

        # Release reserved numbers by deleting draft step data.
        naming_request.server_allocations.all().delete()

        naming_request.rejected_snapshot_json = snapshot
        naming_request.status = NamingRequest.Status.REJECTED
        naming_request.finalized_by_admin_at = timezone.now()
        naming_request.step1_completed = False
        naming_request.step2_completed = False
        naming_request.step3_completed = False
        naming_request.step4_completed = False
        naming_request.save(
            update_fields=[
                "rejected_snapshot_json",
                "status",
                "finalized_by_admin_at",
                "step1_completed",
                "step2_completed",
                "step3_completed",
                "step4_completed",
                "updated_at",
            ]
        )

