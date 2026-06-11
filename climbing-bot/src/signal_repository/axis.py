"""Axis feedback type shared by the signal repository and the actuation layer."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisFeedback:
    """A single axis's sensed state, as read from the fieldbus.

    position / velocity are in axis units (mm for linear, rad for RZ). `moving`
    is the drive's own in-motion flag — the actuation layer also cross-checks
    position against the commanded target before declaring "in position".
    """

    position: float
    velocity: float
    moving: bool
