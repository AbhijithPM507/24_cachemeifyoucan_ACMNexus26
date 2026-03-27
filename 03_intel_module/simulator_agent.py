import json
import os
import math
import time
import requests
import numpy as np
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
from functools import lru_cache

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(project_root, ".env"))

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

agent_thoughts = []

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
}

OSRM_CACHE = {}
OSRM_CACHE_TTL = 300

def get_osrm_route(origin_coords, dest_coords, waypoint_coords=None):
    cache_key = f"{origin_coords['lon']},{origin_coords['lat']}|{dest_coords['lon']},{dest_coords['lat']}"
    if waypoint_coords:
        cache_key += f"|{waypoint_coords['lon']},{waypoint_coords['lat']}"
    
    if cache_key in OSRM_CACHE:
        cached_time, cached_data = OSRM_CACHE[cache_key]
        if time.time() - cached_time < OSRM_CACHE_TTL:
            agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OSRM: Cache hit for route")
            return cached_data
    
    base_url = "http://router.project-osrm.org/route/v1/driving"
    coords = f"{origin_coords['lon']},{origin_coords['lat']};{dest_coords['lon']},{dest_coords['lat']}"
    if waypoint_coords:
        coords += f";{waypoint_coords['lon']},{waypoint_coords['lat']}"
    
    url = f"{base_url}/{coords}?overview=false"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            result = {
                "distance_meters": route["distance"],
                "duration_seconds": route["duration"],
                "distance_km": round(route["distance"] / 1000, 2),
                "duration_hours": round(route["duration"] / 3600, 2),
                "waypoint_used": waypoint_coords is not None
            }
            
            OSRM_CACHE[cache_key] = (time.time(), result)
            agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OSRM: Fetched route {result['distance_km']}km in {result['duration_hours']}h")
            return result
        else:
            return None
            
    except Exception as e:
        agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OSRM Error: {str(e)}")
        return None

def extract_waypoint(strategic_lesson):
    lesson = strategic_lesson.lower()
    for hub_name, coords in KERALA_HUBS.items():
        if hub_name.lower() in lesson:
            agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OSRM: Found waypoint suggestion: {hub_name}")
            return coords
    return None

def extract_coords_from_location(location_str):
    location_lower = location_str.lower()
    for hub_name, coords in KERALA_HUBS.items():
        if hub_name.lower() in location_lower:
            return coords
    return None

def get_route_coords(analyst_output, default_origin="Mumbai", default_dest="Kochi"):
    origin_name = analyst_output.get("origin")
    destination_name = analyst_output.get("destination")
    
    origin = KERALA_HUBS.get(origin_name) if origin_name else None
    destination = KERALA_HUBS.get(destination_name) if destination_name else None
    
    if not origin:
        affected = analyst_output.get("affected_shipments", [])
        if affected:
            route = affected[0].get("route", "")
            if "NH-66" in route:
                destination = KERALA_HUBS.get("Kochi")
            elif "NH-44" in route:
                destination = KERALA_HUBS.get("Bangalore")
            else:
                destination = KERALA_HUBS.get("Kochi")
        else:
            destination = KERALA_HUBS.get(default_dest, KERALA_HUBS["Kochi"])
    
    if not destination:
        location = analyst_output.get("location", "")
        dest_coords = extract_coords_from_location(location)
        if dest_coords:
            destination = dest_coords
        else:
            destination = KERALA_HUBS.get(default_dest, KERALA_HUBS["Kochi"])
    
    if not origin:
        origin = KERALA_HUBS.get(default_origin, KERALA_HUBS["Mumbai"])
    
    return origin, destination

def map_severity(severity_text):
    severity_map = {
        "LOW": 0.4,
        "MEDIUM": 0.7,
        "HIGH": 1.0,
        "CRITICAL": 1.0,
    }
    if isinstance(severity_text, (int, float)):
        if severity_text <= 3:
            return 0.4
        elif severity_text <= 6:
            return 0.7
        else:
            return 1.0
    return severity_map.get(str(severity_text).upper(), 0.7)

