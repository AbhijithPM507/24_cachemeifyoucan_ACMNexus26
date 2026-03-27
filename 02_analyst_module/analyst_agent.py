import json
import os
import time
from groq import Groq

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SHIPMENTS_FILE = os.path.join(SCRIPT_DIR, "shipments.json")
SCOUT_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "shared_exchange", "scout_output.json")
ANALYST_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "shared_exchange", "analyst_output.json")

ROUTE_TO_CITIES = {
    "NH-66": ["Mumbai", "Thane", "Panvel", "Goa", "Mangalore", "Kochi", "Thiruvananthapuram", "Coimbatore"],
    "NH-44": ["Chennai", "Salem", "Namakkal", "Karur", "Dindigul", "Madurai", "Tirunelveli", "Bangalore"],
    "NH-48": ["Bangalore", "Mysore", "Madikeri", "Mangalore", "Kochi"],
    "Sea Route": ["Mumbai", "Goa", "Mangalore", "Kochi", "Cochin Port"],
    "Sea Route via NH-66": ["Mumbai", "Kochi", "Cochin Port"]
}

SYSTEM_PROMPT = """IMPORTANT: Use INR (₹) for ALL monetary values. Never use $ or USD.

You are the Analyst Agent for NexusPath supply chain system.

Your role: Calculate financial risk when disruptions occur.

## Risk Classification Rules
| V_risk (INR) | Risk Level |
|--------------|------------|
| < 100,000 | LOW |
| 100,000 - 499,999 | MEDIUM |
| >= 500,000 | HIGH |

## Route-to-Cities Mapping
- NH-66: Mumbai, Thane, Panvel, Goa, Mangalore, Kochi, Thiruvananthapuram, Coimbatore
- NH-44: Chennai, Salem, Bangalore (via NH-44 stretch)
- NH-48: Bangalore, Mysore, Madikeri, Mangalore, Kochi
- Sea Route: Mumbai, Goa, Mangalore, Kochi, Cochin Port
- Sea Route via NH-66: Mumbai, Kochi, Cochin Port

## Disruption Matching Logic
Only flag a shipment as affected if its route DIRECTLY passes through Kochi - meaning NH-66 or roads that explicitly run through Kochi city. Do NOT flag NH-48 (Mumbai-Bangalore corridor) or pure Sea Routes as affected by a road closure in Kochi. A shipment whose destination is Kochi is affected only if no alternate approach road exists.

Currency is INR. All shipment values are in INR. Use ₹ for all monetary values.

## Output Format
Return JSON with:
- affected_shipments: list of affected shipment IDs and values
- metrics: affected_count, total_value_at_risk, average_value, risk_level
- agent_thoughts: summary of findings (must use ₹ and INR only, never $ or USD)
- recommended_action: directive for next agent

For EACH affected shipment, you MUST write a non-empty reason field. The reason must be a single sentence mentioning: - The specific cargo type (e.g. Electronics, Chemicals) - The shipment priority level - Why the NH-66 road closure at Kochi specifically impacts this shipment Example: 'HIGH priority Electronics shipment is directly blocked as NH-66 is its primary route through Kochi with no bypass available.' An empty reason field is not acceptable."

Be precise and only flag shipments that truly pass through the disruption zone."""


def get_route_cities(route_name):
    for key, cities in ROUTE_TO_CITIES.items():
        if key.lower() in route_name.lower():
            return cities
    return []


def filter_affected_shipments(shipments, scout_output):
    disrupted_location = scout_output["location"]
    severity = scout_output["severity"]
    affected = []
    
    print(f"\nFiltering shipments affected by disruption at: {disrupted_location}")
    
    for shipment in shipments:
        is_affected = False
        route = shipment["route"]
        
        if disrupted_location == "Kochi":
            if "NH-66" in route and disrupted_location in get_route_cities(route):
                is_affected = True
        else:
            route_cities = get_route_cities(route)
            if disrupted_location in route_cities:
                is_affected = True
        
        if is_affected:
            risk_score = calculate_risk_score(shipment, severity)
            reason = generate_reason(shipment)
            affected.append({
                "id": shipment["id"],
                "value": shipment["value"],
                "route": shipment["route"],
                "cargo": shipment["cargo"],
                "priority": shipment["priority"],
                "risk_score": risk_score,
                "reason": reason
            })
            print(f"  -> {shipment['id']}: route={shipment['route']} cargo={shipment['cargo']} (Risk Score: {risk_score})")
    
    print(f"\nFound {len(affected)} shipments affected by disruption at {disrupted_location}")
    return affected


