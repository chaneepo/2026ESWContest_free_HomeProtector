"""CARE-PACK SO-ARM101 six-axis profiled PULSE controller.

The PC normally sends one final raw Goal_Position together with STS3215
Goal_Velocity and Acceleration values. For a measured loaded-axis lift it sends
one bounded lead target, then hands off the exact target before the motor stops.
The motor firmware performs acceleration/deceleration. Motor IDs 1-6 are included.
"""

from __future__ import annotations

import csv
import json
import math
import os
import queue
import shutil
import threading
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "carepack_so101_profiled_config.json"
MOTION_LOG_PATH = APP_DIR / "carepack_motion_log.csv"
RANGE_OVERRIDE_PATH = APP_DIR / "carepack_so101_range_overrides.json"
RANGE_OVERRIDE_FORMAT = "carepack-so101-range-overrides-v1"
PREVIOUS_VERSION_DIR = APP_DIR.parent / "carepack_so101_profiled_studio_v20"
MIGRATED_SETTING_FILES = (
    "carepack_so101_wrist_homing_backup.json",
    "carepack_so101_gripper_calibration.json",
    "carepack_so101_loaded_axis_tuning_backup.json",
    "carepack_so101_range_overrides.json",
)
SEQUENCE_FORMAT = "carepack-so101-motion-sequence-v1"
TUNING_REGISTERS = {
    "p": "P_Coefficient",
    "d": "D_Coefficient",
    "i": "I_Coefficient",
    "punch": "Minimum_Startup_Force",
}
MOTOR_DIAGNOSTIC_REGISTERS = {
    "min_position": "Min_Position_Limit",
    "max_position": "Max_Position_Limit",
    "operating_mode": "Operating_Mode",
    "homing_offset": "Homing_Offset",
    "maximum_velocity": "Maximum_Velocity_Limit",
}


def migrate_previous_settings() -> list[str]:
    """Copy missing v20 settings without overwriting v21 files."""
    copied: list[str] = []
    if not PREVIOUS_VERSION_DIR.is_dir():
        return copied
    for filename in MIGRATED_SETTING_FILES:
        source = PREVIOUS_VERSION_DIR / filename
        destination = APP_DIR / filename
        if source.is_file() and not destination.exists():
            shutil.copy2(source, destination)
            copied.append(filename)
    return copied


@dataclass(frozen=True)
class JointSpec:
    name: str
    label: str
    motor_id: int
    center: int | None
    allowed_ranges: tuple[tuple[int, int], ...]
    torque_limit: int
    forbid_cross_branch: bool = False


@dataclass(frozen=True)
class MotionProfile:
    arm_speed: int
    arm_acceleration: int
    gripper_speed: int
    gripper_acceleration: int


@dataclass(frozen=True)
class GripperCalibration:
    open_raw: int
    closed_raw: int
    open_safe: int
    closed_safe: int
    minimum: int
    maximum: int


class MotionIncompleteError(RuntimeError):
    """A non-dangerous convergence failure after the arm has been frozen in place."""

    def __init__(self, message: str, positions: dict[str, int]) -> None:
        super().__init__(message)
        self.positions = positions


def validate_tuning_values(values: dict[str, int]) -> dict[str, int]:
    required = set(TUNING_REGISTERS)
    if set(values) != required:
        raise ValueError(f"튜닝값에는 {sorted(required)}가 정확히 필요합니다.")
    clean = {key: int(value) for key, value in values.items()}
    for key in ("p", "d", "i"):
        if not 0 <= clean[key] <= 254:
            raise ValueError(f"{key.upper()} 값은 0~254 범위여야 합니다.")
    if not 0 <= clean["punch"] <= 1023:
        raise ValueError("Punch 값은 0~1023 범위여야 합니다.")
    return clean


def load_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_joint_specs(config: dict) -> list[JointSpec]:
    specs = [
        JointSpec(
            name=item["name"],
            label=item["label"],
            motor_id=int(item["motor_id"]),
            center=None if item.get("center") is None else int(item["center"]),
            allowed_ranges=tuple((int(a), int(b)) for a, b in item.get("allowed_ranges", [])),
            torque_limit=int(item["torque_limit"]),
            forbid_cross_branch=bool(item.get("forbid_cross_branch", False)),
        )
        for item in config["joints"]
    ]
    specs.sort(key=lambda spec: spec.motor_id)
    if [spec.motor_id for spec in specs] != [1, 2, 3, 4, 5, 6]:
        raise ValueError("Configuration must define motor IDs 1-6 exactly once.")
    return specs


def in_allowed_ranges(value: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(low <= value <= high for low, high in ranges)


def range_branch(value: int, ranges: tuple[tuple[int, int], ...]) -> int | None:
    for index, (low, high) in enumerate(ranges):
        if low <= value <= high:
            return index
    return None


def ranges_text(ranges: tuple[tuple[int, int], ...]) -> str:
    return " 또는 ".join(f"{low}~{high}" for low, high in ranges)


def clamp_to_ranges(value: int | float, ranges: tuple[tuple[int, int], ...]) -> int:
    """Clamp a numeric target to the nearest point in one of the safe ranges."""
    if not ranges:
        raise ValueError("안전범위가 없습니다.")
    rounded = int(round(value))
    if in_allowed_ranges(rounded, ranges):
        return rounded
    boundaries = [point for low, high in ranges for point in (low, high)]
    return min(boundaries, key=lambda point: abs(point - rounded))


def intersect_ranges(
    ranges: tuple[tuple[int, int], ...], low_limit: int, high_limit: int
) -> tuple[tuple[int, int], ...]:
    """Intersect program ranges with motor EEPROM limits."""
    result = []
    for low, high in ranges:
        clipped_low = max(int(low), int(low_limit))
        clipped_high = min(int(high), int(high_limit))
        if clipped_low <= clipped_high:
            result.append((clipped_low, clipped_high))
    return tuple(result)


def expand_ranges_to_include(
    ranges: tuple[tuple[int, int], ...], value: int
) -> tuple[tuple[int, int], ...]:
    """Temporarily include an out-of-range start pose without an initial jump."""
    if not ranges:
        return ((int(value), int(value)),)
    if in_allowed_ranges(int(value), ranges):
        return ranges
    low = min(low for low, _high in ranges)
    high = max(high for _low, high in ranges)
    return ((min(low, int(value)), max(high, int(value))),)


def validate_range_pair(low: int | str, high: int | str) -> tuple[int, int]:
    """Validate one editable raw PULSE range."""
    try:
        clean_low = int(low)
        clean_high = int(high)
    except (TypeError, ValueError) as exc:
        raise ValueError("최소·최대 PULSE는 정수여야 합니다.") from exc
    if not 0 <= clean_low <= 4095 or not 0 <= clean_high <= 4095:
        raise ValueError("최소·최대 PULSE는 0~4095 범위여야 합니다.")
    if clean_low >= clean_high:
        raise ValueError("최소 PULSE는 최대 PULSE보다 작아야 합니다.")
    return clean_low, clean_high


def unwrap_raw_position(
    previous_raw: int,
    previous_unwrapped: int,
    current_raw: int,
    modulus: int = 4096,
) -> int:
    """Continue a wrapping 0..4095 position without a false full-turn jump."""
    delta = int(current_raw) - int(previous_raw)
    half = modulus // 2
    if delta > half:
        delta -= modulus
    elif delta < -half:
        delta += modulus
    return int(previous_unwrapped) + delta


def map_relative_teleop_targets(
    leader_unwrapped: dict[str, int],
    leader_anchors: dict[str, int],
    follower_anchors: dict[str, int],
    directions: dict[str, int],
    scale: float,
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
    enabled_names: set[str] | None = None,
) -> dict[str, int]:
    """Map leader displacement from the start pose into bounded follower targets."""
    selected = set(follower_anchors) if enabled_names is None else enabled_names
    result: dict[str, int] = {}
    for name, follower_anchor in follower_anchors.items():
        if name not in selected:
            result[name] = int(follower_anchor)
            continue
        direction = int(directions.get(name, 1))
        if direction not in (-1, 1):
            raise ValueError(f"{name} 방향은 1 또는 -1이어야 합니다.")
        delta = int(leader_unwrapped[name]) - int(leader_anchors[name])
        requested = int(follower_anchor) + delta * direction * float(scale)
        result[name] = clamp_to_ranges(requested, ranges_by_name[name])
    return result


def limit_teleop_targets(
    requested: dict[str, int],
    previous_commands: dict[str, int],
    measured: dict[str, int],
    max_steps: dict[str, int],
    max_leads: dict[str, int],
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
) -> dict[str, int]:
    """Limit both command slew rate and how far a target may lead the motor."""
    result: dict[str, int] = {}
    for name, desired in requested.items():
        previous = int(previous_commands[name])
        step = max(1, int(max_steps[name]))
        delta = max(-step, min(step, int(desired) - previous))
        target = previous + delta
        lead = max(1, int(max_leads[name]))
        target = max(int(measured[name]) - lead, min(int(measured[name]) + lead, target))
        result[name] = clamp_to_ranges(target, ranges_by_name[name])
    return result


def select_teleop_targets(
    direct_mode: bool,
    requested: dict[str, int],
    previous_commands: dict[str, int],
    measured: dict[str, int],
    max_steps: dict[str, int],
    max_leads: dict[str, int],
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
) -> dict[str, int]:
    """Use raw leader targets in direct mode and limits only in safe mode."""
    if direct_mode:
        return {name: int(value) for name, value in requested.items()}
    return limit_teleop_targets(
        requested,
        previous_commands,
        measured,
        max_steps,
        max_leads,
        ranges_by_name,
    )


def validate_sequence_steps(
    payload: dict,
    specs: list[JointSpec],
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
) -> list[dict]:
    """Validate and normalize a saved fixed-pose motion sequence."""
    if payload.get("format") != SEQUENCE_FORMAT:
        raise ValueError("지원하지 않는 동작 시퀀스 파일입니다.")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("동작 단계가 하나 이상 필요합니다.")

    known_names = {spec.name for spec in specs}
    normalized: list[dict] = []
    for index, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"{index}번 단계 형식이 올바르지 않습니다.")
        name = str(raw.get("name", "")).strip() or f"단계 {index}"
        target_raw = raw.get("targets")
        if not isinstance(target_raw, dict):
            raise ValueError(f"{name}: 목표값이 없습니다.")
        try:
            targets = {spec.name: int(target_raw[spec.name]) for spec in specs}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{name}: 1~6번 목표 PULSE가 모두 필요합니다.") from exc

        selected_raw = raw.get("selected", [spec.name for spec in specs])
        if not isinstance(selected_raw, list):
            raise ValueError(f"{name}: 이동 축 목록 형식이 올바르지 않습니다.")
        selected = [str(item) for item in selected_raw]
        if not selected or len(set(selected)) != len(selected):
            raise ValueError(f"{name}: 이동 축을 하나 이상 중복 없이 지정하세요.")
        unknown = set(selected) - known_names
        if unknown:
            raise ValueError(f"{name}: 알 수 없는 이동 축 {sorted(unknown)}")

        for axis in selected:
            ranges = ranges_by_name.get(axis, ())
            if not ranges or not in_allowed_ranges(targets[axis], ranges):
                raise ValueError(
                    f"{name}: {axis} 목표 {targets[axis]}가 허용범위를 벗어났습니다."
                )
        try:
            wait_seconds = float(raw.get("wait_seconds", 0.5))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}: 대기시간은 숫자여야 합니다.") from exc
        if not 0.0 <= wait_seconds <= 60.0:
            raise ValueError(f"{name}: 대기시간은 0~60초여야 합니다.")
        normalized.append(
            {
                "name": name,
                "targets": targets,
                "selected": selected,
                "wait_seconds": wait_seconds,
            }
        )
    return normalized


def validate_current_positions(
    specs: list[JointSpec],
    current: dict[str, int],
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
    tolerance: int,
) -> None:
    """Reject torque-on only when the measured pose is clearly outside its range."""
    failures: list[str] = []
    for spec in specs:
        ranges = ranges_by_name.get(spec.name, ())
        if not ranges:
            continue
        value = int(current[spec.name])
        if not any(low - tolerance <= value <= high + tolerance for low, high in ranges):
            failures.append(f"{spec.label} {value} (허용 {ranges_text(ranges)})")
    if failures:
        raise ValueError(
            "현재 위치가 측정 가동범위를 벗어나 토크를 켜지 않았습니다.\n"
            + "\n".join(failures)
        )


def prepare_selected_motion(
    specs: list[JointSpec],
    current: dict[str, int],
    target_texts: dict[str, str],
    selected_names: set[str],
    ranges_by_name: dict[str, tuple[tuple[int, int], ...]],
    forbid_cross_names: set[str] | None = None,
) -> tuple[dict[str, int], list[str]]:
    """Validate selected axes and force every unselected axis to its live position."""
    forbid_cross_names = forbid_cross_names or set()
    known_names = {spec.name for spec in specs}
    unknown = selected_names - known_names
    if unknown:
        raise ValueError(f"알 수 없는 이동 축: {sorted(unknown)}")
    if not selected_names:
        raise ValueError("이동할 축을 하나 이상 선택하세요.")

    targets = dict(current)
    active_names: list[str] = []
    for spec in specs:
        if spec.name not in selected_names:
            continue
        ranges = ranges_by_name.get(spec.name, ())
        if not ranges:
            raise ValueError(f"{spec.label}: 교정 또는 영점 설정이 먼저 필요합니다.")
        try:
            value = int(target_texts[spec.name].strip())
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{spec.label} 목표값은 정수 PULSE여야 합니다.") from exc
        if not in_allowed_ranges(value, ranges):
            raise ValueError(
                f"{spec.label}: {value}는 허용범위 {ranges_text(ranges)} 밖입니다."
            )
        if spec.name in forbid_cross_names:
            start_branch = range_branch(current[spec.name], ranges)
            target_branch = range_branch(value, ranges)
            if start_branch is None:
                raise ValueError(
                    f"{spec.label} 현재값 {current[spec.name]}이 허용범위 밖입니다."
                )
            if start_branch != target_branch:
                raise ValueError(
                    "5번 손목 영점 재설정 전에는 0/4095 경계를 가로질러 이동할 수 없습니다."
                )
        targets[spec.name] = value
        active_names.append(spec.name)
    return targets, active_names


def continuous_lift_target(
    *,
    name: str,
    start: int,
    target: int,
    ranges: tuple[tuple[int, int], ...],
    lifting_delta_signs: dict[str, int],
    minimum_move: int,
    lead: int,
) -> int | None:
    """Return a bounded lead target that keeps a loaded-axis lift moving.

    The exact requested target is handed back to the motor while it is still
    moving, so this never becomes a stop-and-restart correction.
    """
    expected_sign = int(lifting_delta_signs.get(name, 0))
    delta = target - start
    move_sign = 1 if delta > 0 else -1 if delta < 0 else 0
    if (
        expected_sign not in (-1, 1)
        or move_sign != expected_sign
        or abs(delta) < int(minimum_move)
    ):
        return None
    lead_target = target + move_sign * int(lead)
    if not in_allowed_ranges(lead_target, ranges):
        return None
    return lead_target


def gripper_safe_calibration(
    open_raw: int,
    closed_raw: int,
    margin: int,
    maximum_span: int,
) -> GripperCalibration:
    if not 0 <= open_raw <= 4095 or not 0 <= closed_raw <= 4095:
        raise ValueError("집게 교정값은 0~4095 PULSE여야 합니다.")
    span = abs(closed_raw - open_raw)
    if span < 2 * margin + 20:
        raise ValueError("집게 열림·닫힘 교정값 차이가 너무 작습니다.")
    if span > maximum_span:
        raise ValueError("집게 범위가 0/4095를 통과합니다. FD에서 영점 또는 조립을 먼저 확인하세요.")
    direction = 1 if closed_raw > open_raw else -1
    open_safe = open_raw + direction * margin
    closed_safe = closed_raw - direction * margin
    return GripperCalibration(
        open_raw=open_raw,
        closed_raw=closed_raw,
        open_safe=open_safe,
        closed_safe=closed_safe,
        minimum=min(open_safe, closed_safe),
        maximum=max(open_safe, closed_safe),
    )


def scaled_speeds(distances: dict[str, int], maximum_speed: int, minimum_speed: int = 30) -> dict[str, int]:
    moving = {name: distance for name, distance in distances.items() if distance > 0}
    if not moving:
        return {}
    longest = max(moving.values())
    return {
        name: max(minimum_speed, int(round(maximum_speed * distance / longest)))
        for name, distance in moving.items()
    }


def apply_axis_motion_limits(
    speeds: dict[str, int],
    accelerations: dict[str, int],
    settings_by_name: dict[str, dict],
) -> tuple[dict[str, int], dict[str, int]]:
    """Apply conservative per-axis speed and acceleration overrides."""
    adjusted_speeds = dict(speeds)
    adjusted_accelerations = dict(accelerations)
    for name, speed in tuple(adjusted_speeds.items()):
        settings = settings_by_name.get(name, {})
        multiplier = float(settings.get("speed_multiplier", 1.0))
        value = max(1, int(round(speed * multiplier)))
        if "minimum_speed" in settings:
            value = max(value, int(settings["minimum_speed"]))
        if "maximum_speed" in settings:
            value = min(value, int(settings["maximum_speed"]))
        adjusted_speeds[name] = value
        if name in adjusted_accelerations and "maximum_acceleration" in settings:
            adjusted_accelerations[name] = min(
                adjusted_accelerations[name], int(settings["maximum_acceleration"])
            )
    return adjusted_speeds, adjusted_accelerations


