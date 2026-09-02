import argparse
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np


VIDEO_EXTS = {".mp4", ".avi", ".mov"}
CLASS_NAME = "watch"
CLASS_ID = 2

# Set this to a video file path (mp4/avi/mov) or a directory containing videos.
USER_VIDEO_PATH = "videos/watch_02.mov"
USER_MAX_FRAMES = 0
USER_SAMPLE_FRAMES = 300


def get_device():
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def normalize_u8(image):
    image = image.astype(np.float32)
    min_value = float(image.min())
    max_value = float(image.max())
    if max_value - min_value < 1e-6:
        return np.zeros(image.shape, dtype=np.uint8)
    return np.clip((image - min_value) * 255.0 / (max_value - min_value), 0, 255).astype(np.uint8)


def mask_to_yolo_segments(mask, class_id, min_contour_area):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape[:2]
    lines = []

    for contour in contours:
        if cv2.contourArea(contour) < min_contour_area:
            continue

        epsilon = 0.002 * cv2.arcLength(contour, True)
        contour = cv2.approxPolyDP(contour, epsilon, True)
        if len(contour) < 3:
            continue

        coords = []
        for point in contour.reshape(-1, 2):
            x = min(max(point[0] / w, 0.0), 1.0)
            y = min(max(point[1] / h, 0.0), 1.0)
            coords.extend([x, y])
        lines.append(str(class_id) + " " + " ".join(f"{value:.6f}" for value in coords))

    return lines


def make_overlay(image_bgr, mask):
    overlay = image_bgr.copy()
    color = np.zeros_like(image_bgr)
    color[:, :] = (0, 255, 80)
    overlay = np.where(mask[:, :, None] > 0, cv2.addWeighted(image_bgr, 0.45, color, 0.55, 0), overlay)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 0, 255), 2)
    return overlay


def list_videos(video_dir):
    path = Path(video_dir)
    if path.is_file():
        return [path] if path.suffix.lower() in VIDEO_EXTS else []
    return sorted(item for item in path.iterdir() if item.suffix.lower() in VIDEO_EXTS)


def load_sam2(args):
    try:
        from sam2.sam2_video_predictor import SAM2VideoPredictor
    except ImportError as exc:
        raise RuntimeError(
            "SAM2 is not installed. Install it first:\n"
            "  .venv/bin/python -m pip install torch torchvision\n"
            "  .venv/bin/python -m pip install git+https://github.com/facebookresearch/sam2.git"
        ) from exc

    device = get_device()
    mask_generator = None
    image_predictor = None
    if args.anchor_method == "auto":
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

        try:
            mask_generator = SAM2AutomaticMaskGenerator.from_pretrained(
                args.model,
                device=device,
                points_per_side=args.points_per_side,
            )
        except TypeError:
            mask_generator = SAM2AutomaticMaskGenerator.from_pretrained(args.model, device=device)
            mask_generator.points_per_side = args.points_per_side
    else:
        from sam2_autolabel_rgb import load_predictor

        image_predictor, _ = load_predictor(args.model)

    video_predictor = SAM2VideoPredictor.from_pretrained(args.model, device=device)
    return mask_generator, image_predictor, video_predictor, device


def extract_frames(video_path, frame_dir, max_frames=0, sample_frames=0):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_indices = None
    if sample_frames > 0 and total_frames > 0:
        sample_count = min(sample_frames, total_frames)
        sample_indices = set(np.linspace(0, total_frames - 1, sample_count, dtype=np.int32).tolist())

    frames = []
    index = 0
    saved_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if sample_indices is not None and index not in sample_indices:
            index += 1
            continue
        frame_path = frame_dir / f"{saved_index:06d}.jpg"
        cv2.imwrite(str(frame_path), frame)
        frames.append((frame_path, frame, index))
        saved_index += 1
        index += 1
        if sample_indices is None and max_frames > 0 and index >= max_frames:
            break
    cap.release()
    return frames


def mask_metrics(mask, image_shape):
    mask_u8 = mask.astype(np.uint8)
    h, w = image_shape[:2]
    area = int(mask_u8.sum())
    area_ratio = area / float(h * w) if h and w else 0.0
    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {
            "area": area,
            "area_ratio": area_ratio,
            "circularity": 0.0,
            "aspect_ratio": 0.0,
            "centroid": (w / 2.0, h / 2.0),
        }

    contour = max(contours, key=cv2.contourArea)
    perimeter = float(cv2.arcLength(contour, True))
    circularity = (4.0 * np.pi * area / (perimeter * perimeter)) if perimeter > 1e-6 else 0.0
    x, y, bw, bh = cv2.boundingRect(contour)
    aspect_ratio = bw / float(bh) if bh else 0.0
    moments = cv2.moments(contour)
    if abs(moments["m00"]) > 1e-6:
        centroid = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
    else:
        centroid = (x + bw / 2.0, y + bh / 2.0)
    return {
        "area": area,
        "area_ratio": area_ratio,
        "circularity": float(circularity),
        "aspect_ratio": float(aspect_ratio),
        "centroid": centroid,
    }


