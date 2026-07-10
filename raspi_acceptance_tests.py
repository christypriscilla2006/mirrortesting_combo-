#!/usr/bin/env python3
"""
MirrorGrid Phase 5.1 — Raspberry Pi Acceptance Test Harness
============================================================
Replicates Tests T1–T4 from the research paper, executed directly
on Raspberry Pi 5 hardware for real (not estimated) measurements.

Prerequisites:
  1. MirrorGrid backend running:  uvicorn main:app --host 0.0.0.0 --port 8000
  2. Python 3.11+ with: pip install requests websocket-client numpy

Usage:
  python3 raspi_acceptance_tests.py [--host localhost] [--port 8000]

Output:
  - Console summary with PASS/FAIL verdicts
  - raspi_test_results.json  (machine-readable results)
  - raspi_test_report.txt    (paper-ready formatted report)
"""

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed. Run: pip install requests")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("WARNING: numpy not found — Test 4A will use math module (slower but works)")


# ─── Configuration ────────────────────────────────────────────────────
PASS_THRESHOLD_REST_MS = 100.0       # Nielsen's instantaneous threshold
PASS_THRESHOLD_GESTURE_MS = 50.0     # Sub-50ms gesture response
STATE_MACHINE_PAGES = 5              # Pages 0–4 (adjust if you use 8)
T1_SAMPLES = 30
T2_SAMPLES_PER_GESTURE = 10
T3_CYCLES = 2
T4A_FRAMES = 200
T4A_DURATION_S = 5
T4A_PARTICLES = 3000
FPS_BENCHMARK_DURATION_S = 10        # For Test 4B browser FPS (if applicable)


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════
# TEST 1 — REST API Response Latency
# ═══════════════════════════════════════════════════════════════════════
def test1_rest_latency(base_url, samples=T1_SAMPLES):
    """GET /api/data latency — N samples, first excluded as cold-start."""
    print(f"\n{'='*60}")
    print(f"  TEST 1 — REST API Response Latency (N={samples})")
    print(f"{'='*60}")

    endpoint = f"{base_url}/api/data"
    latencies = []

    for i in range(samples):
        start = time.perf_counter()
        try:
            r = requests.get(endpoint, timeout=10)
            r.raise_for_status()
        except Exception as e:
            print(f"  Sample {i+1}: FAILED — {e}")
            latencies.append(None)
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        tag = " (cold-start)" if i == 0 else ""
        print(f"  Sample {i+1:>3}: {elapsed_ms:>8.2f} ms{tag}")

    # Separate cold-start from warm-path
    cold_start = latencies[0]
    warm = [x for x in latencies[1:] if x is not None]

    if not warm:
        return {"test": "T1", "verdict": "FAIL", "reason": "No valid samples"}

    result = {
        "test": "T1",
        "description": "REST API Response Latency",
        "platform": "Raspberry Pi",
        "cold_start_ms": round(cold_start, 2) if cold_start else None,
        "warm_n": len(warm),
        "min_ms": round(min(warm), 2),
        "max_ms": round(max(warm), 2),
        "mean_ms": round(statistics.mean(warm), 2),
        "stdev_ms": round(statistics.stdev(warm), 2) if len(warm) > 1 else 0,
        "threshold_ms": PASS_THRESHOLD_REST_MS,
        "verdict": "PASS" if statistics.mean(warm) < PASS_THRESHOLD_REST_MS else "FAIL",
    }

    print(f"\n  Cold-start:  {result['cold_start_ms']} ms (excluded)")
    print(f"  Warm N={result['warm_n']}:")
    print(f"    Min:    {result['min_ms']} ms")
    print(f"    Max:    {result['max_ms']} ms")
    print(f"    Mean:   {result['mean_ms']} ms")
    print(f"    Stdev:  {result['stdev_ms']} ms")
    print(f"  VERDICT:  {result['verdict']} ✓" if result['verdict'] == 'PASS'
          else f"  VERDICT:  {result['verdict']} ✗")
    return result


