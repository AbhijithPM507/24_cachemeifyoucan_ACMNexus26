import json
import os
import time
from datetime import datetime
from strategist_agent import run_strategist, agent_thoughts as strategist_thoughts
from simulator_agent import run_simulator, agent_thoughts as simulator_thoughts

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_EXCHANGE = os.path.join(os.path.dirname(SCRIPT_DIR), "shared_exchange")
ANALYST_OUTPUT_PATH = os.path.join(SHARED_EXCHANGE, "analyst_output.json")
INTEL_OUTPUT_PATH = os.path.join(SHARED_EXCHANGE, "intel_output.json")
PAST_EVENTS_PATH = os.path.join(SCRIPT_DIR, "past_events.json")

EVENT_COUNTER_FILE = os.path.join(SCRIPT_DIR, "event_counter.json")

def load_event_counter():
    if os.path.exists(EVENT_COUNTER_FILE):
        with open(EVENT_COUNTER_FILE, "r") as f:
            return json.load(f)
    return {"counter": 0}

def save_event_counter(counter_data):
    with open(EVENT_COUNTER_FILE, "w") as f:
        json.dump(counter_data, f, indent=2)

def get_next_event_id():
    counter_data = load_event_counter()
    event_id = counter_data["counter"] + 1
    counter_data["counter"] = event_id
    save_event_counter(counter_data)
    return f"EVT-{event_id:03d}"

def load_analyst_output():
    if not os.path.exists(ANALYST_OUTPUT_PATH):
        return None
    try:
        with open(ANALYST_OUTPUT_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

def load_past_events():
    if os.path.exists(PAST_EVENTS_PATH):
        with open(PAST_EVENTS_PATH, "r") as f:
            return json.load(f)
    return []

def save_past_events(events):
    with open(PAST_EVENTS_PATH, "w") as f:
        json.dump(events, f, indent=2)

def update_memory(analyst_output, strategist_output, simulator_output):
    past_events = load_past_events()
    
    event_id = get_next_event_id()
    
    recommended_mode = simulator_output.get("oracle_recommendation", {}).get("recommended_mode", "Unknown")
    match_confidence = simulator_output.get("oracle_recommendation", {}).get("confidence_score", 0.0)
    
    if match_confidence >= 0.7:
        early_action = "Yes"
    elif match_confidence >= 0.5:
        early_action = "Recommended"
    else:
        early_action = "No"
    
    alternative_routes = simulator_output.get("oracle_recommendation", {}).get("alternative_modes", [])
    
    historical_bias = strategist_output.get("bias_factor", 1.0)
    
    new_event = {
        "event_id": event_id,
        "event_type": analyst_output.get("event_type", "Unknown"),
        "location": analyst_output.get("location", "Unknown"),
        "severity": analyst_output.get("severity", 5),
        "lesson_learned": strategist_output.get("strategic_lesson", ""),
        "chosen_route": recommended_mode,
        "early_action_recommended": early_action,
        "alternative_routes": alternative_routes,
        "bias_factor_applied": historical_bias,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    past_events.append(new_event)
    save_past_events(past_events)
    
    return event_id, new_event

def get_combined_thoughts():
    all_thoughts = strategist_thoughts + simulator_thoughts
    return "\n".join(all_thoughts) if all_thoughts else "No thoughts recorded"

def run_coordinator():
    print("=" * 60)
    print("INTEL COORDINATOR INITIALIZED")
    print("=" * 60)
    print(f"Watching: {ANALYST_OUTPUT_PATH}")
    print(f"Output: {INTEL_OUTPUT_PATH}")
    print(f"Memory: {PAST_EVENTS_PATH}")
    print("=" * 60)
    print()
    
    last_mtime = None
    
    while True:
        try:
            if not os.path.exists(ANALYST_OUTPUT_PATH):
                time.sleep(1)
                continue
            
            current_mtime = os.path.getmtime(ANALYST_OUTPUT_PATH)
            
            if last_mtime is None or current_mtime > last_mtime:
                last_mtime = current_mtime
                
                print("-" * 40)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyst output detected...")
                print("-" * 40)
                
                analyst_output = load_analyst_output()
                
                if analyst_output is None:
                    print("Warning: Empty or invalid analyst output, skipping...")
                    time.sleep(1)
                    continue
                
                print(f"  Event: {analyst_output.get('event_type', 'Unknown')}")
                print(f"  Location: {analyst_output.get('location', 'Unknown')}")
                print(f"  Severity: {analyst_output.get('severity', 'Unknown')}")
                print()
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Running strategist reasoning...")
                strategist_output = run_strategist(analyst_output)
                print(f"  Matched Event ID: {strategist_output.get('matched_event_id')}")
                print(f"  Strategic Lesson: {strategist_output.get('strategic_lesson', '')[:60]}...")
                print(f"  Bias Factor: {strategist_output.get('bias_factor')}")
                print()
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Running simulator...")
                simulator_output = run_simulator(analyst_output, strategist_output)
                recommended = simulator_output.get("oracle_recommendation", {})
                print(f"  Recommended Mode: {recommended.get('recommended_mode', 'Unknown')}")
                print(f"  Confidence: {recommended.get('confidence_score', 0):.0%}")
                print(f"  Risk: {recommended.get('risk_assessment', 'Unknown')}")
                print()
                
                match_confidence = recommended.get("confidence_score", 0.0)
                if match_confidence >= 0.7:
                    early_action = True
                else:
                    early_action = False
                
                intel_output = {
                    "strategic_lesson": strategist_output.get("strategic_lesson", ""),
                    "matched_event_id": strategist_output.get("matched_event_id", -1),
                    "match_confidence": match_confidence,
                    "early_action_recommended": early_action,
                    "alternative_routes": recommended.get("alternative_modes", []),
                    "recommended_mode": recommended.get("recommended_mode", "Unknown"),
                    "risk_assessment": recommended.get("risk_assessment", "MEDIUM"),
                    "bias_factor": strategist_output.get("bias_factor", 1.0),
                    "simulation_details": simulator_output.get("simulation_results", []),
                    "reasoning": recommended.get("reasoning", ""),
                    "agent_thoughts": get_combined_thoughts(),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(INTEL_OUTPUT_PATH, "w") as f:
                    json.dump(intel_output, f, indent=2)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Intel output written to {INTEL_OUTPUT_PATH}")
                print()
                
                event_id, new_event = update_memory(analyst_output, strategist_output, simulator_output)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Memory updated: {event_id} added to experience buffer")
                print(f"  Route chosen: {new_event.get('chosen_route')}")
                print(f"  Early action: {new_event.get('early_action_recommended')}")
                print()
                print("=" * 60)
                print("CYCLE COMPLETE - AWAITING NEXT INPUT")
                print("=" * 60)
                print()
                
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\nCoordinator shutdown requested...")
            break
        except Exception as e:
            print(f"Error in coordinator loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_coordinator()
