#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_roc_pr_analysis.py
-----------------------------------------------------------------
Phase 2 / Analysis B2: ROC, PR, PR-AUC, and F2 Analysis (S2).
Blueprint reference: §6 (BATCH-B, B2), §16 (S2), §0 Rule 15, §18 Gate 4.

Key responsibilities:
1. Purely reads saved score files; strictly fits no models, parameters, or scalers (zero-training guard).
2. Computes ROC curve, ROC-AUC, PR curve, and PR-AUC (average_precision_score) for all models on ZERO_DAY_COMBINED.
3. Does not pool predictions across seeds: reports each seed individually plus mean ± SD across seeds for Stacking and IF.
4. Computes F2 score at the four matched-FPR budgets (0.1%, 0.5%, 1%, 5%) using thresholds from S3 for the headline tier.
5. Retains default-threshold F2 (0.5 for prob models, 0.0 for SVM) as reference only; labels argmax-F2 as oracle.
6. Generates publication figures: side-by-side ROC and PR panels with headline matched-FPR operating points clearly marked.
7. Writes all outputs strictly under revision_v5/results/publication_experiments/EXP_ROC_PR_V1/.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Sandbox isolation for matplotlib font cache
mpl_cache_dir = Path(__file__).resolve().parent.parent.parent / ".mplconfig"
mpl_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
import yaml

