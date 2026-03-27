import os
import sys
import json
import time
import pandas as pd
import pydeck as pdk
import streamlit as st
import requests
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

st.set_page_config(page_title="TRANSIT Dashboard", layout="wide", initial_sidebar_state="expanded")

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
        
        /* Global Background Reset */
        .stApp {
            background: transparent !important;
        }

        /* Fixed Viewport Foundation */
        .viewport-bg {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: radial-gradient(circle at 50% 50%, #0f172a, #020617);
            z-index: -100;
            pointer-events: none;
        }

        /* Tactical Grid Overlay */
        .grid-layer {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: 
                linear-gradient(to right, rgba(99, 102, 241, 0.08) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(99, 102, 241, 0.08) 1px, transparent 1px);
            background-size: 60px 60px;
            z-index: -90;
            pointer-events: none;
        }

        /* Shimmering Dots Overlay */
        .dots-layer {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-image: radial-gradient(circle, rgba(129, 140, 248, 0.2) 1px, transparent 1px);
            background-size: 150px 150px;
            z-index: -80;
            pointer-events: none;
            animation: holoPulse 15s ease-in-out infinite;
        }

        @keyframes holoPulse {
            0% { opacity: 0.15; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.05); }
            100% { opacity: 0.15; transform: scale(1); }
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }

        /* Scanline Effect */
        .card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.4), transparent);
            animation: scanline 4s linear infinite;
        }

        @keyframes scanline {
            0% { top: 0; }
            100% { top: 100%; }
        }

        /* Neon Glow Card */
        .card {
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(20px);
            border-radius: 1.5rem;
            box-shadow: 0 0 30px rgba(99, 102, 241, 0.05);
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(99, 102, 241, 0.15);
            color: #f8fafc;
            position: relative;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            background: rgba(15, 23, 42, 0.6);
            box-shadow: 0 0 50px rgba(99, 102, 241, 0.15);
        }

        .dark-card {
            background: rgba(2, 6, 23, 0.6);
            backdrop-filter: blur(16px);
            border-radius: 1.5rem;
            padding: 2.5rem;
            border: 1px solid rgba(148, 163, 184, 0.05);
            height: 100%;
        }

        .hero-section {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            text-align: left;
            padding: 1rem 0;
            margin-bottom: 1rem;
            background: radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.12) 0%, transparent 60%);
            position: relative;
        }

        .hero-title {
            font-size: 3.5rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: -0.01em;
            color: white;
            text-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
            line-height: 1;
            margin: 0;
            font-family: 'Outfit', sans-serif;
        }

        .hero-divider {
            width: 40px;
            height: 1px;
            background: rgba(129, 140, 248, 0.4);
            margin: 0.75rem 0;
        }

        .hero-subtitle {
            font-size: 0.85rem;
            font-weight: 700;
            color: #94a3b8;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            opacity: 0.8;
        }

        /* Global Particle Background */
        .particles-root {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -95;
            pointer-events: none;
            overflow: hidden;
        }
        .p {
            position: absolute;
            background: rgba(129, 140, 248, 0.15);
            border-radius: 50%;
            filter: blur(15px);
            animation: float linear infinite;
        }
        @keyframes float {
            0% { transform: translate(0, 0); opacity: 0; }
            20% { opacity: 0.2; }
            80% { opacity: 0.2; }
            100% { transform: translate(15vw, -60vh); opacity: 0; }
        }

        .title-glow {
            text-shadow: 0 0 30px rgba(99, 102, 241, 0.6);
            background: linear-gradient(90deg, #fff, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
        }

        /* Metric Typography Override */
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

        /* Route Info Panel Removal of specific borders to avoid ghosting */
        .info-panel { display: none; }
        .card { display: none; }
        .step-panel { display: none; }
        .dark-card { display: none; }

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

        .demo-msg {
            color: #818cf8;
            font-style: italic;
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(99, 102, 241, 0.05);
            border-radius: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Inject Global Viewport Background
    st.markdown('''
        <div class="viewport-bg"></div>
        <div class="grid-layer"></div>
        <div class="dots-layer"></div>
        <div class="particles-root">
            <div class="p" style="width:200px; height:200px; left:10%; top:40%; animation-duration:25s; animation-delay:0s;"></div>
            <div class="p" style="width:300px; height:300px; left:40%; top:80%; animation-duration:35s; animation-delay:-5s;"></div>
            <div class="p" style="width:150px; height:150px; left:70%; top:25%; animation-duration:45s; animation-delay:-10s;"></div>
            <div class="p" style="width:220px; height:220px; left:5%; top:95%; animation-duration:40s; animation-delay:-15s;"></div>
            <div class="p" style="width:350px; height:350px; left:80%; top:70%; animation-duration:55s; animation-delay:-20s;"></div>
            <div class="p" style="width:100px; height:100px; left:30%; top:15%; animation-duration:30s; animation-delay:-8s;"></div>
            <div class="p" style="width:180px; height:180px; left:60%; top:85%; animation-duration:32s; animation-delay:-12s;"></div>
        </div>
    ''', unsafe_allow_html=True)

@st.cache_data(ttl=600)
def get_real_route(origin, dest):
    """Fetches real GeoJSON road coordinates from OSRM Engine."""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[0]},{origin[1]};{dest[0]},{dest[1]}?geometries=geojson&overview=full"
        res = requests.get(url, timeout=5)
        data = res.json()
        if data["code"] == "Ok":
            route = data["routes"][0]
            dist = route["distance"] / 1000
            dur = route["duration"] / 3600
            return route["geometry"]["coordinates"], dist, dur
    except:
        pass
    return [origin, dest], 0, 0

def normalize_mode(mode_text):
    """Extract simple transport mode key from any AI-generated text."""
    if not mode_text: return "TRUCK"
    t = mode_text.upper()
    if "SHIP" in t or "MARITIME" in t or "SEA" in t or "VESSEL" in t: return "SHIP"
    if "AIR" in t or "FLY" in t or "FLIGHT" in t or "CARGO AIR" in t: return "AIR"
    if "RAIL" in t or "TRAIN" in t or "RAILWAY" in t: return "RAIL"
    return "TRUCK"

def get_detailed_path(start, end, mode, location_name):
    """Generates a high-fidelity multi-segment path simulation for logistics routes."""
    # TRUCK: use real OSRM road routing
    if mode == "TRUCK":
        path, d, t = get_real_route(start, end)
        if d > 0: return path, d, t

    # RAIL: dedicated railway station waypoints (Southern Railway / Konkan Railway network)
    RAIL_SPINES = {
        # Main Western Coast Line: Cochin Port → stations north → Mangalore
        "Mangalore":          [[76.30,9.98],[76.21,10.53],[76.27,10.77],[75.93,10.91],[75.78,11.26],[75.59,11.60],[75.35,11.87],[74.99,12.50],[74.84,12.87]],
        "Kozhikode":          [[76.30,9.98],[76.21,10.53],[76.27,10.77],[75.93,10.91],[75.78,11.26]],
        "Thrissur":           [[76.30,9.98],[76.21,10.21],[76.21,10.53]],
        "Kochi":              [[76.30,9.98],[76.29,10.01],[76.28,10.04]],
        # Shoranur-Palakkad branch (east branch from Shoranur)
        "Palakkad":           [[76.30,9.98],[76.21,10.53],[76.27,10.77],[76.52,10.77]],
        # South-bound: Ernakulam → Thiruvananthapuram
        "Thiruvananthapuram": [[76.30,9.98],[76.34,9.49],[76.60,8.89],[76.97,8.48]],
        # Wayanad has no rail; nearest is Calicut → use truncated Kozhikode path
        "Wayanad":            [[76.30,9.98],[76.21,10.53],[76.27,10.77],[75.93,10.91],[75.78,11.26]],
        # Inter-state via Shoranur → Coimbatore → Salem/Bangalore
        "Bangalore":          [[76.30,9.98],[76.27,10.77],[76.65,10.78],[77.03,11.00],[77.82,11.31],[77.59,12.97]],
        "Chennai":            [[76.30,9.98],[76.27,10.77],[76.65,10.78],[77.03,11.00],[77.82,11.31],[77.59,12.97],[79.13,12.91],[80.27,13.08]],
        # Mumbai via Konkan Railway: Mangalore → Goa → Ratnagiri → Mumbai
        "Mumbai":             [[76.30,9.98],[75.78,11.26],[74.84,12.87],[73.83,15.49],[73.30,17.00],[72.87,19.07]],
        # Hyderabad via Salem → Vijayawada
        "Hyderabad":          [[76.30,9.98],[76.27,10.77],[77.03,11.00],[78.14,11.66],[79.99,14.44],[78.49,17.39]],
        # Delhi via Chennai or Mumbai → long haul
        "Delhi":              [[76.30,9.98],[76.27,10.77],[77.03,11.00],[77.59,12.97],[78.49,17.39],[77.21,28.61]],
    }

    if mode == "RAIL":
        rail_path = RAIL_SPINES.get(location_name)
        if rail_path:
            # Estimate distance along waypoints using line length
            from math import radians, cos, sin, asin, sqrt as msqrt
            total_km = 0
            for i in range(len(rail_path) - 1):
                lo1, la1 = rail_path[i]; lo2, la2 = rail_path[i+1]
                lo1,la1,lo2,la2 = map(radians,[lo1,la1,lo2,la2])
                a = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
                total_km += 6371 * 2 * asin(msqrt(a))
            avg_speed_kmh = 65  # typical freight rail speed in India
            return rail_path, total_km, total_km / avg_speed_kmh
        # Fallback: straight line for unknown destinations
        return [start, end], 0, 0

    # Predefined 'Spine Waypoints' Fallback — NH-66/NH-544 Kerala highway corridors
    SPINES = {
        # Inter-state routes
        "Mumbai": [[76.26,9.96],[75.78,11.26],[74.86,12.91],[73.98,15.29],[73.85,18.52],[72.87,19.07]],
        "Bangalore": [[76.26,9.96],[76.21,10.53],[76.52,10.77],[77.59,12.97]],
        "Chennai": [[76.26,9.96],[76.52,10.77],[78.14,11.66],[79.13,12.91],[80.27,13.08]],
        # NH-66 coastal — Cochin → Mangalore (follows coast, stays ~76°E until Kannur)
        "Mangalore": [[76.26,9.96],[76.21,10.53],[75.98,11.15],[75.78,11.26],[75.62,11.87],[74.99,12.36],[74.86,12.91]],
        "Thiruvananthapuram": [[76.26,9.96],[76.33,9.49],[76.60,8.89],[76.97,8.48]],
        # Kerala internal NH-66 hubs
        "Kozhikode": [[76.26,9.96],[76.21,10.53],[76.07,10.98],[75.98,11.15],[75.78,11.26]],
        "Thrissur": [[76.26,9.96],[76.22,10.20],[76.21,10.53]],
        "Palakkad": [[76.26,9.96],[76.21,10.53],[76.35,10.72],[76.52,10.77]],
        "Wayanad": [[76.26,9.96],[76.21,10.53],[76.07,10.98],[76.13,11.41],[76.13,11.68]],
        "Kochi": [[76.26,9.96],[76.30,10.01],[76.32,10.05]],
    }

    path = SPINES.get(location_name, [start, end])
    if mode == "SHIP":
        m_path = [[start[0], start[1]]]
        for wp in path[1:-1]: m_path.append([wp[0] - 1.2, wp[1]])
        m_path.append([end[0], end[1]])
        return m_path, 0, 0
    return path, 0, 0

def render_map(location_name=None, severity="HIGH", rerouting=False, old_mode="TRUCK", new_mode=None,
               custom_origin=None, custom_dest=None):
    """Renders a high-fidelity logistics map. Shows dual routes with rerouting animation when disruption is active."""
    from math import radians, cos, sin, asin, sqrt
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return 6371 * 2 * asin(sqrt(a))

    # Endpoints: use custom user-defined route if provided, else fall back to disruption location
    start_loc = KERALA_HUBS.get(custom_origin, KERALA_HUBS.get("Cochin Port"))
    origin_name = custom_origin or "Cochin Port"

    if custom_dest:
        dest_name = custom_dest
        end_loc = KERALA_HUBS.get(dest_name)
    else:
        dest_name = location_name if (location_name and location_name in KERALA_HUBS) else "Kozhikode"
        end_loc = KERALA_HUBS.get(dest_name)

    # Guard: if destination is too close to origin (<30km) pick a meaningful fallback
    raw_dist = haversine(start_loc["lon"], start_loc["lat"], end_loc["lon"], end_loc["lat"])
    if raw_dist < 30:
        dest_name = "Kozhikode"
        end_loc = KERALA_HUBS.get("Kozhikode")

    mode = new_mode or st.session_state.get("selected_mode", "TRUCK")

    severity_colors = {"LOW":[34,197,94,200],"MEDIUM":[234,179,8,200],"HIGH":[249,115,22,200],"CRITICAL":[239,68,68,255]}
    sev_color = severity_colors.get(severity.upper(), severity_colors["HIGH"])
    # Use visually distinct, bright colors for each mode
    mode_colors = {
        "SHIP": [30, 144, 255, 255],   # dodger blue
        "AIR":  [0, 229, 255, 255],    # bright cyan
        "RAIL": [129, 140, 248, 255],  # indigo (clearly visible)
        "TRUCK": sev_color
    }

    # Current (new/active) route
    path_data, osrm_dist, osrm_dur = get_detailed_path(
        [start_loc["lon"], start_loc["lat"]], [end_loc["lon"], end_loc["lat"]], mode, dest_name
    )
    display_dist = osrm_dist if osrm_dist > 0 else haversine(start_loc["lon"], start_loc["lat"], end_loc["lon"], end_loc["lat"])
    active_color = mode_colors.get(mode, sev_color)

    layers = []

    # Purple overlay
    overlay_layer = pdk.Layer("PolygonLayer",
        pd.DataFrame([{"path": [[0,0],[180,0],[180,90],[0,90],[0,0]], "color": [88,28,135,20]}]),
        get_polygon="path", get_fill_color="color", stroked=False)
    layers.append(overlay_layer)

    if rerouting and old_mode:
        # OLD compromised route — dimmed red ghost (visible but clearly secondary)
        old_path, _, _ = get_detailed_path(
            [start_loc["lon"], start_loc["lat"]], [end_loc["lon"], end_loc["lat"]], old_mode, dest_name
        )
        old_route_layer = pdk.Layer("PathLayer",
            pd.DataFrame([{"path": old_path}]),
            get_path="path", get_color=[220, 38, 38, 70], width_scale=10, width_min_pixels=4, rounded=True)
        old_glow = pdk.Layer("ScatterplotLayer",
            pd.DataFrame([{"lon":start_loc["lon"],"lat":start_loc["lat"]},{"lon":end_loc["lon"],"lat":end_loc["lat"]}]),
            get_position="[lon, lat]", get_color=[220, 38, 38, 50], get_radius=6000, opacity=0.15)
        layers += [old_glow, old_route_layer]

    # NEW recommended route — solid GREEN (safe/go) when rerouting, else mode color
    new_color = [34, 197, 94, 255] if rerouting else active_color
    new_glow_color = [34, 197, 94, 120] if rerouting else active_color

    # NEW active route — bright green (rerouting) or mode color (normal)
    new_route_layer = pdk.Layer("PathLayer",
        pd.DataFrame([{"path": path_data}]),
        get_path="path", get_color=new_color, width_scale=10, width_min_pixels=6, rounded=True)
    glow_layer = pdk.Layer("ScatterplotLayer",
        pd.DataFrame([{"lon":start_loc["lon"],"lat":start_loc["lat"]},{"lon":end_loc["lon"],"lat":end_loc["lat"]}]),
        get_position="[lon, lat]", get_color=new_glow_color, get_radius=5000, opacity=0.4)
    marker_layer = pdk.Layer("ScatterplotLayer",
        pd.DataFrame([{"lon":start_loc["lon"],"lat":start_loc["lat"]},{"lon":end_loc["lon"],"lat":end_loc["lat"]}]),
        get_position="[lon, lat]", get_color=[255,255,255,255], get_radius=2500)
    layers += [glow_layer, new_route_layer, marker_layer]

    # --- Rerouting Banner ---
    if rerouting:
        st.markdown(f'''
        <div style="
            display: flex; align-items: center; gap: 0.75rem;
            padding: 0.6rem 1.2rem;
            background: rgba(239,68,68,0.08);
            border: 1px solid rgba(239,68,68,0.3);
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
        ">
            <span style="
                display: inline-block; width: 10px; height: 10px;
                background: #ef4444; border-radius: 50%;
                animation: pulse-dot 1s ease-in-out infinite;
            "></span>
            <span style="color:#ef4444; font-weight:700; font-size:0.8rem; letter-spacing:0.1em;">DISRUPTION DETECTED &mdash; REROUTING VIA {mode}</span>
            <span style="color:#818cf8; font-size:0.75rem; margin-left:auto;">OLD: {old_mode} &rarr; NEW: {mode}</span>
        </div>
        <style>
        @keyframes pulse-dot {{
            0%,100% {{ opacity:1; transform: scale(1); }}
            50% {{ opacity:0.3; transform: scale(1.5); }}
        }}
        </style>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div style="
            display: flex; align-items: center; gap: 0.75rem;
            padding: 0.6rem 1.2rem;
            background: rgba(129,140,248,0.05);
            border: 1px solid rgba(129,140,248,0.15);
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
        ">
            <span style="display:inline-block; width:10px; height:10px; background:#22c55e; border-radius:50%;"></span>
            <span style="color:#94a3b8; font-size:0.8rem; letter-spacing:0.1em;">ACTIVE CORRIDOR &nbsp;&bull;&nbsp; {dest_name.upper()} &nbsp;&bull;&nbsp; MODE: {mode}</span>
            <span style="color:#818cf8; font-size:0.8rem; margin-left:auto; font-weight:700;">{display_dist:.1f} KM</span>
        </div>
        ''', unsafe_allow_html=True)

    st.pydeck_chart(pdk.Deck(
        map_style=None,
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=(start_loc["lat"]+end_loc["lat"])/2,
            longitude=(start_loc["lon"]+end_loc["lon"])/2,
            zoom=7 if mode in ["SHIP","AIR"] else 9,
            pitch=45
        )
    ))

    # Mode switcher buttons
    cols = st.columns([2, 1, 1, 1, 1])
    with cols[0]:
        st.markdown(f'''
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;">
                <div style="font-size:0.75rem;color:#94a3b8;font-weight:700;letter-spacing:0.1em;">DISTANCE</div>
                <div style="font-size:1.75rem;font-weight:900;color:#818cf8;line-height:1;">{display_dist:.1f} <span style="font-size:0.8rem;font-weight:600;color:#94a3b8;">KM</span></div>
            </div>
        ''', unsafe_allow_html=True)
    for i, (label, m_id) in enumerate([("SHIP","SHIP"),("TRUCK","TRUCK"),("RAIL","RAIL"),("AIR","AIR")]):
        with cols[i+1]:
            if st.button(label, key=f"btn_{m_id}", use_container_width=True):
                st.session_state.selected_mode = m_id
                st.rerun()

    if osrm_dur > 0 and mode == "TRUCK":
        st.info(f"Real Route Optimized: {osrm_dur:.1f} hrs via Highway Corridors.")


