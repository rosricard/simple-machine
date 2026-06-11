"""Holds the active trajectory and a cursor into it.

This is the "top level task" object the README mentions: the orchestration loop
loads a trajectory here, and the control loop advances the cursor as each
waypoint is reached. Keeping the cursor out of the FSM means the machine stays a
pure lifecycle graph and this stays a plain, testable data holder.
"""
from __future__ import annotations

from interfaces.geometry import Trajectory, Waypoint


class TrajectoryManager:
    def __init__(self) -> None:
        self._trajectory: Trajectory | None = None
        self._index = 0

    def load(self, trajectory: Trajectory) -> None:
        self._trajectory = trajectory
        self._index = 0

    def clear(self) -> None:
        self._trajectory = None
        self._index = 0

    @property
    def active(self) -> bool:
        return self._trajectory is not None

    @property
    def trajectory_id(self) -> str:
        assert self._trajectory is not None
        return self._trajectory.id

    @property
    def index(self) -> int:
        return self._index

    def current(self) -> Waypoint:
        assert self._trajectory is not None, "no trajectory loaded"
        return self._trajectory.waypoints[self._index]

    def has_next(self) -> bool:
        assert self._trajectory is not None
        return self._index + 1 < len(self._trajectory)

    def advance(self) -> None:
        self._index += 1