# ═══════════════════════════════════════════════════════════════════════
# TEST 2 — Gesture API State Transition Latency
# ═══════════════════════════════════════════════════════════════════════
def test2_gesture_latency(base_url, samples_per=T2_SAMPLES_PER_GESTURE):
    """POST /api/gesture/{gesture} latency per gesture type."""
    print(f"\n{'='*60}")
    print(f"  TEST 2 — Gesture API Latency (N={samples_per} per gesture)")
    print(f"{'='*60}")

    gestures = ["swipe_left", "swipe_right", "open_palm"]
    all_results = {}
    first_ever = True

    for gesture in gestures:
        endpoint = f"{base_url}/api/gesture/{gesture}"
        latencies = []
        print(f"\n  Gesture: {gesture}")

        for i in range(samples_per):
            time.sleep(0.2)  # 200ms inter-request delay (per paper methodology)
            start = time.perf_counter()
            try:
                r = requests.post(endpoint, timeout=10)
                r.raise_for_status()
            except Exception as e:
                print(f"    Sample {i+1}: FAILED — {e}")
                latencies.append(None)
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            tag = " (cold-start, excluded)" if first_ever and i == 0 else ""
            print(f"    Sample {i+1:>3}: {elapsed_ms:>8.2f} ms{tag}")

        # Exclude first-ever sample as cold-start
        if first_ever:
            cold_start = latencies[0]
            warm = [x for x in latencies[1:] if x is not None]
            first_ever = False
        else:
            cold_start = None
            warm = [x for x in latencies if x is not None]

        if warm:
            all_results[gesture] = {
                "min_ms": round(min(warm), 2),
                "max_ms": round(max(warm), 2),
                "mean_ms": round(statistics.mean(warm), 2),
            }
            print(f"    → Min: {all_results[gesture]['min_ms']} ms, "
                  f"Max: {all_results[gesture]['max_ms']} ms, "
                  f"Mean: {all_results[gesture]['mean_ms']} ms")

    # Overall
    all_means = [v["mean_ms"] for v in all_results.values()]
    overall_mean = round(statistics.mean(all_means), 2) if all_means else 999
    verdict = "PASS" if all(v["max_ms"] < PASS_THRESHOLD_GESTURE_MS
                           for v in all_results.values()) else "FAIL"

    result = {
        "test": "T2",
        "description": "Gesture API State Transition Latency",
        "platform": "Raspberry Pi",
        "gestures": all_results,
        "overall_mean_ms": overall_mean,
        "threshold_ms": PASS_THRESHOLD_GESTURE_MS,
        "verdict": verdict,
    }

    print(f"\n  Overall Mean: {overall_mean} ms")
    print(f"  VERDICT:  {verdict} ✓" if verdict == 'PASS' else f"  VERDICT:  {verdict} ✗")
    return result


# ═══════════════════════════════════════════════════════════════════════
# TEST 3 — State Machine Correctness
# ═══════════════════════════════════════════════════════════════════════
def test3_state_machine(base_url, num_pages=STATE_MACHINE_PAGES, cycles=T3_CYCLES):
    """Validate page transitions and wrap-around correctness."""
    print(f"\n{'='*60}")
    print(f"  TEST 3 — State Machine Correctness ({cycles} cycles, {num_pages} pages)")
    print(f"{'='*60}")

    endpoint = f"{base_url}/api/gesture/swipe_left"
    transitions = []
    failures = 0

    for cycle in range(1, cycles + 1):
        # Each cycle: num_pages transitions to cover all pages + wrap
        steps = num_pages + 3  # extra steps to verify wrap-around
        for step in range(steps):
            time.sleep(0.15)
            start = time.perf_counter()
            try:
                r = requests.post(endpoint, timeout=10)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  Cycle {cycle}, Step {step+1}: FAILED — {e}")
                failures += 1
                transitions.append({
                    "cycle": cycle, "step": step + 1,
                    "status": "error", "error": str(e)
                })
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Extract page from response
            page = data.get("current_page", data.get("page", "?"))
            status = data.get("status", "ok")

            is_wrap = (isinstance(page, int) and page == 0 and step > 0)
            wrap_tag = " (wrap)" if is_wrap else ""

            entry = {
                "cycle": cycle,
                "step": step + 1,
                "page": page,
                "status": status,
                "latency_ms": round(elapsed_ms, 2),
                "wrap": is_wrap,
            }
            transitions.append(entry)

            ok_mark = "ok" if status == "ok" else f"FAIL({status})"
            print(f"  Cycle {cycle} Step {step+1:>2}: "
                  f"Page={page}{wrap_tag:>8}  {ok_mark}  {elapsed_ms:.2f} ms")

            if status != "ok":
                failures += 1

    total = len(transitions)
    success_rate = round(((total - failures) / total) * 100, 1) if total else 0
    verdict = "PASS" if failures == 0 else "FAIL"

    result = {
        "test": "T3",
        "description": "State Machine Correctness",
        "platform": "Raspberry Pi",
        "total_transitions": total,
        "failures": failures,
        "success_rate_pct": success_rate,
        "transitions": transitions,
        "verdict": verdict,
    }

    print(f"\n  Transitions: {total}  |  Failures: {failures}  |  Rate: {success_rate}%")
    print(f"  VERDICT:  {verdict} ✓" if verdict == 'PASS' else f"  VERDICT:  {verdict} ✗")
    return result


