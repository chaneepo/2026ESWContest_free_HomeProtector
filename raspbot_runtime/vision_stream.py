#!/usr/bin/env python3
"""Read-only camera/YOLO stream. Does not import or start any robot drivers."""

import argparse
import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn


def create_app(args):
    lock = threading.Lock()
    stop = threading.Event()
    latest = {"jpeg": None, "sequence": 0, "updated": 0.0,
              "error": "Starting camera and model", "detections": []}

    def capture():
        cap = None
        try:
            import cv2
            import torch
            from ultralytics import YOLO

            torch.set_num_threads(3)
            if not args.model.is_file():
                raise FileNotFoundError(args.model)
            model = YOLO(str(args.model))
            cap = cv2.VideoCapture(args.camera, cv2.CAP_V4L2)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open /dev/video{args.camera}")
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            while not stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped supplying frames")
                result = model.predict(frame, imgsz=320, conf=0.35,
                                       device="cpu", verbose=False)[0]
                ok, jpeg = cv2.imencode(".jpg", result.plot(),
                                       [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ok:
                    raise RuntimeError("JPEG encoding failed")
                detections = []
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls.item())
                        detections.append({"class_id": class_id,
                                           "name": result.names[class_id],
                                           "score": float(box.conf.item())})
                with lock:
                    latest.update(jpeg=jpeg.tobytes(), updated=time.monotonic(),
                                  error=None, detections=detections,
                                  sequence=latest["sequence"] + 1)
        except Exception as exc:
            logging.exception("Vision capture stopped")
            with lock:
                latest.update(error=str(exc), jpeg=None)
        finally:
            if cap is not None:
                cap.release()

    @asynccontextmanager
    async def lifespan(app):
        worker = threading.Thread(target=capture, daemon=True)
        worker.start()
        yield
        stop.set()
        await asyncio.to_thread(worker.join, 3)

    app = FastAPI(title="CARE-PACK read-only vision", lifespan=lifespan)

    @app.get("/status")
    def status():
        with lock:
            ready = latest["jpeg"] is not None and time.monotonic() - latest["updated"] < 5
            data = {"ok": ready, "model": args.model.name, "device": "CPU",
                    "camera": f"/dev/video{args.camera}", "conf": 0.35,
                    "sequence": latest["sequence"], "error": latest["error"],
                    "detections": latest["detections"]}
        return JSONResponse(data, status_code=200 if ready else 503)

    @app.get("/mjpeg")
    async def mjpeg():
        async def frames():
            previous = -1
            while not stop.is_set():
                with lock:
                    jpeg, sequence = latest["jpeg"], latest["sequence"]
                    fresh = time.monotonic() - latest["updated"] < 5
                if jpeg is not None and fresh and sequence != previous:
                    previous = sequence
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                           + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                await asyncio.sleep(0.05)
        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--model", type=Path,
                        default=Path("/home/tracelab/RobotUnified_v2/models/yolo11n-seg.pt"))
    args = parser.parse_args()
    uvicorn.run(create_app(args), host=args.host, port=args.port)
