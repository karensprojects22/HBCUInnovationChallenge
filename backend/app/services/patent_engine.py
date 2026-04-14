import math

GRAVITY_MS2 = 9.81
DEFAULT_MASS_KG = 80.0
MAX_CONTRACTION = 1.0


def ground_reaction_force(emg: float,
                           mvc: float = MAX_CONTRACTION,
                           weight_kg: float = DEFAULT_MASS_KG) -> float:
    weight_n = weight_kg * GRAVITY_MS2
    return round((emg / max(mvc, 1e-9)) * weight_n, 2)


def joint_angle(ax, ay, bx, by, cx, cy):
    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)

    dot = v1[0]*v2[0] + v1[1]*v2[1]
    mag = math.sqrt(v1[0]**2 + v1[1]**2) * math.sqrt(v2[0]**2 + v2[1]**2)

    if mag < 1e-9:
        return 180.0

    cos_angle = max(-1.0, min(1.0, dot / mag))
    return round(math.degrees(math.acos(cos_angle)), 2)


def asymmetry_index(left: float, right: float) -> float:
    total = left + right
    if total < 1e-6:
        return 0.0
    return round(abs(left - right) / total, 4)


def composite_risk_score(fatigue, asymmetry, peak_emg):
    score = (fatigue * 40) + (asymmetry * 35) + (peak_emg * 25)
    return min(round(score, 1), 100.0)


def alert_level(score: float) -> str:
    if score >= 65:
        return "HIGH"
    elif score >= 40:
        return "MODERATE"
    return "LOW"


def process_frame(row: dict) -> dict:
    emg_l = float(row.get("emg_left", 0))
    emg_r = float(row.get("emg_right", 0))
    fatigue = float(row.get("fatigue", 0))

    grf_l = ground_reaction_force(emg_l)
    grf_r = ground_reaction_force(emg_r)

    asym = asymmetry_index(emg_l, emg_r)
    score = composite_risk_score(fatigue, asym, emg_r)

    return {
        "frame": int(row.get("frame", 0)),
        "emg_left": emg_l,
        "emg_right": emg_r,
        "grf_left": grf_l,
        "grf_right": grf_r,
        "asymmetry": asym,
        "risk_score": score,
        "alert": alert_level(score)
    }