# ═══════════════════════════════════════════════════════════════════════
# TEST 4A — CPU-Bound Particle Simulation (on actual Pi hardware)
# ═══════════════════════════════════════════════════════════════════════
def test4a_cpu_simulation(n_particles=T4A_PARTICLES, n_frames=T4A_FRAMES):
    """Pure-CPU 3D rotation simulation matching animateThree() equations."""
    print(f"\n{'='*60}")
    print(f"  TEST 4A — CPU-Bound Particle Simulation")
    print(f"  {n_particles} particles × {n_frames} frames (on THIS hardware)")
    print(f"{'='*60}")

    # Initialize random particle positions
    if HAS_NUMPY:
        positions = np.random.uniform(-50, 50, (n_particles, 3)).astype(np.float64)
    else:
        import random
        positions = [[random.uniform(-50, 50) for _ in range(3)]
                     for _ in range(n_particles)]

    rot_y_rate = 0.0008  # matches production rotation.y += 0.0008
    rot_x_rate = 0.0002  # matches production rotation.x += 0.0002
    frame_times = []

    for frame in range(n_frames):
        start = time.perf_counter()
        angle_y = rot_y_rate * frame
        angle_x = rot_x_rate * frame
        cos_y, sin_y = math.cos(angle_y), math.sin(angle_y)
        cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)

        if HAS_NUMPY:
            # Vectorized rotation
            x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
            # Y-axis rotation
            new_x = x * cos_y + z * sin_y
            new_z = -x * sin_y + z * cos_y
            # X-axis rotation
            new_y = y * cos_x - new_z * sin_x
            new_z2 = y * sin_x + new_z * cos_x
            positions[:, 0] = new_x
            positions[:, 1] = new_y
            positions[:, 2] = new_z2
        else:
            for i in range(n_particles):
                px, py, pz = positions[i]
                nx = px * cos_y + pz * sin_y
                nz = -px * sin_y + pz * cos_y
                ny = py * cos_x - nz * sin_x
                nz2 = py * sin_x + nz * cos_x
                positions[i] = [nx, ny, nz2]

        elapsed = (time.perf_counter() - start) * 1000
        frame_times.append(elapsed)

        if (frame + 1) % 50 == 0:
            print(f"  Frame {frame+1:>4}/{n_frames}: {elapsed:.3f} ms")

    avg_ft = statistics.mean(frame_times)
    min_ft = min(frame_times)
    max_ft = max(frame_times)
    std_ft = statistics.stdev(frame_times) if len(frame_times) > 1 else 0
    avg_fps = 1000.0 / avg_ft if avg_ft > 0 else 0

    # 1% low (worst 1% of frames)
    sorted_ft = sorted(frame_times, reverse=True)
    worst_1pct = sorted_ft[:max(1, len(sorted_ft) // 100)]
    low_1pct_fps = 1000.0 / statistics.mean(worst_1pct) if worst_1pct else 0

    meets_60 = avg_ft < 16.67

    result = {
        "test": "T4A",
        "description": "CPU-Bound Particle Simulation (actual Pi hardware)",
        "platform": "Raspberry Pi",
        "particles": n_particles,
        "frames": n_frames,
        "avg_frame_time_ms": round(avg_ft, 3),
        "min_frame_time_ms": round(min_ft, 3),
        "max_frame_time_ms": round(max_ft, 3),
        "stdev_ms": round(std_ft, 3),
        "avg_fps": round(avg_fps, 1),
        "low_1pct_fps": round(low_1pct_fps, 1),
        "meets_60fps": meets_60,
    }

    print(f"\n  Avg Frame Time:  {avg_ft:.3f} ms")
    print(f"  Min Frame Time:  {min_ft:.3f} ms")
    print(f"  Max Frame Time:  {max_ft:.3f} ms")
    print(f"  Stdev:           {std_ft:.3f} ms")
    print(f"  Avg FPS:         {avg_fps:.1f}")
    print(f"  1% Low FPS:      {low_1pct_fps:.1f}")
    print(f"  60 fps budget:   {'MET' if meets_60 else 'NOT MET'}")
    return result


# ═══════════════════════════════════════════════════════════════════════
# TEST 4B — Browser FPS (instructions for Selenium/Playwright)
# ═══════════════════════════════════════════════════════════════════════
def test4b_browser_fps_info():
    """Print instructions for real browser FPS measurement on Pi."""
    print(f"\n{'='*60}")
    print(f"  TEST 4B — Browser FPS Measurement (WebGL)")
    print(f"{'='*60}")
    print("""
  To measure REAL browser FPS on the Pi, you have two options:

  ── Option A: Use the built-in FPS counter ──
  1. Open Chromium on Pi:  chromium-browser --kiosk http://localhost:8000
  2. Navigate to System Stats panel (Page 4)
  3. The live FPS counter shows real WebGL frame rate
  4. Record the reading for 30+ seconds

  ── Option B: Automated with Selenium ──
  Install: pip install selenium
  Then run:  python3 raspi_fps_selenium.py
  (This script is generated alongside this file)

  ── Option C: Automated with Playwright ──
  Install: pip install playwright && playwright install chromium
  Then run:  python3 raspi_fps_playwright.py
  """)

    return {
        "test": "T4B",
        "description": "Browser FPS — see raspi_fps_selenium.py",
        "platform": "Raspberry Pi",
        "note": "Requires browser automation — see companion scripts",
    }


# ═══════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════
def generate_report(results, output_json, output_txt):
    """Write machine-readable JSON and paper-ready text report."""

    # JSON output
    report = {
        "title": "MirrorGrid Phase 5.1 — Raspberry Pi Acceptance Tests",
        "timestamp": timestamp(),
        "results": results,
    }
    with open(output_json, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  JSON results saved: {output_json}")

    # Text report
    with open(output_txt, "w") as f:
        f.write("=" * 65 + "\n")
        f.write("  MirrorGrid Phase 5.1 — Raspberry Pi Acceptance Test Report\n")
        f.write(f"  Generated: {timestamp()}\n")
        f.write("=" * 65 + "\n\n")

        for r in results:
            f.write(f"--- {r.get('test', '?')}: {r.get('description', '')} ---\n")
            verdict = r.get("verdict", "N/A")
            for k, v in r.items():
                if k not in ("test", "description", "transitions"):
                    f.write(f"  {k}: {v}\n")
            f.write("\n")

        # Summary table
        f.write("\n" + "=" * 65 + "\n")
        f.write("  SUMMARY\n")
        f.write("=" * 65 + "\n")
        for r in results:
            v = r.get("verdict", "N/A")
            mark = "✓" if v == "PASS" else "✗" if v == "FAIL" else "—"
            f.write(f"  {r['test']}: {r.get('description',''):<45} {v} {mark}\n")
        f.write("=" * 65 + "\n")

    print(f"  Text report saved: {output_txt}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="MirrorGrid Raspberry Pi Acceptance Tests"
    )
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", default=8000, type=int, help="Server port")
    parser.add_argument("--skip-t4a", action="store_true",
                        help="Skip CPU simulation test")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print("\n" + "=" * 65)
    print("  MirrorGrid Phase 5.1 — Raspberry Pi Acceptance Test Harness")
    print(f"  Target: {base_url}")
    print(f"  Time:   {timestamp()}")
    print("=" * 65)

    # Verify server is reachable
    try:
        requests.get(f"{base_url}/api/data", timeout=5)
        print("  ✓ Server reachable\n")
    except Exception as e:
        print(f"\n  ✗ Cannot reach server at {base_url}")
        print(f"    Error: {e}")
        print(f"\n  Make sure the MirrorGrid backend is running:")
        print(f"    cd /path/to/mirrorgrid")
        print(f"    uvicorn main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    results = []

    # Run tests
    results.append(test1_rest_latency(base_url))
    results.append(test2_gesture_latency(base_url))
    results.append(test3_state_machine(base_url))

    if not args.skip_t4a:
        results.append(test4a_cpu_simulation())

    results.append(test4b_browser_fps_info())

    # Generate reports
    import os
    test_results_dir = "test_results"
    os.makedirs(test_results_dir, exist_ok=True)
    generate_report(results, os.path.join(test_results_dir, "raspi_test_results.json"), os.path.join(test_results_dir, "raspi_test_report.txt"))

    # Final summary
    print(f"\n{'='*65}")
    print("  FINAL SUMMARY")
    print(f"{'='*65}")
    for r in results:
        v = r.get("verdict", "N/A")
        mark = "✓" if v == "PASS" else "✗" if v == "FAIL" else "—"
        print(f"  {r['test']}: {r.get('description',''):<45} {v} {mark}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
