"""Coordinates the four drive groups to execute a single waypoint.

This is the actuation entry point the high-level controller talks to. It hides
the per-axis drive groups behind a waypoint-level API: command a pose, tick the
IO, and ask whether the whole bot is in position. A waypoint is "reached" only
when *every* drive group is in position — that's what makes the bot stop at each
waypoint before advancing.

Synchronous, like the drive groups it owns; the async IO/control loops in
`controller/` call these methods directly.
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Callable, Optional

from actuation.drive_group import DEFAULT_TOLERANCE, DriveGroup
from interfaces.enums import Axis
from interfaces.geometry import Waypoint
from signal_repository.signal_repository import SignalRepository

log = logging.getLogger(__name__)


class ActuationSignal(Enum):
    """Edge events the actuation layer emits upward to the bot FSM."""

    WAYPOINT_REACHED = auto()  # all drive groups in position for the commanded pose
    FAULTED = auto()           # a drive group entered its faulted state


class ActuationController:
    """Coordinates the drive groups and emits edge events.

    The bot FSM is event-driven: rather than polling `at_waypoint()`, it reacts
    to the signal this controller emits the moment the *last* axis settles. The
    drive groups are still driven by the IO `tick()` (they sample feedback) — the
    timing lives here, at the hardware boundary, and the bot stays event-driven.
    """

    def __init__(self, signal_repo: SignalRepository, tolerance: float = DEFAULT_TOLERANCE) -> None:
        self._signal_repo = signal_repo
        self.drive_groups: dict[Axis, DriveGroup] = {
            axis: DriveGroup(axis, signal_repo, tolerance) for axis in Axis
        }
        self._listener: Optional[Callable[[ActuationSignal], None]] = None
        self._awaiting_waypoint = False
        self._fault_emitted = False

    def set_listener(self, listener: Callable[[ActuationSignal], None]) -> None:
        """Register the sink for emitted signals (the bot controller's queue)."""
        self._listener = listener

    def _emit(self, signal: ActuationSignal) -> None:
        if self._listener is not None:
            self._listener(signal)

    def enable(self) -> None:
        self._signal_repo.enable()
        for group in self.drive_groups.values():
            group.enable()

    def command_waypoint(self, waypoint: Waypoint) -> None:
        """Send each axis its component of the target pose."""
        log.info("commanding waypoint %s", waypoint)
        for axis, target in waypoint.axis_targets().items():
            self.drive_groups[axis].command(target)
        self._awaiting_waypoint = True

    def tick(self) -> None:
        """One IO-loop iteration: settle each drive group, then emit edge events.

        Edge-triggered: WAYPOINT_REACHED fires once when the last axis arrives,
        not every tick; FAULTED fires once per fault.
        """
        for group in self.drive_groups.values():
            group.poll()

        if self.faulted and not self._fault_emitted:
            self._fault_emitted = True
            self._emit(ActuationSignal.FAULTED)
            return

        if self._awaiting_waypoint and self.at_waypoint():
            self._awaiting_waypoint = False
            self._emit(ActuationSignal.WAYPOINT_REACHED)

    def at_waypoint(self) -> bool:
        """True once every drive group has reached its setpoint."""
        return all(group.in_position.is_active for group in self.drive_groups.values())

    def abort(self) -> None:
        """Stop motion, return drive groups to idle."""
        self._awaiting_waypoint = False
        for group in self.drive_groups.values():
            if group.moving.is_active or group.in_position.is_active:
                group.halt()

    def fault_all(self) -> None:
        for group in self.drive_groups.values():
            if not group.faulted.is_active:
                group.fault()

    @property
    def faulted(self) -> bool:
        return any(group.faulted.is_active for group in self.drive_groups.values())
