"""Event schemas — telemetry the bot publishes back to orchestration.

Frozen dataclasses with `to_dict` for serialization over pub/sub. These let the
orchestration system track progress (which waypoint, trajectory done) and faults
without polling.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Union

from interfaces.enums import EventType


@dataclass(frozen=True)
class StateChanged:
    """Bot FSM transitioned between high-level states."""

    from_state: str
    to_state: str
    type: EventType = field(default=EventType.STATE_CHANGED, init=False)


@dataclass(frozen=True)
class TrajectoryStarted:
    trajectory_id: str
    waypoint_count: int
    type: EventType = field(default=EventType.TRAJECTORY_STARTED, init=False)


@dataclass(frozen=True)
class WaypointReached:
    """Bot stopped at and is holding the given waypoint index."""

    trajectory_id: str
    index: int
    type: EventType = field(default=EventType.WAYPOINT_REACHED, init=False)


@dataclass(frozen=True)
class TrajectoryComplete:
    trajectory_id: str
    type: EventType = field(default=EventType.TRAJECTORY_COMPLETE, init=False)


@dataclass(frozen=True)
class Faulted:
    code: str
    message: str
    type: EventType = field(default=EventType.FAULTED, init=False)


@dataclass(frozen=True)
class CommandRejected:
    command_type: str
    reason: str
    type: EventType = field(default=EventType.COMMAND_REJECTED, init=False)


Event = Union[
    StateChanged,
    TrajectoryStarted,
    WaypointReached,
    TrajectoryComplete,
    Faulted,
    CommandRejected,
]


def to_dict(event: Event) -> dict:
    """Serialize an event to a pub/sub payload (enum values flattened to str)."""
    payload = asdict(event)
    payload["type"] = event.type.value
    return payload
