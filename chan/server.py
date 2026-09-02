"""Dependency-free web server for the CARE-PACK Raspbot controller UI."""

from __future__ import annotations

import argparse
import json
import mimetypes
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
    """Serialize robot access and separate sensing from motor permission."""

    def __init__(self, *, hardware: bool = False, sensors_only: bool = False) -> None:
        if hardware and sensors_only:
            raise ValueError("hardware and sensors_only modes are mutually exclusive")
        self.hardware = hardware
        self.sensors_only = sensors_only
        self.sensor_hardware = hardware or sensors_only
        self.limits = SafetyLimits(max_speed=80, max_duration=0.5)
        self.turn_limits = SafetyLimits(max_speed=80, max_duration=4.0)
        self.turn_seconds_per_90 = 1.0
        self.turn_reference_speed = 40
        mode = "hardware" if hardware else "sensors" if sensors_only else "demo"
        self.state = RuntimeState(mode=mode)
        self._controller: RaspbotController | None = None
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, Any]:
        data = asdict(self.state)
        data.update(
            {
                "hardware_enabled": self.hardware,
                "sensors_enabled": self.sensor_hardware,
                "movement_enabled": self.hardware,
                "max_speed": self.limits.max_speed,
                "max_duration": self.limits.max_duration,
                "min_turn_angle": 1,
                "max_turn_angle": 180,
                "turn_seconds_per_90": self.turn_seconds_per_90,
                "turn_reference_speed": self.turn_reference_speed,
                "timestamp": time.time(),
            }
        )
        return data

    def _ensure_controller(self) -> RaspbotController:
        if self._controller is None:
            self._controller = RaspbotController(limits=self.turn_limits)
            self._controller.connect()
            self.state.connected = True
        return self._controller

    def set_mode(self, mode: str, *, confirm_safe: bool = False) -> dict[str, Any]:
        """Switch between movement-locked sensing and real motor control safely."""
        normalized = str(mode).strip().lower()
        aliases = {"safe": "sensors", "sensors": "sensors", "hardware": "hardware"}
        if normalized not in aliases:
            raise ValueError("mode must be safe, sensors, or hardware")
        target = aliases[normalized]
        if target == "hardware" and confirm_safe is not True:
            raise PermissionError("실기모드 전환 전 주변 안전 확인이 필요합니다")

        with self._lock:
            previous = (
                self.hardware,
                self.sensors_only,
                self.sensor_hardware,
                self.state.mode,
            )
            try:
                # Hardware mode must prove the I2C controller is reachable before
                # unlocking movement. Safe mode only needs to stop a controller
                # that is already connected -- it must not require hardware to
                # exist just to lock movement back down.
                if target == "hardware":
                    controller = self._ensure_controller()
                    controller.stop()
                elif self._controller is not None:
                    self._controller.stop()
                self.hardware = target == "hardware"
                self.sensors_only = target == "sensors"
                self.sensor_hardware = True
                self.state.mode = target
                self.state.last_action = "stop"
                self.state.last_speed = 0
                self.state.last_duration = 0.0
                self.state.last_angle = None
                self.state.last_error = None
            except Exception as exc:
                (
                    self.hardware,
                    self.sensors_only,
                    self.sensor_hardware,
                    self.state.mode,
                ) = previous
                self.state.last_error = str(exc)
                raise
        return self.snapshot()

    def move(self, action: str, speed: int, duration: float) -> dict[str, Any]:
        if self.sensors_only:
            raise PermissionError("Movement is locked in sensor-only mode")
        motion = Motion(action)
        speed = int(speed)
        duration = float(duration)
        if not 1 <= speed <= self.limits.max_speed:
            raise ValueError(f"speed must be between 1 and {self.limits.max_speed}")
        if not 0.0 < duration <= self.limits.max_duration:
            raise ValueError(
                f"duration must be greater than 0 and at most {self.limits.max_duration}"
            )

        if not self._lock.acquire(blocking=False):
            # A pulse is already in flight. Drop this command instead of queuing
            # behind it, so rapid keypresses feel responsive rather than buffered.
            raise RuntimeError("이전 이동 명령이 아직 처리 중입니다")
        try:
            if self.hardware:
                self._ensure_controller().pulse(
                    motion, speed=speed, duration=duration
                )
            self.state.last_action = motion.value
            self.state.last_speed = speed
            self.state.last_duration = duration
            self.state.last_angle = None
            self.state.command_count += 1
            self.state.last_error = None
        except Exception as exc:
            self.state.last_error = str(exc)
            raise
        finally:
            self._lock.release()
        return self.snapshot()

    def turn(self, direction: str, angle: float, speed: int) -> dict[str, Any]:
        if self.sensors_only:
            raise PermissionError("Movement is locked in sensor-only mode")

        direction = str(direction).lower()
        if direction not in ("left", "right"):
            raise ValueError("direction must be left or right")
        angle = float(angle)
        speed = int(speed)
        if not 1 <= angle <= 180:
            raise ValueError("angle must be between 1 and 180 degrees")
        if not 1 <= speed <= self.limits.max_speed:
            raise ValueError(f"speed must be between 1 and {self.limits.max_speed}")

        duration = (
            angle
            / 90.0
            * self.turn_seconds_per_90
            * self.turn_reference_speed
            / speed
        )
        if duration > self.turn_limits.max_duration:
            raise ValueError("requested turn is too long for the current speed")

        motion = Motion.TURN_LEFT if direction == "left" else Motion.TURN_RIGHT
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("이전 이동 명령이 아직 처리 중입니다")
        try:
            if self.hardware:
                self._ensure_controller().pulse(
                    motion,
                    speed=speed,
                    duration=duration,
                )
            self.state.last_action = motion.value
            self.state.last_speed = speed
            self.state.last_duration = round(duration, 3)
            self.state.last_angle = angle
            self.state.command_count += 1
            self.state.last_error = None
        except Exception as exc:
            self.state.last_error = str(exc)
            raise
        finally:
            self._lock.release()
        return self.snapshot()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            try:
                if self.hardware and self._controller is not None:
                    self._controller.stop()
                self.state.last_action = "stop"
                self.state.last_speed = 0
                self.state.last_duration = 0.0
                self.state.last_angle = None
                self.state.last_error = None
            except Exception as exc:
                self.state.last_error = str(exc)
                raise
        return self.snapshot()

    def sensors(self) -> dict[str, Any]:
        if not self.sensor_hardware:
            return {
                "mode": "demo",
                "distance_cm": 63.4,
                "line": [False, True, True, False],
                "line_raw": 6,
            }

        with self._lock:
            controller = self._ensure_controller()
            line = controller.read_line()
            distance = controller.read_distance_cm()
            return {
                "mode": self.state.mode,
                "distance_cm": distance,
                "line": [line.x1, line.x2, line.x3, line.x4],
                "line_raw": line.raw,
            }

    def close(self) -> None:
        with self._lock:
            if self._controller is not None:
                self._controller.close()
                self._controller = None
                self.state.connected = False


def build_handler(runtime: ControllerRuntime) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ChanController/1.0"

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
            except (OSError, RaspbotError, RuntimeError) as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"ok": False, "error": str(exc)},
                )

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path in ("/api/move", "/api/raspbot/move"):
                    payload = self._read_json()
                    result = runtime.move(
                        str(payload.get("action", "")),
                        int(payload.get("speed", 40)),
                        float(payload.get("duration", 0.2)),
                    )
                elif path == "/api/raspbot/turn":
                    payload = self._read_json()
                    result = runtime.turn(
                        str(payload.get("direction", "")),
                        float(payload.get("angle", 45)),
                        int(payload.get("speed", 40)),
                    )
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
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
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
        help="enable real I2C motor and sensor access (default: demo mode)",
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
    mode = "HARDWARE" if args.hardware else "SENSORS-ONLY" if args.sensors_only else "DEMO"
    display_host = f"[{args.host}]" if ":" in args.host else args.host
    print(f"CHAN controller: http://{display_host}:{args.port} ({mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping controller server...")
    finally:
        runtime.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
