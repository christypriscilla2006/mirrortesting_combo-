#!/usr/bin/env python3
"""
decoupled_latency_statistics.py
Author: Senior Data Scientist (Embedded Systems & Edge AI Telemetry)

This is a standalone, decoupled, production-grade statistical analysis script 
designed to ingest raw hardware and software latency/prediction dumps from the 
smart mirror codebase and output academic metrics and visualizations suitable 
for high-end IEEE/Springer publication.

Dependencies:
    pip install pandas scipy matplotlib seaborn
"""

import os
import re
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set publication style for figures (IEEE/Springer compliant)
sns.set_theme(style="whitegrid", context="paper", palette="muted")
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 12,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def parse_api_latencies(filepath):
    """
    Parses the raw API latency log file.
    Filters out COLD-START-DISCARDED entries to prevent steady-state skew.
    """
    warm_latencies = []
    cold_latencies = []
    
    if not os.path.exists(filepath):
        print(f"[Warning] File not found: {filepath}")
        return None, None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                lat_str = parts[1].replace('ms', '').strip()
                try:
                    val = float(lat_str)
                    label = parts[2]
                    if 'COLD-START' in label:
                        cold_latencies.append(val)
                    else:
                        warm_latencies.append(val)
                except ValueError:
                    continue
                    
    return np.array(warm_latencies), np.array(cold_latencies)

def parse_gesture_latencies(filepath):
    """
    Parses the raw gesture latency log file.
    Extracts all latency values.
    """
    latencies = []
    
    if not os.path.exists(filepath):
        print(f"[Warning] File not found: {filepath}")
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                lat_str = parts[2].replace('ms', '').strip()
                try:
                    val = float(lat_str)
                    latencies.append(val)
                except ValueError:
                    continue
                    
    return np.array(latencies)

def parse_predictions(filepath):
    """
    Parses expected vs predicted hand gestures for confusion matrix computation.
    """
    expected = []
    predicted = []
    
    if not os.path.exists(filepath):
        print(f"[Warning] File not found: {filepath}")
        return None, None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                exp_match = re.search(r'Expected=(\w+)', parts[0])
                pred_match = re.search(r'Predicted=(\w+)', parts[1])
                if exp_match and pred_match:
                    expected.append(exp_match.group(1))
                    predicted.append(pred_match.group(1))
                    
    return expected, predicted

def compute_statistics(data, label="Dataset"):
    """
    Computes Mean, Median, Min, Max, Variance, Standard Deviation,
    Tail Latency (P95, P99), Outlier Counts, and 95% Confidence Intervals.
    """
    if data is None or len(data) == 0:
        return {}
    
    n = len(data)
    mean = np.mean(data)
    median = np.median(data)
    minimum = np.min(data)
    maximum = np.max(data)
    variance = np.var(data, ddof=1)
    std_dev = np.std(data, ddof=1)
    
    # Tail latencies
    p95 = np.percentile(data, 95)
    p99 = np.percentile(data, 99)
    
    # Outliers via IQR Method
    q25, q75 = np.percentile(data, [25, 75])
    iqr = q75 - q25
    lower_bound = q25 - 1.5 * iqr
    upper_bound = q75 + 1.5 * iqr
    outliers = data[(data < lower_bound) | (data > upper_bound)]
    outlier_count = len(outliers)
    
    # 95% Confidence Interval
    sem = stats.sem(data)
    ci_margin = sem * stats.t.ppf((1 + 0.95) / 2., n - 1)
    ci = (mean - ci_margin, mean + ci_margin)
    
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "min": minimum,
        "max": maximum,
        "var": variance,
        "std": std_dev,
        "p95": p95,
        "p99": p99,
        "outlier_count": outlier_count,
        "ci": ci
    }

def print_statistics_table(win_stats, pi_stats):
    """
    Formats stats output as a clean table copy-pasteable into LaTeX or Word.
    """
    print("="*80)
    print(f"{'LATENCY TELEMETRY SUMMARY TABLE (IEEE READY)':^80}")
    print("="*80)
    print(f"{'Metric':<30} | {'Windows 11 (x86_64)':<22} | {'Raspberry Pi 5 (ARM)':<22}")
    print("-"*80)
    
    w_mean_sd = f"{win_stats['mean']:.4f} ± {win_stats['std']:.4f}"
    pi_mean_sd = f"{pi_stats['mean']:.4f} ± {pi_stats['std']:.4f}"
    
    w_med = f"{win_stats['median']:.4f}"
    pi_med = f"{pi_stats['median']:.4f}"
    
    w_range = f"{win_stats['min']:.4f} / {win_stats['max']:.4f}"
    pi_range = f"{pi_stats['min']:.4f} / {pi_stats['max']:.4f}"
    
    w_var = f"{win_stats['var']:.4f}"
    pi_var = f"{pi_stats['var']:.4f}"
    
    w_p95 = f"{win_stats['p95']:.4f}"
    pi_p95 = f"{pi_stats['p95']:.4f}"
    
    w_p99 = f"{win_stats['p99']:.4f}"
    pi_p99 = f"{pi_stats['p99']:.4f}"
    
    w_ci = f"[{win_stats['ci'][0]:.4f}, {win_stats['ci'][1]:.4f}]"
    pi_ci = f"[{pi_stats['ci'][0]:.4f}, {pi_stats['ci'][1]:.4f}]"
    
    print(f"{'Sample Size (N)':<30} | {str(win_stats['n']):<22} | {str(pi_stats['n']):<22}")
    print(f"{'Mean ± SD (ms)':<30} | {w_mean_sd:<22} | {pi_mean_sd:<22}")
    print(f"{'Median Latency (ms)':<30} | {w_med:<22} | {pi_med:<22}")
    print(f"{'Min / Max Latency (ms)':<30} | {w_range:<22} | {pi_range:<22}")
    print(f"{'Variance (ms^2)':<30} | {w_var:<22} | {pi_var:<22}")
    print(f"{'Tail Latency P95 (ms)':<30} | {w_p95:<22} | {pi_p95:<22}")
    print(f"{'Tail Latency P99 (ms)':<30} | {w_p99:<22} | {pi_p99:<22}")
    print(f"{'IQR Outliers Detected (spikes)':<30} | {str(win_stats['outlier_count']):<22} | {str(pi_stats['outlier_count']):<22}")
    print(f"{'95% Confidence Interval (Mean)':<30} | {w_ci:<22} | {pi_ci:<22}")
    print("="*80)

