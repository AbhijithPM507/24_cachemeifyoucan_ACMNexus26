# 🚚 Transit

## Agentic Supply Chain Swarm with Dynamic Load Pooling

**By CLIQUE x ACM MITS | NEXUS Hackathon 2026**

---

## Overview

Transit is an AI-driven supply chain resilience system that autonomously responds to Black Swan disruptions (floods, strikes, accidents, cyclones, bridge closures). Unlike traditional reactive systems, Transit uses a multi-agent swarm architecture that **learns from historical disruptions**, **simulates multiple route alternatives**, and **monetizes empty cargo space** to subsidize rerouting costs.

The system transforms chaos into actionable decisions by combining real-time routing data, Monte Carlo simulations, and LLM-powered strategic reasoning.

---

## Problem Statement

Supply chain disruptions cost the global economy billions annually. Traditional systems:
- React slowly to disruptions
- Ignore downstream cascade effects
- Miss opportunities to monetize idle capacity
- Don't learn from past events

Transit addresses these by providing an **antifragile** system that improves with each disruption.

---

## Key Features

### 🤖 Multi-Agent Swarm Architecture

A 4-stage pipeline where each agent specializes in one critical aspect:

| Agent | Module | Role |
|-------|--------|------|
| Scout | 01_scout_module | Detects and injects chaos events, parses signals via LLM |
| Analyst | 02_analyst_module | Quantifies financial risk, filters affected shipments |
| Strategist | 03_intel_module | Matches disruptions to historical patterns, adjusts bias |
| Simulator | 03_intel_module | Runs Monte Carlo simulations, calculates ESG metrics |

### 📊 N-Tier Domino Effect Simulation

Predicts cascading financial damage when delivery delays cause downstream factory halts:

```
Cargo Type → Downstream Facility → Halt Threshold → Financial Damage
─────────────────────────────────────────────────────────────────────
Electronics → Bangalore Assembly Line 1 → 24 hours → ₹15,000/hour
Medical     → Coimbatore Hospital       → 12 hours → ₹50,000/hour
Automotive  → Chennai Toyota Plant     → 36 hours → ₹250,000/hour
```

The system calculates:
- Which facilities will halt based on estimated ETA
- Hours of production loss
- Total cascading damage in ₹

### 🌱 ESG & Carbon Tracking

Environmental scoring per transport mode helps optimize for sustainability:

| Mode | CO2 (kg/tonne-km) | Green Score | Use Case |
|------|-------------------|-------------|----------|
| Rail | 0.041 | 100 🟢 | Long distance, bulk |
| Road Bypass | 0.210 | 50 🟡 | Medium routes |
| Air | 0.602 | 0 🔴 | Emergency only |

### 💰 Dynamic Load Pooling (Capacity Sharing Protocol)

When trucks are rerouted, they often have empty cargo space. Transit matches this space with local vendors along the new route:

**Algorithm:**
1. Extract route waypoints from approved reroute
2. Filter vendors by cities on the route
3. Greedy allocation of space to highest-bid vendors
4. Generate contracts with payout calculations

**Example Output:**
```
Matched Contracts:
├── Kochi Fresh Agro Exports (Kochi)
│   ├── Tonnes: 3.5t @ ₹1,500/t = ₹5,250
├── Thrissur Spice Traders (Thrissur)
│   ├── Tonnes: 2.0t @ ₹1,800/t = ₹3,600
└── Total Subsidy: ₹8,850
```

### 🗺️ Live Routing Intelligence

Real-time road data via OSRM (Open Source Routing Machine):
- 5-minute caching to reduce API calls
- Coordinates for 9 major Indian cities
- Strategic waypoint extraction from LLM suggestions
- Distance and duration calculations

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           TRANSIT SYSTEM FLOW                                │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │  Chaos Trigger  │  ← Random disruption events
    │ (01_scout_module)│    (floods, strikes, accidents)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   Scout Agent   │  ← LLM-powered signal parsing
    │ (01_scout_module)│    Output: location, severity, type
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Analyst Agent  │  ← Risk quantification
    │ (02_analyst_module)│  Output: affected shipments, ₹ at risk
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        INTEL MODULE (03)                              │
    │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
    │  │ Strategist      │    │ Simulator       │    │ Capacity Matcher│  │
    │  │ (Historical     │───▶│ (Monte Carlo +  │───▶│ (Dynamic Load   │  │
    │  │  Pattern Match) │    │  OSRM + Domino) │    │  Pooling)       │  │
    │  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
    └─────────────────────────────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │   Dashboard UI  │  ← Streamlit control room
    │ (01_scout_module)│    Real-time metrics & decisions
    └─────────────────┘
