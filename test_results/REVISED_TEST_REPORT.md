# MirrorGrid OS Phase 5.1 — Revised Technical Test Report

> **ISO/IEC 25010 Repetitive Stress Testing, Edge AI Accuracy Analytics & Power Profiling**
> Generated: 2026-07-07 01:17:38  IST
> Platform: N/A

---

## 1. Host Environment Hardware Diagnostics

| Parameter | Value |
|-----------|-------|
| **Hostname** | `Christy-Priscilla` |
| **OS** | Windows 11 |
| **Kernel** | 10.0.26200 |
| **Architecture** | `AMD64` |
| **Board Model** | N/A |
| **CPU** | N/A (N/A cores) |
| **RAM** | 16055 MB total, 6304 MB available |
| **Disk** | 225.2 GB total, 111.7 GB free |
| **Python** | 3.13.14 |
| **Virtual Env** | `Not detected` |
| **Pi 5 Confirmed** | ⚠️ NO (running on dev machine) |

## 2. Test 1: REST API Response Latency (ISO/IEC 25010 — Performance Efficiency)

- **Endpoint**: `GET /api/data`
- **Total Requests**: 1000
- **Cold-Start Sample 1 (discarded)**: 264.2571 ms
- **Warm-Path Samples**: 999

### Warm-Path Latency Distribution

| Metric | Value (ms) |
|--------|-----------|
| Minimum | 2.9358 |
| Maximum | 38.6227 |
| **Mean (μ)** | **4.4398** |
| **Std Dev (σ)** | **2.1498** |
| Median | 4.0383 |
| P95 | 6.4303 |
| P99 | 9.3605 |

> **Quality Assertion**: Mean latency < 500 ms → **[PASS]**
> Raw data: `raw_api_latency_dump.txt`

## 3. Test 2: Gesture Mutation Latency (ISO/IEC 25010 — Time Behaviour)

- **Gestures**: swipe_left, swipe_right, open_palm
- **Iterations per gesture**: 1000
- **Inter-request delay**: 2.0 ms

### Per-Gesture Latency Table

| Gesture | Mean (ms) | Std Dev (ms) | Min (ms) | Max (ms) | P95 (ms) |
|---------|----------|-------------|---------|---------|---------|
| `swipe_left` | 10.1652 | 12.7594 | 3.3570 | 50.0609 | 44.7741 |
| `swipe_right` | 5.4865 | 1.8451 | 3.5366 | 37.5819 | 7.1845 |
| `open_palm` | 5.6636 | 3.2926 | 3.4619 | 46.0388 | 7.5092 |

- **Aggregate Overall Mean**: 7.1051 ms

> **Quality Assertion**: Aggregate gesture mean < 500 ms → **[PASS]**
> Raw data: `raw_gesture_latency_dump.txt`

## 4. Test 3: State Machine Correctness (ISO/IEC 25010 — Functional Correctness)

- **Operation**: 24 sequential `swipe_left` mutations
- **Full cycles completed**: 4 (+ 4 additional)
- **Total transitions**: 24
- **Correct transitions**: 24
- **Wrap-around compliance**: 100.0%
- **Deterministic**: ✅ YES

> **Quality Assertion**: 100% deterministic wrap-around → **[PASS]**
> Raw data: `raw_state_transitions_dump.txt`

## 5. Test 4: Edge AI Gesture Accuracy Evaluation

> Resolves limitation from Section 6.2: *"Gesture Accuracy Not Evaluated"*

- **Total samples**: 500
- **Gesture classes**: 5 (swipe_left, swipe_right, open_palm, closed_fist, thumbs_up)
- **Samples per class**: 10

### Confusion Matrix

| Actual \ Predicted | `swipe_le` | `swipe_ri` | `open_pal` | `closed_f` | `thumbs_u` |
|---|---|---|---|---|---|
| **`swipe_left`** | **100** | 0 | 0 | 0 | 0 |
| **`swipe_right`** | 0 | **99** | 0 | 0 | 0 |
| **`open_palm`** | 0 | 0 | **100** | 0 | 0 |
| **`closed_fist`** | 0 | 0 | 0 | **100** | 0 |
| **`thumbs_up`** | 0 | 0 | 0 | 0 | **100** |

### Classification Performance Metrics

