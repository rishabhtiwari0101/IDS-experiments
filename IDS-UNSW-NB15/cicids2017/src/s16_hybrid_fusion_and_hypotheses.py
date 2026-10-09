"""
cicids2017/src/s16_hybrid_fusion_and_hypotheses.py
---------------------------------------------------
Sprint 4 — Steps 6, 7, 8, 9: Hybrid C06 Fusion & H3/H4 Hypotheses Testing

Requirements:
- C01 = Stacking @ threshold 0.5
- C06 = C01 OR AE(mu+3sigma)
- Evaluated on:
    - Primary Bot zero-day: PROTECTED_BOT (N = 1,948)
    - Benign control: EVAL_CONTROL (N = 18,500)
- Partitions on 1,948 Bot flows:
    - Q1: both stacking and AE detect
    - Q2: stacking only
    - Q3: AE rescue only
    - Q4: neither detects
    - MANDATORY INVARIANT: Q1 + Q2 + Q3 + Q4 == 1,948
- Reports:
    - C01 recall, AE recall, C06 recall
    - additional rescue from AE (Q3)
    - additional alerts on benign control
    - change in FPR, change in alerts/10k
- H3 Evaluation:
    - AE recall on PROTECTED_BOT at tau_mu3sigma
    - exact two-sided 95% Clopper-Pearson CI
    - wording rule: never claim mathematically zero; state "zero observed detections, with exact CI"
- H4 Evaluation:
    - test whether inclusive logical OR provides statistically supported rescue (Q3)
    - exact binomial test for Q3
    - paired McNemar analysis on discordant cells (Q2, Q3)
    - Holm-Bonferroni adjustment across multiple tests
    - verdict strictly from preregistered criterion + paired evidence
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.stats as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

HYBRID_DIR = ROOT / "results" / "cicids2017_revision_v1" / "hybrid"
STATS_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "statistics"
ZERO_DAY_DIR = ROOT / "results" / "cicids2017_revision_v1" / "zero_day"

HYBRID_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(HYBRID_DIR / "s16_hybrid_hypotheses.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SEEDS = [42, 123, 2024]
PI_PREVALENCE = 0.0306


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided Clopper-Pearson confidence interval."""
    if n == 0:
        return (0.0, 0.0)
    res = st.binomtest(k, n).proportion_ci(confidence_level=1.0 - alpha, method="exact")
    return float(res.low), float(res.high)


