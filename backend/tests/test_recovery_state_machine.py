import pytest

from app.models import RecoveryCaseStatus
from app.recovery.state_machine import can_transition, transition


class _FakeCase:
    def __init__(self, status: RecoveryCaseStatus):
        self.status = status.value


VALID_EDGES = [
    (RecoveryCaseStatus.DETECTED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.PLANNED, RecoveryCaseStatus.VALIDATED),
    (RecoveryCaseStatus.PLANNED, RecoveryCaseStatus.FAILED),
    (RecoveryCaseStatus.VALIDATED, RecoveryCaseStatus.EXECUTING),
    (RecoveryCaseStatus.EXECUTING, RecoveryCaseStatus.RECOVERED),
    (RecoveryCaseStatus.EXECUTING, RecoveryCaseStatus.FAILED),
    (RecoveryCaseStatus.EXECUTING, RecoveryCaseStatus.ESCALATED),
    (RecoveryCaseStatus.FAILED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.FAILED, RecoveryCaseStatus.ESCALATED),
    (RecoveryCaseStatus.FAILED, RecoveryCaseStatus.EXHAUSTED),
]

INVALID_EDGES = [
    (RecoveryCaseStatus.DETECTED, RecoveryCaseStatus.VALIDATED),
    (RecoveryCaseStatus.DETECTED, RecoveryCaseStatus.EXECUTING),
    (RecoveryCaseStatus.DETECTED, RecoveryCaseStatus.RECOVERED),
    (RecoveryCaseStatus.PLANNED, RecoveryCaseStatus.EXECUTING),
    (RecoveryCaseStatus.PLANNED, RecoveryCaseStatus.RECOVERED),
    (RecoveryCaseStatus.VALIDATED, RecoveryCaseStatus.RECOVERED),
    (RecoveryCaseStatus.VALIDATED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.RECOVERED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.RECOVERED, RecoveryCaseStatus.FAILED),
    (RecoveryCaseStatus.ESCALATED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.EXHAUSTED, RecoveryCaseStatus.PLANNED),
    (RecoveryCaseStatus.FAILED, RecoveryCaseStatus.RECOVERED),
    (RecoveryCaseStatus.FAILED, RecoveryCaseStatus.DETECTED),
]


@pytest.mark.parametrize("current,new", VALID_EDGES)
def test_valid_transitions_are_allowed(current, new):
    assert can_transition(current, new) is True
    case = _FakeCase(current)
    transition(case, new)
    assert case.status == new.value


@pytest.mark.parametrize("current,new", INVALID_EDGES)
def test_invalid_transitions_are_rejected(current, new):
    assert can_transition(current, new) is False
    case = _FakeCase(current)
    with pytest.raises(ValueError):
        transition(case, new)
    # status must be unchanged after a rejected transition
    assert case.status == current.value


def test_terminal_states_have_no_outgoing_transitions():
    for terminal in (RecoveryCaseStatus.RECOVERED, RecoveryCaseStatus.ESCALATED, RecoveryCaseStatus.EXHAUSTED):
        for target in RecoveryCaseStatus:
            assert can_transition(terminal, target) is False
