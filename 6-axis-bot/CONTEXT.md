# Context export — pick-and-place machine

Snapshot of decisions, structure, and open questions for use in a separate context window (e.g., when preparing a cheat sheet).

## Problem

Interview-style assignment from `readme.md`: build a small machine that does robotic pick-and-place. Inputs come from an orchestration system (manual + auto mode) over gRPC. Three different pick-and-place tasks. Actuation layer is out of scope.

Conceptual layers:
1. Orchestration (external) → MainController via gRPC
2. MainController — event-driven state machine
3. Signal Repository — vendor-agnostic robot HAL
4. Control Device library — vendor HALs (Fanuc, Kuka, …)
5. Mock bot — separate process for SIL testing
6. Actuation layer — out of scope

## Architectural decisions (resolved questions)

| Topic | Decision |
|---|---|
| Overall architecture | **Hexagonal / Ports-and-Adapters.** `interfaces/` holds Protocols (ports); `adapters/` holds concrete impls. Domain code (`controllers/`, `commands/`, `motion/`) depends only on `interfaces/`. Tests depend only on `interfaces/` + domain, never on `adapters/`. |
| Orchestration transport | gRPC. Hide behind a `PubSub` Protocol so the rest of the code doesn't import gRPC. |
| Tasks | Fixed routines for now (`task_a`, `task_b`, `task_c`). TODO: parameterized poses. |
| Kinematics | Assume vendor controller handles IK + trajectory generation; this app sends cartesian goals. TODO: custom-arm support (joint-level + IK / FK / Jacobian). |
| Gripper | Separate interface (`GripperRepository`), distinct from `SignalRepository`. |
| Manual mode | Same `Command` schema as auto for now. TODO: split if pendant / jog commands diverge (continuous velocity input). |
| Status / telemetry | Per-command ack only. TODO: server-streaming `StreamStatus` RPC. |
| Mock bot | Separate process, speaks gRPC — same wire protocol shape as the real robot. Reuses gRPC tooling. |
| Concurrency | `asyncio.gather` (Python 3.9 compat). TODO: upgrade to `asyncio.TaskGroup` on Python 3.11+. |

## Assumptions

1. Three pick-place tasks are parameterized by source/target pose (initially modeled as fixed routine IDs).
2. Orchestration speaks JSON-over-gRPC.
3. Vendor controller does IK + trajectory; app sends cartesian goals.
4. Single-arm, single-gripper.
5. No hard real-time requirement (actuation is out of scope).
6. Manual vs auto differ in command source/cadence, not schema.

## Robotic theory — relevance for this scope

Point-to-point pick-and-place with a vendor controller (Fanuc / Kuka):

| Concept | Relevant? | Why |
|---|---|---|
| Frames (base / user / tool) | **Yes — essential** | Pick/place poses are naturally in workpiece (user) frame; need transforms to robot base frame. |
| TCP (tool center point) | **Yes — essential** | Defines where the gripper tip is relative to the flange. |
| Basic fundamentals (DH params, transforms) | **Yes** | Needed for frame math. |
| Inverse kinematics | **Probably no** | Fanuc/Kuka controllers do IK internally when given cartesian targets. Becomes needed only for custom arm at joint level. |
| Jacobians | **No** at this scope | Matter for velocity/force control, singularity avoidance, continuous-path blending. Not for point-to-point. |
| Forward kinematics | Same as IK | Vendor handles it. Needed only for custom arm. |

## File structure (scaffold)

```
python/
├── main.py                                composition root — wires adapters into MainController
├── interfaces/                            PORTS — Protocols only, no I/O dependencies
│   ├── pub_sub.py                         PubSub Protocol — transport-agnostic
│   ├── signal_repository.py               robot motion Protocol (move_to/home/abort/read_state)
│   └── gripper_repository.py              separate gripper Protocol (open/close/read_state)
├── adapters/                              ADAPTERS — concrete impls of the ports
│   ├── grpc_pub_sub.py                    gRPC impl of PubSub (start() raises NotImplementedError)
│   ├── mock_bot_client.py                 SignalRepository impl that talks to mock-bot process
│   ├── fanuc.py                           vendor SignalRepository stub
│   ├── kuka.py                            vendor SignalRepository stub
│   └── proto/orchestration.proto          service + message defs (gRPC adapter's wire protocol)
├── controllers/                           DOMAIN — depends only on interfaces/
│   ├── main_controller.py                 @dataclass; listener + processor via asyncio.gather
│   ├── robot_machine.py                   RobotMachine (python-statemachine): idle/homing/running/aborting/error
│   ├── pick_place.py                      linear pick-and-place phase walk (move_to + gripper)
│   └── states.py                          PickPlacePhase enum
├── commands/                              DOMAIN
│   ├── schema.py                          Command dataclass, CommandType enum
│   └── routines.py                        3 routines: pick/place Pose pairs
├── motion/                                DOMAIN
│   └── pose.py                            Vec3, Quaternion, Pose, Frame
├── sim/                                   SIL test double — separate process
│   ├── mock_bot.proto                     mock-bot wire protocol (Robot service)
│   └── mock_bot_server.py                 standalone: python -m sim.mock_bot_server
├── tests/                                 depends only on interfaces/ + domain
│   └── test_main_controller.py            FakePubSub / FakeSignalRepo / FakeGripper
└── readme.md                              original problem statement
```

