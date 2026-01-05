import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ---------------- AUTH (UI + SESSION) ----------------
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "operator": {"password": "op123", "role": "Operator"},
    "viewer": {"password": "view123", "role": "Viewer"},
}

if "auth" not in st.session_state:
    st.session_state.auth = {"is_logged_in": False, "username": None, "role": None}

def login_screen():
    st.subheader("Sign in")
    st.caption("Use your username and password to access the dashboard.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        u = USERS.get(username.strip())
        if u and password == u["password"]:
            st.session_state.auth = {
                "is_logged_in": True,
                "username": username.strip(),
                "role": u["role"],
            }
            st.rerun()
        else:
            st.error("Invalid credentials.")



# ---------------- CONFIG ----------------
# Try to get Backend URL from Secrets (Cloud), otherwise use Localhost
if "BACKEND_URL" in st.secrets:
    BACKEND_URL = st.secrets["BACKEND_URL"]
else:
    BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Pipeline Leakage Dashboard", layout="wide")

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
    /* Global Background and Font */
    .stApp {
        background-color: #0e1117;
        font-family: 'Inter', sans-serif;
    }
    
    /* Metrics as Cards */
    div[data-testid="metric-container"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 15px;
        border-radius: 10px;
        color: #ffffff;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        transition: transform 0.2s;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: scale(1.02);
        border-color: #ff4b4b;
    }

    /* Headers */
    h1, h2, h3 {
        color: #ffffff;
        font-weight: 700;
    }
    
    /* Custom Alert Styles */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1a1c24;
    }
