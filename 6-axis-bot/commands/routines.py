"""Hard-coded pick-and-place routines.

Each routine is a pick pose and a place pose in the user (workpiece) frame, plus
a standoff height used to derive the approach / lift / retract waypoints above
each target so the arm never traverses at part height.

TODO(parameterized-routines): drop this table once the Command schema carries
explicit source/target poses, and take the poses from the command instead.
"""
from __future__ import annotations

from dataclasses import dataclass

from climbing_bot.motion.pose import Pose, Quaternion, Vec3

# Identity orientation (tool pointing straight down is the controller's concern;
# these pre-taught poses just carry whatever orientation was authored).
_DOWN = Quaternion(w=1.0, x=0.0, y=0.0, z=0.0)


@dataclass(frozen=True)
class Routine:
    """A single pick-and-place job: where to grab, where to put it."""

    pick: Pose
    place: Pose
    # Standoff above each target for the approach/lift/retract waypoints, meters.
    approach_height: float = 0.10


def _pose(x: float, y: float, z: float) -> Pose:
    return Pose(position=Vec3(x, y, z), orientation=_DOWN)


# Routine ID -> Routine. Poses are illustrative pre-taught values in meters.
ROUTINES: dict[str, Routine] = {
    "task_a": Routine(pick=_pose(0.40, -0.20, 0.05), place=_pose(0.40, 0.20, 0.05)),
    "task_b": Routine(pick=_pose(0.50, 0.00, 0.05), place=_pose(0.30, 0.30, 0.05)),
    "task_c": Routine(pick=_pose(0.35, 0.15, 0.05), place=_pose(0.55, -0.15, 0.05)),
}
