import asyncio
import logging

from adapters.grpc_pub_sub import GrpcPubSub
from adapters.mock_bot_client import MockBotClient
from controllers.main_controller import MainController

# Composition root: wires concrete adapters into the domain MainController.
# Stubs still raise NotImplementedError — see TODOs in adapters/grpc_pub_sub.py,
# adapters/mock_bot_client.py, and sim/mock_bot_server.py. Tests use in-memory
# fakes (in tests/) that satisfy the Protocols in interfaces/ and run today.

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
