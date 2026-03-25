from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from naming.models import DataCenter, NamingRequest, ServerAllocation


def generate_server_name(*, start_name: str, server_number: int, end_name: str) -> str:
    return f"{start_name}-SR{server_number}C-{end_name}"


def _find_first_available_block(
    *,
    start_number: int,
    end_number: int,
    allocated_numbers: set[int],
    block_size: int,
) -> list[int]:
    """
    Find the earliest contiguous block of `block_size` numbers not present in `allocated_numbers`.
    """

    if block_size <= 0:
        raise ValidationError("block_size must be a positive integer.")

    if start_number > end_number:
        raise ValidationError("Invalid DataCenter range.")

    max_start = end_number - block_size + 1
    for candidate_start in range(start_number, max_start + 1):
        block = list(range(candidate_start, candidate_start + block_size))
        if all(n not in allocated_numbers for n in block):
            return block

    raise ValidationError("No available contiguous server-number block found for the requested count.")


@dataclass(frozen=True)
class ReservedServer:
    server_number: int
    server_name: str


def reserve_server_block(
    *,
    naming_request: NamingRequest,
    data_center: DataCenter,
    count: int,
    management_ips: Iterable[str | None] | None = None,
    server_numbers: list[int] | None = None,
    max_retries: int = 5,
) -> list[ServerAllocation]:
    """
    Concurrency-safe reservation of a contiguous server-number block.

    Strategy:
    - Determine available contiguous block given currently allocated numbers.
    - Attempt to insert `ServerAllocation` rows for each reserved number.
    - Unique constraints on `server_name` / (data_center, server_number) prevent duplicates.
    - On conflict, retry the reservation selection.
    """

    if naming_request.status != NamingRequest.Status.DRAFT:
        raise ValidationError("Only DRAFT requests can reserve server numbers.")

    if data_center.id != naming_request.data_center_id:
        raise ValidationError("Request DataCenter mismatch.")

    if count <= 0:
        raise ValidationError("Count must be a positive integer.")

    if count > data_center.count_of_servers:
        raise ValidationError("Requested count exceeds DataCenter capacity.")

    management_ips_list = list(management_ips) if management_ips is not None else []
    if management_ips is not None and len(management_ips_list) != count:
        raise ValidationError("management_ips length must match count.")

    if server_numbers is not None:
        if len(server_numbers) != count:
            raise ValidationError("server_numbers length must match count.")

        sorted_nums = sorted(server_numbers)
        for n in sorted_nums:
            if n < data_center.start_numbers or n > data_center.end_numbers:
                raise ValidationError("server_numbers must be within DataCenter range.")

        # UX/story expectation: numbers are contiguous.
        if any(
            sorted_nums[i + 1] != sorted_nums[i] + 1
            for i in range(len(sorted_nums) - 1)
        ):
            raise ValidationError("server_numbers must be contiguous.")

        with transaction.atomic():
            created: list[ServerAllocation] = []
            try:
                for idx, server_number in enumerate(sorted_nums):
                    server_name = generate_server_name(
                        start_name=data_center.start_name,
                        server_number=server_number,
                        end_name=data_center.end_name,
                    )
                    mgmt_ip = None
                    if management_ips_list:
                        mgmt_ip = management_ips_list[idx] or None

                    created.append(
                        ServerAllocation.objects.create(
                            naming_request=naming_request,
                            data_center=data_center,
                            server_number=server_number,
                            server_name=server_name,
                            management_ip=mgmt_ip,
                        )
                    )
            except IntegrityError:
                raise ValidationError(
                    "Server-number reservation failed due to a concurrent allocation. Please regenerate Step 1."
                )

            naming_request.requested_server_count = count
            naming_request.save(update_fields=["requested_server_count", "updated_at"])
            return created

    for attempt in range(1, max_retries + 1):
        with transaction.atomic():
            # Read currently allocated numbers for this DataCenter.
            allocated_numbers = set(
                ServerAllocation.objects.filter(data_center=data_center).values_list(
                    "server_number", flat=True
                )
            )

            block_numbers = _find_first_available_block(
                start_number=data_center.start_numbers,
                end_number=data_center.end_numbers,
                allocated_numbers=allocated_numbers,
                block_size=count,
            )

            created: list[ServerAllocation] = []
            try:
                for idx, server_number in enumerate(block_numbers):
                    server_name = generate_server_name(
                        start_name=data_center.start_name,
                        server_number=server_number,
                        end_name=data_center.end_name,
                    )
                    mgmt_ip = None
                    if management_ips_list:
                        mgmt_ip = management_ips_list[idx] or None

                    created.append(
                        ServerAllocation.objects.create(
                            naming_request=naming_request,
                            data_center=data_center,
                            server_number=server_number,
                            server_name=server_name,
                            management_ip=mgmt_ip,
                        )
                    )
            except IntegrityError:
                # Someone else reserved overlapping numbers; retry with fresh state.
                if attempt == max_retries:
                    raise ValidationError("Failed to reserve servers due to concurrent reservations. Try again.")
                continue

            # Update request metadata after successful reservation.
            naming_request.requested_server_count = count
            naming_request.save(update_fields=["requested_server_count", "updated_at"])

            return created

    # Should be unreachable due to raising in the loop.
    raise ValidationError("Unable to reserve servers after retries.")


def preview_server_block(*, data_center: DataCenter, count: int) -> list[int]:
    """
    Non-mutating preview of the first available contiguous block.

    Used to render Step 1 server-name rows before persisting anything.
    """
    allocated_numbers = set(
        ServerAllocation.objects.filter(data_center=data_center).values_list(
            "server_number", flat=True
        )
    )
    return _find_first_available_block(
        start_number=data_center.start_numbers,
        end_number=data_center.end_numbers,
        allocated_numbers=allocated_numbers,
        block_size=count,
    )