def calculate_risk_score(shipment, severity):
    priority_weights = {"CRITICAL": 40, "HIGH": 30, "MEDIUM": 20, "LOW": 10}
    severity_weights = {"CRITICAL": 40, "HIGH": 30, "MEDIUM": 20, "LOW": 10}
    
    base_score = priority_weights.get(shipment["priority"], 15)
    severity_bonus = severity_weights.get(severity, 15)
    
    cargo_risk = 20 if shipment["cargo"] in ["Chemicals", "Pharmaceuticals"] else 10
    
    return min(100, base_score + severity_bonus + cargo_risk)


def generate_reason(shipment, disruption_location="Kochi"):
    cargo = shipment["cargo"]
    priority = shipment["priority"]
    route = shipment["route"]
    
    reason_templates = {
        ("Electronics", "HIGH"): f"HIGH priority Electronics shipment blocked as NH-66 through {disruption_location} is its primary route with no bypass.",
        ("Electronics", "CRITICAL"): f"CRITICAL Electronics shipment faces immediate disruption on NH-66 through {disruption_location}.",
        ("Electronics", "MEDIUM"): f"MEDIUM priority Electronics shipment must detour from NH-66 near {disruption_location}.",
        ("Textiles", "HIGH"): f"HIGH priority Textiles shipment cannot transit through {disruption_location} on NH-66.",
        ("Textiles", "MEDIUM"): f"MEDIUM priority Textiles shipment rerouted around blocked NH-66 at {disruption_location}.",
        ("Textiles", "LOW"): f"LOW priority Textiles shipment delayed due to NH-66 closure at {disruption_location}.",
        ("Machinery", "HIGH"): f"HIGH priority Machinery shipment stranded as NH-66 through {disruption_location} is impassable.",
        ("Machinery", "CRITICAL"): f"CRITICAL Machinery shipment severely impacted by NH-66 road closure at {disruption_location}.",
        ("Automobile Parts", "HIGH"): f"HIGH priority Automobile Parts shipment blocked on NH-66 at {disruption_location}.",
        ("Automobile Parts", "CRITICAL"): f"CRITICAL Automobile Parts shipment faces delivery failure due to NH-66 closure at {disruption_location}.",
        ("Spices", "MEDIUM"): f"MEDIUM priority Spices shipment must bypass blocked NH-66 near {disruption_location}.",
        ("Marine Products", "HIGH"): f"HIGH priority Marine Products shipment disrupted as NH-66 through {disruption_location} is closed.",
        ("Agricultural Products", "LOW"): f"LOW priority Agricultural Products shipment delayed on NH-66 near {disruption_location}.",
        ("Coffee", "MEDIUM"): f"MEDIUM priority Coffee shipment affected by NH-66 closure at {disruption_location}.",
        ("Chemicals", "CRITICAL"): f"CRITICAL Chemicals shipment dangerous situation - NH-66 through {disruption_location} blocked with no safe alternative.",
        ("Chemicals", "HIGH"): f"HIGH priority Chemicals shipment must find alternate route around {disruption_location} on NH-66.",
        ("Pharmaceuticals", "HIGH"): f"HIGH priority Pharmaceuticals shipment time-sensitive route through {disruption_location} is blocked.",
        ("Pharmaceuticals", "CRITICAL"): f"CRITICAL Pharmaceuticals shipment urgent - NH-66 through {disruption_location} is only viable route.",
    }
    
    key = (cargo, priority)
    if key in reason_templates:
        return reason_templates[key]
    
    return f"{priority} priority {cargo} shipment blocked on NH-66 at {disruption_location} - no alternate bypass available."


def calculate_metrics(affected_shipments):
    total_value = sum(s["value"] for s in affected_shipments)
    affected_count = len(affected_shipments)
    average_value = total_value // affected_count if affected_count > 0 else 0
    
    if total_value < 100000:
        risk_level = "LOW"
    elif total_value < 500000:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    
    print(f"\n--- Financial Metrics ---")
    print(f"Total Value at Risk: {total_value:,} INR")
    print(f"Average Value per Shipment: {average_value:,} INR")
    print(f"Risk Level: {risk_level}")
    
    return {
        "affected_count": affected_count,
        "total_value_at_risk": total_value,
        "average_value": average_value,
        "risk_level": risk_level
    }


