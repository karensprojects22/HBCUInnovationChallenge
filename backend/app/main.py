from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from app.api import analysis
from app.services.ai_agent import run_agent

app = FastAPI()
FRONTEND_FILE = Path(__file__).resolve().parents[2] / "frontend" / "index.html"

# Allow the static HTML demo to call this API from `file://` or another local origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core motion-analysis routes used by the dashboard.
app.include_router(analysis.router, prefix="/api")


# Local LLM endpoint used by the "AI coach" panel in the front-end.
@app.get("/agent")
async def agent_endpoint(query: str):
    result = await run_agent(query)
    return {
        "query": query,
        "agent_response": result
    }


@app.get("/health")
def health():
    # Lightweight health check so the front-end can show backend-online status.
    return {"status": "ATHLETIQ backend running"}


@app.get("/dashboard")
def dashboard():
    # Serve the front-end from FastAPI so the browser and API share the same origin.
    return FileResponse(FRONTEND_FILE)


@app.get("/")
def root():
    return FileResponse(FRONTEND_FILE)