def run_monte_carlo_sim(mode, osrm_duration_days=None, intensity=0.7, bias_factor=1.0, iterations=100, target_window=None):
    base_params = {
        "Air": {"mu": 0.5, "sigma": 0.1},
        "Rail": {"mu": 2.0, "sigma": 0.2},
        "Road_bypass": {"mu": 1.2, "sigma": 0.5}
    }
    
    if mode == "Road_bypass" and osrm_duration_days:
        mu = osrm_duration_days
        base_sigma = 0.5
    elif mode == "Rail":
        if osrm_duration_days:
            mu = osrm_duration_days * 1.8
        else:
            mu = 2.0
        base_sigma = 0.2
    elif mode == "Air":
        mu = 0.5
        base_sigma = 0.1
    else:
        params = base_params.get(mode, {"mu": 2.0, "sigma": 0.3})
        mu = params["mu"]
        base_sigma = params["sigma"]
    
    if intensity >= 1.0:
        sigma = base_sigma * 1.5
    else:
        sigma = base_sigma
    
    simulated_times = []
    for _ in range(iterations):
        simulated_time = mu + (np.random.normal() * sigma * intensity * bias_factor)
        simulated_times.append(max(0.1, simulated_time))
    
    mean_time = np.mean(simulated_times)
    std_time = np.std(simulated_times)
    
    if target_window is None:
        target_window = mu
    
    p_arrival = float(np.mean([1 if t <= target_window else 0 for t in simulated_times]))
    
    cdf_value = float((1 + math.erf((target_window - mean_time) / (std_time * np.sqrt(2)))) / 2) if std_time > 0 else 0.5
    
    reliability_score = round(1.0 / (1 + std_time / mean_time), 3) if mean_time > 0 else 0.5
    
    return {
        "mode": mode,
        "iterations": iterations,
        "mean_time": round(mean_time, 3),
        "std_time": round(std_time, 3),
        "min_time": round(min(simulated_times), 3),
        "max_time": round(max(simulated_times), 3),
        "p_arrival_within_target": round(p_arrival, 3),
        "cdf_probability": round(cdf_value, 3),
        "target_window": target_window,
        "reliability_score": reliability_score,
        "traffic_volatility": round(sigma / base_sigma, 2) if base_sigma > 0 else 1.0
    }