def compute_ai_metrics(expected, predicted):
    """
    Computes Confusion Matrix, Precision, Recall, Accuracy, and F1-score 
    without relying on scikit-learn.
    """
    if not expected or not predicted:
        return
        
    y_act = pd.Series(expected, name='Actual')
    y_pred = pd.Series(predicted, name='Predicted')
    
    # Compute Confusion Matrix using Pandas crosstab
    cm = pd.crosstab(y_act, y_pred, margins=False)
    
    # Ensure square matrix for confusion matrix representation (add missing classes if needed)
    all_classes = sorted(list(set(expected + predicted)))
    cm = cm.reindex(index=all_classes, columns=all_classes, fill_value=0)
    
    total_samples = len(expected)
    correct_predictions = sum(1 for e, p in zip(expected, predicted) if e == p)
    accuracy = correct_predictions / total_samples
    
    class_metrics = {}
    for c in all_classes:
        tp = cm.loc[c, c]
        fp = cm[c].sum() - tp
        fn = cm.loc[c].sum() - tp
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        class_metrics[c] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn
        }
        
    # Calculate Macro Averages
    macro_precision = np.mean([m["precision"] for m in class_metrics.values()])
    macro_recall = np.mean([m["recall"] for m in class_metrics.values()])
    macro_f1 = np.mean([m["f1"] for m in class_metrics.values()])
    
    print("\n" + "="*80)
    print(f"{'AI VISION CLASSIFIER RELIABILITY REPORT':^80}")
    print("="*80)
    print("\n--- Confusion Matrix ---")
    print(cm)
    print("\n--- Detailed Class-wise Metrics ---")
    print(f"{'Class':<20} | {'Precision':<12} | {'Recall':<12} | {'F1-Score':<12} | {'TP/FP/FN':<15}")
    print("-" * 80)
    for c, m in class_metrics.items():
        p_str = f"{m['precision']:.4f}"
        r_str = f"{m['recall']:.4f}"
        f_str = f"{m['f1']:.4f}"
        counts = f"{m['tp']}/{m['fp']}/{m['fn']}"
        print(f"{c:<20} | {p_str:<12} | {r_str:<12} | {f_str:<12} | {counts:<15}")
        
    print("-" * 80)
    print(f"{'Overall System Accuracy':<20} : {accuracy:.4%}")
    print(f"{'Macro-Averaged Precision':<20} : {macro_precision:.4f}")
    print(f"{'Macro-Averaged Recall':<20} : {macro_recall:.4f}")
    print(f"{'Macro-Averaged F1-Score':<20} : {macro_f1:.4f}")
    print("="*80)
    
    return cm

