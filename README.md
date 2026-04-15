# HBCUInnovationChallenge

ATHLETIQ is a full-stack neuromuscular injury-risk platform for athlete movement analysis.

## Current Stack

- Front end: Next.js 14 + React + TypeScript
- Back end: FastAPI + Python
- Vision model: YOLOv8 pose
- Biomechanics layer: DSU patent-inspired scoring engine
- AI layer: Ollama + Llama 3 coach assistant
- Current storage: in-memory session state for demo

## How The Architecture Maps To The Pitch

- Capture layer: athlete uploads a standard camera video
- Vision layer: YOLOv8 extracts pose keypoints from the uploaded video
- Patent layer: the DSU biomechanics engine turns pose and loading proxies into risk metrics
- Digital twin layer: the front end renders a stylized athlete rig driven by the extracted pose frames
- AI coach layer: the agent translates technical outputs into coach-facing movement guidance

## Demo Run Guide

### 1. Start the FastAPI backend

```bash
cd /Users/karenalabi/source/HBCUInnovationChallenge/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Start the Next.js frontend

```bash
cd /Users/karenalabi/source/HBCUInnovationChallenge/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### 3. Open the app

- Frontend: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 4. Demo flow

1. Upload an athlete movement video
2. Click `Analyze Athlete Motion`
3. Show the source video, digital twin, and YOLO extraction summary
4. Walk through peak risk, asymmetry, fatigue, and the AI movement report

## What The AI Agent Does

The AI agent is not the detector. It is the coach-facing interpretation layer.

- YOLOv8 detects the pose
- the patent engine computes risk signals
- the AI agent explains what those signals mean and what action a trainer should take

## What To Say If Judges Ask About Scope

- ATHLETIQ is designed for multiple sports because the current capture method is movement-based, not sport-locked
- the current MVP is strongest for training, screening, return-to-play review, and post-session analysis
- the same architecture can later support near-real-time sideline review once live capture is integrated
