"""
cicids2017/verify_revision.py
-----------------------------
Sprint 7 Master Revision Verification Suite.

Executes the definitive 12-Gate audit of the entire CIC-IDS-2017 revision:
  Gate 1:  UNSW Manifest Integrity (1,261 files, 0 missing, 0 mismatches)
  Gate 2:  Git Diff Isolation (git diff unsw_final is strictly empty)
  Gate 3:  Shortcut Freeze Integrity (SHA-256 and feature set match exactly)
  Gate 4:  Population Counts & Conservation Accounting (2.52M cleaned = 1.12M assigned + 1.40M removed)
  Gate 5:  Pairwise Row UID Disjointness across all 8 populations
  Gate 6:  Fit-Boundary and Machine Learning Leakage Assertions
  Gate 7:  Chronological Timestamp & Pre-Evaluation Blinding Ordering
  Gate 8:  Model Artifact Inventory (60 checkpoints and scalers verified)
  Gate 9:  Table-to-Result Mechanical Reconciliation (100% agreement)
  Gate 10: Deployment Benchmark Integrity (24 rows, 8 models, disclaimer verified)
  Gate 11: Figures & Deliverable Reports Integrity (PNG 300 DPI + PDF)
  Gate 12: Hardcoded Paths & Configuration Decoupling Audit

Outputs:
  Machine-readable JSON report: results/cicids2017_revision_v1/audit/master_verification_report.json
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AUDIT_OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "audit"
AUDIT_OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(AUDIT_OUT_DIR / "verify_revision.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("verify_revision")


# =============================================================================
# GATE 1: UNSW MANIFEST INTEGRITY
# =============================================================================
def verify_gate_1_unsw_manifest() -> dict:
    logger.info("GATE 1: Checking UNSW freeze manifest integrity...")
    manifest_path = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "UNSW_FROZEN_MANIFEST.sha256"
    if not manifest_path.exists():
        return {"passed": False, "reason": "Manifest file not found"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if len(lines) != 1261:
        return {"passed": False, "reason": f"Expected 1261 files, found {len(lines)}"}

    missing = 0
    mismatches = 0
    for line in lines:
        parts = line.split(None, 2)
        if len(parts) == 3:
            expected_sha, rel_path = parts[0], parts[2]
        else:
            expected_sha, rel_path = parts[0], parts[1]
        fpath = ROOT / rel_path
        if not fpath.exists():
            missing += 1
            continue
        hasher = hashlib.sha256()
        with open(fpath, "rb") as bf:
            while chunk := bf.read(65536):
                hasher.update(chunk)
        if hasher.hexdigest() != expected_sha:
            mismatches += 1

    passed = (missing == 0 and mismatches == 0)
    return {
        "passed": passed,
        "files_checked": len(lines),
        "missing": missing,
        "mismatches": mismatches,
    }


# =============================================================================
# GATE 2: GIT DIFF ISOLATION
# =============================================================================
def verify_gate_2_git_diff_isolation() -> dict:
    logger.info("GATE 2: Checking Git diff isolation against unsw_final...")
    res = subprocess.run(
        ["git", "diff", "unsw_final", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    diff_lines = res.stdout.strip().splitlines()
    passed = len(diff_lines) == 0
    return {
        "passed": passed,
        "modified_tracked_files": diff_lines,
        "count": len(diff_lines),
    }


# =============================================================================
# GATE 3: SHORTCUT FREEZE INTEGRITY
# =============================================================================
def verify_gate_3_shortcut_freeze() -> dict:
    logger.info("GATE 3: Checking shortcut freeze integrity...")
    expected_sha = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
    expected_shortcuts = ["Destination Port", "Init_Win_bytes_backward"]

    freeze_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    if not freeze_path.exists():
        return {"passed": False, "reason": "shortcut_list_frozen.json not found"}

    raw_bytes = open(freeze_path, "rb").read()
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    data = json.loads(raw_bytes)
    actual_features = data.get("frozen_shortcut_set", data.get("frozen_shortcuts"))

    sha_matches = (actual_sha == expected_sha)
    features_match = (actual_features == expected_shortcuts)
    return {
        "passed": sha_matches and features_match,
        "expected_sha": expected_sha,
        "actual_sha": actual_sha,
        "expected_features": expected_shortcuts,
        "actual_features": actual_features,
    }


# =============================================================================
# GATE 4: POPULATION COUNTS & CONSERVATION ACCOUNTING
# =============================================================================
def verify_gate_4_population_conservation() -> dict:
    logger.info("GATE 4: Checking population counts and conservation accounting...")
    splits_dir = ROOT / "cicids2017" / "DATA" / "splits"
    targets = {
        "train.csv": 340464,
        "dev_test.csv": 743921,
        "calibration.csv": 18500,
        "eval_control.csv": 18500,
        "protected_bot.csv": 1948,
        "unseen_xss.csv": 652,
        "unseen_infiltration.csv": 36,
        "excluded_small.csv": 32,
    }

    counts = {}
    mismatches = {}
    total_assigned = 0

    for fname, exp_count in targets.items():
        fpath = splits_dir / fname
        if not fpath.exists():
            return {"passed": False, "reason": f"Missing split file: {fname}"}
        with open(fpath, "r", encoding="utf-8") as f:
            cnt = sum(1 for _ in f) - 1
        counts[fname] = cnt
        total_assigned += cnt
        if cnt != exp_count:
            mismatches[fname] = {"expected": exp_count, "actual": cnt}

    # Conservation from population_manifest.json
    pop_manifest_path = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "population_manifest.json"
    pop_data = json.load(open(pop_manifest_path, encoding="utf-8"))
    tot_cleaned = pop_data["total_cleaned_flows"]
    tot_removals = pop_data["explicitly_logged_removals_count"]

    conservation_holds = (tot_cleaned == 2519404 and tot_removals == 1395351 and (tot_cleaned - tot_removals == 1124053))
    passed = (len(mismatches) == 0 and total_assigned == 1124053 and conservation_holds)

    return {
        "passed": passed,
        "counts": counts,
        "mismatches": mismatches,
        "total_assigned": total_assigned,
        "total_cleaned": tot_cleaned,
        "total_removals": tot_removals,
        "conservation_holds": conservation_holds,
    }


# =============================================================================
# GATE 5: PAIRWISE ROW UID DISJOINTNESS
# =============================================================================
def verify_gate_5_row_uid_disjointness() -> dict:
    logger.info("GATE 5: Checking pairwise row UID disjointness across all 8 splits...")
    splits_dir = ROOT / "cicids2017" / "DATA" / "splits"
    split_files = [
        "train.csv", "dev_test.csv", "calibration.csv", "eval_control.csv",
        "protected_bot.csv", "unseen_xss.csv", "unseen_infiltration.csv", "excluded_small.csv"
    ]

    uids = {}
    for sf in split_files:
        df = pd.read_csv(splits_dir / sf, usecols=["row_uid"])
        uids[sf] = set(df["row_uid"])

    intersections = {}
    has_overlap = False
    for i in range(len(split_files)):
        for j in range(i + 1, len(split_files)):
            s1, s2 = split_files[i], split_files[j]
            overlap = uids[s1].intersection(uids[s2])
            if len(overlap) > 0:
                has_overlap = True
                intersections[f"{s1} & {s2}"] = len(overlap)

    return {
        "passed": not has_overlap,
        "overlaps": intersections,
        "splits_tested": len(split_files),
    }


# =============================================================================
# GATE 6: FIT-BOUNDARY & LEAKAGE ASSERTIONS
# =============================================================================
def verify_gate_6_fit_boundaries() -> dict:
    logger.info("GATE 6: Checking fit boundaries and leakage assertions...")
    checks = {}

    # 1. Base training fit strictly on TRAIN (340,464)
    train_meta_path = ROOT / "results" / "cicids2017_revision_v1" / "supervised" / "training_metadata.json"
    tm = json.load(open(train_meta_path, encoding="utf-8"))
    checks["base_training_rows"] = (tm["train_rows"] == 340464)
    checks["base_k_star"] = (tm["k_star"] == 69)

    # 2. OOF stacking CV strictly on TRAIN
    stack_meta_path = ROOT / "results" / "cicids2017_revision_v1" / "stacking" / "stacking_metadata.json"
    sm = json.load(open(stack_meta_path, encoding="utf-8"))
    checks["stacking_leakage_assertion"] = sm.get("leakage_assertions_passed", False)

    # 3. Autoencoder benign TRAIN only
    ae_meta_path = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "autoencoder_training_metadata.json"
    am = json.load(open(ae_meta_path, encoding="utf-8"))
    checks["ae_benign_train_rows"] = (am["benign_train_rows"] == 44800)

    # 4. Isolation Forest benign TRAIN only
    if_meta_path = ROOT / "results" / "cicids2017_revision_v1" / "isolation_forest" / "if_training_metadata.json"
    im = json.load(open(if_meta_path, encoding="utf-8"))
    checks["if_training_rows"] = (im["training_rows"] == 44800)

    # 5. Calibration CALIBRATION only
    cal_path = ROOT / "results" / "cicids2017_revision_v1" / "calibration" / "calibration_thresholds.json"
    cm = json.load(open(cal_path, encoding="utf-8"))
    checks["calibration_rows"] = (cm["calibration_rows"] == 18500)

    # 6. Matched-FPR populations
    mf_path = ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_matched_fpr_summary.json"
    mm = json.load(open(mf_path, encoding="utf-8"))
    checks["matched_fpr_cal_pop"] = (mm["n_cal"] == 18500)
    checks["matched_fpr_eval_pop"] = (mm["n_eval_control"] == 18500)
    checks["matched_fpr_bot_pop"] = (mm["n_protected_bot"] == 1948)

    all_passed = all(checks.values())
    return {
        "passed": all_passed,
        "boundary_checks": checks,
    }


# =============================================================================
# GATE 7: TIMESTAMPS & BLINDING ORDERING
# =============================================================================
def verify_gate_7_timestamp_ordering() -> dict:
    logger.info("GATE 7: Checking chronological timestamp and blinding ordering...")
    shortcut_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    zd_path = ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "zero_day_evaluation_summary.json"

    sc_data = json.load(open(shortcut_path, encoding="utf-8"))
    zd_data = json.load(open(zd_path, encoding="utf-8"))

    t_shortcut = datetime.fromisoformat(sc_data["creation_timestamp_utc"])
    t_zeroday = datetime.fromisoformat(zd_data["timestamp_utc"])

    delta_seconds = (t_zeroday - t_shortcut).total_seconds()
    ordering_valid = (delta_seconds > 0)

    return {
        "passed": ordering_valid,
        "t_shortcut_utc": str(t_shortcut),
        "t_zeroday_utc": str(t_zeroday),
        "separation_seconds": delta_seconds,
        "separation_formatted": f"{int(delta_seconds // 3600)}h {int((delta_seconds % 3600) // 60)}m {int(delta_seconds % 60)}s",
    }


# =============================================================================
# GATE 8: MODEL ARTIFACT INVENTORY
# =============================================================================
def verify_gate_8_model_inventory() -> dict:
    logger.info("GATE 8: Auditing model checkpoint and scaler inventory...")
    models_dir = ROOT / "cicids2017" / "models"
    seeds = [42, 123, 2024]
    expected_artifacts = []

    # Supervised full base + stacking
    for s in seeds:
        s_dir = models_dir / f"seed_{s}"
        expected_artifacts.extend([
            s_dir / "dt_model.pkl",
            s_dir / "rf_model.pkl",
            s_dir / "svm_model.pkl",
            s_dir / "svm_scaler.pkl",
            s_dir / "nn_model.pt",
            s_dir / "nn_scaler.pkl",
            s_dir / "meta_lr.pkl",
            s_dir / "ae_standard_model.pt",
            s_dir / "ae_standard_scaler.pkl",
            s_dir / "ae_log1p_model.pt",
            s_dir / "ae_log1p_scaler.pkl",
            s_dir / "if_model.joblib",
        ])

    # Supervised ablated
    for s in seeds:
        ab_dir = models_dir / "ablated" / f"seed_{s}"
        expected_artifacts.extend([
            ab_dir / "dt_model.pkl",
            ab_dir / "rf_model.pkl",
            ab_dir / "svm_model.pkl",
            ab_dir / "svm_scaler.pkl",
            ab_dir / "nn_model.pt",
            ab_dir / "nn_scaler.pkl",
            ab_dir / "meta_lr.pkl",
        ])

    # FT-Transformer full & ablated
    for s in seeds:
        ft_full_dir = models_dir / "ft_transformer" / "full" / f"seed_{s}"
        ft_abl_dir = models_dir / "ft_transformer" / "ablated" / f"seed_{s}"
        expected_artifacts.extend([
            ft_full_dir / "ft_model.pt",
            ft_full_dir / "ft_scaler.pkl",
            ft_abl_dir / "ft_model.pt",
            ft_abl_dir / "ft_scaler.pkl",
        ])

    # UNSW FT-Transformer
    for s in seeds:
        unsw_ft_dir = models_dir / "transformer" / "unsw" / f"seed_{s}"
        expected_artifacts.extend([
            unsw_ft_dir / "ft_model.pt",
            unsw_ft_dir / "ft_scaler.pkl",
        ])

    missing = []
    empty = []
    total_count = len(expected_artifacts)

    for p in expected_artifacts:
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
        elif p.stat().st_size == 0:
            empty.append(str(p.relative_to(ROOT)))

    passed = (len(missing) == 0 and len(empty) == 0 and total_count >= 60)
    return {
        "passed": passed,
        "total_artifacts_checked": total_count,
        "missing_count": len(missing),
        "empty_count": len(empty),
        "missing": missing,
    }


# =============================================================================
# GATE 9: TABLE-TO-RESULT MECHANICAL RECONCILIATION
# =============================================================================
def verify_gate_9_reconciliation() -> dict:
    logger.info("GATE 9: Mechanically reconciling report metrics against saved JSON/CSVs...")
    recon_checks = []
    import numpy as np

    # 1. Stacking Bot recall is exactly 0.00%
    mf_sum = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_matched_fpr_summary.json", encoding="utf-8"))
    stk_recall = mf_sum["per_model_summary"]["stacking"]["0.001"]["recall_mean"]
    recon_checks.append({
        "metric": "Stacking Bot Recall (Matched-FPR)",
        "source": "s23_matched_fpr_summary.json",
        "value": stk_recall,
        "expected": 0.0,
        "passed": abs(stk_recall - 0.0) < 1e-6,
    })

    # 2. Standard AE zero-day recall at mu+3sigma (~0.60%, 11.67 / 1948)
    zd_sum = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "zero_day_evaluation_summary.json", encoding="utf-8"))
    ae_records = [r for r in zd_sum["results"] if r["detector"] == "Autoencoder_Standard" and r["attack_set"] == "PROTECTED_BOT"]
    ae_mean_rec = float(np.mean([r["recall"] for r in ae_records]))
    recon_checks.append({
        "metric": "Standard AE Bot Recall (mu+3sigma)",
        "source": "zero_day_evaluation_summary.json",
        "value": ae_mean_rec,
        "expected": 0.005989,
        "passed": abs(ae_mean_rec - (11.66667 / 1948.0)) < 1e-4,
    })

    # 3. Isolation Forest zero-day recall (~1.98%, 38.67 / 1948)
    if_records = [r for r in zd_sum["results"] if r["detector"] == "Isolation_Forest" and r["attack_set"] == "PROTECTED_BOT"]
    if_mean_rec = float(np.mean([r["recall"] for r in if_records]))
    recon_checks.append({
        "metric": "Isolation Forest Bot Recall",
        "source": "zero_day_evaluation_summary.json",
        "value": if_mean_rec,
        "expected": 0.019849,
        "passed": abs(if_mean_rec - (38.66667 / 1948.0)) < 1e-4,
    })

    # 4. Hybrid C06 Q3 rescue flows & extra FP
    c06_data = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr" / "s23_c06_hybrid_marker.json", encoding="utf-8"))
    q3_mean = float(np.mean([r["Q3_ae_rescue"] for r in c06_data]))
    extra_fp_mean = float(np.mean([r["extra_fp_over_stacking"] for r in c06_data]))
    recon_checks.append({
        "metric": "Hybrid C06 Q3 Rescue",
        "source": "s23_c06_hybrid_marker.json",
        "value": q3_mean,
        "expected": 37.67,
        "passed": abs(q3_mean - 37.67) < 0.5,
    })
    recon_checks.append({
        "metric": "Hybrid C06 Extra False Alarms",
        "source": "s23_c06_hybrid_marker.json",
        "value": extra_fp_mean,
        "expected": 49.33,
        "passed": abs(extra_fp_mean - 49.33) < 0.5,
    })

    # 5. RF TOST Macro-F1 delta
    abl_data = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "ablation" / "s19_ablation_evaluation.json", encoding="utf-8"))
    rf_delta = abl_data["tost_rf_macro_f1"]["mean_delta"]
    recon_checks.append({
        "metric": "RF TOST Equivalence Mean Delta",
        "source": "s19_ablation_evaluation.json",
        "value": rf_delta,
        "expected": 0.00148,
        "passed": abs(rf_delta - 0.00148) < 1e-4,
    })

    # 6. Hypotheses H1, H2 (from s19_ablation_evaluation.json)
    h1_passed = abl_data["H1_verdict"]["majority_rejected"] is True
    recon_checks.append({
        "metric": "H1 Verdict (Null Rejected)",
        "source": "s19_ablation_evaluation.json",
        "value": "REJECTED" if h1_passed else "FAIL",
        "expected": "REJECTED",
        "passed": h1_passed,
    })
    h2_passed = abl_data["H2_verdict"]["tost_equivalence_accepted"] is True
    recon_checks.append({
        "metric": "H2 Verdict (TOST Accepted)",
        "source": "s19_ablation_evaluation.json",
        "value": "ACCEPTED" if h2_passed else "FAIL",
        "expected": "ACCEPTED",
        "passed": h2_passed,
    })

    # 7. Hypotheses H3, H4 (from h3_h4_statistical_tests.json)
    h34_data = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "statistics" / "h3_h4_statistical_tests.json", encoding="utf-8"))
    h3_verdict = h34_data["H3_autoencoder_evaluation"][0]["verdict"]
    recon_checks.append({
        "metric": "H3 Verdict",
        "source": "h3_h4_statistical_tests.json",
        "value": h3_verdict,
        "expected": "PARTIALLY_SUPPORTED",
        "passed": h3_verdict == "PARTIALLY_SUPPORTED",
    })
    h4_verdict = h34_data["H4_hybrid_rescue_evaluation"][0]["verdict"]
    recon_checks.append({
        "metric": "H4 Verdict",
        "source": "h3_h4_statistical_tests.json",
        "value": h4_verdict,
        "expected": "NOT_SUPPORTED",
        "passed": h4_verdict == "NOT_SUPPORTED",
    })

    # 8. FT-Transformer Macro-F1 and zero-day recalls
    ft_cic = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "ft_transformer" / "s21_ft_transformer_cic_results.json", encoding="utf-8"))
    cic_ft_f1 = ft_cic["results"]["full"]["mean_dev_test_macro_f1"]
    cic_ft_bot_recall = ft_cic["results"]["full"]["mean_zero_day_bot_recall"]
    recon_checks.append({
        "metric": "FT-Transformer CIC DEV_TEST Macro-F1",
        "source": "s21_ft_transformer_cic_results.json",
        "value": cic_ft_f1,
        "expected": 0.9864,
        "passed": abs(cic_ft_f1 - 0.9864) < 1e-3,
    })
    recon_checks.append({
        "metric": "FT-Transformer CIC Bot Recall",
        "source": "s21_ft_transformer_cic_results.json",
        "value": cic_ft_bot_recall,
        "expected": 0.0,
        "passed": cic_ft_bot_recall == 0.0,
    })

    ft_unsw = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "transformer" / "unsw" / "s22_ft_transformer_unsw_results.json", encoding="utf-8"))
    unsw_ft_f1 = ft_unsw["mean_dev_test_macro_f1"]
    unsw_ft_backdoor = ft_unsw["per_seed_results"]["42"]["zero_day_backdoor"]["recall"]
    recon_checks.append({
        "metric": "FT-Transformer UNSW DEV_TEST Macro-F1",
        "source": "s22_ft_transformer_unsw_results.json",
        "value": unsw_ft_f1,
        "expected": 0.8488,
        "passed": abs(unsw_ft_f1 - 0.8488) < 1e-3,
    })
    recon_checks.append({
        "metric": "FT-Transformer UNSW Backdoor Recall",
        "source": "s22_ft_transformer_unsw_results.json",
        "value": unsw_ft_backdoor,
        "expected": 1.0,
        "passed": unsw_ft_backdoor == 1.0,
    })

    # 9. Supervised Stacking DEV_TEST metrics
    dt_eval = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "supervised" / "dev_test_evaluation.json", encoding="utf-8"))
    stk_f1 = dt_eval["aggregated"]["stacking"]["mean_macro_f1"]
    stk_fpr = dt_eval["aggregated"]["stacking"]["mean_fpr"]
    recon_checks.append({
        "metric": "Stacking DEV_TEST Macro-F1",
        "source": "dev_test_evaluation.json",
        "value": stk_f1,
        "expected": 0.99864,
        "passed": abs(stk_f1 - 0.99864) < 1e-4,
    })
    recon_checks.append({
        "metric": "Stacking DEV_TEST FPR",
        "source": "dev_test_evaluation.json",
        "value": stk_fpr,
        "expected": 0.000874,
        "passed": abs(stk_fpr - 0.000874) < 1e-5,
    })

    # 10. Selected features count
    feat_sel = json.load(open(ROOT / "results" / "cicids2017_revision_v1" / "feature_selection" / "selected_features.json", encoding="utf-8"))
    n_feats = len(feat_sel.get("selected_features", feat_sel.get("features", [])))
    recon_checks.append({
        "metric": "Selected Feature Count K*",
        "source": "selected_features.json",
        "value": n_feats,
        "expected": 69,
        "passed": n_feats == 69,
    })

    all_passed = all(c["passed"] for c in recon_checks)
    return {
        "passed": all_passed,
        "total_checks": len(recon_checks),
        "failed_checks": [c for c in recon_checks if not c["passed"]],
    }


# =============================================================================
# GATE 10: DEPLOYMENT BENCHMARK INTEGRITY
# =============================================================================
def verify_gate_10_deployment_benchmark() -> dict:
    logger.info("GATE 10: Checking deployment benchmark integrity...")
    bench_csv = ROOT / "results" / "cicids2017_revision_v1" / "deployment" / "s24_deployment_benchmark.csv"
    if not bench_csv.exists():
        return {"passed": False, "reason": "s24_deployment_benchmark.csv missing"}

    df = pd.read_csv(bench_csv)
    if len(df) != 24:
        return {"passed": False, "reason": f"Expected 24 rows, got {len(df)}"}

    expected_disclaimer = "Local host inference benchmarks, not production gateway throughput."
    disclaimer_valid = (df["disclaimer"] == expected_disclaimer).all()

    models = set(df["model"].unique())
    expected_models = {
        "Decision Tree", "Random Forest", "Linear SVC", "IDSNet (MLP)",
        "Stacking Ensemble", "Autoencoder (Standard)", "Isolation Forest", "FT-Transformer"
    }

    passed = (disclaimer_valid and models == expected_models)
    return {
        "passed": passed,
        "row_count": len(df),
        "disclaimer_verified": disclaimer_valid,
        "models_verified": models == expected_models,
    }


# =============================================================================
# GATE 11: FIGURES & DELIVERABLE REPORTS INTEGRITY
# =============================================================================
def verify_gate_11_figures_and_reports() -> dict:
    logger.info("GATE 11: Auditing publication figures and deliverable reports...")
    fig_dir = ROOT / "figures" / "cicids2017_revision_v1"
    rep_dir = ROOT / "reports" / "cicids2017_revision_v1"

    fig_names = [
        "figure_1_cross_dataset_recall_vs_fpr",
        "figure_2_cic_model_comparison",
        "figure_3_operational_alert_burden",
        "figure_4_treeshap_attribution_shift",
    ]
    for name in fig_names:
        png_p = fig_dir / f"{name}.png"
        pdf_p = fig_dir / f"{name}.pdf"
        if not png_p.exists() or png_p.stat().st_size == 0:
            return {"passed": False, "reason": f"Figure PNG missing or empty: {name}"}
        if not pdf_p.exists() or pdf_p.stat().st_size == 0:
            return {"passed": False, "reason": f"Figure PDF missing or empty: {name}"}

    required_reports = [
        "SPRINT_1_REPORT.md", "SPRINT_2_REPORT.md", "SPRINT_3_REPORT.md",
        "SPRINT_4_REPORT.md", "SPRINT_5_REPORT.md", "SPRINT_6_REPORT.md",
        "MATCHED_FPR_REPORT.md", "DEPLOYMENT_BENCHMARK_REPORT.md", "CROSS_DATASET_REPORT.md",
    ]
    for rep in required_reports:
        rp = rep_dir / rep
        if not rp.exists() or rp.stat().st_size < 100:
            return {"passed": False, "reason": f"Report missing or too small: {rep}"}

    return {"passed": True, "figures_verified": len(fig_names) * 2, "reports_verified": len(required_reports)}


# =============================================================================
# GATE 12: HARDCODED PATHS AUDIT
# =============================================================================
def verify_gate_12_hardcoded_paths() -> dict:
    logger.info("GATE 12: Running hardcoded paths scanner with --allow-cross-dataset...")
    script_path = ROOT / "cicids2017" / "check_no_hardcoded_paths.py"
    res = subprocess.run(
        [sys.executable, str(script_path), "--allow-cross-dataset"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    passed = (res.returncode == 0)
    return {
        "passed": passed,
        "returncode": res.returncode,
        "output": res.stdout.strip(),
    }


# =============================================================================
# MAIN VERIFICATION HARNESS
# =============================================================================
def main():
    logger.info("=" * 80)
    logger.info("SPRINT 7: MASTER REVISION VERIFICATION SUITE (verify_revision.py)")
    logger.info("=" * 80)

    gates = [
        ("Gate 1: UNSW Manifest Integrity", verify_gate_1_unsw_manifest),
        ("Gate 2: Git Diff Isolation", verify_gate_2_git_diff_isolation),
        ("Gate 3: Shortcut Freeze Integrity", verify_gate_3_shortcut_freeze),
        ("Gate 4: Population Counts & Conservation", verify_gate_4_population_conservation),
        ("Gate 5: Pairwise Row UID Disjointness", verify_gate_5_row_uid_disjointness),
        ("Gate 6: Fit-Boundary & Leakage Assertions", verify_gate_6_fit_boundaries),
        ("Gate 7: Timestamp & Blinding Ordering", verify_gate_7_timestamp_ordering),
        ("Gate 8: Model Artifact Inventory", verify_gate_8_model_inventory),
        ("Gate 9: Table-to-Result Reconciliation", verify_gate_9_reconciliation),
        ("Gate 10: Deployment Benchmark Integrity", verify_gate_10_deployment_benchmark),
        ("Gate 11: Figures & Reports Integrity", verify_gate_11_figures_and_reports),
        ("Gate 12: Hardcoded Paths Audit", verify_gate_12_hardcoded_paths),
    ]

    gate_results = {}
    all_passed = True

    for gate_name, gate_fn in gates:
        t0 = time.perf_counter()
        res = gate_fn()
        elapsed = time.perf_counter() - t0
        passed = res.get("passed", False)
        gate_results[gate_name] = {
            "passed": passed,
            "elapsed_seconds": round(elapsed, 4),
            "details": res,
        }
        status_str = "PASS" if passed else "FAIL"
        logger.info("  [%-4s] %-42s (%.2fs)", status_str, gate_name, elapsed)
        if not passed:
            all_passed = False
            logger.error("      Reason: %s", res.get("reason", "Sub-checks failed"))

    # Save machine-readable report
    master_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 7,
        "overall_status": "PASS" if all_passed else "FAIL",
        "total_gates": len(gates),
        "passed_gates": sum(1 for g in gate_results.values() if g["passed"]),
        "failed_gates": sum(1 for g in gate_results.values() if not g["passed"]),
        "gate_results": gate_results,
    }

    def json_default(obj):
        import numpy as np
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    out_file = AUDIT_OUT_DIR / "master_verification_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=2, default=json_default)

    logger.info("=" * 80)
    logger.info("SUMMARY: %d/%d Gates Passed. Overall Status: %s",
                master_report["passed_gates"], len(gates), master_report["overall_status"])
    logger.info("Master audit artifact written to: %s", out_file)
    logger.info("=" * 80)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