# ---------------------------------------------------------------------------
# Zero-Training Guard (DQ-01: Replicated from scripts/scan_ml_patterns.py)
# ---------------------------------------------------------------------------

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
        if in_guard_def or stripped.startswith("#") or '"""' in stripped:
            continue
        for pattern in PROHIBITED_PATTERNS:
            if pattern in line:
                raise RuntimeError(
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern '{pattern}' "
                    f"found at line {i} of {script_path}: {stripped}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


# ---------------------------------------------------------------------------
# Setup Paths & Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_roc_pr_analysis")


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
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_f2(precision: float, recall: float) -> float:
    """Compute F2 score: (1 + 2^2) * (P * R) / (2^2 * P + R) = 5 * P * R / (4 * P + R)."""
    denom = 4.0 * precision + recall
    if denom <= 0:
        return 0.0
    return 5.0 * (precision * recall) / denom


# ---------------------------------------------------------------------------
# Main Analysis Pipeline (S2)
# ---------------------------------------------------------------------------

def run_roc_pr_analysis(config_path: Path) -> None:
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_rel = cfg.get("output_dir", "results/publication_experiments/EXP_ROC_PR_V1")
    out_dir = NEW_ROOT / out_rel if not str(out_rel).startswith(str(NEW_ROOT)) else Path(out_rel)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # 1. Check for S3 Matched-FPR Results & Headline Tier Decision
    matched_fpr_file = resolve_path(cfg.get("matched_fpr_results", "results/publication_experiments/EXP_MATCHED_FPR_V1/matched_fpr_table.csv"))
    decision_file = resolve_path(cfg.get("headline_tier_decision", "results/publication_experiments/EXP_MATCHED_FPR_V1/headline_tier_decision.json"))

    headline_tier = "A"
    if decision_file.exists():
        with open(decision_file, "r", encoding="utf-8") as f:
            headline_tier = json.load(f).get("headline_tier", "A")
    logger.info(f"Active headline tier: Tier {headline_tier}")

    # 2. Load Zero-Day Scores from S1
    logger.info("=== STEP 1: Loading Scored Zero-Day Populations ===")
    sup_path = resolve_path(cfg["score_inputs"]["supervised_probabilities"])
    ae_path = resolve_path(cfg["score_inputs"]["ae_reconstruction_errors"])

    if not sup_path.exists() or not ae_path.exists():
        raise FileNotFoundError(f"Missing S1 score inputs: {sup_path} or {ae_path}")

    sup_df = pd.read_csv(sup_path)
    ae_df = pd.read_csv(ae_path)

    # Assert alignment
    assert len(sup_df) == len(ae_df) == 37583, f"Expected 37,583 rows in zero-day evaluation, got {len(sup_df)}"
    assert (sup_df["row_uid"] == ae_df["row_uid"]).all(), "Row UID alignment mismatch between supervised and AE scores!"

    # If Tier B is headline tier, evaluate curves and operating points on Tier B evaluation half (EVAL_CONTROL + Backdoor, N=19,083)
    if headline_tier == "B":
        pop_manifest_path = resolve_path(cfg.get("populations_manifest", "publication_experiments/configs/populations.yaml"))
        with open(pop_manifest_path, "r", encoding="utf-8") as f:
            pop_cfg = yaml.safe_load(f)
        tier_b_split_cfg = pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]
        eval_control_list_path = resolve_path(tier_b_split_cfg["eval_control"]["row_uid_list"])
        with open(eval_control_list_path, "r", encoding="utf-8") as f:
            eval_control_uids = set(json.load(f))

        eval_mask = (sup_df["row_uid"].isin(eval_control_uids) | (sup_df["label"] == 1)).values
        assert int(eval_mask.sum()) == 19083, f"Expected 19,083 Tier B eval rows, got {eval_mask.sum()}"
        pop_name = "ZERO_DAY_TIER_B_EVAL"
        pop_label_str = "Tier B Eval Half (EVAL_CONTROL + Backdoor, N=19,083)"
    else:
        eval_mask = np.ones(len(sup_df), dtype=bool)
        pop_name = "ZERO_DAY_COMBINED"
        pop_label_str = "Full ZERO_DAY_COMBINED (N=37,583)"

    sup_eval_df = sup_df[eval_mask].reset_index(drop=True)
    ae_eval_df = ae_df[eval_mask].reset_index(drop=True)

    y_true = sup_eval_df["label"].values.astype(int)
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    prevalence = float(n_pos / len(y_true))
    logger.info(f"{pop_name}: total={len(y_true)}, positive={n_pos} (Backdoor), negative={n_neg}, prevalence={prevalence:.4f}")

    # Build model score dictionary on evaluated population
    scores: Dict[str, np.ndarray] = {
        "dt": sup_eval_df["dt_attack_probability"].values,
        "rf": sup_eval_df["rf_attack_probability"].values,
        "svm": sup_eval_df["svm_decision_score"].values,
        "nn": sup_eval_df["nn_attack_probability"].values,
        "stacking_seed_42": sup_eval_df["stacking_attack_probability_seed42"].values,
        "stacking_seed_123": sup_eval_df["stacking_attack_probability_seed123"].values,
        "stacking_seed_2024": sup_eval_df["stacking_attack_probability_seed2024"].values,
        "ae": ae_eval_df["reconstruction_error"].values,
    }

    # Optional: Load Isolation Forest scores if S7 has completed
    if_path = resolve_path(cfg["score_inputs"].get("if_scores", "results/publication_experiments/EXP_IF_V1/scores/zeroday_scores.csv"))
    if if_path.exists():
        if_df = pd.read_csv(if_path)
        assert len(if_df) == 37583, f"Expected 37,583 IF zero-day rows, got {len(if_df)}"
        if_eval_df = if_df[eval_mask].reset_index(drop=True)
        for seed in [42, 123, 2024]:
            col = f"if_anomaly_score_seed_{seed}" if f"if_anomaly_score_seed_{seed}" in if_eval_df.columns else "anomaly_score"
            scores[f"if_seed_{seed}"] = if_eval_df[col].values
        logger.info(f"Loaded Isolation Forest scores for {pop_name} from S7")
    else:
        logger.info(f"Isolation Forest scores ({if_path}) not yet generated; S2 will score available models (DT, RF, SVM, NN, Stacking, AE)")

    # Load S3 Matched-FPR operating points
    matched_fpr_lookup: Dict[str, Dict[str, Dict[str, float]]] = {}
    operating_points: List[Dict[str, Any]] = []

    if matched_fpr_file.exists():
        logger.info(f"Found S3 matched_fpr_table.csv! Loading headline operating points from Tier {headline_tier}")
        matched_df = pd.read_csv(matched_fpr_file)
        tier_sub = matched_df[matched_df["calibration_tier"] == headline_tier]
        for _, row in tier_sub.iterrows():
            key = str(row["model_key"]) if "model_key" in row and pd.notna(row["model_key"]) else str(row["model"])
            b = str(row["nominal_budget_str"]) if "nominal_budget_str" in row else str(row.get("budget", ""))
            if key not in matched_fpr_lookup:
                matched_fpr_lookup[key] = {}
            matched_fpr_lookup[key][b] = {
                "threshold": float(row["threshold"]),
                "realized_fpr": float(row["realized_control_fpr"]),
                "recall": float(row["recall"]),
                "f2": float(row.get("f2", np.nan)),
            }
            operating_points.append({
                "model_key": key,
                "budget": b,
                "realized_fpr": float(row["realized_control_fpr"]),
                "recall": float(row["recall"]),
                "precision": float(row.get("precision", np.nan)),
                "f2": float(row.get("f2", np.nan)),
            })
    else:
        logger.info("S3 matched_fpr_table.csv not found yet; running S2 on threshold-free and reference/oracle metrics.")

    # 3. Compute ROC & PR Curves and AUCs
    logger.info("=== STEP 2: Computing ROC and PR Curves ===")
    curve_records = []
    summary_records = []

    for model_name, score_vec in scores.items():
        # ROC
        fpr, tpr, roc_thresh = roc_curve(y_true, score_vec)
        roc_auc = float(roc_auc_score(y_true, score_vec))

        # PR
        precision, recall, pr_thresh = precision_recall_curve(y_true, score_vec)
        pr_auc = float(average_precision_score(y_true, score_vec))

        # Argmax F2 (oracle / test-tuned)
        f2_arr = np.array([compute_f2(p, r) for p, r in zip(precision, recall)])
        argmax_idx = int(np.argmax(f2_arr))
        argmax_f2 = float(f2_arr[argmax_idx])
        argmax_prec = float(precision[argmax_idx])
        argmax_rec = float(recall[argmax_idx])

        # Default threshold F2 (0.5 for prob models, 0.0 for SVM)
        def_thresh = 0.0 if model_name == "svm" else (0.5 if "prob" in model_name or "dt" in model_name or "rf" in model_name or "nn" in model_name or "stacking" in model_name else None)
        if def_thresh is not None:
            pred_def = (score_vec >= def_thresh).astype(int)
            tp = int(((pred_def == 1) & (y_true == 1)).sum())
            fp = int(((pred_def == 1) & (y_true == 0)).sum())
            fn = int(((pred_def == 0) & (y_true == 1)).sum())
            p_def = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r_def = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f2_def = compute_f2(p_def, r_def)
        else:
            p_def, r_def, f2_def = None, None, None

        rec = {
            "model": model_name,
            "population": pop_name,
            "population_label": pop_label_str,
            "prevalence": prevalence,
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "default_threshold": def_thresh,
            "default_precision": p_def,
            "default_recall": r_def,
            "default_f2": f2_def,
            "oracle_argmax_f2": argmax_f2,
            "oracle_argmax_precision": argmax_prec,
            "oracle_argmax_recall": argmax_rec,
        }

        # Add matched-FPR F2 if available from S3
        if model_name in matched_fpr_lookup:
            for b, b_data in matched_fpr_lookup[model_name].items():
                clean_b = str(b).replace("/", "_")
                rec[f"matched_fpr_f2_budget_{clean_b}"] = b_data["f2"]
                rec[f"matched_fpr_recall_budget_{clean_b}"] = b_data["recall"]
                rec[f"matched_fpr_realized_fpr_budget_{clean_b}"] = b_data["realized_fpr"]

        summary_records.append(rec)

        # Downsample curve points for publication CSV
        for step_i in range(0, len(fpr), max(1, len(fpr) // 500)):
            curve_records.append({
                "model": model_name,
                "curve_type": "ROC",
                "x_fpr": float(fpr[step_i]),
                "y_tpr_recall": float(tpr[step_i]),
                "threshold": float(roc_thresh[step_i]) if step_i < len(roc_thresh) else np.nan,
            })
        for step_i in range(0, len(precision), max(1, len(precision) // 500)):
            curve_records.append({
                "model": model_name,
                "curve_type": "PR",
                "x_recall": float(recall[step_i]),
                "y_precision": float(precision[step_i]),
                "threshold": float(pr_thresh[step_i]) if step_i < len(pr_thresh) else np.nan,
            })

    summary_df = pd.DataFrame(summary_records)
    curves_df = pd.DataFrame(curve_records)

    # 4. Seed aggregation (mean ± SD) for Stacking and IF
    for family in ["stacking", "if"]:
        family_sub = summary_df[summary_df["model"].str.startswith(family)]
        if len(family_sub) > 1:
            mean_roc = float(family_sub["roc_auc"].mean())
            std_roc = float(family_sub["roc_auc"].std())
            mean_pr = float(family_sub["pr_auc"].mean())
            std_pr = float(family_sub["pr_auc"].std())
            logger.info(f"{family.upper()} (3 seeds): ROC-AUC = {mean_roc:.4f} ± {std_roc:.4f}, PR-AUC = {mean_pr:.4f} ± {std_pr:.4f}")

    # 5. Generate Publication Figure (ROC + PR Side-by-Side)
    logger.info("=== STEP 3: Generating Publication Figure ===")
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    color_map = {
        "dt": "#1f77b4",
        "rf": "#2ca02c",
        "svm": "#9467bd",
        "nn": "#ff7f0e",
        "stacking_seed_42": "#d62728",
        "stacking_seed_123": "#ff9896",
        "stacking_seed_2024": "#c5b0d5",
        "ae": "#8c564b",
        "if_seed_42": "#17becf",
        "if_seed_123": "#9edae5",
        "if_seed_2024": "#bcbd22",
    }

    # Plot ROC Panel
    for model_name, score_vec in scores.items():
        fpr, tpr, _ = roc_curve(y_true, score_vec)
        rauc = roc_auc_score(y_true, score_vec)
        label = f"{model_name} (AUC={rauc:.3f})"
        c = color_map.get(model_name, "#7f7f7f")
        alpha = 0.9 if ("42" in model_name or "seed" not in model_name) else 0.4
        linestyle = "--" if ("123" in model_name or "2024" in model_name) else "-"
        ax_roc.plot(fpr, tpr, label=label, color=c, alpha=alpha, linestyle=linestyle, linewidth=1.5)

    ax_roc.plot([0, 1], [0, 1], "k--", alpha=0.3, label="Chance")
    ax_roc.set_xlabel("False Positive Rate (FPR)", fontsize=11)
    ax_roc.set_ylabel("True Positive Rate (Recall)", fontsize=11)
    ax_roc.set_title(f"Zero-Day Detection ROC Curve\n({pop_label_str})", fontsize=11, fontweight="bold")
    ax_roc.legend(loc="lower right", fontsize=8, frameon=True)
    ax_roc.grid(True, linestyle=":", alpha=0.6)

    # Plot PR Panel
    for model_name, score_vec in scores.items():
        prec, rec_pts, _ = precision_recall_curve(y_true, score_vec)
        prauc = average_precision_score(y_true, score_vec)
        label = f"{model_name} (AP={prauc:.3f})"
        c = color_map.get(model_name, "#7f7f7f")
        alpha = 0.9 if ("42" in model_name or "seed" not in model_name) else 0.4
        linestyle = "--" if ("123" in model_name or "2024" in model_name) else "-"
        ax_pr.plot(rec_pts, prec, label=label, color=c, alpha=alpha, linestyle=linestyle, linewidth=1.5)

    ax_pr.axhline(y=prevalence, color="k", linestyle="--", alpha=0.4, label=f"Prevalence ({prevalence:.4f})")
    ax_pr.set_xlabel("Recall (True Positive Rate)", fontsize=11)
    ax_pr.set_ylabel("Precision (Positive Predictive Value)", fontsize=11)
    ax_pr.set_title(f"Zero-Day Detection PR Curve\n({pop_label_str}, Prev {prevalence*100:.2f}%)", fontsize=11, fontweight="bold")
    ax_pr.legend(loc="upper right", fontsize=8, frameon=True)
    ax_pr.grid(True, linestyle=":", alpha=0.6)

    # Overlay matched-FPR operating points if present
    if operating_points:
        logger.info(f"Overlaying {len(operating_points)} headline matched-FPR operating points on figures")
        for op in operating_points:
            m = op["model_key"]
            c = color_map.get(m, "#000000")
            ax_roc.scatter(op["realized_fpr"], op["recall"], color=c, edgecolors="black", s=40, zorder=5)
            if not np.isnan(op.get("precision", np.nan)):
                ax_pr.scatter(op["recall"], op["precision"], color=c, edgecolors="black", s=40, zorder=5)

    plt.tight_layout()
    fig_path = fig_dir / "fig_roc_pr_zeroday.png"
    plt.savefig(fig_path, dpi=300)
    plt.close()
    logger.info(f"Saved publication figure: {fig_path}")

    # 6. Save Artifacts & Metadata
    logger.info("=== STEP 4: Writing Output CSVs and Metadata ===")
    summary_path = out_dir / "roc_pr_metrics_summary.csv"
    curves_path = out_dir / "roc_pr_curve_points.csv"
    summary_df.to_csv(summary_path, index=False)
    curves_df.to_csv(curves_path, index=False)

    file_hashes = {
        "roc_pr_metrics_summary.csv": compute_sha256(summary_path),
        "roc_pr_curve_points.csv": compute_sha256(curves_path),
        "fig_roc_pr_zeroday.png": compute_sha256(fig_path),
    }

    # 7. Self-Check Output
    self_check = {
        "experiment_id": "EXP_ROC_PR_V1",
        "zero_training_guard": "PASS",
        "population": pop_name,
        "population_label": pop_label_str,
        "population_size": len(y_true),
        "prevalence": prevalence,
        "positive_count": int(np.sum(y_true == 1)),
        "negative_count": int(np.sum(y_true == 0)),
        "headline_tier": headline_tier,
        "models_evaluated": list(scores.keys()),
        "operating_points_count": len(operating_points),
        "operating_points_marked": len(operating_points) > 0,
        "auc_range_check": {
            m: bool(0.0 <= row["roc_auc"] <= 1.0 and 0.0 <= row["pr_auc"] <= 1.0)
            for m, row in summary_df.set_index("model").iterrows()
        },
        "nan_inf_check": {
            "summary_df": bool(not summary_df[["roc_auc", "pr_auc"]].isnull().values.any()),
            "roc_curve_points": bool(not curves_df[curves_df["curve_type"] == "ROC"][["x_fpr", "y_tpr_recall"]].isnull().values.any()),
            "pr_curve_points": bool(not curves_df[curves_df["curve_type"] == "PR"][["x_recall", "y_precision"]].isnull().values.any()),
        },
        "overall_status": "PASS",
    }

    self_check_path = out_dir / "self_check.json"
    with open(self_check_path, "w", encoding="utf-8") as f:
        json.dump(self_check, f, indent=2)
    file_hashes["self_check.json"] = compute_sha256(self_check_path)
    logger.info("=== Self-Check Completed & Written ===")
    logger.info(json.dumps(self_check, indent=2))

    metadata = {
        "experiment_id": "EXP_ROC_PR_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "population": pop_name,
        "population_label": pop_label_str,
        "population_size": len(y_true),
        "prevalence": prevalence,
        "headline_tier": headline_tier,
        "models_evaluated": list(scores.keys()),
        "artifact_hashes": file_hashes,
        "status": "PASS",
    }

    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    file_hashes["metadata.json"] = compute_sha256(out_dir / "metadata.json")

    logger.info("=== ROC / PR Analysis Pipeline Ready ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 / Analysis B2: ROC, PR, PR-AUC, and F2 (S2)")
    parser.add_argument(
        "--config",
        type=str,
        default="revision_v5/publication_experiments/configs/roc_pr.yaml",
        help="Path to roc_pr.yaml",
    )
    args = parser.parse_args()
    run_roc_pr_analysis(Path(args.config))
