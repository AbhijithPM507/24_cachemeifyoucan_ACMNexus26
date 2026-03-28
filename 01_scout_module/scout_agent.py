import os
import json
import urllib.request
import urllib.error
from pathlib import Path

def load_dotenv():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")

load_dotenv()

def get_llm_response(prompt: str) -> str:
    # Attempt to use Groq API
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("Warning: API Key not set. Using mock LLM response for testing.")
        return '''{
  "description": "A flash flood has severely impacted NH-66 near Kochi, disrupting vehicle movement. Delays are expected across key logistics routes.",
  "location": "Kochi",
  "severity": "HIGH",
  "disruption_type": "weather",
  "agent_thoughts": "Flood detected on a critical highway corridor. High disruption risk due to route dependency."
}'''

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "NexusPath-Scout/1.0"
    }
    
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a perception scout agent for a supply chain system. Convert raw chaos into structured data. Output ONLY JSON exactly as requested in the prompt with no other text."},
            {"role": "user", "content": prompt}
        ]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_msg = f"LLM API HTTP Error: {e.code} - {e.reason}"
        try:
            error_msg += f" Body: {e.read().decode('utf-8')}"
        except:
            pass
        raise RuntimeError(error_msg)
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API Network Error: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected LLM Error: {str(e)}")

def _get_fallback_output(signal: dict, reason: str) -> dict:
    return {
        "description": "Fallback processed signal due to extraction failure.",
        "location": signal.get("location", "Unknown"),
        "severity": "CRITICAL",
        "disruption_type": "other",
        "agent_thoughts": f"Error occurred during LLM processing: {reason}",
        "raw_signal": signal
    }

def run_scout_agent(signal: dict) -> dict:
    prompt = f"""
Raw signal:
{json.dumps(signal, indent=2)}

Analyze this signal and output ONLY a JSON object with these EXACT keys (no markdown formatting):
- "description": Short human-friendly description (max 2 sentences)
- "location": Main affected location extracted from the signal
- "severity": "LOW", "MEDIUM", "HIGH", or "CRITICAL"
- "disruption_type": "weather", "strike", "accident", "infrastructure", or "other"
- "agent_thoughts": Internal reasoning

Output JSON:
"""
    raw_output = ""
    try:
        raw_output = get_llm_response(prompt).strip()
    except Exception as e:
        print(f"LLM Call Failed: {e}")
        return _get_fallback_output(signal, f"LLM Call failed: {e}")
        
    # Clean markdown if generated
    cleaned = raw_output
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
        
    cleaned = cleaned.strip()
    
    try:
        parsed = json.loads(cleaned)
        
        # Enforce exact keys
        final_output = {
            "description": str(parsed.get("description", "Unknown Description")),
            "location": str(parsed.get("location", "Unknown Location")),
            "severity": str(parsed.get("severity", "MEDIUM")).upper(),
            "disruption_type": str(parsed.get("disruption_type", "other")).lower(),
            "agent_thoughts": str(parsed.get("agent_thoughts", "No thoughts.")),
            "raw_signal": signal
        }
        return final_output
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response. Error: {e}")
        print(f"RAW RESPONSE:\n{raw_output}")
        return _get_fallback_output(signal, "Failed to parse JSON string from LLM.")

def process_signal():
    project_root = Path(__file__).parent.parent
    shared_exchange = project_root / "shared_exchange"
    signal_file = shared_exchange / "signal.json"
    output_file = shared_exchange / "scout_output.json"
    
    if not signal_file.exists():
        print(f"Fail gracefully: Missing signal file at {signal_file}.")
        return
        
    try:
        with open(signal_file, "r", encoding="utf-8") as f:
            signal_data = json.load(f)
    except Exception as e:
        print(f"Fail gracefully: Could not read signal.json: {e}")
        return
        
    scout_output = run_scout_agent(signal_data)
    
    # Ensure all required keys exist before writing output
    required_keys = {"description", "location", "severity", "disruption_type", "agent_thoughts", "raw_signal"}
    if not required_keys.issubset(scout_output.keys()):
        print("Scout output schema mismatch. Halting to prevent pipeline breakage.")
        return
        
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scout_output, f, indent=2)
        print(f"Scout complete: {scout_output.get('description')}")
    except Exception as e:
        print(f"Failed to write scout_output.json: {e}")

if __name__ == "__main__":
    process_signal()
