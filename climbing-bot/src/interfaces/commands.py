"""Command schemas — what the orchestration layer sends over pub/sub.

Modeled as a small tagged union of frozen dataclasses. Each carries its
`CommandType` so the orchestration loop can dispatch without isinstance ladders,
and `from_dict` reconstructs them from a NATS/JSON payload.

In production this is the proto contract; the `from_dict` here stands in for the
generated deserializer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

from interfaces.enums import CommandType
from interfaces.geometry import Trajectory, Waypoint


@dataclass(frozen=True)
class ExecuteTrajectory:
    """Run an ordered set of waypoints, stopping at each."""

    trajectory: Trajectory
    type: CommandType = field(default=CommandType.EXECUTE_TRAJECTORY, init=False)


@dataclass(frozen=True)
class Home:
    """Home all axes (establish the reference position)."""

    type: CommandType = field(default=CommandType.HOME, init=False)


@dataclass(frozen=True)
class Abort:
    """Stop motion and return to idle, abandoning the active trajectory."""

    type: CommandType = field(default=CommandType.ABORT, init=False)


@dataclass(frozen=True)
class Reset:
    """Clear a fault / estop and return to idle."""

    type: CommandType = field(default=CommandType.RESET, init=False)


@dataclass(frozen=True)
class EStop:
    """Emergency stop — drop motion authority immediately."""

    type: CommandType = field(default=CommandType.ESTOP, init=False)


Command = Union[ExecuteTrajectory, Home, Abort, Reset, EStop]


def from_dict(payload: dict) -> Command:
    """Reconstruct a Command from a deserialized pub/sub payload.

    Stand-in for the generated proto deserializer.
    """
    kind = CommandType(payload["type"])
    if kind is CommandType.EXECUTE_TRAJECTORY:
        traj = payload["trajectory"]
        return ExecuteTrajectory(
            trajectory=Trajectory(
                id=traj["id"],
                waypoints=[Waypoint(**wp) for wp in traj["waypoints"]],
                cruise_speed=traj.get("cruise_speed"),
            )
        )
    return {
        CommandType.HOME: Home,
        CommandType.ABORT: Abort,
        CommandType.RESET: Reset,
        CommandType.ESTOP: EStop,
    }[kind]()
