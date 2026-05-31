import asyncio
import logging

from api.grpc_pub_sub import GrpcPubSub
from controllers.main_controller import MainController
from hal.mock_bot_client import MockBotClient

# Entry point wires concrete impls into MainController. Stubs still raise
# NotImplementedError — see TODOs in api/grpc_pub_sub.py, hal/mock_bot_client.py,
# and sim/mock_bot_server.py. Tests use in-memory fakes and run today.


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("starting main program")

    pub_sub = GrpcPubSub()
    await pub_sub.start()

    controller = MainController(
        pub_sub=pub_sub,
        signal_repo=MockBotClient(),
        gripper=None,  # TODO: pick a concrete GripperRepository impl
    )
    await controller.run()


if __name__ == "__main__":
    asyncio.run(main())
