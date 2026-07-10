"""
MIrrorGrid — Backend Core
FastAPI + WebSocket broadcast engine (< 100ms latency)
In-memory Python dict cache — zero SD card I/O
Phase 5: 5-Page UI, Telemetry, Chennai Mock Data
"""

import asyncio
import json
import time
import logging
import psutil
from contextlib import asynccontextmanager
from typing import Set

VISION_AVAILABLE = False # Disabled to allow frontend MediaPipe to access camera

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("mirrorgrid")

# ─────────────────────────────────────────────
# IN-MEMORY STATE CACHE
# ─────────────────────────────────────────────
MIRROR_STATE: dict = {
    # UI Mode: "sleep" (blackout) | "wake" (UI visible)
    "mode": "wake",
    # Last gesture received from vision_tracker
    "gesture": "none",
    # Timestamp of last state update
    "updated_at": time.time(),
    # Active Page (0 to 4)
    # 0 = Idle (Wallpaper)
    # 1 = Briefing (Task + Weather)
    # 2 = Commute (Traffic)
    # 3 = Comms (Emails)
    # 4 = System (Telemetry)
    "page": 0,
}

# ─────────────────────────────────────────────
# MOCK DATA PAYLOAD
# ─────────────────────────────────────────────
MOCK_PAYLOAD: dict = {
    "task": {
        "title": "Student Schedule",
        "priority": "HIGH",
        "due": "TODAY",
        "subtasks": [
            {"label": "Submit Data Structures Assignment", "done": True},
            {"label": "Group Study for Finals",            "done": False},
            {"label": "Pay Mess Bill",                     "done": False},
            {"label": "Complete Lab Record",               "done": False},
        ],
    },
    "weather": {
        "location": "Chennai, India",
        "condition": "Humid / Partly Cloudy",
        "temp_c": 34,
        "humidity_pct": 82,
        "wind_kph": 18,
        "forecast": [
            {"day": "MON", "icon": "☀️",  "high": 36, "low": 28},
            {"day": "TUE", "icon": "⛅",  "high": 35, "low": 27},
            {"day": "WED", "icon": "🌧️", "high": 33, "low": 26},
        ],
    },
    "traffic": {
        "location": "OMR to Guindy",
        "status": "Heavy Traffic",
        "eta_mins": 45,
        "incidents": "Congestion near Tidel Park",
        "trend": "increasing"
    },
    "emails": [
        {"sender": "Prof. Sharma", "subject": "Exam Syllabus Update", "time": "10:30 AM"},
        {"sender": "Internship Team", "subject": "Action Required: Onboarding", "time": "09:15 AM"},
        {"sender": "Library", "subject": "Overdue Book Notice", "time": "Yesterday"},
    ],
    "system": {
        "hostname": "mirrorgrid-pi5",
        "uptime_hrs": 0,
    },
}

# ─────────────────────────────────────────────
# WEBSOCKET CONNECTION MANAGER
# ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        log.info(f"WS client connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        log.info(f"WS client disconnected. Total: {len(self.active)}")

    async def broadcast(self, payload: dict):
        if not self.active:
            return
        message = json.dumps(payload)
        dead: Set[WebSocket] = set()
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active.discard(ws)

manager = ConnectionManager()


# ─────────────────────────────────────────────
# TELEMETRY LOOP
# ─────────────────────────────────────────────
async def telemetry_loop():
    """Broadcasts live CPU/RAM metrics and mock data for the UI."""
    # Initialize psutil metrics
    psutil.cpu_percent(interval=None)
    while True:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        current_time = time.strftime("%H:%M:%S")
        
        await manager.broadcast({
            "type": "telemetry",
            "cpu": cpu,
            "ram": mem,
            "time": current_time,
            "weather": {"temp": f"{MOCK_PAYLOAD['weather']['temp_c']}°C"},
            "traffic": {"delay": "14 min"}
        })
        await asyncio.sleep(1.0)


