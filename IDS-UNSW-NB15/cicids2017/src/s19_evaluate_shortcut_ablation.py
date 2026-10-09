"""
cicids2017/src/s19_evaluate_shortcut_ablation.py
-------------------------------------------------
Sprint 5 — Part A, Step 3: Shortcut Ablation Evaluation (H1 / H2)

Evaluates ablated models on DEV_TEST.
Computes:
  1. McNemar's test (paired, exact two-sided) for H1: RF original vs RF ablated
  2. TOST equivalence test for H2: |ΔMacro-F1| < δ=0.01 (materiality bound)
  3. Materiality check: |ΔBot| < 20 flows (1% of 1,948)

Hypotheses:
  H1 (null): Removing shortcuts does NOT significantly change RF error pattern.
             Rejected if McNemar p < 0.05 (shortcuts materially change decisions).
  H2 (null): |ΔMacro-F1| >= δ (shortcuts give non-negligible performance boost).
             TOST equivalence accepted if both one-sided p < 0.05.

Output:
  results/cicids2017_revision_v1/ablation/s19_ablation_evaluation.json
  results/cicids2017_revision_v1/ablation/s19_dev_test_ablation.csv
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
from scipy.stats import binom

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "ablation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s19_ablation_evaluation.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR   = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
MODEL_DIR    = ROOT / "cicids2017" / "models"
ABL_MODEL_DIR = ROOT / "cicids2017" / "models" / "ablated"
SHORTCUT_FILE = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
SUPERVISED_DIR = ROOT / "results" / "cicids2017_revision_v1" / "supervised"

EXPECTED_SHORTCUT_SHA256 = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
H1_SEEDS   = [42, 123, 2024]
ALPHA      = 0.05
DELTA_F1   = 0.01   # Materiality bound for TOST
BOT_N      = 1948   # Protected Bot population
BOT_THRESH = 20     # |ΔBot| materiality threshold (1% of 1948)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# IDSNet (IDENTICAL to sprint 3)
# ---------------------------------------------------------------------------
class IDSNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def predict_idsnet(net, scaler, X, device, threshold=0.5):
    net.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    proba = 1.0 / (1.0 + np.exp(-logits))
    return (proba >= threshold).astype(np.int64), proba


def compute_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    return {
        "macro_f1":  float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_attack": float(f1_score(y_true, y_pred, average="binary", zero_division=0)),
        "fpr":       float(fpr),
        "n_tp": int(tp), "n_fp": int(fp), "n_fn": int(fn), "n_tn": int(tn),
        "confusion_matrix": cm.tolist(),
    }


def exact_mcnemar_p(b: int, c: int) -> float:
    """
    Exact two-sided McNemar test.
    b = cases where original correct, ablated wrong.
    c = cases where original wrong, ablated correct.
    Returns two-sided p-value via exact binomial.
    """
    n = b + c
    if n == 0:
        return 1.0
    # Two-sided: p-value = 2 * min(P(X<=min(b,c)), P(X>=max(b,c))) under H0: p=0.5
    k = min(b, c)
    p_val = 2.0 * float(binom.cdf(k, n, 0.5))
    return min(p_val, 1.0)


def tost_macro_f1(f1_orig: list[float], f1_abl: list[float], delta: float) -> dict:
    """
    TOST equivalence: test if |mean(orig) - mean(abl)| < delta.
    Using paired t-test (two one-sided) across seeds.
    Returns p_lower, p_upper, equivalence_accepted.
    """
    from scipy import stats
    diffs = np.array(f1_orig) - np.array(f1_abl)
    n = len(diffs)
    mean_d = np.mean(diffs)
    se_d   = np.std(diffs, ddof=1) / np.sqrt(n) if n > 1 else 0.0

    if se_d == 0:
        # Exact: equivalence if |mean_d| < delta
        equiv = abs(mean_d) < delta
        return {
            "mean_delta": float(mean_d), "se_delta": 0.0, "n_seeds": n,
            "p_lower": 0.0 if mean_d < delta else 1.0,
            "p_upper": 0.0 if mean_d > -delta else 1.0,
            "equivalence_accepted": equiv,
            "delta": delta,
        }

    df = n - 1
    # H0_lower: mean_d >= delta (upper bound test: t = (mean_d - delta)/se_d)
    t_upper = (mean_d - delta) / se_d
    p_upper = float(stats.t.cdf(t_upper, df=df))  # P(T <= t) under H0_lower

    # H0_upper: mean_d <= -delta (lower bound test: t = (mean_d + delta)/se_d)
    t_lower = (mean_d + delta) / se_d
    p_lower = float(1.0 - stats.t.cdf(t_lower, df=df))  # P(T >= t) under H0_upper

    equiv = (p_lower < ALPHA) and (p_upper < ALPHA)
    return {
        "mean_delta": float(mean_d), "se_delta": float(se_d), "n_seeds": n,
        "t_lower": float(t_lower), "t_upper": float(t_upper),
        "p_lower": float(p_lower), "p_upper": float(p_upper),
        "equivalence_accepted": bool(equiv),
        "delta": delta, "alpha": ALPHA,
    }


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 5 — STEP 3: SHORTCUT ABLATION EVALUATION (H1/H2)")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Preflight shortcut SHA
    actual_sha = sha256_file(SHORTCUT_FILE)
    assert actual_sha == EXPECTED_SHORTCUT_SHA256, f"Shortcut SHA mismatch: {actual_sha}"
    logger.info("Shortcut freeze SHA-256 verified: PASS")

    with open(SHORTCUT_FILE) as f:
        sc_json = json.load(f)
    frozen_shortcuts = sc_json["frozen_shortcut_set"]

    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]

    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]

    ablated_features = [f for f in selected_features if f not in frozen_shortcuts]
    D_ablated = len(ablated_features)
    logger.info("K*=%d  D_ablated=%d  shortcuts=%s", k_star, D_ablated, frozen_shortcuts)

    # Load DEV_TEST
    dev_test_path = SPLITS_DIR / "dev_test.csv"
    logger.info("Loading DEV_TEST: %s", dev_test_path)
    dev_df = pd.read_csv(dev_test_path)
    X_dev_full = dev_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in dev_df.columns:
        y_dev = (dev_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_dev = (dev_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    n_dev_benign = int((y_dev == 0).sum())
    n_dev_attack = int((y_dev == 1).sum())
    logger.info("DEV_TEST: rows=%d  benign=%d  attack=%d", len(y_dev), n_dev_benign, n_dev_attack)

    sel_idx = [feature_list.index(f) for f in selected_features]
    abl_idx = [feature_list.index(f) for f in ablated_features]
    X_dev_sel = X_dev_full[:, sel_idx]    # original K*=69
    X_dev_abl = X_dev_full[:, abl_idx]    # ablated D=67

    # Load PROTECTED_BOT
    bot_path = SPLITS_DIR / "protected_bot.csv"
    logger.info("Loading PROTECTED_BOT: %s", bot_path)
    bot_df = pd.read_csv(bot_path)
    X_bot_full = bot_df[feature_list].to_numpy(dtype=np.float64)
    X_bot_sel  = X_bot_full[:, sel_idx]
    X_bot_abl  = X_bot_full[:, abl_idx]
    logger.info("PROTECTED_BOT: rows=%d", len(bot_df))

    # Load original dev_test results (Sprint 3 baseline)
    orig_eval_path = SUPERVISED_DIR / "dev_test_evaluation.json"
    with open(orig_eval_path) as f:
        orig_eval = json.load(f)

    all_seed_results = {}
    rf_f1_orig_list  = []
    rf_f1_abl_list   = []
    mcnemar_results  = []

    for seed in H1_SEEDS:
        logger.info("-" * 50)
        logger.info("EVALUATING ABLATED MODELS | seed=%d", seed)
        logger.info("-" * 50)

        # --- Load original RF predictions from stored metadata ---
        orig_r = orig_eval["per_seed_results"][str(seed)]
        rf_orig_f1 = orig_r["rf"]["macro_f1"]
        rf_orig_n_tp = orig_r["rf"]["n_tp"]
        rf_orig_n_fp = orig_r["rf"]["n_fp"]
        rf_orig_n_fn = orig_r["rf"]["n_fn"]
        rf_orig_n_tn = orig_r["rf"]["n_tn"]
        logger.info("Original RF seed=%d: macro_f1=%.4f", seed, rf_orig_f1)

        # Need original RF predictions for McNemar — reload original RF model
        rf_orig_path = MODEL_DIR / f"seed_{seed}" / "rf_model.pkl"
        with open(rf_orig_path, "rb") as f:
            rf_orig = pickle.load(f)
        y_rf_orig = rf_orig.predict(X_dev_sel)
        y_bot_rf_orig = rf_orig.predict(X_bot_sel)
        det_bot_rf_orig = int(np.sum(y_bot_rf_orig == 1))
        del rf_orig

        # Load ablated RF
        rf_abl_path = MODEL_DIR / "ablated" / f"seed_{seed}" / "rf_model.pkl"
        with open(rf_abl_path, "rb") as f:
            rf_abl = pickle.load(f)
        y_rf_abl = rf_abl.predict(X_dev_abl)
        y_bot_rf_abl = rf_abl.predict(X_bot_abl)
        det_bot_rf_abl = int(np.sum(y_bot_rf_abl == 1))
        del rf_abl

        delta_bot_rf = det_bot_rf_orig - det_bot_rf_abl
        logger.info("PROTECTED_BOT seed=%d RF: orig=%d/%d  abl=%d/%d  ΔBot=%d",
                    seed, det_bot_rf_orig, BOT_N, det_bot_rf_abl, BOT_N, delta_bot_rf)

        # Ablated metrics
        rf_abl_metrics = compute_metrics(y_dev, y_rf_abl)
        logger.info("Ablated RF seed=%d: macro_f1=%.4f", seed, rf_abl_metrics["macro_f1"])

        rf_f1_orig_list.append(rf_orig_f1)
        rf_f1_abl_list.append(rf_abl_metrics["macro_f1"])

        # McNemar: compute b and c
        # b = original correct, ablated wrong
        # c = original wrong, ablated correct
        orig_correct = (y_rf_orig == y_dev).astype(int)
        abl_correct  = (y_rf_abl  == y_dev).astype(int)
        b = int(((orig_correct == 1) & (abl_correct == 0)).sum())
        c = int(((orig_correct == 0) & (abl_correct == 1)).sum())
        mcnemar_p = exact_mcnemar_p(b, c)
        logger.info("McNemar seed=%d: b=%d  c=%d  p=%.6f  (reject H0: p<%.2f: %s)",
                    seed, b, c, mcnemar_p, ALPHA, mcnemar_p < ALPHA)

        mcnemar_results.append({
            "seed": seed,
            "b_orig_correct_abl_wrong": b,
            "c_orig_wrong_abl_correct": c,
            "n_discordant": b + c,
            "mcnemar_p": mcnemar_p,
            "H1_rejected_shortcuts_matter": bool(mcnemar_p < ALPHA),
        })

        # Load ablated SVM
        svm_abl_path = MODEL_DIR / "ablated" / f"seed_{seed}" / "svm_model.pkl"
        svm_sc_path  = MODEL_DIR / "ablated" / f"seed_{seed}" / "svm_scaler.pkl"
        with open(svm_abl_path, "rb") as f:
            svm_abl = pickle.load(f)
        with open(svm_sc_path, "rb") as f:
            svm_sc_abl = pickle.load(f)
        X_dev_abl_sc = svm_sc_abl.transform(X_dev_abl)
        y_svm_abl = svm_abl.predict(X_dev_abl_sc)
        svm_abl_metrics = compute_metrics(y_dev, y_svm_abl)
        del svm_abl, svm_sc_abl

        # Load ablated DT
        dt_abl_path = MODEL_DIR / "ablated" / f"seed_{seed}" / "dt_model.pkl"
        with open(dt_abl_path, "rb") as f:
            dt_abl = pickle.load(f)
        y_dt_abl = dt_abl.predict(X_dev_abl)
        dt_abl_metrics = compute_metrics(y_dev, y_dt_abl)
        del dt_abl

        # Load ablated NN
        nn_path    = MODEL_DIR / "ablated" / f"seed_{seed}" / "nn_model.pt"
        nn_sc_path = MODEL_DIR / "ablated" / f"seed_{seed}" / "nn_scaler.pkl"
        with open(nn_sc_path, "rb") as f:
            nn_scaler = pickle.load(f)
        net = IDSNet(input_dim=D_ablated).to(device)
        net.load_state_dict(torch.load(nn_path, map_location=device, weights_only=True))
        y_nn_abl, _ = predict_idsnet(net, nn_scaler, X_dev_abl, device)
        nn_abl_metrics = compute_metrics(y_dev, y_nn_abl)
        del net

        # Load ablated stacking meta-LR
        meta_path = MODEL_DIR / "ablated" / f"seed_{seed}" / "meta_lr.pkl"
        oof_abl_path = OUT_DIR / f"oof_abl_seed{seed}.csv"
        with open(meta_path, "rb") as f:
            meta_lr = pickle.load(f)

        # For stacking inference on dev_test:
        # Need all 4 base model probabilities/scores on dev_test (ablated)
        rf2 = pickle.load(open(MODEL_DIR / "ablated" / f"seed_{seed}" / "rf_model.pkl", "rb"))
        dt2 = pickle.load(open(MODEL_DIR / "ablated" / f"seed_{seed}" / "dt_model.pkl", "rb"))
        svm2 = pickle.load(open(MODEL_DIR / "ablated" / f"seed_{seed}" / "svm_model.pkl", "rb"))
        sc2  = pickle.load(open(MODEL_DIR / "ablated" / f"seed_{seed}" / "svm_scaler.pkl", "rb"))
        net2 = IDSNet(input_dim=D_ablated).to(device)
        net2.load_state_dict(torch.load(MODEL_DIR / "ablated" / f"seed_{seed}" / "nn_model.pt",
                                         map_location=device, weights_only=True))

        dt_prob_dev   = dt2.predict_proba(X_dev_abl)[:, 1]
        rf_prob_dev   = rf2.predict_proba(X_dev_abl)[:, 1]
        svm_score_dev = svm2.decision_function(sc2.transform(X_dev_abl))
        net2.eval()
        with torch.no_grad():
            nn_logits = net2(torch.tensor(
                nn_scaler.transform(X_dev_abl),
                dtype=torch.float32).to(device)).cpu().numpy()
        nn_prob_dev = 1.0 / (1.0 + np.exp(-nn_logits))

        # Stacking on PROTECTED_BOT
        dt_prob_bot   = dt2.predict_proba(X_bot_abl)[:, 1]
        rf_prob_bot   = rf2.predict_proba(X_bot_abl)[:, 1]
        svm_score_bot = svm2.decision_function(sc2.transform(X_bot_abl))
        with torch.no_grad():
            nn_logits_bot = net2(torch.tensor(
                nn_scaler.transform(X_bot_abl),
                dtype=torch.float32).to(device)).cpu().numpy()
        nn_prob_bot = 1.0 / (1.0 + np.exp(-nn_logits_bot))
        del rf2, dt2, svm2, sc2, net2

        meta_X_dev = np.column_stack([dt_prob_dev, rf_prob_dev, svm_score_dev, nn_prob_dev])
        y_stack_abl = meta_lr.predict(meta_X_dev)
        stack_abl_metrics = compute_metrics(y_dev, y_stack_abl)

        meta_X_bot = np.column_stack([dt_prob_bot, rf_prob_bot, svm_score_bot, nn_prob_bot])
        y_stack_bot_abl = meta_lr.predict(meta_X_bot)
        det_bot_stack_abl = int(np.sum(y_stack_bot_abl == 1))
        det_bot_stack_orig = 0  # from Sprint 4 zero-day evaluation
        delta_bot_stack = det_bot_stack_orig - det_bot_stack_abl
        del meta_lr

        seed_record = {
            "seed": seed,
            "n_dev_total": len(y_dev), "n_dev_benign": n_dev_benign, "n_dev_attack": n_dev_attack,
            "rf_orig_macro_f1":  rf_orig_f1,
            "rf_abl_macro_f1":   rf_abl_metrics["macro_f1"],
            "delta_rf_f1":       rf_orig_f1 - rf_abl_metrics["macro_f1"],
            "dt_abl_metrics":    dt_abl_metrics,
            "rf_abl_metrics":    rf_abl_metrics,
            "svm_abl_metrics":   svm_abl_metrics,
            "nn_abl_metrics":    nn_abl_metrics,
            "stacking_abl_metrics": stack_abl_metrics,
            "zero_day_bot": {
                "rf_orig_detected": det_bot_rf_orig,
                "rf_abl_detected": det_bot_rf_abl,
                "delta_bot_rf": delta_bot_rf,
                "rf_bot_material": bool(abs(delta_bot_rf) >= BOT_THRESH),
                "stack_orig_detected": det_bot_stack_orig,
                "stack_abl_detected": det_bot_stack_abl,
                "delta_bot_stack": delta_bot_stack,
                "stack_bot_material": bool(abs(delta_bot_stack) >= BOT_THRESH),
            },
            "mcnemar": mcnemar_results[-1],
        }
        all_seed_results[str(seed)] = seed_record
        logger.info("Seed %d | RF: orig=%.4f  abl=%.4f  delta=%.4f | Stack abl=%.4f",
                    seed, rf_orig_f1, rf_abl_metrics["macro_f1"],
                    rf_orig_f1 - rf_abl_metrics["macro_f1"], stack_abl_metrics["macro_f1"])

    # --- TOST equivalence test across seeds ---
    tost_result = tost_macro_f1(rf_f1_orig_list, rf_f1_abl_list, DELTA_F1)
    logger.info("TOST | mean_delta=%.5f  se=%.5f  equiv_accepted=%s",
                tost_result["mean_delta"], tost_result["se_delta"],
                tost_result["equivalence_accepted"])

    # Materiality summary
    delta_f1_per_seed = [r["delta_rf_f1"] for r in all_seed_results.values()]
    mean_delta_f1 = float(np.mean(delta_f1_per_seed))
    material_f1 = abs(mean_delta_f1) >= DELTA_F1

    # H1 verdict
    h1_votes = [r["mcnemar"]["H1_rejected_shortcuts_matter"] for r in all_seed_results.values()]
    h1_majority = sum(h1_votes) >= 2  # majority of 3 seeds

    # H2 verdict
    h2_equiv_accepted = tost_result["equivalence_accepted"]

    logger.info("=" * 70)
    logger.info("H1 VERDICT: McNemar rejects H0 in %d/3 seeds → majority=%s "
                "(shortcuts SIGNIFICANTLY change errors: %s)",
                sum(h1_votes), h1_majority,
                "CONFIRMED" if h1_majority else "NOT CONFIRMED")
    logger.info("H2 VERDICT: TOST equivalence=%s  mean_ΔF1=%.5f  δ=%.3f "
                "(shortcuts give negligible F1 boost: %s)",
                h2_equiv_accepted, mean_delta_f1, DELTA_F1,
                "CONFIRMED" if h2_equiv_accepted else "NOT CONFIRMED")
    logger.info("=" * 70)

    out_data = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 5,
        "step": "s19_evaluate_shortcut_ablation",
        "frozen_shortcuts": frozen_shortcuts,
        "shortcut_sha256_verified": EXPECTED_SHORTCUT_SHA256,
        "k_star_original": k_star,
        "D_ablated": D_ablated,
        "alpha": ALPHA,
        "delta_materiality": DELTA_F1,
        "bot_n": BOT_N,
        "bot_thresh": BOT_THRESH,
        "seeds": H1_SEEDS,
        "per_seed_results": all_seed_results,
        "mcnemar_per_seed": mcnemar_results,
        "tost_rf_macro_f1": tost_result,
        "mean_delta_rf_f1": mean_delta_f1,
        "material_f1_change": bool(material_f1),
        "H1_verdict": {
            "description": "Removing shortcuts does NOT significantly change RF error pattern",
            "rejected_count": sum(h1_votes),
            "n_seeds": len(H1_SEEDS),
            "majority_rejected": bool(h1_majority),
            "conclusion": "SHORTCUTS SIGNIFICANTLY CHANGE ERRORS" if h1_majority
                          else "SHORTCUTS DO NOT SIGNIFICANTLY CHANGE ERRORS",
        },
        "H2_verdict": {
            "description": "|ΔMacro-F1| < 0.01 (shortcuts give negligible boost)",
            "tost_equivalence_accepted": bool(h2_equiv_accepted),
            "mean_delta_rf_f1": mean_delta_f1,
            "delta": DELTA_F1,
            "conclusion": "SHORTCUT CONTRIBUTION IS NEGLIGIBLE (H2 CONFIRMED)" if h2_equiv_accepted
                          else "SHORTCUT CONTRIBUTION IS MATERIAL (H2 NOT CONFIRMED)",
        },
    }

    out_path = OUT_DIR / "s19_ablation_evaluation.json"
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    logger.info("Ablation evaluation saved: %s", out_path)
    logger.info("STEP 3 (ABLATION EVALUATION): PASS")
    print(f"\n[S19 COMPLETE] H1: majority_rejected={h1_majority}  H2: equiv={h2_equiv_accepted}")
    return out_data


if __name__ == "__main__":
    main()
