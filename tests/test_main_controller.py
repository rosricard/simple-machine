"""Unit test for MainController using in-memory fakes (no gRPC, no subprocess).

Uses stdlib unittest.IsolatedAsyncioTestCase (Python 3.8+) — no pytest-asyncio
or any third-party test dependency needed.

Run from the project root:
    python -m unittest tests.test_main_controller
    # or discover all:
    python -m unittest discover

TODO: add tests/test_grpc_integration.py that spins up a real grpc.aio.server
and a sim.mock_bot_server subprocess fixture.
"""
from __future__ import annotations

import asyncio
import contextlib
import unittest
from typing import List

from commands.schema import Command, CommandType
from controllers.main_controller import MainController
from motion.pose import Pose


class FakePubSub:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Command] = asyncio.Queue()
        self.published: List[dict] = []

    async def push(self, cmd: Command) -> None:
        await self._queue.put(cmd)

    async def recv(self) -> Command:
        return await self._queue.get()

    async def publish(self, event: dict) -> None:
        self.published.append(event)


class FakeSignalRepo:
    def __init__(self) -> None:
        self.calls: List[str] = []

    async def move_to(self, pose: Pose) -> None:
        self.calls.append(f"move_to {pose}")

    async def home(self) -> None:
        self.calls.append("home")

    async def abort(self) -> None:
        self.calls.append("abort")

    async def read_state(self) -> dict:
        return {"state": "idle"}


class FakeGripper:
    async def open(self) -> None: ...
    async def close(self) -> None: ...
    async def read_state(self) -> dict:
        return {}


class MainControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_receives_command(self) -> None:
        pub_sub = FakePubSub()
        controller = MainController(
            pub_sub=pub_sub,
            signal_repo=FakeSignalRepo(),
            gripper=FakeGripper(),
        )

        await pub_sub.push(Command(id="1", type=CommandType.HOME))

        task = asyncio.create_task(controller.run())
        await asyncio.sleep(0.05)
        task.cancel()
        # Await the cancellation so unittest doesn't warn about a pending task.
        with contextlib.suppress(asyncio.CancelledError):
            await task
        # TODO: assert dispatch effects once _dispatch is implemented
        #   (e.g., that signal_repo.home was called for a HOME command).


if __name__ == "__main__":
    unittest.main()
