"""Dependency-free web server for the CARE-PACK Raspbot controller UI."""

from __future__ import annotations

import argparse
import json
import mimetypes
import math
import secrets
import signal
import socket
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from raspbot import RaspbotError
except ModuleNotFoundError:  # Demo mode also runs on the Mac without the driver.
    class RaspbotError(Exception):
        """Fallback used only when the Raspberry Pi driver is not installed."""

from chan_control import Motion, RaspbotController, SafetyLimits

WEB_ROOT = Path(__file__).resolve().parent / "web"


class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
    """Serve IPv6 and, where supported, IPv4-mapped clients on one socket."""

    address_family = socket.AF_INET6

    def server_bind(self) -> None:
        if hasattr(socket, "IPV6_V6ONLY"):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def server_class_for(host: str) -> type[ThreadingHTTPServer]:
    return IPv6ThreadingHTTPServer if ":" in host else ThreadingHTTPServer


@dataclass
class RuntimeState:
    mode: str
    connected: bool = False
    last_action: str = "stop"
    last_speed: int = 0
    last_duration: float = 0.0
    last_angle: float | None = None
    command_count: int = 0
    last_error: str | None = None


class ControllerRuntime:
    """Single motion owner; never hold the state/I2C lock during a timed wait."""

    def __init__(self, *, hardware: bool = False, sensors_only: bool = False,
                 controller_factory=None, clock=time.monotonic, lease_seconds=5.0) -> None:
        if hardware and sensors_only:
            raise ValueError("hardware and sensors_only modes are mutually exclusive")
        # Even legacy --hardware starts locked. Only explicit UI arming grants a lease.
        self.hardware = False
        self.sensors_only = hardware or sensors_only
        self.sensor_hardware = self.sensors_only
        self.limits = SafetyLimits(max_speed=80, max_duration=0.5)
        self.turn_limits = SafetyLimits(max_speed=80, max_duration=4.0)
        self.turn_seconds_per_90 = 1.0
        self.turn_reference_speed = 40
        self.state = RuntimeState(mode="sensors" if self.sensors_only else "demo")
        self._factory = controller_factory or (lambda: RaspbotController(limits=self.turn_limits))
        self._controller = None
        self._lock = threading.RLock()
        self._motion_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._stop_serial = 0
        self._halt = threading.Event()
        self._halt.set()
        self._active_cancel = None
        self._token = None
        self._clock = clock
        self._lease_seconds = float(lease_seconds)
        self._deadline = 0.0
        self._closing = False
        self._watchdog_exit = threading.Event()
        self._watchdog = None
        self._revision = 0
        self._instance_id = secrets.token_hex(8)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = asdict(self.state)
            data.update(
                safety_protocol=2,
                hardware_enabled=self.hardware,
                sensors_enabled=self.sensor_hardware,
                movement_enabled=bool(self.hardware and self.state.connected and self._token
                                      and not self._halt.is_set() and self._clock() < self._deadline),
                busy=self._active_cancel is not None,
                max_speed=self.limits.max_speed,
                max_duration=self.limits.max_duration,
                min_turn_angle=1, max_turn_angle=180,
                turn_seconds_per_90=self.turn_seconds_per_90,
                turn_reference_speed=self.turn_reference_speed,
                control_lease_seconds=self._lease_seconds,
                revision=self._revision, instance_id=self._instance_id,
                timestamp=time.time(),
            )
            # Never expose the owner's control token through status polling.
            return data

    def _ensure_controller(self):
        if self._controller is None:
            candidate = self._factory()
            try:
                candidate.connect()
                candidate.read_line()  # Read-only I2C response, not just opening /dev/i2c-1.
            except Exception:
                try:
                    candidate.close()
                except Exception:
                    pass
                self.state.connected = False
                raise
            self._controller = candidate  # Publish only after a successful probe.
            self.state.connected = True
        return self._controller

    def _disarm_locked(self):
        self._halt.set()
        if self._active_cancel is not None:
            self._active_cancel.set()
        self._token = None
        self._deadline = 0.0
        self.hardware = False
        self.sensors_only = self.sensor_hardware
        self.state.mode = "sensors" if self.sensor_hardware else "demo"
        self.state.last_action = "stop"
        self.state.last_speed = 0
        self.state.last_duration = 0.0
        self.state.last_angle = None
        self._revision += 1

    def _fault_locked(self, exc):
        self._disarm_locked()
        self.state.connected = False
        self.state.last_error = str(exc)
        controller, self._controller = self._controller, None
        if controller is not None:
            try:
                controller.stop()
            except Exception as stop_exc:
                self.state.last_error += f"; STOP failed: {stop_exc}"
            try:
                controller.close()
            except Exception as close_exc:
                self.state.last_error += f"; close failed: {close_exc}"

    def set_mode(self, mode: str, *, confirm_safe: bool = False) -> dict[str, Any]:
        target = {"safe": "sensors", "sensors": "sensors", "hardware": "hardware"}.get(str(mode).lower())
        if target is None:
            raise ValueError("mode must be safe, sensors, or hardware")
        if target == "sensors":
            return self.stop(sensor_mode=True)
        if confirm_safe is not True:
            raise PermissionError("주변 안전 확인이 필요합니다")
        with self._request_lock:
            serial = self._stop_serial
        with self._lock:
            if self._closing:
                raise PermissionError("Server is shutting down")
            if self.hardware or self._motion_lock.locked():
                raise PermissionError("먼저 STOP을 누르고 현재 동작이 종료된 뒤 다시 전환하세요")
            try:
                self.sensor_hardware = self.sensors_only = True
                self._halt.clear()
                controller = self._ensure_controller()
                controller.stop()
                with self._request_lock:
                    cancelled = serial != self._stop_serial
                if cancelled or self._halt.is_set():
                    raise PermissionError("STOP 요청으로 실기모드 전환이 취소됐습니다")
                self._token = secrets.token_urlsafe(32)
                self._deadline = self._clock() + self._lease_seconds
                self.hardware, self.sensors_only = True, False
                self.state.mode = "hardware"
                self.state.last_error = None
                self._revision += 1
                return {**self.snapshot(), "control_token": self._token}
            except Exception as exc:
                self._fault_locked(exc)
                raise

    def _validate_control_locked(self, token):
        if self.hardware and self._clock() >= self._deadline:
            self.stop(reason="통신 확인 시간 초과: 이동 잠금")
        if (not self.hardware or self._halt.is_set() or not isinstance(token, str)
                or not self._token or not secrets.compare_digest(token, self._token)):
            raise PermissionError("이동이 잠겨 있거나 운전 권한이 만료됐습니다. 안전 확인 후 다시 전환하세요")

    def heartbeat(self, token):
        with self._lock:
            self._validate_control_locked(token)
            self._deadline = self._clock() + self._lease_seconds
            return self.snapshot()

    @staticmethod
    def _speed(value, maximum):
        number = float(value)
        if isinstance(value, bool) or not math.isfinite(number) or not number.is_integer() or not 1 <= number <= maximum:
            raise ValueError(f"speed must be an integer between 1 and {maximum}")
        return int(number)

    def move(self, action, speed, duration, *, control_token=None):
        motion = Motion(action)
        speed = self._speed(speed, self.limits.max_speed)
        if isinstance(duration, bool):
            raise ValueError("duration must be numeric, not boolean")
        duration = float(duration)
        if not math.isfinite(duration) or not 0 < duration <= self.limits.max_duration:
            raise ValueError(f"duration must be greater than 0 and at most {self.limits.max_duration}")
        return self._run_motion(motion, speed, duration, None, control_token)

    def turn(self, direction, angle, speed, *, control_token=None):
        if direction not in ("left", "right"):
            raise ValueError("direction must be left or right")
        if isinstance(angle, bool):
            raise ValueError("angle must be numeric, not boolean")
        angle = float(angle)
        speed = self._speed(speed, self.limits.max_speed)
        if not math.isfinite(angle) or not 1 <= angle <= 180:
            raise ValueError("angle must be between 1 and 180 degrees")
        duration = angle / 90 * self.turn_seconds_per_90 * self.turn_reference_speed / speed
        if not math.isfinite(duration) or duration > self.turn_limits.max_duration:
            raise ValueError("requested turn is too long")
        motion = Motion.TURN_LEFT if direction == "left" else Motion.TURN_RIGHT
        return self._run_motion(motion, speed, duration, angle, control_token)

    def _run_motion(self, motion, speed, duration, angle, token):
        if not self._motion_lock.acquire(blocking=False):
            raise RuntimeError("이전 이동 명령이 아직 처리 중입니다")
        cancel = threading.Event()
        controller = None
        try:
            with self._lock:
                if self._closing or self.sensors_only:
                    raise PermissionError("Movement is locked")
                if self.hardware:
                    self._validate_control_locked(token)
                    controller = self._ensure_controller()
                self._active_cancel = cancel
                self.state.last_action = motion.value
                self.state.last_speed = speed
                self.state.last_duration = round(duration, 3)
                self.state.last_angle = angle
                try:
                    if controller is not None:
                        controller.start_motion(motion, speed=speed)
                    self.state.command_count += 1
                    self.state.last_error = None
                    self._revision += 1
                except Exception as exc:
                    self._fault_locked(exc)
                    raise
            # STOP/watchdog can now take _lock and write STOP immediately.
            if controller is not None:
                cancel.wait(duration)
        finally:
            try:
                with self._lock:
                    try:
                        if controller is not None and self._controller is controller:
                            controller.stop()
                    except Exception as exc:
                        self._fault_locked(exc)
                        raise
                    finally:
                        if self._active_cancel is cancel:
                            self._active_cancel = None
            finally:
                self._motion_lock.release()
        return {**self.snapshot(), "interrupted": cancel.is_set()}

    def stop(self, *, reason=None, sensor_mode=False):
        # This signal also cancels a slow in-flight arming request.
        with self._request_lock:
            self._stop_serial += 1
            self._halt.set()
            if self._active_cancel is not None:
                self._active_cancel.set()
        with self._lock:
            if sensor_mode:
                self.sensor_hardware = True
            self._disarm_locked()  # Never restore hardware mode after a stop failure.
            confirmed = False
            try:
                if self._controller is not None:
                    self._controller.stop()
                    confirmed = True
                if reason:
                    self.state.last_error = reason
            except Exception as exc:
                self._fault_locked(exc)
                raise
            return {**self.snapshot(), "stop_confirmed": confirmed}

    def sensors(self):
        with self._lock:
            if not self.sensor_hardware:
                return {"mode": "demo", "distance_cm": 63.4,
                        "line": [False, True, True, False], "line_raw": 6}
            # Avoid a potentially slow sensor read while a motor pulse is active.
            if self._active_cancel is not None:
                raise RuntimeError("이동 중 센서 갱신은 잠시 대기합니다")
            try:
                controller = self._ensure_controller()
                line = controller.read_line()
                distance = controller.read_distance_cm()
                if not math.isfinite(distance):
                    raise ValueError("Invalid distance reading")
                return {"mode": self.state.mode, "distance_cm": distance,
                        "line": [line.x1, line.x2, line.x3, line.x4], "line_raw": line.raw}
            except Exception as exc:
                self._fault_locked(exc)
                raise

    def check_watchdog(self):
        with self._lock:
            if self.hardware and self._clock() >= self._deadline:
                self.stop(reason="운전 화면 응답 없음: 자동 정지 및 이동 잠금")

    def start_watchdog(self):
        if self._watchdog is not None:
            return
        def watch():
            while not self._watchdog_exit.wait(0.1):
                try:
                    self.check_watchdog()
                except Exception:
                    # stop() has already latched safe state and recorded the error.
                    pass
        self._watchdog = threading.Thread(target=watch, name="chan-watchdog", daemon=True)
        self._watchdog.start()

    def close(self):
        self._watchdog_exit.set()
        self._closing = True
        try:
            self.stop(reason="서버 종료")
        finally:
            with self._lock:
                self._closing = True
                controller, self._controller = self._controller, None
                self.state.connected = False
                if controller is not None:
                    controller.close()
            if self._watchdog is not None and self._watchdog is not threading.current_thread():
                self._watchdog.join(timeout=1)


