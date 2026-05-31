from abc import ABC, abstractmethod
from dataclasses import dataclass
import time
import math

class I_Encoder(ABC):
    """Beckhoff-style interface: signatures only, no implementation."""

    @property
    # @abstractmethod
    def position(self) -> int: ...

    @property
    # @abstractmethod
    def velocity(self) -> int: ...

    # @abstractmethod
    def read(self) -> bool:
        ...

class EncoderVendor1(I_Encoder):
    """Mock vendor encoder. Each read() samples a sinusoid driven by elapsed
    time, so the position 'moves' like a shaft turning back and forth."""

    def __init__(self, amplitude: int = 1000, frequency_hz: float = 0.5):
        self._amplitude = amplitude          # peak counts either side of zero
        self._frequency = frequency_hz       # cycles per second
        self._position = 0
        self._velocity = 0
        self._start = time.monotonic()        # t0 for the waveform

    @property  # read-only; no setter so external assignment raises
    def position(self) -> int:
        return self._position

    @property
    def velocity(self) -> int:
        return self._velocity

    def read(self) -> bool:
        """Sample the 'hardware': update position (sine) and velocity (its
        derivative, cosine). Returns True if the sample is valid."""
        t = time.monotonic() - self._start
        omega = 2 * math.pi * self._frequency

        # position = A * sin(wt)   ->   velocity = A * w * cos(wt)
        self._position = round(self._amplitude * math.sin(omega * t))
        self._velocity = round(self._amplitude * omega * math.cos(omega * t))
        return True


# class I_RangeSensor(ABC):
#   """Vendor Agnostic Range Sensor interface"""

#   @property
#   @abstractmethod
#   def distance(self) -> int: # simplification, this would actually need some wire format / serialization handling for the sizes to properly match
#   #normally this would be over some protocol like CAN, EtherCAT, IO link,etc 
