import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from gtts import gTTS


# ============================================================
# Manager Agent (Final Step of Multi-Agent Pipeline)
# ------------------------------------------------------------
# Input:  ../shared_exchange/intel_output.json
# Output: ../shared_exchange/final_results.json
# Audio:  ./alert.mp3
# ============================================================

# Absolute path to this module directory (/04_manager_module).
MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))

# Required pipeline paths.
INTEL_INPUT_PATH = os.path.abspath(
    os.path.join(MANAGER_DIR, "..", "shared_exchange", "intel_output.json")
)
SCOUT_OUTPUT_PATH = os.path.abspath(
    os.path.join(MANAGER_DIR, "..", "shared_exchange", "scout_output.json")
)
ANALYST_OUTPUT_PATH = os.path.abspath(
    os.path.join(MANAGER_DIR, "..", "shared_exchange", "analyst_output.json")
)
FINAL_OUTPUT_PATH = os.path.abspath(
    os.path.join(MANAGER_DIR, "..", "shared_exchange", "final_results.json")
)
ALERT_AUDIO_PATH = os.path.join(MANAGER_DIR, "alert.mp3")
ALERT_AUDIO_EN_PATH = os.path.join(MANAGER_DIR, "alert_english.mp3")
ALERT_AUDIO_ML_PATH = os.path.join(MANAGER_DIR, "alert_malayalam.mp3")

# Polling cadence while waiting for upstream intel.
POLL_INTERVAL_SECONDS = 2
API_HOST = "0.0.0.0"
API_PORT = 8000

# Fallback mode metadata used when Intel provides alternative_routes as mode strings.
MODE_ROUTE_MAP = {
    "air": {
        "route_description": "Air Freight Corridor via nearest cargo airport",
        "cost_per_shipment": 6000,
    },
    "rail": {
        "route_description": "Rail Cargo Corridor via inland rail network",
        "cost_per_shipment": 3000,
    },
    "road_bypass": {
        "route_description": "Road Bypass using alternate highway corridor",
        "cost_per_shipment": 2000,
    },
}


def _path_exists(path):
    """Tiny helper for readable validation responses."""
    return os.path.exists(path)


def _missing_keys(payload, required_keys):
    """Return missing keys from payload for required schema check."""
    return [key for key in required_keys if key not in payload]


def validate_scout_output(payload):
    """Validate Scout output contract consumed by Analyst."""
    required = ["location", "severity"]
    compatible_alt = ["event", "location", "severity", "details"]

    missing = _missing_keys(payload, required)
    alt_missing = _missing_keys(payload, compatible_alt)

    is_valid = not missing
    notes = []
    if not is_valid and not alt_missing:
        notes.append("Scout payload is compatible via alternate event/details shape.")
        is_valid = True
    if missing and alt_missing:
        notes.append(f"Missing required keys for Analyst: {missing}")

    return {"ok": is_valid, "missing": missing if missing else [], "notes": notes}


def validate_analyst_output(payload):
    """Validate Analyst output contract consumed by Intel and Manager."""
    core_required = ["affected_shipments", "total_value_at_risk", "recommended_action"]
    intel_enrichment = ["event_type", "location", "severity"]

    core_missing = _missing_keys(payload, core_required)
    enrichment_missing = _missing_keys(payload, intel_enrichment)

    notes = []
    if not isinstance(payload.get("affected_shipments", []), list):
        notes.append("affected_shipments should be a list.")

    if enrichment_missing:
        notes.append(
            "Intel will fallback to Unknown values because analyst enrichment keys are absent: "
            f"{enrichment_missing}"
        )

    return {
        "ok": not core_missing,
        "missing": core_missing,
        "missing_for_intel_quality": enrichment_missing,
        "notes": notes,
    }