def segmented_axis_waypoints(
    start: int,
    target: int,
    settings: dict,
) -> list[int]:
    """Return bounded intermediate goals for a configured movement direction."""
    delta = int(target) - int(start)
    if delta == 0:
        return []
    direction = 1 if delta > 0 else -1
    configured_direction = int(settings.get("segment_direction_sign", 0))
    segment_limit = int(settings.get("segment_limit_pulse", 0))
    if segment_limit <= 0 or configured_direction not in (0, direction):
        return [int(target)]
    count = max(1, int(math.ceil(abs(delta) / segment_limit)))
    return [
        int(start + round(delta * index / count))
        for index in range(1, count + 1)
    ]


def estimated_move_seconds(distance: int, speed: int, acceleration_raw: int) -> float:
    """Estimate trapezoidal/triangular motion time for timeout sizing."""
    if distance <= 0:
        return 0.0
    speed = max(1, speed)
    acceleration = max(1, acceleration_raw) * 100.0
    ramp_distance_total = speed * speed / acceleration
    if distance <= ramp_distance_total:
        return 2.0 * math.sqrt(distance / acceleration)
    return distance / speed + speed / acceleration


class PulseBus:
    def __init__(self, port: str, specs: list[JointSpec]) -> None:
        from lerobot.motors import Motor, MotorNormMode
        from lerobot.motors.feetech import FeetechMotorsBus

        self.specs = specs
        self.bus = FeetechMotorsBus(
            port=port,
            motors={
                spec.name: Motor(spec.motor_id, "sts3215", MotorNormMode.DEGREES)
                for spec in specs
            },
        )
        self.lock = threading.RLock()
        self.torque_on = False

    @property
    def connected(self) -> bool:
        return bool(self.bus.is_connected)

    def connect(self) -> None:
        with self.lock:
            self.bus.connect()
            self.bus.disable_torque()
            self.torque_on = False

    def disconnect(self) -> None:
        with self.lock:
            if self.bus.is_connected:
                try:
                    self.bus.disable_torque()
                finally:
                    self.torque_on = False
                    self.bus.disconnect()

    def _sync_write_raw(self, data_name: str, values: dict[str, int]) -> None:
        if not values:
            return
        try:
            self.bus.sync_write(data_name, values, normalize=False)
            return
        except (AttributeError, TypeError):
            # Compatibility fallback for older LeRobot versions.
            for name, value in values.items():
                self.bus.write(data_name, name, int(value), normalize=False)

    def read_positions(self) -> dict[str, int]:
        with self.lock:
            return {
                spec.name: int(self.bus.read("Present_Position", spec.name, normalize=False))
                for spec in self.specs
            }

    def read_telemetry(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        with self.lock:
            for spec in self.specs:
                values = {
                    key: int(self.bus.read(key, spec.name, normalize=False))
                    for key in (
                        "Present_Position",
                        "Present_Velocity",
                        "Present_Voltage",
                        "Present_Temperature",
                        "Present_Load",
                        "Moving",
                    )
                }
                try:
                    values["Present_Current"] = int(
                        self.bus.read("Present_Current", spec.name, normalize=False)
                    )
                except (KeyError, TypeError):
                    values["Present_Current"] = -1
                result[spec.name] = values
        return result

    def enable_torque(self, torque_limits: dict[str, int], hold_profile: MotionProfile) -> dict[str, int]:
        with self.lock:
            current = self.read_positions()
            self._sync_write_raw("Goal_Time", {name: 0 for name in current})
            self._sync_write_raw(
                "Goal_Velocity",
                {
                    spec.name: hold_profile.gripper_speed if spec.motor_id == 6 else hold_profile.arm_speed
                    for spec in self.specs
                },
            )
            self._sync_write_raw(
                "Acceleration",
                {
                    spec.name: (
                        hold_profile.gripper_acceleration if spec.motor_id == 6 else hold_profile.arm_acceleration
                    )
                    for spec in self.specs
                },
            )
            self._sync_write_raw("Torque_Limit", torque_limits)
            self._sync_write_raw("Goal_Position", current)
            self.bus.enable_torque()
            self.torque_on = True
            return current

    def disable_torque(self) -> None:
        with self.lock:
            if self.bus.is_connected:
                self.bus.disable_torque()
            self.torque_on = False

    def command_profiled(
        self,
        targets: dict[str, int],
        speeds: dict[str, int],
        accelerations: dict[str, int],
    ) -> None:
        with self.lock:
            self._sync_write_raw("Goal_Time", {name: 0 for name in targets})
            self._sync_write_raw("Acceleration", accelerations)
            self._sync_write_raw("Goal_Velocity", speeds)
            self._sync_write_raw("Goal_Position", targets)

    def hold_current_position(self) -> dict[str, int]:
        """Cancel the unfinished target and hold the measured pose without dropping torque."""
        with self.lock:
            current = self.read_positions()
            self._sync_write_raw("Goal_Time", {name: 0 for name in current})
            self._sync_write_raw("Goal_Position", current)
            return current

    def read_tuning(self, names: list[str]) -> dict[str, dict[str, int]]:
        with self.lock:
            return {
                name: {
                    key: int(self.bus.read(register, name, normalize=False))
                    for key, register in TUNING_REGISTERS.items()
                }
                for name in names
            }

    def read_motor_diagnostics(
        self, names: list[str] | None = None
    ) -> dict[str, dict[str, int]]:
        """Read EEPROM motion limits and mode without changing any setting."""
        selected = names or [spec.name for spec in self.specs]
        result: dict[str, dict[str, int]] = {}
        with self.lock:
            for name in selected:
                values: dict[str, int] = {}
                for key, register in MOTOR_DIAGNOSTIC_REGISTERS.items():
                    try:
                        values[key] = int(
                            self.bus.read(register, name, normalize=False)
                        )
                    except (KeyError, TypeError):
                        values[key] = -1
                values["present_position"] = int(
                    self.bus.read("Present_Position", name, normalize=False)
                )
                values["goal_position"] = int(
                    self.bus.read("Goal_Position", name, normalize=False)
                )
                result[name] = values
        return result

    def write_tuning(self, settings: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
        if self.torque_on:
            raise RuntimeError("모터 튜닝은 토크 OFF에서만 가능합니다.")
        clean = {name: validate_tuning_values(values) for name, values in settings.items()}
        with self.lock:
            for name, values in clean.items():
                self.bus.write("Lock", name, 0, normalize=False)
                try:
                    for key, register in TUNING_REGISTERS.items():
                        self.bus.write(register, name, values[key], normalize=False)
                        time.sleep(0.05)
                finally:
                    self.bus.write("Lock", name, 1, normalize=False)
            verified = self.read_tuning(list(clean))
        if verified != clean:
            raise RuntimeError(f"튜닝값 검증 실패: 요청={clean}, 읽기={verified}")
        return verified

    def read_homing_offset(self, name: str) -> int:
        with self.lock:
            return int(self.bus.read("Homing_Offset", name, normalize=False))

    def set_half_turn_homing(self, name: str) -> dict[str, int]:
        """Calculate and persist the offset that maps the current pose to 2048."""
        if self.torque_on:
            raise RuntimeError("손목 영점 재설정은 토크 OFF에서만 가능합니다.")
        with self.lock:
            before_position = int(
                self.bus.read("Present_Position", name, normalize=False)
            )
            before_offset = int(
                self.bus.read("Homing_Offset", name, normalize=False)
            )
            try:
                calculated = self.bus.set_half_turn_homings([name])
            except TypeError as exc:
                raise RuntimeError(
                    "현재 LeRobot 버전이 선택 모터 영점 재설정을 지원하지 않습니다. "
                    "lerobot을 업데이트한 뒤 다시 실행하세요."
                ) from exc
            if not isinstance(calculated, dict) or name not in calculated:
                raise RuntimeError("LeRobot이 5번 손목의 계산된 Homing Offset을 반환하지 않았습니다.")
            calculated_offset = int(calculated[name])

            # set_half_turn_homings() only calculates the offset. Persist it to
            # the motor EEPROM so Present_Position itself becomes continuous.
            self.bus.write("Lock", name, 0, normalize=False)
            try:
                self.bus.write(
                    "Homing_Offset", name, calculated_offset, normalize=False
                )
                time.sleep(0.2)
            finally:
                self.bus.write("Lock", name, 1, normalize=False)
            after_position = int(
                self.bus.read("Present_Position", name, normalize=False)
            )
            after_offset = int(
                self.bus.read("Homing_Offset", name, normalize=False)
            )
        if after_offset != calculated_offset:
            raise RuntimeError(
                f"Homing Offset 기록 검증 실패: 계산 {calculated_offset}, 읽기 {after_offset}"
            )
        return {
            "before_position": before_position,
            "before_offset": before_offset,
            "after_position": after_position,
            "after_offset": after_offset,
            "calculated_offset": calculated_offset,
        }

    def write_homing_offset(self, name: str, offset: int) -> int:
        if self.torque_on:
            raise RuntimeError("손목 영점 복원은 토크 OFF에서만 가능합니다.")
        with self.lock:
            self.bus.write("Lock", name, 0, normalize=False)
            try:
                self.bus.write("Homing_Offset", name, int(offset), normalize=False)
                time.sleep(0.2)
            finally:
                self.bus.write("Lock", name, 1, normalize=False)
            verified = int(self.bus.read("Homing_Offset", name, normalize=False))
        if verified != int(offset):
            raise RuntimeError(
                f"영점 복원 검증 실패: 요청 {offset}, 읽기 {verified}"
            )
        return verified


class ProfiledStudio:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.config = load_config()
        self.specs = load_joint_specs(self.config)
        self.by_name = {spec.name: spec for spec in self.specs}
        self.gripper_spec = self.by_name["gripper"]
        self.gripper_path = APP_DIR / self.config["gripper"]["calibration_file"]
        self.tuning_path = APP_DIR / self.config["loaded_axis_tuning"]["backup_file"]
        self.wrist_homing_settings = self.config["wrist_homing"]
        self.wrist_name = str(self.wrist_homing_settings["motor_name"])
        self.wrist_homing_path = APP_DIR / self.wrist_homing_settings["backup_file"]
        self.wrist_homing_applied = False
        self.wrist_homing_state = "legacy"
        self._load_wrist_homing_state()
        self.wrist_setup_prompt_shown = False
        self.loaded_joint_names = list(self.config["loaded_axis_tuning"]["motor_names"])
        self.loaded_tuning_baseline = validate_tuning_values(
            self.config["loaded_axis_tuning"]["baseline"]
        )
        self.loaded_tuning_targets = {
            stage: validate_tuning_values(self.config["loaded_axis_tuning"][stage])
            for stage in ("stage1", "stage2")
        }
        self.gripper_open_raw: int | None = None
        self.gripper_closed_raw: int | None = None
        self.gripper_calibration: GripperCalibration | None = None
        self._load_gripper_calibration()
        self.range_overrides: dict[str, tuple[tuple[int, int], ...]] = {}
        self.range_override_load_error: str | None = None
        self._load_range_overrides()

        self.pulse_bus: PulseBus | None = None
        self.leader_bus: PulseBus | None = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.motion_stop = threading.Event()
        self.monitor_stop = threading.Event()
        self.teleop_stop = threading.Event()
        self.motion_thread: threading.Thread | None = None
        self.monitor_thread: threading.Thread | None = None
        self.teleop_thread: threading.Thread | None = None
        self.teleop_running = False
        self.closing = False
        self.sequence_steps: list[dict] = []
        self.sequence_running = False
        self.sequence_index = 0
        self.sequence_after_id: str | None = None
        self.motion_context: dict | None = None
        self.latest_telemetry: dict[str, dict[str, int]] = {}

        self.port_var = tk.StringVar(value=self.config.get("port", "COM3"))
        teleop_config = self.config.get("teleoperation", {})
        self.leader_port_var = tk.StringVar(
            value=str(teleop_config.get("leader_port", "COM4"))
        )
        self.teleop_scale_var = tk.DoubleVar(
            value=float(teleop_config.get("default_scale", 0.5))
        )
        default_mode = str(teleop_config.get("default_mode", "direct"))
        self.teleop_mode_var = tk.StringVar(
            value="1:1 빠른 추종" if default_mode == "direct" else "안전 추종"
        )
        configured_directions = teleop_config.get("directions", {})
        self.teleop_reverse_vars = {
            spec.name: tk.BooleanVar(
                value=int(configured_directions.get(spec.name, 1)) < 0
            )
            for spec in self.specs
        }
        self.teleop_enabled_vars = {
            spec.name: tk.BooleanVar(value=False) for spec in self.specs
        }
        self.profile_var = tk.StringVar(value=self.config.get("default_profile", "gentle"))
        profile = self._profile_from_config(self.profile_var.get())
        self.arm_speed_var = tk.IntVar(value=profile.arm_speed)
        self.arm_accel_var = tk.IntVar(value=profile.arm_acceleration)
        self.gripper_speed_var = tk.IntVar(value=profile.gripper_speed)
        self.gripper_accel_var = tk.IntVar(value=profile.gripper_acceleration)
        self.status_var = tk.StringVar(value="연결 안 됨 · 토크 OFF")
        self.gripper_cal_var = tk.StringVar()
        self.wrist_homing_var = tk.StringVar()
        self.motor_diagnostic_var = tk.StringVar(
            value="연결 후 토크 OFF에서 내부 MIN·MAX·MODE를 확인할 수 있습니다."
        )
        self.sequence_name_var = tk.StringVar(value="CARE-PACK 고정 자세 동작")
        self.sequence_step_name_var = tk.StringVar(value="단계 1")
        self.sequence_wait_var = tk.DoubleVar(value=0.5)
        self.sequence_status_var = tk.StringVar(value="등록된 동작 단계 없음")
        self.leader_status_var = tk.StringVar(value="리더암 연결 안 됨 · 토크 OFF")
        self.teleop_status_var = tk.StringVar(
            value="팔로워와 리더를 연결한 뒤 작은 움직임부터 시험하세요."
        )
        self.leader_position_vars: dict[str, tk.StringVar] = {}
        self.teleop_target_vars: dict[str, tk.StringVar] = {}
        self.range_min_vars: dict[str, tk.StringVar] = {}
        self.range_max_vars: dict[str, tk.StringVar] = {}
        self.range_active_vars: dict[str, tk.StringVar] = {}
        self.range_settings_status_var = tk.StringVar(
            value=(
                f"저장된 범위 파일 오류: {self.range_override_load_error}"
                if self.range_override_load_error
                else "사용자가 저장한 값만 프로그램 허용범위로 사용합니다. EEPROM은 변경하지 않습니다."
            )
        )
        self.position_vars: dict[str, tk.StringVar] = {}
        self.target_vars: dict[str, tk.StringVar] = {}
        self.selected_vars: dict[str, tk.BooleanVar] = {}
        self.telemetry_vars: dict[str, tk.StringVar] = {}
        self.limit_vars: dict[str, tk.StringVar] = {}
        filter_size = int(self.config["safety"].get("telemetry_filter_samples", 3))
        self.ui_voltage_history = {
            spec.name: deque(maxlen=filter_size) for spec in self.specs
        }
        self.ui_temperature_history = {
            spec.name: deque(maxlen=filter_size) for spec in self.specs
        }

        self._build()
        self._refresh_gripper_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.root.after(100, self._poll_events)

    def _load_range_overrides(self) -> None:
        self.range_overrides = {}
        self.range_override_load_error = None
        if not RANGE_OVERRIDE_PATH.exists():
            return
        try:
            payload = json.loads(RANGE_OVERRIDE_PATH.read_text(encoding="utf-8"))
            if payload.get("format") != RANGE_OVERRIDE_FORMAT:
                raise ValueError("지원하지 않는 허용범위 파일 형식입니다.")
            raw_ranges = payload.get("ranges")
            if not isinstance(raw_ranges, dict):
                raise ValueError("ranges 항목이 없습니다.")
            known_names = {spec.name for spec in self.specs}
            unknown = set(raw_ranges) - known_names
            if unknown:
                raise ValueError(f"알 수 없는 축: {sorted(unknown)}")
            for name, raw_pair in raw_ranges.items():
                if not isinstance(raw_pair, list) or len(raw_pair) != 2:
                    raise ValueError(f"{name}: [최소, 최대] 형식이어야 합니다.")
                low, high = validate_range_pair(raw_pair[0], raw_pair[1])
                self.range_overrides[name] = ((low, high),)
        except Exception as exc:
            self.range_overrides = {}
            self.range_override_load_error = str(exc)

    def _profile_from_config(self, name: str) -> MotionProfile:
        raw = self.config["profiles"][name]
        return MotionProfile(
            arm_speed=int(raw["arm_speed"]),
            arm_acceleration=int(raw["arm_acceleration"]),
            gripper_speed=int(raw["gripper_speed"]),
            gripper_acceleration=int(raw["gripper_acceleration"]),
        )

    def _build(self) -> None:
        self.root.title("CARE-PACK SO-ARM101 Profiled PULSE Studio v21")
        self.root.geometry("1480x900")
        self.root.minsize(1050, 700)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        manual_tab = ttk.Frame(self.notebook)
        automation_tab = ttk.Frame(self.notebook, padding=14)
        range_tab = ttk.Frame(self.notebook, padding=14)
        leader_tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(manual_tab, text="수동 조작·교정")
        self.notebook.add(automation_tab, text="자동 동작·기록")
        self.notebook.add(range_tab, text="허용범위 설정")
        self.notebook.add(leader_tab, text="리더암 조작")
        outer = self._make_scrollable_tab(manual_tab)

        ttk.Label(outer, text="SO-ARM101 Profiled PULSE Studio v21", font=("Malgun Gothic", 17, "bold")).grid(
            row=0, column=0, columnspan=9, sticky="w"
        )
        ttk.Label(
            outer,
            text="모터 1~6 · 선택 축만 이동 · 손목 연속범위 · 들어 올림 연속 보정",
        ).grid(row=1, column=0, columnspan=9, sticky="w", pady=(2, 10))

        connection = ttk.LabelFrame(outer, text="연결과 토크", padding=10)
        connection.grid(row=2, column=0, columnspan=9, sticky="ew", pady=(0, 8))
        ttk.Label(connection, text="Port").grid(row=0, column=0, padx=4)
        ttk.Entry(connection, textvariable=self.port_var, width=10).grid(row=0, column=1, padx=4)
        self.connect_btn = ttk.Button(connection, text="연결", command=self.connect_async)
        self.connect_btn.grid(row=0, column=2, padx=4)
        self.torque_btn = ttk.Button(connection, text="토크 켜기", command=self.toggle_torque, state="disabled")
        self.torque_btn.grid(row=0, column=3, padx=4)
        self.stop_btn = ttk.Button(
            connection, text="긴급 정지 + 6축 토크 OFF", command=self.emergency_stop, state="disabled"
        )
        self.stop_btn.grid(row=0, column=4, padx=(20, 4))
        self.read_tuning_btn = ttk.Button(
            connection, text="2·3축 설정 확인", command=self.show_loaded_axis_tuning, state="disabled"
        )
        self.read_tuning_btn.grid(row=0, column=5, padx=(20, 4))
        self.apply_tuning_btn = ttk.Button(
            connection,
            text="2·3축 1단계 보강",
            command=lambda: self.apply_loaded_axis_tuning("stage1"),
            state="disabled",
        )
        self.apply_tuning_btn.grid(row=0, column=6, padx=4)
        self.apply_tuning_stage2_btn = ttk.Button(
            connection,
            text="2·3축 2단계 보강",
            command=lambda: self.apply_loaded_axis_tuning("stage2"),
            state="disabled",
        )
        self.apply_tuning_stage2_btn.grid(row=0, column=7, padx=4)
        self.restore_tuning_btn = ttk.Button(
            connection, text="원래값 복원", command=self.restore_loaded_axis_tuning, state="disabled"
        )
        self.restore_tuning_btn.grid(row=0, column=8, padx=4)
        ttk.Label(
            connection,
            text="1단계 P20/D36/I0/Punch24 · 2단계 P24/D40/I0/Punch32 · 토크 OFF에서만 적용",
            foreground="#6b3f00",
        ).grid(row=1, column=0, columnspan=9, sticky="w", padx=4, pady=(8, 0))
        self.recover_btn = ttk.Button(
            connection,
            text="통신 복구(토크 OFF)",
            command=self.recover_connection,
        )
        self.recover_btn.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0))
        ttk.Label(
            connection,
            text="연결·토크 버튼이 반응하지 않을 때 팔을 받치고 누르면 포트를 닫았다가 다시 연결합니다.",
            foreground="#7a2e00",
        ).grid(row=2, column=2, columnspan=7, sticky="w", padx=4, pady=(8, 0))

        motion = ttk.LabelFrame(outer, text="내장 가속·감속 프로필 (다음 이동부터 적용)", padding=10)
        motion.grid(row=3, column=0, columnspan=9, sticky="ew", pady=(0, 8))
        ttk.Label(motion, text="프리셋").grid(row=0, column=0, padx=4)
        profile_combo = ttk.Combobox(
            motion,
            textvariable=self.profile_var,
            values=tuple(self.config["profiles"].keys()),
            state="readonly",
            width=10,
        )
        profile_combo.grid(row=0, column=1, padx=4)
        profile_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_preset())
        ttk.Button(motion, text="프리셋 불러오기", command=self.apply_preset).grid(row=0, column=2, padx=4)

        ttk.Label(motion, text="팔 속도(PULSE/s)").grid(row=0, column=3, padx=(18, 4))
        self._spin(motion, self.arm_speed_var, *self.config["profile_limits"]["arm_speed"], row=0, col=4)
        ttk.Label(motion, text="팔 가속도(×100 PULSE/s²)").grid(row=0, column=5, padx=(12, 4))
        self._spin(motion, self.arm_accel_var, *self.config["profile_limits"]["arm_acceleration"], row=0, col=6)
        ttk.Label(motion, text="집게 속도").grid(row=1, column=3, padx=(18, 4), pady=(7, 0))
        self._spin(motion, self.gripper_speed_var, *self.config["profile_limits"]["gripper_speed"], row=1, col=4)
        ttk.Label(motion, text="집게 가속도(×100 PULSE/s²)").grid(row=1, column=5, padx=(12, 4), pady=(7, 0))
        self._spin(
            motion,
            self.gripper_accel_var,
            *self.config["profile_limits"]["gripper_acceleration"],
            row=1,
            col=6,
        )
        ttk.Label(
            motion,
            text="값이 낮을수록 느리고 완만합니다. 가속도 0은 순간 가속이므로 입력할 수 없습니다.",
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=4, pady=(8, 0))

        headers = ("관절", "ID", "허용범위", "현재 PULSE", "목표 PULSE", "이동 선택", "미세조정", "상태")
        for col, label in enumerate(headers):
            ttk.Label(outer, text=label, font=("Malgun Gothic", 10, "bold")).grid(
                row=4, column=col, padx=5, pady=4
            )
        for row, spec in enumerate(self.specs, start=5):
            self.position_vars[spec.name] = tk.StringVar(value="----")
            self.target_vars[spec.name] = tk.StringVar(value=str(spec.center or 2048))
            self.selected_vars[spec.name] = tk.BooleanVar(value=False)
            self.telemetry_vars[spec.name] = tk.StringVar(value="--.-V  --°C")
            self.limit_vars[spec.name] = tk.StringVar(value=self._limit_text(spec))
            ttk.Label(outer, text=spec.label, width=15).grid(row=row, column=0, sticky="w", padx=5, pady=6)
            ttk.Label(outer, text=str(spec.motor_id), width=4).grid(row=row, column=1)
            ttk.Label(outer, textvariable=self.limit_vars[spec.name], width=23).grid(row=row, column=2)
            ttk.Label(outer, textvariable=self.position_vars[spec.name], width=12).grid(row=row, column=3)
            target_entry = ttk.Entry(
                outer, textvariable=self.target_vars[spec.name], width=12, justify="center"
            )
            target_entry.grid(row=row, column=4)
            target_entry.bind(
                "<KeyRelease>",
                lambda _event, n=spec.name: self.selected_vars[n].set(True),
            )
            ttk.Checkbutton(
                outer, variable=self.selected_vars[spec.name]
            ).grid(row=row, column=5)
            nudge = ttk.Frame(outer)
            nudge.grid(row=row, column=6)
            for col, delta in enumerate((-20, -5, 5, 20)):
                ttk.Button(
                    nudge,
                    text=f"{delta:+d}",
                    width=5,
                    command=lambda n=spec.name, d=delta: self.nudge_target(n, d),
                ).grid(row=0, column=col, padx=1)
            ttk.Label(outer, textvariable=self.telemetry_vars[spec.name], width=23).grid(row=row, column=7)

        controls = ttk.LabelFrame(outer, text="프로파일 위치 이동", padding=10)
        controls.grid(row=11, column=0, columnspan=9, sticky="ew", pady=(10, 8))
        self.capture_btn = ttk.Button(controls, text="현재값 → 목표값", command=self.capture_current, state="disabled")
        self.capture_btn.grid(row=0, column=0, padx=5)
        self.move_btn = ttk.Button(controls, text="프로파일 이동", command=self.start_motion, state="disabled")
        self.move_btn.grid(row=0, column=1, padx=5)
        ttk.Button(controls, text="목표 자세 저장", command=self.save_pose).grid(row=0, column=2, padx=(20, 5))
        ttk.Button(controls, text="목표 자세 불러오기", command=self.load_pose).grid(row=0, column=3, padx=5)
        self.open_target_btn = ttk.Button(
            controls, text="집게 열림 목표", command=lambda: self.set_gripper_target(True), state="disabled"
        )
        self.open_target_btn.grid(row=0, column=4, padx=(20, 5))
        self.close_target_btn = ttk.Button(
            controls, text="집게 닫힘 목표", command=lambda: self.set_gripper_target(False), state="disabled"
        )
        self.close_target_btn.grid(row=0, column=5, padx=5)

        wrist = ttk.LabelFrame(outer, text="5번 손목 회전 영점 — 토크 OFF에서만", padding=10)
        wrist.grid(row=12, column=0, columnspan=9, sticky="ew", pady=(0, 8))
        self.read_wrist_homing_btn = ttk.Button(
            wrist, text="현재 영점 확인", command=self.show_wrist_homing, state="disabled"
        )
        self.read_wrist_homing_btn.grid(row=0, column=0, padx=5)
        self.apply_wrist_homing_btn = ttk.Button(
            wrist,
            text="현재 중앙을 2048로 설정",
            command=self.apply_wrist_half_turn_homing,
            state="disabled",
        )
        self.apply_wrist_homing_btn.grid(row=0, column=1, padx=5)
        self.restore_wrist_homing_btn = ttk.Button(
            wrist,
            text="원래 손목 영점 복원",
            command=self.restore_wrist_homing,
            state="disabled",
        )
        self.restore_wrist_homing_btn.grid(row=0, column=2, padx=5)
        ttk.Label(wrist, textvariable=self.wrist_homing_var, font=("Malgun Gothic", 10, "bold")).grid(
            row=1, column=0, columnspan=8, sticky="w", padx=5, pady=(8, 0)
        )

        gripper = ttk.LabelFrame(outer, text="6번 집게 교정 — 토크 OFF에서만", padding=10)
        gripper.grid(row=13, column=0, columnspan=9, sticky="ew", pady=(0, 8))
        self.gripper_open_capture_btn = ttk.Button(
            gripper, text="현재 위치를 열림으로 저장", command=lambda: self.capture_gripper_endpoint(True), state="disabled"
        )
        self.gripper_open_capture_btn.grid(row=0, column=0, padx=5)
        self.gripper_closed_capture_btn = ttk.Button(
            gripper, text="현재 위치를 닫힘으로 저장", command=lambda: self.capture_gripper_endpoint(False), state="disabled"
        )
        self.gripper_closed_capture_btn.grid(row=0, column=1, padx=5)
        ttk.Label(gripper, textvariable=self.gripper_cal_var, font=("Malgun Gothic", 10, "bold")).grid(
            row=1, column=0, columnspan=7, sticky="w", padx=5, pady=(8, 0)
        )

        diagnostics = ttk.LabelFrame(
            outer, text="1~6번 모터 내부 제한 진단 — 읽기 전용·토크 OFF", padding=10
        )
        diagnostics.grid(row=14, column=0, columnspan=9, sticky="ew", pady=(0, 8))
        self.motor_diagnostic_btn = ttk.Button(
            diagnostics,
            text="내부 MIN·MAX·MODE 확인",
            command=self.show_motor_diagnostics,
            state="disabled",
        )
        self.motor_diagnostic_btn.grid(row=0, column=0, padx=5)
        ttk.Label(
            diagnostics,
            textvariable=self.motor_diagnostic_var,
            font=("Malgun Gothic", 9),
            justify="left",
        ).grid(row=1, column=0, columnspan=8, sticky="w", padx=5, pady=(8, 0))

        ttk.Separator(outer).grid(row=15, column=0, columnspan=9, sticky="ew", pady=5)
        ttk.Label(outer, textvariable=self.status_var, font=("Malgun Gothic", 10, "bold")).grid(
            row=16, column=0, columnspan=9, sticky="w", padx=4
        )
        ttk.Label(
            outer,
            text="주의: 체크한 축만 움직입니다. 손목 재설정은 물리적 중앙에 둔 뒤 한 번만 실행하세요.",
            foreground="#8a3b00",
        ).grid(row=17, column=0, columnspan=9, sticky="w", padx=4, pady=(6, 0))

        self._refresh_wrist_homing_ui()
        self._build_automation_tab(automation_tab)
        self._build_range_tab(range_tab)
        self._build_leader_tab(leader_tab)

    def _make_scrollable_tab(self, parent: ttk.Frame) -> ttk.Frame:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        canvas = tk.Canvas(parent, highlightthickness=0)
        vertical = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        outer = ttk.Frame(canvas, padding=14)
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        def refresh_scroll_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_width(event) -> None:
            requested = max(1320, outer.winfo_reqwidth())
            canvas.itemconfigure(window_id, width=max(event.width, requested))
            refresh_scroll_region()

        outer.bind("<Configure>", refresh_scroll_region)
        canvas.bind("<Configure>", fit_width)
        canvas.bind(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"),
        )
        return outer

    def _build_automation_tab(self, outer: ttk.Frame) -> None:
        outer.columnconfigure(0, weight=1)
        ttk.Label(
            outer,
            text="고정 자세 자동 동작",
            font=("Malgun Gothic", 17, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "수동 탭의 현재 목표 PULSE 6개를 한 단계로 등록하고 순서대로 실행합니다. "
                "카메라·센서 확인이 없는 고정 위치 시험용입니다."
            ),
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        editor = ttk.LabelFrame(outer, text="단계 추가", padding=10)
        editor.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(editor, text="시퀀스 이름").grid(row=0, column=0, padx=4)
        ttk.Entry(editor, textvariable=self.sequence_name_var, width=28).grid(row=0, column=1, padx=4)
        ttk.Label(editor, text="단계 이름").grid(row=0, column=2, padx=(20, 4))
        ttk.Entry(editor, textvariable=self.sequence_step_name_var, width=22).grid(row=0, column=3, padx=4)
        ttk.Label(editor, text="완료 후 대기(초)").grid(row=0, column=4, padx=(20, 4))
        ttk.Spinbox(
            editor,
            from_=0.0,
            to=60.0,
            increment=0.1,
            textvariable=self.sequence_wait_var,
            width=7,
        ).grid(row=0, column=5, padx=4)
        ttk.Button(
            editor,
            text="현재 목표 6축을 단계 추가",
            command=self.add_sequence_step,
        ).grid(row=0, column=6, padx=(20, 4))

        sequence_frame = ttk.LabelFrame(outer, text="동작 단계", padding=10)
        sequence_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        outer.rowconfigure(3, weight=1)
        sequence_frame.rowconfigure(0, weight=1)
        sequence_frame.columnconfigure(0, weight=1)
        self.sequence_listbox = tk.Listbox(
            sequence_frame,
            height=16,
            font=("Consolas", 10),
            exportselection=False,
        )
        sequence_scroll = ttk.Scrollbar(
            sequence_frame, orient="vertical", command=self.sequence_listbox.yview
        )
        self.sequence_listbox.configure(yscrollcommand=sequence_scroll.set)
        self.sequence_listbox.grid(row=0, column=0, sticky="nsew")
        sequence_scroll.grid(row=0, column=1, sticky="ns")

        edit_buttons = ttk.Frame(sequence_frame)
        edit_buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(edit_buttons, text="선택 단계 목표 불러오기", command=self.apply_selected_sequence_step).grid(row=0, column=0, padx=3)
        ttk.Button(edit_buttons, text="위로", command=lambda: self.move_sequence_step(-1)).grid(row=0, column=1, padx=3)
        ttk.Button(edit_buttons, text="아래로", command=lambda: self.move_sequence_step(1)).grid(row=0, column=2, padx=3)
        ttk.Button(edit_buttons, text="삭제", command=self.delete_sequence_step).grid(row=0, column=3, padx=3)
        ttk.Button(edit_buttons, text="전체 삭제", command=self.clear_sequence_steps).grid(row=0, column=4, padx=3)

        controls = ttk.LabelFrame(outer, text="저장 및 실행", padding=10)
        controls.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="시퀀스 저장", command=self.save_sequence).grid(row=0, column=0, padx=4)
        ttk.Button(controls, text="시퀀스 불러오기", command=self.load_sequence).grid(row=0, column=1, padx=4)
        self.sequence_start_btn = ttk.Button(
            controls, text="시퀀스 실행", command=self.start_sequence
        )
        self.sequence_start_btn.grid(row=0, column=2, padx=(20, 4))
        self.sequence_stop_btn = ttk.Button(
            controls, text="시퀀스 중지 + 토크 OFF", command=self.stop_sequence, state="disabled"
        )
        self.sequence_stop_btn.grid(row=0, column=3, padx=4)
        ttk.Button(controls, text="기록 폴더 열기", command=self.open_output_folder).grid(row=0, column=4, padx=(20, 4))

        ttk.Label(
            outer,
            textvariable=self.sequence_status_var,
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=5, column=0, sticky="w", pady=(2, 4))
        ttk.Label(
            outer,
            text=f"이동 기록: {MOTION_LOG_PATH.name}",
            foreground="#5f4a00",
        ).grid(row=6, column=0, sticky="w")

    def _build_range_tab(self, outer: ttk.Frame) -> None:
        outer.columnconfigure(0, weight=1)
        ttk.Label(
            outer,
            text="관절별 프로그램 허용범위",
            font=("Malgun Gothic", 17, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "연결 전에도 저장할 수 있습니다. 팔로워가 연결된 경우에는 토크 OFF에서 변경하세요. "
                "저장한 범위가 수동 이동·시퀀스·리더암 조작의 유일한 프로그램 기준입니다."
            ),
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        table = ttk.LabelFrame(outer, text="최소·최대 PULSE", padding=10)
        table.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        headers = ("관절", "기본 자유범위", "현재 적용범위", "새 최소", "새 최대")
        for column, label in enumerate(headers):
            ttk.Label(table, text=label, font=("Malgun Gothic", 10, "bold")).grid(
                row=0, column=column, padx=10, pady=5
            )
        for row, spec in enumerate(self.specs, start=1):
            default_ranges = self._default_ranges_for(spec)
            active_ranges = self._ranges_for(spec)
            low, high = active_ranges[0] if active_ranges else (0, 4095)
            self.range_min_vars[spec.name] = tk.StringVar(value=str(low))
            self.range_max_vars[spec.name] = tk.StringVar(value=str(high))
            self.range_active_vars[spec.name] = tk.StringVar(
                value=ranges_text(active_ranges) if active_ranges else "교정 필요"
            )
            ttk.Label(table, text=spec.label, width=16).grid(
                row=row, column=0, sticky="w", padx=10, pady=6
            )
            ttk.Label(
                table,
                text=ranges_text(default_ranges) if default_ranges else "교정 필요",
                width=20,
            ).grid(row=row, column=1, padx=10)
            ttk.Label(
                table,
                textvariable=self.range_active_vars[spec.name],
                width=20,
            ).grid(row=row, column=2, padx=10)
            ttk.Entry(
                table, textvariable=self.range_min_vars[spec.name], width=12, justify="center"
            ).grid(row=row, column=3, padx=10)
            ttk.Entry(
                table, textvariable=self.range_max_vars[spec.name], width=12, justify="center"
            ).grid(row=row, column=4, padx=10)

        controls = ttk.LabelFrame(outer, text="저장과 복원", padding=10)
        controls.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(
            controls,
            text="내 허용범위 저장",
            command=self.save_range_overrides,
        ).grid(row=0, column=0, padx=5)
        ttk.Button(
            controls,
            text="전체 0~4095로 복원",
            command=self.reset_range_overrides,
        ).grid(row=0, column=1, padx=5)
        ttk.Button(
            controls,
            text="현재 적용값 다시 불러오기",
            command=self.refresh_range_editor,
        ).grid(row=0, column=2, padx=5)
        ttk.Label(
            outer,
            textvariable=self.range_settings_status_var,
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=4, column=0, sticky="w", pady=(2, 4))
        ttk.Label(
            outer,
            text=(
                "프로그램은 기존 실측범위·현재위치·집게 교정값·EEPROM 범위로 저장을 거부하지 않습니다. "
                "모터 EEPROM과 물리적 한계는 별개이며 자동으로 변경되지 않습니다."
            ),
            foreground="#8a3b00",
        ).grid(row=5, column=0, sticky="w", pady=(6, 0))

    def _require_range_edit_ready(self) -> PulseBus | None:
        if self.pulse_bus and self.pulse_bus.connected and self.pulse_bus.torque_on:
            raise RuntimeError("팔을 받치고 팔로워 토크를 먼저 끄세요.")
        if self.teleop_running or (self.motion_thread and self.motion_thread.is_alive()):
            raise RuntimeError("진행 중인 이동을 먼저 중지하세요.")
        return self.pulse_bus

    def refresh_range_editor(self) -> None:
        for spec in self.specs:
            ranges = self._ranges_for(spec)
            if not ranges:
                self.range_active_vars[spec.name].set("교정 필요")
                continue
            low, high = ranges[0]
            self.range_min_vars[spec.name].set(str(low))
            self.range_max_vars[spec.name].set(str(high))
            self.range_active_vars[spec.name].set(ranges_text(ranges))
            if spec.name in self.limit_vars:
                self.limit_vars[spec.name].set(ranges_text(ranges))

    def save_range_overrides(self) -> None:
        try:
            self._require_range_edit_ready()
            new_ranges: dict[str, tuple[tuple[int, int], ...]] = {}
            for spec in self.specs:
                low, high = validate_range_pair(
                    self.range_min_vars[spec.name].get(),
                    self.range_max_vars[spec.name].get(),
                )
                new_ranges[spec.name] = ((low, high),)

            summary = "\n".join(
                f"{spec.label}: {ranges_text(new_ranges[spec.name])}" for spec in self.specs
            )
            if not messagebox.askyesno(
                "프로그램 허용범위 저장",
                summary
                + "\n\n위 값이 프로그램의 유일한 허용범위가 됩니다. "
                "현재위치·교정값·EEPROM과 비교하지 않고 저장할까요?",
            ):
                return
            payload = {
                "format": RANGE_OVERRIDE_FORMAT,
                "ranges": {
                    name: [ranges[0][0], ranges[0][1]]
                    for name, ranges in new_ranges.items()
                },
            }
            temporary_path = RANGE_OVERRIDE_PATH.with_suffix(".json.tmp")
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary_path.replace(RANGE_OVERRIDE_PATH)
            self.range_overrides = new_ranges
            self.range_override_load_error = None
            self.refresh_range_editor()
            self._refresh_wrist_homing_ui()
            self._refresh_gripper_ui()
            self.range_settings_status_var.set(
                f"허용범위 저장 완료: {RANGE_OVERRIDE_PATH.name} · EEPROM 변경 없음"
            )
            self._set_status("사용자 지정 프로그램 허용범위 저장 완료")
        except Exception as exc:
            self._show_error(f"허용범위 저장 실패: {exc}")

    def reset_range_overrides(self) -> None:
        try:
            self._require_range_edit_ready()
            if not messagebox.askyesno(
                "기본 범위 복원",
                "저장한 사용자 범위를 지우고 v21 기본 자유범위 0~4095로 복원할까요?\n"
                "모터 EEPROM은 변경하지 않습니다.",
            ):
                return
            RANGE_OVERRIDE_PATH.unlink(missing_ok=True)
            self.range_overrides = {}
            self.range_override_load_error = None
            self.refresh_range_editor()
            self._refresh_wrist_homing_ui()
            self._refresh_gripper_ui()
            self.range_settings_status_var.set("전체 자유범위 0~4095 복원 완료 · EEPROM 변경 없음")
            self._set_status("전체 프로그램 허용범위 0~4095 복원 완료")
        except Exception as exc:
            self._show_error(f"기본 범위 복원 실패: {exc}")

    def _build_leader_tab(self, outer: ttk.Frame) -> None:
        outer.columnconfigure(0, weight=1)
        ttk.Label(
            outer,
            text="카메라 없는 리더암 텔레오퍼레이션",
            font=("Malgun Gothic", 17, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=(
                "리더암의 시작 자세 대비 상대 이동량을 팔로워에 전달합니다. "
                "팔로워의 기존 손목 영점·집게 교정·실측 안전범위는 변경하지 않습니다."
            ),
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))

        connection = ttk.LabelFrame(outer, text="리더암 연결과 운전", padding=10)
        connection.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(connection, text="리더 Port").grid(row=0, column=0, padx=4)
        ttk.Entry(connection, textvariable=self.leader_port_var, width=10).grid(
            row=0, column=1, padx=4
        )
        self.leader_connect_btn = ttk.Button(
            connection, text="리더 연결", command=self.connect_leader_async
        )
        self.leader_connect_btn.grid(row=0, column=2, padx=4)
        ttk.Label(connection, text="이동 배율").grid(row=0, column=3, padx=(20, 4))
        teleop = self.config["teleoperation"]
        ttk.Spinbox(
            connection,
            from_=float(teleop["minimum_scale"]),
            to=float(teleop["maximum_scale"]),
            increment=0.1,
            textvariable=self.teleop_scale_var,
            width=7,
        ).grid(row=0, column=4, padx=4)
        self.teleop_start_btn = ttk.Button(
            connection,
            text="기준 자세 저장 + 리더 조작 시작",
            command=self.start_teleoperation,
            state="disabled",
        )
        self.teleop_start_btn.grid(row=0, column=5, padx=(20, 4))
        self.teleop_stop_btn = ttk.Button(
            connection,
            text="리더 조작 중지 + 현재 자세 유지",
            command=self.stop_teleoperation,
            state="disabled",
        )
        self.teleop_stop_btn.grid(row=0, column=6, padx=4)
        ttk.Button(
            connection,
            text="긴급 정지 + 팔로워 토크 OFF",
            command=self.emergency_stop,
        ).grid(row=0, column=7, padx=(20, 4))
        ttk.Label(connection, text="추종 모드").grid(row=1, column=0, padx=4, pady=(8, 0))
        mode_combo = ttk.Combobox(
            connection,
            textvariable=self.teleop_mode_var,
            values=("1:1 빠른 추종", "안전 추종"),
            state="readonly",
            width=10,
        )
        mode_combo.grid(row=1, column=1, padx=4, pady=(8, 0))
        mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_teleop_mode())
        ttk.Label(
            connection,
            text="1:1 직접 추종: 25Hz·배율 1.0·속도값 0(모터 최대) · 안전 추종: 제한 적용",
            foreground="#5f4a00",
        ).grid(row=1, column=2, columnspan=6, sticky="w", padx=4, pady=(8, 0))
        ttk.Label(
            connection,
            textvariable=self.leader_status_var,
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=4, pady=(8, 0))

        axes = ttk.LabelFrame(outer, text="리더 입력 축", padding=10)
        axes.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        headers = ("관절", "리더 PULSE", "팔로워 PULSE", "전송 목표", "사용", "방향 반전")
        for column, label in enumerate(headers):
            ttk.Label(axes, text=label, font=("Malgun Gothic", 10, "bold")).grid(
                row=0, column=column, padx=8, pady=4
            )
        for row, spec in enumerate(self.specs, start=1):
            self.leader_position_vars[spec.name] = tk.StringVar(value="----")
            self.teleop_target_vars[spec.name] = tk.StringVar(value="----")
            ttk.Label(axes, text=spec.label, width=16).grid(
                row=row, column=0, sticky="w", padx=8, pady=5
            )
            ttk.Label(axes, textvariable=self.leader_position_vars[spec.name], width=12).grid(
                row=row, column=1, padx=8
            )
            ttk.Label(axes, textvariable=self.position_vars[spec.name], width=12).grid(
                row=row, column=2, padx=8
            )
            ttk.Label(axes, textvariable=self.teleop_target_vars[spec.name], width=12).grid(
                row=row, column=3, padx=8
            )
            ttk.Checkbutton(axes, variable=self.teleop_enabled_vars[spec.name]).grid(
                row=row, column=4, padx=8
            )
            ttk.Checkbutton(axes, variable=self.teleop_reverse_vars[spec.name]).grid(
                row=row, column=5, padx=8
            )

        safety = ttk.LabelFrame(outer, text="시작 전 확인", padding=10)
        safety.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(
            safety,
            text=(
                "1) 팔로워 COM3 연결 및 토크 ON  2) 리더 COM4 연결  "
                "3) 두 팔을 안전한 중앙 자세에 배치  4) 처음에는 배율 0.5와 한 축만 사용"
            ),
            foreground="#7a2e00",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            safety,
            text=(
                "방향이 반대인 축은 즉시 중지한 뒤 '방향 반전'을 선택하세요. "
                "진동·이상음·통신 오류·저전압·과열 시 팔로워 토크를 자동으로 끕니다."
            ),
            foreground="#8a3b00",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            outer,
            textvariable=self.teleop_status_var,
            font=("Malgun Gothic", 10, "bold"),
        ).grid(row=5, column=0, sticky="w", pady=(2, 4))

    def _spin(self, parent, variable, low, high, row: int, col: int) -> None:
        ttk.Spinbox(parent, from_=low, to=high, increment=1, textvariable=variable, width=8).grid(
            row=row, column=col, padx=4, pady=(7, 0) if row else 0
        )

    def _limit_text(self, spec: JointSpec) -> str:
        ranges = self._ranges_for(spec)
        if not ranges:
            return "교정 필요"
        return ranges_text(ranges)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _load_wrist_homing_state(self) -> None:
        if not self.wrist_homing_path.exists():
            self.wrist_homing_applied = False
            self.wrist_homing_state = "legacy"
            return
        try:
            data = json.loads(self.wrist_homing_path.read_text(encoding="utf-8"))
            status = str(data.get("status", "legacy"))
            self.wrist_homing_state = status
            self.wrist_homing_applied = status == "applied"
        except Exception:
            self.wrist_homing_applied = False
            self.wrist_homing_state = "invalid"

    def _wrist_ranges(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (int(low), int(high))
            for low, high in self.wrist_homing_settings["continuous_ranges"]
        )

    def _refresh_wrist_homing_ui(self) -> None:
        if not hasattr(self, "wrist_homing_var"):
            return
        wrist_range = ranges_text(self._wrist_ranges())
        if self.wrist_homing_applied:
            text = f"영점 재설정 완료 · 물리적 중앙 2048 · 안전 허용범위 {wrist_range}"
        elif self.wrist_homing_state == "pending":
            text = "이전 영점 작업이 완료되지 않았습니다 · 현재 영점 확인 후 원래값 복원을 권장"
        elif self.wrist_homing_state == "invalid":
            text = "손목 영점 백업 파일 오류 · 자동 변경하지 않음"
        else:
            text = f"안전 허용범위 {wrist_range} · 사용 전 현재 중앙을 2048로 설정해야 함"
        self.wrist_homing_var.set(text)
        if hasattr(self, "limit_vars") and self.wrist_name in self.limit_vars:
            self.limit_vars[self.wrist_name].set(
                ranges_text(self._ranges_for(self.by_name[self.wrist_name]))
            )

    def _set_wrist_homing_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.read_wrist_homing_btn.configure(state=state)
        self.apply_wrist_homing_btn.configure(state=state)
        self.restore_wrist_homing_btn.configure(state=state)

    def show_wrist_homing(self) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            position = pulse_bus.read_positions()[self.wrist_name]
            offset = pulse_bus.read_homing_offset(self.wrist_name)
            mode = (
                f"안전범위 {ranges_text(self._wrist_ranges())} 적용 완료"
                if self.wrist_homing_applied
                else "연속범위 적용 전"
            )
            messagebox.showinfo(
                "5번 손목 현재 영점",
                f"현재 PULSE: {position}\nHoming Offset: {offset}\n프로그램 상태: {mode}",
            )
        except Exception as exc:
            self._show_error(f"손목 영점 읽기 실패: {exc}")

    def apply_wrist_half_turn_homing(self) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            if self.wrist_homing_applied:
                raise RuntimeError("이미 손목 중앙을 2048로 재설정했습니다. 다시 적용하지 마세요.")
            current = pulse_bus.read_positions()[self.wrist_name]
            original_offset = pulse_bus.read_homing_offset(self.wrist_name)
            question = (
                "팔을 받치고 토크 OFF인지 확인하세요.\n\n"
                f"현재 손목 PULSE {current}\n현재 Homing Offset {original_offset}\n\n"
                "PULSE 숫자와 관계없이 지금 손목의 물리적 위치를 정확한 회전 중앙으로 보고 "
                "2048로 재설정할까요?\n"
                "이 작업은 모터 5번 EEPROM을 한 번 변경합니다."
            )
            if not messagebox.askyesno("5번 손목 중앙 영점 재설정", question):
                return
            pending = {
                "format": "carepack-so101-wrist-homing-v1",
                "status": "pending",
                "motor_name": self.wrist_name,
                "original_homing_offset": original_offset,
                "position_before": current,
            }
            self.wrist_homing_path.write_text(
                json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            try:
                result = pulse_bus.set_half_turn_homing(self.wrist_name)
                expected = int(self.wrist_homing_settings["expected_center_raw"])
                tolerance = int(self.wrist_homing_settings["verification_tolerance_pulse"])
                if abs(result["after_position"] - expected) > tolerance:
                    raise RuntimeError(
                        f"재설정 후 위치가 {result['after_position']}입니다. "
                        f"예상 {expected}±{tolerance} 검증에 실패했습니다."
                    )
            except Exception:
                try:
                    pulse_bus.write_homing_offset(self.wrist_name, original_offset)
                    pending["status"] = "restored_after_failure"
                    self.wrist_homing_path.write_text(
                        json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except Exception:
                    pass
                raise
            applied = {
                **pending,
                "status": "applied",
                "new_homing_offset": result["after_offset"],
                "position_after": result["after_position"],
                "continuous_range": self.wrist_homing_settings["continuous_ranges"][0],
            }
            self.wrist_homing_path.write_text(
                json.dumps(applied, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.wrist_homing_applied = True
            self.wrist_homing_state = "applied"
            self._refresh_wrist_homing_ui()
            positions = pulse_bus.read_positions()
            self._update_positions(positions, copy_targets=True)
            self._clear_axis_selection()
            wrist_range = ranges_text(self._wrist_ranges())
            self._set_status(
                f"5번 손목 중앙=2048 재설정 완료 · 안전범위 {wrist_range} 적용"
            )
            messagebox.showinfo(
                "손목 영점 완료",
                f"현재 손목 {positions[self.wrist_name]} PULSE\n"
                f"이제 손목 안전범위는 {wrist_range}이며 중간에 0/4095가 없습니다.",
            )
        except Exception as exc:
            self._show_error(f"손목 영점 재설정 실패: {exc}")

    def restore_wrist_homing(self) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            if not self.wrist_homing_path.exists():
                raise RuntimeError("복원할 손목 영점 백업 파일이 없습니다.")
            data = json.loads(self.wrist_homing_path.read_text(encoding="utf-8"))
            original_offset = int(data["original_homing_offset"])
            if not messagebox.askyesno(
                "원래 손목 영점 복원",
                f"5번 Homing Offset을 {original_offset}(으)로 복원할까요?\n"
                "팔을 받치고 토크 OFF 상태를 유지하세요.",
            ):
                return
            verified = pulse_bus.write_homing_offset(self.wrist_name, original_offset)
            data["status"] = "restored"
            data["restored_homing_offset"] = verified
            self.wrist_homing_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.wrist_homing_applied = False
            self.wrist_homing_state = "restored"
            self._refresh_wrist_homing_ui()
            positions = pulse_bus.read_positions()
            self._update_positions(positions, copy_targets=True)
            self._clear_axis_selection()
            self._set_status("5번 손목 원래 영점 복원 완료 · 토크 OFF")
            messagebox.showinfo("복원 완료", f"Homing Offset {verified} 복원 및 읽기 검증 완료")
        except Exception as exc:
            self._show_error(f"손목 영점 복원 실패: {exc}")

    def apply_preset(self) -> None:
        profile = self._profile_from_config(self.profile_var.get())
        self.arm_speed_var.set(profile.arm_speed)
        self.arm_accel_var.set(profile.arm_acceleration)
        self.gripper_speed_var.set(profile.gripper_speed)
        self.gripper_accel_var.set(profile.gripper_acceleration)
        self._set_status(f"{self.config['profiles'][self.profile_var.get()]['label']} 프리셋을 불러옴")

    def _validated_profile(self) -> MotionProfile:
        values = {
            "arm_speed": int(self.arm_speed_var.get()),
            "arm_acceleration": int(self.arm_accel_var.get()),
            "gripper_speed": int(self.gripper_speed_var.get()),
            "gripper_acceleration": int(self.gripper_accel_var.get()),
        }
        for key, value in values.items():
            low, high = self.config["profile_limits"][key]
            if not int(low) <= value <= int(high):
                raise ValueError(f"{key}: {value}는 허용범위 {low}~{high} 밖입니다.")
        return MotionProfile(**values)

    def connect_async(self) -> None:
        if self.pulse_bus and self.pulse_bus.connected:
            self.disconnect()
            return
        self.connect_btn.configure(state="disabled")
        self._set_status(f"{self.port_var.get()}에서 모터 ID 1~6 연결 중...")
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self) -> None:
        pulse_bus: PulseBus | None = None
        try:
            pulse_bus = PulseBus(self.port_var.get().strip(), self.specs)
            pulse_bus.connect()
            positions = pulse_bus.read_positions()
            telemetry = pulse_bus.read_telemetry()
            self.pulse_bus = pulse_bus
            self.events.put(("connected", (positions, telemetry)))
        except Exception as exc:
            if pulse_bus is not None:
                try:
                    pulse_bus.disconnect()
                except Exception:
                    pass
            self.pulse_bus = None
            self.events.put(("error", f"연결 실패: {exc}"))

    def _start_monitor(self) -> None:
        assert self.pulse_bus is not None
        pulse_bus = self.pulse_bus
        stop = threading.Event()
        self.monitor_stop = stop
        self.monitor_thread = threading.Thread(target=self._monitor_worker, args=(pulse_bus, stop), daemon=True)
        self.monitor_thread.start()

    def _monitor_worker(self, pulse_bus: PulseBus, stop: threading.Event) -> None:
        interval = 1.0 / float(self.config.get("monitor_hz", 4.0))
        failures = 0
        next_full = 0.0
        while not stop.is_set() and pulse_bus.connected:
            if (
                (self.motion_thread and self.motion_thread.is_alive())
                or (self.teleop_thread and self.teleop_thread.is_alive())
            ):
                stop.wait(0.1)
                continue
            try:
                self.events.put(("positions", pulse_bus.read_positions()))
                now = time.monotonic()
                if now >= next_full:
                    self.events.put(("telemetry", pulse_bus.read_telemetry()))
                    next_full = now + 2.0
                failures = 0
            except Exception as exc:
                if stop.is_set():
                    return
                failures += 1
                if failures >= 3:
                    self.events.put(("monitor_fault", str(exc)))
                    return
            stop.wait(interval)

    def disconnect(self) -> None:
        self._abort_sequence("연결 해제")
        self.teleop_stop.set()
        self.teleop_running = False
        self.motion_stop.set()
        self.monitor_stop.set()
        if self.pulse_bus:
            try:
                self.pulse_bus.disconnect()
            except Exception as exc:
                messagebox.showwarning("연결 해제 경고", str(exc))
        self.pulse_bus = None
        self.connect_btn.configure(text="연결", state="normal")
        self.torque_btn.configure(text="토크 켜기", state="disabled")
        self.capture_btn.configure(state="disabled")
        self.move_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.gripper_open_capture_btn.configure(state="disabled")
        self.gripper_closed_capture_btn.configure(state="disabled")
        self._set_tuning_buttons(False)
        self._set_wrist_homing_buttons(False)
        self._set_status("연결 안 됨 · 토크 OFF")
        self.teleop_status_var.set("팔로워 연결이 해제되어 리더 조작을 사용할 수 없습니다.")
        self._refresh_teleop_controls()

    def recover_connection(self) -> None:
        if not messagebox.askyesno(
            "통신 복구",
            "팔을 받치세요. 모터 1~6 토크를 끄고 COM 포트를 닫은 뒤 다시 연결합니다.",
        ):
            return
        self.disconnect()
        self.root.after(500, self.connect_async)

    def _apply_teleop_mode(self) -> None:
        mode = "direct" if self.teleop_mode_var.get() == "1:1 빠른 추종" else "safe"
        settings = self.config["teleoperation"]
        if mode == "direct":
            self.teleop_scale_var.set(float(settings["direct"].get("scale", 1.0)))
            self.teleop_status_var.set(
                "1:1 직접 추종 선택 · 목표 단계/선행거리 제한 없음 · 처음에는 축 하나만 시험하세요."
            )
        else:
            self.teleop_scale_var.set(0.5)
            self.teleop_status_var.set("안전 추종 선택 · v18과 같은 저속 제한을 사용합니다.")

    def _refresh_teleop_controls(self) -> None:
        if not hasattr(self, "teleop_start_btn"):
            return
        ready = bool(
            self.pulse_bus
            and self.pulse_bus.connected
            and self.pulse_bus.torque_on
            and self.leader_bus
            and self.leader_bus.connected
            and not self.teleop_running
        )
        self.teleop_start_btn.configure(state="normal" if ready else "disabled")
        self.teleop_stop_btn.configure(
            state="normal" if self.teleop_running else "disabled"
        )

    def connect_leader_async(self) -> None:
        if self.teleop_running:
            messagebox.showinfo("리더 조작 중", "리더 조작을 먼저 중지하세요.")
            return
        if self.leader_bus and self.leader_bus.connected:
            self.disconnect_leader()
            return
        leader_port = self.leader_port_var.get().strip().upper()
        follower_port = self.port_var.get().strip().upper()
        if not leader_port:
            self._show_error("리더암 COM 포트를 입력하세요.")
            return
        if leader_port == follower_port:
            self._show_error("리더암과 팔로워암은 서로 다른 COM 포트를 사용해야 합니다.")
            return
        self.leader_connect_btn.configure(state="disabled")
        self.leader_status_var.set(f"{leader_port}에서 리더 모터 ID 1~6 연결 중...")
        threading.Thread(
            target=self._connect_leader_worker,
            args=(leader_port,),
            daemon=True,
        ).start()

    def _connect_leader_worker(self, port: str) -> None:
        leader_bus: PulseBus | None = None
        try:
            leader_bus = PulseBus(port, self.specs)
            leader_bus.connect()
            positions = leader_bus.read_positions()
            self.leader_bus = leader_bus
            self.events.put(("leader_connected", positions))
        except Exception as exc:
            if leader_bus is not None:
                try:
                    leader_bus.disconnect()
                except Exception:
                    pass
            self.leader_bus = None
            self.events.put(("leader_error", f"리더암 연결 실패: {exc}"))

    def disconnect_leader(self) -> None:
        self.teleop_stop.set()
        if self.leader_bus:
            try:
                self.leader_bus.disconnect()
            except Exception as exc:
                messagebox.showwarning("리더 연결 해제 경고", str(exc))
        self.leader_bus = None
        self.teleop_running = False
        self.leader_connect_btn.configure(text="리더 연결", state="normal")
        self.leader_status_var.set("리더암 연결 안 됨 · 토크 OFF")
        for variable in self.leader_position_vars.values():
            variable.set("----")
        for variable in self.teleop_target_vars.values():
            variable.set("----")
        self._refresh_teleop_controls()

    def _teleop_effective_ranges(self) -> tuple[
        dict[str, tuple[tuple[int, int], ...]], list[str]
    ]:
        if not self.pulse_bus:
            raise RuntimeError("팔로워암이 연결되지 않았습니다.")
        diagnostics = self.pulse_bus.read_motor_diagnostics()
        effective: dict[str, tuple[tuple[int, int], ...]] = {}
        warnings: list[str] = []
        for spec in self.specs:
            values = diagnostics[spec.name]
            if int(values["operating_mode"]) != 0:
                raise RuntimeError(
                    f"{spec.label} Operating Mode가 {values['operating_mode']}입니다. "
                    "MODE 0에서만 리더 조작할 수 있습니다."
                )
            program_ranges = self._ranges_for(spec)
            if not program_ranges:
                raise RuntimeError(f"{spec.label} 안전범위가 없습니다. 먼저 교정하세요.")
            program_low = min(low for low, _high in program_ranges)
            program_high = max(high for _low, high in program_ranges)
            motor_low = int(values["min_position"])
            motor_high = int(values["max_position"])
            if program_low < motor_low or program_high > motor_high:
                warnings.append(
                    f"{spec.label}: 사용자 {program_low}~{program_high}, "
                    f"EEPROM 참고값 {motor_low}~{motor_high} · 자동 축소하지 않음"
                )
            effective[spec.name] = program_ranges
        return effective, warnings

    def start_teleoperation(self) -> None:
        if self.teleop_running:
            return
        if not self.pulse_bus or not self.pulse_bus.connected or not self.pulse_bus.torque_on:
            messagebox.showinfo("팔로워 준비 필요", "수동 탭에서 팔로워를 연결하고 토크를 켜세요.")
            return
        if not self.leader_bus or not self.leader_bus.connected:
            messagebox.showinfo("리더 준비 필요", "리더암을 먼저 연결하세요.")
            return
        if self.motion_thread and self.motion_thread.is_alive():
            messagebox.showinfo("이동 중", "현재 프로파일 이동이 끝난 뒤 시작하세요.")
            return
        if self.sequence_running:
            messagebox.showinfo("시퀀스 실행 중", "시퀀스를 먼저 중지하세요.")
            return
        try:
            settings = self.config["teleoperation"]
            mode = (
                "direct"
                if self.teleop_mode_var.get() == "1:1 빠른 추종"
                else "safe"
            )
            scale = (
                float(settings["direct"].get("scale", 1.0))
                if mode == "direct"
                else float(self.teleop_scale_var.get())
            )
            self.teleop_scale_var.set(scale)
            if not float(settings["minimum_scale"]) <= scale <= float(
                settings["maximum_scale"]
            ):
                raise ValueError(
                    f"이동 배율은 {settings['minimum_scale']}~{settings['maximum_scale']}여야 합니다."
                )
            enabled_names = {
                spec.name for spec in self.specs if self.teleop_enabled_vars[spec.name].get()
            }
            if not enabled_names:
                raise ValueError("리더 입력으로 사용할 축을 하나 이상 선택하세요.")
            directions = {
                spec.name: -1 if self.teleop_reverse_vars[spec.name].get() else 1
                for spec in self.specs
            }
            effective_ranges, range_warnings = self._teleop_effective_ranges()
            leader_anchors = self.leader_bus.read_positions()
            follower_anchors = self.pulse_bus.read_positions()
            effective_ranges = {
                spec.name: expand_ranges_to_include(
                    effective_ranges[spec.name], follower_anchors[spec.name]
                )
                for spec in self.specs
            }
            profile = self._validated_profile()
        except Exception as exc:
            self._show_error(f"리더 조작 시작 불가: {exc}")
            return

        if not messagebox.askyesno(
            "리더 조작 시작",
            f"현재 두 팔의 자세를 기준점으로 저장합니다.\n"
            f"모드 {self.teleop_mode_var.get()} · 사용 축 {len(enabled_names)}개 · "
            f"이동 배율 {scale:g}\n\n"
            "리더암을 아주 조금씩 움직일 준비가 되었나요?",
        ):
            return
        self.teleop_stop.clear()
        self.teleop_running = True
        self.move_btn.configure(state="disabled")
        self.capture_btn.configure(state="disabled")
        self.sequence_start_btn.configure(state="disabled")
        self.teleop_start_btn.configure(state="disabled")
        self.teleop_stop_btn.configure(state="normal")
        warning_text = " · ".join(range_warnings)
        self.teleop_status_var.set(
            "리더 조작 실행 중 · 작은 움직임부터 시험"
            + (f" · {warning_text}" if warning_text else "")
        )
        self.teleop_thread = threading.Thread(
            target=self._teleoperation_worker,
            args=(
                leader_anchors,
                follower_anchors,
                directions,
                enabled_names,
                scale,
                effective_ranges,
                profile,
                mode,
            ),
            daemon=True,
        )
        self.teleop_thread.start()

    def _teleoperation_worker(
        self,
        leader_anchors: dict[str, int],
        follower_anchors: dict[str, int],
        directions: dict[str, int],
        enabled_names: set[str],
        scale: float,
        effective_ranges: dict[str, tuple[tuple[int, int], ...]],
        profile: MotionProfile,
        mode: str,
    ) -> None:
        assert self.pulse_bus is not None and self.leader_bus is not None
        follower_bus = self.pulse_bus
        leader_bus = self.leader_bus
        settings = self.config["teleoperation"]
        direct_settings = settings.get("direct", {})
        direct_mode = mode == "direct"
        interval = 1.0 / float(
            direct_settings["control_hz"] if direct_mode else settings["control_hz"]
        )
        input_jump_limit = int(settings["input_jump_limit_pulse"])
        # These limits belong to safe mode only. Direct mode bypasses them.
        step_settings = settings["max_step_pulse"]
        lead_settings = settings["max_command_lead_pulse"]
        max_steps = {name: int(value) for name, value in step_settings.items()}
        max_leads = {
            name: int(value) for name, value in lead_settings.items()
        }
        previous_raw = dict(leader_anchors)
        leader_unwrapped = dict(leader_anchors)
        previous_commands = dict(follower_anchors)
        telemetry_interval = float(settings["telemetry_interval_seconds"])
        next_telemetry = 0.0
        filter_size = int(self.config["safety"].get("telemetry_filter_samples", 3))
        voltage_history = {spec.name: deque(maxlen=filter_size) for spec in self.specs}
        temperature_history = {spec.name: deque(maxlen=filter_size) for spec in self.specs}

        if direct_mode:
            speeds = {name: int(value) for name, value in direct_settings["speeds"].items()}
            accelerations = {
                name: int(value) for name, value in direct_settings["accelerations"].items()
            }
        else:
            speeds = {
                spec.name: profile.gripper_speed if spec.motor_id == 6 else profile.arm_speed
                for spec in self.specs
            }
            accelerations = {
                spec.name: (
                    profile.gripper_acceleration
                    if spec.motor_id == 6
                    else profile.arm_acceleration
                )
                for spec in self.specs
            }
            speeds, accelerations = apply_axis_motion_limits(
                speeds, accelerations, self.config.get("axis_motion", {})
            )
        try:
            while not self.teleop_stop.is_set():
                loop_started = time.monotonic()
                leader_raw = leader_bus.read_positions()
                follower_positions = follower_bus.read_positions()
                for spec in self.specs:
                    name = spec.name
                    unwrapped = unwrap_raw_position(
                        previous_raw[name], leader_unwrapped[name], leader_raw[name]
                    )
                    step = unwrapped - leader_unwrapped[name]
                    if abs(step) > input_jump_limit:
                        raise RuntimeError(
                            f"{spec.label} 리더 입력이 한 번에 {step:+d} PULSE 변했습니다."
                        )
                    leader_unwrapped[name] = unwrapped
                    previous_raw[name] = leader_raw[name]

                requested = map_relative_teleop_targets(
                    leader_unwrapped,
                    leader_anchors,
                    follower_anchors,
                    directions,
                    scale,
                    effective_ranges,
                    enabled_names,
                )
                commands = select_teleop_targets(
                    direct_mode,
                    requested,
                    previous_commands,
                    follower_positions,
                    max_steps,
                    max_leads,
                    effective_ranges,
                )
                follower_bus.command_profiled(commands, speeds, accelerations)
                previous_commands = commands
                now = time.monotonic()
                if now >= next_telemetry:
                    telemetry = follower_bus.read_telemetry()
                    self._check_telemetry(telemetry, voltage_history, temperature_history)
                    self.events.put(("telemetry", telemetry))
                    next_telemetry = now + telemetry_interval
                self.events.put(
                    (
                        "teleop_positions",
                        {
                            "leader": leader_raw,
                            "follower": follower_positions,
                            "targets": commands,
                        },
                    )
                )
                elapsed = time.monotonic() - loop_started
                self.teleop_stop.wait(max(0.0, interval - elapsed))
            held = follower_bus.hold_current_position()
            self.events.put(("teleop_stopped", held))
        except Exception as exc:
            if self.teleop_stop.is_set():
                self.events.put(("teleop_cancelled", str(exc)))
                return
            try:
                follower_bus.disable_torque()
            finally:
                self.events.put(("teleop_fault", str(exc)))

    def stop_teleoperation(self) -> None:
        if not self.teleop_running:
            return
        self.teleop_status_var.set("리더 조작 중지 요청 · 현재 자세 유지 준비 중...")
        self.teleop_stop.set()

    def _finish_teleop_ui(self, torque_on: bool) -> None:
        self.teleop_running = False
        self.teleop_stop_btn.configure(state="disabled")
        self.move_btn.configure(state="normal" if torque_on else "disabled")
        self.capture_btn.configure(state="normal" if self.pulse_bus else "disabled")
        self.sequence_start_btn.configure(state="normal")
        self._refresh_teleop_controls()

    def _set_tuning_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.read_tuning_btn.configure(state=state)
        self.apply_tuning_btn.configure(state=state)
        self.apply_tuning_stage2_btn.configure(state=state)
        self.restore_tuning_btn.configure(
            state=state
        )
        if hasattr(self, "motor_diagnostic_btn"):
            self.motor_diagnostic_btn.configure(state=state)

    def _require_torque_off_for_tuning(self) -> PulseBus:
        if not self.pulse_bus or not self.pulse_bus.connected:
            raise RuntimeError("먼저 모터 ID 1~6에 연결하세요.")
        if self.pulse_bus.torque_on:
            raise RuntimeError("팔을 받친 뒤 토크를 먼저 끄세요.")
        return self.pulse_bus

    def _format_loaded_axis_tuning(self, values: dict[str, dict[str, int]]) -> str:
        lines = []
        for name in self.loaded_joint_names:
            value = values[name]
            lines.append(
                f"{self.by_name[name].label}: "
                f"P{value['p']} / D{value['d']} / I{value['i']} / Punch{value['punch']}"
            )
        return "\n".join(lines)

    def show_loaded_axis_tuning(self) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            values = pulse_bus.read_tuning(self.loaded_joint_names)
            messagebox.showinfo(
                "2·3축 현재 설정",
                self._format_loaded_axis_tuning(values),
            )
        except Exception as exc:
            self._show_error(f"튜닝값 읽기 실패: {exc}")

    def show_motor_diagnostics(self) -> None:
        """Show all motor EEPROM limits without writing to the motors."""
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            values = pulse_bus.read_motor_diagnostics()
            lines: list[str] = []
            warnings: list[str] = []
            for spec in self.specs:
                value = values[spec.name]
                ranges = self._ranges_for(spec)
                requested_low = min(low for low, _high in ranges) if ranges else None
                requested_high = max(high for _low, high in ranges) if ranges else None
                internal_low = value["min_position"]
                internal_high = value["max_position"]
                mode = value["operating_mode"]
                verdict = "정상"
                if mode != 0:
                    verdict = "MODE 확인 필요"
                    warnings.append(f"{spec.label}: Operating Mode {mode}")
                elif (
                    requested_low is not None
                    and requested_high is not None
                    and (internal_low > requested_low or internal_high < requested_high)
                ):
                    verdict = "내부 제한이 더 좁음"
                    warnings.append(
                        f"{spec.label}: 프로그램 {requested_low}~{requested_high}, "
                        f"모터 {internal_low}~{internal_high}"
                    )
                lines.append(
                    f"{spec.label} · MIN {internal_low} / MAX {internal_high} / "
                    f"MODE {mode} / 현재 {value['present_position']} / {verdict}"
                )
            text = "\n".join(lines)
            if warnings:
                text += "\n\n주의\n" + "\n".join(warnings)
            self.motor_diagnostic_var.set(text)
            self._set_status("1~6번 내부 제한 진단 완료 · 설정은 변경하지 않음")
            messagebox.showinfo("모터 내부 제한 진단", text)
        except Exception as exc:
            self._show_error(f"모터 내부 제한 읽기 실패: {exc}")

    def apply_loaded_axis_tuning(self, stage: str) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            current = pulse_bus.read_tuning(self.loaded_joint_names)
            if stage not in self.loaded_tuning_targets:
                raise ValueError(f"알 수 없는 보강 단계: {stage}")
            stage_label = "1단계" if stage == "stage1" else "2단계"
            target = {
                name: dict(self.loaded_tuning_targets[stage]) for name in self.loaded_joint_names
            }
            question = (
                "현재 설정\n"
                + self._format_loaded_axis_tuning(current)
                + f"\n\n{stage_label} 보강 설정\n"
                + self._format_loaded_axis_tuning(target)
                + "\n\n토크 OFF 상태에서 적용할까요?"
            )
            if not messagebox.askyesno(f"2·3축 {stage_label} 보강", question):
                return
            if not self.tuning_path.exists():
                recognized_tuned_values = list(self.loaded_tuning_targets.values())
                if all(current[name] in recognized_tuned_values for name in self.loaded_joint_names):
                    original = {
                        name: dict(self.loaded_tuning_baseline) for name in self.loaded_joint_names
                    }
                else:
                    original = current
                backup = {"version": 1, "motors": original}
                self.tuning_path.write_text(
                    json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            try:
                verified = pulse_bus.write_tuning(target)
            except Exception:
                try:
                    pulse_bus.write_tuning(current)
                except Exception:
                    pass
                raise
            self._set_tuning_buttons(True)
            self._set_status(f"2·3축 {stage_label} 보강 적용 및 읽기 검증 완료 · 토크 OFF")
            messagebox.showinfo(
                "적용 완료",
                self._format_loaded_axis_tuning(verified)
                + "\n\n이제 gentle에서 어깨 -60을 한 축만 시험하세요.",
            )
        except Exception as exc:
            self._show_error(f"2·3축 보강 실패: {exc}")

    def restore_loaded_axis_tuning(self) -> None:
        try:
            pulse_bus = self._require_torque_off_for_tuning()
            if self.tuning_path.exists():
                raw = json.loads(self.tuning_path.read_text(encoding="utf-8"))
                original = {
                    name: validate_tuning_values(raw["motors"][name])
                    for name in self.loaded_joint_names
                }
            else:
                original = {
                    name: dict(self.loaded_tuning_baseline) for name in self.loaded_joint_names
                }
            if not messagebox.askyesno(
                "원래값 복원",
                self._format_loaded_axis_tuning(original) + "\n\n이 값으로 복원할까요?",
            ):
                return
            verified = pulse_bus.write_tuning(original)
            self._set_status("2·3축 원래 튜닝값 복원 및 읽기 검증 완료 · 토크 OFF")
            messagebox.showinfo("복원 완료", self._format_loaded_axis_tuning(verified))
        except Exception as exc:
            self._show_error(f"원래값 복원 실패: {exc}")

    def toggle_torque(self) -> None:
        if not self.pulse_bus:
            return
        try:
            if self.pulse_bus.torque_on:
                self._abort_sequence("토크 OFF")
                self.teleop_stop.set()
                self.teleop_running = False
                self.pulse_bus.disable_torque()
                self.torque_btn.configure(text="토크 켜기")
                self.move_btn.configure(state="disabled")
                self.gripper_open_capture_btn.configure(state="normal")
                self.gripper_closed_capture_btn.configure(state="normal")
                self._set_tuning_buttons(True)
                self._set_wrist_homing_buttons(True)
                self._set_status("연결됨 · 6축 토크 OFF · 팔을 받쳐주세요")
                self.teleop_status_var.set("팔로워 토크 OFF · 리더 조작 중지")
            else:
                profile = self._validated_profile()
                if not self.wrist_homing_applied:
                    raise RuntimeError(
                        "5번 손목이 아직 연속범위로 설정되지 않았습니다. 토크 OFF에서 손목을 "
                        "물리적 중앙에 놓고 '현재 중앙을 2048로 설정'을 먼저 누르세요."
                    )
                limits = {spec.name: spec.torque_limit for spec in self.specs}
                current = self.pulse_bus.enable_torque(limits, profile)
                self._update_positions(current, copy_targets=False)
                self.torque_btn.configure(text="토크 끄기")
                self.move_btn.configure(state="normal")
                self.stop_btn.configure(state="normal")
                self.gripper_open_capture_btn.configure(state="disabled")
                self.gripper_closed_capture_btn.configure(state="disabled")
                self._set_tuning_buttons(False)
                self._set_wrist_homing_buttons(False)
                self._set_status("6축 토크 ON · 현재 자세 유지 중")
            self._refresh_teleop_controls()
        except Exception as exc:
            self._show_error(f"토크 전환 실패: {exc}")

    def capture_current(self) -> None:
        if not self.pulse_bus:
            return
        try:
            self._update_positions(self.pulse_bus.read_positions(), copy_targets=True)
            self._clear_axis_selection()
            self._set_status("현재 1~6번 PULSE를 목표값으로 복사 · 이동 선택 초기화")
        except Exception as exc:
            self._show_error(f"위치 읽기 실패: {exc}")

    def nudge_target(self, name: str, delta: int) -> None:
        try:
            current = int(self.target_vars[name].get())
        except ValueError:
            current = self.by_name[name].center or 2048
        self.target_vars[name].set(str(max(0, min(4095, current + delta))))
        self.selected_vars[name].set(True)

    def _clear_axis_selection(self) -> None:
        for variable in self.selected_vars.values():
            variable.set(False)

    def _default_ranges_for(self, spec: JointSpec) -> tuple[tuple[int, int], ...]:
        return spec.allowed_ranges or ((0, 4095),)

    def _ranges_for(self, spec: JointSpec) -> tuple[tuple[int, int], ...]:
        override = getattr(self, "range_overrides", {}).get(spec.name)
        return override if override else self._default_ranges_for(spec)

    def _validated_targets(self, current: dict[str, int]) -> tuple[dict[str, int], list[str]]:
        selected = {
            name for name, variable in self.selected_vars.items() if variable.get()
        }
        forbid_cross = {
            spec.name for spec in self.specs if spec.forbid_cross_branch
        }
        return prepare_selected_motion(
            self.specs,
            current,
            {name: variable.get() for name, variable in self.target_vars.items()},
            selected,
            {spec.name: self._ranges_for(spec) for spec in self.specs},
            forbid_cross,
        )

    def start_motion(
        self,
        skip_confirmation: bool = False,
        motion_label: str = "수동 이동",
    ) -> bool:
        if self.teleop_running:
            messagebox.showinfo("리더 조작 중", "리더 조작을 먼저 중지하세요.")
            return False
        if not self.pulse_bus or not self.pulse_bus.torque_on:
            messagebox.showinfo("토크 OFF", "팔을 받친 뒤 토크를 켜세요.")
            return False
        if self.motion_thread and self.motion_thread.is_alive():
            return False
        try:
            profile = self._validated_profile()
            current = self.pulse_bus.read_positions()
            targets, active_names = self._validated_targets(current)
        except Exception as exc:
            self._show_error(str(exc))
            return False
        moving_names = [
            name for name in active_names if targets[name] != current[name]
        ]
        if not moving_names:
            if not skip_confirmation:
                messagebox.showinfo("이동 없음", "선택한 축의 목표값이 현재값과 같습니다.")
            return False
        distances = {name: abs(targets[name] - current[name]) for name in moving_names}
        confirmation_threshold = int(
            self.config["safety"].get("large_move_confirmation_pulse", 300)
        )
        if not skip_confirmation and (len(moving_names) > 1 or any(
            distance >= confirmation_threshold for distance in distances.values()
        )):
            summary = "\n".join(
                f"{self.by_name[name].label}: {current[name]} → {targets[name]} "
                f"({targets[name] - current[name]:+d})"
                for name in moving_names
            )
            if not messagebox.askyesno(
                "선택 축 이동 확인",
                summary + "\n\n위 축만 이동할까요? 선택하지 않은 축은 현재 위치를 유지합니다.",
            ):
                return False
        self.motion_context = {
            "started": time.monotonic(),
            "mode": motion_label,
            "active_names": list(moving_names),
            "current": {name: int(current[name]) for name in moving_names},
            "targets": {name: int(targets[name]) for name in moving_names},
        }
        self.motion_stop.clear()
        self.move_btn.configure(state="disabled")
        self.capture_btn.configure(state="disabled")
        self._set_status("내장 가속·감속 프로파일 이동 시작...")
        self.motion_thread = threading.Thread(
            target=self._motion_worker,
            args=(current, targets, active_names, profile),
            daemon=True,
        )
        self.motion_thread.start()
        return True

    def _motion_worker(
        self,
        current: dict[str, int],
        targets: dict[str, int],
        active_names: list[str],
        profile: MotionProfile,
    ) -> None:
        try:
            assert self.pulse_bus is not None
            safety = self.config["safety"]
            tolerance = int(safety["completion_tolerance_pulse"])
            poll_seconds = float(safety.get("motion_poll_seconds", 0.2))
            stable_samples_required = int(safety.get("completion_stable_samples", 3))
            progress_epsilon = int(safety.get("progress_epsilon_pulse", 2))
            stall_seconds = float(safety.get("stall_seconds", 3.0))
            hard_timeout_seconds = float(safety.get("hard_timeout_seconds", 30.0))
            correction_timeout = float(safety.get("correction_timeout_seconds", 6.0))
            correction_speed = int(safety.get("correction_speed", 60))
            correction_acceleration = int(safety.get("correction_acceleration", 1))
            filter_size = int(safety.get("telemetry_filter_samples", 3))
            continuous_lift = self.config.get("continuous_lift", {})
            continuous_lift_enabled = bool(continuous_lift.get("enabled", False))
            lifting_delta_signs = {
                str(name): int(sign)
                for name, sign in continuous_lift.get("lifting_delta_sign", {}).items()
            }
            continuous_lift_minimum_move = int(
                continuous_lift.get("minimum_move_pulse", 20)
            )
            continuous_lift_lead = int(continuous_lift.get("lead_pulse", 18))
            continuous_lift_handoff = max(
                tolerance,
                int(continuous_lift.get("handoff_remaining_pulse", tolerance)),
            )
            voltage_history = {
                name: deque(maxlen=filter_size) for name in self.by_name
            }
            temperature_history = {
                name: deque(maxlen=filter_size) for name in self.by_name
            }
            distances = {name: abs(targets[name] - current[name]) for name in active_names}
            arm_distances = {name: d for name, d in distances.items() if name != "gripper"}
            speeds = scaled_speeds(arm_distances, profile.arm_speed, minimum_speed=30)
            if "gripper" in distances and distances["gripper"] > 0:
                speeds["gripper"] = profile.gripper_speed
            moving_names = list(speeds)
            if not moving_names:
                self.events.put(("motion_done", current))
                return
            accelerations = {
                name: profile.gripper_acceleration if name == "gripper" else profile.arm_acceleration
                for name in moving_names
            }
            axis_motion_settings = self.config.get("axis_motion", {})
            speeds, accelerations = apply_axis_motion_limits(
                speeds, accelerations, axis_motion_settings
            )
            move_targets = {name: targets[name] for name in moving_names}
            segmented_queues: dict[str, deque[int]] = {}
            segmented_active_targets: dict[str, int] = {}
            for name in moving_names:
                waypoints = segmented_axis_waypoints(
                    current[name], targets[name], axis_motion_settings.get(name, {})
                )
                if len(waypoints) > 1:
                    move_targets[name] = waypoints[0]
                    segmented_active_targets[name] = waypoints[0]
                    segmented_queues[name] = deque(waypoints[1:])
                    self.events.put(
                        (
                            "motion_status",
                            f"{self.by_name[name].label} 안전 구간 이동 "
                            f"1/{len(waypoints)} · 목표 {waypoints[0]}",
                        )
                    )
            continuous_lift_names: set[str] = set()
            preloaded_lift_names: set[str] = set()
            if continuous_lift_enabled:
                for name in moving_names:
                    if name in segmented_queues:
                        continue
                    lead_target = continuous_lift_target(
                        name=name,
                        start=current[name],
                        target=targets[name],
                        ranges=self._ranges_for(self.by_name[name]),
                        lifting_delta_signs=lifting_delta_signs,
                        minimum_move=continuous_lift_minimum_move,
                        lead=continuous_lift_lead,
                    )
                    if lead_target is not None:
                        move_targets[name] = lead_target
                        continuous_lift_names.add(name)
                        preloaded_lift_names.add(name)
            self.pulse_bus.command_profiled(move_targets, speeds, accelerations)
            started = time.monotonic()
            best_errors = {name: distances[name] for name in moving_names}
            last_progress = {name: started for name in moving_names}
            stable_samples = 0
            latest_positions = dict(current)
            correction_reason = ""
            while not self.motion_stop.is_set():
                telemetry = self.pulse_bus.read_telemetry()
                self._check_telemetry(telemetry, voltage_history, temperature_history)
                self.events.put(("telemetry", telemetry))
                positions = {name: values["Present_Position"] for name, values in telemetry.items()}
                latest_positions = positions
                errors = {name: abs(targets[name] - positions[name]) for name in moving_names}
                now = time.monotonic()

                # Long gravity-aided elbow moves are handed through bounded
                # intermediate goals. This avoids one large endpoint command
                # while keeping the same gentle profile and torque state.
                for name in tuple(segmented_queues):
                    segment_target = segmented_active_targets[name]
                    settings = axis_motion_settings.get(name, {})
                    handoff = max(
                        tolerance, int(settings.get("segment_handoff_pulse", tolerance))
                    )
                    move_sign = 1 if segment_target > current[name] else -1
                    remaining_signed = segment_target - positions[name]
                    if (
                        remaining_signed * move_sign <= 0
                        or abs(remaining_signed) <= handoff
                    ):
                        queue_for_axis = segmented_queues[name]
                        if queue_for_axis:
                            next_target = queue_for_axis.popleft()
                            segmented_active_targets[name] = next_target
                            self.pulse_bus.command_profiled(
                                {name: next_target},
                                {name: speeds[name]},
                                {name: accelerations[name]},
                            )
                            total = len(segmented_axis_waypoints(
                                current[name], targets[name], settings
                            ))
                            completed = total - len(queue_for_axis)
                            self.events.put(
                                (
                                    "motion_status",
                                    f"{self.by_name[name].label} 안전 구간 이동 "
                                    f"{completed}/{total} · 목표 {next_target}",
                                )
                            )
                        else:
                            del segmented_queues[name]

                # Hand the exact target back while the preloaded axis is still
                # moving. This preserves one continuous lift and removes the
                # stop/restart cycle that caused the observed vibration.
                for name in tuple(continuous_lift_names):
                    move_sign = 1 if targets[name] > current[name] else -1
                    remaining_signed = targets[name] - positions[name]
                    if (
                        remaining_signed * move_sign <= 0
                        or abs(remaining_signed) <= continuous_lift_handoff
                    ):
                        self.pulse_bus.command_profiled(
                            {name: targets[name]},
                            {name: speeds[name]},
                            {name: accelerations[name]},
                        )
                        continuous_lift_names.remove(name)
                        self.events.put(
                            (
                                "motion_status",
                                f"{self.by_name[name].label} 연속 들어 올림 · 최종 목표 진입",
                            )
                        )

                if all(error <= tolerance for error in errors.values()):
                    stable_samples += 1
                    if stable_samples >= stable_samples_required:
                        self.events.put(("motion_done", positions))
                        return
                else:
                    stable_samples = 0

                for name, error in errors.items():
                    if error <= tolerance:
                        last_progress[name] = now
                    elif error <= best_errors[name] - progress_epsilon:
                        best_errors[name] = error
                        last_progress[name] = now

                stalled = [
                    name
                    for name, error in errors.items()
                    if error > tolerance and now - last_progress[name] >= stall_seconds
                ]
                if stalled:
                    correction_reason = "진행 정지"
                    break
                if now - started >= hard_timeout_seconds:
                    correction_reason = f"최대 {hard_timeout_seconds:g}초 초과"
                    break
                self.motion_stop.wait(poll_seconds)

            if self.motion_stop.is_set():
                raise RuntimeError("사용자가 이동을 중지했습니다.")

            # One gentle correction pass is allowed only for axes still outside tolerance.
            first_errors = {
                name: abs(targets[name] - latest_positions[name]) for name in moving_names
            }
            # A preloaded lift is never restarted after it stops. If the one-pass
            # motion misses, the current pose is held and reported immediately.
            failed_names = [
                name
                for name, error in first_errors.items()
                if error > tolerance and name not in preloaded_lift_names
            ]
            if failed_names:
                self.events.put(
                    (
                        "motion_status",
                        "잔여 오차 보정 중: "
                        + ", ".join(
                            f"{self.by_name[name].label} {first_errors[name]}" for name in failed_names
                        ),
                    )
                )
                correction_targets = {name: targets[name] for name in failed_names}
                correction_speeds = {name: correction_speed for name in failed_names}
                correction_accelerations = {
                    name: correction_acceleration for name in failed_names
                }
                self.pulse_bus.command_profiled(
                    correction_targets, correction_speeds, correction_accelerations
                )
                correction_started = time.monotonic()
                stable_samples = 0
                while not self.motion_stop.is_set():
                    telemetry = self.pulse_bus.read_telemetry()
                    self._check_telemetry(telemetry, voltage_history, temperature_history)
                    self.events.put(("telemetry", telemetry))
                    positions = {
                        name: values["Present_Position"] for name, values in telemetry.items()
                    }
                    latest_positions = positions
                    errors = {
                        name: abs(targets[name] - positions[name]) for name in moving_names
                    }
                    if all(error <= tolerance for error in errors.values()):
                        stable_samples += 1
                        if stable_samples >= stable_samples_required:
                            self.events.put(("motion_done", positions))
                            return
                    else:
                        stable_samples = 0
                    if time.monotonic() - correction_started >= correction_timeout:
                        break
                    self.motion_stop.wait(poll_seconds)

            if self.motion_stop.is_set():
                raise RuntimeError("사용자가 이동을 중지했습니다.")

            held_positions = self.pulse_bus.hold_current_position()
            final_errors = {
                name: abs(targets[name] - held_positions[name]) for name in moving_names
            }
            failed = {name: error for name, error in final_errors.items() if error > tolerance}
            details = ", ".join(
                f"{self.by_name[name].label} {error} PULSE" for name, error in failed.items()
            )
            raise MotionIncompleteError(
                f"부분 이동 종료({correction_reason}) · 현재 자세로 안전 유지\n{details}",
                held_positions,
            )
        except MotionIncompleteError as exc:
            self.events.put(
                (
                    "motion_incomplete",
                    {"message": str(exc), "positions": exc.positions},
                )
            )
        except Exception as exc:
            try:
                if self.pulse_bus:
                    self.pulse_bus.disable_torque()
            finally:
                self.events.put(("motion_fault", str(exc)))

    def _check_telemetry(
        self,
        telemetry: dict[str, dict[str, int]],
        voltage_history: dict[str, deque],
        temperature_history: dict[str, deque],
    ) -> None:
        min_voltage = int(self.config["safety"]["minimum_voltage_raw"])
        max_temp = int(self.config["safety"]["maximum_temperature_c"])
        for name, values in telemetry.items():
            voltage_history[name].append(values["Present_Voltage"])
            temperature_history[name].append(values["Present_Temperature"])
            if len(voltage_history[name]) == voltage_history[name].maxlen:
                filtered_voltage = int(median(voltage_history[name]))
                if filtered_voltage < min_voltage:
                    raise RuntimeError(
                        f"{self.by_name[name].label} 전압 {filtered_voltage / 10:.1f}V"
                    )
            if len(temperature_history[name]) == temperature_history[name].maxlen:
                filtered_temp = int(median(temperature_history[name]))
                if filtered_temp >= max_temp:
                    raise RuntimeError(
                        f"{self.by_name[name].label} 온도 {filtered_temp}°C"
                    )

    def emergency_stop(self) -> None:
        self._abort_sequence("긴급 정지")
        self.teleop_stop.set()
        self.teleop_running = False
        self.motion_stop.set()
        try:
            if self.pulse_bus:
                self.pulse_bus.disable_torque()
        finally:
            self.torque_btn.configure(text="토크 켜기")
            self.move_btn.configure(state="disabled")
            self.capture_btn.configure(state="normal" if self.pulse_bus else "disabled")
            self.gripper_open_capture_btn.configure(state="normal" if self.pulse_bus else "disabled")
            self.gripper_closed_capture_btn.configure(state="normal" if self.pulse_bus else "disabled")
            self._set_tuning_buttons(bool(self.pulse_bus))
            self._set_wrist_homing_buttons(bool(self.pulse_bus))
            self._clear_axis_selection()
            self._set_status("긴급 정지 · 모터 1~6 토크 OFF")
            self.teleop_status_var.set("긴급 정지 · 팔로워 토크 OFF")
            self._refresh_teleop_controls()

    def capture_gripper_endpoint(self, is_open: bool) -> None:
        if not self.pulse_bus:
            return
        if self.pulse_bus.torque_on:
            messagebox.showinfo("토크를 먼저 끄세요", "집게 교정은 토크 OFF에서만 가능합니다.")
            return
        try:
            value = self.pulse_bus.read_positions()["gripper"]
            if is_open:
                self.gripper_open_raw = value
            else:
                self.gripper_closed_raw = value
            self._finish_gripper_calibration_if_ready()
        except Exception as exc:
            self._show_error(f"집게 교정 실패: {exc}")

    def _finish_gripper_calibration_if_ready(self) -> None:
        if self.gripper_open_raw is None or self.gripper_closed_raw is None:
            self._refresh_gripper_ui()
            return
        settings = self.config["gripper"]
        calibration = gripper_safe_calibration(
            self.gripper_open_raw,
            self.gripper_closed_raw,
            int(settings["endpoint_margin_pulse"]),
            int(settings["maximum_calibration_span"]),
        )
        payload = {
            "format": "carepack-so101-gripper-calibration-v1",
            "motor_id": 6,
            "open_raw": calibration.open_raw,
            "closed_raw": calibration.closed_raw,
            "open_safe": calibration.open_safe,
            "closed_safe": calibration.closed_safe,
            "minimum": calibration.minimum,
            "maximum": calibration.maximum,
        }
        self.gripper_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.gripper_calibration = calibration
        self.target_vars["gripper"].set(str(calibration.open_safe))
        self._refresh_gripper_ui()
        self._set_status("6번 집게 교정 저장 완료 · 열림/닫힘 목표 사용 가능")

    def _load_gripper_calibration(self) -> None:
        try:
            settings = self.config["gripper"]
            if self.gripper_path.exists():
                data = json.loads(self.gripper_path.read_text(encoding="utf-8"))
                self.gripper_open_raw = int(data["open_raw"])
                self.gripper_closed_raw = int(data["closed_raw"])
            else:
                self.gripper_open_raw = int(settings["default_open_raw"])
                self.gripper_closed_raw = int(settings["default_closed_raw"])
            self.gripper_calibration = gripper_safe_calibration(
                self.gripper_open_raw,
                self.gripper_closed_raw,
                int(settings["endpoint_margin_pulse"]),
                int(settings["maximum_calibration_span"]),
            )
        except Exception:
            self.gripper_open_raw = None
            self.gripper_closed_raw = None
            self.gripper_calibration = None

    def _refresh_gripper_ui(self) -> None:
        if not hasattr(self, "gripper_cal_var"):
            return
        if self.gripper_calibration:
            c = self.gripper_calibration
            self.gripper_cal_var.set(
                f"교정 완료 · 원시 열림 {c.open_raw} / 닫힘 {c.closed_raw} · "
                f"안전 목표 열림 {c.open_safe} / 닫힘 {c.closed_safe}"
            )
            self.limit_vars["gripper"].set(
                ranges_text(self._ranges_for(self.gripper_spec))
            )
            self.open_target_btn.configure(state="normal")
            self.close_target_btn.configure(state="normal")
        else:
            open_text = "미저장" if self.gripper_open_raw is None else str(self.gripper_open_raw)
            closed_text = "미저장" if self.gripper_closed_raw is None else str(self.gripper_closed_raw)
            self.gripper_cal_var.set(
                f"열림·닫힘 버튼만 교정 필요 · 열림 {open_text} / 닫힘 {closed_text} · "
                "수동 PULSE 이동은 사용자 허용범위 사용"
            )
            self.limit_vars["gripper"].set(
                ranges_text(self._ranges_for(self.gripper_spec))
            )
            self.open_target_btn.configure(state="disabled")
            self.close_target_btn.configure(state="disabled")

    def set_gripper_target(self, is_open: bool) -> None:
        if not self.gripper_calibration:
            return
        value = self.gripper_calibration.open_safe if is_open else self.gripper_calibration.closed_safe
        self.target_vars["gripper"].set(str(value))
        self.selected_vars["gripper"].set(True)
        self._set_status(f"집게 {'열림' if is_open else '닫힘'} 목표 {value} PULSE 설정")

    def save_pose(self) -> None:
        targets = {}
        try:
            for spec in self.specs:
                targets[spec.name] = int(self.target_vars[spec.name].get())
        except ValueError as exc:
            self._show_error(f"목표값 오류: {exc}")
            return
        path = filedialog.asksaveasfilename(
            title="6축 목표 자세 저장",
            defaultextension=".json",
            filetypes=(("JSON pose", "*.json"),),
            initialdir=str(APP_DIR),
        )
        if not path:
            return
        payload = {"format": "carepack-so101-profiled-pose-v1", "motors": targets}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._set_status(f"목표 자세 저장: {Path(path).name}")

    def load_pose(self) -> None:
        path = filedialog.askopenfilename(
            title="6축 목표 자세 불러오기",
            filetypes=(("JSON pose", "*.json"),),
            initialdir=str(APP_DIR),
        )
        if not path:
            return
        try:
            motors = json.loads(Path(path).read_text(encoding="utf-8"))["motors"]
            for spec in self.specs:
                self.target_vars[spec.name].set(str(int(motors[spec.name])))
                self.selected_vars[spec.name].set(True)
            self._set_status(f"목표 자세 불러옴: {Path(path).name} · 6축 이동 선택")
        except Exception as exc:
            self._show_error(f"자세 파일 오류: {exc}")

    def _sequence_payload(self) -> dict:
        return {
            "format": SEQUENCE_FORMAT,
            "name": self.sequence_name_var.get().strip() or "CARE-PACK 고정 자세 동작",
            "steps": self.sequence_steps,
        }

    def _validate_sequence(self, payload: dict | None = None) -> list[dict]:
        return validate_sequence_steps(
            payload or self._sequence_payload(),
            self.specs,
            {spec.name: self._ranges_for(spec) for spec in self.specs},
        )

    def _refresh_sequence_list(self, selected_index: int | None = None) -> None:
        self.sequence_listbox.delete(0, tk.END)
        for index, step in enumerate(self.sequence_steps, start=1):
            target_text = "  ".join(
                f"ID{spec.motor_id}:{int(step['targets'][spec.name])}"
                for spec in self.specs
            )
            self.sequence_listbox.insert(
                tk.END,
                f"{index:02d}. {step['name']}  |  {target_text}  |  대기 {step['wait_seconds']:g}s",
            )
        if self.sequence_steps:
            selected_index = (
                min(max(0, selected_index), len(self.sequence_steps) - 1)
                if selected_index is not None
                else len(self.sequence_steps) - 1
            )
            self.sequence_listbox.selection_set(selected_index)
            self.sequence_listbox.see(selected_index)
            self.sequence_status_var.set(f"등록된 단계 {len(self.sequence_steps)}개")
        else:
            self.sequence_status_var.set("등록된 동작 단계 없음")

    def _selected_sequence_index(self) -> int | None:
        selection = self.sequence_listbox.curselection()
        return int(selection[0]) if selection else None

    def _sequence_edit_allowed(self) -> bool:
        if self.sequence_running:
            messagebox.showinfo("시퀀스 실행 중", "실행을 중지한 뒤 단계를 수정하세요.")
            return False
        return True

    def add_sequence_step(self) -> None:
        if not self._sequence_edit_allowed():
            return
        try:
            targets = {
                spec.name: int(self.target_vars[spec.name].get())
                for spec in self.specs
            }
            step = {
                "name": self.sequence_step_name_var.get().strip()
                or f"단계 {len(self.sequence_steps) + 1}",
                "targets": targets,
                "selected": [spec.name for spec in self.specs],
                "wait_seconds": float(self.sequence_wait_var.get()),
            }
            normalized = validate_sequence_steps(
                {"format": SEQUENCE_FORMAT, "steps": [step]},
                self.specs,
                {spec.name: self._ranges_for(spec) for spec in self.specs},
            )[0]
            self.sequence_steps.append(normalized)
            self._refresh_sequence_list(len(self.sequence_steps) - 1)
            self.sequence_step_name_var.set(f"단계 {len(self.sequence_steps) + 1}")
            self._set_status(f"자동 동작 단계 추가: {normalized['name']}")
        except Exception as exc:
            self._show_error(f"단계 추가 실패: {exc}")

    def apply_selected_sequence_step(self) -> None:
        index = self._selected_sequence_index()
        if index is None:
            messagebox.showinfo("단계 선택", "목표로 불러올 단계를 선택하세요.")
            return
        step = self.sequence_steps[index]
        for spec in self.specs:
            self.target_vars[spec.name].set(str(step["targets"][spec.name]))
            self.selected_vars[spec.name].set(spec.name in step["selected"])
        self.sequence_step_name_var.set(step["name"])
        self.sequence_wait_var.set(step["wait_seconds"])
        self.notebook.select(0)
        self._set_status(f"시퀀스 단계 목표 불러옴: {step['name']}")

    def move_sequence_step(self, direction: int) -> None:
        if not self._sequence_edit_allowed():
            return
        index = self._selected_sequence_index()
        if index is None:
            return
        destination = index + int(direction)
        if not 0 <= destination < len(self.sequence_steps):
            return
        self.sequence_steps[index], self.sequence_steps[destination] = (
            self.sequence_steps[destination],
            self.sequence_steps[index],
        )
        self._refresh_sequence_list(destination)

    def delete_sequence_step(self) -> None:
        if not self._sequence_edit_allowed():
            return
        index = self._selected_sequence_index()
        if index is None:
            return
        del self.sequence_steps[index]
        self._refresh_sequence_list(max(0, index - 1) if self.sequence_steps else None)

    def clear_sequence_steps(self) -> None:
        if not self._sequence_edit_allowed() or not self.sequence_steps:
            return
        if messagebox.askyesno("전체 삭제", "등록된 동작 단계를 모두 삭제할까요?"):
            self.sequence_steps.clear()
            self._refresh_sequence_list()

    def save_sequence(self) -> None:
        if not self._sequence_edit_allowed():
            return
        try:
            self.sequence_steps = self._validate_sequence()
        except Exception as exc:
            self._show_error(f"시퀀스 저장 실패: {exc}")
            return
        path = filedialog.asksaveasfilename(
            title="CARE-PACK 동작 시퀀스 저장",
            defaultextension=".json",
            filetypes=(("CARE-PACK sequence", "*.json"),),
            initialdir=str(APP_DIR),
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(self._sequence_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.sequence_status_var.set(f"시퀀스 저장: {Path(path).name}")

    def load_sequence(self) -> None:
        if not self._sequence_edit_allowed():
            return
        path = filedialog.askopenfilename(
            title="CARE-PACK 동작 시퀀스 불러오기",
            filetypes=(("CARE-PACK sequence", "*.json"),),
            initialdir=str(APP_DIR),
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.sequence_steps = self._validate_sequence(payload)
            self.sequence_name_var.set(
                str(payload.get("name", Path(path).stem)).strip() or Path(path).stem
            )
            self._refresh_sequence_list(0)
            self.sequence_status_var.set(
                f"시퀀스 불러옴: {Path(path).name} · {len(self.sequence_steps)}단계"
            )
        except Exception as exc:
            self._show_error(f"시퀀스 파일 오류: {exc}")

    def start_sequence(self) -> None:
        if self.teleop_running:
            messagebox.showinfo("리더 조작 중", "리더 조작을 먼저 중지하세요.")
            return
        if self.sequence_running:
            return
        if not self.pulse_bus or not self.pulse_bus.torque_on:
            messagebox.showinfo("토크 OFF", "수동 탭에서 연결하고 토크를 켠 뒤 실행하세요.")
            return
        try:
            self.sequence_steps = self._validate_sequence()
        except Exception as exc:
            self._show_error(f"시퀀스 실행 불가: {exc}")
            return
        summary = "\n".join(
            f"{index}. {step['name']} · 완료 후 {step['wait_seconds']:g}초 대기"
            for index, step in enumerate(self.sequence_steps, start=1)
        )
        if not messagebox.askyesno(
            "고정 자세 시퀀스 실행",
            f"{self.sequence_name_var.get()}\n\n{summary}\n\n위 동작을 순서대로 실행할까요?",
        ):
            return
        self.sequence_running = True
        self.sequence_index = 0
        self.sequence_start_btn.configure(state="disabled")
        self.sequence_stop_btn.configure(state="normal")
        self.sequence_status_var.set("시퀀스 시작 준비")
        self.root.after(100, self._run_next_sequence_step)

    def _run_next_sequence_step(self) -> None:
        self.sequence_after_id = None
        if not self.sequence_running:
            return
        if self.motion_thread and self.motion_thread.is_alive():
            self.sequence_after_id = self.root.after(50, self._run_next_sequence_step)
            return
        if self.sequence_index >= len(self.sequence_steps):
            self._finish_sequence()
            return
        step = self.sequence_steps[self.sequence_index]
        for spec in self.specs:
            self.target_vars[spec.name].set(str(step["targets"][spec.name]))
            self.selected_vars[spec.name].set(spec.name in step["selected"])
        self.sequence_status_var.set(
            f"실행 중 {self.sequence_index + 1}/{len(self.sequence_steps)} · {step['name']}"
        )
        try:
            assert self.pulse_bus is not None
            current = self.pulse_bus.read_positions()
        except Exception as exc:
            self._abort_sequence(f"현재 위치 읽기 실패: {exc}")
            return
        if all(
            int(step["targets"][name]) == int(current[name])
            for name in step["selected"]
        ):
            self.sequence_index += 1
            wait_ms = max(0, int(round(step["wait_seconds"] * 1000)))
            self.sequence_after_id = self.root.after(wait_ms, self._run_next_sequence_step)
            return
        started = self.start_motion(
            skip_confirmation=True,
            motion_label=f"시퀀스 {self.sequence_index + 1}: {step['name']}",
        )
        if not started:
            self._abort_sequence("단계 이동 시작 실패")

    def _advance_sequence_after_success(self) -> None:
        if not self.sequence_running or self.sequence_index >= len(self.sequence_steps):
            return
        step = self.sequence_steps[self.sequence_index]
        self.sequence_index += 1
        self.sequence_status_var.set(
            f"완료 {self.sequence_index}/{len(self.sequence_steps)} · {step['name']}"
        )
        wait_ms = max(0, int(round(step["wait_seconds"] * 1000)))
        self.sequence_after_id = self.root.after(wait_ms, self._run_next_sequence_step)

    def _finish_sequence(self) -> None:
        self.sequence_running = False
        self.sequence_after_id = None
        self.sequence_start_btn.configure(state="normal")
        self.sequence_stop_btn.configure(state="disabled")
        self._clear_axis_selection()
        self.sequence_status_var.set(
            f"시퀀스 완료 · {len(self.sequence_steps)}단계 · 현재 자세 유지"
        )
        self._set_status("CARE-PACK 고정 자세 시퀀스 완료 · 토크 ON")

    def _abort_sequence(self, reason: str) -> None:
        if self.sequence_after_id is not None:
            try:
                self.root.after_cancel(self.sequence_after_id)
            except Exception:
                pass
            self.sequence_after_id = None
        was_running = self.sequence_running
        self.sequence_running = False
        if hasattr(self, "sequence_start_btn"):
            self.sequence_start_btn.configure(state="normal")
            self.sequence_stop_btn.configure(state="disabled")
        if was_running:
            self.sequence_status_var.set(f"시퀀스 중단 · {reason}")

    def stop_sequence(self) -> None:
        if not self.sequence_running:
            return
        self._abort_sequence("사용자 중지")
        self.emergency_stop()

    def open_output_folder(self) -> None:
        try:
            if os.name == "nt":
                os.startfile(APP_DIR)  # type: ignore[attr-defined]
            else:
                self._set_status(f"기록 폴더: {APP_DIR}")
        except Exception as exc:
            self._show_error(f"기록 폴더 열기 실패: {exc}")

    def _log_motion_result(
        self,
        result: str,
        positions: dict[str, int] | None,
        message: str = "",
    ) -> None:
        context = self.motion_context
        self.motion_context = None
        if not context:
            return
        final_positions = positions or {}
        errors = {
            name: abs(int(context["targets"][name]) - int(final_positions[name]))
            for name in context["active_names"]
            if name in final_positions
        }
        voltage = {
            name: values.get("Present_Voltage")
            for name, values in self.latest_telemetry.items()
        }
        temperature = {
            name: values.get("Present_Temperature")
            for name, values in self.latest_telemetry.items()
        }
        current = {
            name: values.get("Present_Current")
            for name, values in self.latest_telemetry.items()
        }
        row = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": context["mode"],
            "result": result,
            "duration_s": f"{time.monotonic() - context['started']:.3f}",
            "active_axes": ",".join(context["active_names"]),
            "start_positions": json.dumps(context["current"], ensure_ascii=False),
            "target_positions": json.dumps(context["targets"], ensure_ascii=False),
            "final_positions": json.dumps(final_positions, ensure_ascii=False),
            "errors": json.dumps(errors, ensure_ascii=False),
            "voltage_raw": json.dumps(voltage, ensure_ascii=False),
            "temperature_c": json.dumps(temperature, ensure_ascii=False),
            "current_raw": json.dumps(current, ensure_ascii=False),
            "message": message.replace("\n", " | "),
        }
        fieldnames = list(row)
        write_header = not MOTION_LOG_PATH.exists() or MOTION_LOG_PATH.stat().st_size == 0
        try:
            with MOTION_LOG_PATH.open("a", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as exc:
            if hasattr(self, "sequence_status_var"):
                self.sequence_status_var.set(f"CSV 기록 실패: {exc}")

    def _update_positions(self, positions: dict[str, int], copy_targets: bool) -> None:
        for spec in self.specs:
            if spec.name == self.wrist_name and not self.wrist_homing_applied:
                self.position_vars[spec.name].set("영점 설정 필요")
                if copy_targets:
                    self.target_vars[spec.name].set("2048")
                continue
            self.position_vars[spec.name].set(str(positions[spec.name]))
            if copy_targets:
                self.target_vars[spec.name].set(str(positions[spec.name]))

    def _update_telemetry(self, telemetry: dict[str, dict[str, int]]) -> None:
        self.latest_telemetry = {
            name: {key: int(value) for key, value in values.items()}
            for name, values in telemetry.items()
        }
        positions = {}
        for spec in self.specs:
            values = telemetry[spec.name]
            positions[spec.name] = values["Present_Position"]
            self.ui_voltage_history[spec.name].append(values["Present_Voltage"])
            self.ui_temperature_history[spec.name].append(values["Present_Temperature"])
            filtered_voltage = median(self.ui_voltage_history[spec.name])
            filtered_temperature = int(median(self.ui_temperature_history[spec.name]))
            current = values.get("Present_Current", -1)
            current_text = "--" if current < 0 else str(current)
            self.telemetry_vars[spec.name].set(
                f"{filtered_voltage / 10:.1f}V {filtered_temperature}°C I{current_text}"
            )
        self._update_positions(positions, copy_targets=False)

    def _show_error(self, text: str) -> None:
        self._set_status(text)
        messagebox.showerror("SO-ARM101 Profiled PULSE Studio", text)

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "connected":
                    positions, telemetry = payload
                    for history in self.ui_voltage_history.values():
                        history.clear()
                    for history in self.ui_temperature_history.values():
                        history.clear()
                    self._update_positions(positions, copy_targets=True)
                    self._clear_axis_selection()
                    self._update_telemetry(telemetry)
                    self.connect_btn.configure(text="연결 해제", state="normal")
                    self.torque_btn.configure(state="normal")
                    self.capture_btn.configure(state="normal")
                    self.gripper_open_capture_btn.configure(state="normal")
                    self.gripper_closed_capture_btn.configure(state="normal")
                    self._set_tuning_buttons(True)
                    self._set_wrist_homing_buttons(True)
                    self._refresh_wrist_homing_ui()
                    self._start_monitor()
                    self._set_status("모터 ID 1~6 연결됨 · 토크 OFF · 실시간 PULSE 읽기 중")
                    self._refresh_teleop_controls()
                    if not self.wrist_homing_applied and not self.wrist_setup_prompt_shown:
                        self.wrist_setup_prompt_shown = True
                        self.root.after(
                            200,
                            lambda: messagebox.showinfo(
                                "5번 손목 영점 설정 필수",
                                "손목을 물리적 회전범위의 정확한 중앙에 놓은 뒤\n"
                                "'현재 중앙을 2048로 설정'을 누르세요.\n\n"
                                "설정 전에는 손목 원시 0/4095 값을 화면에 표시하지 않고 토크 ON도 차단합니다.",
                            ),
                        )
                elif kind == "positions":
                    self._update_positions(payload, copy_targets=False)
                elif kind == "telemetry":
                    self._update_telemetry(payload)
                elif kind == "motion_done":
                    self._log_motion_result("success", payload)
                    self._update_positions(payload, copy_targets=False)
                    self._clear_axis_selection()
                    self.move_btn.configure(state="normal" if self.pulse_bus and self.pulse_bus.torque_on else "disabled")
                    self.capture_btn.configure(state="normal")
                    if self.sequence_running:
                        self._set_status("시퀀스 단계 완료 · 다음 단계 대기")
                        self._advance_sequence_after_success()
                    else:
                        self._set_status("프로파일 이동 완료 · 최종 자세 유지 중")
                elif kind == "motion_status":
                    self._set_status(str(payload))
                elif kind == "motion_incomplete":
                    positions = payload["positions"]
                    self._log_motion_result("incomplete", positions, payload["message"])
                    self._abort_sequence(payload["message"])
                    self._update_positions(positions, copy_targets=True)
                    self._clear_axis_selection()
                    self.move_btn.configure(
                        state="normal" if self.pulse_bus and self.pulse_bus.torque_on else "disabled"
                    )
                    self.capture_btn.configure(state="normal")
                    self._set_status(payload["message"])
                    messagebox.showwarning(
                        "SO-ARM101 Profiled PULSE Studio",
                        payload["message"] + "\n토크는 ON이며 현재 위치를 유지합니다.",
                    )
                elif kind == "motion_fault":
                    self._log_motion_result("fault", None, str(payload))
                    self._abort_sequence(str(payload))
                    self.torque_btn.configure(text="토크 켜기")
                    self.move_btn.configure(state="disabled")
                    self.capture_btn.configure(state="normal")
                    self.gripper_open_capture_btn.configure(state="normal")
                    self.gripper_closed_capture_btn.configure(state="normal")
                    self._set_tuning_buttons(True)
                    self._set_wrist_homing_buttons(True)
                    self._clear_axis_selection()
                    self._show_error(f"안전 정지 · 모터 1~6 토크 OFF\n{payload}")
                elif kind == "monitor_fault":
                    self._set_status(f"실시간 읽기 중지 · 재연결하세요: {payload}")
                elif kind == "leader_connected":
                    for spec in self.specs:
                        self.leader_position_vars[spec.name].set(str(payload[spec.name]))
                    self.leader_connect_btn.configure(text="리더 연결 해제", state="normal")
                    self.leader_status_var.set(
                        f"리더암 {self.leader_port_var.get().strip()} 연결됨 · 토크 OFF"
                    )
                    self.teleop_status_var.set(
                        "팔로워 토크를 켠 뒤 기준 자세 저장 + 리더 조작 시작을 누르세요."
                    )
                    self._refresh_teleop_controls()
                elif kind == "leader_error":
                    self.leader_connect_btn.configure(text="리더 연결", state="normal")
                    self.leader_status_var.set("리더암 연결 실패 · 토크 OFF")
                    self._refresh_teleop_controls()
                    self._show_error(str(payload))
                elif kind == "teleop_positions":
                    self._update_positions(payload["follower"], copy_targets=False)
                    for spec in self.specs:
                        self.leader_position_vars[spec.name].set(
                            str(payload["leader"][spec.name])
                        )
                        self.teleop_target_vars[spec.name].set(
                            str(payload["targets"][spec.name])
                        )
                elif kind == "teleop_stopped":
                    self._update_positions(payload, copy_targets=True)
                    self._finish_teleop_ui(torque_on=True)
                    self.teleop_status_var.set("리더 조작 중지 · 팔로워 현재 자세 유지 중")
                    self._set_status("리더 조작 중지 · 6축 토크 ON · 현재 자세 유지")
                elif kind == "teleop_cancelled":
                    torque_on = bool(self.pulse_bus and self.pulse_bus.torque_on)
                    self._finish_teleop_ui(torque_on=torque_on)
                elif kind == "teleop_fault":
                    self._finish_teleop_ui(torque_on=False)
                    self.torque_btn.configure(text="토크 켜기")
                    self.gripper_open_capture_btn.configure(state="normal")
                    self.gripper_closed_capture_btn.configure(state="normal")
                    self._set_tuning_buttons(True)
                    self._set_wrist_homing_buttons(True)
                    self.teleop_status_var.set(f"안전 정지 · 팔로워 토크 OFF · {payload}")
                    self._show_error(f"리더 조작 안전 정지 · 팔로워 토크 OFF\n{payload}")
                elif kind == "error":
                    self.connect_btn.configure(text="연결", state="normal")
                    self._show_error(str(payload))
        except queue.Empty:
            pass
        if not self.closing:
            self.root.after(100, self._poll_events)

    def request_close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self._abort_sequence("프로그램 종료")
        self.teleop_stop.set()
        self.motion_stop.set()
        self.monitor_stop.set()
        try:
            if self.pulse_bus:
                self.pulse_bus.disconnect()
            if self.leader_bus:
                self.leader_bus.disconnect()
        finally:
            self.root.destroy()


def main() -> None:
    migrate_previous_settings()
    root = tk.Tk()
    ProfiledStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
