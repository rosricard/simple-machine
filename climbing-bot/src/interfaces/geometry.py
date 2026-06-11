"""Geometry primitives for trajectory commands.

A `Waypoint` is a fully-specified pose for the 4-axis climber: a 3D position plus
a rotation about Z. A `Trajectory` is the ordered list of waypoints the bot stops
at, in order. Authoring is in the world frame (millimetres / radians); the
actuation layer converts to per-axis targets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from interfaces.enums import Axis


@dataclass(frozen=True)
class Waypoint:
    """A pose the bot should stop at.

    x / y / z in millimetres, rz in radians (rotation about Z). The bot drives
    all four axes to this pose and holds until every axis is in position before
    advancing to the next waypoint.
    """

    x: float
    y: float
    z: float
    rz: float = 0.0

    def axis_targets(self) -> dict[Axis, float]:
        """Decompose into per-axis setpoints for the drive groups."""
        return {Axis.X: self.x, Axis.Y: self.y, Axis.Z: self.z, Axis.RZ: self.rz}


@dataclass(frozen=True)
class Trajectory:
    """An ordered set of waypoints from orchestration.

    `id` lets orchestration correlate the WAYPOINT_REACHED / TRAJECTORY_COMPLETE
    events back to the request. `cruise_speed` is an optional hint (mm/s) the
    motion layer may clamp to axis limits.
    """

    id: str
    waypoints: list[Waypoint] = field(default_factory=list)
    cruise_speed: float | None = None

    def __post_init__(self) -> None:
        if not self.waypoints:
            raise ValueError("trajectory must contain at least one waypoint")

    def __len__(self) -> int:
        return len(self.waypoints)
