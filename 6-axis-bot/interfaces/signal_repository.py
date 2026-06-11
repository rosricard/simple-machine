from __future__ import annotations

from typing import Protocol

from climbing_bot.motion.pose import Pose


class SignalRepository(Protocol):
    """Vendor-agnostic robot motion interface.

    Concrete impls: hal/fanuc.py, hal/kuka.py, hal/mock_bot_client.py.

    TODO(custom-arm): add a joint-level variant for driving a non-vendor arm
    where this app is responsible for trajectory generation.
    """

    async def move_to(self, pose: Pose) -> None: ...

    async def home(self) -> None: ...

    async def abort(self) -> None: ...

    async def read_state(self) -> dict: ...
    # TODO: replace dict with a typed RobotState dataclass.
