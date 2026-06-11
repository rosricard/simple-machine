# Architecture

Design rationale for `climbing-bot`. The README has scope and orientation; this
document covers the *why* behind the structural decisions. It's the sibling of
`6-axis-bot/Architecture.md` and follows the same ports-and-adapters spirit,
adapted to a Cartesian climbing robot driven by a waypoint trajectory.

## Layered architecture

```
┌─ Orchestration (external) ─── NATS ──> BotController          ← transport hidden behind PubSub Protocol
├─ BotController ─── event-driven FSM + timed IO loop           ← single event loop, no locks
│    ├─ BotStateMachine ─── high-level bot FSM (event-driven)   ← lifecycle: idle→homing→…→executing⇄holding
│    └─ TrajectoryManager ─── active trajectory + cursor        ← the "top level task" object
├─ ActuationController ─── coordinates 4 drive groups           ← waypoint → per-axis setpoints; emits edge events
│    └─ DriveGroup ×4 ─── per-axis FSM (X, Y, Z, RZ)            ← disabled→idle→moving→in_position
├─ SignalRepository ─── vendor-agnostic motion I/O (HAL)        ← command(axis,target) / feedback(axis)
└─ MockSignalRepository · (real CAN/EtherCAT impl)              ← swappable concrete adapters
```

The application core (`BotController`, the two state machines, `TrajectoryManager`)
depends only on abstractions: the `PubSub` Protocol for messaging and the
`SignalRepository` ABC for motion I/O. Concrete implementations — NATS, the mock,
eventually a fieldbus client — are injected at the composition root (`main.py`).
Consequences mirror the 6-axis project: application code never imports the
transport or the bus, tests run with no I/O, and swapping the mock for real
hardware is a one-line change in `main.py`.

## The three loops

`BotController.run()` is `asyncio.gather` over three coroutines. Only one is a
timed loop; the bot FSM is **event-driven**.

| Coroutine | Responsibility | Driven by |
|---|---|---|
| **IO** (`_io_loop`) | Tick the drive groups so they sample feedback; emit an edge event when the last axis settles (or faults) | timer — 200 Hz |
| **Actuation events** (`_actuation_event_loop`) | The bot FSM's reaction to motion: `await` the next edge event, fire `arrived` / `advance` / `finish` or `fault` | event — `await queue.get()` |
| **Orchestration** (`_orchestration_loop`) | Consume commands from pub/sub, load trajectories, fire FSM events | event — `await recv()` |

**Why the bot FSM is event-driven, not a timed loop.** Polling `at_waypoint()`
on a fixed cadence couples the FSM's responsiveness to a tick rate and burns
cycles asking "are we there yet?" Instead the FSM sleeps until something actually
happens: a command arrives, or actuation reports an edge. The two event sources
(`_actuation_event_loop`, `_orchestration_loop`) both fire transitions on the one
synchronous machine — safe because it's a single-threaded event loop, so there's
no concurrent access and no locking.

**Why IO is still timed.** Something has to sample hardware feedback to know when
an axis reaches its target — that's inherently periodic, and it lives at the
hardware boundary in the IO loop. The drive-group SMs transition on those samples
(`poll()` → `reached`), and `ActuationController.tick()` emits a single
`WAYPOINT_REACHED` edge event when the last axis arrives. So the periodicity is
confined to the HAL; everything above it reacts to events.

**Why one event loop, not threads.** All three coroutines share state (the FSMs,
the trajectory cursor, the actuation controller). A single-threaded event loop
means cooperative scheduling with no locks — the same reasoning as the 6-axis
`asyncio.gather`.

**Exit on fault.** When a drive group faults, the IO loop emits `FAULTED`; the
actuation-event loop drives the bot FSM to `faulted`, publishes the fault, and
raises `FaultExit`, which `asyncio.gather` cancels the siblings and propagates —
"run forever, exit on fault." A supervisor (out of scope) restarts `run()` after
an operator `reset`.

## Two state machines, split by altitude

