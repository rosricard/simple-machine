from __future__ import annotations

from typing import Protocol

from commands.schema import Command


class PubSub(Protocol):
    """Transport-agnostic interface between orchestration and MainController.

    Concrete impl is gRPC (api/grpc_pub_sub.py). Tests use FakePubSub.
    """

    async def recv(self) -> Command: ...

    async def publish(self, event: dict) -> None: ...
    # TODO: replace dict with a typed Event once telemetry schema is defined.
