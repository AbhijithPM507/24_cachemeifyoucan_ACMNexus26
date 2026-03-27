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

st.set_page_config(page_title="NexusPath Dashboard", layout="wide", initial_sidebar_state="collapsed")

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
        /* Base page styling */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Light mode card */
        .card {
            background-color: #ffffff;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #e2e8f0;
        }

        /* Dark mode card for agent feed */
        .dark-card {
            background-color: #0f172a;
            border-radius: 0.75rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #1e293b;
            height: 100%;
        }

        /* Typography */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.25rem;
            color: #64748b;
            margin-bottom: 2rem;
            font-weight: 500;
        }
        
        /* Dashboard Metrics */
        .metric-value {
            font-size: 3.5rem;
            font-weight: 800;
            color: #10b981; /* Emerald-500 */
            line-height: 1;
            margin-top: 0.5rem;
            margin-bottom: 0.25rem;
        }
        .metric-label {
            font-size: 1rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Agent Monologue Styles */
        .agent-label {
            font-weight: 700;
            color: #e2e8f0;
            font-size: 1.15rem;
            margin-top: 1rem;
            margin-bottom: 0.25rem;
        }
        .agent-thought {
            border-left: 4px solid #3b82f6; /* Blue-500 indicator */
            padding-left: 1rem;
            margin-top: 0.25rem;
            margin-bottom: 1.5rem;
            font-size: 1rem;
            font-style: italic;
            color: #94a3b8; /* Slate-400 */
            background: rgba(30, 41, 59, 0.5); /* Slate-800 translucent */
            padding: 1rem;
            border-radius: 0 0.5rem 0.5rem 0;
            line-height: 1.5;
        }

        /* Empty State */
        .empty-state {
            color: #64748b;
            font-style: italic;
            margin-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------
# APP LAYOUT
# -----------------
inject_custom_css()

# SECTION 1: HEADER
st.title("🛰️ NexusPath — Antifragile Supply Chain")
st.markdown('<div class="subtitle">Real-time AI Control Room</div>', unsafe_allow_html=True)

# Auto-refresh session state
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True

# Main Layout: Left (2/3) and Right (1/3)
col_left, col_space, col_right = st.columns([6.5, 0.5, 3])

with col_left:
    # --- CONTROL PANEL ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Control Panel")
    st.markdown("<p style='color: #64748b; margin-bottom: 1rem;'>Simulate real-world disruption events</p>", unsafe_allow_html=True)
    
    if st.button("🔴 CHAOS BUTTON — Inject Black Swan Event", use_container_width=True, type="primary"):
        with st.spinner("Injecting Chaos & Initializing Scout Protocol..."):
            # Trigger downstream
            event_data = trigger_chaos()
            process_signal()
            
            # Format UI response
            event_name = event_data.get('event', 'Unknown Event').upper()
            location = event_data.get('location', 'Unknown Location')
            st.warning(f"⚠️ **Chaos Injected:** {event_name} at {location}")
            
            # Pause slightly so user can read it, then let it rerun normally
            time.sleep(1.5)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # --- LIVE RISK DASHBOARD ---
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Live Risk Dashboard")
    
    final_res = load_json(FINAL_RESULTS_PATH)
    if final_res:
        # A. ROI Metric
        roi = str(final_res.get("projected_savings", "---"))
        st.markdown(f'<div class="metric-value">{roi}</div>', unsafe_allow_html=True)
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
    st.markdown("<h3 style='color: white; margin-bottom: 1rem;'>Agent Intelligence Feed</h3>", unsafe_allow_html=True)
    
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
# Place a discreet toggle at the bottom to allow manual pausing of the 3s loop
st.markdown("---")
col_refresh1, col_refresh2 = st.columns([1, 6])
with col_refresh1:
    st.session_state.auto_refresh = st.checkbox("Auto-Refresh UI (3s)", value=st.session_state.auto_refresh)

# Only auto-reload if checked and no interaction buttons are currently overriding thread
if st.session_state.auto_refresh:
    time.sleep(3)
    st.rerun()
