"""
MirrorGrid Phase 5 — Local Server
Run: python server.py
Then open: http://localhost:8000
"""

import asyncio
import json
import time
import psutil
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# ── Serve static files ──
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("templates/index.html")

# ── Shared gesture state (written by /gesture POST, read by WS) ──
gesture_state = {
    "page": 0,
    "sleeping": True,
    "pointer": {"x": 0.5, "y": 0.5},
    "gesture": "NONE",
    "last_swipe": 0,
    "last_thumb": 0,
    "prev_x": 0.5,
}

TOTAL_PAGES = 5

def apply_gesture(gesture: str, pointer: dict):
    """Server-side gesture → page logic (mirrors frontend logic as backup)."""
    now = time.time()
    state = gesture_state
    x = pointer.get("x", 0.5)
    vel = x - state["prev_x"]
    state["prev_x"] = x
    state["pointer"] = pointer
    state["gesture"] = gesture

    if gesture == "CLOSED_FIST":
        state["sleeping"] = True
        return

    if state["sleeping"]:
        if gesture == "OPEN_PALM":
            state["sleeping"] = False
            state["page"] = 0
        return

    if gesture == "OPEN_PALM":
        state["page"] = 0
    elif gesture == "THUMB_UP":
        if now - state["last_thumb"] > 1.0:
            state["page"] = (state["page"] + 1) % TOTAL_PAGES
            state["last_thumb"] = now

    # Swipe
    if abs(vel) > 0.04 and now - state["last_swipe"] > 0.7:
        if vel < 0:
            state["page"] = min(TOTAL_PAGES - 1, state["page"] + 1)
        else:
            state["page"] = max(0, state["page"] - 1)
        state["last_swipe"] = now

@app.post("/gesture")
async def receive_gesture(body: dict):
    """Called by the frontend with detected gesture data."""
    gesture = body.get("gesture", "NONE")
    pointer = body.get("pointer", {"x": 0.5, "y": 0.5})
    apply_gesture(gesture, pointer)
    return {"ok": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✔ WebSocket client connected")
    try:
        while True:
            payload = {
                "page":     gesture_state["page"],
                "sleeping": gesture_state["sleeping"],
                "pointer":  gesture_state["pointer"],
                "gesture":  gesture_state["gesture"],
                "cpu":      psutil.cpu_percent(interval=None),
                "ram":      psutil.virtual_memory().percent,
                "time":     datetime.now().strftime("%H:%M"),
                "weather":  {"temp": "32°C", "desc": "Humid", "loc": "Chennai"},
                "traffic":  {"route": "OMR to Guindy", "delay": "14 mins", "status": "Heavy"},
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.05)  # 20 Hz
    except WebSocketDisconnect:
        print("✘ WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("  MirrorGrid Phase 5")
    print("  http://localhost:8000")
    print("=" * 50)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
