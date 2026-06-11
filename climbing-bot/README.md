# climbing robot

Control stack for a Cartesian climbing robot with four independently-driven axes
(X / Y / Z linear + RZ rotational). An external orchestration system hands the
bot a **trajectory of waypoints** over pub/sub; the bot stops at each waypoint in
turn, then reports completion.

This package is the application layer — high-level coordination and motion goals.
The vendor controller / RTOS owns real-time servo timing. An example hardware
abstraction is provided in `signal_repository/`.

## How it runs: an event-driven FSM + one timed IO loop

`BotController.run()` ([src/controller/bot_controller.py](src/controller/bot_controller.py))
gathers three cooperative coroutines in a single asyncio event loop (one thread,
so no locking). They run forever and exit on fault. The **bot FSM is
event-driven** — it does not poll on a timed loop; only IO is periodic.

1. **IO loop** (timed) — ticks the drive groups so they sample feedback from the
   signal repository. The per-axis drive-group FSM (`actuation/drive_group.py`,
   one per X / Y / Z linear axis + RZ rotational) transitions on those samples,
   and the `ActuationController` emits an edge event when the last axis settles.
   See `signal_repository/` for the IO abstractions over hardware.
2. **Actuation-event loop** (event-driven) — the bot FSM's reaction to motion:
   it `await`s the next edge event (waypoint reached / faulted) and drives the
   bot-level FSM (`controller/fsm.py`) accordingly. No polling.
3. **Orchestration loop** (event-driven) — `await`s commands/trajectories from
   the orchestration layer and loads them into the `TrajectoryManager` (the "top
   level task" object, `controller/trajectory_manager.py`).

So the bot-level FSM advances only in response to events (a command, or an
"in position" / fault signal from actuation); the drive-group FSMs are the
sampling-driven layer, ticked by the IO loop at the hardware boundary.

## Layout (`src/`)

```
src/
├── main.py                      ENTRY · composition root, wires adapters + runs the loops
│
├── controller/                  ── HIGH-LEVEL ORCHESTRATION ──
│   ├── bot_controller.py         the three async loops + command handling
│   ├── fsm.py                    bot state machine (booting → idle → … → executing ⇄ holding)
│   └── trajectory_manager.py     active trajectory + waypoint cursor
│
├── actuation/                   ── LOW-LEVEL MOTOR CONTROL (HAL) ──
│   ├── actuation_controller.py   coordinates the four drive groups; waypoint → per-axis setpoints
│   └── drive_group.py            per-axis state machine (disabled → idle → moving → in_position)
│
├── signal_repository/           ── HARDWARE IO ABSTRACTION ──
│   ├── signal_repository.py      I_Encoder + SignalRepository (vendor-agnostic motion I/O) ABCs
│   ├── axis.py                   AxisFeedback (sensed position / velocity)
│   └── mock_signal_repository.py in-memory motion model (no hardware)
│
├── interfaces/                  ── CONTRACTS (schemas, enums) ──
│   ├── geometry.py               Waypoint / Trajectory
│   ├── commands.py               ExecuteTrajectory / Home / Abort / Reset / EStop
│   ├── events.py                 telemetry published back to orchestration
│   ├── enums.py                  Axis, CommandType, EventType
│   └── fault.py                  fault codes + mitigation strategies
│
└── pub_sub/                     ── MESSAGING (hide transport) ──
    ├── pub_sub.py                PubSub Protocol (recv command / publish event)
    ├── in_memory_pub_sub.py      in-process transport for local runs / tests
    └── nats_pub_sub.py           NATS transport (production) — skeleton
```

Contracts live in `interfaces/` (command schemas, events, enums, fault types).
In production these would live in a separate repo as a proto contract imported by
both bot and orchestration. Messaging is hidden behind `pub_sub/` (NATS in
production, in-memory for tests).

Design rationale is in [Architecture.md](Architecture.md); an as-built diagram is
in [docs/architecture.md](docs/architecture.md).

## Build & run

```bash
poetry install
PYTHONPATH=src python -m main   # runs the demo: home, then a 3-waypoint trajectory
```

## Test

```bash
poetry run pytest          # SIL test: orchestration sends a trajectory, bot visits each waypoint
```

Tests run the full stack (`InMemoryPubSub` + `MockSignalRepository`) with no
hardware. Marker taxonomy (`unit` / `integration` / `sil` / `hil`) is declared in
`pyproject.toml`; `pythonpath = ["src"]` lets modules and tests import packages by
bare name.

## Not yet wired

`pub_sub/nats_pub_sub.py` is a skeleton (the NATS connection is left for
integration). A safety-relay service, sensors / bounding-box collision checks,
trajectory blending, and Hydra/OmegaConf config are noted as future work in
[Architecture.md](Architecture.md).
