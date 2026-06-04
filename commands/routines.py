"""Hard-coded pick-and-place routines.

TODO(parameterized-routines): replace with routines that accept Pose arguments
once Command schema carries explicit pose data.
"""
from __future__ import annotations

# Routine ID -> placeholder description.
# Real impl will hold sequences of waypoints / gripper actions.
ROUTINES: dict[str, str] = {
    "task_a": "TODO: define task A waypoints",
    "task_b": "TODO: define task B waypoints",
    "task_c": "TODO: define task C waypoints",
}
