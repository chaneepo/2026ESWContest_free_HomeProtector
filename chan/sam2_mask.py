#!/usr/bin/env python3
"""Create SAM2 masks from a point or box prompt on one image."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

try:
    from ultralytics import SAM
except ImportError as error:
    raise SystemExit(
        "ultralytics가 필요합니다. "
        "/home/tracelab/RobotUnified_v2/.venv/bin/python으로 실행하세요."
    ) from error


DEFAULT_MODEL = Path("/home/tracelab/chan/models/sam2_t.pt")
DEFAULT_OUTPUT_ROOT = Path("/home/tracelab/carepack-dataset/sam_masks")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SAM2 Tiny로 사진 속 물체 마스크를 생성합니다.")
    parser.add_argument("source", type=Path, help="마스킹할 사진")
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument(
        "--point",
        nargs=2,
        type=float,
        action="append",
        metavar=("X", "Y"),
        help="물체 내부의 양성 점. 여러 번 지정할 수 있습니다.",
    )
    prompt.add_argument(
        "--box",
        nargs=4,
        type=float,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="물체를 둘러싼 사각형",
    )
    parser.add_argument(
        "--negative-point",
        nargs=2,
        type=float,
        action="append",
        default=[],
        metavar=("X", "Y"),
        help="마스크에서 제외할 배경 점. --point와 함께 사용합니다.",
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="SAM2 모델 파일")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="결과 상위 폴더")
    parser.add_argument("--name", help="결과 폴더 이름. 기본값은 사진 파일명_sam2")
    parser.add_argument("--device", default="cpu", help="추론 장치")
    return parser


def save_results(result, source: Path, model_path: Path, output_dir: Path, elapsed: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = output_dir / "overlay.jpg"
    cv2.imwrite(str(overlay_path), result.plot())

    masks = result.masks
    if masks is None or len(masks.data) == 0:
        raise RuntimeError("마스크가 생성되지 않았습니다. 점 또는 박스 위치를 확인하세요.")

    mask_arrays = masks.data.cpu().numpy() > 0.5
    combined = np.any(mask_arrays, axis=0).astype(np.uint8) * 255
    cv2.imwrite(str(output_dir / "mask_combined.png"), combined)
    for index, mask in enumerate(mask_arrays):
        cv2.imwrite(str(output_dir / f"mask_{index:02d}.png"), mask.astype(np.uint8) * 255)

    boxes = result.boxes
    scores = boxes.conf.cpu().tolist() if boxes is not None and boxes.conf is not None else []
    xyxy = boxes.xyxy.cpu().tolist() if boxes is not None and boxes.xyxy is not None else []
    summary = {
        "source": str(source.resolve()),
        "model": str(model_path.resolve()),
        "elapsed_seconds": round(elapsed, 3),
        "image_shape": list(result.orig_shape),
        "mask_count": len(mask_arrays),
        "scores": scores,
        "boxes_xyxy": xyxy,
        "files": {
            "overlay": str(overlay_path),
            "combined_mask": str(output_dir / "mask_combined.png"),
        },
    }
    (output_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"마스크 {len(mask_arrays)}개 생성")
    if scores:
        print("점수:", ", ".join(f"{score:.3f}" for score in scores))
    print(f"소요 시간: {elapsed:.2f}초")
    print(f"결과 폴더: {output_dir}")


def main() -> int:
    args = build_parser().parse_args()
    if not args.source.is_file():
        print(f"오류: 사진을 찾을 수 없습니다: {args.source}", file=sys.stderr)
        return 1
    if not args.model.is_file():
        print(f"오류: SAM2 모델을 찾을 수 없습니다: {args.model}", file=sys.stderr)
        return 1
    if args.negative_point and not args.point:
        print("오류: --negative-point는 --point와 함께 사용하세요.", file=sys.stderr)
        return 1

    predict_args: dict[str, object] = {
        "source": str(args.source),
        "device": args.device,
        "verbose": False,
    }
    if args.point:
        predict_args["points"] = args.point + args.negative_point
        predict_args["labels"] = [1] * len(args.point) + [0] * len(args.negative_point)
    else:
        predict_args["bboxes"] = [args.box]

    output_name = args.name or f"{args.source.stem}_sam2"
    output_dir = args.output_root / output_name
    started = time.perf_counter()
    model = SAM(str(args.model))
    result = model.predict(**predict_args)[0]
    elapsed = time.perf_counter() - started
    save_results(result, args.source, args.model, output_dir, elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