**Dependency rule**: arrows point inward only. `adapters/` and `tests/` may import from `interfaces/` and domain (`controllers/`, `commands/`, `motion/`). `interfaces/` and domain must NOT import from `adapters/`. `main.py` is the only place that imports `adapters/`.

## Key objects

| Object | Role |
|---|---|
| `MainController` | Owns queue + repos + `RobotMachine`. Runs `_listen_commands` and `_process_commands` concurrently; `_dispatch` maps commands → machine events. |
| `RobotMachine` | python-statemachine over idle/homing/running/aborting/error; I/O on `on_enter_*` hooks |
| `PickPlacePhase` | Enum: linear routine phases (approach/descend/grasp/lift/.../retract), walked by `pick_place.py` |
| `Command` | dataclass `{id, type, routine_id}` (TODO: poses, frame) |
| `CommandType` | Enum: PICK_AND_PLACE, HOME, ABORT, STATUS |
| `Pose` | `{position: Vec3, orientation: Quaternion}` |
| `Frame` | Named transform (base / user / tool); TCP lives in tool frame |
| `PubSub` (Protocol) | `recv() → Command`, `publish(event)` |
| `SignalRepository` (Protocol) | `move_to / home / abort / read_state` — vendor-agnostic |
| `GripperRepository` (Protocol) | `open / close / read_state` — separate I/O channel |
| `GrpcPubSub` | Concrete PubSub via grpc.aio.server (stubbed) |
| `MockBotClient` | SignalRepository that talks to mock_bot_server (stubbed) |
| `FanucRepository` / `KukaRepository` | Vendor SignalRepository impls (stubbed) |
| `mock_bot_server.py` | Standalone process emulating a robot via gRPC |

## What runs today vs. what's stubbed

**Runs**:
- `pytest tests/` with in-memory fakes (`FakePubSub`, `FakeSignalRepo`, `FakeGripper`). Needs `pytest pytest-asyncio` (asyncio_mode=auto in pytest.ini).
- Runtime dep: `pip install python-statemachine` (the high-level `RobotMachine`).
- `MainController._dispatch()` — full state machine: commands → `RobotMachine` events, with the pick-and-place phase walk driving `signal_repo` + `gripper`.

**Stubbed (next things to fill in)**:
- `GrpcPubSub.start()` in `adapters/grpc_pub_sub.py` — needs grpc.aio.server + servicer.
- `MockBotClient.*` in `adapters/mock_bot_client.py` — needs gRPC client calls.
- `sim/mock_bot_server.py` — needs RobotServicer impl.

**Proto stub generation** (when ready):
```sh
python -m grpc_tools.protoc \
  -I adapters/proto --python_out=adapters/proto --grpc_python_out=adapters/proto \
  adapters/proto/orchestration.proto

python -m grpc_tools.protoc \
  -I sim --python_out=sim --grpc_python_out=sim \
  sim/mock_bot.proto
```

## TODO markers by category (in-code)

- **`parameterized-routines`** — `commands/schema.py`, `commands/routines.py`, `adapters/proto/orchestration.proto`
- **`custom-arm`** — `motion/pose.py`, `interfaces/signal_repository.py`
- **`manual-mode`** — `commands/schema.py`
- **`streaming-telemetry`** — `adapters/grpc_pub_sub.py`, `controllers/main_controller.py`, `adapters/proto/orchestration.proto`
- **`upgrade to asyncio.TaskGroup`** — `controllers/main_controller.py` (Python 3.11+)
- **Misc** — typed `Event` / `RobotState` dataclasses to replace `dict`; mock-bot servicer impl; integration tests with subprocess fixture.

## Suggested cheat-sheet topics (for the other context window)

Topics that came up that are worth crisp notes on:
1. **Frames in robotics** — base / user / tool, TCP, how to compose transforms.
2. **When IK / Jacobians matter** — vendor controller vs custom arm.
3. **Protocol vs ABC in Python typing** — structural vs nominal subtyping; why we used Protocol for `PubSub` / `SignalRepository`.
4. **`@dataclass` patterns** — `field(default_factory=...)` for mutable defaults like `asyncio.Queue`.
5. **asyncio concurrency primitives** — `gather` (3.9-compatible) vs `TaskGroup` (3.11+) vs raw `create_task`. Cancellation semantics.
6. **gRPC in Python** — `.proto` → `protoc` → generated stubs → hide behind your own Protocol so callers don't import gRPC.
7. **SIL testing pattern** — same wire protocol as real hardware, separate process, swap repo impls.
8. **Profiling / timing tools** — `timeit`, `cProfile`, `tracemalloc`, `line_profiler`, `memory_profiler`, `pyinstrument`, `scalene`, `py-spy`, `snakeviz`, `perfplot`, `big_O`.

## Open follow-up offers

At end of last turn I offered two next steps:
- Generate proto stubs so gRPC compiles, OR
- Fill in `MainController._dispatch` to wire routines through `signal_repo` + `gripper`.
