import json
import os
import math
import numpy as np
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(project_root, ".env"))

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

agent_thoughts = []

def map_severity(severity_text):
    severity_map = {
        "LOW": 0.4,
        "MEDIUM": 0.7,
        "HIGH": 1.0,
        "CRITICAL": 1.0,
        "1": 0.4,
        "2": 0.4,
        "3": 0.4,
        "4": 0.7,
        "5": 0.7,
        "6": 0.7,
        "7": 1.0,
        "8": 1.0,
        "9": 1.0,
        "10": 1.0
    }
    if isinstance(severity_text, (int, float)):
        if severity_text <= 3:
            return 0.4
        elif severity_text <= 6:
            return 0.7
        else:
            return 1.0
    return severity_map.get(str(severity_text).upper(), 0.7)

def run_monte_carlo_sim(mode, intensity, bias_factor, iterations=100, target_window=None):
    base_params = {
        "Air": {"mu": 0.5, "sigma": 0.1},
        "Rail": {"mu": 2.0, "sigma": 0.2},
        "Road_bypass": {"mu": 1.2, "sigma": 0.5}
    }
    
    params = base_params.get(mode, {"mu": 2.0, "sigma": 0.3})
    mu = params["mu"]
    sigma = params["sigma"]
    
    simulated_times = []
    for _ in range(iterations):
        simulated_time = mu + (np.random.normal() * sigma * intensity * bias_factor)
        simulated_times.append(max(0.1, simulated_time))
    
    mean_time = np.mean(simulated_times)
    std_time = np.std(simulated_times)
    
    if target_window is None:
        target_window = mu
    
    p_arrival = float(np.mean([1 if t <= target_window else 0 for t in simulated_times]))
    
    cdf_value = float((1 + math.erf((target_window - mean_time) / (std_time * np.sqrt(2)))) / 2)
    
    return {
        "mode": mode,
        "iterations": iterations,
        "mean_time": round(mean_time, 3),
        "std_time": round(std_time, 3),
        "min_time": round(min(simulated_times), 3),
        "max_time": round(max(simulated_times), 3),
        "p_arrival_within_target": round(p_arrival, 3),
        "cdf_probability": round(cdf_value, 3),
        "target_window": target_window
    }

def run_simulator(analyst_output, strategist_output):
    intensity = map_severity(analyst_output.get("severity", "MEDIUM"))
    bias_factor = strategist_output.get("bias_factor", 1.0)
    strategic_lesson = strategist_output.get("strategic_lesson", "")
    
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
        sim_result = run_monte_carlo_sim(mode, intensity, bias_factor, target_window=target_window)
        results.append(sim_result)
        
        insight = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Simulator: Mode={mode}, mean={sim_result['mean_time']}d, P(arrival)={sim_result['p_arrival_within_target']}"
        agent_thoughts.append(insight)
    
    system_prompt = """You are a Logistics Simulation Oracle analyzing probabilistic delivery scenarios.

You have run Monte Carlo simulations for multiple transport modes. Your task is to interpret the results and provide strategic recommendations.

Analyze the simulation results considering:
1. Probability of arrival within target window
2. Mean delivery time
3. Variance and risk
4. Historical strategic lesson

Return ONLY a JSON object with this exact structure:
{
    "recommended_mode": (string) - Best mode for this scenario,
    "confidence_score": (float) - 0.0 to 1.0 confidence in recommendation,
    "risk_assessment": (string) - "LOW", "MEDIUM", or "HIGH",
    "reasoning": (string) - Brief explanation of the recommendation,
    "alternative_modes": (array) - Array of mode names ranked by preference
}"""

    user_prompt = f"""Simulate this delivery scenario:

ANALYST OUTPUT:
{json.dumps(analyst_output, indent=2)}

STRATEGIST OUTPUT:
{json.dumps(strategist_output, indent=2)}

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
            "bias_factor_used": bias_factor
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
                "alternative_modes": [r["mode"] for r in sorted(results, key=lambda x: x["p_arrival_within_target"], reverse=True)]
            },
            "intensity_used": intensity,
            "bias_factor_used": bias_factor,
            "error": str(e)
        }
        
        insight = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Simulator: Oracle failed ({str(e)}), using fallback"
        agent_thoughts.append(insight)
        
        return fallback

if __name__ == "__main__":
    sample_analyst = {
        "event_type": "Flood",
        "location": "NH-66, Goa coast",
        "severity": "HIGH",
        "description": "Heavy flooding on NH-66 affecting road transport"
    }
    
    sample_strategist = {
        "matched_event_id": 0,
        "strategic_lesson": "Last time NH-66 flooded, the Rail bypass was 4 hours faster than the hill road",
        "bias_factor": 1.2
    }
    
    result = run_simulator(sample_analyst, sample_strategist)
    print(json.dumps(result, indent=2))
    print("\nAgent Thoughts Log:")
    for thought in agent_thoughts:
        print(thought)
