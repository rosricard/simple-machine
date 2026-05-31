"""SignalRepository impl that talks to the standalone mock-bot process.

Launch the mock bot in a separate terminal first:
    python -m sim.mock_bot_server

TODO: implement once stubs are generated from sim/mock_bot.proto.
"""
from __future__ import annotations

from motion.pose import Pose


class MockBotClient:
    def __init__(self, host: str = "localhost", port: int = 50061):
        self.host = host
        self.port = port

    async def move_to(self, pose: Pose) -> None:
        raise NotImplementedError("TODO: gRPC call to Robot.MoveTo")

    async def home(self) -> None:
        raise NotImplementedError("TODO: gRPC call to Robot.Home")

    async def abort(self) -> None:
        raise NotImplementedError("TODO: gRPC call to Robot.Abort")

    async def read_state(self) -> dict:
        raise NotImplementedError("TODO: gRPC call to Robot.ReadState")
