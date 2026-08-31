"""Hardware-free tests for the safety wrapper."""

from __future__ import annotations

import unittest

from chan_control import Motion, RaspbotController


class FakeMotors:
    def __init__(self) -> None:
        self.events: list[tuple[str, int | None]] = []

    def forward(self, *, speed: int) -> None:
        self.events.append(("forward", speed))

    def stop(self) -> None:
        self.events.append(("stop", None))


class FakeUltrasonic:
    def read_cm(self) -> float:
        return 42.5

    def disable(self) -> None:
        pass


class FakeLineTracker:
    def read(self) -> str:
        return "line"


class FakeRobot:
    def __init__(self) -> None:
        self.motors = FakeMotors()
        self.ultrasonic = FakeUltrasonic()
        self.line_tracker = FakeLineTracker()

    def close(self) -> None:
        self.motors.stop()


class ControllerTests(unittest.TestCase):
    def test_pulse_always_stops(self) -> None:
        robot = FakeRobot()
        controller = RaspbotController(
            robot_factory=lambda: robot,
            sleep_fn=lambda _: None,
        )

        controller.pulse(Motion.FORWARD, speed=40, duration=0.2)

        self.assertEqual(robot.motors.events, [("forward", 40), ("stop", None)])

    def test_speed_limit_rejects_motion_before_connect(self) -> None:
        controller = RaspbotController(robot_factory=FakeRobot)

        with self.assertRaises(ValueError):
            controller.pulse(Motion.FORWARD, speed=81, duration=0.2)

    def test_duration_limit_rejects_motion_before_connect(self) -> None:
        controller = RaspbotController(robot_factory=FakeRobot)

        with self.assertRaises(ValueError):
            controller.pulse(Motion.FORWARD, speed=40, duration=1.1)


if __name__ == "__main__":
    unittest.main()
