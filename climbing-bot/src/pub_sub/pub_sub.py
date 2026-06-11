# normally this would live in a separate interface repo (like a proto) that would
# be imported and then used.
#
# The PubSub Protocol is the messaging boundary: the controller depends only on
# `recv()` / `publish()`, so the transport (NATS in production, in-memory for
# tests) is swapped at the composition root and never leaks into domain code.
from __future__ import annotations

from typing import Protocol

from interfaces.commands import Command
from interfaces.events import Event


class PubSub(Protocol):
    """Transport-agnostic messaging between orchestration and the bot."""

    async def recv(self) -> Command:
        """Block until the next command arrives from orchestration."""
        ...

    async def publish(self, event: Event) -> None:
        """Emit a telemetry event back to orchestration."""
        ...
