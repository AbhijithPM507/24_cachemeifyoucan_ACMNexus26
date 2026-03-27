import os
import sys
import json
import time
import streamlit as st
from pathlib import Path

# Add the current directory to path so we can import local modules easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chaos_trigger import trigger_chaos
from scout_agent import process_signal

# Paths to shared exchange
BASE_DIR = Path(__file__).parent.parent
SHARED_DIR = BASE_DIR / "shared_exchange"

SCOUT_PATH = SHARED_DIR / "scout_output.json"
ANALYST_PATH = SHARED_DIR / "analyst_output.json"
INTEL_PATH = SHARED_DIR / "intel_output.json"
FINAL_RESULTS_PATH = SHARED_DIR / "final_results.json"

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
    """Injects Tailwind-like styling for a modern, minimalist control room feel."""
    st.markdown("""
        <style>
        /* Base Dark App Background */
        .stApp {
            background-color: #0b0f19;
            color: #f8fafc;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }

        /* Main Dark Card */
        .card {
            background-color: #111827; /* Gray-900 */
            border-radius: 1rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid #1f2937; /* Gray-800 border */
            color: #f8fafc;
            transition: all 0.3s ease;
        }
        
        .card:hover {
            border-color: #374151; /* Lighter on hover */
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.6);
        }

        /* Deep Dark card for Agent Feed */
        .dark-card {
            background-color: #0d1117; /* GitHub Dark dimension */
            border-radius: 1rem;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.2);
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid #1e293b;
            height: 100%;
            color: #f8fafc;
        }

        /* Typography */
        h1, h2, h3 {
            font-family: 'Inter', -apple-system, sans-serif;
            margin-bottom: 0.5rem;
            letter-spacing: -0.025em;
        }
        
        .title-glow {
            text-shadow: 0 0 25px rgba(56, 189, 248, 0.4);
            color: #ffffff;
            font-weight: 800;
        }

        .subtitle {
            font-size: 1.15rem;
            color: #94a3b8; /* Slate-400 */
            margin-bottom: 3rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        
        /* Dashboard Metrics */
        .metric-value {
            font-size: 4.5rem;
            font-weight: 900;
            color: #10b981; /* Emerald-500 */
            line-height: 1;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 25px rgba(16, 185, 129, 0.4); /* Glow effect */
        }
        .metric-label {
            font-size: 1.15rem;
            font-weight: 600;
            color: #cbd5e1; /* Slate-300 */
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

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
            border-left: 4px solid #3b82f6; /* Blue-500 indicator */
            padding: 1.5rem;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            font-size: 1.1rem;
            font-weight: 400;
            color: #e2e8f0; /* Slate-200 */
            background: linear-gradient(90deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.4) 100%);
            border-radius: 0 0.75rem 0.75rem 0;
            line-height: 1.6;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: border-color 0.3s;
        }
        .agent-thought:hover {
            border-left: 4px solid #60a5fa; /* Lighter blue on hover */
        }

        /* Empty State */
        .empty-state {
            color: #64748b;
            font-style: italic;
            margin-top: 1rem;
            padding: 2.5rem;
            border: 2px dashed #334155;
            border-radius: 0.75rem;
            text-align: center;
        }
        
        /* Custom Button Styling via Streamlit native classes override */
        div[data-testid="stButton"] > button {
            border-radius: 0.5rem;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.2s ease;
        }
        
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            border: none;
            box-shadow: 0 4px 15px 0 rgba(220, 38, 38, 0.5);
            letter-spacing: 0.05em;
        }
        
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            box-shadow: 0 8px 25px rgba(220, 38, 38, 0.7);
            transform: translateY(-2px);
        }
        
        /* Custom Alert Boxes */
        div[data-testid="stAlert"] {
            border-radius: 0.75rem;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            background-color: rgba(30, 41, 59, 0.8);
            color: #f8fafc;
        }

        /* --- DEMO MODE CSS --- */
        @keyframes pulse-glow {
            0% { text-shadow: 0 0 15px rgba(16, 185, 129, 0.4); transform: scale(1); }
            50% { text-shadow: 0 0 40px rgba(16, 185, 129, 1); transform: scale(1.02); }
            100% { text-shadow: 0 0 15px rgba(16, 185, 129, 0.4); transform: scale(1); }
        }
        @keyframes pulse-text {
            0% { opacity: 0.7; }
            50% { opacity: 1; }
            100% { opacity: 0.7; }
        }
        .roi-highlight {
            animation: pulse-glow 2s infinite;
            color: #34d399 !important;
        }
        .step-panel {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 1rem;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px dashed #334155;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
        }
        .step-active {
            color: #38bdf8;
            font-weight: 700;
            border-left: 4px solid #38bdf8;
            padding-left: 1rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, rgba(56, 189, 248, 0.15) 0%, transparent 100%);
            border-radius: 0 0.5rem 0.5rem 0;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            font-size: 1.1rem;
        }
        .step-inactive {
            color: #64748b;
            font-weight: 500;
            border-left: 4px solid #334155;
            padding-left: 1rem;
            margin-bottom: 0.5rem;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            font-size: 1.05rem;
        }
        .demo-msg {
            color: #fca5a5;
            font-style: italic;
            margin-top: 1.5rem;
            font-size: 1.15rem;
            animation: pulse-text 2s infinite;
            border-top: 1px solid #334155;
            padding-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------
# APP LAYOUT
# -----------------
inject_custom_css()

# --- SIDEBAR DEMO MODE ---
st.sidebar.title("System Parameters")
demo_mode = st.sidebar.toggle("🎬 Enable Guided Demo Mode", value=False)
st.session_state.auto_refresh = st.sidebar.checkbox("Auto-Refresh UI (3s)", value=True)

# SECTION 1: HEADER
st.markdown('<h1 class="title-glow">🛰️ NexusPath — Antifragile Supply Chain</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">REAL-TIME AI CONTROL ROOM</div>', unsafe_allow_html=True)

# Main Layout: Left (2/3) and Right (1/3)
col_left, col_space, col_right = st.columns([6.5, 0.5, 3])

with col_left:
    # --- DEMO STEP INDICATOR ---
    if demo_mode:
        st.markdown('<div class="step-panel">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: white; margin-bottom: 1.5rem;'>🎬 Demo Progression Sequence</h3>", unsafe_allow_html=True)
        
        # Determine Current Step
        step = 0
        if load_json(FINAL_RESULTS_PATH): step = 5
        elif load_json(INTEL_PATH): step = 4
        elif load_json(ANALYST_PATH): step = 3
        elif load_json(SCOUT_PATH): step = 2
        elif load_json(SHARED_DIR / "signal.json"): step = 1

        steps = [
            "Step 1: Chaos Injected",
            "Step 2: Scout Analysis",
            "Step 3: Risk Assessment",
            "Step 4: Strategy Simulation",
            "Step 5: Final Decision"
        ]
        
        msgs = [
            "Awaiting system trigger...",
            "Detecting disruption anomalies...",
            "Analyzing blast radius & supply impact...",
            "Simulating strategic alternatives...",
            "Calculating ROI projections...",
            "System fully stabilized. Awaiting executive approval."
        ]
        
        for i, s_name in enumerate(steps):
            s_idx = i + 1
            if s_idx == step:
                st.markdown(f"<div class='step-active'>▶ {s_name}</div>", unsafe_allow_html=True)
            elif s_idx < step:
                st.markdown(f"<div class='step-inactive' style='color: #475569;'>✓ {s_name}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='step-inactive'>{s_name}</div>", unsafe_allow_html=True)

        st.markdown(f"<div class='demo-msg'>▶ {msgs[step]}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- CONTROL PANEL ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: white;'>Control Panel</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; margin-bottom: 1.5rem; text-transform: uppercase; letter-spacing: 0.05em;'>SYSTEM OVERRIDE — INITIALIZE BLACK SWAN SCENARIO</p>", unsafe_allow_html=True)
    
    if st.button("🔴 CHAOS BUTTON — Inject Black Swan Event", use_container_width=True, type="primary"):
        with st.spinner("Injecting Chaos & Initializing Scout Protocol..."):
            if demo_mode:
                # Target clean slate
                for p in [SCOUT_PATH, ANALYST_PATH, INTEL_PATH, FINAL_RESULTS_PATH, SHARED_DIR / "signal.json"]:
                    if p.exists(): p.unlink()
                st.info("Initializing Black Swan Scenario...")
                time.sleep(1.5)
                
            event_data = trigger_chaos()
            
            if demo_mode:
                st.info("Detecting disruption...")
                time.sleep(2.0)
                
            process_signal()
            
            event_name = event_data.get('event', 'Unknown Event').upper()
            location = event_data.get('location', 'Unknown Location')
            st.warning(f"⚠️ **Chaos Injected:** {event_name} at {location}")
            
            if demo_mode:
                st.info("Analyzing impact...")
                time.sleep(1.5)
                st.info("Waiting for downstream agents to connect...")
                time.sleep(1.5)
                
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # --- LIVE RISK DASHBOARD ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: white;'>Live Risk Dashboard</h2>", unsafe_allow_html=True)
    
    final_res = load_json(FINAL_RESULTS_PATH)
    if final_res:
        # A. ROI Metric
        roi = str(final_res.get("projected_savings", "---"))
        pulse_class = "metric-value roi-highlight" if demo_mode else "metric-value"
        st.markdown(f'<div class="{pulse_class}">{roi}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Projected Savings</div><br>', unsafe_allow_html=True)
        
        # B. Alert / Briefing
        briefing = final_res.get("briefing_text", "No executive summary provided.")
        st.info(f"📋 **Manager Briefing:** {briefing}")
        st.write("")
        
        # C. Audio Player
        mp3_path = final_res.get("mp3_path")
        if mp3_path and os.path.exists(mp3_path):
            st.audio(mp3_path, format="audio/mp3")
            st.write("")
        
        # D. Action Buttons
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("✅ Approve Reroute", use_container_width=True):
                st.success("Reroute execution authorized. Logistics pivoting engaged.")
                time.sleep(2)
        with btn_c2:
            if st.button("❌ Reject", use_container_width=True):
                st.error("Reroute rejected. Maintaining structural hold.")
                time.sleep(2)
    else:
        st.markdown('<div class="empty-state">Waiting for Final Manager Agent results... Ensure all modules have executed safely.</div>', unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)


with col_right:
    # --- AGENT INTELLIGENCE FEED ---
    st.markdown('<div class="dark-card">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: white; margin-bottom: 1.5rem;'>Agent Intelligence Feed</h2>", unsafe_allow_html=True)
    
    scout_data = load_json(SCOUT_PATH)
    analyst_data = load_json(ANALYST_PATH)
    intel_data = load_json(INTEL_PATH)
    
    has_feed_data = False
    
    if scout_data and "agent_thoughts" in scout_data:
        st.markdown("<div class='agent-label'>🔭 Scout Agent</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='agent-thought'>{scout_data['agent_thoughts']}</div>", unsafe_allow_html=True)
        has_feed_data = True

    if analyst_data and "agent_thoughts" in analyst_data:
        st.markdown("<div class='agent-label'>📊 Analyst Agent</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='agent-thought'>{analyst_data['agent_thoughts']}</div>", unsafe_allow_html=True)
        has_feed_data = True

    if intel_data and "agent_thoughts" in intel_data:
        st.markdown("<div class='agent-label'>🧠 Strategist Agent</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='agent-thought'>{intel_data['agent_thoughts']}</div>", unsafe_allow_html=True)
        has_feed_data = True

    if final_res and "agent_thoughts" in final_res:
        st.markdown("<div class='agent-label'>🎙️ Manager Agent</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='agent-thought'>{final_res['agent_thoughts']}</div>", unsafe_allow_html=True)
        has_feed_data = True

    if not has_feed_data:
         st.markdown('<div class="empty-state">Waiting for agents... Initiate Chaos to begin.</div>', unsafe_allow_html=True)
         
    st.markdown("</div>", unsafe_allow_html=True)


# --- REFRESH LOGIC ---
if st.session_state.auto_refresh:
    time.sleep(3)
    st.rerun()
