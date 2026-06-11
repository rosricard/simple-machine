"""High-level system state machine, backed by python-statemachine.

Models the IDLE / HOMING / RUNNING / ABORTING / ERROR lifecycle as a transition
graph. Illegal transitions raise `TransitionNotAllowed`, which replaces the
hand-written state guards in the controller. I/O hangs off `on_enter_*` hooks;
the engine auto-detects the async callbacks.

The pick-and-place phase sequence is intentionally NOT modeled here — it is a
plain linear walk in `controllers.pick_place`.
"""
from __future__ import annotations

import logging

from statemachine import State, StateMachine

from climbing_bot.commands.routines import Routine
from climbing_bot.controllers.pick_place import run_pick_place
from climbing_bot.interfaces.gripper_repository import GripperRepository
from climbing_bot.interfaces.signal_repository import SignalRepository

log = logging.getLogger(__name__)


class RobotMachine(StateMachine):
    # State values match the strings used in Architecture.md / telemetry acks.
    idle = State(initial=True, value="idle")
    homing = State(value="homing")
    running = State(value="running")
    aborting = State(value="aborting")
    error = State(value="error")

    # Command-driven transitions (event names mirror CommandType where they map).
    home = idle.to(homing) | error.to(homing)
    pick_and_place = idle.to(running)
    abort = running.to(aborting) | idle.to(aborting)
    reset = error.to(idle)

    # Internal completions, fired from on_enter_* once the work finishes.
    _homed = homing.to(idle)
    _done = running.to(idle)
    _aborted = aborting.to(idle)

    # Any failure parks the machine; reset() recovers it.
    fail = idle.to(error) | homing.to(error) | running.to(error) | aborting.to(error)

    def __init__(self, signal_repo: SignalRepository, gripper: GripperRepository) -> None:
        self.signal_repo = signal_repo
        self.gripper = gripper
        super().__init__()

    async def on_enter_homing(self) -> None:
        await self.signal_repo.home()
        await self._homed()

    async def on_enter_running(self, routine: Routine) -> None:
        await run_pick_place(self.signal_repo, self.gripper, routine)
        await self._done()

    async def on_enter_aborting(self) -> None:
        await self.signal_repo.abort()
        await self._aborted()
