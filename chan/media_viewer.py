#!/usr/bin/env python3
"""CARE-PACK dataset image, video, and live-camera viewer."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import cv2


DEFAULT_DATASET_ROOT = Path("/home/tracelab/carepack-dataset")
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES
WINDOW_NAME = "CARE-PACK Media Viewer"


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def find_media(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def display_name(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def print_media(media: Iterable[Path], root: Path) -> None:
    for index, path in enumerate(media, start=1):
        size_mb = path.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{index:3d}. {display_name(path, root)}  ({size_mb:.1f} MB, {modified})")


def require_gui() -> None:
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        runtime_dir = Path(f"/run/user/{os.getuid()}")
        x11_sockets = sorted(Path("/tmp/.X11-unix").glob("X*"))
        xauthority_files = sorted(runtime_dir.glob(".mutter-Xwaylandauth.*"))
        if x11_sockets and xauthority_files:
            os.environ["DISPLAY"] = f":{x11_sockets[0].name.removeprefix('X')}"
            os.environ["XAUTHORITY"] = str(xauthority_files[0])
            os.environ.setdefault("XDG_RUNTIME_DIR", str(runtime_dir))
            os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime_dir}/bus")
            return
        raise RuntimeError(
            "화면 세션을 찾지 못했습니다. 라즈베리파이 데스크톱에 로그인되어 있는지 "
            "확인하거나 SSH X11 전달(ssh -X)을 사용하세요."
        )


def create_window() -> None:
    require_gui()
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 960, 540)


def overlay(frame, lines: list[str]):
    output = frame.copy()
    y = 30
    for line in lines:
        cv2.putText(output, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(output, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
        y += 28
    return output


def view_image(path: Path) -> None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"사진을 읽을 수 없습니다: {path}")

    create_window()
    shown = overlay(image, [path.name, "q/ESC: close"])
    cv2.imshow(WINDOW_NAME, shown)
    while True:
        key = cv2.waitKeyEx(0)
        if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break
    cv2.destroyAllWindows()


def seek_relative(capture: cv2.VideoCapture, delta_ms: float) -> None:
    target = max(0.0, capture.get(cv2.CAP_PROP_POS_MSEC) + delta_ms)
    capture.set(cv2.CAP_PROP_POS_MSEC, target)


def view_video(path: Path) -> None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"영상을 열 수 없습니다: {path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 30.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if frame_count > 0 else 0.0
    delay_ms = max(1, round(1000 / fps))
    paused = False
    frame = None

    create_window()
    print("조작: SPACE 일시정지 | a/d 5초 이동 | r 처음부터 | q 종료")

    while True:
        if not paused or frame is None:
            ok, next_frame = capture.read()
            if not ok:
                print("영상 재생이 끝났습니다. r을 누르면 다시 재생하고, q를 누르면 닫습니다.")
                paused = True
            else:
                frame = next_frame

        if frame is not None:
            current = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            state = "PAUSED" if paused else "PLAYING"
            info = f"{state}  {current:05.1f}s / {duration:05.1f}s"
            cv2.imshow(
                WINDOW_NAME,
                overlay(frame, [path.name, info, "SPACE pause | a/d seek | r restart | q close"]),
            )

        key = cv2.waitKeyEx(0 if paused else delay_ms)
        if key in (ord("q"), 27):
            break
        if key == ord(" "):
            paused = not paused
        elif key == ord("a"):
            seek_relative(capture, -5000)
            paused = False
        elif key == ord("d"):
            seek_relative(capture, 5000)
            paused = False
        elif key == ord("r"):
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            paused = False

        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    capture.release()
    cv2.destroyAllWindows()


def view_camera(index: int, width: int, height: int, fps: int, snapshot_dir: Path) -> None:
    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
    capture = cv2.VideoCapture(index, backend)
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)
    if not capture.isOpened():
        raise RuntimeError(f"카메라 /dev/video{index}을(를) 열 수 없습니다.")

    actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = capture.get(cv2.CAP_PROP_FPS)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    create_window()
    print("조작: s 사진 저장 | q 종료")

    failures = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            failures += 1
            if failures >= 30:
                raise RuntimeError("카메라 프레임을 연속 30회 읽지 못했습니다.")
            continue
        failures = 0

        cv2.imshow(
            WINDOW_NAME,
            overlay(
                frame,
                [
                    f"LIVE /dev/video{index}  {actual_width}x{actual_height}  {actual_fps:.1f}fps",
                    "s snapshot | q close",
                ],
            ),
        )
        key = cv2.waitKeyEx(1)
        if key in (ord("q"), 27):
            break
        if key == ord("s"):
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            target = snapshot_dir / f"snapshot_{stamp}.jpg"
            if not cv2.imwrite(str(target), frame):
                raise RuntimeError(f"사진 저장에 실패했습니다: {target}")
            print(f"사진 저장: {target}")
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    capture.release()
    cv2.destroyAllWindows()


def view_path(path: Path) -> None:
    if is_image(path):
        view_image(path)
    elif is_video(path):
        view_video(path)
    else:
        raise RuntimeError(f"지원하지 않는 파일 형식입니다: {path.suffix or '(확장자 없음)'}")


def browse(root: Path) -> None:
    while True:
        media = find_media(root)
        if not media:
            print(f"사진이나 영상을 찾지 못했습니다: {root}")
            return
        print(f"\n미디어 목록: {root} (최신순)")
        print_media(media, root)
        choice = input("\n열 번호 입력 (새로고침 Enter, 종료 q): ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return
        if not choice:
            continue
        try:
            index = int(choice) - 1
            if not 0 <= index < len(media):
                raise ValueError
        except ValueError:
            print("목록에 있는 번호를 입력하세요.")
            continue
        view_path(media[index])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="사진, 녹화 영상, U20CAM 실시간 화면을 확인합니다.")
    parser.add_argument("path", nargs="?", type=Path, help="열 파일 또는 검색할 폴더")
    parser.add_argument("--camera", nargs="?", const=0, type=int, metavar="INDEX", help="실시간 카메라 열기")
    parser.add_argument("--list", action="store_true", help="미디어 목록만 출력")
    parser.add_argument("--root", type=Path, default=DEFAULT_DATASET_ROOT, help="기본 데이터셋 폴더")
    parser.add_argument("--width", type=int, default=1280, help="카메라 너비")
    parser.add_argument("--height", type=int, default=720, help="카메라 높이")
    parser.add_argument("--fps", type=int, default=30, help="카메라 FPS")
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=DEFAULT_DATASET_ROOT / "snapshots",
        help="실시간 화면 사진 저장 폴더",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.camera is not None:
            view_camera(args.camera, args.width, args.height, args.fps, args.snapshot_dir)
            return 0

        target = args.path or args.root
        if args.list:
            root = target if target.is_dir() else target.parent
            media = find_media(target) if target.is_dir() else [target]
            print_media(media, root)
            return 0

        if target.is_dir():
            browse(target)
        elif target.is_file():
            view_path(target)
        else:
            raise RuntimeError(f"경로가 존재하지 않습니다: {target}")
    except (OSError, RuntimeError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    finally:
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