# -----------------
# APP LAYOUT
# -----------------
inject_custom_css()

# Initialize stable route state BEFORE any widgets (survives all reruns)
if "route_origin" not in st.session_state:
    st.session_state.route_origin = "Cochin Port"
if "route_dest" not in st.session_state:
    st.session_state.route_dest = "Kozhikode"

# --- SIDEBAR ---
st.sidebar.title("System Parameters")
demo_mode = st.sidebar.toggle("Enable Guided Demo Mode", value=True)
st.session_state.auto_refresh = st.sidebar.checkbox("Auto-Refresh UI (3s)", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Disruption Simulation")
if st.sidebar.button("INJECT CHAOS EVENT", use_container_width=True, type="primary"):
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
if st.sidebar.button("Master Reset", use_container_width=True):
    for p in [SCOUT_PATH, ANALYST_PATH, INTEL_PATH, FINAL_RESULTS_PATH, SHARED_DIR / "signal.json"]:
        if p.exists(): p.unlink()
    for f in (BASE_DIR / "04_manager_module").glob("*.mp3"): f.unlink()
    st.sidebar.success("System Purged.")
    time.sleep(1); st.rerun()

# SECTION 1: HERO HEADER
st.markdown('''
    <h1 class="hero-title">TRANSIT</h1>
    <div class="hero-divider"></div>
    <div class="hero-subtitle">ANTIFRAGILE LOGISTICS CONTROL</div>
''', unsafe_allow_html=True)

col_left, col_right = st.columns([7, 3])

# Load data once
final_res = load_json(FINAL_RESULTS_PATH)
intel_data = load_json(INTEL_PATH)
analyst_data = load_json(ANALYST_PATH)
scout_data = load_json(SCOUT_PATH)

with col_left:
    # --- ROUTE CONFIGURATION (inline, top of map) ---
    hub_names = sorted(KERALA_HUBS.keys())

    from math import radians, cos, sin, asin, sqrt as _sqrt
    def _hav(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
        return round(6371 * 2 * asin(_sqrt(a)), 1)

    rc1, rc2, rc3 = st.columns([5, 5, 2])
    with rc1:
        # Use neutral key 'sel_origin' — never conflicts with route_origin state var
        origin_sel = st.selectbox(
            "🛫 Origin Hub",
            options=hub_names,
            index=hub_names.index(st.session_state.route_origin) if st.session_state.route_origin in hub_names else 0,
            key="sel_origin"
        )
        st.session_state.route_origin = origin_sel  # always update authoritative state
    with rc2:
        # Use neutral key 'sel_dest' — never conflicts with route_dest state var
        dest_sel = st.selectbox(
            "📍 Destination Hub",
            options=hub_names,
            index=hub_names.index(st.session_state.route_dest) if st.session_state.route_dest in hub_names else 0,
            key="sel_dest"
        )
        st.session_state.route_dest = dest_sel  # always update authoritative state
    with rc3:
        if origin_sel != dest_sel:
            o = KERALA_HUBS[origin_sel]; d = KERALA_HUBS[dest_sel]
            est_km = _hav(o["lon"], o["lat"], d["lon"], d["lat"])
            st.markdown(f"""
            <div style='padding-top: 1.75rem; color:#818cf8; font-weight:700; font-size:1rem;'>
                {est_km} <span style='color:#94a3b8; font-size:0.75rem; font-weight:400;'>KM</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Pick different hubs.")

    is_rerouting = scout_data is not None
    raw_new_mode = None
    if final_res:
        raw_new_mode = final_res.get("recommended_route", "TRUCK")
    elif intel_data:
        raw_new_mode = intel_data.get("recommended_mode", "TRUCK")

    new_mode_key = normalize_mode(raw_new_mode) if raw_new_mode else st.session_state.get("selected_mode", "TRUCK")

    # --- DISRUPTION ALERT CARD ---
    signal_data = load_json(SHARED_DIR / "signal.json")
    if scout_data or signal_data:
        src        = signal_data or {}
        evt_type   = src.get("event", (scout_data or {}).get("event_type", "Unknown Event")).title()
        evt_loc    = src.get("location", (scout_data or {}).get("location", "Unknown Location"))
        evt_id     = src.get("id", "N/A")
        evt_source = src.get("source", "Internal Signal").replace("_", " ").title()
        ts         = src.get("timestamp", "")
        evt_time   = ts[:16].replace("T", " ") if ts else ""
        severity   = (scout_data or {}).get("severity", "HIGH")
        impact_raw = (scout_data or {}).get("impact_summary", (scout_data or {}).get("agent_thoughts", ""))
        impact_txt = str(impact_raw)[:120] + ("…" if len(str(impact_raw)) > 120 else "") if impact_raw else ""

        sev_colors = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#f97316", "CRITICAL": "#ef4444"}
        sev_color  = sev_colors.get(severity.upper(), "#ef4444")

        # Pre-build optional HTML rows (no Python expressions inside f-string)
        time_row   = f'<div>Detected: <span style="color:#94a3b8;">{evt_time}</span></div>' if evt_time else ""
        impact_row = f'<div style="color:#f97316;font-size:0.72rem;margin-top:0.25rem;">{impact_txt}</div>' if impact_txt else ""

        st.markdown(f"""
        <style>
        @keyframes pulse-dot {{
            0%,100% {{ opacity:1; transform:scale(1); box-shadow:0 0 0 0 {sev_color}88; }}
            50% {{ opacity:0.6; transform:scale(1.5); box-shadow:0 0 0 6px {sev_color}22; }}
        }}
        </style>
        <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.35);border-radius:0.75rem;padding:0.9rem 1.25rem;margin-bottom:0.6rem;display:flex;flex-wrap:wrap;gap:1rem;align-items:center;">
            <span style="display:inline-block;width:12px;height:12px;min-width:12px;background:{sev_color};border-radius:50%;animation:pulse-dot 1.2s ease-in-out infinite;"></span>
            <div style="flex:1;min-width:160px;">
                <div style="font-size:1rem;font-weight:800;color:#f8fafc;letter-spacing:0.02em;">&#9888;&nbsp; {evt_type}</div>
                <div style="font-size:0.82rem;color:#94a3b8;margin-top:0.2rem;">&#128205; Affected Zone: <strong style="color:#f8fafc;">{evt_loc}</strong></div>
            </div>
            <div style="text-align:center;">
                <div style="background:{sev_color}22;border:1px solid {sev_color}88;border-radius:0.4rem;padding:0.25rem 0.75rem;font-size:0.78rem;font-weight:800;color:{sev_color};letter-spacing:0.12em;">{severity.upper()}</div>
                <div style="font-size:0.7rem;color:#64748b;margin-top:0.2rem;">SEVERITY</div>
            </div>
            <div style="font-size:0.75rem;color:#64748b;line-height:1.7;min-width:140px;">
                <div>ID: <span style="color:#94a3b8;">{evt_id}</span></div>
                <div>Source: <span style="color:#94a3b8;">{evt_source}</span></div>
                {time_row}
                {impact_row}
            </div>
        </div>
        """, unsafe_allow_html=True)

    render_map(
        location_name=st.session_state.route_dest,
        severity=scout_data.get("severity", "HIGH") if scout_data else "LOW",
        rerouting=is_rerouting and raw_new_mode is not None,
        old_mode="TRUCK",
        new_mode=new_mode_key,
        custom_origin=st.session_state.route_origin,
        custom_dest=st.session_state.route_dest,
    )

with col_right:
    # DEMO PROGRESSION
    if demo_mode:
        st.markdown("<h3 style='color: white; margin-top: 1rem; margin-bottom: 1rem;'>Demo Sequence</h3>", unsafe_allow_html=True)
        step = 0
        if final_res: step = 5
        elif intel_data: step = 4
        elif analyst_data: step = 3
        elif scout_data: step = 2
        elif load_json(SHARED_DIR / "signal.json"): step = 1
        steps = ["Chaos Injected", "Scout Analysis", "Risk Assessment", "Strategy Simulation", "Final Decision"]
        msgs = ["Awaiting system trigger...", "Detecting disruption anomalies...", "Analyzing blast radius impact...", "Simulating alternatives...", "Calculating ROI...", "System stabilized."]
        for i, s_name in enumerate(steps):
            s_idx = i + 1
            if s_idx == step:
                st.markdown(f"<div style='color: #818cf8; font-weight: 700; border-left: 3px solid #818cf8; padding: 0.4rem 0.75rem; margin-bottom: 0.4rem; background: rgba(129,140,248,0.08); font-size: 0.85rem;'>{i+1}. {s_name}</div>", unsafe_allow_html=True)
            elif s_idx < step:
                st.markdown(f"<div style='color: #334155; padding: 0.4rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.85rem;'>✓ {s_name}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color: #475569; padding: 0.4rem 0.75rem; margin-bottom: 0.4rem; font-size: 0.85rem;'>{i+1}. {s_name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='demo-msg'>STATUS: {msgs[step]}</div>", unsafe_allow_html=True)

    # LIVE RISK DASHBOARD
    st.markdown("<h3 style='color: white; margin-top: 1.5rem; margin-bottom: 0.75rem;'>Live Risk Dashboard</h3>", unsafe_allow_html=True)
    if final_res:
        roi_data = final_res.get("roi", {})
        savings = roi_data.get("savings", "---")
        mode_reco = final_res.get("recommended_route", "UNKNOWN").upper()
        st.markdown(f'<div class="metric-value" style="color: #818cf8; font-size: 2.5rem;">₹ {savings:,}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Projected Savings</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value" style="color: #38bdf8; font-size: 2rem; margin-top: 1rem;">{mode_reco}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Authorized Mode</div>', unsafe_allow_html=True)
        briefing = final_res.get("summary_text") or "No executive summary."
        st.info(f"{briefing}")
        audio_path = os.path.join(BASE_DIR, "04_manager_module", "alert_english.mp3")
        if not os.path.exists(audio_path): audio_path = os.path.join(BASE_DIR, "04_manager_module", "alert.mp3")
        if os.path.exists(audio_path): st.audio(audio_path, format="audio/mp3")
    elif intel_data:
        mode_reco = intel_data.get("recommended_mode", "UNKNOWN").upper()
        st.markdown(f'<div class="metric-value" style="color: #38bdf8; font-size: 2rem;">{mode_reco}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">RECOMMENDED ROUTE</div>', unsafe_allow_html=True)
        conf = float(intel_data.get("match_confidence", 0.0)) * 100
        st.info(f"Confidence: {conf:.1f}%")
    elif analyst_data:
        risk_val = analyst_data.get("total_value_at_risk", 0)
        st.markdown(f'<div class="metric-value" style="color: #ef4444; font-size: 2rem;">₹ {risk_val:,}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">TOTAL INR AT RISK</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color: #475569; font-style: italic;">Waiting for system signals.</div>', unsafe_allow_html=True)

    # AGENT INTELLIGENCE FEED
    st.markdown("<h3 style='color: white; margin-top: 1.5rem; margin-bottom: 0.75rem;'>Agent Intelligence Feed</h3>", unsafe_allow_html=True)
    feed = {"Scout": scout_data, "Analyst": analyst_data, "Strategist": intel_data, "Manager": final_res}
    has_feed = False
    for label, data in feed.items():
        if data and "agent_thoughts" in data:
            st.markdown(f"<div class='agent-label'>{label} Agent</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='agent-thought'>{data['agent_thoughts']}</div>", unsafe_allow_html=True)
            has_feed = True
    if not has_feed:
        st.markdown('<div style="color: #475569; font-style: italic;">Waiting for agents...</div>', unsafe_allow_html=True)

if st.session_state.get("auto_refresh", True):
    time.sleep(3); st.rerun()
