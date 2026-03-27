import os
import sys
import json
import time
import pandas as pd
import pydeck as pdk
import streamlit as st
from pathlib import Path

# Add the current directory to path so we can import local modules easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02_analyst_module"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "03_intel_module"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04_manager_module"))

from chaos_trigger import trigger_chaos
from scout_agent import process_signal

# Paths to shared exchange
BASE_DIR = Path(__file__).parent.parent
SHARED_DIR = BASE_DIR / "shared_exchange"

SCOUT_PATH = SHARED_DIR / "scout_output.json"
ANALYST_PATH = SHARED_DIR / "analyst_output.json"
INTEL_PATH = SHARED_DIR / "intel_output.json"
FINAL_RESULTS_PATH = SHARED_DIR / "final_results.json"

KERALA_HUBS = {
    "Kochi": {"lon": 76.2605, "lat": 10.0153},
    "Thrissur": {"lon": 76.2105, "lat": 10.5276},
    "Palakkad": {"lon": 76.5214, "lat": 10.7733},
    "Wayanad": {"lon": 76.1323, "lat": 11.6854},
    "Kozhikode": {"lon": 75.7772, "lat": 11.2588},
    "Thiruvananthapuram": {"lon": 76.9728, "lat": 8.4855},
    "Mumbai": {"lon": 72.8777, "lat": 19.0760},
    "Bangalore": {"lon": 77.5946, "lat": 12.9716},
    "Chennai": {"lon": 80.2707, "lat": 13.0827},
    "Delhi": {"lon": 77.2090, "lat": 28.6139},
    "Hyderabad": {"lon": 78.4867, "lat": 17.3850},
    "Mangalore": {"lon": 74.8560, "lat": 12.9141},
    "Cochin Port": {"lon": 76.2619, "lat": 9.9634}
}

st.set_page_config(page_title="NexusPath Dashboard", layout="wide", initial_sidebar_state="expanded")

