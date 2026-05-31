from enum import Enum, auto


class SystemState(Enum):
    IDLE = auto()
    HOMING = auto()
    RUNNING = auto()
    ABORTING = auto()
    ERROR = auto()
