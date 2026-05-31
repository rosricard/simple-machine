#publish the state and diagnostics to protocol of choice. Maybe TCP
from abc import ABC
from dataclasses import dataclass
from time import time

@dataclass
class MotionControllerSafetyCommand(ABC):
  """interface for external controller communication"""
  # contract between us and motion controller
  StopRequest : bool
  TimeRemainingToStop : int #todo: look up the python time type

  