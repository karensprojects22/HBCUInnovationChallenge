import math
import tempfile
from pathlib import Path
from typing import Any, Optional

import cv2
from ultralytics import YOLO

from app.services.patent_engine import joint_angle, process_frame

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "yolov8n-pose.pt"

# COCO pose keypoint indices used by YOLOv8 pose models.
KEYPOINT_NAMES = {
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}

_MODEL: Optional[YOLO] = None


def get_model() -> YOLO:
    global _MODEL
    if _MODEL is None:
        _MODEL = YOLO(str(MODEL_PATH))
    return _MODEL


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _point_or_none(points, confs, index: int):
    x, y = points[index]
    conf = float(confs[index]) if confs is not None else 0.0
    if conf < 0.2:
        return None
    return (float(x), float(y), conf)


def _build_keypoint_map(points, confs) -> dict[str, Optional[list[float]]]:
    data = {}
    for name, index in KEYPOINT_NAMES.items():
        point = _point_or_none(points, confs, index)
        data[name] = [round(point[0], 2), round(point[1], 2), round(point[2], 3)] if point else None
    return data


def _angle_from_map(keypoints: dict[str, Optional[list[float]]], a: str, b: str, c: str) -> float:
    pa, pb, pc = keypoints.get(a), keypoints.get(b), keypoints.get(c)
    if not pa or not pb or not pc:
        return 180.0
    return joint_angle(pa[0], pa[1], pb[0], pb[1], pc[0], pc[1])


def _extract_pose_frame(result, sampled_index: int, timestamp: float, fatigue_hint: float) -> Optional[dict[str, Any]]:
    if result.keypoints is None or result.keypoints.xy is None or len(result.keypoints.xy) == 0:
        return None

    points = result.keypoints.xy[0].cpu().numpy()
    confs = result.keypoints.conf[0].cpu().numpy() if result.keypoints.conf is not None else None
    keypoints = _build_keypoint_map(points, confs)

    left_knee_angle = _angle_from_map(keypoints, "left_hip", "left_knee", "left_ankle")
    right_knee_angle = _angle_from_map(keypoints, "right_hip", "right_knee", "right_ankle")
    angle_difference = abs(left_knee_angle - right_knee_angle)

    # Lightweight muscle-activation proxies derived from knee flexion depth.
    left_depth = _clip((180.0 - left_knee_angle) / 90.0)
    right_depth = _clip((180.0 - right_knee_angle) / 90.0)
    asymmetry_hint = _clip(angle_difference / 45.0)
    fatigue = _clip((fatigue_hint * 0.7) + (asymmetry_hint * 0.3))

    analysis = process_frame(
        {
            "frame": sampled_index + 1,
            "emg_left": round(left_depth, 3),
            "emg_right": round(right_depth, 3),
            "fatigue": round(fatigue, 3),
        }
    )
    analysis["rep"] = max(1, (sampled_index // 10) + 1)
    analysis["left_knee_angle"] = round(left_knee_angle, 1)
    analysis["right_knee_angle"] = round(right_knee_angle, 1)
    analysis["angle_difference"] = round(angle_difference, 1)
    analysis["asymmetry"] = round(analysis["asymmetry"] * 100, 1)

    return {
        "frame": sampled_index + 1,
        "timestamp": round(timestamp, 2),
        "keypoints": keypoints,
        "analysis": analysis,
    }


def analyze_video_file(video_path: str, sample_stride: int = 3, max_frames: int = 90) -> dict[str, Any]:
    model = get_model()
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("Unable to open uploaded video")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = round(total_frames / fps, 2) if fps else 0.0

    sampled_paths: list[str] = []
    sampled_timestamps: list[float] = []
    sampled_positions: list[int] = []

    frame_index = 0
    sampled_index = 0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            if frame_index % sample_stride == 0:
                fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                Path(temp_path).unlink(missing_ok=True)
                cv2.imwrite(temp_path, frame)
                sampled_paths.append(temp_path)
                sampled_timestamps.append(frame_index / fps if fps else sampled_index * 0.03)
                sampled_positions.append(frame_index)
                sampled_index += 1
                if sampled_index >= max_frames:
                    break
            frame_index += 1
    finally:
        capture.release()

    if not sampled_paths:
        raise ValueError("No frames could be sampled from the uploaded video")

    results = model(sampled_paths, verbose=False)
    pose_frames = []
    for idx, result in enumerate(results):
        fatigue_hint = idx / max(len(sampled_paths) - 1, 1)
        pose_frame = _extract_pose_frame(result, idx, sampled_timestamps[idx], fatigue_hint)
        if pose_frame:
            pose_frames.append(pose_frame)

    for path in sampled_paths:
        Path(path).unlink(missing_ok=True)

    if not pose_frames:
        raise ValueError("Pose model did not detect an athlete in the uploaded video")

    frame_data = [item["analysis"] for item in pose_frames]
    risk_scores = [frame["risk_score"] for frame in frame_data]
    peak_risk = max(risk_scores)
    avg_risk = round(sum(risk_scores) / len(risk_scores), 1)
    high_risk_count = sum(1 for frame in frame_data if frame["alert"] == "HIGH")
    alert_level = "HIGH" if peak_risk >= 65 else "MODERATE" if peak_risk >= 40 else "LOW"

    return {
        "fps": round(fps, 2),
        "duration_seconds": duration,
        "frame_width": frame_width,
        "frame_height": frame_height,
        "total_video_frames": total_frames,
        "total_frames_analyzed": len(frame_data),
        "peak_risk_score": peak_risk,
        "average_risk_score": avg_risk,
        "alert_level": alert_level,
        "high_risk_frame_count": high_risk_count,
        "frame_data": frame_data,
        "pose_frames": pose_frames,
    }
