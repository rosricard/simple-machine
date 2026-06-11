"""The pick-and-place phase sequence.

Kept as a plain async function (not a python-statemachine machine): the sequence
is strictly linear, so a transition graph would be more ceremony than the
(phase, action) table below. The high-level RobotMachine calls this while it is
in the `running` state.
"""
from __future__ import annotations

import logging

from climbing_bot.commands.routines import Routine
from climbing_bot.controllers.states import PickPlacePhase
from climbing_bot.interfaces.gripper_repository import GripperRepository
from climbing_bot.interfaces.signal_repository import SignalRepository
from climbing_bot.motion.pose import Pose, Vec3

log = logging.getLogger(__name__)


def standoff(pose: Pose, height: float) -> Pose:
    """Pose directly above `pose` by `height` meters (same orientation)."""
    p = pose.position
    return Pose(position=Vec3(p.x, p.y, p.z + height), orientation=pose.orientation)


async def run_pick_place(
    signal_repo: SignalRepository,
    gripper: GripperRepository,
    routine: Routine,
) -> None:
    """Walk a single pick-and-place through its PickPlacePhase sequence.

    Approach/lift/retract go to a standoff pose above the target; descend goes to
    the target itself; grasp/release drive the gripper.
    """
    above_pick = standoff(routine.pick, routine.approach_height)
    above_place = standoff(routine.place, routine.approach_height)

    # (phase, action) — actions are thunks so we await them under the phase.
    steps = [
        (PickPlacePhase.APPROACH_PICK, lambda: signal_repo.move_to(above_pick)),
        (PickPlacePhase.DESCEND_PICK, lambda: signal_repo.move_to(routine.pick)),
        (PickPlacePhase.GRASP, gripper.close),
        (PickPlacePhase.LIFT, lambda: signal_repo.move_to(above_pick)),
        (PickPlacePhase.APPROACH_PLACE, lambda: signal_repo.move_to(above_place)),
        (PickPlacePhase.DESCEND_PLACE, lambda: signal_repo.move_to(routine.place)),
        (PickPlacePhase.RELEASE, gripper.open),
        (PickPlacePhase.RETRACT, lambda: signal_repo.move_to(above_place)),
    ]

    for phase, action in steps:
        log.info("routine phase %s", phase.name)
        await action()
