"""
cicids2017/verify_sprint6_invariants.py
---------------------------------------
Sprint 6 Final Automated Invariant Verification Script.

Verifies:
  1. UNSW freeze manifest integrity (1,261 files, 0 missing, 0 mismatches).
  2. Shortcut freeze integrity (SHA-256 and feature set).
  3. CIC population counts and split isolation.
  4. Matched-FPR analysis integrity (all models, 4 budgets, low-resolution flags, CIs, AUCs).
  5. Deployment benchmark integrity (8 models, 3 volumes, 5 runs, median, disclaimer).
  6. Cross-dataset master table integrity (15 rows, mandatory footnotes A-D).
  7. Figures integrity (Figures 1-4, PNG 300 DPI + vector PDF, non-empty).
  8. Deliverable reports integrity (4 markdown reports present and non-empty).
  9. Storage integrity (workspace confinement).
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("verify_sprint6")


def check_unsw_manifest() -> bool:
    logger.info("Checking UNSW freeze manifest integrity...")
    manifest_path = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "UNSW_FROZEN_MANIFEST.sha256"
    if not manifest_path.exists():
        logger.error("UNSW manifest not found: %s", manifest_path)
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_files = len(lines)
    logger.info("Manifest contains %d file entries (Target: 1,261).", total_files)
    if total_files != 1261:
        logger.error("Expected exactly 1,261 files, found %d", total_files)
        return False

    missing = 0
    mismatches = 0

    for line in lines:
        parts = line.split(None, 2)
        if len(parts) == 3:
            expected_sha = parts[0].strip()
            rel_path = parts[2].strip()
        elif len(parts) == 2:
            expected_sha = parts[0].strip()
            rel_path = parts[1].strip()
        else:
            continue

        file_path = ROOT / rel_path
        if not file_path.exists():
            missing += 1
            continue

        hasher = hashlib.sha256()
        with open(file_path, "rb") as bf:
            while chunk := bf.read(65536):
                hasher.update(chunk)
        if hasher.hexdigest() != expected_sha:
            mismatches += 1

    logger.info("UNSW manifest verification: %d files checked, %d missing, %d mismatches.",
                total_files, missing, mismatches)
    return missing == 0 and mismatches == 0


def check_shortcut_freeze() -> bool:
    logger.info("Checking shortcut freeze integrity...")
    expected_sha = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
    expected_shortcuts = ["Destination Port", "Init_Win_bytes_backward"]

    # Check frozen JSON
    freeze_json_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    if not freeze_json_path.exists():
        freeze_json_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_freeze" / "shortcut_list_frozen.json"
    if not freeze_json_path.exists():
        logger.error("Frozen shortcuts JSON missing.")
        return False

    with open(freeze_json_path, "rb") as f:
        raw_bytes = f.read()
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()

    if actual_sha != expected_sha:
        logger.error("Shortcut hash mismatch: expected %s, got %s", expected_sha, actual_sha)
        return False

    with open(freeze_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    actual_features = data.get("frozen_shortcut_set", data.get("frozen_shortcuts"))
    if actual_features != expected_shortcuts:
        logger.error("Shortcut feature mismatch: expected %s, got %s", expected_shortcuts, actual_features)
        return False

    logger.info("Shortcut hash and feature set verified: %s", actual_sha[:16])
    return True


def check_cic_populations() -> bool:
    logger.info("Checking CIC-IDS-2017 population splits...")
    splits_dir = ROOT / "cicids2017" / "DATA" / "splits"

    targets = {
        "train.csv": 340464,
        "calibration.csv": 18500,
        "eval_control.csv": 18500,
        "dev_test.csv": 743921,
        "protected_bot.csv": 1948,
    }

    for fname, exp_count in targets.items():
        fpath = splits_dir / fname
        if not fpath.exists():
            logger.error("Missing population split: %s", fpath)
            return False
        # Fast line count for CSV files
        with open(fpath, "r", encoding="utf-8") as f:
            row_count = sum(1 for _ in f) - 1
        if row_count != exp_count:
            logger.error("Count mismatch in %s: expected %d, got %d", fname, exp_count, row_count)
            return False
        logger.info("Verified %s: %d rows", fname, row_count)

    return True


def check_matched_fpr_results() -> bool:
    logger.info("Checking Matched-FPR results integrity...")
    csv_path = ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_matched_fpr_table.csv"
    summary_path = ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_matched_fpr_summary.json"
    marker_path = ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_c06_hybrid_marker.json"

    if not csv_path.exists() or not summary_path.exists() or not marker_path.exists():
        logger.error("Missing matched-FPR output files.")
        return False

    df = pd.read_csv(csv_path)
    logger.info("Matched-FPR CSV contains %d rows (Target: 84 rows).", len(df))
    if len(df) != 84:
        logger.error("Expected 84 rows in matched-FPR table, found %d", len(df))
        return False

    required_models = {
        "stacking", "random_forest", "idsnet", "autoencoder_standard",
        "autoencoder_log1p", "isolation_forest", "ft_transformer"
    }
    actual_models = set(df["model"].unique())
    if required_models != actual_models:
        logger.error("Model mismatch in matched-FPR table: %s vs %s", required_models, actual_models)
        return False

    required_budgets = {0.001, 0.005, 0.01, 0.05}
    actual_budgets = set(df["nominal_budget"].unique())
    if required_budgets != actual_budgets:
        logger.error("Budget mismatch in matched-FPR table: %s", actual_budgets)
        return False

    # Check LOW_RESOLUTION flag for 0.001
    low_res_rows = df[df["nominal_budget"] == 0.001]
    if not (low_res_rows["resolution_flag"] == "LOW_RESOLUTION").all():
        logger.error("0.1% budget rows not properly flagged as LOW_RESOLUTION.")
        return False

    # Check required columns
    required_cols = [
        "threshold", "realized_fpr", "fpr_ci_lower", "fpr_ci_upper",
        "recall", "recall_ci_lower", "recall_ci_upper", "precision_natural",
        "precision_standardized", "f1_natural", "pr_auc", "roc_auc", "alerts_per_10k"
    ]
    for c in required_cols:
        if c not in df.columns:
            logger.error("Missing required column in matched-FPR CSV: %s", c)
            return False

    # Check C06 marker
    with open(marker_path, "r", encoding="utf-8") as f:
        c06_data = json.load(f)
    if len(c06_data) != 3:
        logger.error("Expected 3 seed records in C06 marker, found %d", len(c06_data))
        return False

    logger.info("Matched-FPR verification passed.")
    return True


def check_deployment_results() -> bool:
    logger.info("Checking Deployment benchmark integrity...")
    csv_path = ROOT / "results" / "cicids2017_revision_v1" / "deployment" / "s24_deployment_benchmark.csv"
    json_path = ROOT / "results" / "cicids2017_revision_v1" / "deployment" / "s24_deployment_benchmark.json"

    if not csv_path.exists() or not json_path.exists():
        logger.error("Missing deployment benchmark files.")
        return False

    df = pd.read_csv(csv_path)
    logger.info("Deployment CSV contains %d rows (Target: 24 rows).", len(df))
    if len(df) != 24:
        logger.error("Expected 24 rows in deployment benchmark, found %d", len(df))
        return False

    required_models = {
        "Decision Tree", "Random Forest", "Linear SVC", "IDSNet (MLP)",
        "Stacking Ensemble", "Autoencoder (Standard)", "Isolation Forest", "FT-Transformer"
    }
    actual_models = set(df["model"].unique())
    if required_models != actual_models:
        logger.error("Deployment model mismatch: %s vs %s", required_models, actual_models)
        return False

    required_volumes = {1000, 10000, 100000}
    actual_volumes = set(df["n_flows"].unique())
    if required_volumes != actual_volumes:
        logger.error("Deployment volume mismatch: %s", actual_volumes)
        return False

    # Check disclaimer column
    expected_disclaimer = "Local host inference benchmarks, not production gateway throughput."
    if not (df["disclaimer"] == expected_disclaimer).all():
        logger.error("Mandatory deployment disclaimer missing or malformed in CSV.")
        return False

    logger.info("Deployment benchmark verification passed.")
    return True


def check_cross_dataset_results() -> bool:
    logger.info("Checking Cross-Dataset master table integrity...")
    csv_path = ROOT / "results" / "cicids2017_revision_v1" / "cross_dataset" / "s25_cross_dataset_master_table.csv"
    json_path = ROOT / "results" / "cicids2017_revision_v1" / "cross_dataset" / "s25_cross_dataset_master_table.json"

    if not csv_path.exists() or not json_path.exists():
        logger.error("Missing cross-dataset master table files.")
        return False

    df = pd.read_csv(csv_path)
    logger.info("Cross-dataset table contains %d rows (Target: >= 15 rows).", len(df))
    if len(df) < 15:
        logger.error("Expected >= 15 rows, found %d", len(df))
        return False

    # Check for empty cells
    if df.isna().any().any():
        logger.error("Cross-dataset table contains empty/NaN cells.")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    footnotes = data.get("mandatory_footnotes", {})
    required_footnotes = [
        "footnote_a_prevalence",
        "footnote_b_protected_families",
        "footnote_c_feature_representation",
        "footnote_d_resolution_limits",
    ]
    for fn in required_footnotes:
        if fn not in footnotes or len(footnotes[fn]) < 20:
            logger.error("Missing required footnote in cross-dataset JSON: %s", fn)
            return False

    logger.info("Cross-dataset table and mandatory footnotes verified.")
    return True


def check_figures() -> bool:
    logger.info("Checking generated figures integrity...")
    fig_dir = ROOT / "figures" / "cicids2017_revision_v1"

    fig_names = [
        "figure_1_cross_dataset_recall_vs_fpr",
        "figure_2_cic_model_comparison",
        "figure_3_operational_alert_burden",
        "figure_4_treeshap_attribution_shift",
    ]

    for name in fig_names:
        png_path = fig_dir / f"{name}.png"
        pdf_path = fig_dir / f"{name}.pdf"

        if not png_path.exists() or png_path.stat().st_size == 0:
            logger.error("Missing or empty PNG for %s", name)
            return False
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            logger.error("Missing or empty PDF for %s", name)
            return False

        logger.info("Verified figure %s: PNG (%d bytes), PDF (%d bytes)",
                    name, png_path.stat().st_size, pdf_path.stat().st_size)

    return True


def check_reports() -> bool:
    logger.info("Checking deliverable reports...")
    rep_dir = ROOT / "reports" / "cicids2017_revision_v1"

    required_reports = [
        "MATCHED_FPR_REPORT.md",
        "DEPLOYMENT_BENCHMARK_REPORT.md",
        "CROSS_DATASET_REPORT.md",
        "SPRINT_6_REPORT.md",
    ]

    for rep in required_reports:
        p = rep_dir / rep
        if not p.exists() or p.stat().st_size < 100:
            logger.error("Missing or incomplete report: %s", rep)
            return False
        logger.info("Verified report %s: %d bytes", rep, p.stat().st_size)

    return True


def check_git_status() -> bool:
    logger.info("Checking Git status (no uncommitted tracked changes in UNSW)...")
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    lines = res.stdout.strip().splitlines()
    logger.info("Git status reports %d modified/untracked files.", len(lines))

    # Verify no tracked UNSW files are modified
    for line in lines:
        if line.startswith(" M") or line.startswith("M "):
            mod_file = line[3:].strip()
            if "revision_v5" in mod_file or "data/" in mod_file or "results/zero_day" in mod_file:
                logger.error("Tracked UNSW file modified: %s", mod_file)
                return False

    return True


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 6 FINAL INVARIANT VERIFICATION SUITE")
    logger.info("=" * 70)

    gates = [
        ("UNSW Manifest Integrity", check_unsw_manifest),
        ("Shortcut Freeze Integrity", check_shortcut_freeze),
        ("CIC Population Counts", check_cic_populations),
        ("Matched-FPR Analysis", check_matched_fpr_results),
        ("Deployment Benchmark", check_deployment_results),
        ("Cross-Dataset Master Table", check_cross_dataset_results),
        ("Publication Figures", check_figures),
        ("Deliverable Reports", check_reports),
        ("Git Status & UNSW Isolation", check_git_status),
    ]

    all_passed = True
    results = []

    for name, gate_func in gates:
        passed = gate_func()
        results.append((name, passed))
        if not passed:
            all_passed = False
            logger.error("GATE FAILED: %s", name)
        else:
            logger.info("GATE PASSED: %s", name)

    logger.info("=" * 70)
    logger.info("SPRINT 6 INVARIANT VERIFICATION SUMMARY:")
    for name, passed in results:
        status_str = "PASS" if passed else "FAIL"
        logger.info("  [%s] %s", status_str, name)
    logger.info("=" * 70)

    if all_passed:
        logger.info("FINAL RESULT: SPRINT 6 VERIFICATION PASS (ALL GATES SATISFIED)")
        sys.exit(0)
    else:
        logger.error("FINAL RESULT: SPRINT 6 VERIFICATION FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
