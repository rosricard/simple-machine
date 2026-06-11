"""Fault types and their mitigation strategies.

Faults are first-class: each carries a code and the strategy the controller
should apply. Keeping the strategy on the fault (rather than scattered in the
controller) means the policy for "what to do when X happens" is declared in one
place and is testable in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FaultCode(Enum):
    AXIS_FAULT = auto()        # a drive group entered its faulted state
    UNREACHABLE = auto()       # commanded pose outside the work envelope
    MOTION_TIMEOUT = auto()    # axis failed to reach target within deadline
    COMMS_LOSS = auto()        # lost the pub/sub or fieldbus link
    COLLISION = auto()         # bounding-box / range-sensor violation
    ESTOP = auto()             # external emergency stop asserted


class MitigationStrategy(Enum):
    HOLD = auto()              # stop in place, keep authority, await operator
    ABORT_AND_HOME = auto()    # abandon trajectory, return to a safe reference
    ESTOP_RESET = auto()       # drop authority; requires explicit reset to clear


# Default policy: which strategy applies to which fault. Tunable per deployment.
DEFAULT_MITIGATION: dict[FaultCode, MitigationStrategy] = {
    FaultCode.AXIS_FAULT: MitigationStrategy.ABORT_AND_HOME,
    FaultCode.UNREACHABLE: MitigationStrategy.HOLD,
    FaultCode.MOTION_TIMEOUT: MitigationStrategy.ABORT_AND_HOME,
    FaultCode.COMMS_LOSS: MitigationStrategy.HOLD,
    FaultCode.COLLISION: MitigationStrategy.ESTOP_RESET,
    FaultCode.ESTOP: MitigationStrategy.ESTOP_RESET,
}


@dataclass(frozen=True)
class Fault:
    code: FaultCode
    message: str = ""

    @property
    def mitigation(self) -> MitigationStrategy:
        return DEFAULT_MITIGATION[self.code]
