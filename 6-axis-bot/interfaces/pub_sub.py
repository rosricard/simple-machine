from __future__ import annotations

from typing import Protocol

from climbing_bot.commands.schema import Command


class PubSub(Protocol):
    """Transport-agnostic interface between orchestration and MainController.

    Concrete impl is gRPC (api/grpc_pub_sub.py). Tests use FakePubSub.
    
    Orchestrator Pushes, we consume from a buffer that orchestrator fills.
    """

    # Receive pops from the buffer. If Orchestrator hasn't sent anything, the call blocks (asynchronously, the event loop is free to do other things)
    # this is standard long running service waiting for instructions shape
    async def recv(self) -> Command: ...

    async def publish(self, event: dict) -> None: ...
    # TODO: replace dict with a typed Event once telemetry schema is defined.