def validate_intel_output(payload):
    """Validate Intel output contract consumed by Manager."""
    direct_required = [
        "disruption_type",
        "location",
        "value_at_risk",
        "cost_of_new_route",
        "recommended_route",
    ]
    direct_missing = _missing_keys(payload, direct_required)

    has_alternatives = isinstance(payload.get("alternative_routes"), list)
    has_recommended_mode = bool(str(payload.get("recommended_mode", "")).strip())

    notes = []
    if direct_missing and not has_alternatives and not has_recommended_mode:
        notes.append(
            "Manager fallback needs alternative_routes list or recommended_mode when direct ROI keys are absent."
        )

    routes = payload.get("alternative_routes", [])
    if isinstance(routes, list) and routes:
        if isinstance(routes[0], str):
            notes.append(
                "alternative_routes is string-based; Manager compatibility mapping is active."
            )
        elif isinstance(routes[0], dict):
            route_required = ["route_description", "cost_per_shipment", "reliability_score"]
            route_missing = _missing_keys(routes[0], route_required)
            if route_missing:
                notes.append(f"First alternative route object missing keys: {route_missing}")

    return {
        "ok": (not direct_missing) or has_alternatives or has_recommended_mode,
        "missing_direct_fields": direct_missing,
        "notes": notes,
    }


def validate_final_output(payload):
    """Validate final handoff payload contract for UI consumers."""
    required = [
        "disruption_type",
        "location",
        "recommended_route",
        "roi",
        "summary_text",
        "recommended_action_text",
        "show_approve_button",
    ]
    missing = _missing_keys(payload, required)
    roi_missing = []

    roi = payload.get("roi", {})
    if isinstance(roi, dict):
        roi_missing = _missing_keys(roi, ["value_at_risk", "cost_of_new_route", "savings"])
    else:
        roi_missing = ["value_at_risk", "cost_of_new_route", "savings"]

    return {
        "ok": not missing and not roi_missing,
        "missing": missing,
        "missing_roi_fields": roi_missing,
        "notes": [],
    }


def run_shared_exchange_validation():
    """Validate all important shared_exchange contracts and return a structured report."""
    report = {
        "ok": True,
        "files": {},
        "summary": [],
    }

    # Scout output
    if _path_exists(SCOUT_OUTPUT_PATH):
        try:
            scout_payload = read_json_with_retry(SCOUT_OUTPUT_PATH)
            scout_status = validate_scout_output(scout_payload)
            report["files"]["scout_output"] = scout_status
        except Exception as error:
            report["files"]["scout_output"] = {"ok": False, "error": str(error)}
    else:
        report["files"]["scout_output"] = {"ok": False, "error": "File missing."}

    # Analyst output
    if _path_exists(ANALYST_OUTPUT_PATH):
        try:
            analyst_payload = read_json_with_retry(ANALYST_OUTPUT_PATH)
            analyst_status = validate_analyst_output(analyst_payload)
            report["files"]["analyst_output"] = analyst_status
        except Exception as error:
            report["files"]["analyst_output"] = {"ok": False, "error": str(error)}
    else:
        report["files"]["analyst_output"] = {"ok": False, "error": "File missing."}

    # Intel output
    if _path_exists(INTEL_INPUT_PATH):
        try:
            intel_payload = read_json_with_retry(INTEL_INPUT_PATH)
            intel_status = validate_intel_output(intel_payload)
            report["files"]["intel_output"] = intel_status
        except Exception as error:
            report["files"]["intel_output"] = {"ok": False, "error": str(error)}
    else:
        report["files"]["intel_output"] = {"ok": False, "error": "File missing."}

    # Final output
    if _path_exists(FINAL_OUTPUT_PATH):
        try:
            final_payload = read_json_with_retry(FINAL_OUTPUT_PATH)
            final_status = validate_final_output(final_payload)
            report["files"]["final_results"] = final_status
        except Exception as error:
            report["files"]["final_results"] = {"ok": False, "error": str(error)}
    else:
        report["files"]["final_results"] = {"ok": False, "error": "File missing."}

    # Aggregate summary.
    failed = []
    for file_key, status in report["files"].items():
        if not status.get("ok", False):
            failed.append(file_key)
    if failed:
        report["ok"] = False
        report["summary"].append(f"Validation failed for: {', '.join(failed)}")
    else:
        report["summary"].append("All shared_exchange contracts look compatible.")

    return report


