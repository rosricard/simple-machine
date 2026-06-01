from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from api.pub_sub import PubSub
from commands.schema import Command
from controllers.states import SystemState
from hal.gripper_repository import GripperRepository
from hal.signal_repository import SignalRepository

log = logging.getLogger(__name__)


@dataclass
class MainController:
    pub_sub: PubSub
    signal_repo: SignalRepository
    gripper: GripperRepository
    state: SystemState = SystemState.IDLE
    queue: asyncio.Queue[Command] = field(default_factory=asyncio.Queue)

    async def run(self) -> None:
        # asyncio.gather cancels siblings on first exception.
        # TODO: upgrade to asyncio.TaskGroup once on Python 3.11+.
        await asyncio.gather(
            self._listen_commands(),
            self._process_commands(),
            # TODO(streaming-telemetry): add self._publish_status() task
        )

    async def _listen_commands(self) -> None:
        log.info("listening for commands")
        while True:
            cmd = await self.pub_sub.recv()
            await self.queue.put(cmd)

    async def _process_commands(self) -> None:
        log.info("processing commands")
        while True:
            cmd = await self.queue.get()
            await self._dispatch(cmd)

    async def _dispatch(self, cmd: Command) -> None:
        # TODO: implement the state machine + routine execution.
        # Should look up the routine, drive signal_repo through its waypoints,
        # and coordinate gripper open/close at pick + place poses.
        log.info("dispatch %s in state %s", cmd, self.state)
