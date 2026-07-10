"""
MIrrorGrid — Vision Tracker
Uses MediaPipe GestureRecognizer for robust, AI-driven gesture tracking.
Resolution: 320x240 @ 15fps — strict CPU ceiling for Pi 5.
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import httpx
import time
import threading
import logging
import os

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VISION] %(message)s",
)
log = logging.getLogger("vision_tracker")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
CAPTURE_WIDTH   = 320
CAPTURE_HEIGHT  = 240
TARGET_FPS      = 15
BACKEND_URL     = "http://localhost:8000"
GESTURE_COOLDOWN_S = 1.0   # Minimum seconds between repeated gesture fires

# Map MediaPipe's official gesture strings to our UI commands
GESTURE_MAP = {
    "Open_Palm":   "open_palm",
    "Closed_Fist": "closed_fist",
    "Thumb_Up":    "thumbs_up",
    "Thumb_Down":  "thumbs_up",  # Treat down as dismiss too
    "Pointing_Up": "swipe_left", # Fallback for cycle
    "Victory":     "swipe_right" # Fallback for cycle
}

# ─────────────────────────────────────────────
# GESTURE INJECTOR
# ─────────────────────────────────────────────

def _inject(gesture: str):
    """Send gesture to FastAPI backend via HTTP POST."""
    try:
        with httpx.Client(timeout=0.5) as client:
            r = client.post(f"{BACKEND_URL}/api/gesture/{gesture}")
            log.info(f"→ {gesture}  [{r.status_code}]")
    except Exception as e:
        log.warning(f"Inject failed for '{gesture}': {e}")


def inject_gesture_async(gesture: str):
    """Fire-and-forget daemon thread injection."""
    t = threading.Thread(target=_inject, args=(gesture,), daemon=True)
    t.start()


# ─────────────────────────────────────────────
# MAIN CV LOOP
# ─────────────────────────────────────────────

def run_tracker():
    """Main vision tracking loop using MediaPipe GestureRecognizer."""
    log.info(f"Initialising camera @ {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} {TARGET_FPS}fps...")

    # Ensure model exists
    model_path = os.path.join(os.path.dirname(__file__), "gesture_recognizer.task")
    if not os.path.exists(model_path):
        log.error(f"Model file not found: {model_path}")
        return

    # ── Camera setup ──────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          TARGET_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    if not cap.isOpened():
        log.error("Camera not found. Is your webcam connected?")
        return

    # ── MediaPipe GestureRecognizer setup ────────────────────
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.GestureRecognizerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    recognizer = vision.GestureRecognizer.create_from_options(options)

    # ── State ─────────────────────────────────────────────────
    frame_interval  = 1.0 / TARGET_FPS
    last_gesture_ts = 0.0
    last_gesture    = None
    fist_start_ts   = 0.0
    
    # We use basic x-position tracking for explicit left/right swipes
    # since MediaPipe's built-in gestures don't include Swipe out of the box.
    prev_index_x = None

    log.info("Vision tracker ONLINE. Utilizing AI GestureRecognizer...")

    try:
        while True:
            try:
                loop_start = time.monotonic()

                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                # Convert to MediaPipe Image
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                # Detect Gestures
                results = recognizer.recognize(mp_image)
                gesture = None

                if results.gestures and len(results.gestures) > 0:
                    top_gesture = results.gestures[0][0]
                    category_name = top_gesture.category_name
                    score = top_gesture.score
                    
                    # We need the index finger tip (landmark 8) for horizontal swipes based on user request
                    index_x = results.hand_landmarks[0][8].x if (results.hand_landmarks and len(results.hand_landmarks[0]) > 8) else 0
                    
                    # Check for Left/Right Swipes on ANY hand movement (more lenient)
                    if prev_index_x is not None:
                        delta = index_x - prev_index_x
                        if delta > 0.03:  # Lowered threshold for much easier swiping
                            gesture = "swipe_right"
                        elif delta < -0.03:
                            gesture = "swipe_left"
                    
                    # If it's not a swipe, use the pre-trained neural network class
                    if not gesture and category_name in GESTURE_MAP and score > 0.6:
                        gesture = GESTURE_MAP[category_name]
                        
                    prev_index_x = index_x
                else:
                    prev_index_x = None

                # Fist sensitivity reduction: require 800ms hold
                if gesture == "closed_fist":
                    if fist_start_ts == 0.0:
                        fist_start_ts = loop_start
                        gesture = None
                    elif (loop_start - fist_start_ts) < 0.8:
                        gesture = None
                else:
                    fist_start_ts = 0.0

                # ── Cooldown-gated injection ──────────────────────
                now = time.monotonic()
                if gesture and (
                    gesture != last_gesture or
                    (now - last_gesture_ts) > GESTURE_COOLDOWN_S
                ):
                    last_gesture    = gesture
                    last_gesture_ts = now
                    inject_gesture_async(gesture)

                # ── FPS cap ───────────────────────────────────────
                elapsed = time.monotonic() - loop_start
                sleep_t = frame_interval - elapsed
                if sleep_t > 0:
                    time.sleep(sleep_t)
            except Exception as e:
                log.error(f"CRASH in vision loop: {e}. Recovering in 1s...")
                time.sleep(1)

    except KeyboardInterrupt:
        log.info("Vision tracker stopped by user.")
    finally:
        cap.release()
        log.info("Camera released.")

def start_tracker() -> threading.Thread:
    t = threading.Thread(target=run_tracker, name="vision-tracker", daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    run_tracker()
