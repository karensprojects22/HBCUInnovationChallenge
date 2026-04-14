"""
ATHLETIQ AI AGENT
Simple ReAct-style coaching assistant
"""

import httpx
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"


# -----------------------------------
# TOOL: call your FastAPI backend
# -----------------------------------
async def get_risk_analysis():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://127.0.0.1:8000/api/demo")
        return response.json()


# -----------------------------------
# AI AGENT CORE
# -----------------------------------
async def run_agent(user_query: str):
    analysis = await get_risk_analysis()

    system_prompt = f"""
    You are an elite sports biomechanics AI coach.

    You analyze injury risk and give training recommendations.

    DATA:
    {json.dumps(analysis, indent=2)}

    USER QUESTION:
    {user_query}

    TASK:
    - Interpret risk scores
    - Explain injury risk
    - Give actionable training advice
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt}
                ]
            }
        )

        return response.json()