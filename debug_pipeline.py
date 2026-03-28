import os
import sys
import json
from pathlib import Path

# Paths
PY = r"C:\Users\lithi\AppData\Local\Programs\Python\Python311\python.exe"
ROOT = Path(r"x:\NEXUS\24_cachemeifyoucan_ACMNexus26")
SHARED = ROOT / "shared_exchange"

def run():
    print("--- 1. TRIGGER CHAOS ---")
    os.system(f'"{PY}" "{ROOT}/01_scout_module/chaos_trigger.py"')
    
    print("--- 2. RUN SCOUT agent ---")
    os.system(f'"{PY}" "{ROOT}/01_scout_module/scout_agent.py"')
    
    print("--- 3. RUN ANALYST agent ---")
    os.system(f'"{PY}" "{ROOT}/02_analyst_module/analyst_agent.py"')

    print("--- CHECKING SHARED FOLDER ---")
    for f in ["signal.json", "scout_output.json", "analyst_output.json", "intel_output.json"]:
        path = SHARED / f
        if path.exists():
            print(f"✅ {f} exists ({os.path.getsize(path)} bytes)")
        else:
            print(f"❌ {f} MISSING")

if __name__ == "__main__":
    run()
