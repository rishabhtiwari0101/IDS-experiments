#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_ae_threshold_ablation.py
-------------------------------------------------------------------------
Phase 4 / Analysis B4: AE Threshold Ablation (S6).
Blueprint reference: SS16 (S6), SS18 Gate 4.

Key protocol requirements:
1. Zero-Training Guard: purely evaluation -- no ML fitting, tuning, or recomputation
   of thresholds. Thresholds are loaded verbatim from EXP_MAD_THRESHOLD_V1/
   mad_threshold.json (output of S5).
2. Detection Rule: strict > (score strictly greater than threshold).
3. Populations evaluated:
   a. Tier B eval half (EVAL_CONTROL, N=18,500) -- benign, computes AE FPR per rule.
   b. Full benign control (N=37,000) -- supplementary FPR.
   c. Zero-day Backdoor (N=583) -- AE recall per rule.
   d. Unseen families (Worms/Shellcode/Analysis, N=1,099) -- AE recall per rule
      and per attack_cat.
4. Exact Arithmetic: FPR/recall computed as exact rational fractions (Fraction) and
   floats; Clopper-Pearson 95% CIs via scipy.stats.beta.
5. Frozen-Run Assertion: mean_plus_3sigma must produce exactly 0 Backdoor
   detections and exactly 19 control FPs across the full 37,000 benign control.
   Script raises AssertionError immediately if violated.
6. Strict output directory: revision_v5/results/publication_experiments/
   EXP_AE_ABLATION_V1/
   - ae_ablation_results.csv
   - ae_ablation_results_unseen.csv
   - self_check.json
   - metadata.json
