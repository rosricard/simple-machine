"""Pose / frame primitives.

Minimal because we assume the vendor controller handles IK and trajectory
generation.

TODO(custom-arm): add motion/kinematics.py with FK / IK / Jacobian for the
case where we drive a custom arm at the joint level.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vec3:
    """Location of something in 3D space, in meters. No orientation information."""
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Quaternion:
    """Encodes how something is rotated in space. We use quaternions to avoid gimbal lock and singularities."""

    w: float
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Pose:
    position: Vec3
    orientation: Quaternion


@dataclass(frozen=True)
class Frame:
    """Named transform. Examples: 'base', 'user', 'tool'.

    TCP offset lives in the tool frame.
    """
    name: str
    transform: Pose
