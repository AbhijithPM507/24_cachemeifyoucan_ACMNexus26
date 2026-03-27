import json
import os
from groq import Groq
from dotenv import load_dotenv

# Load .env from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

agent_thoughts = []

def load_past_events():
    """Load historical events from the experience buffer."""
    try:
        # Use absolute path or relative to the module to avoid FileNotFoundError
        path = os.path.join(os.path.dirname(__file__), "past_events.json")
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading memory: {e}")
        return []

def run_strategist(analyst_output):
    """
    Analyzes current disruption against historical memory using Llama 3 on Groq.
    """
    past_events = load_past_events()
    
    system_prompt = f"""
    You are the 'Strategist', the long-term memory of the NexusPath supply chain swarm.
    Your role is to compare current disruptions to our historical 'Experience Buffer' and 
    determine if we should act more aggressively than standard models suggest.

    HISTORICAL CONTEXT:
    {json.dumps(past_events, indent=2)}

    TASK:
    1. Match the current event to the most relevant historical event.
    2. Provide a 'strategic_lesson' starting with "Last time...".
    3. Determine a 'bias_factor' (0.8 to 1.5). 
       - Increase (>1.0) if history shows this disruption is worse than it looks.
       - Decrease (<1.0) if history shows this location recovers faster than average.
    """

    user_prompt = f"CURRENT DISRUPTION (JSON): {json.dumps(analyst_output)}\n\nPlease respond in JSON format."

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse result
        result = json.loads(chat_completion.choices[0].message.content)
        
        # Ensure 'agent_thoughts' is included for the UI sidebar
        if "agent_thoughts" not in result:
            result["agent_thoughts"] = f"Memory match found: {result.get('matched_event_id')}. Adjusting bias to {result.get('bias_factor')}."
        
        from datetime import datetime
        agent_thoughts.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Strategic Insight: Matched event_id={result.get('matched_event_id')}, bias_factor={result.get('bias_factor')}")
            
        return result

    except Exception as e:
        print(f"Strategist Agent Error: {e}")
        # Local Fallback
        return {
            "matched_event_id": "FALLBACK",
            "strategic_lesson": "No direct memory match. Proceeding with standard probability models.",
            "bias_factor": 1.0,
            "agent_thoughts": "Strategist is operating on real-time data only; historical buffer unavailable."
        }