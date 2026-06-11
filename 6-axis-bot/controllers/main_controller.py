from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field

from statemachine.exceptions import TransitionNotAllowed

from climbing_bot.commands.routines import ROUTINES
from climbing_bot.commands.schema import Command, CommandType
from climbing_bot.controllers.robot_machine import RobotMachine
from climbing_bot.interfaces.gripper_repository import GripperRepository
from climbing_bot.interfaces.pub_sub import PubSub
from climbing_bot.interfaces.signal_repository import SignalRepository

log = logging.getLogger(__name__)


@dataclass
class MainController:
    pub_sub: PubSub
    signal_repo: SignalRepository
    gripper: GripperRepository
    queue: asyncio.Queue[Command] = field(default_factory=asyncio.Queue)
    machine: RobotMachine = field(init=False)

    def __post_init__(self) -> None:
        self.machine = RobotMachine(self.signal_repo, self.gripper)

    @property
    def state(self) -> str:
        """Current high-level state value (idle/homing/running/aborting/error)."""
        return self.machine.current_state_value

    async def run(self) -> None:
        # In async mode the initial state isn't active until the first event;
        # activate it explicitly so STATUS works before any transition.
        await self.machine.activate_initial_state()
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
        """Translate a command into a RobotMachine event.

        The transition graph enforces which commands are legal in which state —
        an illegal one raises TransitionNotAllowed and is rejected without
        changing state. Any failure during execution drives the machine to ERROR.
        """
        log.info("dispatch %s in state %s", cmd, self.state)
        try:
            if cmd.type is CommandType.STATUS:
                # Read-only; valid in any state, no transition.
                await self._ack(cmd, "status", state=await self.signal_repo.read_state())
                return

            if cmd.type is CommandType.HOME:
                await self.machine.home()
                await self._ack(cmd, "completed")
            elif cmd.type is CommandType.PICK_AND_PLACE:
                routine = ROUTINES.get(cmd.routine_id or "")
                if routine is None:
                    await self._reject(cmd, f"unknown routine {cmd.routine_id!r}")
                    return
                await self.machine.pick_and_place(routine=routine)
                await self._ack(cmd, "completed")
            elif cmd.type is CommandType.ABORT:
                await self.machine.abort()
                await self._ack(cmd, "aborted")
            else:  # pragma: no cover - exhaustive over CommandType today
                await self._reject(cmd, f"unknown command type {cmd.type}")
        except TransitionNotAllowed as exc:
            await self._reject(cmd, str(exc))
        except Exception as exc:  # noqa: BLE001 - any failure parks the machine
            log.exception("command %s failed", cmd.id)
            # fail() is undefined from `error`, so guard the already-parked case.
            with contextlib.suppress(TransitionNotAllowed):
                await self.machine.fail()
            await self._ack(cmd, "error", error=str(exc))

    async def _ack(self, cmd: Command, status: str, **extra: object) -> None:
        await self.pub_sub.publish({"id": cmd.id, "status": status, **extra})

    async def _reject(self, cmd: Command, reason: str) -> None:
        log.warning("rejected %s: %s", cmd.id, reason)
        await self._ack(cmd, "rejected", reason=reason)