def call_groq_llm(scout_output, affected_shipments, metrics):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n[Rule-based mode - set GROQ_API_KEY for LLM analysis]")
        return None
    
    try:
        client = Groq(api_key=api_key)
        
        user_prompt = f"""Analyze this supply chain disruption:

Event: {scout_output['event']}
Location: {scout_output['location']}
Severity: {scout_output['severity']}

Affected Shipments:
{json.dumps(affected_shipments, indent=2)}

Metrics: {metrics['affected_count']} shipments, ₹{metrics['total_value_at_risk']:,} at risk, {metrics['risk_level']} level

For EACH affected shipment, you MUST write a non-empty reason field. The reason must be a single sentence mentioning:
- The specific cargo type (e.g. Electronics, Chemicals)
- The shipment priority level
- Why the NH-66 road closure at Kochi specifically impacts this shipment
Example: 'HIGH priority Electronics shipment is directly blocked as NH-66 is its primary route through Kochi with no bypass available.'

Output ONLY valid JSON in this exact format:
{{
  "affected_shipments": [
    {{"id": "...", "value": ..., "route": "...", "cargo": "...", "risk_score": ..., "reason": "YOUR REASON HERE"}}
  ],
  "total_value_at_risk": {metrics['total_value_at_risk']},
  "recommended_action": "YOUR ACTION",
  "agent_thoughts": "YOUR THOUGHTS using ₹ and INR"
}}

YOUR ENTIRE RESPONSE MUST BE ONLY THE JSON OBJECT ABOVE.
No explanation. No preamble. No markdown. No prose.
Start your response with {{ and end with }}. Nothing else."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        llm_summary = response.choices[0].message.content
        print(f"\n--- LLM Analysis ---\n{llm_summary}")
        return llm_summary
    except Exception as e:
        print(f"\nLLM call failed: {e}")
        return None


def get_backup_routes(affected_shipments):
    routes_used = set(s["route"] for s in affected_shipments)
    alternatives = {
        "NH-66": "NH-48 or NH-44",
        "NH-44": "NH-66 via alternate path",
        "NH-48": "NH-7",
        "Sea Route": "Air freight",
        "Sea Route via NH-66": "Air freight"
    }
    suggestions = [alternatives.get(r, "alternate route") for r in routes_used if r in alternatives]
    return ", ".join(suggestions) if suggestions else "alternate routes"


def save_output(scout_output, affected_shipments, metrics, llm_output=None):
    if llm_output:
        try:
            llm_result = json.loads(llm_output)
            os.makedirs(os.path.dirname(ANALYST_OUTPUT_FILE), exist_ok=True)
            with open(ANALYST_OUTPUT_FILE, "w") as f:
                json.dump(llm_result, f, indent=2)
            print(f"\nSaved analysis to {ANALYST_OUTPUT_FILE}")
            return llm_result
        except json.JSONDecodeError:
            print("Warning: LLM returned invalid JSON, using rule-based output")
    
    risk_level = metrics["risk_level"]
    recommended_action = f"Immediate rerouting or delay notification for affected shipments. Consider activating backup routes via {get_backup_routes(affected_shipments)}."
    agent_thoughts = f"{metrics['affected_count']} shipments totaling ₹{metrics['total_value_at_risk']:,} at {risk_level} risk. {risk_level} risk exposure requires immediate attention."
    
    result = {
        "affected_shipments": [
            {
                "id": s["id"],
                "value": s["value"],
                "route": s["route"],
                "cargo": s["cargo"],
                "risk_score": s["risk_score"],
                "reason": s["reason"]
            }
            for s in affected_shipments
        ],
        "total_value_at_risk": metrics["total_value_at_risk"],
        "recommended_action": recommended_action,
        "agent_thoughts": agent_thoughts
    }
    
    os.makedirs(os.path.dirname(ANALYST_OUTPUT_FILE), exist_ok=True)
    with open(ANALYST_OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nSaved analysis to {ANALYST_OUTPUT_FILE}")
    print(f"Analyst: {metrics['total_value_at_risk']:,} INR at risk across {metrics['affected_count']} shipments")
    return result


def run_analyst_agent():
    print("=" * 60)
    print("ANALYST AGENT - Financial Risk Assessment (Groq AI)")
    print("=" * 60)
    
    if not os.path.exists(SCOUT_OUTPUT_FILE):
        print(f"ERROR: Scout output file not found: {SCOUT_OUTPUT_FILE}")
        return None
    
    if not os.path.exists(SHIPMENTS_FILE):
        print(f"ERROR: Shipments file not found: {SHIPMENTS_FILE}")
        return None
    
    try:
        scout_output = json.load(open(SCOUT_OUTPUT_FILE))
        shipments = json.load(open(SHIPMENTS_FILE))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON - {e}")
        return None
    
    print(f"Loaded scout data: {scout_output['event']} at {scout_output['location']}")
    print(f"Loaded {len(shipments)} shipments")
    
    affected = filter_affected_shipments(shipments, scout_output)
    metrics = calculate_metrics(affected)
    llm_output = call_groq_llm(scout_output, affected, metrics)
    result = save_output(scout_output, affected, metrics, llm_output)
    
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    return result


def watch_and_run():
    print("Analyst watching for scout_output.json...")
    last_mtime = 0
    while True:
        if os.path.exists(SCOUT_OUTPUT_FILE):
            mtime = os.path.getmtime(SCOUT_OUTPUT_FILE)
            if mtime > last_mtime:
                last_mtime = mtime
                print("\n>>> Scout output detected - running Analyst...\n")
                run_analyst_agent()
                print()
        time.sleep(1)


if __name__ == "__main__":
    run_analyst_agent()