def print_validation_report(report):
    """Console-friendly validator output for quick pipeline diagnostics."""
    print("[Validator] Shared exchange compatibility report")
    print(f"[Validator] Overall status: {'OK' if report.get('ok') else 'ISSUES FOUND'}")
    for file_key, status in report.get("files", {}).items():
        print(f"[Validator] - {file_key}: {'OK' if status.get('ok') else 'FAIL'}")
        if status.get("error"):
            print(f"[Validator]   error: {status['error']}")
        for note in status.get("notes", []):
            print(f"[Validator]   note: {note}")


def wait_for_intel_file(file_path):
    """
    STEP 1 (Polling)
    Keep checking for the intel file until it exists.
    """
    print(f"[Manager] Watching for {file_path}...")
    while not os.path.exists(file_path):
        time.sleep(POLL_INTERVAL_SECONDS)
    print("[Manager] Intel input detected.")


def read_json_with_retry(file_path, retries=5, delay_seconds=0.5):
    """
    Robust JSON reader.

    This protects against transient empty/partial writes from upstream modules
    that can cause JSON parsing failures.
    """
    last_error = None
    for _ in range(retries):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                raw = file.read().strip()
            if not raw:
                raise ValueError("Input file is empty.")
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as error:
            last_error = error
            time.sleep(delay_seconds)
    raise ValueError(f"Failed to parse intel JSON after retries: {last_error}")


def _infer_disruption_type(intel_data):
    """Infer disruption_type from available intel narrative fields."""
    if "disruption_type" in intel_data:
        return str(intel_data["disruption_type"])

    lesson = str(intel_data.get("strategic_lesson", "")).lower()
    if "flood" in lesson:
        return "Flood"
    if "strike" in lesson:
        return "Strike"
    if "accident" in lesson:
        return "Accident"
    return "Disruption"


def _infer_location(intel_data, analyst_data):
    """Infer location from intel first, then analyst shipment context."""
    if "location" in intel_data and str(intel_data.get("location", "")).strip():
        return str(intel_data["location"])

    if analyst_data:
        affected_shipments = analyst_data.get("affected_shipments", [])
        if affected_shipments:
            first = affected_shipments[0]
            route = str(first.get("route", ""))
            if "NH-66" in route:
                return "Kochi"
            if first.get("destination"):
                return str(first["destination"])

    lesson = str(intel_data.get("strategic_lesson", ""))
    if "NH-66" in lesson:
        return "NH-66"
    return "Unknown Location"


def _simulation_reliability_map(intel_data):
    """Build a map of mode -> reliability score from simulation details."""
    reliability_by_mode = {}
    simulation_details = intel_data.get("simulation_details", [])
    if not isinstance(simulation_details, list):
        return reliability_by_mode

    for item in simulation_details:
        if not isinstance(item, dict):
            continue
        mode_name = str(item.get("mode", "")).strip().lower()
        if not mode_name:
            continue

        # Prefer reliability_score; fallback to probability-based score.
        reliability = item.get("reliability_score")
        if reliability is None:
            reliability = item.get("p_arrival_within_target", 0)
        try:
            reliability_by_mode[mode_name] = float(reliability)
        except (TypeError, ValueError):
            reliability_by_mode[mode_name] = 0.0

    return reliability_by_mode


def _build_route_candidates_from_modes(intel_data):
    """Convert mode strings from Intel output into route-like candidate objects."""
    routes = intel_data.get("alternative_routes", [])
    if not isinstance(routes, list):
        return []

    reliability_by_mode = _simulation_reliability_map(intel_data)
    recommended_mode = str(intel_data.get("recommended_mode", "")).strip().lower()

    candidates = []
    for raw_mode in routes:
        mode_name = str(raw_mode).strip().lower()
        if not mode_name:
            continue

        mapped = MODE_ROUTE_MAP.get(mode_name, {
            "route_description": f"{mode_name.title()} contingency route",
            "cost_per_shipment": 2500,
        })

        # Bias recommended mode if no simulation reliability exists.
        reliability_score = reliability_by_mode.get(mode_name)
        if reliability_score is None:
            reliability_score = 1.0 if mode_name == recommended_mode else 0.5

        candidates.append({
            "mode": mode_name,
            "route_description": mapped["route_description"],
            "cost_per_shipment": mapped["cost_per_shipment"],
            "reliability_score": reliability_score,
        })

    # If Intel provides only recommended_mode but no alternatives, synthesize one candidate.
    if not candidates and recommended_mode:
        mapped = MODE_ROUTE_MAP.get(recommended_mode, {
            "route_description": f"{recommended_mode.title()} contingency route",
            "cost_per_shipment": 2500,
        })
        candidates.append({
            "mode": recommended_mode,
            "route_description": mapped["route_description"],
            "cost_per_shipment": mapped["cost_per_shipment"],
            "reliability_score": 1.0,
        })

    return candidates


