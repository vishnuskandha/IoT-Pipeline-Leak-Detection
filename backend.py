from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import random

app = FastAPI(title="Pipeline Dummy Backend")

# Allow Streamlit (frontend) to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory history buffer (simple for demo)
HISTORY = []
MAX_POINTS = 300  # last ~300 samples


def simulate_sensor_reading():
    """
    Generates a single reading with mild noise.
    Occasionally injects a 'leak-like' pattern.
    """
    # Base normal operating values (tweak anytime)
    base_pressure = 3.2  # bar
    base_flow = 18.0     # L/min
    base_vibration = 0.15
    base_turbidity = 3.0  # NTU
    base_tds = 420        # ppm

    # Normal noise
    pressure = base_pressure + random.uniform(-0.08, 0.08)
    flow = base_flow + random.uniform(-0.8, 0.8)
    vibration = base_vibration + random.uniform(-0.03, 0.03)
    turbidity = base_turbidity + random.uniform(-0.5, 0.5)
    tds = base_tds + random.uniform(-12, 12)

    # Occasionally inject anomaly (simulate leak)
    anomaly = random.random() < 0.06  # ~6% chance
    if anomaly:
        pressure -= random.uniform(0.25, 0.6)
        flow += random.uniform(1.5, 3.5)
        vibration += random.uniform(0.15, 0.35)
        turbidity += random.uniform(1.0, 2.5)

    # Simple rule-based "leak status" placeholder (replace later with ML)
    leak_score = 0
    leak_score += 1 if pressure < 2.8 else 0
    leak_score += 1 if flow > 21.0 else 0
    leak_score += 1 if vibration > 0.28 else 0
    leak_score += 1 if turbidity > 5.0 else 0

    if leak_score >= 3:
        status = "LEAK DETECTED"
    elif leak_score == 2:
        status = "SUSPECTED"
    else:
        status = "NORMAL"

    # Dummy leak localization
    node_count = 3
    node_spacing_m = 50
    estimated_node = random.randint(1, node_count)
    estimated_distance_m = (estimated_node - 1) * node_spacing_m

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pressure_bar": round(pressure, 3),
        "flow_lpm": round(flow, 2),
        "vibration": round(vibration, 3),
        "turbidity_ntu": round(turbidity, 2),
        "tds_ppm": round(tds, 1),
        "leak_status": status,
        "leak_score": leak_score,
        "estimated_node": estimated_node,
        "estimated_distance_m": estimated_distance_m,
        "node_spacing_m": node_spacing_m,
    }


def push_history(point):
    HISTORY.append(point)
    if len(HISTORY) > MAX_POINTS:
        HISTORY.pop(0)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Backend running. Try /api/health or /api/latest/1"}


@app.get("/api/latest/{node_id}")
def latest_node(node_id: int):
    # 1. Try to find the latest real data for this node in history
    # Filter points for this node
    node_points = [p for p in HISTORY if p.get("node_id") == node_id]
    
    if node_points:
        # Return the most recent point (last ONE added)
        return node_points[-1]
    
    # 2. If no real data, return "Waiting" placeholder (Zeroes)
    # This prevents random confusion.
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "node_id": node_id,
        "pressure_bar": 0.0,
        "flow_lpm": 0.0,
        "vibration": 0.0,
        "turbidity_ntu": 0.0,
        "tds_ppm": 0.0,
        "leak_status": "WAITING FOR DATA",
        "leak_score": 0,
        "estimated_node": 0,
        "estimated_distance_m": 0,
        "node_spacing_m": 50,
    }


@app.get("/api/history/{node_id}")
def history_node(node_id: int):
    node_points = [p for p in HISTORY if p.get("node_id") == node_id]
    return {"points": node_points}


from pydantic import BaseModel

class SensorData(BaseModel):
    node_id: int
    tds: float
    turbidity: float
    flow: float
    is_leak: bool

@app.post("/api/sensor-data")
def receive_sensor_data(data: SensorData):
    # Convert bool status to string for frontend compatibility
    status = "LEAK DETECTED" if data.is_leak else "NORMAL"
    
    # Create a record compatible with the existing frontend
    # We fill missing fields (pressure, vibration) with defaults or dummy values
    # to prevent the frontend from crashing.
    point = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "node_id": data.node_id,
        "pressure_bar": 0.0,  # Not measured by these sensors
        "flow_lpm": round(data.flow, 2),
        "vibration": 0.0,     # Not measured
        "turbidity_ntu": round(data.turbidity, 2),
        "tds_ppm": round(data.tds, 1),
        "leak_status": status,
        "leak_score": 100 if data.is_leak else 0,
        "estimated_node": data.node_id if data.is_leak else 0,
        "estimated_distance_m": 0, # Could be calculated if we knew position
        "node_spacing_m": 50,
    }
    
    push_history(point)
    return {"status": "received", "data": point}

# ---------------- PREDICTIVE MAINTENANCE (LEVEL 1, NO TRAINING) ----------------

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return var ** 0.5


