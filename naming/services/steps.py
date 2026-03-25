from __future__ import annotations

from typing import Literal

from django.core.exceptions import PermissionDenied, ValidationError

from naming.models import NamingRequest


StepNumber = Literal[1, 2, 3, 4]


def _assert_request_editable(request: NamingRequest) -> None:
    if request.status != NamingRequest.Status.DRAFT:
        raise PermissionDenied("This request is not editable by normal users.")


def assert_step_accessible(
    *,
    naming_request: NamingRequest,
    step: StepNumber,
) -> None:
    """
    Server-side step locking:
    - Step 1 is always accessible for DRAFT requests.
    - Step 2 requires step1_completed.
    - Step 3 requires step2_completed.
    - Step 4 requires step3_completed.
    """
    if naming_request.status != NamingRequest.Status.DRAFT:
        raise PermissionDenied("You can only work on DRAFT requests.")

    if step == 1:
        return
    if step == 2 and not naming_request.step1_completed:
        raise ValidationError("Complete Step 1 before accessing Step 2.")
    if step == 3 and not naming_request.step2_completed:
        raise ValidationError("Complete Step 2 before accessing Step 3.")
    if step == 4 and not naming_request.step3_completed:
        raise ValidationError("Complete Step 3 before accessing Step 4.")


def assert_step_submission_allowed(
    *,
    naming_request: NamingRequest,
    step: StepNumber,
) -> None:
    _assert_request_editable(naming_request)
    assert_step_accessible(naming_request=naming_request, step=step)


def assert_final_submission_allowed(naming_request: NamingRequest) -> None:
    if naming_request.status != NamingRequest.Status.DRAFT:
        raise PermissionDenied("Only DRAFT requests can be submitted.")

    missing: list[str] = []
    if not naming_request.step1_completed:
        missing.append("Step 1")
    if not naming_request.step2_completed:
        missing.append("Step 2")
    if not naming_request.step3_completed:
        missing.append("Step 3")
    if not naming_request.step4_completed:
        missing.append("Step 4")

    if missing:
        raise ValidationError(f"Cannot submit request. Missing completion: {', '.join(missing)}.")