def run_simulator(analyst_output, strategist_output):
    intensity = map_severity(analyst_output.get("severity", "MEDIUM"))
    bias_factor = strategist_output.get("bias_factor", 1.0)
    strategic_lesson = strategist_output.get("strategic_lesson", "")
    
    origin, destination = get_route_coords(analyst_output)
    
    agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Simulator: Origin={origin}, Dest={destination}")
    
    osrm_data = get_osrm_route(origin, destination)
    
    waypoint = extract_waypoint(strategic_lesson)
    osrm_data_waypoint = None
    if waypoint:
        osrm_data_waypoint = get_osrm_route(origin, destination, waypoint)
    
    priority_modes = ["Road_bypass", "Rail", "Air"]
    lesson_lower = strategic_lesson.lower()
    
    if "rail" in lesson_lower or "train" in lesson_lower:
        priority_modes = ["Rail", "Air", "Road_bypass"]
    elif "road" in lesson_lower or "bypass" in lesson_lower or "highway" in lesson_lower:
        priority_modes = ["Road_bypass", "Rail", "Air"]
    elif "air" in lesson_lower or "fly" in lesson_lower or "airport" in lesson_lower:
        priority_modes = ["Air", "Rail", "Road_bypass"]
    
    target_window = analyst_output.get("target_window", 2.0)
    
    results = []
    for mode in priority_modes:
        osrm_duration = None
        live_data = None
        
        if mode == "Road_bypass" and osrm_data_waypoint:
            osrm_duration = osrm_data_waypoint.get("duration_hours", 24) / 24
            live_data = {
                "osrm_distance_km": osrm_data_waypoint.get("distance_km"),
                "osrm_duration_hours": osrm_data_waypoint.get("duration_hours"),
                "waypoint_used": True
            }
        elif mode == "Road_bypass" and osrm_data:
            osrm_duration = osrm_data.get("duration_hours", 24) / 24
            live_data = {
                "osrm_distance_km": osrm_data.get("distance_km"),
                "osrm_duration_hours": osrm_data.get("duration_hours"),
                "waypoint_used": False
            }
        
        sim_result = run_monte_carlo_sim(mode, osrm_duration, intensity, bias_factor, target_window=target_window)
        sim_result["live_data"] = live_data
        results.append(sim_result)
        
        insight = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Simulator: Mode={mode}, mean={sim_result['mean_time']}d, P(arrival)={sim_result['p_arrival_within_target']}, reliability={sim_result['reliability_score']}"
        agent_thoughts.append(insight)
    
    system_prompt = """You are a Logistics Simulation Oracle analyzing probabilistic delivery scenarios.

You have run Monte Carlo simulations for multiple transport modes using real-time OSRM routing data. Your task is to interpret the results and provide strategic recommendations.

Analyze the simulation results considering:
1. Probability of arrival within target window
2. Mean delivery time from Monte Carlo simulation
3. Reliability score based on traffic volatility
4. Historical strategic lesson from the Strategist
5. Live OSRM routing data if available

Return ONLY a JSON object with this exact structure:
{
    "recommended_mode": (string) - Best mode for this scenario,
    "confidence_score": (float) - 0.0 to 1.0 confidence in recommendation,
    "risk_assessment": (string) - "LOW", "MEDIUM", or "HIGH",
    "reasoning": (string) - Brief explanation combining OSRM live data and historical lessons,
    "alternative_modes": (array) - Array of mode names ranked by preference,
    "best_for": (string) - What cargo type/scenario this mode is best suited for
}"""

    user_prompt = f"""Simulate this delivery scenario using live OSRM routing data:

ANALYST OUTPUT:
{json.dumps(analyst_output, indent=2)}

STRATEGIST OUTPUT:
{json.dumps(strategist_output, indent=2)}

OSRM LIVE DATA:
- Direct route: {osrm_data}
- Via waypoint: {osrm_data_waypoint}

MONTE CARLO SIMULATION RESULTS:
{json.dumps(results, indent=2)}

Priority modes based on strategic lesson: {priority_modes}

Analyze and return JSON recommendation."""

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        response_content = chat_completion.choices[0].message.content
        oracle_result = json.loads(response_content)
        
        final_output = {
            "simulation_results": results,
            "oracle_recommendation": oracle_result,
            "intensity_used": intensity,
            "bias_factor_used": bias_factor,
            "osrm_data": osrm_data,
            "osrm_data_waypoint": osrm_data_waypoint
        }
        
        insight = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Oracle: Recommended {oracle_result.get('recommended_mode')} with {oracle_result.get('confidence_score')} confidence"
        agent_thoughts.append(insight)
        
        return final_output
        
    except Exception as e:
        best_result = max(results, key=lambda x: x["p_arrival_within_target"])
        
        fallback = {
            "simulation_results": results,
            "oracle_recommendation": {
                "recommended_mode": best_result["mode"],
                "confidence_score": 0.5,
                "risk_assessment": "MEDIUM",
                "reasoning": f"LLM failed, defaulting to highest P(arrival) mode: {best_result['mode']}",
                "alternative_modes": [r["mode"] for r in sorted(results, key=lambda x: x["p_arrival_within_target"], reverse=True)],
                "best_for": "Standard shipments"
            },
            "intensity_used": intensity,
            "bias_factor_used": bias_factor,
            "osrm_data": osrm_data,
            "error": str(e)
        }
        
        insight = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Simulator: Oracle failed ({str(e)}), using fallback"
        agent_thoughts.append(insight)
        
        return fallback

if __name__ == "__main__":
    sample_analyst = {
        "event_type": "Flood",
        "location": "NH-66, Kochi",
        "severity": "HIGH",
        "origin": "Mumbai",
        "destination": "Kochi",
        "description": "Heavy flooding on NH-66 affecting road transport"
    }
    
    sample_strategist = {
        "matched_event_id": 0,
        "strategic_lesson": "Last time NH-66 flooded, the Rail bypass was 4 hours faster than the hill road. Consider via Bangalore.",
        "bias_factor": 1.2
    }
    
    result = run_simulator(sample_analyst, sample_strategist)
    print(json.dumps(result, indent=2))
    print("\nAgent Thoughts Log:")
    for thought in agent_thoughts:
        print(thought)
