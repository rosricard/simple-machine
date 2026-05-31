"""Unit test for MainController using in-memory fakes (no gRPC, no subprocess).

Requires pytest-asyncio:
    pip install pytest pytest-asyncio

TODO: add tests/test_grpc_integration.py that spins up a real grpc.aio.server
and a sim.mock_bot_server subprocess fixture.
"""
from __future__ import annotations

import asyncio
from typing import List

import pytest

from commands.schema import Command, CommandType
from controllers.main_controller import MainController


class FakePubSub:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
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

    async def move_to(self, pose) -> None:
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


@pytest.mark.asyncio
async def test_main_controller_receives_command():
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
    # TODO: assert dispatch effects once _dispatch is implemented
    #   (e.g., that signal_repo.home was called for a HOME command).