def build_handler(runtime: ControllerRuntime) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ChanController/2.0"

        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def _check_write_origin(self):
            # CSRF mitigation, not authentication. Restrict deployment to trusted networks.
            origin = self.headers.get("Origin")
            if self.headers.get("Sec-Fetch-Site") == "cross-site" or (
                origin and origin != f"http://{self.headers.get('Host')}"
            ):
                raise PermissionError("Cross-origin control requests are blocked")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Content-Type must be application/json")

        def log_message(self, format_string: str, *args: object) -> None:
            print(f"[web] {self.address_string()} {format_string % args}")

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 4096:
                raise ValueError("request body is missing or too large")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            return payload

        def _send_static(self, relative: str) -> None:
            relative = relative.lstrip("/") or "index.html"
            candidate = (WEB_ROOT / relative).resolve()
            if WEB_ROOT not in candidate.parents and candidate != WEB_ROOT:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = candidate.read_bytes()
            content_type, _ = mimetypes.guess_type(candidate.name)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path in ("/api/status", "/api/raspbot/status"):
                    self._send_json(HTTPStatus.OK, runtime.snapshot())
                elif path in ("/api/sensors", "/api/raspbot/sensors"):
                    self._send_json(HTTPStatus.OK, runtime.sensors())
                elif path == "/":
                    self._send_static("index.html")
                elif path.startswith("/web/"):
                    self._send_static(path.removeprefix("/web/"))
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except (OSError, RaspbotError, RuntimeError, ValueError) as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": False, "error": str(exc)},
                )

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                self._check_write_origin()
                if path in ("/api/move", "/api/raspbot/move"):
                    payload = self._read_json()
                    result = runtime.move(
                        str(payload.get("action", "")),
                        payload.get("speed", 40),
                        payload.get("duration", 0.2),
                        control_token=payload.get("control_token"),
                    )
                elif path == "/api/raspbot/turn":
                    payload = self._read_json()
                    result = runtime.turn(
                        str(payload.get("direction", "")),
                        payload.get("angle", 45),
                        payload.get("speed", 40),
                        control_token=payload.get("control_token"),
                    )
                elif path == "/api/raspbot/heartbeat":
                    payload = self._read_json()
                    result = runtime.heartbeat(payload.get("control_token"))
                elif path == "/api/raspbot/mode":
                    payload = self._read_json()
                    result = runtime.set_mode(
                        str(payload.get("mode", "")),
                        confirm_safe=payload.get("confirm_safe") is True,
                    )
                elif path in ("/api/stop", "/api/raspbot/stop"):
                    result = runtime.stop()
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_json(HTTPStatus.OK, {"ok": True, **result})
            except PermissionError as exc:
                self._send_json(
                    HTTPStatus.FORBIDDEN, {"ok": False, "error": str(exc)}
                )
            except (ValueError, TypeError, OverflowError, json.JSONDecodeError) as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)}
                )
            except (OSError, RaspbotError, RuntimeError) as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": False, "error": str(exc)},
                )

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--hardware",
        action="store_true",
        help="legacy alias for sensors-only; UI safety confirmation is required to move",
    )
    mode_group.add_argument(
        "--sensors-only",
        action="store_true",
        help="read real I2C sensors while keeping all movement commands locked",
    )
    args = parser.parse_args()

    runtime = ControllerRuntime(
        hardware=args.hardware,
        sensors_only=args.sensors_only,
    )
    server_class = server_class_for(args.host)
    server = server_class((args.host, args.port), build_handler(runtime))
    runtime.start_watchdog()
    def terminate(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    mode = "SENSORS-ONLY (movement locked)" if args.hardware or args.sensors_only else "DEMO"
    display_host = f"[{args.host}]" if ":" in args.host else args.host
    print(f"CHAN controller: http://{display_host}:{args.port} ({mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping controller server...")
    finally:
        try:
            runtime.close()
        finally:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
