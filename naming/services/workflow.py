from __future__ import annotations

from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from naming.models import (
    HypervisorOS,
    NamingRequest,
    NetworkConfiguration,
    ServerAllocation,
    VirtualMachine,
)


def complete_step1_management_ips(
    *,
    naming_request: NamingRequest,
    servers: Iterable[ServerAllocation],
    management_ips: list[str],
) -> None:
    if naming_request.status not in {NamingRequest.Status.DRAFT, NamingRequest.Status.PENDING}:
        raise ValidationError("Request is not editable.")

    servers_list = list(servers)
    if len(servers_list) != len(management_ips):
        raise ValidationError("Server count and management_ips length mismatch.")

    for server, ip in zip(servers_list, management_ips):
        server.management_ip = ip
        server.save(update_fields=["management_ip", "updated_at"])

    naming_request.step1_completed = all(s.management_ip for s in servers_list)
    naming_request.save(update_fields=["step1_completed", "updated_at"])


def complete_step2_hypervisors(
    *,
    naming_request: NamingRequest,
    server_forms_data: list[tuple[ServerAllocation, dict]],
) -> None:
    if naming_request.status not in {NamingRequest.Status.DRAFT, NamingRequest.Status.PENDING}:
        raise ValidationError("Request is not editable.")

    with transaction.atomic():
        for server, data in server_forms_data:
            # One-to-one per server allocation.
            HypervisorOS.objects.update_or_create(server=server, defaults=data)

        naming_request.step2_completed = naming_request.server_allocations.count() == naming_request.server_allocations.filter(
            hypervisor_os__isnull=False
        ).count()
        naming_request.save(update_fields=["step2_completed", "updated_at"])


def replace_step3_vms(
    *,
    naming_request: NamingRequest,
    hypervisors: Iterable[HypervisorOS],
    vm_rows: list[dict],
) -> int:
    if naming_request.status not in {NamingRequest.Status.DRAFT, NamingRequest.Status.PENDING}:
        raise ValidationError("Request is not editable.")

    hypervisors_list = list(hypervisors)

    with transaction.atomic():
        VirtualMachine.objects.filter(hypervisor__in=hypervisors_list).delete()

        saved_count = 0
        for row in vm_rows:
            hypervisor = row.pop("hypervisor")
            VirtualMachine.objects.create(hypervisor=hypervisor, **row)
            saved_count += 1

        naming_request.step3_completed = saved_count > 0
        naming_request.save(update_fields=["step3_completed", "updated_at"])

    return saved_count


def replace_step4_network(
    *,
    naming_request: NamingRequest,
    servers: Iterable[ServerAllocation],
    net_rows: list[dict],
) -> int:
    if naming_request.status not in {NamingRequest.Status.DRAFT, NamingRequest.Status.PENDING}:
        raise ValidationError("Request is not editable.")

    servers_list = list(servers)

    with transaction.atomic():
        NetworkConfiguration.objects.filter(server__in=servers_list).delete()

        saved_count = 0
        for row in net_rows:
            server = row.pop("server")
            NetworkConfiguration.objects.create(server=server, **row)
            saved_count += 1

        naming_request.step4_completed = saved_count > 0
        naming_request.save(update_fields=["step4_completed", "updated_at"])

    return saved_count


def final_submit_to_admin(*, naming_request: NamingRequest) -> None:
    if naming_request.status != NamingRequest.Status.DRAFT:
        raise ValidationError("Only DRAFT requests can be submitted.")

    naming_request.status = NamingRequest.Status.PENDING
    naming_request.submitted_at = timezone.now()
    naming_request.save(update_fields=["status", "submitted_at", "updated_at"])

