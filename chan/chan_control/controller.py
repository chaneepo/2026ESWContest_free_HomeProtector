"""Safety-oriented wrapper around the installed ``raspbot`` package."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from raspbot import Robot as _RaspbotRobot
except ModuleNotFoundError:  # The Mac development environment has no robot driver.
    _RaspbotRobot = None


class Motion(str, Enum):
    """Movements exposed by the Raspbot V2 mecanum drive."""

    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    STRAFE_LEFT = "strafe_left"
    STRAFE_RIGHT = "strafe_right"
    DIAGONAL_FORWARD_LEFT = "diagonal_forward_left"
    DIAGONAL_FORWARD_RIGHT = "diagonal_forward_right"
    DIAGONAL_BACKWARD_LEFT = "diagonal_backward_left"
    DIAGONAL_BACKWARD_RIGHT = "diagonal_backward_right"


@dataclass(frozen=True)
class SafetyLimits:
    """Conservative limits for first bench tests."""

    max_speed: int = 80
    max_duration: float = 1.0


class RaspbotController:
    """Own a Raspbot connection and guarantee a stop after pulse movement."""

    def __init__(
        self,
        limits: SafetyLimits | None = None,
        *,
        robot_factory: Callable[[], Any] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.limits = limits or SafetyLimits()
        self._robot_factory = robot_factory
        self._sleep = sleep_fn
        self._robot: Any | None = None

    def connect(self) -> None:
        """Open the configured I2C bus once."""
        if self._robot is None:
            robot_factory = self._robot_factory or _RaspbotRobot
            if robot_factory is None:
                raise RuntimeError(
                    "The raspbot driver is unavailable. Use demo mode on this computer "
                    "or run hardware mode on the Raspberry Pi."
                )
            self._robot = robot_factory()

    @property
    def robot(self) -> Any:
        if self._robot is None:
            raise RuntimeError("Raspbot is not connected. Call connect() first.")
        return self._robot

    def pulse(self, motion: Motion | str, *, speed: int, duration: float) -> None:
        """Run one movement briefly and always stop afterward.

        This method intentionally does not support continuous movement. Higher-level
        navigation should call short pulses while repeatedly checking sensors.
        """
        motion = Motion(motion)
        speed = int(speed)
        duration = float(duration)

        if not 1 <= speed <= self.limits.max_speed:
            raise ValueError(f"speed must be between 1 and {self.limits.max_speed}")
        if not 0.0 < duration <= self.limits.max_duration:
            raise ValueError(
                f"duration must be greater than 0 and at most {self.limits.max_duration}"
            )

        self.connect()
        move = getattr(self.robot.motors, motion.value)
        try:
            move(speed=speed)
            self._sleep(duration)
        finally:
            self.robot.motors.stop()

    def stop(self) -> None:
        """Stop all four motors if a connection is open."""
        if self._robot is not None:
            self._robot.motors.stop()

    def read_line(self) -> Any:
        """Read the four-channel line tracker."""
        self.connect()
        return self.robot.line_tracker.read()

    def read_distance_cm(self) -> float:
        """Read ultrasonic distance and disable the sensor afterward."""
        self.connect()
        try:
            return float(self.robot.ultrasonic.read_cm())
        finally:
            self.robot.ultrasonic.disable()

    def close(self) -> None:
        """Stop actuators and release the I2C bus."""
        if self._robot is not None:
            self._robot.close()
            self._robot = None

    def __enter__(self) -> RaspbotController:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
