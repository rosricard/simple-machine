"""gRPC adapter implementing the PubSub Protocol (interfaces/pub_sub.py).

To regenerate stubs from adapters/proto/orchestration.proto, from project root:

    python -m grpc_tools.protoc \
        -I adapters/proto \
        --python_out=adapters/proto \
        --grpc_python_out=adapters/proto \
        adapters/proto/orchestration.proto
"""
from __future__ import annotations

import asyncio
import logging

from climbing_bot.commands.schema import Command

log = logging.getLogger(__name__)


class GrpcPubSub:
    """gRPC server that translates inbound RPCs into Command objects on a queue.

    TODO: implement once protoc has been run.
        - Start grpc.aio.server bound to host:port.
        - Register OrchestrationServicer that turns SendCommand RPCs into
          Command objects and puts them on self._inbox.
        - publish() writes to a streamed StatusEvent channel.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 50051) -> None:
        self.host: str = host
        self.port: int = port
        self._inbox: asyncio.Queue[Command] = asyncio.Queue()

    async def start(self) -> None:
        raise NotImplementedError("TODO: implement gRPC server startup")

    async def recv(self) -> Command:
        return await self._inbox.get()

    async def publish(self, event: dict) -> None:
        # TODO(streaming-telemetry): push to StreamStatus subscribers.
        log.debug("publish %s", event)