def extract_required_data(intel_data, analyst_data=None):
    """
    STEP 2 (Data Extraction)

    Primary expected keys:
    - disruption_type
    - location
    - value_at_risk
    - cost_of_new_route
    - recommended_route

    Fallback support is included for the alternative intel format that contains
    strategic_lesson + alternative_routes.
    """
    required_keys = {
        "disruption_type",
        "location",
        "value_at_risk",
        "cost_of_new_route",
        "recommended_route",
    }

    # Preferred format: direct keys are present.
    if required_keys.issubset(set(intel_data.keys())):
        return {
            "disruption_type": str(intel_data["disruption_type"]),
            "location": str(intel_data["location"]),
            "value_at_risk": float(intel_data["value_at_risk"]),
            "cost_of_new_route": float(intel_data["cost_of_new_route"]),
            "recommended_route": str(intel_data["recommended_route"]),
            "input_shape": "direct",
        }

    # Fallback format: infer values from alternative routes intel payload.
    routes = intel_data.get("alternative_routes", [])
    if not routes and not intel_data.get("recommended_mode"):
        missing = sorted(required_keys - set(intel_data.keys()))
        raise KeyError(
            "Input JSON is missing required keys and has no alternative_routes/recommended_mode fallback. "
            f"Missing keys: {missing}"
        )

    structured_routes = []
    if isinstance(routes, list) and routes and isinstance(routes[0], dict):
        structured_routes = routes
    else:
        structured_routes = _build_route_candidates_from_modes(intel_data)

    if not structured_routes:
        raise KeyError("No usable route candidates were found in intel output.")

    best_route = max(
        structured_routes, key=lambda route: float(route.get("reliability_score", 0))
    )

    disruption_type = _infer_disruption_type(intel_data)
    location = _infer_location(intel_data, analyst_data)

    value_at_risk = intel_data.get("value_at_risk")
    if value_at_risk is None and analyst_data:
        value_at_risk = analyst_data.get("total_value_at_risk")
    if value_at_risk is None:
        value_at_risk = 50000

    return {
        "disruption_type": disruption_type,
        "location": location,
        "value_at_risk": float(value_at_risk),
        "cost_of_new_route": float(best_route.get("cost_per_shipment", 0)),
        "recommended_route": str(best_route.get("route_description", "Alternative Route")),
        "input_shape": "alternative_routes",
    }


def calculate_savings(value_at_risk, cost_of_new_route):
    """
    STEP 3 (ROI Engine)

    Exact formula required by project specification:
    savings = (value_at_risk * 0.8) - cost_of_new_route
    """
    return (value_at_risk * 0.8) - cost_of_new_route


def generate_text(disruption_type, location, recommended_route, savings):
    """
    STEP 4 (Content Generation)

    - summary_text: exactly 2 sentences
    - action_text: exactly 1 sentence with route + ROI savings
    """
    summary_text = (
        f"A {disruption_type} disruption has been identified at {location}. "
        f"This event can impact delivery flow and needs immediate response."
    )

    action_text = (
        f"Recommended action: switch to {recommended_route} for estimated ROI savings of {savings:.2f}."
    )

    return summary_text, action_text


def synthesize_voice(summary_text, action_text, output_path):
    """
    STEP 5 (Voice Synthesis)
    Convert generated text to speech using gTTS and save as alert.mp3.
    """
    message = f"{summary_text} {action_text}"
    tts = gTTS(text=message, lang="en")
    tts.save(output_path)
    print(f"[Manager] Audio alert saved at {output_path}")