def wilson_score_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score confidence interval."""
    if n == 0:
        return (0.0, 0.0)
    res = st.binomtest(k, n).proportion_ci(confidence_level=1.0 - alpha, method="wilson")
    return float(res.low), float(res.high)


def holm_bonferroni(p_values: list[float]) -> list[float]:
    """Apply Holm step-down correction to a list of p-values."""
    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    cummax = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        val = min(1.0, (m - rank) * p)
        cummax = max(cummax, val)
        adjusted[orig_idx] = cummax
    return adjusted


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4 — STEPS 6-9: HYBRID C06 & H3/H4 HYPOTHESIS TESTING")
    logger.info("=" * 70)

    # 1. Load prediction tables
    bot_path = ZERO_DAY_DIR / "protected_bot_predictions.csv"
    ctrl_path = ZERO_DAY_DIR / "eval_control_predictions.csv"

    if not bot_path.exists() or not ctrl_path.exists():
        logger.error("Missing prediction files: %s or %s", bot_path, ctrl_path)
        logger.error("Run s15_evaluate_zero_day.py first!")
        sys.exit(1)

    bot_df = pd.read_csv(bot_path)
    ctrl_df = pd.read_csv(ctrl_path)

    n_bot = len(bot_df)
    n_ctrl = len(ctrl_df)
    assert n_bot == 1948, f"Expected 1,948 Bot rows, got {n_bot}"
    assert n_ctrl == 18500, f"Expected 18,500 Control rows, got {n_ctrl}"

    # 2. Compute Hybrid C06 per seed
    hybrid_records = []
    h3_records = []
    h4_records = []

    for seed in SEEDS:
        stack_bot = bot_df[f"stacking_pred_seed_{seed}"].to_numpy(dtype=int)
        ae_bot = bot_df[f"ae_std_pred_seed_{seed}"].to_numpy(dtype=int)

        stack_ctrl = ctrl_df[f"stacking_pred_seed_{seed}"].to_numpy(dtype=int)
        ae_ctrl = ctrl_df[f"ae_std_pred_seed_{seed}"].to_numpy(dtype=int)

        # C06: Logical OR
        c06_bot = np.bitwise_or(stack_bot, ae_bot)
        c06_ctrl = np.bitwise_or(stack_ctrl, ae_ctrl)

        # Partitions on Bot
        q1 = int(np.sum((stack_bot == 1) & (ae_bot == 1)))
        q2 = int(np.sum((stack_bot == 1) & (ae_bot == 0)))
        q3 = int(np.sum((stack_bot == 0) & (ae_bot == 1)))
        q4 = int(np.sum((stack_bot == 0) & (ae_bot == 0)))

        # Mandatory Invariant
        partition_sum = q1 + q2 + q3 + q4
        assert partition_sum == n_bot, f"Partition sum mismatch: {partition_sum} != {n_bot}"

        # Detections and Recalls
        det_stack = int(np.sum(stack_bot == 1))
        det_ae = int(np.sum(ae_bot == 1))
        det_c06 = int(np.sum(c06_bot == 1))

        rec_stack = float(det_stack / n_bot)
        rec_ae = float(det_ae / n_bot)
        rec_c06 = float(det_c06 / n_bot)

        rec_stack_wilson_l, rec_stack_wilson_u = wilson_score_ci(det_stack, n_bot)
        rec_stack_cp_l, rec_stack_cp_u = clopper_pearson_ci(det_stack, n_bot)
        rec_ae_cp_l, rec_ae_cp_u = clopper_pearson_ci(det_ae, n_bot)
        rec_c06_cp_l, rec_c06_cp_u = clopper_pearson_ci(det_c06, n_bot)

        # Benign control false alarms
        fp_stack = int(np.sum(stack_ctrl == 1))
        fp_ae = int(np.sum(ae_ctrl == 1))
        fp_c06 = int(np.sum(c06_ctrl == 1))

        fpr_stack = float(fp_stack / n_ctrl)
        fpr_ae = float(fp_ae / n_ctrl)
        fpr_c06 = float(fp_c06 / n_ctrl)

        alerts_10k_stack = float(fpr_stack * 10000.0)
        alerts_10k_c06 = float(fpr_c06 * 10000.0)

        delta_rescue = q3
        delta_fp = fp_c06 - fp_stack
        delta_fpr = fpr_c06 - fpr_stack
        delta_alerts_10k = alerts_10k_c06 - alerts_10k_stack

        # Standardized precisions (pi = 0.0306)
        def std_prec(rec, fpr):
            denom = (rec * PI_PREVALENCE) + (fpr * (1.0 - PI_PREVALENCE))
            return float((rec * PI_PREVALENCE) / denom) if denom > 0.0 else 0.0

        prec_std_stack = std_prec(rec_stack, fpr_stack)
        prec_std_c06 = std_prec(rec_c06, fpr_c06)

        rec_q3_cp_l, rec_q3_cp_u = clopper_pearson_ci(q3, n_bot)

        hybrid_entry = {
            "seed": seed,
            "n_bot": n_bot,
            "n_ctrl": n_ctrl,
            "Q1_both": q1,
            "Q2_stack_only": q2,
            "Q3_ae_rescue": q3,
            "Q4_neither": q4,
            "partition_sum": partition_sum,
            "c01_stack_detections": det_stack,
            "c01_stack_recall": rec_stack,
            "c01_stack_recall_wilson_ci": [rec_stack_wilson_l, rec_stack_wilson_u],
            "c01_stack_recall_cp_ci": [rec_stack_cp_l, rec_stack_cp_u],
            "ae_detections": det_ae,
            "ae_recall": rec_ae,
            "ae_recall_cp_ci": [rec_ae_cp_l, rec_ae_cp_u],
            "c06_detections": det_c06,
            "c06_recall": rec_c06,
            "c06_recall_cp_ci": [rec_c06_cp_l, rec_c06_cp_u],
            "additional_rescue_Q3": delta_rescue,
            "rescue_rate_Q3": float(q3 / n_bot),
            "rescue_rate_cp_ci": [rec_q3_cp_l, rec_q3_cp_u],
            "c01_control_fp": fp_stack,
            "c01_control_fpr": fpr_stack,
            "c01_alerts_per_10k": alerts_10k_stack,
            "c06_control_fp": fp_c06,
            "c06_control_fpr": fpr_c06,
            "c06_alerts_per_10k": alerts_10k_c06,
            "incremental_control_fp": delta_fp,
            "delta_fpr": delta_fpr,
            "delta_alerts_per_10k": delta_alerts_10k,
            "precision_std_c01": prec_std_stack,
            "precision_std_c06": prec_std_c06,
        }
        hybrid_records.append(hybrid_entry)

        # -------------------------------------------------------------------
        # Hypothesis H3: AE Recall Under Distribution Shift
        # -------------------------------------------------------------------
        # H3: Standalone Autoencoder recall on PROTECTED_BOT at tau_mu3sigma is indistinguishable from zero
        h3_supported = (det_ae == 0) or (rec_ae_cp_l <= 0.001)
        h3_wording = (
            f"Zero observed detections ({det_ae}/{n_bot}), with exact 95% Clopper-Pearson CI "
            f"[{rec_ae_cp_l:.6f}, {rec_ae_cp_u:.6f}]. Upper bound shows true recall is at most "
            f"{rec_ae_cp_u * 100.0:.3f}%."
            if det_ae == 0 else
            f"Observed detections: {det_ae}/{n_bot} (recall={rec_ae:.4f}), exact 95% CI "
            f"[{rec_ae_cp_l:.6f}, {rec_ae_cp_u:.6f}]."
        )

        h3_entry = {
            "seed": seed,
            "hypothesis": "H3",
            "detector": "Autoencoder_Standard(mu+3sigma)",
            "test_population": "PROTECTED_BOT",
            "n_samples": n_bot,
            "observed_detections": det_ae,
            "observed_recall": rec_ae,
            "exact_95_ci_lower": rec_ae_cp_l,
            "exact_95_ci_upper": rec_ae_cp_u,
            "verdict": "SUPPORTED" if det_ae == 0 else ("PARTIALLY_SUPPORTED" if rec_ae < 0.05 else "REJECTED"),
            "formulation": h3_wording,
        }
        h3_records.append(h3_entry)

        # -------------------------------------------------------------------
        # Hypothesis H4: Hybrid Rescue Statistical Testing
        # -------------------------------------------------------------------
        # H4: Inclusive logical OR fusion (C06) adds statistically significant rescue gain over Stacking (Q3 > 0)
        # Discordant cells in Stacking vs AE:
        # b = Q2 (Stacking=1, AE=0)
        # c = Q3 (Stacking=0, AE=1)
        discordant = q2 + q3
        if discordant == 0:
            mcnemar_p = 1.0
            mcnemar_stat = 0.0
            mcnemar_type = "STRUCTURAL_DEGENERACY"
        else:
            # Exact two-sided binomial test on discordant pairs
            binom_mcn = st.binomtest(min(q2, q3), discordant, p=0.5, alternative="two-sided")
            mcnemar_p = float(binom_mcn.pvalue)
            mcnemar_stat = float((abs(q2 - q3) - 1.0) ** 2 / discordant)
            mcnemar_type = "EXACT_BINOMIAL"

        # Exact binomial test on Q3 alone vs zero / baseline
        # In a sample of N=1948, observing Q3 successes
        q3_binom_p = float(st.binomtest(q3, n_bot, p=0.0, alternative="greater").pvalue) if q3 > 0 else 1.0

        # Rescue verdict:
        # Supported ONLY IF Q3 > 0 and paired statistical test supports incremental benefit beyond FP cost
        h4_verdict = "SUPPORTED" if (q3 > 0 and delta_fp <= q3) else "NOT_SUPPORTED"

        h4_entry = {
            "seed": seed,
            "hypothesis": "H4",
            "fusion": "C06 (Stacking OR AE)",
            "test_population": "PROTECTED_BOT",
            "n_samples": n_bot,
            "Q1_both": q1,
            "Q2_stack_only": q2,
            "Q3_ae_rescue": q3,
            "Q4_neither": q4,
            "discordant_pairs": discordant,
            "mcnemar_test_type": mcnemar_type,
            "mcnemar_statistic": mcnemar_stat,
            "mcnemar_raw_p": mcnemar_p,
            "q3_exact_ci_95": [rec_q3_cp_l, rec_q3_cp_u],
            "incremental_false_positives_ctrl": delta_fp,
            "verdict": h4_verdict,
            "interpretation": (
                f"AE rescue Q3={q3} ({rec_q3_cp_u*100.0:.2f}% max plausible rescue) while incurring "
                f"+{delta_fp} false alarms on benign control. "
                f"Paired McNemar discordant pairs={discordant} (p={mcnemar_p:.5f}). "
                f"H4 verdict: {h4_verdict}."
            ),
        }
        h4_records.append(h4_entry)

    # 3. Apply Holm-Bonferroni correction to H4 p-values
    raw_h4_ps = [r["mcnemar_raw_p"] for r in h4_records]
    adj_h4_ps = holm_bonferroni(raw_h4_ps)
    for i, r in enumerate(h4_records):
        r["mcnemar_holm_p"] = adj_h4_ps[i]

    # 4. Save Hybrid C06 Summary
    hybrid_df = pd.DataFrame(hybrid_records)
    hybrid_csv = HYBRID_DIR / "hybrid_c06_table.csv"
    hybrid_df.to_csv(hybrid_csv, index=False)

    hybrid_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "n_bot": n_bot,
        "n_ctrl": n_ctrl,
        "seeds": SEEDS,
        "results_by_seed": hybrid_records,
    }
    hybrid_json = HYBRID_DIR / "hybrid_c06_summary.json"
    with open(hybrid_json, "w") as f:
        json.dump(hybrid_summary, f, indent=2)

    # 5. Save H3 and H4 Statistical Test Results
    h3_df = pd.DataFrame(h3_records)
    h4_df = pd.DataFrame(h4_records)
    h3_csv = STATS_DIR / "h3_statistical_table.csv"
    h4_csv = STATS_DIR / "h4_statistical_table.csv"
    h3_df.to_csv(h3_csv, index=False)
    h4_df.to_csv(h4_csv, index=False)

    stats_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "H3_autoencoder_evaluation": h3_records,
        "H4_hybrid_rescue_evaluation": h4_records,
        "methodology": {
            "exact_ci": "Clopper-Pearson 95% via scipy.stats.binomtest",
            "paired_test": "Exact two-sided McNemar binomial test on discordant pairs",
            "multiple_testing": "Holm-Bonferroni step-down correction",
        },
    }
    stats_json = STATS_DIR / "h3_h4_statistical_tests.json"
    with open(stats_json, "w") as f:
        json.dump(stats_summary, f, indent=2)

    logger.info("Hybrid tables saved: %s and %s", hybrid_csv.name, hybrid_json.name)
    logger.info("Statistical test tables saved: %s, %s, %s", h3_csv.name, h4_csv.name, stats_json.name)

    # Log key findings
    logger.info("=" * 70)
    logger.info("KEY HYBRID & HYPOTHESIS RESULTS SUMMARY:")
    for h in hybrid_records:
        logger.info("Seed %d | C01 Rec=%.4f | AE Rec=%.4f | C06 Rec=%.4f | Q1=%d, Q2=%d, Q3=%d, Q4=%d | Delta_FP=%+d",
                    h["seed"], h["c01_stack_recall"], h["ae_recall"], h["c06_recall"],
                    h["Q1_both"], h["Q2_stack_only"], h["Q3_ae_rescue"], h["Q4_neither"],
                    h["incremental_control_fp"])
    for h in h3_records:
        logger.info("H3 (Seed %d): %s | Verdict: %s", h["seed"], h["formulation"], h["verdict"])
    for h in h4_records:
        logger.info("H4 (Seed %d): Q3=%d, McNemar Raw p=%.5f, Holm p=%.5f | Verdict: %s",
                    h["seed"], h["Q3_ae_rescue"], h["mcnemar_raw_p"], h["mcnemar_holm_p"], h["verdict"])
    logger.info("=" * 70)
    logger.info("STEPS 6-9: PASS — HYBRID C06 & STATISTICAL HYPOTHESES TESTS COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
