"""The high-level bot state machine (the README's "bot fsm").

A python-statemachine over the bot lifecycle. Side effects hang off `on_enter_*`
hooks and drive the ActuationController; the orchestration / control loops in
`bot_controller.py` fire the events. Synchronous — the loops calling it own the
event loop.

This is a representative subset of the ~16-state production machine, focused on
the path that matters for this sample: receive a trajectory from orchestration
and stop at each waypoint in turn.

    booting → idle → homing → ready → executing ⇄ holding → completing → ready
                                                                  (loops per waypoint)

Cross-cutting: any active state can `abort` (→ idle), `fault` (→ faulted), or
`estop` (→ estopped). `reset` recovers from faulted / estopped.
"""
from __future__ import annotations

import logging

from statemachine import State, StateMachine

from actuation.actuation_controller import ActuationController
from controller.trajectory_manager import TrajectoryManager

log = logging.getLogger(__name__)


class BotStateMachine(StateMachine):
    booting = State(initial=True, value="booting")
    idle = State(value="idle")
    homing = State(value="homing")
    ready = State(value="ready")
    executing = State(value="executing")
    holding = State(value="holding")          # stopped at a waypoint
    completing = State(value="completing")
    aborting = State(value="aborting")
    faulted = State(value="faulted")
    estopped = State(value="estopped")

    boot_complete = booting.to(idle)
    home = idle.to(homing) | ready.to(homing)
    homed = homing.to(ready)
    # Motion requires a homed (enabled) bot, so start is only legal from ready.
    start = ready.to(executing)
    arrived = executing.to(holding)
    advance = holding.to(executing)
    finish = holding.to(completing)
    completed = completing.to(ready)

    abort = (
        homing.to(aborting)
        | executing.to(aborting)
        | holding.to(aborting)
        | completing.to(aborting)
    )
    aborted = aborting.to(idle)

    fault = (
        idle.to(faulted)
        | homing.to(faulted)
        | ready.to(faulted)
        | executing.to(faulted)
        | holding.to(faulted)
        | completing.to(faulted)
        | aborting.to(faulted)
    )
    reset = faulted.to(idle) | estopped.to(idle)

    estop = (
        idle.to(estopped)
        | homing.to(estopped)
        | ready.to(estopped)
        | executing.to(estopped)
        | holding.to(estopped)
        | completing.to(estopped)
        | aborting.to(estopped)
        | faulted.to(estopped)
    )

    def __init__(self, actuation: ActuationController, trajectory: TrajectoryManager) -> None:
        self._actuation = actuation
        self._trajectory = trajectory
        # Every transition is recorded here (sync); the controller drains and
        # publishes StateChanged events asynchronously. Keeps the machine free of
        # async I/O while still emitting per-transition telemetry.
        self.transition_log: list[tuple[str, str]] = []
        super().__init__()

    def after_transition(self, source: State, target: State) -> None:
        self.transition_log.append((source.id, target.id))

    # -- side effects on state entry --

    def on_enter_homing(self) -> None:
        # Homing in this sample is just energizing the axes; a real bot would
        # drive each axis to its reference switch and wait for completion.
        self._actuation.enable()

    def on_enter_executing(self) -> None:
        self._actuation.command_waypoint(self._trajectory.current())

    def on_enter_aborting(self) -> None:
        self._actuation.abort()

    def on_enter_faulted(self) -> None:
        self._actuation.abort()
