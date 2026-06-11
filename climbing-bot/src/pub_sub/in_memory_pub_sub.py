"""In-process PubSub for local runs and tests.

Commands are fed in via `inject()` (standing in for orchestration); published
events are both recorded (for assertions) and pushed to a queue (so a test can
await specific telemetry).
"""
from __future__ import annotations

import asyncio
from typing import Callable

from interfaces.commands import Command
from interfaces.events import Event


class InMemoryPubSub:
    def __init__(self) -> None:
        self._commands: asyncio.Queue[Command] = asyncio.Queue()
        self.published: list[Event] = []
        self.events: asyncio.Queue[Event] = asyncio.Queue()

    # -- orchestration side (test / local driver) --
    async def inject(self, cmd: Command) -> None:
        await self._commands.put(cmd)

    async def wait_for(self, predicate: Callable[[Event], bool], timeout: float = 5.0) -> Event:
        """Block until a published event matches `predicate`.

        Models an orchestrator reacting to telemetry (e.g. wait for `ready`
        before sending a trajectory). Consumes from the events queue; the full
        history remains in `published` for assertions.
        """

        async def _loop() -> Event:
            while True:
                event = await self.events.get()
                if predicate(event):
                    return event

        return await asyncio.wait_for(_loop(), timeout)

    # -- PubSub Protocol (bot side) --
    async def recv(self) -> Command:
        return await self._commands.get()

    async def publish(self, event: Event) -> None:
        self.published.append(event)
        await self.events.put(event)