def build_english_message(final_payload):
    """Build English narration from stored final payload."""
    summary = final_payload.get("summary_text", "")
    action = final_payload.get("recommended_action_text", "")
    return f"{summary} {action}".strip()


def build_malayalam_message(final_payload):
    """Build Malayalam narration from stored final payload using deterministic template."""
    disruption_type = final_payload.get("disruption_type", "Disruption")
    location = final_payload.get("location", "Unknown Location")
    route = final_payload.get("recommended_route", "Alternative Route")
    savings = final_payload.get("roi", {}).get("savings", 0)

    return (
        f"{location} പ്രദേശത്ത് {disruption_type} ബാധ കണ്ടെത്തിയിട്ടുണ്ട്. "
        f"വിതരണ ശൃംഖല നിലനിര്‍ത്താന്‍ അടിയന്തര നടപടി ആവശ്യമാണ്. "
        f"{route} വഴി മാറുകയാണെങ്കില്‍ ഏകദേശ ലാഭം {savings:.2f} ലഭിക്കും."
    )


def synthesize_language_audio(language_path):
    """
    Generate language-specific audio based on API path.

    Supported paths:
    - /english
    - /malayalam
    - /malayalm (alias)
    """
    if not os.path.exists(FINAL_OUTPUT_PATH):
        raise FileNotFoundError(
            "final_results.json not found. Run pipeline first to produce manager output."
        )

    final_payload = read_json_with_retry(FINAL_OUTPUT_PATH)

    if language_path == "/english":
        text = build_english_message(final_payload)
        tts = gTTS(text=text, lang="en")
        tts.save(ALERT_AUDIO_EN_PATH)
        return {
            "language": "english",
            "audio_file": ALERT_AUDIO_EN_PATH,
            "text": text,
        }

    if language_path in {"/malayalam", "/malayalm"}:
        text = build_malayalam_message(final_payload)
        tts = gTTS(text=text, lang="ml")
        tts.save(ALERT_AUDIO_ML_PATH)
        return {
            "language": "malayalam",
            "audio_file": ALERT_AUDIO_ML_PATH,
            "text": text,
        }

    raise ValueError("Unsupported language path. Use /english or /malayalam.")


class ManagerApiHandler(BaseHTTPRequestHandler):
    """Simple built-in API server for language-specific audio generation."""

    def _send_json(self, status_code, payload):
        response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def _send_audio(self, file_path):
        if not os.path.exists(file_path):
            self._send_json(404, {"ok": False, "error": "Audio file not found."})
            return

        with open(file_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(audio_bytes)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(audio_bytes)

    def do_GET(self):
        if self.path == "/validate":
            report = run_shared_exchange_validation()
            self._send_json(200, report)
            return

        if self.path in {"/english", "/malayalam", "/malayalm"}:
            try:
                result = synthesize_language_audio(self.path)
                language = result["language"]
                if language == "english":
                    audio_endpoint = "/audio/english"
                else:
                    audio_endpoint = "/audio/malayalam"

                host_header = self.headers.get("Host", f"127.0.0.1:{API_PORT}")
                audio_url = f"http://{host_header}{audio_endpoint}"

                self._send_json(
                    200,
                    {
                        "ok": True,
                        **result,
                        "audio_endpoint": audio_endpoint,
                        "audio_url": audio_url,
                    },
                )
                return
            except Exception as error:
                self._send_json(500, {"ok": False, "error": str(error)})
            return

        if self.path in {"/audio/english", "/audio/malayalam", "/audio/malayalm"}:
            try:
                if self.path == "/audio/english":
                    if not os.path.exists(ALERT_AUDIO_EN_PATH):
                        synthesize_language_audio("/english")
                    self._send_audio(ALERT_AUDIO_EN_PATH)
                    return

                if not os.path.exists(ALERT_AUDIO_ML_PATH):
                    synthesize_language_audio("/malayalam")
                self._send_audio(ALERT_AUDIO_ML_PATH)
                return
            except Exception as error:
                self._send_json(500, {"ok": False, "error": str(error)})
            return

        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "manager-agent-api"})
            return

        if self.path == "/":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "manager-agent-api",
                    "routes": {
                        "generate_english": "/english",
                        "generate_malayalam": "/malayalam",
                        "play_english_audio": "/audio/english",
                        "play_malayalam_audio": "/audio/malayalam",
                        "validate_contracts": "/validate",
                        "health": "/health",
                    },
                },
            )
            return

        self._send_json(
            404,
            {
                "ok": False,
                "error": "Not found",
                "supported_paths": [
                    "/",
                    "/english",
                    "/malayalam",
                    "/malayalm",
                    "/audio/english",
                    "/audio/malayalam",
                    "/audio/malayalm",
                    "/validate",
                    "/health",
                ],
            },
        )


