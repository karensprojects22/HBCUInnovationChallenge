from fastapi import FastAPI
from app.api.analysis import router as analysis_router

app = FastAPI()

app.include_router(analysis_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Backend is running"}