</style>
""", unsafe_allow_html=True)

st.title("Water Pipeline Monitoring Dashboard")
st.caption("Live Monitoring System (ESP32 Modbus RTU + FastAPI)")
# Require login before rendering the dashboard
if not st.session_state.auth["is_logged_in"]:
    login_screen()
    st.stop()


# ---------------- SESSION STATE ----------------
if "alert_log" not in st.session_state:
    st.session_state.alert_log = []

if "last_status_by_node" not in st.session_state:
    st.session_state.last_status_by_node = {}
# ---------------- SIDEBAR: USER ----------------
st.sidebar.markdown("### Account")
st.sidebar.write(f"**User:** {st.session_state.auth['username']}")
st.sidebar.write(f"**Role:** {st.session_state.auth['role']}")

if st.sidebar.button("Sign out"):
    st.session_state.auth = {"is_logged_in": False, "username": None, "role": None}
    st.rerun()

st.sidebar.markdown("---")

# ---------------- SIDEBAR ----------------
refresh_seconds = st.sidebar.slider("Refresh interval (seconds)", 1, 10, 2)
auto_refresh = st.sidebar.toggle("Auto refresh", value=True)

node_id = st.sidebar.selectbox(
    "Select Sensor Node",
    options=[1, 2, 3],
    index=0
)

if st.sidebar.button("Clear Alert History"):
    if st.session_state.auth["role"] != "Admin":
        st.sidebar.error("You don’t have permission to clear history.")
    else:
        st.session_state.alert_log = []
        st.session_state.last_status_by_node = {}
        st.sidebar.success("Alert history cleared.")


history_view = st.sidebar.radio(
    "Alert History View",
    options=["Selected node only", "All nodes"],
    index=0
)

# ---------------- BACKEND HELPERS ----------------
def backend_is_alive():
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

alive = backend_is_alive()

if alive:
    st.sidebar.success("✅ Backend Connected")
else:
    st.sidebar.error("❌ Backend Disconnected")


def fetch_latest(node_id: int):
    r = requests.get(f"{BACKEND_URL}/api/latest/{node_id}", timeout=4)
    r.raise_for_status()
    return r.json()


def fetch_history(node_id: int):
    r = requests.get(f"{BACKEND_URL}/api/history/{node_id}", timeout=4)
    r.raise_for_status()
    return r.json()["points"]


def fetch_predictive(node_id: int, short_window: int = 30, long_window: int = 120):
    r = requests.get(
        f"{BACKEND_URL}/api/predictive/{node_id}",
        params={"short_window": short_window, "long_window": long_window},
        timeout=4
    )
    r.raise_for_status()
    return r.json()


# ---------------- UI HELPERS ----------------
def status_style(status: str) -> str:
    if status == "LEAK DETECTED":
        return "🚨 LEAK DETECTED"
    if status == "SUSPECTED":
        return "⚠️ SUSPECTED"
    return "✅ NORMAL"


def show_alert_banner(status: str):
    if status == "LEAK DETECTED":
        st.error("🚨 LEAK DETECTED — Immediate inspection required!")
    elif status == "SUSPECTED":
        st.warning("⚠️ SUSPECTED LEAK — Please monitor closely.")
    else:
        st.success("✅ NORMAL — Pipeline operating within expected range.")


# ---------------- MAIN RENDER ----------------
def render():
    latest = fetch_latest(node_id)
    points = fetch_history(node_id)

    current_status = latest.get("leak_status")
    prev_status = st.session_state.last_status_by_node.get(node_id)

    # Log only on status change
    if prev_status != current_status:
        st.session_state.alert_log.append({
            "time": latest.get("timestamp"),
            "node": node_id,
            "status": current_status,
            "leak_score": latest.get("leak_score"),
            "estimated_node": latest.get("estimated_node"),
            "distance_m": latest.get("estimated_distance_m"),
        })
        st.session_state.alert_log = st.session_state.alert_log[-50:]
        st.session_state.last_status_by_node[node_id] = current_status

    df = pd.DataFrame(points)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

    tab_live, tab_predictive = st.tabs(["Live Monitoring", "Predictive Maintenance"])

    with tab_live:
        placeholder_top = st.empty()
        placeholder_charts = st.empty()

        show_alert_banner(current_status)
        st.caption(f"Viewing data for Node {node_id}")

        st.subheader("Leak Localization")
        c1, c2, c3 = st.columns(3)
        c1.metric("Estimated Node", latest.get("estimated_node"))
        c2.metric("Distance from Start (m)", latest.get("estimated_distance_m"))
        c3.metric("Node Spacing (m)", latest.get("node_spacing_m"))

        with placeholder_top.container():
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Pressure (bar)", latest["pressure_bar"])
            m2.metric("Flow (L/min)", latest["flow_lpm"])
            m3.metric("Vibration", latest["vibration"])
            m4.metric("Turbidity (NTU)", latest["turbidity_ntu"])
            m5.metric("TDS (ppm)", latest["tds_ppm"])
            m6.metric("Leak Status", status_style(current_status))

        with placeholder_charts.container():
            if not df.empty:
                left, right = st.columns(2)
                with left:
                    st.subheader("Pressure & Flow Trend")
                    st.line_chart(df.set_index("timestamp")[["pressure_bar", "flow_lpm"]])
                with right:
                    st.subheader("Vibration, Turbidity, TDS Trend")
                    st.line_chart(df.set_index("timestamp")[["vibration", "turbidity_ntu", "tds_ppm"]])
            else:
                st.info("No history yet for this node. Let it run for a few seconds.")

        st.subheader("Alert History (Last 50 Status Changes)")
        log_df = pd.DataFrame(st.session_state.alert_log)

        if not log_df.empty:
            if history_view == "Selected node only":
                log_df = log_df[log_df["node"] == node_id]

            if log_df.empty:
                st.info("No status changes for this node yet.")
            else:
                st.dataframe(log_df[::-1], use_container_width=True)
        else:
            st.info("No status changes logged yet.")

    with tab_predictive:
        st.subheader("Predictive Maintenance (Level 1 — Trend & Health Index)")
        st.caption("This does not claim a leak exists; it estimates risk based on drift/instability patterns.")

        role = st.session_state.auth["role"]
        can_tune = role in ("Admin", "Operator")

        if can_tune:
            short_window = st.slider("Short window (recent samples)", 10, 120, 30)
            long_window = st.slider("Long window (baseline samples)", 30, 300, 120)
        else:
            short_window, long_window = 30, 120
            st.info("Read-only access: using default predictive settings.")

        try:
            pred = fetch_predictive(node_id, short_window=short_window, long_window=long_window)
            risk_score = int(pred.get("risk_score", 0))
            risk_level = pred.get("risk_level", "UNKNOWN")

            eta_hours = pred.get("eta_hours", None)
            likely_segment = pred.get("likely_segment", "N/A")
            dominant_factor = pred.get("dominant_factor", "N/A")

            c3, c4, c5 = st.columns(3)
            c3.metric("Expected Issue Window", f"~{eta_hours} hours" if eta_hours else "N/A")
            c4.metric("Likely Segment", likely_segment)
            c5.metric("Main Driver", dominant_factor)

            c1, c2 = st.columns(2)
            c1.metric("Risk Level", risk_level)
            c2.metric("Risk Score (0–100)", risk_score)

            st.progress(min(max(risk_score, 0), 100))

            # Risk history (in-memory, per session)
            if "risk_history" not in st.session_state:
                st.session_state.risk_history = []

            st.session_state.risk_history.append({
                "timestamp": pd.Timestamp.utcnow(),
                "node_id": node_id,
                "risk_score": risk_score
            })
            st.session_state.risk_history = st.session_state.risk_history[-200:]

            rh = pd.DataFrame(st.session_state.risk_history)
            rh = rh[rh["node_id"] == node_id]
            if not rh.empty:
                st.subheader("Risk Trend (History)")
                st.line_chart(rh.set_index("timestamp")[["risk_score"]])

            st.markdown("**Why this score increased:**")
            for reason in pred.get("reasons", []):
                st.write(f"- {reason}")

            if not df.empty:
                st.subheader("Recent Window View")
                recent = df.tail(short_window) if len(df) > short_window else df
                st.line_chart(
                    recent.set_index("timestamp")[["pressure_bar", "flow_lpm", "vibration", "turbidity_ntu"]]
                )

        except Exception as e:
            st.error(f"Predictive endpoint not reachable or failed: {e}")
            st.info("Restart the backend after updating backend.py, then refresh this page.")


# ---------------- RUN ----------------
if auto_refresh:
    st_autorefresh(interval=refresh_seconds * 1000, key="auto_refresh")

if alive:
    render()
else:
    st.info("Start the backend to see live data.")