| Gesture Class | TP | FP | FN | TN | Accuracy (%) | Precision | Recall | F1-Score |
|---------------|---|----|----|----|-------------|-----------|--------|---------|
| `swipe_left` | 100 | 0 | 0 | 400 | 100.0 | 1.0000 | 1.0000 | 1.0000 |
| `swipe_right` | 99 | 0 | 0 | 401 | 100.0 | 1.0000 | 1.0000 | 1.0000 |
| `open_palm` | 100 | 0 | 0 | 400 | 100.0 | 1.0000 | 1.0000 | 1.0000 |
| `closed_fist` | 100 | 0 | 0 | 400 | 100.0 | 1.0000 | 1.0000 | 1.0000 |
| `thumbs_up` | 100 | 0 | 0 | 400 | 100.0 | 1.0000 | 1.0000 | 1.0000 |

- **Overall Accuracy**: 99.80%

> **Quality Assertion**: Overall accuracy ≥ 90% → **[PASS]**
> Raw data: `raw_edge_ai_predictions_dump.txt`

## 6. Test 5: Hardware Power Analysis & Profiling

### Power Analysis Table

| Operational State | Description | Mean Power (W) |
|-------------------|-------------|---------------|
| **Idle** | Screen on, no gesture processing, static browser | N/A |
| **Active Gesture** | MediaPipe WASM pipeline active, 21 landmark tracking | N/A |
| **WebGL Load** | Three.js r128 canvas, 3000-particle vertex shader | N/A |

- **Δ Gesture over Idle**: N/A
- **Δ WebGL over Idle**: N/A

### Measurement Methodology

Power values are derived exclusively from direct physical hardware telemetry:
1. **Direct PMIC telemetry**: `/sys/class/power_supply/` voltage/current nodes (Pi 5 PMIC)
2. **vcgencmd diagnostics**: Core voltage, clock frequencies, throttle status
3. No CPU-utilization-based proxy or simulated/estimated equations are used. If direct PMIC telemetry is unavailable, power is reported as `N/A`.

> **Quality Assertion**: Peak power within USB-PD 15W budget → **[N/A]**
> Raw data: `raw_hardware_power_dump.txt`

## 7. Quality Standards Summary

| Test | Standard | Assertion | Result |
|------|----------|-----------|--------|
| Test 1: API Latency | ISO 25010 Performance Efficiency | μ < 500 ms | **PASS** |
| Test 2: Gesture Latency | ISO 25010 Time Behaviour | Aggregate μ < 500 ms | **PASS** |
| Test 3: State Machine | ISO 25010 Functional Correctness | 100% deterministic | **PASS** |
| Test 4: Edge AI Accuracy | Classification Performance | Overall ≥ 90% | **PASS** |
| Test 5: Power Profile | USB-PD Budget Compliance | Peak < 15W | **N/A** |

### Overall Verdict: ⚠️ SOME TESTS REQUIRE ATTENTION

## 8. Raw Data File Verification

All raw data streams have been independently mirrored to their respective `.txt` files:

| File | Path | Status |
|------|------|--------|
| `raw_api_latency_dump.txt` | `C:\Users\HP\Documents\MIrrorGrid\test_results\raw_api_latency_dump.txt` | ✅ 94,246 bytes |
| `raw_gesture_latency_dump.txt` | `C:\Users\HP\Documents\MIrrorGrid\test_results\raw_gesture_latency_dump.txt` | ✅ 183,372 bytes |
| `raw_state_transitions_dump.txt` | `C:\Users\HP\Documents\MIrrorGrid\test_results\raw_state_transitions_dump.txt` | ✅ 1,698 bytes |
| `raw_edge_ai_predictions_dump.txt` | `C:\Users\HP\Documents\MIrrorGrid\test_results\raw_edge_ai_predictions_dump.txt` | ✅ 42,435 bytes |
| `raw_hardware_power_dump.txt` | `C:\Users\HP\Documents\MIrrorGrid\test_results\raw_hardware_power_dump.txt` | ✅ 1,613 bytes |

---

*Report generated by `iso25010_stress_test.py` at 2026-07-07T01:17:38.727136*
*MirrorGrid OS Phase 5.1 | Python 3.13.14 | Windows-11-10.0.26200-SP0*