def start_api_server():
    """Start HTTP API for language-specific audio requests."""
    server = HTTPServer((API_HOST, API_PORT), ManagerApiHandler)
    print(f"[Manager API] Listening on http://{API_HOST}:{API_PORT}")
    print("[Manager API] Use /english or /malayalam to generate language audio.")
    server.serve_forever()


def write_final_results(output_path, extracted, savings, summary_text, action_text):
    """
    STEP 6 (Final Handoff)
    Save final payload to ../shared_exchange/final_results.json.
    """
    payload = {
        "disruption_type": extracted["disruption_type"],
        "location": extracted["location"],
        "recommended_route": extracted["recommended_route"],
        "roi": {
            "value_at_risk": extracted["value_at_risk"],
            "cost_of_new_route": extracted["cost_of_new_route"],
            "savings": savings,
        },
        "summary_text": summary_text,
        "recommended_action_text": action_text,
        "show_approve_button": True,
        "input_shape": extracted["input_shape"],
    }

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"[Manager] Final results written to {output_path}")


def cleanup_intel_input(file_path):
    """
    STEP 7 (Cleanup)
    Delete consumed intel file to reset the pipeline.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[Manager] Cleaned up input file: {file_path}")


def run_manager_pipeline_once():
    """Run one complete manager cycle from polling to cleanup."""
    wait_for_intel_file(INTEL_INPUT_PATH)

    intel_data = read_json_with_retry(INTEL_INPUT_PATH)
    analyst_data = None
    if os.path.exists(ANALYST_OUTPUT_PATH):
        try:
            analyst_data = read_json_with_retry(ANALYST_OUTPUT_PATH)
        except ValueError:
            # Continue with intel-only mode if analyst output is temporarily unreadable.
            analyst_data = None

    extracted = extract_required_data(intel_data, analyst_data)

    savings = calculate_savings(
        extracted["value_at_risk"], extracted["cost_of_new_route"]
    )

    summary_text, action_text = generate_text(
        extracted["disruption_type"],
        extracted["location"],
        extracted["recommended_route"],
        savings,
    )

    synthesize_voice(summary_text, action_text, ALERT_AUDIO_PATH)
    write_final_results(FINAL_OUTPUT_PATH, extracted, savings, summary_text, action_text)
    cleanup_intel_input(INTEL_INPUT_PATH)

    print("[Manager] Pipeline complete.")


def create_mock_intel_input(file_path):
    """
    Test helper for standalone execution.

    Creates sample upstream output so this module can be tested immediately.
    """
    mock_payload = {
        "disruption_type": "Flood",
        "location": "MG Road",
        "value_at_risk": 50000,
        "cost_of_new_route": 2000,
        "recommended_route": "Bypass Route B via Ring Road",
    }

    parent = os.path.dirname(file_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(mock_payload, file, indent=2)

    print(f"[Manager] Mock intel input created at {file_path}")


if __name__ == "__main__":
    try:
        validation = run_shared_exchange_validation()
        print_validation_report(validation)

        # If new intel exists, process it first.
        if os.path.exists(INTEL_INPUT_PATH):
            run_manager_pipeline_once()

        # If no manager output exists yet, create mock intel and run once.
        if not os.path.exists(FINAL_OUTPUT_PATH):
            create_mock_intel_input(INTEL_INPUT_PATH)
            run_manager_pipeline_once()

        # Start API service for language-specific audio generation.
        start_api_server()
    except KeyboardInterrupt:
        print("\n[Manager API] Shutting down.")
    except Exception as error:
        print(f"[Manager] Error during execution: {error}")