Like the 6-axis project splits system-state from routine-phase, this splits the
**bot lifecycle** from the **per-axis drive lifecycle**. Both use
[`python-statemachine`](https://python-statemachine.readthedocs.io/); both are
synchronous (their callbacks do no blocking I/O). The drive groups are *ticked*
by the IO loop; the bot FSM is *fed events* by the actuation-event and
orchestration loops. Either way the surrounding async coroutines call sync events
directly.

Telemetry stays out of the sync machine: every transition is recorded in
`BotStateMachine.transition_log` (a sync `after_transition` hook), which the
controller drains and publishes as `StateChanged` events asynchronously.

### Bot FSM (`controller/fsm.py`)

```
booting → idle → homing → ready → executing ⇄ holding → completing → ready
                                                  (loop once per waypoint)
```

`executing` commands the current waypoint (on enter). When the actuation layer
emits `WAYPOINT_REACHED`, the actuation-event loop fires `arrived` (→ `holding`),
publishes `WaypointReached`, then either `advance` (→ `executing` with the next
waypoint) or `finish` (→ `completing` → `ready`). Nothing here is polled — the
FSM advances only in response to that edge event. Cross-cutting `abort` /
`fault` / `estop` transitions exist from every active state; `reset` recovers
from `faulted` / `estopped`. This is a representative subset of the production
~16-state machine, scoped to the trajectory path.

**Why `start` only from `ready`.** Motion requires energized axes, so a
trajectory can't begin until the bot has homed. Sending `execute_trajectory` from
`idle` raises `TransitionNotAllowed`, which the orchestration loop turns into a
`CommandRejected` event rather than a crash — the graph *is* the guard.

### Drive-group FSM (`actuation/drive_group.py`)

```
disabled → idle → moving → in_position
             ↑________________|            (re-command from in_position)
any non-fault → faulted → disabled         (reset)
```

One per axis. `command(target)` sets the setpoint and starts moving; `poll()`
(called each IO tick) compares sensed position to the setpoint and fires
`reached` once inside tolerance. This is the layer that *is* sampling-driven:
the IO loop ticks it, and its transitions react to feedback.

A waypoint is "reached" only when **all four** drive groups are `in_position` —
that's the mechanism that makes the bot *stop at* each waypoint before advancing.
`ActuationController.tick()` watches for that all-axes edge and emits a single
`WAYPOINT_REACHED` signal, which is what the (event-driven) bot FSM consumes. So
the boundary is clear: drive groups are polled at the hardware edge; the bot FSM
above them never polls.

## Why a waypoint is `(x, y, z, rz)`

The climber has four independently-driven axes: three linear (X, Y, Z) and one
rotational about Z. A `Waypoint` carries a setpoint for each. `Waypoint.axis_targets()`
decomposes it into the per-axis map the drive groups consume, so the conversion
from "pose" to "per-axis setpoints" lives in one place. A `Trajectory` is just an
ordered, non-empty list of waypoints plus an id for telemetry correlation.

Authoring is in world-frame millimetres / radians. Unlike the 6-axis arm there is
no IK or tool frame here — the axes *are* the Cartesian DOF, so a waypoint maps to
axis setpoints directly. (A real deployment adds an encoder-counts conversion per
axis; modeled as 1:1 here.)

## HAL: ABC here, Protocol in the 6-axis project

`SignalRepository` is an `abc.ABC`, not a `typing.Protocol`. Both are valid HAL
boundaries; the choice here is **local consistency** — the existing encoder
interfaces in `signal_repository/signal_repository.py` (`I_Encoder`, …) are
Beckhoff-style ABCs, so the motion interface matches them. The 6-axis project
documents the Protocol-vs-ABC tradeoff; the short version: Protocol conforms
third-party vendor classes without adapter boilerplate (caught by the type
checker), ABC gives nominal, runtime-enforced contracts. For a single in-house
HAL with a mock, ABC's explicitness is fine.

## Hide the transport behind PubSub

`BotController` depends on a `PubSub` Protocol (`recv()` / `publish()`). The
concrete transport — `NatsPubSub` in production, `InMemoryPubSub` for local/test
— is wired in at `main.py` and referenced nowhere else. Commands and events are
frozen dataclasses in `interfaces/`; `commands.from_dict` / `events.to_dict`
stand in for the generated proto (de)serializer. If orchestration moves transports,
only the `pub_sub/` impl changes.

`InMemoryPubSub.wait_for(predicate)` lets a local driver or test react to
telemetry the way a real orchestrator does — e.g. *wait for `ready` before
sending the trajectory* — instead of racing the control loop.

## Faults are first-class

`interfaces/fault.py` pairs each `FaultCode` with a `MitigationStrategy`
(`HOLD` / `ABORT_AND_HOME` / `ESTOP_RESET`) in a single policy table, so "what to
do when X happens" is declared in one place and testable in isolation rather than
scattered through the controller.

| Failure | Detection | Response |
|---|---|---|
| Axis fault | A `DriveGroup` enters `faulted` | Control loop fires bot `fault` → `ABORT_AND_HOME`; loops exit |
| Unreachable pose | Setpoint outside the work envelope (future: envelope check) | `HOLD`; operator intervention |
| Motion timeout | Axis fails to reach target within deadline (future: watchdog) | `ABORT_AND_HOME` |
| Comms loss | NATS / fieldbus link drops | `HOLD`; watchdog brings axes to a safe state |
| Collision | Bounding-box / range-sensor violation (future: `sensors/`) | `ESTOP_RESET` |
| E-stop | External estop asserted | `ESTOP_RESET`; requires explicit `reset` |
| Trajectory before home | `start` illegal from `idle` | `CommandRejected` event; state unchanged |

## Testing strategy

| Layer | What it uses | When it runs |
|---|---|---|
| Unit | A single FSM or the trajectory manager in isolation | Every commit; fast |
| SIL | Full stack via `InMemoryPubSub` + `MockSignalRepository`, real async loops | Pre-merge — see `test/controller/test_trajectory_execution.py` |
| HIL | Real fieldbus + a physical or hardware-in-the-loop rig | Pre-release |

The marker taxonomy (`unit` / `integration` / `sil` / `hil`) is declared in
`pyproject.toml`. The mock integrates a first-order motion model in real time
(sampled on `feedback()`, the same trick `EncoderVendor1` uses on `time.monotonic`),
so SIL tests exercise the real loop timing without hardware.

## Open questions / future work

- **Trajectory blending.** Today the bot fully stops at every waypoint
  (all axes `in_position`). Continuous-path motion (blend radius / look-ahead)
  would let it pass through intermediate waypoints without stopping.
- **Per-axis encoder scaling & limits.** The mock is 1:1 position units; real
  axes need counts-per-unit, soft limits, and a work-envelope reachability check
  feeding the `UNREACHABLE` fault.
- **Motion watchdog.** No `MOTION_TIMEOUT` detection yet — a per-axis deadline
  should fault a drive group that stalls.
- **Real homing.** Homing is modeled as "energize the axes"; a real bot drives
  each axis to a reference switch and waits, which means `homing → ready` becomes
  sensor-driven like `executing → holding`.
- **Safety relay.** `interfaces/fault.py` anticipates an estop path; the Modbus
  safety-relay service (its own entry point in the README) isn't wired here.
- **Digital twins.** The README mentions software replicas of hardware state for
  the manager layer; not modeled in this sample.
```
