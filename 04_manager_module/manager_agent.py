import json
import os
import time
import random
import datetime
import requests
from gtts import gTTS
from groq import Groq
from dotenv import load_dotenv

# Load secret keys from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WAREHOUSE_CHAT_ID = os.getenv("WAREHOUSE_CHAT_ID")

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.abspath(os.path.join(MANAGER_DIR, "..", "shared_exchange"))

# File Paths
INTEL_INPUT_PATH = os.path.join(SHARED_DIR, "intel_output.json")
ANALYST_INPUT_PATH = os.path.join(SHARED_DIR, "analyst_output.json")
FINAL_OUTPUT_PATH = os.path.join(SHARED_DIR, "final_results.json")
AGV_OUTPUT_PATH = os.path.join(SHARED_DIR, "agv_payload.json")
SCOUT_OUTPUT_PATH = os.path.join(SHARED_DIR, "scout_output.json")
WAREHOUSE_SCHEDULE_PATH = os.path.join(SHARED_DIR, "warehouse_schedule.json")
MP3_ENGLISH = os.path.join(MANAGER_DIR, "alert_english.mp3")
MP3_MALAYALAM = os.path.join(MANAGER_DIR, "alert_malayalam.mp3")

POLL_INTERVAL_SECONDS = 2

# ==========================================
# FEATURE 1: LIVE TELEGRAM DISPATCHER
# ==========================================
def send_telegram_alert(disruption_type, location, route_desc, malayalam_audio_path):
    # Always load from project-root .env so it works regardless of execution cwd.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=dotenv_path)

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ [Telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env. Skipping alert safely.")
        return

    # Message 1: Standard dispatch text with confirm button only.
    dispatch_text = (
        "🚨 *URGENT DRIVER DISPATCH* 🚨\n\n"
        f"{disruption_type}\n"
        f"*Location:* {location}\n"
        f"🛣️ *Assigned Reroute:* {route_desc}\n\n"
        "Please confirm reroute acknowledgement immediately."
    )

    send_message_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm Reroute", "callback_data": "confirm"},
                {"text": "👷 Notify Warehouse", "callback_data": "notify_warehouse"},
            ]
        ]
    }

    # Message 3: Dedicated emergency reporting message with accident trigger button.
    emergency_reporting_text = (
        "⚠️ EMERGENCY REPORTING ⚠️\n"
        "If you are in an accident or the road is completely blocked, click the "
        "button below to instantly warn all other trucks in the network."
    )
    emergency_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🚨 REPORT ACCIDENT (Trigger Swarm)",
                    "callback_data": "accident",
                }
            ]
        ]
    }

    try:
        # Message 1: Text + inline buttons.
        resp1 = requests.post(
            send_message_url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": dispatch_text,
                "parse_mode": "Markdown",
                "reply_markup": inline_keyboard,
            },
            timeout=15,
        )

        # Message 2: Audio file upload immediately after text alert.
        url_audio = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendAudio"
        try:
            if not malayalam_audio_path:
                resp2 = None
            else:
                with open(malayalam_audio_path, "rb") as audio_file:
                    resp2 = requests.post(
                        url_audio,
                        data={"chat_id": TELEGRAM_CHAT_ID},
                        files={"audio": audio_file},
                        timeout=30,
                    )
        except FileNotFoundError:
            resp2 = None
            print(f"⚠️ [Telegram] Audio file not found yet: {malayalam_audio_path}")
        except OSError as error:
            resp2 = None
            print(f"⚠️ [Telegram] Could not open audio file: {error}")
        except TypeError:
            resp2 = None
            print(f"⚠️ [Telegram] Invalid audio path: {malayalam_audio_path}")

        # Message 3: Dedicated accident trigger message.
        resp3 = requests.post(
            send_message_url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": emergency_reporting_text,
                "parse_mode": "Markdown",
                "reply_markup": emergency_keyboard,
            },
            timeout=15,
        )

        if resp1.status_code == 200 and resp3.status_code == 200 and (
            resp2 is None or resp2.status_code == 200
        ):
            print("📱 [Telegram] Driver dispatch sequence sent successfully.")
        else:
            print(
                "❌ [Telegram] Dispatch issue: "
                f"msg1={resp1.status_code}, "
                f"audio={(resp2.status_code if resp2 is not None else 'skipped')}, "
                f"msg3={resp3.status_code}"
            )
    except requests.RequestException as error:
        print(f"⚠️ [Telegram] Network/API error: {error}")


