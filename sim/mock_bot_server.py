"""Standalone gRPC server that emulates a robot for SIL testing.

Run from project root:
    python -m sim.mock_bot_server

TODO: implement once stubs are generated from sim/mock_bot.proto.
    - Instantiate grpc.aio.server.
    - Register a RobotServicer that tracks a fake current_pose, sleeps a
      configurable duration on MoveTo to emulate motion, and returns acks.
"""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger(__name__)


async def serve(host: str = "0.0.0.0", port: int = 50061) -> None:
    log.info("mock bot listening on %s:%d", host, port)
    # Placeholder: idle forever so the process can be left running.
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