def score_mask(mask, image_shape, args):
    metrics = mask_metrics(mask, image_shape)
    if metrics["area_ratio"] < args.min_area_ratio or metrics["area_ratio"] > args.max_area_ratio:
        return None
    if metrics["circularity"] < args.min_circularity:
        return None
    if metrics["aspect_ratio"] < 0.5 or metrics["aspect_ratio"] > 2.0:
        return None

    h, w = image_shape[:2]
    cx, cy = w / 2.0, h / 2.0
    mx, my = metrics["centroid"]
    max_dist = (cx * cx + cy * cy) ** 0.5
    dist = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
    center_proximity = 1.0 - min(dist / max(max_dist, 1e-6), 1.0)
    area_score = 1.0 - min(abs(metrics["area_ratio"] - args.target_area_ratio) / args.target_area_ratio, 1.0)
    score = metrics["circularity"] * 0.5 + area_score * 0.3 + center_proximity * 0.2

    metrics["area_score"] = float(area_score)
    metrics["center_proximity"] = float(center_proximity)
    metrics["score"] = float(score)
    return metrics


def find_anchor(mask_generator, frames, args):
    best = None
    all_candidates = {}
    for frame_index in range(0, len(frames), max(args.anchor_step, 1)):
        _, frame_bgr, _ = frames[frame_index]
        image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        anns = mask_generator.generate(image_rgb)
        candidates = []
        for ann in anns:
            mask = ann["segmentation"].astype(bool)
            metrics = score_mask(mask, frame_bgr.shape, args)
            if metrics is None:
                continue
            item = {
                "frame_index": frame_index,
                "mask": mask,
                "sam2_score": float(ann.get("predicted_iou", ann.get("stability_score", 0.0))),
                "metrics": metrics,
            }
            candidates.append(item)
            if best is None or metrics["score"] > best["metrics"]["score"]:
                best = item
        all_candidates[frame_index] = candidates
    return best, all_candidates


def find_rgb_anchor(image_predictor, frames, args):
    from sam2_autolabel_rgb import predict_image

    best = None
    all_candidates = {}
    for frame_index in range(0, len(frames), max(args.anchor_step, 1)):
        _, frame_bgr, _ = frames[frame_index]
        selected, _, candidates, _ = predict_image(image_predictor, frame_bgr, args)
        all_candidates[frame_index] = []
        if selected is None:
            continue
        mask = selected["segmentation"].astype(bool)
        metrics = score_mask(mask, frame_bgr.shape, args)
        if metrics is None:
            continue
        metrics["score"] = float(selected.get("selection_score", metrics["score"]))
        item = {
            "frame_index": frame_index,
            "mask": mask,
            "sam2_score": float(selected.get("predicted_iou", 0.0)),
            "metrics": metrics,
        }
        all_candidates[frame_index] = [item]
        if best is None or metrics["score"] > best["metrics"]["score"]:
            best = item
    return best, all_candidates


def logits_to_mask(logits):
    array = logits
    if hasattr(array, "detach"):
        array = array.detach().cpu().numpy()
    array = np.asarray(array)
    while array.ndim > 2:
        array = array[0]
    return array > 0.0


def propagate_video(video_predictor, frame_dir, anchor):
    state = video_predictor.init_state(video_path=str(frame_dir))
    video_predictor.reset_state(state)
    video_predictor.add_new_mask(
        inference_state=state,
        frame_idx=int(anchor["frame_index"]),
        obj_id=1,
        mask=anchor["mask"].astype(np.uint8),
    )

    propagated = {}
    for reverse in (False, True):
        for out_frame_idx, out_obj_ids, out_mask_logits in video_predictor.propagate_in_video(
            state,
            start_frame_idx=int(anchor["frame_index"]),
            reverse=reverse,
        ):
            if len(out_obj_ids) == 0:
                continue
            propagated[int(out_frame_idx)] = logits_to_mask(out_mask_logits[0])
    return propagated


def save_empty_outputs(frame_bgr, out_dirs, stem, meta):
    empty_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
    cv2.imwrite(str(out_dirs["images"] / f"{stem}.jpg"), frame_bgr)
    cv2.imwrite(str(out_dirs["masks"] / f"{stem}.png"), empty_mask)
    cv2.imwrite(str(out_dirs["overlays"] / f"{stem}.jpg"), make_overlay(frame_bgr, empty_mask))
    (out_dirs["yolo"] / f"{stem}.txt").write_text("")


