# climbing-bot architecture

This diagram reflects the code as built (`src/`), not the original whiteboard
sketch. Key differences from the sketch are called out in
[Notes](#notes-vs-the-original-sketch) at the bottom.

## System view

```mermaid
flowchart TD
    subgraph ext["External"]
        orch["Orchestration layer"]
    end

    subgraph py["climbing-bot — single asyncio event loop (one thread)"]
        direction TB

        subgraph bc["BotController.run() — event-driven FSM + timed IO"]
            direction LR
            orchloop["orchestration loop<br/><i>await commands (event)</i>"]
            ctrlloop["actuation-event loop<br/><i>BotStateMachine<br/>await edge events (event)</i>"]
            ioloop["IO loop @ 200 Hz<br/><i>tick actuation (timed)</i>"]
        end

        act["ActuationController<br/><i>coordinates the axes;<br/>'reached' only when ALL in position</i>"]

        subgraph dgs["DriveGroups — one FSM per axis"]
            direction LR
            dgx["DriveGroup X"]
            dgy["DriveGroup Y"]
            dgz["DriveGroup Z"]
            dgrz["DriveGroup RZ"]
        end

        repo["SignalRepository (HAL)<br/><i>command(axis,target) / feedback(axis)</i>"]
    end

    subgraph hw["Motor controllers — firmware / RTOS (real-time)"]
        direction LR
        mc["Motor controllers<br/><i>close current/velocity loop locally</i>"]
        motors["Motors + encoders"]
    end

    orch <-->|"NATS<br/>(PubSub Protocol:<br/>recv / publish)"| orchloop
    orchloop -->|"fire FSM events (commands)"| ctrlloop
    ctrlloop -->|events / telemetry| orchloop
    ctrlloop -->|"command_waypoint()"| act
    ioloop -->|"tick()"| act
    act -->|"WAYPOINT_REACHED / FAULTED<br/>(edge events)"| ctrlloop
    act --> dgx & dgy & dgz & dgrz
    dgx & dgy & dgz & dgrz -->|"command / feedback"| repo
    repo <-.->|"CAN / EtherCAT<br/>setpoints down, feedback up"| mc
    mc <--> motors

    classDef rt fill:#fff3cd,stroke:#d39e00;
    classDef boundary fill:#e7f1ff,stroke:#0d6efd;
    class hw,mc,motors rt;
    class repo,orchloop boundary;
```

> The blue boxes are the **swap boundaries**: `PubSub` (in-memory ↔ NATS) and
> `SignalRepository` (mock ↔ real CAN/EtherCAT). Nothing downstream of the
> composition root (`main.py`) changes when these are swapped.
>
> The yellow region is the **real-time boundary**: loop closure runs in motor-
> controller firmware. Python streams setpoints and reads feedback — it does not
> close the servo loop.

## Bot state machine (event-driven)

```mermaid
stateDiagram-v2
    [*] --> booting
    booting --> idle: boot_complete
    idle --> homing: home
    homing --> ready: homed
    ready --> homing: home
    ready --> executing: start
    executing --> holding: arrived
    holding --> executing: advance
    holding --> completing: finish
    completing --> ready: completed

    note right of holding
        stopped at a waypoint;
        loops per waypoint
    end note

    state "abort → idle" as aborting
    note left of aborting
        abort: any active state → aborting → idle
        fault: any state → faulted (reset → idle)
        estop: any state → estopped (reset → idle)
    end note
```

## Drive group state machine (per axis)

```mermaid
stateDiagram-v2
    [*] --> disabled
    disabled --> idle: enable
    idle --> moving: start_move
    moving --> in_position: reached
    in_position --> moving: start_move (re-command)
    moving --> idle: halt
    in_position --> idle: halt
    idle --> disabled: disable
    in_position --> disabled: disable

    disabled --> faulted: fault
    idle --> faulted: fault
    moving --> faulted: fault
    in_position --> faulted: fault
    faulted --> disabled: reset
```

## Notes vs. the original sketch

- **No 2D-array event queue.** The transport is a `PubSub` Protocol
  (`recv`/`publish`), swapped between `InMemoryPubSub` and NATS at the
  composition root — not a queue data structure inside the controller.
- **"Top Level Task" and "Bot State machine" are one component.**
  `BotController` owns `BotStateMachine`. The bot FSM is **event-driven**: it
  reacts to commands (orchestration loop) and to actuation edge events
  (actuation-event loop), never polling. The only timed loop is IO (200 Hz),
  which samples hardware so the drive-group FSMs can transition. All run
  cooperatively in one asyncio loop — no shared-state locking.
- **Naming reconciled.** The sketch's "Drive Group" coordinator is the code's
  `ActuationController`; the sketch's per-axis "Motor Controller" is the code's
  `DriveGroup`. This diagram uses the code's names.
- **HAL boundary made explicit.** `SignalRepository` is the CAN/EtherCAT swap
  point; the real-time servo loop lives below it in motor-controller firmware.
- **Safety paths shown.** abort / fault / estop are reachable from active
  states; a latched fault unwinds all three loops via `FaultExit`.
