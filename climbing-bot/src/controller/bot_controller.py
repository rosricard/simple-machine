"""Top-level coordinator: wires the FSMs to actuation and pub/sub.

The bot FSM is **event-driven**. It does not run on a timed loop; it reacts to
two event sources:

    1. orchestration commands  — `_orchestration_loop` awaits the next command
    2. actuation signals       — `_actuation_event_loop` awaits the next edge
                                  event (waypoint reached / faulted)

The only timed loop is **IO** (`_io_loop`), which ticks the drive groups so they
sample hardware feedback. The drive-group state machines fire their own
transitions on those samples, and the ActuationController emits an edge event the
moment the last axis settles — which is what wakes the bot FSM. So the bot reacts
to events; only the hardware sampling is periodic.

All coroutines run in one event loop, so the synchronous FSMs need no locking.
The loops run forever and exit on fault: `_actuation_event_loop` raises
`FaultExit`, which `asyncio.gather` propagates after cancelling its siblings.
"""
from __future__ import annotations

import asyncio
import logging

from statemachine.exceptions import TransitionNotAllowed

from actuation.actuation_controller import ActuationController, ActuationSignal
from controller.fsm import BotStateMachine
from controller.trajectory_manager import TrajectoryManager
from interfaces import events
from interfaces.commands import Command, ExecuteTrajectory
from interfaces.enums import CommandType
from interfaces.fault import FaultCode
from pub_sub.pub_sub import PubSub

log = logging.getLogger(__name__)

IO_PERIOD_S = 0.005  # 200 Hz IO tick (hardware sampling — the only timed loop)


class FaultExit(Exception):
    """Raised by the actuation-event loop to unwind all loops on a latched fault."""


class BotController:
    def __init__(self, pub_sub: PubSub, actuation: ActuationController) -> None:
        self._pub_sub = pub_sub
        self._actuation = actuation
        self._trajectory = TrajectoryManager()
        self._bot = BotStateMachine(actuation, self._trajectory)
        # Actuation emits edge events into this queue; the bot FSM reacts to them.
        self._actuation_events: asyncio.Queue[ActuationSignal] = asyncio.Queue()
        actuation.set_listener(self._actuation_events.put_nowait)

    @property
    def bot(self) -> BotStateMachine:
        return self._bot

    async def run(self) -> None:
        log.info("bot controller starting; state=%s", self._bot.current_state_value)
        self._bot.boot_complete()  # booting -> idle
        await self._publish_transitions()
        try:
            await asyncio.gather(
                self._io_loop(),
                self._actuation_event_loop(),
                self._orchestration_loop(),
            )
        except FaultExit:
            log.error("bot faulted — all loops stopped")

    # -- timed loop: IO / hardware sampling --
    async def _io_loop(self) -> None:
        while True:
            self._actuation.tick()
            await asyncio.sleep(IO_PERIOD_S)

    # -- event-driven: react to actuation edge events --
    async def _actuation_event_loop(self) -> None:
        while True:
            signal = await self._actuation_events.get()
            if signal is ActuationSignal.WAYPOINT_REACHED:
                await self._on_waypoint_reached()
            elif signal is ActuationSignal.FAULTED:
                await self._on_fault()
                raise FaultExit

    async def _on_waypoint_reached(self) -> None:
        bot = self._bot
        if not bot.executing.is_active:
            return  # aborted / faulted between settling and handling — ignore
        bot.arrived()  # executing -> holding
        await self._pub_sub.publish(
            events.WaypointReached(self._trajectory.trajectory_id, self._trajectory.index)
        )
        if self._trajectory.has_next():
            self._trajectory.advance()
            bot.advance()  # -> executing, commands the next waypoint
        else:
            bot.finish()  # -> completing
            await self._pub_sub.publish(events.TrajectoryComplete(self._trajectory.trajectory_id))
            bot.completed()  # -> ready
        await self._publish_transitions()

    async def _on_fault(self) -> None:
        bot = self._bot
        if not bot.faulted.is_active:
            bot.fault()
        await self._pub_sub.publish(
            events.Faulted(code=FaultCode.AXIS_FAULT.name, message="drive group faulted")
        )
        await self._publish_transitions()

    # -- event-driven: react to orchestration commands --
    async def _orchestration_loop(self) -> None:
        while True:
            cmd = await self._pub_sub.recv()
            await self._handle_command(cmd)

    async def _handle_command(self, cmd: Command) -> None:
        bot = self._bot
        try:
            if isinstance(cmd, ExecuteTrajectory):
                self._trajectory.load(cmd.trajectory)
                bot.start()  # ready -> executing, commands waypoint 0
                await self._pub_sub.publish(
                    events.TrajectoryStarted(cmd.trajectory.id, len(cmd.trajectory))
                )
            elif cmd.type is CommandType.HOME:
                bot.home()  # -> homing (on_enter energizes the axes)
                # Homing is instantaneous in this sample; a real bot would fire
                # `homed` from an actuation event once the axes hit their
                # reference switches (like WAYPOINT_REACHED).
                bot.homed()  # -> ready
            elif cmd.type is CommandType.ABORT:
                bot.abort()
                bot.aborted()
            elif cmd.type is CommandType.RESET:
                bot.reset()
            elif cmd.type is CommandType.ESTOP:
                bot.estop()
        except TransitionNotAllowed as exc:
            log.warning("rejected %s: %s", cmd.type.value, exc)
            await self._pub_sub.publish(events.CommandRejected(cmd.type.value, str(exc)))
        await self._publish_transitions()

    # -- telemetry --
    async def _publish_transitions(self) -> None:
        """Drain the FSM's transition log, publishing one StateChanged each."""
        while self._bot.transition_log:
            source, target = self._bot.transition_log.pop(0)
            await self._pub_sub.publish(events.StateChanged(source, target))