def save_frame_outputs(video_path, frames, propagated, anchor, out_dirs, args):
    ok = 0
    for frame_index, (_, frame_bgr, source_frame_index) in enumerate(frames):
        stem = f"{CLASS_NAME}_{frame_index + 1:05d}"
        mask_bool = propagated.get(frame_index)
        sam2_score = float(anchor["sam2_score"]) if frame_index == anchor["frame_index"] else 0.0
        metrics = mask_metrics(mask_bool, frame_bgr.shape) if mask_bool is not None else None
        meta = {
            "video": str(video_path),
            "frame_index": int(source_frame_index),
            "method": "auto_video",
            "anchor_frame": frame_index == anchor["frame_index"],
            "sam2_score": sam2_score,
            "area_ratio": float(metrics["area_ratio"]) if metrics else 0.0,
            "circularity": float(metrics["circularity"]) if metrics else 0.0,
        }

        if (
            mask_bool is None
            or metrics["area_ratio"] < args.min_area_ratio
            or metrics["area_ratio"] > args.max_area_ratio
        ):
            save_empty_outputs(frame_bgr, out_dirs, stem, meta)
            continue

        mask = mask_bool.astype(np.uint8) * 255
        cv2.imwrite(str(out_dirs["images"] / f"{stem}.jpg"), frame_bgr)
        cv2.imwrite(str(out_dirs["masks"] / f"{stem}.png"), mask)
        cv2.imwrite(str(out_dirs["overlays"] / f"{stem}.jpg"), make_overlay(frame_bgr, mask))
        yolo_lines = mask_to_yolo_segments(mask, CLASS_ID, args.min_contour_area)
        (out_dirs["yolo"] / f"{stem}.txt").write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""))
        ok += 1
    return ok


