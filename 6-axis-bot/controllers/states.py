from enum import Enum, auto


# NOTE: the high-level IDLE/HOMING/RUNNING/ABORTING/ERROR lifecycle is defined by
# `controllers.robot_machine.RobotMachine` (python-statemachine). The phase enum
# below stays a plain Enum — its sequence is linear and walked in
# `controllers.pick_place`, so it needs no transition graph.


class PickPlacePhase(Enum):
    """Sub-states of a single pick-and-place routine while the machine is RUNNING.

    Conventional point-to-point sequence: approach the pick pose from above,
    descend, close the gripper, lift clear, traverse to the place pose, descend,
    release, then retract. Approach/lift use a safe standoff height above the
    target so the arm never traverses at part height.
    """

    APPROACH_PICK = auto()
    DESCEND_PICK = auto()
    GRASP = auto()
    LIFT = auto()
    APPROACH_PLACE = auto()
    DESCEND_PLACE = auto()
    RELEASE = auto()
    RETRACT = auto()
