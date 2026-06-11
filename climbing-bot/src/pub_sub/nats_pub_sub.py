"""NATS-backed PubSub (production transport) — skeleton.

Subscribes to the command subject and publishes telemetry on the event subject,
(de)serializing via `interfaces.commands.from_dict` / `interfaces.events.to_dict`.
The connection wiring is left for integration; the rest of the stack is designed
around this satisfying the same `PubSub` Protocol as the in-memory impl.
"""
from __future__ import annotations

from interfaces.commands import Command
from interfaces.events import Event


class NatsPubSub:
    def __init__(self, servers: list[str], command_subject: str, event_subject: str) -> None:
        self._servers = servers
        self._command_subject = command_subject
        self._event_subject = event_subject
        # TODO: hold the nats.aio.client.Client and a JetStream context.

    async def connect(self) -> None:
        raise NotImplementedError("NATS connection wiring left for integration")

    async def recv(self) -> Command:
        raise NotImplementedError

    async def publish(self, event: Event) -> None:
        raise NotImplementedError
