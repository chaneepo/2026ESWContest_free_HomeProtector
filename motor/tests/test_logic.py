import sys
import queue
import threading
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from carepack_so101_profiled_studio import (
    JointSpec,
    MotionProfile,
    PulseBus,
    ProfiledStudio,
    apply_axis_motion_limits,
    clamp_to_ranges,
    estimated_move_seconds,
    expand_ranges_to_include,
    gripper_safe_calibration,
    in_allowed_ranges,
    intersect_ranges,
    limit_teleop_targets,
    map_relative_teleop_targets,
    continuous_lift_target,
    load_config,
    load_joint_specs,
    prepare_selected_motion,
    range_branch,
    scaled_speeds,
    select_teleop_targets,
    segmented_axis_waypoints,
    validate_current_positions,
    validate_range_pair,
    validate_sequence_steps,
    validate_tuning_values,
    unwrap_raw_position,
)


class FakePulseBus:
    def __init__(self, positions):
        self.positions = list(positions)
        self.last_position = self.positions[-1]
        self.name = "joint"
        self.commands = []
        self.disabled = False

    def command_profiled(self, targets, speeds, accelerations):
        self.commands.append((targets, speeds, accelerations))

    def read_telemetry(self):
        if self.positions:
            self.last_position = self.positions.pop(0)
        return {
            self.name: {
                "Present_Position": self.last_position,
                "Present_Velocity": 0,
                "Present_Voltage": 122,
                "Present_Temperature": 35,
                "Present_Load": 0,
                "Present_Current": 0,
                "Moving": 0,
            }
        }

    def hold_current_position(self):
        return {self.name: self.last_position}

    def disable_torque(self):
        self.disabled = True


class FakeRegisterBus:
    def __init__(self):
        self.values = {}

    def write(self, register, name, value, normalize=False):
        if register != "Lock":
            if register == "Homing_Offset" and (name, register) in self.values:
                old_offset = self.values[(name, register)]
                old_position = self.values[(name, "Present_Position")]
                self.values[(name, "Present_Position")] = (
                    old_position + int(value) - old_offset
                ) % 4096
            self.values[(name, register)] = int(value)

    def read(self, register, name, normalize=False):
        return self.values[(name, register)]

    def set_half_turn_homings(self, motors):
        result = {}
        for name in motors:
            old_offset = self.values[(name, "Homing_Offset")]
            current = self.values[(name, "Present_Position")]
            new_offset = old_offset + 2048 - current
            result[name] = new_offset
        return result


def make_motion_studio(
    fake_bus,
    *,
    stall_seconds=1.0,
    correction_timeout=0.01,
    joint_name="joint",
    motor_id=1,
    continuous_lift=False,
):
    studio = ProfiledStudio.__new__(ProfiledStudio)
    studio.pulse_bus = fake_bus
    fake_bus.name = joint_name
    studio.motion_stop = threading.Event()
    studio.events = queue.Queue()
    spec = JointSpec(joint_name, "시험축", motor_id, 100, ((0, 4095),), 1000)
    studio.specs = [spec]
    studio.by_name = {joint_name: spec}
    studio.config = {
        "safety": {
            "minimum_voltage_raw": 105,
            "maximum_temperature_c": 65,
            "completion_tolerance_pulse": 15,
            "motion_poll_seconds": 0.0,
            "completion_stable_samples": 2,
            "progress_epsilon_pulse": 2,
            "stall_seconds": stall_seconds,
            "hard_timeout_seconds": 1.0,
            "correction_timeout_seconds": correction_timeout,
            "correction_speed": 60,
            "correction_acceleration": 1,
            "telemetry_filter_samples": 3,
        },
        "continuous_lift": {
            "enabled": continuous_lift,
            "lifting_delta_sign": {
                "shoulder_lift": -1,
                "elbow_flex": -1,
            },
            "minimum_move_pulse": 20,
            "lead_pulse": 18,
            "handoff_remaining_pulse": 8,
        },
    }
    return studio


