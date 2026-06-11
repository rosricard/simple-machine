# Architecture

Detailed design rationale for `simple-machine`. The README has scope and orientation;
this document covers the *why* behind the structural decisions.

## Layered architecture

```
┌─ Orchestration (external) ─── gRPC ──> MainController        ← transport hidden behind PubSub Protocol
├─ MainController ─── state machine + asyncio.Queue            ← async listener + processor
├─ SignalRepository / GripperRepository ─── Protocols          ← vendor-agnostic robot HAL
├─ Vendor impls (Fanuc, KUKA) · MockBotClient (SIL)            ← swappable concrete adapters
└─ Actuation ─── OUT OF SCOPE (vendor controller)
```

The pattern is Hexagonal / Ports-and-Adapters: the application core (MainController,
command handling, routine execution) depends only on Protocols (`PubSub`,
`SignalRepository`, `GripperRepository`). Concrete implementations (gRPC, vendor SDKs,
the mock bot) are injected at the boundary in `main.py`. Consequences:

- The application code never imports `grpc`, vendor SDKs, or any transport-specific module.
- Tests inject fakes and run with no I/O.
- Switching from a Fanuc cell to a KUKA cell is a one-line change in `main.py`.

## Key design decisions

### Protocol over ABC for the HAL

We use `typing.Protocol` (structural subtyping) rather than `abc.ABC` (nominal
subtyping) for `SignalRepository` and `GripperRepository`.

**Why.** Vendor SDKs ship classes we don't control. With ABC, we'd need adapter
classes that inherit from our ABC and delegate to the vendor class — boilerplate
that scales with the number of vendors. With Protocol, any class with the right
method signatures conforms automatically, including third-party classes and test
fakes. The tradeoff: Protocol violations are caught by static type checkers (mypy)
rather than at runtime, which we accept because the type-check pass is part of CI.

### Gripper on a separate Protocol from the robot

`GripperRepository` is a distinct Protocol, not a method on `SignalRepository`.

**Why.** The gripper is a separate I/O channel with its own timing and safety
considerations. Treating it as part of the robot's motion API conflates two
independently-failing devices. In a real cell the gripper might:

