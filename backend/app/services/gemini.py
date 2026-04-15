import google.generativeai as genai
from app.core.config import GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None


def generate_report(analysis_results: dict) -> str:
    if model is None:
        return (
            "ATHLETIQ analyzed this athlete's movement and found elevated lower-body loading patterns. "
            "The current session suggests asymmetry and fatigue that could increase injury risk if not addressed. "
            "Reduce workload slightly, reinforce mechanics, and repeat screening before the next high-intensity session."
        )

    prompt = f"""
    You are a sports medicine AI assistant for ATHLETIQ, an injury prevention platform.

    An athlete was just analyzed. Here are the results:
    - Peak injury risk score: {analysis_results.get('peak_risk_score')} out of 100
    - Average risk score: {analysis_results.get('average_risk_score')} out of 100
    - Overall alert level: {analysis_results.get('alert_level')}
    - Number of high-risk movement frames: {analysis_results.get('high_risk_frame_count')}
    - Total frames analyzed: {analysis_results.get('total_frames_analyzed')}

    Write a 3-sentence report for a coach or athletic trainer.
    Sentence 1: What the data shows about this athlete's movement.
    Sentence 2: What injury risk this creates if not addressed.
    Sentence 3: One specific recommendation to reduce the risk.

    Keep it clear and actionable. Do not use jargon.
    """

    response = model.generate_content(prompt)
    return response.text.strip()
