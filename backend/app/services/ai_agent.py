# ATHLETIQ AI agent (demo-safe version)


import httpx
import json

# Local development model. This follows the DSU workshop pattern:
# FastAPI exposes an endpoint and Ollama serves the Llama-family model locally.
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"


# Tool 1 in the agent loop: fetch the latest motion-analysis summary from FastAPI.

async def get_risk_analysis():
    """
    Calls the local FastAPI backend for structured risk data the agent can reason over.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get("http://127.0.0.1:8000/api/demo")
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


# Core agent entry point. Right now this is a lightweight one-step pattern rather than a
# full multi-tool ReAct loop, but the structure is intentionally compatible with that direction.

async def run_agent(user_query: str):
    analysis = await get_risk_analysis()

    # The system prompt gives the model the same structured context a future tool-calling
    # agent would use: current data, user question, and the action we want from the model.
    system_prompt = f"""
You are an elite sports biomechanics AI coach.

You analyze injury risk and give training recommendations.

DATA:
{json.dumps(analysis, indent=2)}

USER QUESTION:
{user_query}

TASK:
- Interpret risk scores
- Explain injury risk clearly
- Give actionable training advice
"""

    
    # Try the real local LLM first so the demo reflects the DSU workshop architecture.

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ]
                }
            )

            result = response.json()

            return {
                "mode": "llm",
                "response": result
            }

    
    # Guaranteed fallback keeps the coach panel functional if Ollama is offline.
    
    except Exception:
        risk = analysis.get("peak_risk_score", 0)
        alert = analysis.get("alert_level", "UNKNOWN")

        if risk >= 70:
            recommendation = "High injury risk detected..."
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
