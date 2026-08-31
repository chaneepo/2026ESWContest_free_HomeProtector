"""Hardware-free tests for the web controller runtime."""

from __future__ import annotations

import unittest

from server import ControllerRuntime


class ControllerRuntimeTests(unittest.TestCase):
    def test_demo_move_records_command_without_hardware(self) -> None:
        runtime = ControllerRuntime(hardware=False)

        state = runtime.move("forward", 40, 0.2)

        self.assertEqual(state["last_action"], "forward")
        self.assertEqual(state["command_count"], 1)
        self.assertFalse(state["hardware_enabled"])

    def test_demo_sensors_are_available(self) -> None:
        sensors = ControllerRuntime(hardware=False).sensors()

        self.assertEqual(len(sensors["line"]), 4)
        self.assertGreater(sensors["distance_cm"], 0)

    def test_server_limits_are_enforced(self) -> None:
        runtime = ControllerRuntime(hardware=False)

        with self.assertRaises(ValueError):
            runtime.move("forward", 81, 0.2)
        with self.assertRaises(ValueError):
            runtime.move("forward", 40, 0.6)

    def test_sensor_only_mode_reads_hardware_but_locks_motion(self) -> None:
        runtime = ControllerRuntime(sensors_only=True)

        self.assertTrue(runtime.snapshot()["sensors_enabled"])
        self.assertFalse(runtime.snapshot()["movement_enabled"])
        with self.assertRaises(PermissionError):
            runtime.move("forward", 40, 0.2)
        with self.assertRaises(PermissionError):
            runtime.turn("left", 45, 40)

    def test_direct_turn_angle_is_recorded_in_demo_mode(self) -> None:
        runtime = ControllerRuntime(hardware=False)

        state = runtime.turn("left", 37, 40)

        self.assertEqual(state["last_action"], "turn_left")
        self.assertEqual(state["last_angle"], 37)
        self.assertAlmostEqual(state["last_duration"], 37 / 90, places=3)

    def test_turn_angle_range_is_enforced(self) -> None:
        runtime = ControllerRuntime(hardware=False)

        with self.assertRaises(ValueError):
            runtime.turn("right", 0, 40)
        with self.assertRaises(ValueError):
            runtime.turn("right", 181, 40)


if __name__ == "__main__":
    unittest.main()
