# simple-machine

A small machine that does robotic pick-and-place. Receives commands from an external
orchestration system over gRPC and dispatches them through a vendor-agnostic robot HAL.

This repo contains the application layer (state machine, command dispatch, hardware
abstraction). The vendor controller handles trajectory generation and inverse
kinematics; this application only deals with cartesian goals in well-defined frames.

## Status

**Scaffold + fakes + tests.** The architecture is laid out and the core controller
logic is exercised by in-memory fakes (`FakePubSub`, `FakeSignalRepo`, `FakeGripper`).
Concrete I/O implementations are stubbed pending integration — see Scope below.

Run the tests:

```bash
pip install pytest pytest-asyncio
pytest tests/
```

## Scope

### In scope

- Application-layer state machine (`IDLE / HOMING / RUNNING / ABORTING / ERROR`)
- Vendor-agnostic robot HAL (`SignalRepository`, `GripperRepository` Protocols)
- gRPC command intake hidden behind a `PubSub` Protocol so domain code doesn't import `grpc`
- Three named pick-and-place routines
- SIL testing path: mock bot as a separate process speaking the same wire protocol
- Frame conventions (user → base composition) at the application boundary
- Motion-authority lifecycle in the `SignalRepository` Protocol

### Out of scope

- **Actuation layer.** Vendor controller handles trajectory generation, inverse
  kinematics, and servo-loop timing. Real-time determinism is the controller's problem.
- **Perception.** No camera or vision integration. Routines use pre-taught poses
  authored in user frame; nothing detection-driven.
- **`GrpcPubSub.start()` implementation.** The gRPC service binding raises
  `NotImplementedError`. The Protocol contract and the rest of the stack are designed
  around it; the actual `grpc.aio.server` wiring is left for integration.
- **`MockBotClient` implementation.** The SIL client/server skeleton exists
  (`hal/mock_bot_client.py`, `sim/mock_bot_server.py`) but the gRPC stubs are not
  generated and the network calls are stubbed.
- Custom-arm kinematics (joint-level control, IK, FK, Jacobians).
- Multi-robot coordination.

## Robotics primitives — decisions

| Concept | Decision | Rationale |
|---|---|---|
| Frames (base / user / tool, TCP) | In scope | Pick/place poses authored in user frame, composed to base before send |
| Inverse / forward kinematics | Out of scope | Vendor controller handles IK from cartesian goals |
| Jacobians | Out of scope | Point-to-point pick-and-place doesn't need velocity/force control or singularity avoidance |
| TCP definition | Configured on the controller | Vendor knows about it; we just send cartesian targets and the controller positions the TCP |
| "Manipulation frame" | Not used | Not standard vendor terminology. We use user frame (workpiece) and tool frame (TCP) per Fanuc / KUKA / ABB conventions |

See `architecture.md` for the full design rationale behind each.

## Architecture (one paragraph)

Five layers, each hiding the layer below behind a Protocol so the application is
testable in isolation:

1. **Orchestration** (external) — speaks gRPC, hidden behind a `PubSub` Protocol.
2. **MainController** — state machine + asyncio queue; listener and processor run
   concurrently via `asyncio.gather`.
3. **SignalRepository / GripperRepository** — Protocols defining the robot HAL;
   gripper is on its own channel for independent timing and safety.
4. **Vendor impls / MockBotClient** — concrete adapters (Fanuc, KUKA, or the SIL
   mock bot in a separate process speaking the same gRPC wire).
5. **Actuation** — out of scope, owned by the vendor controller.

Full details in [`architecture.md`](architecture.md).

## File structure

```
.
├── main.py                          Entry point: wires concrete impls into MainController
├── controllers/
│   ├── main_controller.py           Event-driven state machine
│   └── states.py                    SystemState enum
├── api/
│   ├── pub_sub.py                   PubSub Protocol (transport-agnostic)
│   ├── grpc_pub_sub.py              gRPC implementation (stubbed — see Scope)
│   └── proto/
│       └── orchestration.proto
├── commands/
│   ├── schema.py                    Command dataclass + CommandType enum
│   └── routines.py                  Named routine IDs (task_a / task_b / task_c)
├── motion/
│   └── pose.py                      Vec3, Quaternion, Pose, Frame
├── hal/
│   ├── signal_repository.py         Robot motion Protocol
│   ├── gripper_repository.py        Gripper Protocol (separate I/O)
│   ├── mock_bot_client.py           SignalRepository → mock_bot_server (stubbed)
│   ├── fanuc.py                     Fanuc vendor stub
│   └── kuka.py                      KUKA vendor stub
├── sim/
│   ├── mock_bot.proto               Mock-bot wire protocol
│   └── mock_bot_server.py           Standalone process emulating a robot (stubbed)
└── tests/
    └── test_main_controller.py      FakePubSub / FakeSignalRepo / FakeGripper
```

## Future work

- Parameterized routine poses (currently fixed task IDs referenced by `routine_id`).
- Server-streaming telemetry RPC for live status (currently per-command ack only).
- Upgrade `asyncio.gather` to `asyncio.TaskGroup` on Python 3.11+ for cleaner
  cancellation semantics.
- Typed `Event` and `RobotState` dataclasses replacing dict payloads.
- Concrete `GrpcPubSub` and `MockBotClient` implementations once proto stubs are
  generated (`python -m grpc_tools.protoc ...`).
- Contract tests verifying every concrete `SignalRepository` implementation
  (Fanuc, KUKA, MockBotClient) satisfies the same behavioral expectations.

## References

- [FANUC ROS 2 Driver](https://github.com/FANUC-CORPORATION/fanuc_driver) — reference
  for the vendor interface a `FanucRepository` would wrap, including the motion-authority
  lifecycle that informs our `SignalRepository` Protocol.
