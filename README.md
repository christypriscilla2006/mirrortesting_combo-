# MirrorGrid Phase 5 — Local Setup

## Folder Structure
```
mirrorgrid/
├── server.py          ← FastAPI backend (WebSocket + telemetry)
├── requirements.txt   ← Python dependencies
├── start.bat          ← Windows launcher
├── start.sh           ← Mac/Linux launcher
└── templates/
    └── index.html     ← Full frontend (Three.js + MediaPipe)
```

## Quick Start

### Windows
Double-click `start.bat`  
Then open: http://localhost:8000

### Mac / Linux
```bash
chmod +x start.sh
./start.sh
```
Then open: http://localhost:8000

### Manual
```bash
pip install -r requirements.txt
python server.py
```

## Requirements
- Python 3.9+
- Webcam
- Chrome or Edge (for MediaPipe camera access)
- Internet (for MediaPipe CDN on first load; cached after)

## Gesture Controls
| Gesture       | Action              |
|---------------|---------------------|
| ✊ Fist        | Sleep mode          |
| 🖐 Open Palm  | Wake / Go Home      |
| 👍 Thumb Up   | Next page           |
| ← Swipe Right | Previous page       |
| → Swipe Left  | Next page           |

## Keyboard Fallback
| Key           | Action        |
|---------------|---------------|
| Arrow Right   | Next page     |
| Arrow Left    | Previous page |
| W             | Wake          |
| S             | Sleep         |
| H             | Home          |

## Architecture
```
Browser (index.html)
  ├── MediaPipe Hands  → detects gesture + finger pos
  ├── Three.js         → particle background
  ├── GSAP             → animations
  └── WebSocket ──────→ server.py (FastAPI)
                              ├── psutil (CPU/RAM)
                              └── Broadcasts state @ 20Hz
```