class LogicTests(unittest.TestCase):
    def test_teleop_relative_mapping_clamps_to_follower_ranges(self):
        targets = map_relative_teleop_targets(
            {"a": 1300, "b": 900},
            {"a": 1000, "b": 1000},
            {"a": 1500, "b": 1500},
            {"a": 1, "b": -1},
            0.5,
            {"a": ((1000, 1600),), "b": ((1000, 1600),)},
            {"a", "b"},
        )
        self.assertEqual(targets, {"a": 1600, "b": 1550})

    def test_teleop_disabled_axis_holds_start_pose(self):
        targets = map_relative_teleop_targets(
            {"a": 1300, "b": 1300},
            {"a": 1000, "b": 1000},
            {"a": 1500, "b": 1500},
            {"a": 1, "b": 1},
            1.0,
            {"a": ((0, 4095),), "b": ((0, 4095),)},
            {"a"},
        )
        self.assertEqual(targets, {"a": 1800, "b": 1500})

    def test_teleop_command_is_step_and_lead_limited(self):
        targets = limit_teleop_targets(
            {"a": 2000},
            {"a": 1500},
            {"a": 1490},
            {"a": 12},
            {"a": 18},
            {"a": ((1000, 2200),)},
        )
        self.assertEqual(targets, {"a": 1508})

    def test_direct_teleop_bypasses_step_and_lead_limits(self):
        targets = select_teleop_targets(
            True,
            {"a": 2000},
            {"a": 1500},
            {"a": 1490},
            {"a": 12},
            {"a": 18},
            {"a": ((1000, 2200),)},
        )
        self.assertEqual(targets, {"a": 2000})

    def test_safe_teleop_keeps_step_and_lead_limits(self):
        targets = select_teleop_targets(
            False,
            {"a": 2000},
            {"a": 1500},
            {"a": 1490},
            {"a": 12},
            {"a": 18},
            {"a": ((1000, 2200),)},
        )
        self.assertEqual(targets, {"a": 1508})

    def test_teleop_unwrap_avoids_false_full_turn(self):
        self.assertEqual(unwrap_raw_position(4090, 4090, 5), 4101)
        self.assertEqual(unwrap_raw_position(5, 5, 4090), -6)

    def test_effective_range_intersects_motor_eeprom_limits(self):
        self.assertEqual(intersect_ranges(((742, 3439),), 1520, 3426), ((1520, 3426),))
        self.assertEqual(clamp_to_ranges(1400, ((1520, 3426),)), 1520)

    def test_teleop_config_covers_all_six_axes(self):
        config = load_config()
        names = {spec.name for spec in load_joint_specs(config)}
        settings = config["teleoperation"]
        self.assertEqual(set(settings["directions"]), names)
        self.assertEqual(set(settings["max_step_pulse"]), names)
        self.assertEqual(set(settings["max_command_lead_pulse"]), names)
        self.assertEqual(settings["leader_port"], "COM4")
        self.assertEqual(settings["default_mode"], "direct")
        self.assertEqual(settings["direct"]["scale"], 1.0)
        self.assertEqual(set(settings["direct"]["speeds"]), names)
        self.assertTrue(
            all(value == 0 for value in settings["direct"]["speeds"].values())
        )

    def test_editable_range_pair_validation(self):
        self.assertEqual(validate_range_pair("742", "3439"), (742, 3439))
        with self.assertRaises(ValueError):
            validate_range_pair(2000, 1000)
        with self.assertRaises(ValueError):
            validate_range_pair(-1, 1000)
        with self.assertRaises(ValueError):
            validate_range_pair(0, 4096)

    def test_sequence_validation_normalizes_fixed_pose_steps(self):
        specs = [
            JointSpec("a", "A", 1, 100, ((0, 200),), 1000),
            JointSpec("b", "B", 2, 100, ((50, 250),), 1000),
        ]
        steps = validate_sequence_steps(
            {
                "format": "carepack-so101-motion-sequence-v1",
                "steps": [
                    {
                        "name": "접근",
                        "targets": {"a": "120", "b": 180},
                        "selected": ["a", "b"],
                        "wait_seconds": "0.5",
                    }
                ],
            },
            specs,
            {"a": ((0, 200),), "b": ((50, 250),)},
        )
        self.assertEqual(steps[0]["targets"], {"a": 120, "b": 180})
        self.assertEqual(steps[0]["wait_seconds"], 0.5)

    def test_sequence_validation_rejects_out_of_range_target(self):
        specs = [JointSpec("a", "A", 1, 100, ((0, 200),), 1000)]
        with self.assertRaises(ValueError):
            validate_sequence_steps(
                {
                    "format": "carepack-so101-motion-sequence-v1",
                    "steps": [
                        {
                            "name": "위험 목표",
                            "targets": {"a": 999},
                            "selected": ["a"],
                            "wait_seconds": 0,
                        }
                    ],
                },
                specs,
                {"a": ((0, 200),)},
            )

    def test_six_motors(self):
        specs = load_joint_specs(load_config())
        self.assertEqual([spec.motor_id for spec in specs], [1, 2, 3, 4, 5, 6])

    def test_default_ranges_are_full_raw_domain(self):
        specs = {spec.name: spec for spec in load_joint_specs(load_config())}
        for spec in specs.values():
            self.assertEqual(spec.allowed_ranges, ((0, 4095),))
            self.assertTrue(in_allowed_ranges(0, spec.allowed_ranges))
            self.assertTrue(in_allowed_ranges(4095, spec.allowed_ranges))

    def test_wrist_homing_uses_continuous_range(self):
        settings = load_config()["wrist_homing"]
        self.assertEqual(settings["continuous_ranges"], [[0, 4095]])
        self.assertEqual(settings["expected_center_raw"], 2048)

    def test_wrist_ui_range_is_continuous_even_before_homing(self):
        studio = ProfiledStudio.__new__(ProfiledStudio)
        studio.wrist_homing_settings = load_config()["wrist_homing"]
        studio.wrist_homing_applied = False
        self.assertEqual(studio._wrist_ranges(), ((0, 4095),))

    def test_outside_start_pose_can_be_temporarily_included_without_jump(self):
        self.assertEqual(expand_ranges_to_include(((1000, 2000),), 2500), ((1000, 2500),))
        self.assertEqual(expand_ranges_to_include(((1000, 2000),), 1500), ((1000, 2000),))

    def test_default_gripper_uses_measured_endpoints_without_margin(self):
        config = load_config()
        settings = config["gripper"]
        calibration = gripper_safe_calibration(
            settings["default_open_raw"],
            settings["default_closed_raw"],
            settings["endpoint_margin_pulse"],
            settings["maximum_calibration_span"],
        )
        self.assertEqual(calibration.open_safe, 2243)
        self.assertEqual(calibration.closed_safe, 816)
        self.assertEqual((calibration.minimum, calibration.maximum), (816, 2243))

    def test_wrist_branches(self):
        ranges = ((0, 750), (1350, 4095))
        self.assertEqual(range_branch(500, ranges), 0)
        self.assertEqual(range_branch(3000, ranges), 1)
        self.assertIsNone(range_branch(1000, ranges))

    def test_gripper_calibration_both_directions(self):
        increasing = gripper_safe_calibration(1000, 1600, 20, 2000)
        self.assertEqual((increasing.open_safe, increasing.closed_safe), (1020, 1580))
        decreasing = gripper_safe_calibration(1600, 1000, 20, 2000)
        self.assertEqual((decreasing.open_safe, decreasing.closed_safe), (1580, 1020))

    def test_reject_wrapped_gripper(self):
        with self.assertRaises(ValueError):
            gripper_safe_calibration(3800, 200, 20, 2000)

    def test_scaled_speeds(self):
        values = scaled_speeds({"a": 1000, "b": 500, "c": 0}, 200)
        self.assertEqual(values, {"a": 200, "b": 100})

    def test_axis_motion_limits_slow_elbow_and_speed_wrist(self):
        speeds, accelerations = apply_axis_motion_limits(
            {"elbow_flex": 220, "wrist_roll": 120},
            {"elbow_flex": 4, "wrist_roll": 2},
            load_config()["axis_motion"],
        )
        self.assertEqual(speeds["elbow_flex"], 120)
        self.assertEqual(accelerations["elbow_flex"], 2)
        self.assertEqual(speeds["wrist_roll"], 180)

    def test_elbow_positive_move_is_segmented(self):
        settings = load_config()["axis_motion"]["elbow_flex"]
        points = segmented_axis_waypoints(825, 2950, settings)
        self.assertGreater(len(points), 1)
        self.assertEqual(points[-1], 2950)
        self.assertTrue(all(b - a <= 400 for a, b in zip([825] + points, points)))

    def test_elbow_lift_direction_keeps_continuous_profile(self):
        settings = load_config()["axis_motion"]["elbow_flex"]
        self.assertEqual(segmented_axis_waypoints(2500, 1500, settings), [1500])

    def test_segmented_elbow_worker_hands_off_all_waypoints(self):
        fake = FakePulseBus([900, 1025, 1040, 1150, 1240, 1250, 1250])
        studio = make_motion_studio(
            fake, joint_name="elbow_flex", motor_id=3, stall_seconds=1.0
        )
        studio.config["axis_motion"] = {
            "elbow_flex": {
                "speed_multiplier": 0.7,
                "maximum_speed": 120,
                "maximum_acceleration": 2,
                "segment_limit_pulse": 400,
                "segment_direction_sign": 1,
                "segment_handoff_pulse": 15,
            }
        }
        studio._motion_worker(
            {"elbow_flex": 825},
            {"elbow_flex": 1250},
            ["elbow_flex"],
            MotionProfile(220, 4, 70, 1),
        )
        commanded_targets = [command[0]["elbow_flex"] for command in fake.commands]
        self.assertEqual(commanded_targets[-1], 1250)
        self.assertGreaterEqual(len(commanded_targets), 2)
        kinds = []
        while not studio.events.empty():
            kinds.append(studio.events.get_nowait()[0])
        self.assertIn("motion_done", kinds)
        self.assertFalse(fake.disabled)

    def test_time_estimate(self):
        self.assertGreater(estimated_move_seconds(1000, 120, 2), 0)
        self.assertEqual(estimated_move_seconds(0, 120, 2), 0)

    def test_continuous_lift_adds_safe_lead(self):
        common = {
            "name": "shoulder_lift",
            "start": 100,
            "target": 40,
            "ranges": ((0, 4095),),
            "lifting_delta_signs": {"shoulder_lift": -1},
            "minimum_move": 20,
            "lead": 18,
        }
        self.assertEqual(continuous_lift_target(**common), 22)

    def test_continuous_lift_rejects_gravity_aided_direction(self):
        self.assertIsNone(
            continuous_lift_target(
                name="shoulder_lift",
                start=40,
                target=100,
                ranges=((0, 4095),),
                lifting_delta_signs={"shoulder_lift": -1},
                minimum_move=20,
                lead=18,
            )
        )

    def test_continuous_lift_rejects_unsafe_lead_target(self):
        self.assertIsNone(
            continuous_lift_target(
                name="shoulder_lift",
                start=80,
                target=10,
                ranges=((0, 4095),),
                lifting_delta_signs={"shoulder_lift": -1},
                minimum_move=20,
                lead=18,
            )
        )

    def test_continuous_lift_rejects_tiny_nudge(self):
        self.assertIsNone(
            continuous_lift_target(
                name="shoulder_lift",
                start=50,
                target=40,
                ranges=((0, 4095),),
                lifting_delta_signs={"shoulder_lift": -1},
                minimum_move=20,
                lead=18,
            )
        )

    def test_stage1_tuning_config(self):
        config = load_config()
        self.assertEqual(
            validate_tuning_values(config["loaded_axis_tuning"]["baseline"]),
            {"p": 16, "d": 32, "i": 0, "punch": 16},
        )
        self.assertEqual(
            validate_tuning_values(config["loaded_axis_tuning"]["stage1"]),
            {"p": 20, "d": 36, "i": 0, "punch": 24},
        )
        self.assertEqual(
            validate_tuning_values(config["loaded_axis_tuning"]["stage2"]),
            {"p": 24, "d": 40, "i": 0, "punch": 32},
        )

    def test_tuning_write_and_verify(self):
        pulse_bus = PulseBus.__new__(PulseBus)
        pulse_bus.bus = FakeRegisterBus()
        pulse_bus.lock = threading.RLock()
        pulse_bus.torque_on = False
        target = {"joint": {"p": 20, "d": 36, "i": 0, "punch": 24}}
        self.assertEqual(pulse_bus.write_tuning(target), target)

    def test_tuning_rejects_torque_on(self):
        pulse_bus = PulseBus.__new__(PulseBus)
        pulse_bus.bus = FakeRegisterBus()
        pulse_bus.lock = threading.RLock()
        pulse_bus.torque_on = True
        with self.assertRaises(RuntimeError):
            pulse_bus.write_tuning(
                {"joint": {"p": 20, "d": 36, "i": 0, "punch": 24}}
            )

    def test_half_turn_homing_and_restore(self):
        pulse_bus = PulseBus.__new__(PulseBus)
        pulse_bus.bus = FakeRegisterBus()
        pulse_bus.lock = threading.RLock()
        pulse_bus.torque_on = False
        pulse_bus.bus.values[("wrist_roll", "Present_Position")] = 0
        pulse_bus.bus.values[("wrist_roll", "Homing_Offset")] = 100
        result = pulse_bus.set_half_turn_homing("wrist_roll")
        self.assertEqual(result["before_position"], 0)
        self.assertEqual(result["after_position"], 2048)
        self.assertEqual(result["after_offset"], 2148)
        self.assertEqual(pulse_bus.write_homing_offset("wrist_roll", 100), 100)

    def test_half_turn_homing_rejects_torque_on(self):
        pulse_bus = PulseBus.__new__(PulseBus)
        pulse_bus.bus = FakeRegisterBus()
        pulse_bus.lock = threading.RLock()
        pulse_bus.torque_on = True
        with self.assertRaises(RuntimeError):
            pulse_bus.set_half_turn_homing("wrist_roll")

    def test_half_turn_homing_accepts_arbitrary_current_offset(self):
        pulse_bus = PulseBus.__new__(PulseBus)
        pulse_bus.bus = FakeRegisterBus()
        pulse_bus.lock = threading.RLock()
        pulse_bus.torque_on = False
        pulse_bus.bus.values[("wrist_roll", "Present_Position")] = 2913
        pulse_bus.bus.values[("wrist_roll", "Homing_Offset")] = 454
        result = pulse_bus.set_half_turn_homing("wrist_roll")
        self.assertEqual(result["before_position"], 2913)
        self.assertEqual(result["before_offset"], 454)
        self.assertEqual(result["after_position"], 2048)
        self.assertEqual(result["after_offset"], -411)

    def test_unselected_stale_target_is_forced_to_current(self):
        specs = [
            JointSpec("a", "A", 1, 100, ((0, 200),), 1000),
            JointSpec("b", "B", 2, 100, ((0, 200),), 1000),
        ]
        targets, active = prepare_selected_motion(
            specs,
            {"a": 100, "b": 100},
            {"a": "80", "b": "999"},
            {"a"},
            {"a": ((0, 200),), "b": ((0, 200),)},
        )
        self.assertEqual(targets, {"a": 80, "b": 100})
        self.assertEqual(active, ["a"])

    def test_selected_invalid_target_is_rejected(self):
        specs = [JointSpec("a", "A", 1, 100, ((0, 200),), 1000)]
        with self.assertRaises(ValueError):
            prepare_selected_motion(
                specs,
                {"a": 100},
                {"a": "999"},
                {"a"},
                {"a": ((0, 200),)},
            )

    def test_current_range_validation_has_small_entry_tolerance(self):
        specs = [JointSpec("a", "A", 1, 100, ((100, 200),), 1000)]
        validate_current_positions(specs, {"a": 85}, {"a": ((100, 200),)}, 15)
        with self.assertRaises(ValueError):
            validate_current_positions(specs, {"a": 84}, {"a": ((100, 200),)}, 15)

    def test_progress_motion_completes(self):
        fake = FakePulseBus([90, 82, 80, 80])
        studio = make_motion_studio(fake)
        studio._motion_worker(
            {"joint": 100},
            {"joint": 80},
            ["joint"],
            MotionProfile(120, 2, 70, 1),
        )
        kinds = []
        while not studio.events.empty():
            kinds.append(studio.events.get_nowait()[0])
        self.assertIn("motion_done", kinds)
        self.assertFalse(fake.disabled)

    def test_incomplete_motion_holds_torque(self):
        fake = FakePulseBus([100, 100, 100])
        studio = make_motion_studio(fake, stall_seconds=0.0, correction_timeout=0.0)
        studio._motion_worker(
            {"joint": 100},
            {"joint": 40},
            ["joint"],
            MotionProfile(120, 2, 70, 1),
        )
        kinds = []
        while not studio.events.empty():
            kinds.append(studio.events.get_nowait()[0])
        self.assertIn("motion_incomplete", kinds)
        self.assertEqual(len(fake.commands), 2)
        self.assertFalse(fake.disabled)

    def test_loaded_axis_continuous_lift_completes_without_restart(self):
        fake = FakePulseBus([70, 48, 42, 40])
        studio = make_motion_studio(
            fake,
            joint_name="shoulder_lift",
            motor_id=2,
            continuous_lift=True,
        )
        studio._motion_worker(
            {"shoulder_lift": 100},
            {"shoulder_lift": 40},
            ["shoulder_lift"],
            MotionProfile(120, 2, 70, 1),
        )
        kinds = []
        while not studio.events.empty():
            kinds.append(studio.events.get_nowait()[0])
        self.assertIn("motion_done", kinds)
        self.assertEqual(len(fake.commands), 2)
        self.assertEqual(fake.commands[0][0], {"shoulder_lift": 22})
        self.assertEqual(fake.commands[1][0], {"shoulder_lift": 40})
        self.assertFalse(fake.disabled)

    def test_loaded_axis_continuous_lift_never_restarts_after_stall(self):
        fake = FakePulseBus([70, 70])
        studio = make_motion_studio(
            fake,
            stall_seconds=0.0,
            correction_timeout=0.0,
            joint_name="shoulder_lift",
            motor_id=2,
            continuous_lift=True,
        )
        studio._motion_worker(
            {"shoulder_lift": 100},
            {"shoulder_lift": 40},
            ["shoulder_lift"],
            MotionProfile(120, 2, 70, 1),
        )
        kinds = []
        while not studio.events.empty():
            kinds.append(studio.events.get_nowait()[0])
        self.assertIn("motion_incomplete", kinds)
        self.assertEqual(len(fake.commands), 1)
        self.assertEqual(fake.commands[0][0], {"shoulder_lift": 22})
        self.assertFalse(fake.disabled)


if __name__ == "__main__":
    unittest.main()
