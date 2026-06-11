"""Tests for MainController using in-memory fakes (no gRPC, no subprocess).

Uses pytest + pytest-asyncio. asyncio_mode = auto (see pytest.ini) means async
test functions are collected and run without an explicit marker.

Run from the project root:
    pytest tests/
    # or a single test:
    pytest tests/test_main_controller.py -k receives_command

TODO: add tests/test_grpc_integration.py that spins up a real grpc.aio.server
and a sim.mock_bot_server subprocess fixture.
"""
from __future__ import annotations

import asyncio
import contextlib

from climbing_bot.commands.schema import Command, CommandType
from climbing_bot.controllers.main_controller import MainController
from climbing_bot.motion.pose import Pose


class FakePubSub:
    def __init__(self) -> None:
        # initialize a queue of jobs to publish to controller and to keep track of assertions
        self._queue: asyncio.Queue[Command] = asyncio.Queue()
        # keep track of published events for assertions
        self.published: list[dict] = []

    async def push(self, cmd: Command) -> None:
        await self._queue.put(cmd)

    async def recv(self) -> Command:
        return await self._queue.get()

    async def publish(self, event: dict) -> None:
        self.published.append(event)


class FakeSignalRepo:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def move_to(self, pose: Pose) -> None:
        self.calls.append(f"move_to {pose}")

    async def home(self) -> None:
        self.calls.append("home")

    async def abort(self) -> None:
        self.calls.append("abort")

    async def read_state(self) -> dict:
        return {"state": "idle"}


class FakeGripper:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def open(self) -> None:
        self.calls.append("open")

    async def close(self) -> None:
        self.calls.append("close")

    async def read_state(self) -> dict:
        return {}


def make_controller() -> tuple[MainController, FakePubSub, FakeSignalRepo, FakeGripper]:
    pub_sub, signal_repo, gripper = FakePubSub(), FakeSignalRepo(), FakeGripper()
    controller = MainController(pub_sub=pub_sub, signal_repo=signal_repo, gripper=gripper)
    return controller, pub_sub, signal_repo, gripper


async def test_receives_command() -> None:
    controller, pub_sub, signal_repo, _ = make_controller()

    await pub_sub.push(Command(id="1", type=CommandType.HOME))

    task = asyncio.create_task(controller.run())
    await asyncio.sleep(0.05)
    task.cancel()
    # Await the cancellation so pytest doesn't warn about a pending task.
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert "home" in signal_repo.calls
    assert pub_sub.published[-1] == {"id": "1", "status": "completed"}


async def test_pick_and_place_runs_full_sequence() -> None:
    controller, _, signal_repo, gripper = make_controller()
    await controller.machine.activate_initial_state()

    await controller._dispatch(
        Command(id="1", type=CommandType.PICK_AND_PLACE, routine_id="task_a")
    )

    # 6 cartesian moves: approach/descend/lift + approach/descend/retract.
    moves = [c for c in signal_repo.calls if c.startswith("move_to")]
    assert len(moves) == 6
    # grasp closes before release opens.
    assert gripper.calls == ["close", "open"]
    assert controller.state == "idle"


async def test_unknown_routine_rejected() -> None:
    controller, pub_sub, signal_repo, _ = make_controller()
    await controller.machine.activate_initial_state()

    await controller._dispatch(
        Command(id="1", type=CommandType.PICK_AND_PLACE, routine_id="nope")
    )

    assert signal_repo.calls == []  # nothing moved
    assert pub_sub.published[-1]["status"] == "rejected"
    assert controller.state == "idle"


async def test_failure_parks_in_error_and_recovers() -> None:
    controller, pub_sub, signal_repo, _ = make_controller()
    await controller.machine.activate_initial_state()

    async def boom(_pose: Pose) -> None:
        raise RuntimeError("unreachable pose")

    signal_repo.move_to = boom  # type: ignore[method-assign]

    await controller._dispatch(
        Command(id="1", type=CommandType.PICK_AND_PLACE, routine_id="task_a")
    )
    assert controller.state == "error"
    assert pub_sub.published[-1]["status"] == "error"

    # Starting a routine from error is illegal -> rejected, state unchanged.
    await controller._dispatch(
        Command(id="2", type=CommandType.PICK_AND_PLACE, routine_id="task_a")
    )
    assert pub_sub.published[-1]["status"] == "rejected"
    assert controller.state == "error"

    # home recovers: error -> homing -> idle.
    await controller._dispatch(Command(id="3", type=CommandType.HOME))
    assert controller.state == "idle"
