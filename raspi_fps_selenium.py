#!/usr/bin/env python3
"""
MirrorGrid Test 4B — Automated Browser FPS Measurement (Selenium)
==================================================================
Launches Chromium on the Pi, injects a FPS counter, and records
real WebGL frame rates for the paper.

Prerequisites:
  sudo apt install chromium-chromedriver
  pip install selenium

Usage:
  python3 raspi_fps_selenium.py [--url http://localhost:8000] [--duration 30]
"""

import argparse
import json
import statistics
import time
import sys
from datetime import datetime

# Force UTF-8 output on all platforms
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
except ImportError:
    sys.exit("Install selenium: pip install selenium")


def measure_fps(url="http://localhost:8000", duration=30):
    """Open Chromium, inject FPS counter, collect readings."""

    print(f"\n  Launching Chromium -> {url}")
    print(f"  Measurement window: {duration} seconds\n")

    opts = Options()
    opts.add_argument("--kiosk")                    # fullscreen
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--use-gl=egl")               # Use GPU on Pi
    opts.add_argument("--enable-webgl")
    opts.add_argument("--ignore-gpu-blocklist")

    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for Three.js scene + MediaPipe to initialize

        # Inject a precise FPS measurement script
        driver.execute_script("""
            window.__fpsReadings = [];
            window.__fpsRunning = true;
            let lastTime = performance.now();
            let frameCount = 0;

            function measureFPS() {
                if (!window.__fpsRunning) return;
                frameCount++;
                const now = performance.now();
                if (now - lastTime >= 1000) {
                    window.__fpsReadings.push(frameCount);
                    frameCount = 0;
                    lastTime = now;
                }
                requestAnimationFrame(measureFPS);
            }
            requestAnimationFrame(measureFPS);
        """)

        print(f"  Recording FPS for {duration}s...")
        time.sleep(duration)

        # Stop and collect
        driver.execute_script("window.__fpsRunning = false;")
        readings = driver.execute_script("return window.__fpsReadings;")

    finally:
        driver.quit()

    if not readings:
        print("  ERROR: No FPS readings collected!")
        return None

    # Analyze
    avg_fps = statistics.mean(readings)
    min_fps = min(readings)
    max_fps = max(readings)
    std_fps = statistics.stdev(readings) if len(readings) > 1 else 0

    # 1% low
    sorted_r = sorted(readings)
    low_1pct = sorted_r[:max(1, len(sorted_r) // 100)]
    low_1pct_fps = statistics.mean(low_1pct)

    result = {
        "test": "T4B",
        "description": "Browser WebGL FPS (Raspberry Pi — real measurement)",
        "platform": "Raspberry Pi",
        "timestamp": datetime.now().isoformat(),
        "duration_s": duration,
        "samples": len(readings),
        "readings": readings,
        "avg_fps": round(avg_fps, 1),
        "min_fps": min_fps,
        "max_fps": max_fps,
        "stdev_fps": round(std_fps, 1),
        "low_1pct_fps": round(low_1pct_fps, 1),
        "exceeds_24fps": avg_fps >= 24,
        "verdict": "PASS" if avg_fps >= 24 else "FAIL",
    }

    print(f"\n  {'='*50}")
    print(f"  TEST 4B RESULTS — Real Browser FPS")
    print(f"  {'='*50}")
    print(f"  Samples:    {len(readings)} seconds")
    print(f"  Avg FPS:    {avg_fps:.1f}")
    print(f"  Min FPS:    {min_fps}")
    print(f"  Max FPS:    {max_fps}")
    print(f"  Stdev:      {std_fps:.1f}")
    print(f"  1% Low:     {low_1pct_fps:.1f}")
    print(f"  >=24 fps:    {'YES' if avg_fps >= 24 else 'NO'}")
    print(f"  VERDICT:    {result['verdict']}")
    print(f"  {'='*50}")

    # Save
    import os
    test_results_dir = "test_script"
    os.makedirs(test_results_dir, exist_ok=True)
    results_path = os.path.join(test_results_dir, "test_results_raspi_fps_selenium.json")
    with open(results_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {results_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()
    measure_fps(args.url, args.duration)