```

---

## Project Structure

```
transit/
├── 01_scout_module/                  # Chaos detection & injection
│   ├── chaos_trigger.py              # Generates random disruption events
│   ├── scout_agent.py                # LLM-powered signal parser
│   └── dashboard.py                  # Streamlit UI dashboard
│
├── 02_analyst_module/               # Financial risk assessment
│   ├── analyst_agent.py              # Risk calculation & shipment filtering
│   └── shipments.json                # Shipment database (15 shipments)
│
├── 03_intel_module/                 # Strategy & simulation
│   ├── strategist_agent.py           # Historical pattern matching
│   ├── simulator_agent.py            # Monte Carlo + OSRM + Domino Effect
│   ├── capacity_matcher.py          # Dynamic Load Pooling algorithm
│   ├── intel_coordinator.py         # Pipeline orchestrator
│   ├── past_events.json             # Experience buffer
│   └── capacity_market_ui.py        # Streamlit sidebar component
│
├── 04_manager_module/               # ROI & voice briefing (placeholder)
│
├── shared_exchange/                  # JSON data handoffs
│   ├── signal.json                  # Raw disruption event
│   ├── scout_output.json             # Scout-processed event
│   ├── analyst_output.json           # Risk assessment results
│   ├── intel_output.json             # Strategy + simulation results
│   ├── local_vendors.json           # Vendor database (10 vendors)
│   └── open_cargo_manifest.json     # Vendor contracts
│
├── progress/                         # Hackathon progress files
├── CHANGELOG.md                     # Development log
├── README.md                        # This file
└── .env                             # API keys (gitignored)
```

---

## Tech Stack

| Technology | Purpose | Usage |
|------------|---------|-------|
| **Python 3.11** | Core language | All agents |
| **Groq API** | LLM inference | Scout, Strategist, Oracle |
| **OSRM** | Live routing | Route optimization |
| **NumPy** | Statistical computing | Monte Carlo simulations |
| **Streamlit** | Web UI | Dashboard & visualizations |
| **JSON** | Data persistence | All inter-module communication |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Groq API Key (free at [groq.com](https://console.groq.com))
- Internet connection (for OSRM routing)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd transit

# Install dependencies
pip install groq numpy requests python-dotenv streamlit

# Configure API key
cp .env.example .env
# Edit .env and add:
# GROQ_API_KEY=your_key_here
```

### Running the System

#### Option 1: Dashboard (Recommended)
```bash
streamlit run 01_scout_module/dashboard.py
```
Opens the Streamlit control room with:
- Chaos injection button
- Real-time agent feed
- ROI metrics
- Capacity market sidebar

#### Option 2: Run Agents Individually

**Terminal 1 - Scout & Analyst:**
```bash
python 01_scout_module/chaos_trigger.py    # Generate disruption
python 01_scout_module/scout_agent.py       # Process signal
python 02_analyst_module/analyst_agent.py   # Assess risk
```

**Terminal 2 - Intel:**
```bash
python 03_intel_module/intel_coordinator.py # Run full pipeline
```

---

## Data Schemas

### Input: signal.json
```json
{
  "id": "EVT-1234",
  "event": "flash flood",
  "location": "Kochi",
  "timestamp": "2026-03-28T10:30:00Z",
  "source": "IMD_alert"
}
```

### Output: intel_output.json
```json
{
  "strategic_lesson": "Last time flood at Kochi...",
  "recommended_route": ["Mumbai", "Pune", "Bangalore"],
  "recommended_mode": "Air",
  "projected_savings": 75000.0,
  "capacity_subsidy_earned_inr": 8850.0,
  "total_roi_with_subsidy": 83850.0,
  "simulation_results": [
    {
      "mode": "Air",
      "mean_time": 0.5,
      "reliability_score": 0.85,
      "network_health": "STABLE 🟢",
      "total_cascading_damage_inr": 0
    }
  ]
}
```

### Capacity Market: open_cargo_manifest.json
```json
{
  "status": "success",
  "route_waypoints": ["Kochi", "Thrissur", "Bangalore"],
  "total_space_sold_tonnes": 8.0,
  "total_subsidy_earned_inr": 8850.0,
  "matched_contracts": [
    {"vendor_name": "Kochi Fresh Agro", "city": "Kochi", "tonnes_matched": 3.5, "payout_inr": 5250}
  ]
}
```

---

## Configuration

### Environment Variables (.env)
```
GROQ_API_KEY=your_groq_api_key_here
```

### Route Distances (km)
```python
ROUTE_DISTANCES_KM = {
    "Air": 450,
    "Rail": 620,
    "Road_bypass": 580,
    "Road": 550
}
```

### Emissions (kg CO2 per tonne-km)
```python
EMISSIONS_KG_PER_TONNE_KM = {
    "Air": 0.602,
    "Rail": 0.041,
    "Road_bypass": 0.210,
    "Road": 0.210
}
```

### Downstream Network (Domino Effect)
```python
DOWNSTREAM_NETWORK = {
    "Electronics_Components": [
        {"facility": "Bangalore Assembly Line 1", "halts_after_hours": 24, "damage_per_hour_inr": 15000}
    ],
    "Medical_Supplies": [
        {"facility": "Coimbatore Hospital", "halts_after_hours": 12, "damage_per_hour_inr": 50000}
    ]
}
```

---

## License

This project was built during NEXUS 2026 Hackathon by CLIQUE x ACM MITS.

---

## Team

**CLIQUE x ACM MITS**

---

**Build. Break. Innovate.**
