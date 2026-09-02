"""Hardware-free tests for the web controller runtime."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from http.server import ThreadingHTTPServer

from server import ControllerRuntime, IPv6ThreadingHTTPServer, server_class_for


class ControllerRuntimeTests(unittest.TestCase):
    class FakeController:
        def __init__(self) -> None:
            self.stop_calls = 0

        def stop(self) -> None:
            self.stop_calls += 1

        def connect(self):
            pass

        def read_line(self):
            return SimpleNamespace(x1=False, x2=True, x3=True, x4=False, raw=6)

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

    def test_ipv6_host_selects_ipv6_server(self) -> None:
        self.assertIs(server_class_for("::"), IPv6ThreadingHTTPServer)
        self.assertIs(server_class_for("2001:db8::1"), IPv6ThreadingHTTPServer)
        self.assertIs(server_class_for("0.0.0.0"), ThreadingHTTPServer)

    def test_hardware_mode_requires_explicit_safety_confirmation(self) -> None:
        runtime = ControllerRuntime(sensors_only=True)
        runtime._controller = self.FakeController()  # type: ignore[assignment]

        with self.assertRaises(PermissionError):
            runtime.set_mode("hardware")

        self.assertFalse(runtime.snapshot()["movement_enabled"])

    def test_mode_switch_stops_before_changing_movement_permission(self) -> None:
        controller = self.FakeController()
        runtime = ControllerRuntime(controller_factory=lambda: controller)

        hardware = runtime.set_mode("hardware", confirm_safe=True)
        safe = runtime.set_mode("safe")

        self.assertTrue(hardware["movement_enabled"])
        self.assertFalse(safe["movement_enabled"])
        self.assertEqual(safe["mode"], "sensors")
        self.assertEqual(controller.stop_calls, 2)


if __name__ == "__main__":
    unittest.main()
