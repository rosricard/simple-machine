"""Drive-group state machine (the low-level FSM the README calls out).

One DriveGroup per axis (X / Y / Z linear, RZ rotational). Each is a small
python-statemachine over the drive lifecycle:

    disabled → idle → moving → in_position
                 ↑________________|        (re-command from in_position)
    any non-fault → faulted → disabled     (reset)

The actuation layer commands a target and then `poll()`s every IO tick; the
group compares sensed position against its setpoint and transitions
moving → in_position once inside tolerance.

Synchronous on purpose: the machine does no I/O that blocks, so the surrounding
async control loops just call its events directly. All awaiting lives one layer
up in `controller/`.
"""
from __future__ import annotations

import logging

from statemachine import State, StateMachine

from interfaces.enums import Axis
from signal_repository.signal_repository import SignalRepository

log = logging.getLogger(__name__)

# Default in-position window (mm for linear axes, rad for RZ).
DEFAULT_TOLERANCE = 0.5


class DriveGroup(StateMachine):
    disabled = State(initial=True, value="disabled")
    idle = State(value="idle")
    moving = State(value="moving")
    in_position = State(value="in_position")
    faulted = State(value="faulted")

    enable = disabled.to(idle)
    disable = idle.to(disabled) | in_position.to(disabled)
    start_move = idle.to(moving) | in_position.to(moving)
    reached = moving.to(in_position)
    halt = moving.to(idle) | in_position.to(idle)
    fault = (
        disabled.to(faulted)
        | idle.to(faulted)
        | moving.to(faulted)
        | in_position.to(faulted)
    )
    reset = faulted.to(disabled)

    def __init__(self, axis: Axis, signal_repo: SignalRepository, tolerance: float = DEFAULT_TOLERANCE) -> None:
        self.axis = axis
        self._signal_repo = signal_repo
        self._tolerance = tolerance
        self._target = 0.0
        super().__init__()

    def command(self, target: float) -> None:
        """Set a new setpoint and begin moving."""
        self._target = target
        self._signal_repo.command(self.axis, target)
        if not self.moving.is_active:
            self.start_move()

    def poll(self) -> None:
        """Called each IO tick: settle moving → in_position once at target."""
        if not self.moving.is_active:
            return
        fb = self._signal_repo.feedback(self.axis)
        if abs(fb.position - self._target) <= self._tolerance:
            self.reached()

    def on_enter_state(self, target: State, event: str) -> None:
        log.debug("drive %s: %s -> %s", self.axis.value, event, target.id)