"""

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import scipy.stats


# START_ZERO_TRAINING_GUARD_DEFINITION
PROHIBITED_PATTERNS = [
    "fit_" + "transform",
    "import " + "shap",
    "torch." + "optim",
    "." + "backward()",
    "model." + "train()",
    "Grid" + "Search",
    "Randomized" + "Search",
    "." + "fit(",
]


def execute_zero_training_guard(script_path: Path) -> None:
    """Verify that this analysis script contains no prohibited ML training/tuning calls."""
    if not script_path.exists():
        return
    src = script_path.read_text(encoding="utf-8")
    in_guard_def = False
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if "# START_ZERO_TRAINING_GUARD_DEFINITION" in stripped:
            in_guard_def = True
            continue
        if "# END_ZERO_TRAINING_GUARD_DEFINITION" in stripped:
            in_guard_def = False
            continue
        if in_guard_def or stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.endswith('"""') or stripped == '"""':
            continue
        for pattern in PROHIBITED_PATTERNS:
            if pattern in line:
                raise RuntimeError(
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern {pattern!r} "
                    f"found at line {i} of {script_path}: {stripped}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


# ---------------------------------------------------------------------------
# Setup Paths and Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_ae_threshold_ablation")


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "data" / "splits").exists() and (current / "results").exists():
            return current
        current = current.parent
    return Path.cwd()


REPO_ROOT = find_repo_root()
NEW_ROOT = REPO_ROOT / "revision_v5"


def resolve_path(rel_path: str) -> Path:
    p1 = NEW_ROOT / rel_path
    if p1.exists():
        return p1
    p2 = REPO_ROOT / rel_path
    if p2.exists():
        return p2
    return p1


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def clopper_pearson_95(k: int, n: int) -> Tuple[float, float]:
    """Exact Clopper-Pearson 95% CI for k successes out of n trials."""
    alpha = 0.05
    lo = float(scipy.stats.beta.ppf(alpha / 2, k, n - k + 1)) if k > 0 else 0.0
    hi = float(scipy.stats.beta.ppf(1 - alpha / 2, k + 1, n - k)) if k < n else 1.0
    return lo, hi


# ---------------------------------------------------------------------------
# Core Evaluation Helper
# ---------------------------------------------------------------------------

def evaluate_population(
    re_vector: np.ndarray,
    n_expected: int,
    pop_label: str,
    thresholds: Dict[str, Any],
    is_attack: bool,
) -> List[Dict[str, Any]]:
    """
    Apply all thresholds (strict >) to re_vector; return one dict per threshold.

    Parameters
    ----------
    re_vector  : 1-D float array of reconstruction errors.
    n_expected : expected number of rows; raises AssertionError if mismatched.
    pop_label  : population name for output column.
    thresholds : dict of {rule_name: rule_info} loaded from mad_threshold.json.
    is_attack  : if True, metric column is "recall"; if False, "fpr".
    """
    n = len(re_vector)
    if n != n_expected:
        raise AssertionError(
            f"Population {pop_label!r}: expected {n_expected} rows, got {n}."
        )
    if np.isnan(re_vector).any():
        raise AssertionError(f"NaN in RE vector for population {pop_label!r}.")
    if np.isinf(re_vector).any():
        raise AssertionError(f"Inf in RE vector for population {pop_label!r}.")

    metric_name = "recall" if is_attack else "fpr"
    rows = []
    for rule_name, rule_info in thresholds.items():
        t = float(rule_info["threshold_value"])
        detections = int((re_vector > t).sum())  # strict > per blueprint SS16
        rate_float = float(detections / n)
        rate_frac = Fraction(detections, n)
        ci_lo, ci_hi = clopper_pearson_95(detections, n)
        rows.append({
            "population": pop_label,
            "rule_name": rule_name,
            "category": rule_info.get("category", "unknown"),
            "threshold_value": t,
            "n_total": n,
            "n_detected": detections,
            "metric": metric_name,
            "rate": rate_float,
            "rate_fraction": str(rate_frac),
            "rate_cp95_lo": ci_lo,
            "rate_cp95_hi": ci_hi,
            "formula": rule_info.get("formula", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Main S6 Analysis Routine
# ---------------------------------------------------------------------------

def run_ae_threshold_ablation() -> None:
    # 0. Zero-Training Guard
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    # Strict output directory -- must be inside revision_v5/
    out_dir = NEW_ROOT / "results/publication_experiments/EXP_AE_ABLATION_V1"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # 1. Load S5 Threshold Catalogue (NEVER RECOMPUTE thresholds)
    logger.info("=== STEP 1: Loading Thresholds from EXP_MAD_THRESHOLD_V1 ===")
    s5_path = resolve_path(
        "results/publication_experiments/EXP_MAD_THRESHOLD_V1/mad_threshold.json"
    )
    if not s5_path.exists():
        raise FileNotFoundError(
            f"S5 mad_threshold.json not found at {s5_path}. "
            "Run S5 (run_mad_threshold.py) first."
        )
    s5_sha = compute_sha256(s5_path)
    with open(s5_path, "r", encoding="utf-8") as fh:
        s5_data = json.load(fh)

    thresholds: Dict[str, Any] = s5_data["thresholds"]
    n_rules = len(thresholds)
    n_primary = sum(1 for r in thresholds.values() if r.get("category") == "primary")
    n_cal_s5 = int(s5_data["N_cal"])
    logger.info(
        f"Loaded {n_rules} rules ({n_primary} primary) from S5; "
        f"N_cal={n_cal_s5}; SHA256={s5_sha[:16]}..."
    )

    if "mean_plus_3sigma" not in thresholds:
        raise AssertionError(
            "mean_plus_3sigma not found in S5 thresholds -- cannot run frozen-run assertion."
        )
    m3s_threshold = float(thresholds["mean_plus_3sigma"]["threshold_value"])
    logger.info(f"mean_plus_3sigma threshold (frozen): {m3s_threshold:.8f}")

    # 2. Load S1 AE Reconstruction Error Files
    logger.info("=== STEP 2: Loading S1 AE Reconstruction Error Files ===")
    ae_base = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1")
    if not ae_base.exists():
        raise FileNotFoundError(f"EXP_PROB_INFERENCE_V1 dir not found: {ae_base}")

    def load_ae_csv(filename: str) -> Tuple[pd.DataFrame, str]:
        p = ae_base / filename
        if not p.exists():
            raise FileNotFoundError(f"S1 AE output not found: {p}")
        df = pd.read_csv(p)
        sha = compute_sha256(p)
        logger.info(f"  Loaded {filename}: N={len(df)}, SHA256={sha[:16]}...")
        return df, sha

    df_zeroday, sha_zeroday = load_ae_csv("ae_zeroday_reconstruction_errors.csv")
    df_unseen, sha_unseen = load_ae_csv("ae_unseen_family_reconstruction_errors.csv")

    required_cols = ["row_uid", "label", "attack_cat", "population_type", "reconstruction_error"]
    for df_name, df_obj in [("ae_zeroday", df_zeroday), ("ae_unseen_family", df_unseen)]:
        for col in required_cols:
            if col not in df_obj.columns:
                raise AssertionError(f"Column {col!r} missing from {df_name}")

    # 3. Load Population UID Lists
    logger.info("=== STEP 3: Loading Population UID Lists ===")
    pop_dir = resolve_path("results/publication_experiments/EXP_POPULATIONS_V1")

    def load_uid_list(filename: str) -> Tuple[List[str], str]:
        p = pop_dir / filename
        if not p.exists():
            raise FileNotFoundError(f"UID list not found: {p}")
        with open(p, "r", encoding="utf-8") as fh:
            uids = json.load(fh)
        sha = compute_sha256(p)
        return uids, sha

    eval_ctrl_uids, sha_eval_ctrl = load_uid_list("eval_control_row_uids.json")
    benign_ctrl_uids, sha_benign_ctrl = load_uid_list("benign_control_row_uids.json")
    logger.info(f"eval_control N={len(eval_ctrl_uids)}, SHA={sha_eval_ctrl[:16]}...")
    logger.info(f"benign_control N={len(benign_ctrl_uids)}, SHA={sha_benign_ctrl[:16]}...")

    eval_ctrl_set = set(eval_ctrl_uids)
    benign_ctrl_set = set(benign_ctrl_uids)
    if not eval_ctrl_set <= benign_ctrl_set:
        raise AssertionError(
            "eval_control UIDs are NOT a subset of benign_control -- "
            "populations.yaml disjoint-halves contract violated."
        )
    logger.info("PASS: eval_control is a strict subset of benign_control.")

    # 4. Carve Population Slices from S1 Files
    logger.info("=== STEP 4: Carving Population Slices ===")

    # Backdoor: population_type == ZERO_DAY_BACKDOOR
    df_backdoor = df_zeroday[df_zeroday["population_type"] == "ZERO_DAY_BACKDOOR"].copy()
    if df_backdoor["label"].eq(0).any():
        raise AssertionError("ZERO_DAY_BACKDOOR rows contain benign labels -- data integrity failure.")
    logger.info(f"Backdoor slice: N={len(df_backdoor)}")

    # Full benign control: population_type == BENIGN_CONTROL
    df_ctrl_full = df_zeroday[df_zeroday["population_type"] == "BENIGN_CONTROL"].copy()
    ctrl_full_uid_set = set(df_ctrl_full["row_uid"])
    if ctrl_full_uid_set != benign_ctrl_set:
        raise AssertionError(
            f"BENIGN_CONTROL rows in ae_zeroday file do not exactly match "
            f"benign_control_row_uids.json "
            f"(file={len(ctrl_full_uid_set)}, uid_list={len(benign_ctrl_set)})."
        )
    logger.info(f"Full benign control: N={len(df_ctrl_full)} (verified against uid list)")

    # Tier B eval half: subset of BENIGN_CONTROL by eval_control UIDs
    df_eval_ctrl = df_ctrl_full[df_ctrl_full["row_uid"].isin(eval_ctrl_set)].copy()
    if len(df_eval_ctrl) != len(eval_ctrl_uids):
        raise AssertionError(
            f"eval_control slice has {len(df_eval_ctrl)} rows but uid list has "
            f"{len(eval_ctrl_uids)}. Missing UIDs in ae_zeroday file."
        )
    logger.info(f"Tier B eval_control: N={len(df_eval_ctrl)} (verified against uid list)")

    # Unseen families: Worms, Shellcode, Analysis
    UNSEEN_CATS = ["Worms", "Shellcode", "Analysis"]
    EXPECTED_UNSEEN: Dict[str, int] = {"Worms": 44, "Shellcode": 378, "Analysis": 677}
    df_unseen_filt = df_unseen[df_unseen["attack_cat"].isin(UNSEEN_CATS)].copy()
    for cat, exp_n in EXPECTED_UNSEEN.items():
        actual_n = int((df_unseen_filt["attack_cat"] == cat).sum())
        if actual_n != exp_n:
            raise AssertionError(
                f"Unseen family {cat!r}: expected {exp_n} rows, got {actual_n}."
            )
    logger.info(f"Unseen families: N={len(df_unseen_filt)} (Worms=44, Shellcode=378, Analysis=677)")

    # 5. Frozen-Run Assertion
    # Reference values derived from live S1 data before S6 was drafted (2026-09-28).
    # At mean_plus_3sigma (11.160063397140519): 0 Backdoor detections, 19/37,000 control FPs.
    logger.info("=== STEP 5: Frozen-Run Assertion (mean_plus_3sigma) ===")
    FROZEN_BACKDOOR_DETECTIONS: int = 0
    FROZEN_CONTROL_FP: int = 19

    re_backdoor_all = df_backdoor["reconstruction_error"].values.astype(float)
    re_ctrl_all = df_ctrl_full["reconstruction_error"].values.astype(float)

    actual_bd = int((re_backdoor_all > m3s_threshold).sum())
    actual_ctrl = int((re_ctrl_all > m3s_threshold).sum())

    if actual_bd != FROZEN_BACKDOOR_DETECTIONS:
        raise AssertionError(
            f"FROZEN-RUN ASSERTION FAILED: mean_plus_3sigma Backdoor detections "
            f"= {actual_bd}, expected {FROZEN_BACKDOOR_DETECTIONS}. "
            f"Threshold: {m3s_threshold:.8f}"
        )
    if actual_ctrl != FROZEN_CONTROL_FP:
        raise AssertionError(
            f"FROZEN-RUN ASSERTION FAILED: mean_plus_3sigma full-control FPs "
            f"= {actual_ctrl}, expected {FROZEN_CONTROL_FP}. "
            f"Threshold: {m3s_threshold:.8f}"
        )
    logger.info(
        f"PASS: Backdoor detections={actual_bd}=={FROZEN_BACKDOOR_DETECTIONS}; "
        f"control FP={actual_ctrl}=={FROZEN_CONTROL_FP} (N=37,000)."
    )

    # 6. Evaluate All Populations Against All Thresholds
    logger.info("=== STEP 6: Evaluating All Populations vs All Thresholds ===")
    all_rows: List[Dict[str, Any]] = []

    logger.info("  Evaluating: Tier B eval_control (N=18,500, benign -> fpr)")
    all_rows.extend(evaluate_population(
        re_vector=df_eval_ctrl["reconstruction_error"].values.astype(float),
        n_expected=18500,
        pop_label="eval_control_tier_b",
        thresholds=thresholds,
        is_attack=False,
    ))

    logger.info("  Evaluating: Full benign control (N=37,000, benign -> fpr)")
    all_rows.extend(evaluate_population(
        re_vector=re_ctrl_all,
        n_expected=37000,
        pop_label="benign_control_full",
        thresholds=thresholds,
        is_attack=False,
    ))

    logger.info("  Evaluating: Backdoor zero-day (N=583, attack -> recall)")
    all_rows.extend(evaluate_population(
        re_vector=re_backdoor_all,
        n_expected=583,
        pop_label="backdoor_zeroday",
        thresholds=thresholds,
        is_attack=True,
    ))

    logger.info("  Evaluating: Unseen families combined (N=1,099, attack -> recall)")
    all_rows.extend(evaluate_population(
        re_vector=df_unseen_filt["reconstruction_error"].values.astype(float),
        n_expected=1099,
        pop_label="unseen_families_combined",
        thresholds=thresholds,
        is_attack=True,
    ))

    df_out = pd.DataFrame(all_rows)
    logger.info(f"  Main results table: {len(df_out)} rows x {len(df_out.columns)} cols")

    # Spot-check: eval_control_tier_b FPs for mean_plus_3sigma must not exceed full-control FPs
    m3s_eval_fps = int(df_out.loc[
        (df_out["population"] == "eval_control_tier_b") &
        (df_out["rule_name"] == "mean_plus_3sigma"),
        "n_detected",
    ].iloc[0])
    logger.info(
        f"Spot-check: eval_control_tier_b mean_plus_3sigma FPs={m3s_eval_fps} "
        f"(must be <= {FROZEN_CONTROL_FP} full-control FPs)"
    )
    if m3s_eval_fps > FROZEN_CONTROL_FP:
        raise AssertionError(
            f"eval_control FPs ({m3s_eval_fps}) > full-control FPs ({FROZEN_CONTROL_FP}) "
            f"for mean_plus_3sigma -- impossible if eval_control is a subset of benign_control."
        )

    # 7. Per-Family Unseen Recall Table
    logger.info("=== STEP 7: Per-Family Unseen Recall ===")
    unseen_rows: List[Dict[str, Any]] = []
    for cat in UNSEEN_CATS:
        df_cat = df_unseen_filt[df_unseen_filt["attack_cat"] == cat]
        unseen_rows.extend(evaluate_population(
            re_vector=df_cat["reconstruction_error"].values.astype(float),
            n_expected=EXPECTED_UNSEEN[cat],
            pop_label=f"unseen_{cat.lower()}",
            thresholds=thresholds,
            is_attack=True,
        ))
    df_unseen_out = pd.DataFrame(unseen_rows)
    logger.info(f"  Per-family table: {len(df_unseen_out)} rows")

    # 8. Write Output Artifacts
    logger.info("=== STEP 8: Writing Output Artifacts ===")

    ablation_csv_path = out_dir / "ae_ablation_results.csv"
    df_out.to_csv(ablation_csv_path, index=False)
    logger.info(f"Wrote {ablation_csv_path}")

    ablation_unseen_csv_path = out_dir / "ae_ablation_results_unseen.csv"
    df_unseen_out.to_csv(ablation_unseen_csv_path, index=False)
    logger.info(f"Wrote {ablation_unseen_csv_path}")

    self_check_path = out_dir / "self_check.json"
    self_check = {
        "experiment_id": "EXP_AE_ABLATION_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_training_guard": "PASS",
        "s5_threshold_source_sha256": s5_sha,
        "n_threshold_rules": n_rules,
        "n_primary_rules": n_primary,
        "frozen_run_assertion": {
            "rule": "mean_plus_3sigma",
            "threshold": m3s_threshold,
            "expected_backdoor_detections": FROZEN_BACKDOOR_DETECTIONS,
            "actual_backdoor_detections": actual_bd,
            "expected_control_fp_n37000": FROZEN_CONTROL_FP,
            "actual_control_fp_n37000": actual_ctrl,
            "status": "PASS",
        },
        "populations_evaluated": {
            "eval_control_tier_b": {"n": 18500, "metric": "fpr"},
            "benign_control_full": {"n": 37000, "metric": "fpr"},
            "backdoor_zeroday": {"n": 583, "metric": "recall"},
            "unseen_families_combined": {"n": 1099, "metric": "recall"},
            "unseen_worms": {"n": 44, "metric": "recall"},
            "unseen_shellcode": {"n": 378, "metric": "recall"},
            "unseen_analysis": {"n": 677, "metric": "recall"},
        },
        "eval_control_subset_of_benign_control": True,
        "strict_detection_rule": "> (strict greater than)",
        "ci_method": "Clopper-Pearson 95%",
        "overall_status": "PASS",
    }
    with open(self_check_path, "w", encoding="utf-8") as fh:
        json.dump(self_check, fh, indent=2)
    logger.info(f"Wrote {self_check_path}")

    metadata_path = out_dir / "metadata.json"
    metadata = {
        "experiment_id": "EXP_AE_ABLATION_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provenance_hashes": {
            "s5_mad_threshold_json": s5_sha,
            "ae_zeroday_reconstruction_errors": sha_zeroday,
            "ae_unseen_family_reconstruction_errors": sha_unseen,
            "eval_control_row_uids": sha_eval_ctrl,
            "benign_control_row_uids": sha_benign_ctrl,
        },
        "artifact_hashes": {
            "ae_ablation_results.csv": compute_sha256(ablation_csv_path),
            "ae_ablation_results_unseen.csv": compute_sha256(ablation_unseen_csv_path),
            "self_check.json": compute_sha256(self_check_path),
        },
        "status": "PASS",
    }
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info(f"Wrote {metadata_path}")

    logger.info("=== S6 AE Threshold Ablation Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S6: AE Threshold Ablation Analysis")
    # No mandatory config -- all inputs are resolved from S5 outputs + populations manifest.
    parser.parse_args()
    run_ae_threshold_ablation()
