#!/usr/bin/env python3
"""Live YOLO11n object detection demo on the U20CAM, shown on the local HDMI display."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from media_viewer import WINDOW_NAME, require_gui

DEFAULT_MODEL = Path("/home/tracelab/RobotUnified_v2/models/yolo11n.pt")


def run(index: int, width: int, height: int, fps: int, model_path: Path, conf: float) -> None:
    from ultralytics import YOLO

    model = YOLO(str(model_path))

    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
    capture = cv2.VideoCapture(index, backend)
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)
    if not capture.isOpened():
        raise RuntimeError(f"카메라 /dev/video{index}을(를) 열 수 없습니다.")

    require_gui()
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 960, 540)
    print(f"모델: {model_path}  |  conf >= {conf}  |  q 종료")

    failures = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            failures += 1
            if failures >= 30:
                raise RuntimeError("카메라 프레임을 연속 30회 읽지 못했습니다.")
            continue
        failures = 0

        result = model.predict(frame, conf=conf, verbose=False)[0]
        annotated = result.plot()
        label = f"YOLO11n  {len(result.boxes)} detections  q close"
        cv2.putText(annotated, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(annotated, label, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow(WINDOW_NAME, annotated)
        key = cv2.waitKeyEx(1)
        if key in (ord("q"), 27):
            break
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

    capture.release()
    cv2.destroyAllWindows()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="U20CAM 실시간 YOLO11n 객체 인식 데모")
    parser.add_argument("--camera", type=int, default=0, metavar="INDEX", help="카메라 장치 번호")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="YOLO11n 모델 경로")
    parser.add_argument("--conf", type=float, default=0.25, help="탐지 신뢰도 기준")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run(args.camera, args.width, args.height, args.fps, args.model, args.conf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
