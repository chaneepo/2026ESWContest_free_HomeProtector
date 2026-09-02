from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT))

import torch
from ultralytics import YOLO


DEFAULT_DATA = ROOT / "yolo_dataset" / "data.yaml"
DEFAULT_PROJECT = ROOT / "runs" / "segment"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train an Ultralytics YOLO instance-segmentation model on CUDA."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model", default="yolo26n-seg.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", type=int, default=0, help="CUDA GPU index")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--name", default="car_key_lip_balm_watch")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--test-after-train",
        action="store_true",
        help="Evaluate best.pt on the test split after training.",
    )
    return parser.parse_args()


def validate_cuda(device: int) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available. This script intentionally does not fall back to CPU. "
            f"Installed PyTorch: {torch.__version__}"
        )

    device_count = torch.cuda.device_count()
    if device < 0 or device >= device_count:
        raise RuntimeError(
            f"Invalid CUDA device {device}. Available GPU indices: 0-{device_count - 1}"
        )

    torch.cuda.set_device(device)
    properties = torch.cuda.get_device_properties(device)
    memory_gb = properties.total_memory / (1024**3)
    print(f"[INFO] PyTorch: {torch.__version__}")
    print(f"[INFO] CUDA device: {device} ({properties.name}, {memory_gb:.1f} GB)")


def main() -> None:
    args = parse_args()
    data_path = args.data.expanduser().resolve()
    project_path = args.project.expanduser().resolve()

    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset config not found: {data_path}")

    validate_cuda(args.device)
    print(f"[INFO] Dataset: {data_path}")
    print(f"[INFO] Model: {args.model}")

    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        project=str(project_path),
        name=args.name,
        seed=args.seed,
        deterministic=True,
        amp=True,
        cache=False,
        plots=True,
    )

    save_dir = Path(model.trainer.save_dir)
    best_path = save_dir / "weights" / "best.pt"
    print(f"[INFO] Training output: {save_dir}")
    print(f"[INFO] Best checkpoint: {best_path}")

    if args.test_after_train:
        print("[INFO] Evaluating best checkpoint on the test split")
        best_model = YOLO(str(best_path))
        metrics = best_model.val(
            data=str(data_path),
            split="test",
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            workers=args.workers,
            project=str(project_path),
            name=f"{args.name}_test",
        )
        print(f"[INFO] Test box mAP50-95: {metrics.box.map:.4f}")
        print(f"[INFO] Test mask mAP50-95: {metrics.seg.map:.4f}")


if __name__ == "__main__":
    main()
