from __future__ import annotations

from typing import Protocol


class GripperRepository(Protocol):
    """Separate from SignalRepository — gripper has its own I/O channel."""

    async def open(self) -> None: ...

    async def close(self) -> None: ...

    async def read_state(self) -> dict: ...