def make_plots(win_data, pi_data, output_dir):
    """
    Generates high-resolution publication-ready visualizations.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Dataframe representation for Seaborn
    df_win = pd.DataFrame({"Latency": win_data, "Platform": "Windows 11 (x86-64)"})
    df_pi = pd.DataFrame({"Latency": pi_data, "Platform": "Raspberry Pi 5 (ARM)"})
    df_combined = pd.concat([df_win, df_pi])
    
    # -------------------------------------------------------------
    # 1. Combined Box Plot
    # -------------------------------------------------------------
    plt.figure(figsize=(6, 4))
    sns.boxplot(x="Platform", y="Latency", data=df_combined, width=0.5, fliersize=3)
    plt.ylabel("Latency (ms)")
    plt.xlabel("")
    plt.title("Latency Distribution & Outliers Comparison")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_boxplot.png"))
    plt.close()
    
    # -------------------------------------------------------------
    # 2. Overlaid Histograms with KDE
    # -------------------------------------------------------------
    plt.figure(figsize=(6, 4))
    # We clip right-tail outliers for visualization clarity on skewed data
    limit_win = np.percentile(win_data, 99.5)
    limit_pi = np.percentile(pi_data, 99.5)
    max_plot_limit = max(limit_win, limit_pi)
    
    sns.histplot(data=df_win, x="Latency", kde=True, label="Windows 11 (x86-64)", color="blue", alpha=0.4, binrange=(0, max_plot_limit), bins=40)
    sns.histplot(data=df_pi, x="Latency", kde=True, label="Raspberry Pi 5 (ARM)", color="green", alpha=0.4, binrange=(0, max_plot_limit), bins=40)
    plt.xlabel("Latency (ms)")
    plt.ylabel("Count")
    plt.xlim(0, max_plot_limit)
    plt.title("Latency Probability Density Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_histogram_kde.png"))
    plt.close()
    
    # -------------------------------------------------------------
    # 3. Empirical Cumulative Distribution Function (ECDF)
    # -------------------------------------------------------------
    plt.figure(figsize=(6, 4))
    sns.ecdfplot(data=df_win, x="Latency", label="Windows 11 (x86-64)", color="blue", linewidth=1.5)
    sns.ecdfplot(data=df_pi, x="Latency", label="Raspberry Pi 5 (ARM)", color="green", linewidth=1.5)
    
    # Frame deadline line (30 FPS threshold = 33.3ms)
    deadline = 33.33
    plt.axvline(x=deadline, color="red", linestyle="--", linewidth=1.2, label="30 FPS Limit (33.3ms)")
    
    # Annotate probability under the curve
    p_under_win = np.mean(win_data <= deadline)
    p_under_pi = np.mean(pi_data <= deadline)
    
    plt.text(deadline + 1, 0.4, f"Win: {p_under_win:.2%}\nPi: {p_under_pi:.2%}", color="red", weight="bold")
    
    plt.xlabel("Latency (ms)")
    plt.ylabel("Cumulative Probability")
    plt.title("Empirical Cumulative Distribution Function (ECDF)")
    plt.legend(loc="lower right")
    plt.xlim(0, max(np.max(win_data), np.max(pi_data)) + 5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "latency_ecdf.png"))
    plt.close()
    
    print(f"\n[Info] High-resolution plots successfully written to: {output_dir}")

def run_mann_whitney(win_data, pi_data):
    """
    Runs the Mann-Whitney U statistical significance test (robust for right-skewed latencies).
    """
    stat, p_value = stats.mannwhitneyu(win_data, pi_data, alternative="two-sided")
    print("\n" + "="*80)
    print(f"{'STATISTICAL SIGNIFICANCE TESTING (MANN-WHITNEY U)':^80}")
    print("="*80)
    print(f"U-Statistic  : {stat:.1f}")
    print(f"p-value      : {p_value:.6e}")
    
    # Decision boundary
    alpha = 0.05
    if p_value < alpha:
        print("Conclusion   : Reject H0. The difference in latency distributions between Windows")
        print("               and the Raspberry Pi target is statistically significant (p < 0.05).")
    else:
        print("Conclusion   : Fail to reject H0. No statistically significant difference in latency")
        print("               distributions was detected (p >= 0.05).")
    print("="*80)

def main():
    parser = argparse.ArgumentParser(description="Standalone Telemetry Evaluation Script for IEEE Publications.")
    parser.add_argument("--win_log", type=str, default="test_results/raw_api_latency_dump.txt",
                        help="Path to Windows API latency log file.")
    parser.add_argument("--pi_log", type=str, default="test_results/raw_gesture_latency_dump.txt",
                        help="Path to Raspberry Pi gesture mutation log file.")
    parser.add_argument("--ai_log", type=str, default="test_results/raw_edge_ai_predictions_dump.txt",
                        help="Path to expected vs predicted hand gestures log file.")
    parser.add_argument("--plot_dir", type=str, default="test_results/plots",
                        help="Directory to export the generated graphs.")
    args = parser.parse_args()
    
    print(f"[Process] Loading Windows data from: {args.win_log}")
    win_warm, win_cold = parse_api_latencies(args.win_log)
    
    print(f"[Process] Loading Raspberry Pi data from: {args.pi_log}")
    pi_data = parse_gesture_latencies(args.pi_log)
    
    if win_warm is None or pi_data is None:
        print("[Error] Failed to ingest latency data. Ensure paths are correct.")
        return
        
    # Analyze Latency Datasets
    win_stats = compute_statistics(win_warm, "Windows")
    pi_stats = compute_statistics(pi_data, "Raspberry Pi")
    
    # Display Latinized Table
    print_statistics_table(win_stats, pi_stats)
    
    # Run Mann-Whitney U test
    run_mann_whitney(win_warm, pi_data)
    
    # Draw and Save Graphs
    make_plots(win_warm, pi_data, args.plot_dir)
    
    # AI Vision Reliability evaluation
    print(f"\n[Process] Loading AI Predictions from: {args.ai_log}")
    expected, predicted = parse_predictions(args.ai_log)
    if expected is not None and len(expected) > 0:
        compute_ai_metrics(expected, predicted)
    else:
        print("[Info] AI predictions dump empty or missing. Skipping reliability report.")

if __name__ == "__main__":
    main()