# -----------------
# UTILITIES
# -----------------
def load_json(filepath):
    """Safely loads a JSON file. Returns None if it doesn't exist or is invalid."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def inject_custom_css():
    """Injects futuristic dark purple gradient and modern typography."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap');
        
        /* Futuristic Gradient Background */
        .stApp {
            background: radial-gradient(circle at top right, #1e1b4b, #0f172a, #020617);
            color: #f8fafc;
            font-family: 'Outfit', sans-serif !important;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }

        /* Neon Glow Card */
        .card {
            background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(12px);
            border-radius: 1.5rem;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(99, 102, 241, 0.2);
            color: #f8fafc;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            box-shadow: 0 0 40px rgba(99, 102, 241, 0.2);
        }

        .dark-card {
            background: rgba(2, 6, 23, 0.8);
            border-radius: 1.5rem;
            padding: 2.5rem;
            border: 1px solid rgba(148, 163, 184, 0.1);
            height: 100%;
        }

        .title-glow {
            text-shadow: 0 0 30px rgba(99, 102, 241, 0.6);
            background: linear-gradient(90deg, #fff, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
        }

        /* Metric Typography Override for Futuristic Feel */
        .metric-value {
            font-size: 4.5rem;
            font-weight: 900;
            line-height: 1;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 25px rgba(129, 140, 248, 0.4);
        }
        .metric-label {
            font-size: 1.15rem;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        /* Route Info Panel */
        .info-panel {
            display: flex;
            justify-content: space-around;
            background: rgba(30, 41, 59, 0.5);
            padding: 1.5rem;
            border-radius: 1rem;
            margin-top: -1rem;
            border: 1px solid rgba(99, 102, 241, 0.1);
        }
        .info-item { text-align: center; }
        .info-val { font-size: 1.5rem; font-weight: 700; color: #818cf8; }
        .info-lab { font-size: 0.8rem; text-transform: uppercase; color: #94a3b8; }

        /* Agent Monologue Styles */
        .agent-label {
            font-weight: 700;
            color: #f8fafc;
            font-size: 1.25rem;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
        }
        .agent-thought {
            border-left: 4px solid #818cf8;
            padding: 1.5rem;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
            color: #e2e8f0;
            background: rgba(30, 41, 59, 0.4);
            border-radius: 0 0.75rem 0.75rem 0;
        }

        .map-container {
            border-radius: 1.5rem;
            overflow: hidden;
            border: 1px solid rgba(99, 102, 241, 0.3);
            margin-top: 1rem;
            margin-bottom: 2.5rem;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }

        /* --- DEMO MODE CSS --- */
        .step-panel {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 1rem;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px dashed rgba(99, 102, 241, 0.3);
        }
        .step-active {
            color: #818cf8;
            font-weight: 700;
            border-left: 4px solid #818cf8;
            padding-left: 1rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, rgba(129, 140, 248, 0.1) 0%, transparent 100%);
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
        .step-inactive {
            color: #475569;
            padding-left: 1rem;
            margin-bottom: 0.5rem;
        }
        .demo-msg {
            color: #818cf8;
            font-style: italic;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(99, 102, 241, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)

def get_detailed_path(start, end, mode, location_name):
    """Generates a high-fidelity multi-segment path simulation for logistics routes."""
    # Predefined 'Spine Waypoints' for Kerala/India Logistics Corridors
    SPINES = {
        "Mumbai": [
            [72.87, 19.07], # Mumbai
            [73.85, 18.52], # Pune
            [73.98, 15.29], # Goa
            [74.85, 12.91], # Mangalore
            [76.26, 9.96]   # Cochin Port
        ],
        "Bangalore": [
            [77.59, 12.97], # Bangalore
            [78.14, 11.66], # Salem
            [76.52, 10.77], # Palakkad
            [76.21, 10.52], # Thrissur
            [76.26, 9.96]   # Cochin Port
        ],
        "Chennai": [
            [80.27, 13.08], # Chennai
            [79.13, 12.91], # Vellore
            [78.14, 11.66], # Salem
            [76.52, 10.77], # Palakkad
            [76.26, 9.96]   # Cochin Port
        ],
        "Thiruvananthapuram": [
            [76.97, 8.48],  # TVM
            [76.60, 8.89],  # Kollam
            [76.33, 9.49],  # Alappuzha
            [76.26, 9.96]   # Cochin Port
        ]
    }
    
    # If route is unknown, provide a 'Bypass' jittered path to look 'detailed'
    if location_name in SPINES:
        path = SPINES[location_name]
    else:
        # Default with a slight "logistics curve"
        mid_lon = (start[0] + end[0]) / 2 + 0.1
        mid_lat = (start[1] + end[1]) / 2 + 0.05
        path = [start, [mid_lon, mid_lat], end]

    if mode == "SHIP":
        # Maritime route must stay in the West Sea
        maritime_path = [[start[0], start[1]]]
        for wp in path[1:-1]:
            maritime_path.append([wp[0] - 1.2, wp[1]]) # Offset way out into sea
        maritime_path.append([end[0], end[1]])
        return maritime_path
    
    if mode == "AIR":
        # Direct flight vectors
        return [start, end]
        
    return path

def render_map(location_name, severity="HIGH"):
    """Renders a high-fidelity interactive mult-mode logistics map."""
    start_loc = KERALA_HUBS.get("Cochin Port")
    end_loc = KERALA_HUBS.get(location_name) if location_name in KERALA_HUBS else KERALA_HUBS.get("Kochi")
    
    # Mode selection from session state
    mode = st.session_state.get("selected_mode", "TRUCK")
    
    colors = {
        "LOW": [34, 197, 94, 200],
        "MEDIUM": [234, 179, 8, 200],
        "HIGH": [249, 115, 22, 200],
        "CRITICAL": [239, 68, 68, 255]
    }
    base_color = colors.get(severity.upper(), colors["HIGH"])
    
    # Get high-fidelity simulated road/path
    path_data = get_detailed_path([start_loc["lon"], start_loc["lat"]], [end_loc["lon"], end_loc["lat"]], mode, location_name)
    
    mode_colors = {
        "SHIP": [30, 64, 175, 255], # Deep Blue
        "AIR": [6, 182, 212, 255],  # Cyan
        "RAIL": [71, 85, 105, 255], # Slate
        "TRUCK": base_color
    }
    mode_color = mode_colors.get(mode, base_color)

    route_df = pd.DataFrame([{"path": path_data}])
    marker_df = pd.DataFrame([
        {"lon": start_loc["lon"], "lat": start_loc["lat"], "tag": "ORIGIN"},
        {"lon": end_loc["lon"], "lat": end_loc["lat"], "tag": "DISRUPTION SITE"}
    ])

    route_layer = pdk.Layer(
        "PathLayer", route_df, get_path="path", get_color=mode_color, 
        width_scale=10, width_min_pixels=6, rounded=True, pickable=True
    )
    marker_layer = pdk.Layer("ScatterplotLayer", marker_df, get_position="[lon, lat]", get_color="[255, 255, 255, 255]", get_radius=2000)
    glow_layer = pdk.Layer("ScatterplotLayer", marker_df, get_position="[lon, lat]", get_color=mode_color, get_radius=5000, opacity=0.3)

    view_state = pdk.ViewState(
        latitude=(start_loc["lat"] + end_loc["lat"]) / 2,
        longitude=(start_loc["lon"] + end_loc["lon"]) / 2,
        zoom=7 if mode in ["SHIP", "AIR"] else 9, pitch=45
    )

    overlay_layer = pdk.Layer(
        "PolygonLayer", pd.DataFrame([{"path": [[0,0], [180, 0], [180, 90], [0, 90], [0,0]], "color": [88, 28, 135, 30]}]),
        get_polygon="path", get_fill_color="color", stroked=False,
    )

    from math import radians, cos, sin, asin, sqrt
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return 6371 * 2 * asin(sqrt(a))
    
    dist = haversine(start_loc["lon"], start_loc["lat"], end_loc["lon"], end_loc["lat"])
    
    st.markdown(f'<h3 class="title-glow" style="font-size: 1.15rem; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 1.5rem; margin-bottom: 0.5rem;">📍 Logistics Corridor: {mode}</h3>', unsafe_allow_html=True)
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(map_style=None, layers=[overlay_layer, glow_layer, route_layer, marker_layer], initial_view_state=view_state))
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Interactive Selector Plate
    st.markdown('<div class="info-panel">', unsafe_allow_html=True)
    modes = [("🚢 SHIP", "SHIP"), ("🚛 TRUCK", "TRUCK"), ("🚆 RAIL", "RAIL"), ("✈️ AIR", "AIR")]
    cols = st.columns(len(modes) + 1)
    
    with cols[0]:
        st.markdown(f'<div style="text-align:center"><div class="info-lab">Distance</div><div class="info-val">{dist:.1f}</div><div class="info-lab">KM</div></div>', unsafe_allow_html=True)
    
    for i, (label, m_id) in enumerate(modes):
        with cols[i+1]:
            if st.button(label, key=f"btn_{m_id}", use_container_width=True):
                st.session_state.selected_mode = m_id
                st.rerun()
    st.markdown('</div><br>', unsafe_allow_html=True)

# -----------------
# APP LAYOUT
# -----------------
inject_custom_css()

# --- SIDEBAR ---
st.sidebar.title("System Parameters")
demo_mode = st.sidebar.toggle("🎬 Enable Guided Demo Mode", value=True)
st.session_state.auto_refresh = st.sidebar.checkbox("Auto-Refresh UI (3s)", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Disruption Simulation")
if st.sidebar.button("🔴 INJECT CHAOS EVENT", use_container_width=True, type="primary"):
    with st.sidebar.status("Injecting Black Swan Event..."):
        for p in [SCOUT_PATH, ANALYST_PATH, INTEL_PATH, FINAL_RESULTS_PATH, SHARED_DIR / "signal.json"]:
            if p.exists(): p.unlink()
        event_data = trigger_chaos()
        process_signal()
        from analyst_agent import run_analyst_agent
        run_analyst_agent()
        from strategist_agent import run_strategist
        from simulator_agent import run_simulator
        a_data = load_json(ANALYST_PATH)
        if a_data:
            strat_res = run_strategist(a_data)
            sim_res = run_simulator(a_data, strat_res)
            intel_output = {
                "strategic_lesson": strat_res.get("strategic_lesson", ""),
                "match_confidence": sim_res.get("oracle_recommendation", {}).get("confidence_score", 0.0),
                "alternative_routes": sim_res.get("oracle_recommendation", {}).get("alternative_modes", []),
                "recommended_mode": sim_res.get("oracle_recommendation", {}).get("recommended_mode", "Unknown"),
                "simulation_details": sim_res.get("simulation_results", []),
                "agent_thoughts": "Strategist and Simulator complete analytics.",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(INTEL_PATH, "w") as f: json.dump(intel_output, f, indent=2)
        from manager_agent import run_manager_pipeline_once
        run_manager_pipeline_once()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("System Recovery")
if st.sidebar.button("🧹 Master Reset", use_container_width=True):
    for p in [SCOUT_PATH, ANALYST_PATH, INTEL_PATH, FINAL_RESULTS_PATH, SHARED_DIR / "signal.json"]:
        if p.exists(): p.unlink()
    for f in (BASE_DIR / "04_manager_module").glob("*.mp3"): f.unlink()
    st.sidebar.success("System Purged.")
    time.sleep(1); st.rerun()

# SECTION 1: HEADER
st.markdown('<h1 class="title-glow">🛰️ NexusPath — Antifragile Supply Chain</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle" style="color: #94a3b8; font-size: 1.15rem; margin-bottom: 3rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;">REAL-TIME AI CONTROL ROOM</div>', unsafe_allow_html=True)

col_left, col_space, col_right = st.columns([6.5, 0.5, 3])

with col_left:
    if demo_mode:
        st.markdown('<div class="step-panel">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: white; margin-bottom: 1.5rem;'>🎬 Demo Progression Sequence</h3>", unsafe_allow_html=True)
        step = 0
        if load_json(FINAL_RESULTS_PATH): step = 5
        elif load_json(INTEL_PATH): step = 4
        elif load_json(ANALYST_PATH): step = 3
        elif load_json(SCOUT_PATH): step = 2
        elif load_json(SHARED_DIR / "signal.json"): step = 1
        steps = ["Step 1: Chaos Injected", "Step 2: Scout Analysis", "Step 3: Risk Assessment", "Step 4: Strategy Simulation", "Step 5: Final Decision"]
        msgs = ["Awaiting system trigger...", "Detecting disruption anomalies...", "Analyzing blast radius impact...", "Simulating alternatives...", "Calculating ROI...", "System stabilized."]
        for i, s_name in enumerate(steps):
            s_idx = i + 1
            if s_idx == step: st.markdown(f"<div class='step-active'>▶ {s_name}</div>", unsafe_allow_html=True)
            elif s_idx < step: st.markdown(f"<div class='step-inactive' style='color: #475569;'>✓ {s_name}</div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='step-inactive'>{s_name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='demo-msg'>▶ {msgs[step]}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # MAIN RISK DASHBOARD
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: white;'>Live Risk Dashboard</h2>", unsafe_allow_html=True)
    final_res = load_json(FINAL_RESULTS_PATH)
    intel_data = load_json(INTEL_PATH)
    analyst_data = load_json(ANALYST_PATH)
    scout_data = load_json(SCOUT_PATH)
    
    if final_res:
        roi_data = final_res.get("roi", {})
        savings = roi_data.get("savings", "---")
        
        # Use recommended_route from final_res as Intel payload is cleaned up by Manager
        mode_reco = final_res.get("recommended_route", "UNKNOWN").upper()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="metric-value" style="color: #818cf8; font-size: 3.5rem;">₹ {savings:,}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Projected Savings</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-value" style="color: #38bdf8; font-size: 3.5rem;">{mode_reco}</div>', unsafe_allow_html=True)
            st.markdown('<div class="metric-label">Authorized Mode</div>', unsafe_allow_html=True)
            
        st.write("")
        briefing = final_res.get("summary_text") or "No executive summary."
        st.info(f"🎙️ **Executive Briefing:** {briefing}")
        audio_path = os.path.join(BASE_DIR, "04_manager_module", "alert_english.mp3")
        if not os.path.exists(audio_path): audio_path = os.path.join(BASE_DIR, "04_manager_module", "alert.mp3")
        if os.path.exists(audio_path): st.audio(audio_path, format="audio/mp3")
    elif intel_data:
        mode_reco = intel_data.get("recommended_mode", "UNKNOWN").upper()
        st.markdown(f'<div class="metric-value" style="color: #38bdf8;">{mode_reco}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">SIMULATOR RECOMMENDED ROUTE</div><br>', unsafe_allow_html=True)
        conf = float(intel_data.get("match_confidence", 0.0)) * 100
        st.info(f"🧠 **Strategist Match:** Intercepted with {conf:.1f}% confidence.")
    elif analyst_data:
        risk_val = analyst_data.get("total_value_at_risk", 0)
        st.markdown(f'<div class="metric-value" style="color: #ef4444;">₹ {risk_val:,}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">TOTAL INR AT RISK</div><br>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">Waiting for system signals.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if scout_data:
        render_map(scout_data.get("location"), severity=scout_data.get("severity", "HIGH"))

with col_right:
    st.markdown('<div class="dark-card">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: white; margin-bottom: 1.5rem;'>Agent Intelligence Feed</h2>", unsafe_allow_html=True)
    feed = {"🔭 Scout": scout_data, "📊 Analyst": analyst_data, "🧠 Strategist": intel_data, "🎙️ Manager": final_res}
    has_feed = False
    for label, data in feed.items():
        if data and "agent_thoughts" in data:
            st.markdown(f"<div class='agent-label'>{label} Agent</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='agent-thought'>{data['agent_thoughts']}</div>", unsafe_allow_html=True)
            has_feed = True
    if not has_feed: st.markdown('<div class="empty-state">Waiting for agents...</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.get("auto_refresh", True):
    time.sleep(3); st.rerun()
