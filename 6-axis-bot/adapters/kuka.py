"""Kuka SignalRepository impl.

TODO: implement using Kuka's chosen comms layer (KRL, RSI, etc).
"""
from __future__ import annotations

from climbing_bot.motion.pose import Pose


class KukaRepository:
    async def move_to(self, pose: Pose) -> None:
        raise NotImplementedError

    async def home(self) -> None:
        raise NotImplementedError

    async def abort(self) -> None:
        raise NotImplementedError

    async def read_state(self) -> dict:
        raise NotImplementedError
