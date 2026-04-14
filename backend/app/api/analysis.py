import math
from typing import Optional

from fastapi import APIRouter, File, UploadFile

from app.services.patent_engine import process_frame

router = APIRouter()


def generate_ai_report(peak: float, avg: float, alert: str, high_count: int, total_frames: int) -> str:
    # Demo-safe narrative so the dashboard always has a coach-facing summary to show.
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


def build_demo_dataset(source_label: Optional[str] = None) -> dict:
    # This synthetic dataset mirrors the shape the eventual YOLO + patent pipeline should return.
    # It keeps the front-end fully functional while the real pose-detection pipeline is still evolving.
    sample_frames = []
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
            # The patent engine returns asymmetry as a ratio; the dashboard presents it as a percentage.
            frame["asymmetry"] = round(frame["asymmetry"] * 100, 1)
            sample_frames.append(frame)

    risk_scores = [frame["risk_score"] for frame in sample_frames]
    peak_risk = max(risk_scores)
    avg_risk = round(sum(risk_scores) / len(risk_scores), 1)
    high_risk_count = sum(1 for frame in sample_frames if frame["alert"] == "HIGH")
    alert_level = "HIGH" if peak_risk >= 65 else "MODERATE" if peak_risk >= 40 else "LOW"

    return {
        "message": "API is working with ATHLETIQ demo data",
        "source": source_label or "demo",
        "peak_risk_score": peak_risk,
        "average_risk_score": avg_risk,
        "alert_level": alert_level,
        "high_risk_frame_count": high_risk_count,
        "total_frames_analyzed": len(sample_frames),
        "frame_data": sample_frames,
        "ai_report": generate_ai_report(
            peak_risk,
            avg_risk,
            alert_level,
            high_risk_count,
            len(sample_frames),
        ),
    }


@router.get("/demo")
def demo():
    # Fast path for live demos when you want predictable output without uploading a file first.
    return build_demo_dataset()


@router.post("/analyze")
async def analyze_video(video: UploadFile = File(...)):
    # Temporary upload handler: accepts a real file but returns demo-shaped analytics until
    # YOLO pose extraction is wired into the backend processing path.
    result = build_demo_dataset(source_label=video.filename or "uploaded-video")
    result["uploaded_file"] = video.filename
    result["message"] = f"Processed demo analysis for {video.filename}"
    return result