# ─────────────────────────────────────────────
# GESTURE → STATE MACHINE
# ─────────────────────────────────────────────
GESTURE_TRANSITIONS = {
    # Open Palm: Return to Page 0 (Idle)
    "open_palm":   lambda s: {"mode": "wake",  "page": 0},
    
    # Closed Fist: Stealth Mode
    "closed_fist": lambda s: {"mode": "sleep", "page": s["page"]},
    
    # Swipe Left/Right: Cycle pages 1-4 (If on page 0, swipe goes to 1 or 4)
    "swipe_left":  lambda s: {"mode": "wake",  "page": (s["page"] + 1) % 5},
    "swipe_right": lambda s: {"mode": "wake",  "page": (s["page"] - 1) % 5},
    
    # Thumbs Up: Move to next page (Alias for Swipe Left)
    "thumbs_up":   lambda s: {"mode": "wake",  "page": (s["page"] + 1) % 5},
}

async def apply_gesture(gesture: str) -> dict:
    if gesture not in GESTURE_TRANSITIONS:
        return MIRROR_STATE

    patch = GESTURE_TRANSITIONS[gesture](MIRROR_STATE)
    MIRROR_STATE.update(patch)
    MIRROR_STATE["gesture"]    = gesture
    MIRROR_STATE["updated_at"] = time.time()

    broadcast_payload = {
        "type":          "state_update",
        "mode":          MIRROR_STATE["mode"],
        "gesture":       gesture,
        "page":          MIRROR_STATE["page"],
        "ts":            MIRROR_STATE["updated_at"],
    }
    await manager.broadcast(broadcast_payload)
    log.info(f"Gesture '{gesture}' → mode='{MIRROR_STATE['mode']}' page={MIRROR_STATE['page']}")
    return MIRROR_STATE


# ─────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("═══ MIrrorGrid Backend ONLINE (Phase 5) ═══")
    
    telemetry_task = asyncio.create_task(telemetry_loop())
    
    if VISION_AVAILABLE:
        from vision_tracker import start_tracker
        tracker_thread = start_tracker()
        log.info(f"Vision tracker thread: {tracker_thread.name} (id={tracker_thread.ident})")
    else:
        log.warning("vision_tracker not available — running in API-only mode.")
        
    yield
    
    telemetry_task.cancel()
    log.info("═══ MIrrorGrid Backend SHUTDOWN ═══")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="MIrrorGrid OS",
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="../frontend"), name="frontend")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/static/index.html")

@app.get("/api/data", tags=["Data"])
async def get_data():
    MOCK_PAYLOAD["system"]["uptime_hrs"] = round(
        (time.time() - (time.time() % 3600)) / 3600, 1
    )
    return MOCK_PAYLOAD

@app.get("/api/state", tags=["State"])
async def get_state():
    return MIRROR_STATE

@app.post("/api/gesture/{gesture_name}", tags=["Gesture"])
async def inject_gesture(gesture_name: str):
    if gesture_name not in GESTURE_TRANSITIONS:
        return {"error": "Unknown gesture"}
    state = await apply_gesture(gesture_name)
    return {"ok": True, "state": state}

@app.get("/api/news", tags=["News"])
async def get_news():
    return [
        {"source": "AP News", "headline": "Global Markets Rally on Rate Cut Expectations", "summary": "World markets rose sharply as central banks signal a potential pause in rate hikes amid cooling inflation data."},
        {"source": "Reuters", "headline": "UN Climate Summit Reaches Landmark Agreement", "summary": "Member nations agreed on new carbon reduction targets, pledging net-zero emissions by 2045 in a historic vote."},
        {"source": "BBC World", "headline": "Tech Giants Face New AI Regulation Framework", "summary": "The EU unveiled sweeping AI governance rules requiring transparency and human oversight for high-risk applications."},
        {"source": "The Hindu", "headline": "India Q1 GDP Growth Surprises at 7.2%", "summary": "India's economy outpaced forecasts, driven by strong manufacturing output and robust domestic consumption."}
    ]

@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_text(json.dumps({
        "type":          "state_update",
        "mode":          MIRROR_STATE["mode"],
        "gesture":       MIRROR_STATE["gesture"],
        "page":          MIRROR_STATE["page"],
        "ts":            MIRROR_STATE["updated_at"],
    }))
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": time.time()}))
            else:
                try:
                    payload = json.loads(data)
                    gesture = payload.get("gesture")
                    if gesture:
                        await apply_gesture(gesture)
                except Exception as ex:
                    log.warning(f"Failed to process WS message '{data}': {ex}")
    except WebSocketDisconnect:
        manager.disconnect(ws)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=10,
    )