- Run on a different network or fieldbus (Ethernet/IP, separate from the robot
  controller's connection).
- Have its own timeout, retry, and force-feedback logic.
- Need to be controlled by the MainController directly during certain abort
  sequences without going through the robot.

Keeping it on its own Protocol makes those concerns first-class.

### Mock bot in a separate process speaking the same wire protocol

For SIL (Software-In-the-Loop) testing we run the mock bot as a separate process
that exposes a gRPC interface identical to what the real robot's vendor adapter
expects. The `MockBotClient` (a `SignalRepository` impl) talks to it over the
network.

**Why.** An in-process mock would exercise controller logic but not the network
stack. Bugs in serialization, async handling, deadline management, or connection
lifecycle wouldn't surface until we tried real hardware. Running the mock bot as
a separate process forces us through the same code path as production. The
tradeoff is that SIL tests are heavier than unit tests, so we maintain both
layers: unit tests against in-memory fakes for fast feedback, SIL tests against
the mock-bot process for integration confidence.

### Hide gRPC behind a PubSub Protocol

`MainController` and the rest of the application depend on a `PubSub` Protocol
with `recv()` and `publish()` methods. The concrete `GrpcPubSub` implementation
is wired in at the entry point and not referenced anywhere else.

**Why.** This decouples the transport choice from the application logic. If
orchestration moves to MQTT, NATS, HTTP, or an in-memory queue for testing, only
`api/grpc_pub_sub.py` (and its sibling) changes. Application code, including
`MainController._dispatch`, is invariant.

### asyncio.gather for listener and processor

`MainController.run()` uses `asyncio.gather(self._listen_commands(), self._process_commands())`
to run command intake and dispatch concurrently in a single event loop.

**Why.** Two long-running coroutines share a queue. They need to run concurrently
but don't need separate threads — both are I/O-bound. A single-threaded event loop
eliminates the need for locking around the queue and the state machine.
`asyncio.gather` is the simplest primitive that gives us this. On Python 3.11+,
`asyncio.TaskGroup` provides cleaner cancellation semantics and is the upgrade path.

### Fixed routines first; parameterized later

`commands/routines.py` defines three named routines (`task_a`, `task_b`, `task_c`)
as fixed pose sequences. The `Command` dataclass references them by ID.

**Why.** Starts simpler. The interface (`Command` → `routine_id` → execution) is
the same whether routines are fixed identifiers or parameterized pose sets, so we
can swap the implementation later without changing the boundary. Parameterized
routines are listed in Future Work.

## State machine

Two machines, deliberately split by shape:

- **High level** — `controllers/robot_machine.py` defines `RobotMachine`, a
  [`python-statemachine`](https://python-statemachine.readthedocs.io/) machine over
  the `idle / homing / running / aborting / error` lifecycle. The transition graph
  *is* the guard logic: an illegal command raises `TransitionNotAllowed`, which
  `MainController` turns into a rejected ack. I/O hangs off `on_enter_*` hooks
  (e.g. `on_enter_homing` calls `signal_repo.home()`).
- **Routine level** — the pick-and-place phase sequence (`PickPlacePhase` in
  `controllers/states.py`, walked by `controllers/pick_place.py`). Kept as a plain
  linear function: a transition graph would be more ceremony than the
  `(phase, action)` table for a strictly linear sequence.

Top-level transitions:

| From → To | Event / trigger |
|---|---|
| idle → homing | `home` command |
| error → homing | `home` command (recovery) |
| idle → running | `pick_and_place` command |
| running → aborting | `abort` command or safety stop |
| any → error | `fail` — exception, timeout, unreachable pose |
| error → idle | `reset` command |

`homing → idle`, `running → idle`, and `aborting → idle` are internal
completions fired from the `on_enter_*` hooks once the work finishes.

`MainController._dispatch` only translates a `Command` into the matching event;
the graph enforces validity, so there are no hand-written state guards.

## Coordinate frames

We use the standard industrial-robotics frame taxonomy:

| Frame | What it is | Parent |
|---|---|---|
| world | Room-level fixed origin | — |
| base | Robot's mounting point | world |
| user / part | Workpiece-defined; pick/place poses live here | base (via calibration) |
| flange | End of the arm, before the tool | base (via FK from joint angles — dynamic) |
| tool / TCP | Working tip of the gripper | flange (configured at tool setup) |

Pick and place poses are authored in user frame and composed to base via
`T_base_user · pose_user = pose_base` before being sent to the vendor controller.
The `Pose` dataclass carries an explicit `frame` stamp so that frame mismatches
are caught at function boundaries — a pose in the wrong frame doesn't raise, it
silently moves the robot to the wrong physical location.

The vendor controller handles flange-to-TCP, IK, and trajectory generation. We
only send cartesian targets.

### Why user frame for authoring

Pick and place locations are physical features of the workpiece, so they belong
in the workpiece's frame, not the robot's base frame. If we authored them in
base, every fixture move or recalibration would invalidate every taught pose.
Authoring in user frame means we update one transform (`T_base_user`) when the
fixture changes, and all downstream poses stay correct.

## Vendor lifecycle

A real `SignalRepository` needs more than `move_to / home / abort / read_state`.
Vendor controllers (Fanuc, KUKA, ABB) all have an explicit motion-authority
lifecycle: the robot can be in teach mode, manual mode, faulted, executing a TP
program, etc. The application can't send motion commands unless it currently
owns motion control.

The Fanuc ROS 2 driver requires AUTO mode, all alarms cleared, teach pendant
disabled, and all TP programs aborted before it can take motion control via its
`switch_control_state` service. It publishes a `motion_possible` topic so the
application knows whether it currently owns the robot.

This is why `SignalRepository` includes:

```python
def acquire_motion_authority(self) -> None: ...
def release_motion_authority(self) -> None: ...
def reset_alarms(self) -> None: ...
```

And why `read_state` returns a `RobotState` that includes more than position:

```python
@dataclass(frozen=True)
class RobotState:
    pose: Pose
    joint_positions: list[float]
    motion_possible: bool       # do we own motion?
    alarm_active: bool          # pending alarms?
    in_motion: bool             # currently moving?
    last_error: str | None
```

Hiding this from the application layer would mean callers eventually invoke
`move_to` when they don't own the robot, and the failure mode is confusing
("nothing happened, but no error either"). Surfacing it in the type forces the
controller to reason about authority.

## Failure modes considered

| Failure | Detection | Response |
|---|---|---|
| Unreachable pose | Vendor returns error from `move_to` | → ERROR; operator must reset |
| Gripper timeout (object missing / jammed) | Gripper's own timeout fires | ABORTING → ERROR; future: force feedback for graceful recovery |
| Comms loss | gRPC deadline expires | Vendor watchdog puts robot in safe state; controller detects via `motion_possible = false` |
| Concurrent commands | Single-consumer queue (the processor coroutine) | Abort is the only command that can interrupt mid-routine |
| Partial routine completion | ABORTING leaves robot in mid-trajectory state | Recovery: home, then re-attempt |
| Frame mismatch | Pose in wrong frame moves robot to wrong place silently | Mitigation: frame is non-optional on `Pose`; asserted at function entry on every motion call |
| Alarm during execution | Vendor sets `motion_possible = false` | Controller must `reset_alarms()` + `acquire_motion_authority()` before resuming |

Frame mismatch is called out specifically because it's the rare failure that
*doesn't* throw — you find out when the gripper crashes into the fixture. Hence
the explicit `frame` field on `Pose` and the assertion discipline at every
function boundary that handles a pose.

## Testing strategy

Three layers:

| Layer | What it uses | When it runs |
|---|---|---|
| Unit | In-memory fakes (`FakePubSub`, `FakeSignalRepo`, `FakeGripper`); no I/O | Every commit; fast |
| SIL | Real gRPC protocol, `mock_bot_server.py` in a separate process | Pre-merge |
| Integration | Real vendor controller or vendor's simulator | Pre-release |

A **contract test** layer is planned for once we have more than one real
`SignalRepository` implementation: the same set of behavioral test cases run
against every concrete impl (Fanuc, KUKA, MockBotClient) to verify they all
satisfy the same Protocol semantics, not just the same Protocol shape.

## Open questions / future architecture work

- **Routine parameterization.** Currently routines are fixed IDs. Real cells will
  want parameterized routines (pick from pose A, place at pose B, with approach
  vectors per fixture). The `Command` schema needs a typed parameter set.
- **Manual mode schema.** Manual and auto currently share the `Command` schema.
  If a pendant / jog interface is added with continuous velocity input, the
  schema will need to fork — likely `Command` becomes a sum type.
- **Telemetry channel.** Currently per-command ack only. A server-streaming
  `StreamStatus` RPC would let orchestration see real-time state without polling.
- **Multi-fixture / multi-robot.** Both require expanding the frame system from
  module-level transforms to a `FrameTree` registry indexed by name. The data
  structure is already designed for this; the wiring isn't done.