def _slope(xs):
    """
    Simple linear slope of xs over time index 0..n-1.
    Returns slope per sample.
    """
    n = len(xs)
    if n < 3:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = _mean(xs)
    num = sum((i - x_mean) * (xs[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return (num / den) if den != 0 else 0.0


def compute_predictive_risk(node_points, short_window=30, long_window=120):
    """
    Level-1 risk score based on:
    - slow negative pressure drift
    - rising vibration baseline
    - rising turbidity trend / volatility
    - pressure/flow coupling instability (proxy)
    Output: risk_score 0..100 + reasons (explainable)
    """
    if not node_points:
        return {
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "reasons": ["No data for this node yet."],
            "short_window": short_window,
            "long_window": long_window
        }

    points = node_points[-max(long_window, short_window):]

    p = [_safe_float(pt.get("pressure_bar")) for pt in points]
    f = [_safe_float(pt.get("flow_lpm")) for pt in points]
    v = [_safe_float(pt.get("vibration")) for pt in points]
    t = [_safe_float(pt.get("turbidity_ntu")) for pt in points]

    long_p = p[-long_window:] if len(p) >= long_window else p
    long_f = f[-long_window:] if len(f) >= long_window else f
    long_v = v[-long_window:] if len(v) >= long_window else v
    long_t = t[-long_window:] if len(t) >= long_window else t

    short_p = p[-short_window:] if len(p) >= short_window else p
    short_f = f[-short_window:] if len(f) >= short_window else f
    short_v = v[-short_window:] if len(v) >= short_window else v
    short_t = t[-short_window:] if len(t) >= short_window else t

    p_slope = _slope(short_p)     # negative suspicious
    v_slope = _slope(short_v)     # positive suspicious
    t_slope = _slope(short_t)     # positive suspicious

    t_std_long = _std(long_t)
    t_std_short = _std(short_t)
    v_std_long = _std(long_v)
    v_std_short = _std(short_v)

    ratio_long = []
    ratio_short = []
    for i in range(len(long_p)):
        denom = long_f[i] if long_f[i] != 0 else 1.0
        ratio_long.append(long_p[i] / denom)
    for i in range(len(short_p)):
        denom = short_f[i] if short_f[i] != 0 else 1.0
        ratio_short.append(short_p[i] / denom)

    ratio_std_long = _std(ratio_long)
    ratio_std_short = _std(ratio_short)

    risk = 0.0
    reasons = []

    if p_slope < -0.001:
        add = min(30.0, abs(p_slope) * 20000.0)
        risk += add
        reasons.append(f"Pressure is drifting down (slope={p_slope:.4f}/sample).")

    if v_slope > 0.0005:
        add = min(25.0, v_slope * 20000.0)
        risk += add
        reasons.append(f"Vibration baseline is rising (slope={v_slope:.4f}/sample).")

    if t_slope > 0.005:
        add = min(15.0, t_slope * 500.0)
        risk += add
        reasons.append(f"Turbidity is trending upward (slope={t_slope:.4f}/sample).")

    if t_std_long > 0 and t_std_short > (t_std_long * 1.4):
        risk += 10.0
        reasons.append("Turbidity short-term volatility increased vs baseline.")

    if v_std_long > 0 and v_std_short > (v_std_long * 1.4):
        risk += 10.0
        reasons.append("Vibration short-term volatility increased vs baseline.")

    if ratio_std_long > 0 and ratio_std_short > (ratio_std_long * 1.5):
        risk += 10.0
        reasons.append("Pressure-to-flow relationship looks less stable than usual.")

    risk = max(0.0, min(100.0, risk))

    if not reasons:
        level = "LOW"
        reasons = ["No meaningful drift/instability detected in the recent window."]
    elif risk >= 70:
        level = "HIGH"
    elif risk >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
        # --- ETA (Expected issue window) heuristic ---
    # You can tune these later; the point is: explainable early-warning, not a promise.
    if risk >= 70:
        eta_hours = 6
    elif risk >= 40:
        eta_hours = 24
    else:
        eta_hours = 72

    # Dominant factor (for explainability)
    dominant_factor = "STABLE"
    if p_slope < -0.001:
        dominant_factor = "PRESSURE_DRIFT"
    if v_slope > 0.0005 and risk >= 40:
        dominant_factor = "VIBRATION_DRIFT"

    # Likely segment wording (node-based)
    # If estimated_node exists in latest reading, we can reuse it; otherwise use current node_id.
    likely_node = node_points[-1].get("estimated_node") or node_points[-1].get("node_id") or 1
    node_spacing_m = node_points[-1].get("node_spacing_m") or 50
    start_m = max(0, (likely_node - 1) * node_spacing_m)
    end_m = start_m + node_spacing_m
    likely_segment = f"Near Node {likely_node} (approx {start_m}m – {end_m}m)"

    return {
        "risk_score": int(round(risk)),
        "risk_level": level,
        "eta_hours": eta_hours,
        "dominant_factor": dominant_factor,
        "likely_segment": likely_segment,
        "reasons": reasons,
        "short_window": short_window,
        "long_window": long_window
    }


    return {
        "risk_score": int(round(risk)),
        "risk_level": level,
        "reasons": reasons,
        "short_window": short_window,
        "long_window": long_window
    }


@app.get("/api/predictive/{node_id}")
def predictive_node(node_id: int, short_window: int = 30, long_window: int = 120):
    node_points = [p for p in HISTORY if p.get("node_id") == node_id]
    return compute_predictive_risk(node_points, short_window=short_window, long_window=long_window)
