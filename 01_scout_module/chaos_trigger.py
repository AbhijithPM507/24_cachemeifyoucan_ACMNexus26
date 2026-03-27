import os
import json
import random
import datetime
from pathlib import Path

def trigger_chaos():
    events = ["flash flood", "port strike", "road accident", "cyclone warning", "bridge closure"]
    locations = ["Kochi", "Mumbai", "Mangalore", "Chennai", "Bangalore", "Cochin Port"]
    sources = ["IMD_alert", "traffic_api", "union_feed", "NHAI_feed"]
    highways = ["NH-66", "NH-544", "NH-85"]

    event_type = random.choice(events)
    location = random.choice(locations)
    source = random.choice(sources)
    
    # Base event
    event_data = {
        "id": f"EVT-{random.randint(1000, 9999)}",
        "event": event_type,
        "location": location,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": source
    }

    # Conditional fields
    if event_type in ["flash flood", "cyclone warning"]:
        event_data["severity_raw"] = round(random.uniform(1.0, 10.0), 1)
        event_data["source"] = "IMD_alert" # Logic override for realism
    elif event_type == "port strike":
        event_data["delay_hours"] = random.randint(12, 72)
        event_data["location"] = "Cochin Port" # Logic override for port strike
        event_data["source"] = "union_feed"
    elif event_type in ["road accident", "bridge closure"]:
        event_data["highway"] = random.choice(highways)
        event_data["source"] = random.choice(["traffic_api", "NHAI_feed"])

    # Resolve paths relative to this script
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    shared_exchange_dir = project_root / "shared_exchange"
    
    # Ensure directory exists
    shared_exchange_dir.mkdir(parents=True, exist_ok=True)
    
    signal_file = shared_exchange_dir / "signal.json"
    
    with open(signal_file, "w", encoding="utf-8") as f:
        json.dump(event_data, f, indent=2)
        
    return event_data

if __name__ == "__main__":
    event = trigger_chaos()
    print(f"Chaos triggered! Event saved: {event}")
