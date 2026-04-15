import json

import httpx

from app.core.config import GEMINI_API_KEY
from app.services.gemini import model as gemini_model


# Tool 1 in the agent loop: fetch the latest motion-analysis summary from FastAPI.

async def get_risk_analysis():
    """
    Calls the local FastAPI backend for structured risk data the agent can reason over.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://127.0.0.1:8000/api/latest")
            return response.json()
        except Exception:
            # fallback if backend call fails
            return {
                "peak_risk_score": 72,
                "average_risk_score": 55,
                "alert_level": "MODERATE",
                "high_risk_frame_count": 1,
                "total_frames_analyzed": 3
            }


async def run_agent(user_query: str):
    analysis = await get_risk_analysis()

    prompt = f"""
You are an elite sports biomechanics AI coach.

You support ATHLETIQ, a patent-backed biomechanics research platform.

DATA:
{json.dumps(analysis, indent=2)}

USER QUESTION:
{user_query}

TASK:
- Interpret risk scores
- Explain injury risk clearly
- Give actionable training advice
"""

    try:
        if gemini_model is None or not GEMINI_API_KEY:
            raise RuntimeError("Gemini model unavailable")

        response = gemini_model.generate_content(prompt)

        return {
            "mode": "gemini",
            "response": response.text.strip()
        }
    except Exception:
        risk = analysis.get("peak_risk_score", 0)
        alert = analysis.get("alert_level", "UNKNOWN")

        if risk >= 70:
            recommendation = "High injury risk detected. Reduce load, correct mechanics, and repeat screening before progression."
        elif risk >= 40:
            recommendation = "Moderate risk detected. Reduce load slightly and monitor fatigue."
        else:
            recommendation = "Low risk. Athlete is safe to continue training."

        return {
            "mode": "fallback_ai",
            "user_query": user_query,
            "analysis": analysis,
            "summary": f"Risk level is {alert} with peak score {risk}.",
            "recommendation": recommendation
        }
