"""Composition root.

Wires the concrete transport (pub/sub) and HAL (signal repository) into the
domain (ActuationController + BotController), then runs the three forever loops.
Swap `MockSignalRepository` / `InMemoryPubSub` for the real CAN/Modbus and NATS
impls here — nothing downstream changes.

The three loops (IO, bot FSM, orchestration intake) live inside
`BotController.run()`; see controller/bot_controller.py.

Run locally:
    PYTHONPATH=src python -m main
"""
from __future__ import annotations

import asyncio
import logging

from actuation.actuation_controller import ActuationController
from controller.bot_controller import BotController
from interfaces.commands import ExecuteTrajectory, Home
from interfaces.enums import EventType
from interfaces.geometry import Trajectory, Waypoint
from pub_sub.in_memory_pub_sub import InMemoryPubSub
from signal_repository.mock_signal_repository import MockSignalRepository

log = logging.getLogger(__name__)

DEMO_TRAJECTORY = Trajectory(
    id="demo",
    waypoints=[
        Waypoint(x=100.0, y=0.0, z=0.0),
        Waypoint(x=100.0, y=200.0, z=50.0),
        Waypoint(x=0.0, y=200.0, z=0.0, rz=1.57),
    ],
)


async def _orchestrator(pub_sub: InMemoryPubSub) -> None:
    """Stand-in for the external orchestration system.

    Reacts to telemetry the way a real orchestrator would: home, wait until the
    bot reports `ready`, then send the trajectory and wait for completion.
    """

    def reached_state(name: str):
        return lambda e: e.type is EventType.STATE_CHANGED and e.to_state == name

    await pub_sub.inject(Home())
    await pub_sub.wait_for(reached_state("ready"))

    await pub_sub.inject(ExecuteTrajectory(DEMO_TRAJECTORY))
    await pub_sub.wait_for(lambda e: e.type is EventType.TRAJECTORY_COMPLETE)
    log.info("trajectory complete")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info("starting climbing-bot")

    # --- adapters (swap for NATS + real SignalRepository in production) ---
    pub_sub = InMemoryPubSub()
    signal_repo = MockSignalRepository()

    # --- domain ---
    actuation = ActuationController(signal_repo)
    controller = BotController(pub_sub, actuation)

    # Run the bot's three loops; drive them from the stand-in orchestrator and
    # stop once the demo trajectory finishes.
    bot_task = asyncio.create_task(controller.run())
    await _orchestrator(pub_sub)
    bot_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