def save_anchor_debug(video_path, frames, anchor, candidates_by_frame, out_dir):
    frame_index = int(anchor["frame_index"])
    frame_bgr = frames[frame_index][1]
    stem = video_path.stem
    cv2.imwrite(str(out_dir / f"{stem}_anchor_original.jpg"), frame_bgr)

    candidates = candidates_by_frame.get(frame_index, [])
    candidate_image = frame_bgr.copy()
    for idx, candidate in enumerate(candidates):
        color = (
            int((37 * idx + 60) % 255),
            int((97 * idx + 120) % 255),
            int((173 * idx + 30) % 255),
        )
        mask = candidate["mask"].astype(np.uint8) * 255
        color_layer = np.zeros_like(frame_bgr)
        color_layer[:, :] = color
        candidate_image = np.where(
            mask[:, :, None] > 0,
            cv2.addWeighted(candidate_image, 0.65, color_layer, 0.35, 0),
            candidate_image,
        )
    cv2.imwrite(str(out_dir / f"{stem}_anchor_candidates.jpg"), candidate_image)

    selected = make_overlay(frame_bgr, anchor["mask"].astype(np.uint8) * 255)
    metrics = anchor["metrics"]
    lines = [
        f"frame={frame_index} score={metrics['score']:.3f}",
        f"circularity={metrics['circularity']:.3f} area_score={metrics['area_score']:.3f}",
        f"center={metrics['center_proximity']:.3f} area_ratio={metrics['area_ratio']:.3f}",
    ]
    y = 28
    for line in lines:
        cv2.putText(selected, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(selected, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        y += 28
    cv2.imwrite(str(out_dir / f"{stem}_anchor_selected.jpg"), selected)


def make_out_dirs(video_out):
    out_dirs = {
        "images": video_out / "images",
        "masks": video_out / "masks",
        "overlays": video_out / "overlays",
        "yolo": video_out / "yolo",
        "debug": video_out / "debug",
    }
    for out_dir in out_dirs.values():
        out_dir.mkdir(parents=True, exist_ok=True)
    return out_dirs


def apply_rgb_defaults(args):
    defaults = {
        "shadow": True,
        "shadow_sigma": 45.0,
        "shadow_target_mean": 128.0,
        "clahe_clip": 3.0,
        "unsharp_sigma": 2.0,
        "unsharp_amount": 0.8,
        "median_kernel": 5,
        "canny_low": 35,
        "canny_high": 110,
        "object_block": 91,
        "object_c": 3.0,
        "object_kernel": 5,
        "hough_dp": 1.2,
        "roi_left": 0.0,
        "roi_right": 1.0,
        "roi_top": 0.0,
        "roi_bottom": 1.0,
        "hough_min_dist": 120.0,
        "hough_param1": 90.0,
        "hough_param2": 24.0,
        "hough_min_radius": 55,
        "hough_max_radius": 330,
        "hough_max_candidates": 18,
        "inner_radius_max": 155,
        "inner_to_outer_scale": 2.25,
        "outer_scale": 1.18,
        "min_prompt_radius": 115,
        "max_prompt_radius": 280,
        "inner_ratio": 0.36,
        "positive_left_ratio": 0.45,
        "positive_inner_ratio": 0.35,
        "positive_outer_ratio": 0.90,
        "positive_min_pixels": 80,
        "positive_x_percentiles": [20.0, 50.0, 80.0],
        "preferred_prompt_radius": 250.0,
        "max_border_touches": 1,
        "box_min_area_ratio": 0.015,
        "box_max_area_ratio": 0.72,
        "min_object_ratio": 0.08,
        "edge_thickness": 3,
        "outer_edge_weight": 0.35,
        "detected_edge_weight": 0.20,
        "object_weight": 0.20,
        "dark_weight": 0.10,
        "center_weight": 0.15,
        "radius_weight": 0.10,
        "side_search_left_scale": 1.8,
        "side_search_top_scale": 1.8,
        "side_search_right_scale": 1.25,
        "side_search_bottom_scale": 1.05,
        "side_box_low_percentile": 2.0,
        "side_box_high_percentile": 92.0,
        "side_box_pad": 8,
        "side_min_object_pixels": 500,
        "refine_low_outer_edge": 0.205,
        "refine_search_scale": 2.2,
        "refine_search_top_scale": 1.8,
        "refine_search_bottom_scale": 1.4,
        "min_component_annulus_pixels": 20,
    }
    for name, value in defaults.items():
        if not hasattr(args, name):
            setattr(args, name, value)


def process_video(video_path, mask_generator, image_predictor, video_predictor, args):
    video_out = Path(args.out) / video_path.stem
    out_dirs = make_out_dirs(video_out)
    with tempfile.TemporaryDirectory(prefix=f"{video_path.stem}_sam2_frames_") as tmp_name:
        frame_dir = Path(tmp_name)
        frames = extract_frames(video_path, frame_dir, args.max_frames, args.sample_frames)
        if not frames:
            print(f"[WARN] {video_path.name}: no frames")
            return 0, 0

        if args.anchor_method == "auto":
            anchor, candidates_by_frame = find_anchor(mask_generator, frames, args)
        else:
            anchor, candidates_by_frame = find_rgb_anchor(image_predictor, frames, args)
        if anchor is None:
            print(f"[WARN] {video_path.name}: no anchor mask passed filters")
            return 0, len(frames)

        if args.debug:
            save_anchor_debug(video_path, frames, anchor, candidates_by_frame, out_dirs["debug"])

        propagated = propagate_video(video_predictor, frame_dir, anchor)
        ok = save_frame_outputs(video_path, frames, propagated, anchor, out_dirs, args)
        print(f"[OK] {video_path.name}: anchor={anchor['frame_index']}, labeled={ok}/{len(frames)}")
        return ok, len(frames)


def main():
    parser = argparse.ArgumentParser(description="Auto-label video masks with SAM2 anchor selection and propagation.")
    parser.add_argument("--videos", default=USER_VIDEO_PATH)
    parser.add_argument("--out", default="sam2_labels/final")
    parser.add_argument("--model", default="facebook/sam2.1-hiera-small")
    parser.add_argument("--anchor-method", choices=["rgb", "auto"], default="auto")
    parser.add_argument("--prompt-method", choices=["contour", "hough"], default="contour")
    parser.add_argument("--anchor-step", type=int, default=30)
    parser.add_argument("--min-circularity", type=float, default=0.55)
    parser.add_argument("--min-area-ratio", type=float, default=0.03)
    parser.add_argument("--max-area-ratio", type=float, default=0.45)
    parser.add_argument("--target-area-ratio", type=float, default=0.18)
    parser.add_argument("--min-contour-area", type=float, default=50.0)
    parser.add_argument("--points-per-side", type=int, default=32)
    parser.add_argument("--max-frames", type=int, default=USER_MAX_FRAMES)
    parser.add_argument("--sample-frames", type=int, default=USER_SAMPLE_FRAMES)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-full", action="store_true")
    args = parser.parse_args()
    apply_rgb_defaults(args)

    video_paths = list_videos(args.videos)
    if not video_paths:
        raise RuntimeError(f"No videos found in: {args.videos}")

    mask_generator, image_predictor, video_predictor, device = load_sam2(args)
    print(f"[INFO] SAM2 model: {args.model}")
    print(f"[INFO] Device: {device}")
    print(f"[INFO] Videos: {len(video_paths)}")

    total_ok = 0
    total_frames = 0
    for video_path in video_paths:
        ok, count = process_video(video_path, mask_generator, image_predictor, video_predictor, args)
        total_ok += ok
        total_frames += count

    print(f"[INFO] Done: {total_ok}/{total_frames} frames labeled")
    print(f"[INFO] Output: {Path(args.out)}")


if __name__ == "__main__":
    main()
