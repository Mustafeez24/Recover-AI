"""The recovery case lifecycle.

The core loop is: DETECTED -> PLANNED -> VALIDATED -> EXECUTING -> RECOVERED
(or FAILED, or ESCALATED). A FAILED case can be re-planned (another
attempt), escalated, or -- once too many attempts have been made --
exhausted.

Two edges are added beyond that core loop, both necessary consequences of
having an explicit validation step and an ESCALATE action:
  - PLANNED -> FAILED: the safety validator rejected the planned action.
  - EXECUTING -> ESCALATED: the action that was executed was itself
    ESCALATE (see `simulate_execution`), so the case lands directly in
    ESCALATED rather than RECOVERED/FAILED.
"""

from app.models.enums import RecoveryCaseStatus

VALID_TRANSITIONS = {
    RecoveryCaseStatus.DETECTED: {RecoveryCaseStatus.PLANNED},
    RecoveryCaseStatus.PLANNED: {RecoveryCaseStatus.VALIDATED, RecoveryCaseStatus.FAILED},
    RecoveryCaseStatus.VALIDATED: {RecoveryCaseStatus.EXECUTING},
    RecoveryCaseStatus.EXECUTING: {
        RecoveryCaseStatus.RECOVERED,
        RecoveryCaseStatus.FAILED,
        RecoveryCaseStatus.ESCALATED,
    },
    RecoveryCaseStatus.FAILED: {
        RecoveryCaseStatus.PLANNED,
        RecoveryCaseStatus.ESCALATED,
        RecoveryCaseStatus.EXHAUSTED,
    },
    RecoveryCaseStatus.RECOVERED: set(),
    RecoveryCaseStatus.ESCALATED: set(),
    RecoveryCaseStatus.EXHAUSTED: set(),
}

TERMINAL_STATES = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.ESCALATED,
    RecoveryCaseStatus.EXHAUSTED,
}


def can_transition(current: RecoveryCaseStatus, new: RecoveryCaseStatus) -> bool:
    return new in VALID_TRANSITIONS.get(current, set())


def transition(case, new_status: RecoveryCaseStatus) -> None:
    """Move `case.status` to `new_status`, raising if the edge isn't valid."""
    current = RecoveryCaseStatus(case.status)
    if not can_transition(current, new_status):
        raise ValueError(
            f"Invalid state transition: {current.value} -> {new_status.value}"
        )
    case.status = new_status.value
