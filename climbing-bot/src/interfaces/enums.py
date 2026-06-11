"""Enums shared across the wire boundary.

State-name enums (bot / drive group) deliberately live with their state machines
in `controller/fsm.py` and `actuation/drive_group.py` — the machine is the source
of truth for its own states. The enums here are the ones that cross the
orchestration boundary (axes, command/event kinds).
"""
from __future__ import annotations

from enum import Enum


class Axis(str, Enum):
    """The four independently-driven axes of the climbing robot.

    X / Y / Z are linear; RZ is rotation about Z. `str` mixin so values
    serialize cleanly over NATS / JSON.
    """

    X = "x"
    Y = "y"
    Z = "z"
    RZ = "rz"


class CommandType(str, Enum):
    """Commands the orchestration layer can send."""

    EXECUTE_TRAJECTORY = "execute_trajectory"
    HOME = "home"
    ABORT = "abort"
    RESET = "reset"
    ESTOP = "estop"


class EventType(str, Enum):
    """Telemetry the bot publishes back to orchestration."""

    STATE_CHANGED = "state_changed"
    TRAJECTORY_STARTED = "trajectory_started"
    WAYPOINT_REACHED = "waypoint_reached"
    TRAJECTORY_COMPLETE = "trajectory_complete"
    FAULTED = "faulted"
    COMMAND_REJECTED = "command_rejected"