def poll_telegram_updates():
    """
    Poll Telegram updates and trigger swarm rerouting flow on driver SOS callbacks.

     Trigger callback:
     - accident

     Flow:
     1) On accident callback -> ask driver for live GPS using request_location button.
     2) On incoming location message -> broadcast swarm alert with maps link,
         remove reply keyboard, and write scout_output.json with geo context.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=dotenv_path)

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not telegram_token or not telegram_chat_id:
        print("⚠️ [Telegram Poller] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env. Poller disabled.")
        return

    get_updates_url = f"https://api.telegram.org/bot{telegram_token}/getUpdates"
    answer_callback_url = f"https://api.telegram.org/bot{telegram_token}/answerCallbackQuery"
    send_message_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"

    next_offset = 0
    awaiting_location_users = set()
    stop_poller = False
    print("📡 [Telegram Poller] Listening for driver callbacks...")

    while True:
        if stop_poller:
            break
        try:
            response = requests.get(
                get_updates_url,
                params={"timeout": 30, "offset": next_offset},
                timeout=35,
            )
            payload = response.json()
            updates = payload.get("result", [])

            for update in updates:
                update_id = update.get("update_id")
                if update_id is not None:
                    next_offset = update_id + 1

                callback = update.get("callback_query", {})
                callback_data = str(callback.get("data", "")).lower()
                callback_id = callback.get("id")

                if callback_data == "notify_warehouse":
                    callback_message = callback.get("message", {})
                    callback_chat_id = callback_message.get("chat", {}).get("id", telegram_chat_id)

                    # Stop Telegram button spinner immediately.
                    if callback_id:
                        requests.post(
                            answer_callback_url,
                            json={
                                "callback_query_id": callback_id,
                                "text": "Notifying warehouse now...",
                            },
                            timeout=15,
                        )

                    warehouse_chat_id = os.getenv("WAREHOUSE_CHAT_ID")
                    if not warehouse_chat_id:
                        print("⚠️ [Telegram Poller] WAREHOUSE_CHAT_ID missing. Cannot notify warehouse.")
                        stop_poller = True
                        break

                    # Demo delay math.
                    delay_hours = 4
                    labor_saved_inr = delay_hours * 10 * 150
                    new_arrival_time = (
                        datetime.datetime.now() + datetime.timedelta(hours=delay_hours)
                    ).strftime("%d %b %Y, %I:%M %p")

                    # Notify warehouse manager chat.
                    warehouse_message = (
                        "🏭 WAREHOUSE DOCK ALERT 🏭\n\n"
                        f"⚠️ Driver Reported Delay: The inbound truck has been delayed by {delay_hours} hours.\n"
                        f"🕒 New ETA: {new_arrival_time}\n\n"
                        "✅ Action Required: Reallocate Dock crew.\n"
                        f"💰 Idle Labor Cost Prevented: ₹{labor_saved_inr:,}"
                    )
                    requests.post(
                        send_message_url,
                        json={
                            "chat_id": warehouse_chat_id,
                            "text": warehouse_message,
                            "parse_mode": "Markdown",
                        },
                        timeout=15,
                    )

                    # Confirm back to driver.
                    requests.post(
                        send_message_url,
                        json={
                            "chat_id": callback_chat_id,
                            "text": "✅ Warehouse successfully notified. They are reallocating the dock crew.",
                        },
                        timeout=15,
                    )
                    continue

                # Step 1: Accident callback -> acknowledge + request live location.
                if callback_data == "accident":
                    callback_message = callback.get("message", {})
                    callback_chat_id = callback_message.get("chat", {}).get("id", telegram_chat_id)
                    callback_user_id = callback.get("from", {}).get("id")

                    if callback_id:
                        requests.post(
                            answer_callback_url,
                            json={
                                "callback_query_id": callback_id,
                                "text": "Emergency acknowledged. Share GPS now.",
                            },
                            timeout=15,
                        )

                    gps_request_text = (
                        "⚠️ Emergency acknowledged. Please tap the button below to share your exact GPS "
                        "location so we can warn the fleet."
                    )
                    location_keyboard = {
                        "keyboard": [
                            [
                                {
                                    "text": "📍 Send My GPS Location",
                                    "request_location": True,
                                }
                            ]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True,
                    }
                    requests.post(
                        send_message_url,
                        json={
                            "chat_id": callback_chat_id,
                            "text": gps_request_text,
                            "reply_markup": location_keyboard,
                        },
                        timeout=15,
                    )

                    if callback_user_id is not None:
                        awaiting_location_users.add(callback_user_id)
                    continue

                # Step 2: Listen for incoming Telegram messages containing location.
                message = update.get("message", {})
                if "location" in message:
                    sender_user_id = message.get("from", {}).get("id")
                    sender_chat_id = message.get("chat", {}).get("id", telegram_chat_id)

                    # Process only if we previously requested location from this user.
                    if sender_user_id is not None and sender_user_id not in awaiting_location_users:
                        continue

                    # Step 3: Extract latitude/longitude and build Google Maps URL.
                    lat = message["location"]["latitude"]
                    lon = message["location"]["longitude"]
                    maps_url = f"https://www.google.com/maps?q={lat},{lon}"

                    # Step 4A: Broadcast to fleet chat (if configured).
                    FLEET_CHAT_ID = os.getenv("FLEET_CHAT_ID")
                    swarm_alert = (
                        "🚨 SWARM ALERT 🚨\n\n"
                        "A truck ahead is stuck and has triggered an SOS.\n"
                        f"📍 Live Location: {maps_url}\n\n"
                        "⚠️ ALL TRUCKS HALT & REROUTE."
                    )
                    if FLEET_CHAT_ID:
                        requests.post(
                            send_message_url,
                            json={
                                "chat_id": FLEET_CHAT_ID,
                                "text": swarm_alert,
                            },
                            timeout=15,
                        )
                    else:
                        print("⚠️ [Telegram Poller] FLEET_CHAT_ID missing. Fleet broadcast skipped.")

                    # Step 4B: Confirm to driver and remove GPS keyboard.
                    requests.post(
                        send_message_url,
                        json={
                            "chat_id": sender_chat_id,
                            "text": "✅ Swarm Alert and live location successfully broadcast to the fleet.",
                            "reply_markup": {"remove_keyboard": True},
                        },
                        timeout=15,
                    )

                    # Step 5: Trigger pipeline and include geo context for Analyst.
                    scout_trigger_payload = {
                        "disruption_type": "Driver SOS (Accident)",
                        "location": "NH-66 Highway",
                        "severity": "CRITICAL",
                        "latitude": lat,
                        "longitude": lon,
                        "maps_url": maps_url,
                    }
                    os.makedirs(SHARED_DIR, exist_ok=True)
                    with open(SCOUT_OUTPUT_PATH, "w", encoding="utf-8") as scout_file:
                        json.dump(scout_trigger_payload, scout_file, indent=2)

                    if sender_user_id is not None:
                        awaiting_location_users.discard(sender_user_id)

                    print("🚨 [Swarm Trigger] Driver GPS captured. scout_output.json written with geo location.")

        except requests.RequestException as error:
            print(f"⚠️ [Telegram Poller] Network error (retrying in 5s): {type(error).__name__}")
            time.sleep(5)
        except Exception as error:
            print(f"⚠️ [Telegram Poller] Error (retrying in 5s): {type(error).__name__}")
            time.sleep(5)

# ==========================================
# FEATURE 2: AGV WAREHOUSE HANDSHAKE
# ==========================================
def generate_agv_payload(route_desc):
    arrival = datetime.datetime.now() + datetime.timedelta(days=1)
    payload = {
        "agv_command": "PRE_ALLOCATE_FORKLIFT",
        "shipment_id": f"SHP-{random.randint(1000, 9999)}",
        "cargo_weight_kg": random.randint(1500, 4000),
        "expected_arrival_readable": arrival.strftime("%d %b %Y, %I:%M %p"),
        "bay_number": random.randint(1, 20),
        "priority_override": True,
        "instructions": f"Emergency reroute via {route_desc}. Zero idle time required."
    }
    with open(AGV_OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"🤖 [AGV Robot] Handshake complete! Bay {payload['bay_number']} reserved.")
    return payload


def update_warehouse_wms(shipment_id: str, delay_hours: int, new_eta_days: int):
    """Notify warehouse operations about inbound delay and dock/labor adjustments."""
    idle_labor_saved_inr = delay_hours * 10 * 150
    new_arrival_dt = datetime.datetime.now() + datetime.timedelta(
        days=new_eta_days,
        hours=delay_hours,
    )
    new_arrival_time = new_arrival_dt.strftime("%d %b %Y, %I:%M %p")

    warehouse_payload = {
        "shipment_id": shipment_id,
        "agv_status": "Standby",
        "dock_status": "Reallocated",
        "labor_saved_inr": idle_labor_saved_inr,
        "new_arrival_time": new_arrival_time,
    }

    os.makedirs(SHARED_DIR, exist_ok=True)
    with open(WAREHOUSE_SCHEDULE_PATH, "w", encoding="utf-8") as warehouse_file:
        json.dump(warehouse_payload, warehouse_file, indent=2)
    print("🏭 [Warehouse WMS] warehouse_schedule.json updated for dashboard.")

# ==========================================
# FEATURE 3: BLEED RATE CALCULATOR
# ==========================================
def calculate_bleed_rate(value_at_risk, delay_hours=12.0):
    total_loss = value_at_risk * 0.8
    per_minute = round(total_loss / (delay_hours * 60), 2)
    return {
        "bleed_rate_per_minute_usd": per_minute,
        "bleed_rate_inr_per_minute": round(per_minute * 83)
    }

# ==========================================
# CORE PIPELINE LOGIC
# ==========================================
def wait_for_files():
    print(f"👀 [Manager] Watching for {INTEL_INPUT_PATH}...")
    while not (os.path.exists(INTEL_INPUT_PATH) and os.path.exists(ANALYST_INPUT_PATH)):
        time.sleep(POLL_INTERVAL_SECONDS)
    print("⚡ [Manager] Upstream inputs detected.")

def read_json_with_retry(file_path):
    for _ in range(5):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content: return json.loads(content)
        except Exception:
            time.sleep(0.5)
    raise ValueError(f"Failed to read {file_path}")

def run_pipeline_once():
    wait_for_files()
    intel_data = read_json_with_retry(INTEL_INPUT_PATH)
    analyst_data = read_json_with_retry(ANALYST_INPUT_PATH)

    # 1. Math & ROI
    val_risk = float(analyst_data.get("total_value_at_risk", 50000))
    routes = intel_data.get("alternative_routes", [])
    sim_details = intel_data.get("simulation_details", [])
    recommended_mode = intel_data.get("recommended_mode", "Road")
    
    if not routes:
        best_route = {"route_description": recommended_mode, "cost_per_shipment": 2000}
    elif isinstance(routes[0], str):
        route_name = routes[0]
        best_route = {"route_description": route_name, "cost_per_shipment": 2000}
    elif isinstance(routes[0], dict):
        route_dict = routes[0]
        if "mode" in route_dict:
            best_route = {"route_description": route_dict.get("mode", recommended_mode), "cost_per_shipment": 2000}
        elif "route_description" in route_dict:
            best_route = route_dict
        else:
            best_route = {"route_description": recommended_mode, "cost_per_shipment": 2000}
    else:
        best_route = {"route_description": recommended_mode, "cost_per_shipment": 2000}
    
    cost = float(best_route.get("cost_per_shipment", 2000))
    
    savings = (val_risk * 0.8) - cost
    bleed = calculate_bleed_rate(val_risk)

    # 2. AI Translation
    print("🤖 [Manager] Asking Llama-3 to generate Executive Audio Briefings...")
    prompt = f"Situation: Flood at NH-66. Value: ${val_risk}. Route: {best_route['route_description']}. Savings: ${savings:.0f}. Write TWO sections separated by '|'. 1: A 2-sentence English alert. 2: Translate it exactly to Malayalam."
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=200
    )
    
    try:
        content = response.choices[0].message.content
        if content:
            exec_en, exec_ml = content.strip().split("|")
        else:
            raise ValueError("Empty response")
    except:
        exec_en = f"Alert: Flood on NH-66. Rerouting via {best_route['route_description']} saving ${savings:.0f}."
        exec_ml = "മുന്നറിയിപ്പ്: NH-66 ൽ വെള്ളപ്പൊക്കം. വഴിതിരിച്ചുവിടുന്നു."

    # 3. Audio Generation
    gTTS(text=exec_en.strip(), lang="en", tld="co.in").save(MP3_ENGLISH)
    gTTS(text=exec_ml.strip(), lang="ml").save(MP3_MALAYALAM)

    # 4. Trigger Advanced Hardware/Mobile Features
    agv_payload = generate_agv_payload(best_route['route_description'])

    delay_hours = int(best_route.get("delay_hours", 6))
    new_eta_days = int(best_route.get("new_eta_days", 1))
    update_warehouse_wms(
        shipment_id=agv_payload["shipment_id"],
        delay_hours=delay_hours,
        new_eta_days=new_eta_days,
    )

    send_telegram_alert(
        exec_en.strip(),
        savings,
        best_route['route_description'],
        MP3_MALAYALAM,
    )

    # 5. Output Final Dashboard JSON
    final_payload = {
        "disruption": "Flood",
        "recommended_route": best_route['route_description'],
        "roi": {"value_at_risk": val_risk, "savings": savings},
        **bleed, # Injects the bleed rate dict into this level
        "agv_status": f"Bay {agv_payload['bay_number']} Reserved",
        "briefing_text_english": exec_en.strip(),
        "briefing_text_malayalam": exec_ml.strip(),
        "show_approve_button": True
    }

    with open(FINAL_OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(final_payload, file, indent=2, ensure_ascii=False)

    print(f"✅ [Manager] Final payload written to {FINAL_OUTPUT_PATH}")
    
    # Clean up triggers
    os.remove(INTEL_INPUT_PATH)
    os.remove(ANALYST_INPUT_PATH)
    print("🏁 [Manager] Pipeline reset and waiting for next disruption...")

# ==========================================
# MOCK DATA FOR TESTING
# ==========================================
def create_mock_files():
    os.makedirs(SHARED_DIR, exist_ok=True)
    with open(INTEL_INPUT_PATH, "w") as f:
        json.dump({"alternative_routes": [{"route_description": "Kochi Airport Air Freight", "cost_per_shipment": 6000}]}, f)
    with open(ANALYST_INPUT_PATH, "w") as f:
        json.dump({"total_value_at_risk": 427000}, f)

if __name__ == "__main__":
    import threading

    if not os.path.exists(INTEL_INPUT_PATH):
        create_mock_files()

    # Start Telegram callback poller as background daemon before main loop.
    telegram_poller_thread = threading.Thread(target=poll_telegram_updates, daemon=True)
    telegram_poller_thread.start()

    try:
        while True:
            run_pipeline_once()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down.")