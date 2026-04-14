from fastapi import APIRouter
from app.services.patent_engine import process_frame

router = APIRouter()


# ─────────────────────────────
# Demo endpoint (NOW REAL DATA)
# ─────────────────────────────
@router.get("/demo")
def demo():

    # fake sample frames (this simulates your athlete data)
    sample_frames = [
        {"emg_left": 0.6, "emg_right": 0.4, "fatigue": 0.2, "frame": 1},
        {"emg_left": 0.7, "emg_right": 0.5, "fatigue": 0.3, "frame": 2},
        {"emg_left": 0.9, "emg_right": 0.6, "fatigue": 0.5, "frame": 3},
    ]

    results = [process_frame(f) for f in sample_frames]

    risk_scores = [r["risk_score"] for r in results]
    alerts = [r["alert"] for r in results]

    return {
        "message": "API is working with REAL engine",
        "peak_risk_score": max(risk_scores),
        "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
        "alert_level": "HIGH" if "HIGH" in alerts else "MODERATE",
        "high_risk_frame_count": sum(1 for r in results if r["risk_score"] >= 65),
        "total_frames_analyzed": len(results),
        "frame_data": results
    }