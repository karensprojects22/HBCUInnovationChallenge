# HBCUInnovationChallenge

## ATHLETIQ Live Demo

ATHLETIQ is a demo MVP for AI-accelerated biomechanics research and injury-risk screening.

### Live MVP stack

- Frontend: static HTML, Tailwind CDN, Chart.js
- Backend: FastAPI + Python
- Pose detection: YOLOv8 pose
- Biomechanics layer: DSU patent-inspired neuromuscular risk engine
- AI reporting: Google Gemini 1.5 Flash

### What the demo does

1. Upload a movement video.
2. YOLOv8 extracts lower-body keypoints from the athlete.
3. The patent-inspired engine computes asymmetry, fatigue, GRF proxies, and risk.
4. Gemini writes a coach-facing movement report.
5. The dashboard shows the uploaded video, digital twin playback, timeline risk, and frame-by-frame analysis.

### Demo-day run command

From the repo root:

```bash
./run-demo.sh
```

Then open:

```text
http://127.0.0.1:8000
```

### First-time setup on a teammate's machine

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If a `backend/.env` file is available, add:

```env
GEMINI_API_KEY=your_key_here
```

Without a Gemini key, the demo still runs with a safe fallback report.
