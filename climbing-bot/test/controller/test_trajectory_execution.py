"""Integration test: orchestration hands the bot a trajectory of waypoints and
the bot stops at each, in order.

Exercises the whole stack with the in-memory transport and the mock signal
repository — no hardware. This is the SIL-style happy path the README's three
loops exist to serve.
"""
from __future__ import annotations

import asyncio
import contextlib

import pytest

from actuation.actuation_controller import ActuationController
from controller.bot_controller import BotController
from interfaces.commands import Abort, ExecuteTrajectory, Home
from interfaces.enums import Axis, EventType
from interfaces.geometry import Trajectory, Waypoint
from pub_sub.in_memory_pub_sub import InMemoryPubSub
from signal_repository.mock_signal_repository import MockSignalRepository

WAYPOINTS = [
    Waypoint(x=100.0, y=0.0, z=0.0),
    Waypoint(x=100.0, y=200.0, z=50.0),
    Waypoint(x=0.0, y=200.0, z=0.0, rz=1.57),
]


def _reached(name: str):
    return lambda e: e.type is EventType.STATE_CHANGED and e.to_state == name


@contextlib.asynccontextmanager
async def running_bot():
    """Spin up the full stack and tear the loops down cleanly."""
    pub_sub = InMemoryPubSub()
    signal_repo = MockSignalRepository()
    actuation = ActuationController(signal_repo)
    controller = BotController(pub_sub, actuation)
    task = asyncio.create_task(controller.run())
    try:
        yield pub_sub, signal_repo, controller
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def test_executes_trajectory_visiting_each_waypoint() -> None:
    async with running_bot() as (pub_sub, signal_repo, controller):
        # Home, wait for ready, then send the trajectory.
        await pub_sub.inject(Home())
        await pub_sub.wait_for(_reached("ready"))

        await pub_sub.inject(ExecuteTrajectory(Trajectory(id="t1", waypoints=WAYPOINTS)))
        await pub_sub.wait_for(lambda e: e.type is EventType.TRAJECTORY_COMPLETE)

        # Every waypoint was reported reached, in order.
        reached = [e for e in pub_sub.published if e.type is EventType.WAYPOINT_REACHED]
        assert [e.index for e in reached] == [0, 1, 2]
        assert all(e.trajectory_id == "t1" for e in reached)

        # Final pose matches the last waypoint (within the in-position tolerance).
        last = WAYPOINTS[-1]
        assert signal_repo.feedback(Axis.X).position == pytest.approx(last.x, abs=0.5)
        assert signal_repo.feedback(Axis.Y).position == pytest.approx(last.y, abs=0.5)
        assert signal_repo.feedback(Axis.Z).position == pytest.approx(last.z, abs=0.5)
        assert signal_repo.feedback(Axis.RZ).position == pytest.approx(last.rz, abs=0.5)

        # Bot returns to ready, available for the next trajectory.
        assert controller.bot.current_state_value == "ready"


async def test_trajectory_before_home_is_rejected() -> None:
    async with running_bot() as (pub_sub, _signal_repo, controller):
        # No Home first → start is illegal from idle → rejected, not executed.
        await pub_sub.inject(ExecuteTrajectory(Trajectory(id="t2", waypoints=WAYPOINTS)))
        rejected = await pub_sub.wait_for(lambda e: e.type is EventType.COMMAND_REJECTED)
        assert rejected.command_type == "execute_trajectory"
        assert controller.bot.current_state_value in ("idle", "booting")


async def test_abort_returns_to_idle() -> None:
    async with running_bot() as (pub_sub, _signal_repo, controller):
        await pub_sub.inject(Home())
        await pub_sub.wait_for(_reached("ready"))

        await pub_sub.inject(ExecuteTrajectory(Trajectory(id="t3", waypoints=WAYPOINTS)))
        await pub_sub.wait_for(_reached("executing"))

        await pub_sub.inject(Abort())
        await pub_sub.wait_for(_reached("idle"))
        assert controller.bot.current_state_value == "idle"
