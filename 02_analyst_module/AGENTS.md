# Analyst Agent - NexusPath

**Role:** Financial Risk Lead | **Module:** `/02_analyst_module`

## Overview
The Analyst Agent processes disruption signals from the Scout Agent and calculates financial risk for affected shipments.

## Files Owned
```
/02_analyst_module/
├── analyst_agent.py   # Main agent with Groq AI integration
├── shipments.json     # 15 shipment records
└── AGENTS.md          # This file
```

## Input/Output
| Direction | File | Description |
|-----------|------|-------------|
| Reads | `/shared_exchange/scout_output.json` | Disruption event from Scout |
| Writes | `/shared_exchange/analyst_output.json` | Risk analysis output |

## scout_output.json Format
```json
{
  "event": "STORM",
  "location": "Mumbai",
  "severity": "HIGH"
}
```

## analyst_output.json Format
```json
{
  "event": "PORT_CLOSURE",
  "location": "Mumbai",
  "severity": "HIGH",
  "affected_shipments": [
    {"id": "SHP-001", "value": 285000, "route": "NH-66", "cargo": "Electronics", "risk_score": 70}
  ],
  "total_value_at_risk": 2787500,
  "metrics": {
    "affected_count": 11,
    "total_value_at_risk": 2787500,
    "average_value": 253409,
    "risk_level": "HIGH"
  },
  "agent_thoughts": "...",
  "recommended_action": "..."
}
```

## Risk Classification
| V_risk (INR) | Risk Level |
|--------------|------------|
| < 100,000 | LOW |
| 100,000 - 499,999 | MEDIUM |
| >= 500,000 | HIGH |

## Route-to-Cities Mapping
- **NH-66**: Mumbai, Thane, Panvel, Goa, Mangalore, Kochi, Thiruvananthapuram, Coimbatore
- **NH-44**: Chennai, Salem, Bangalore
- **NH-48**: Bangalore, Mysore, Mangalore, Kochi
- **Sea Route**: Mumbai, Goa, Mangalore, Kochi, Cochin Port

## Disruption Matching Logic
A shipment is **AFFECTED** if:
1. Disruption location is in the shipment's route cities
2. OR disruption location matches origin
3. OR disruption location matches destination

## Risk Score Calculation
```
risk_score = priority_weight + severity_weight + cargo_risk
```
- Priority weights: CRITICAL=40, HIGH=30, MEDIUM=20, LOW=10
- Severity weights: CRITICAL=40, HIGH=30, MEDIUM=20, LOW=10
- Cargo risk: Chemicals/Pharmaceuticals=20, Others=10
- Max score: 100

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | No | Enables LLM analysis (falls back to rule-based) |

## Usage
```bash
# Run once
python analyst_agent.py

# Watch mode (auto-run on scout_output change)
python analyst_agent.py --watch

# With LLM analysis
export GROQ_API_KEY=your_key
python analyst_agent.py
```

## Dependencies
- `groq` - LLM inference (optional)

## Shipments Distribution (15 total)
- 9 shipments using NH-66 (Kochi highway)
- 2 shipments using NH-44
- 2 shipments using NH-48
- 2 shipments using Sea Route
- 2 shipments via Cochin Port
- Cargo types: Electronics, Pharmaceuticals, Textiles, Machinery, Chemicals, Marine Products, Coffee, etc.
