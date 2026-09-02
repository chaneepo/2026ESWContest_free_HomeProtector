import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT))

import cv2
from ultralytics import YOLO


TRAINED_MODEL = ROOT / "runs" / "segment" / "car_key_lip_balm_watch" / "weights" / "best.pt"


def main():
    parser = argparse.ArgumentParser(description="CPU-only YOLO segmentation inference")
    parser.add_argument("source", help="Image, video, directory, or camera number such as 0")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=416)
    args = parser.parse_args()

    local_model = ROOT / "best.pt"
    model_path = args.model or (local_model if local_model.exists() else TRAINED_MODEL)
    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")

    source = int(args.source) if args.source.isdigit() else args.source
    model = YOLO(str(model_path))

    window_name = "YOLO Segmentation - q or ESC to quit"
    for result in model.predict(
        source=source,
        device="cpu",
        imgsz=args.imgsz,
        conf=args.conf,
        save=True,
        project=str(ROOT / "runs" / "inference"),
        name="predict",
        exist_ok=True,
        stream=True,
    ):
        cv2.imshow(window_name, result.plot())
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
