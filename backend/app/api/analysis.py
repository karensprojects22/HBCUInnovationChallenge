import math
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, UploadFile

from app.services.patent_engine import process_frame
from app.services.yolo_pose import analyze_video_file

router = APIRouter()
LATEST_ANALYSIS: Optional[dict[str, Any]] = None


def generate_ai_report(peak: float, avg: float, alert: str, high_count: int, total_frames: int) -> str:
    flagged_pct = round((high_count / max(total_frames, 1)) * 100)
    if alert == "HIGH":
        return (
            f"ATHLETIQ detected a peak risk score of {peak}/100 with {flagged_pct}% of frames flagged high-risk, "
            "suggesting fatigue-driven asymmetry and elevated lower-body loading. Recommend reducing workload, "
            "prioritizing unilateral stability drills, and re-screening before returning to full sprint volume."
        )
    if alert == "MODERATE":
        return (
            f"ATHLETIQ observed a moderate average risk score of {avg}/100 with intermittent asymmetry across "
            f"{flagged_pct}% of frames. This pattern suggests accumulating fatigue and compensation that should be "
            "corrected with mobility, glute activation, and monitored workload progression."
        )
    return (
        f"ATHLETIQ found low overall injury risk with an average score of {avg}/100 and only {flagged_pct}% of "
        "frames showing elevated load. Current movement quality appears stable; continue monitoring to preserve "
        "the athlete's personalized baseline."
    )


def set_latest_analysis(result: dict[str, Any]) -> dict[str, Any]:
    global LATEST_ANALYSIS
    LATEST_ANALYSIS = result
    return result


def build_demo_dataset(source_label: Optional[str] = None) -> dict[str, Any]:
    sample_frames = []
    pose_frames = []
    reps = 8
    frames_per_rep = 18
    fatigue_onset = 5

    for rep in range(reps):
        for step in range(frames_per_rep):
            phase = step / frames_per_rep
            depth = math.sin(math.pi * phase)
            fatigue = max(0.0, (rep - fatigue_onset) / max(reps - fatigue_onset, 1))
            left_emg = min(0.34 + 0.52 * depth, 0.98)
            right_emg = min(left_emg + 0.06 + fatigue * 0.10, 1.0)

            frame = process_frame(
                {
                    "frame": rep * frames_per_rep + step + 1,
                    "emg_left": round(left_emg, 3),
                    "emg_right": round(right_emg, 3),
                    "fatigue": round(fatigue, 3),
                }
            )

            left_knee_angle = round(168 - depth * 58, 1)
            right_knee_angle = round(168 - depth * 55 + fatigue * 10, 1)
            frame["rep"] = rep + 1
            frame["left_knee_angle"] = left_knee_angle
            frame["right_knee_angle"] = right_knee_angle
            frame["angle_difference"] = round(abs(left_knee_angle - right_knee_angle), 1)
            frame["asymmetry"] = round(frame["asymmetry"] * 100, 1)
            sample_frames.append(frame)

            cx = 360
            pose_frames.append(
                {
                    "frame": len(sample_frames),
                    "timestamp": round(len(sample_frames) / 30.0, 2),
                    "keypoints": {
                        "left_shoulder": [cx - 38, 145, 0.9],
                        "right_shoulder": [cx + 38, 145, 0.9],
                        "left_hip": [cx - 20, 245 + depth * 18, 0.9],
                        "right_hip": [cx + 20, 245 + depth * 18, 0.9],
                        "left_knee": [cx - 24 - depth * 10, 330 + depth * 22, 0.9],
                        "right_knee": [cx + 24 + depth * 10, 330 + depth * 22 + fatigue * 10, 0.9],
                        "left_ankle": [cx - 22, 425, 0.9],
                        "right_ankle": [cx + 22, 425, 0.9],
                    },
                    "analysis": frame,
                }
            )

    risk_scores = [frame["risk_score"] for frame in sample_frames]
    peak_risk = max(risk_scores)
    avg_risk = round(sum(risk_scores) / len(risk_scores), 1)
    high_risk_count = sum(1 for frame in sample_frames if frame["alert"] == "HIGH")
    alert_level = "HIGH" if peak_risk >= 65 else "MODERATE" if peak_risk >= 40 else "LOW"

    return {
        "message": "API is working with ATHLETIQ demo data",
        "source": source_label or "demo",
        "fps": 30,
        "duration_seconds": round(len(sample_frames) / 30.0, 2),
        "peak_risk_score": peak_risk,
        "average_risk_score": avg_risk,
        "alert_level": alert_level,
        "high_risk_frame_count": high_risk_count,
        "total_frames_analyzed": len(sample_frames),
        "frame_data": sample_frames,
        "pose_frames": pose_frames,
        "ai_report": generate_ai_report(peak_risk, avg_risk, alert_level, high_risk_count, len(sample_frames)),
    }


@router.get("/demo")
def demo():
    return set_latest_analysis(build_demo_dataset())


@router.get("/latest")
def latest():
    return LATEST_ANALYSIS or set_latest_analysis(build_demo_dataset())


@router.post("/analyze")
async def analyze_video(video: UploadFile = File(...)):
    suffix = Path(video.filename or "upload.mp4").suffix or ".mp4"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await video.read())
            temp_path = temp_file.name

        result = analyze_video_file(temp_path)
        result["source"] = video.filename or "uploaded-video"
        result["uploaded_file"] = video.filename
        result["message"] = f"Processed analysis for {video.filename}"
        result["ai_report"] = generate_ai_report(
            result["peak_risk_score"],
            result["average_risk_score"],
            result["alert_level"],
            result["high_risk_frame_count"],
            result["total_frames_analyzed"],
        )
        return set_latest_analysis(result)
    except Exception as exc:
        fallback = build_demo_dataset(source_label=(video.filename or "uploaded-video") + " (demo fallback)")
        fallback["uploaded_file"] = video.filename
        fallback["message"] = f"Real analysis unavailable: {exc}"
        return set_latest_analysis(fallback)
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)
