from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandType(Enum):
    PICK_AND_PLACE = "pick_and_place"
    HOME = "home"
    ABORT = "abort"
    STATUS = "status"


@dataclass
class Command:
    id: str
    type: CommandType
    routine_id: str | None = None
    # TODO(parameterized-routines): add source_pose, target_pose, frame fields
    #   once routines accept Pose arguments rather than fixed IDs.
    # TODO(manual-mode): currently shares the same schema as auto. If pendant /
    #   jog commands diverge (continuous velocity input), split into
    #   ManualCommand with its own handler.
