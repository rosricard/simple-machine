"""In-memory SignalRepository for local runs / SIL tests.

Each axis integrates toward its setpoint in real time, sampled on `feedback()`
the same way `EncoderVendor1` samples its waveform off `time.monotonic()`. No
fieldbus, no hardware — but the actuation layer drives it through the exact same
`SignalRepository` interface it uses for the real bus, so controller logic is
exercised unchanged.
"""
from __future__ import annotations

import time

from interfaces.enums import Axis
from signal_repository.axis import AxisFeedback
from signal_repository.signal_repository import SignalRepository

# Per-axis max speed (mm/s for linear, rad/s for RZ). Generous so sample
# trajectories converge quickly.
_DEFAULT_MAX_SPEED: dict[Axis, float] = {
    Axis.X: 500.0,
    Axis.Y: 500.0,
    Axis.Z: 300.0,
    Axis.RZ: 6.28,
}


class _MockAxis:
    """First-order motion model: position ramps toward target at max_speed."""

    def __init__(self, max_speed: float) -> None:
        self._max_speed = max_speed
        self._position = 0.0
        self._target = 0.0
        self._velocity = 0.0
        self._enabled = False
        self._last = time.monotonic()

    def set_target(self, target: float) -> None:
        # Reset the clock so the first sample after a new command doesn't take a
        # giant integration step from accumulated idle time.
        self._integrate()
        self._target = target

    def set_enabled(self, enabled: bool) -> None:
        self._integrate()
        self._enabled = enabled

    def _integrate(self) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        if not self._enabled or dt <= 0:
            self._velocity = 0.0
            return
        remaining = self._target - self._position
        max_step = self._max_speed * dt
        if abs(remaining) <= max_step:
            self._position = self._target
            self._velocity = 0.0
        else:
            direction = 1.0 if remaining > 0 else -1.0
            self._position += direction * max_step
            self._velocity = direction * self._max_speed

    def feedback(self) -> AxisFeedback:
        self._integrate()
        moving = self._position != self._target
        return AxisFeedback(position=self._position, velocity=self._velocity, moving=moving)


class MockSignalRepository(SignalRepository):
    def __init__(self, max_speed: dict[Axis, float] | None = None) -> None:
        speeds = max_speed or _DEFAULT_MAX_SPEED
        self._axes: dict[Axis, _MockAxis] = {
            axis: _MockAxis(speeds[axis]) for axis in Axis
        }

    def enable(self) -> None:
        for axis in self._axes.values():
            axis.set_enabled(True)

    def disable(self) -> None:
        for axis in self._axes.values():
            axis.set_enabled(False)

    def command(self, axis: Axis, target: float) -> None:
        self._axes[axis].set_target(target)

    def feedback(self, axis: Axis) -> AxisFeedback:
        return self._axes[axis].feedback()
