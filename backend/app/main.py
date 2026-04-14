from fastapi import FastAPI
from backend.app.api import analysis
from backend.app.services.ai_agent import run_agent

app = FastAPI()

# Existing demo route
app.include_router(analysis.router, prefix="/api")


# AI AGENT ENDPOINT (NEW — CORE DEMO)
@app.get("/agent")
async def agent_endpoint(query: str):
    result = await run_agent(query)
    return {
        "query": query,
        "agent_response": result
    }


@app.get("/")
def root():
    return {"status": "ATHLETIQ backend running"}