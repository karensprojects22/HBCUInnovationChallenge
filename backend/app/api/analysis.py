from fastapi import APIRouter

router = APIRouter()

@router.get("/demo")
def demo():
    return {
        "message": "API is working",
        "peak_risk_score": 72,
        "average_risk_score": 55,
        "alert_level": "HIGH",
        "high_risk_frame_count": 12,
        "total_frames_analyzed": 100,
        "frame_data": []
    }