"""
cicids2017/src/s23_matched_fpr_analysis.py
-------------------------------------------
Sprint 6 — Step 1: Matched-FPR Analysis Across All Models on CIC-IDS-2017.

Protocol:
  - Nominal false-positive budgets: alpha in {0.1%, 0.5%, 1.0%, 5.0%}
  - Calibration: CALIBRATION = 18,500 benign flows
  - Evaluation control: EVAL_CONTROL = 18,500 held-out benign flows
  - Attack evaluation: PROTECTED_BOT = 1,948 zero-day flows
  - Order-statistic rule: k = floor(alpha * 18500), t = sorted_desc[k], alert: score > t
  - Models evaluated:
      1. Stacking (meta-logistic regression over base models)
      2. Random Forest
      3. IDSNet / MLP
      4. Standard Autoencoder (reconstruction error)
      5. Log1p Autoencoder (mandatory sensitivity variant)
      6. Isolation Forest (anomaly score)
      7. FT-Transformer (full K*=69 variant)
  - Hybrid C06: single reproduced operating point marker C01 OR AE(mu + 3sigma)

Outputs:
  - results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_table.csv
  - results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_summary.json
  - results/cicids2017_revision_v1/matched_fpr/s23_c06_hybrid_marker.json
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import joblib

import numpy as np
import pandas as pd
from scipy.stats import beta, binomtest
from sklearn.metrics import auc, precision_recall_curve, roc_auc_score
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
MODELS_DIR = ROOT / "cicids2017" / "models"
SEL_FEAT_PATH = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection" / "selected_features.json"
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "matched_fpr"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT_DIR / "s23_matched_fpr.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("s23_matched_fpr")

SEEDS = [42, 123, 2024]
BUDGETS = ["0.001", "0.005", "0.01", "0.05"]
PI_STANDARDIZED = 0.0306


# ---------------------------------------------------------------------------
# Statistical utilities
# ---------------------------------------------------------------------------

def clopper_pearson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact Clopper-Pearson 95% binomial confidence interval via Beta distribution."""
    if n == 0:
        return (0.0, 1.0)
    alpha = 1.0 - confidence
    lower = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    upper = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return lower, upper


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score confidence interval for recall."""
    if n == 0:
        return (0.0, 0.0)
    res = binomtest(k, n).proportion_ci(confidence_level=confidence, method="wilson")
    return float(res.low), float(res.high)


def compute_exact_k(budget_str: str, n_cal: int) -> int:
    """k = floor(budget * n_cal) using exact rational Fraction arithmetic."""
    frac = Fraction(str(budget_str))
    return int(math.floor(frac * n_cal))


def calibrate_threshold(cal_scores: np.ndarray, k: int) -> tuple[float, int, float, bool]:
    """
    Calibrate threshold using order statistic rule:
    t = sorted_desc[k] (0-indexed).
    Alert condition: score > t (strict greater).
    """
    n_cal = len(cal_scores)
    sorted_desc = np.sort(cal_scores)[::-1]
    t = float(sorted_desc[k])
    cal_fp = int(np.sum(cal_scores > t))
    realized_cal_fpr = float(cal_fp / n_cal)
    tie_unattainable = bool(cal_fp < k)
    return t, cal_fp, realized_cal_fpr, tie_unattainable


# ---------------------------------------------------------------------------
# PyTorch Model Definitions
# ---------------------------------------------------------------------------

class IDSNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class Autoencoder(nn.Module):
    def __init__(self, input_dim: int = 69):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 12),
            nn.ReLU(),
            nn.Linear(12, 6),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(6, 12),
            nn.ReLU(),
            nn.Linear(12, input_dim),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


class FTTransformerBlock(nn.Module):
    def __init__(self, d_model: int, n_heads: int, ffn_dim: int, dropout: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn  = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn   = nn.Sequential(
            nn.Linear(d_model, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.norm1(x)
        h, _ = self.attn(h, h, h, need_weights=False)
        x = x + h
        h = self.norm2(x)
        h = self.ffn(h)
        x = x + h
        return x


class FTTransformerCIC(nn.Module):
    def __init__(self, n_features: int = 69, d_model: int = 64, n_heads: int = 4,
                 n_blocks: int = 3, ffn_dim: int = 128, dropout: float = 0.1):
        super().__init__()
        self.feat_embed = nn.Linear(1, d_model)
        self.feat_bias  = nn.Parameter(torch.zeros(n_features, d_model))
        self.cls_token  = nn.Parameter(torch.randn(1, 1, d_model))
        self.blocks     = nn.ModuleList([
            FTTransformerBlock(d_model, n_heads, ffn_dim, dropout) for _ in range(n_blocks)
        ])
        self.norm_out = nn.LayerNorm(d_model)
        self.head     = nn.Linear(d_model, 1)

    def forward(self, x):
        B, F = x.shape
        tokens = self.feat_embed(x.unsqueeze(-1)) + self.feat_bias.unsqueeze(0)
        cls    = self.cls_token.expand(B, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        for block in self.blocks:
            tokens = block(tokens)
        cls_out = self.norm_out(tokens[:, 0, :])
        return self.head(cls_out).squeeze(-1)


# ---------------------------------------------------------------------------
# Continuous Scoring Functions
# ---------------------------------------------------------------------------

def score_models_for_seed(seed: int, X_cal: pd.DataFrame, X_eval: pd.DataFrame, X_bot: pd.DataFrame,
                          selected_features: list[str], device: torch.device):
    """Compute continuous anomaly scores/probabilities for all models for a given seed."""
    logger.info("Scoring models for seed=%d...", seed)
    model_dir = MODELS_DIR / f"seed_{seed}"

    # Scalers
    scaler_std = joblib.load(model_dir / "nn_scaler.pkl")
    scaler_log1p = joblib.load(model_dir / "ae_log1p_scaler.pkl")

    X_cal_raw = X_cal[selected_features].values.astype(np.float32)
    X_eval_raw = X_eval[selected_features].values.astype(np.float32)
    X_bot_raw = X_bot[selected_features].values.astype(np.float32)

    X_cal_std = scaler_std.transform(X_cal_raw)
    X_eval_std = scaler_std.transform(X_eval_raw)
    X_bot_std = scaler_std.transform(X_bot_raw)

    # Log1p
    X_cal_l1p = scaler_log1p.transform(np.log1p(np.clip(X_cal_raw, 0, None)))
    X_eval_l1p = scaler_log1p.transform(np.log1p(np.clip(X_eval_raw, 0, None)))
    X_bot_l1p = scaler_log1p.transform(np.log1p(np.clip(X_bot_raw, 0, None)))

    scores = {}

    # 1. Random Forest
    rf = joblib.load(model_dir / "rf_model.pkl")
    scores["random_forest"] = {
        "cal": rf.predict_proba(X_cal_raw)[:, 1],
        "eval": rf.predict_proba(X_eval_raw)[:, 1],
        "bot": rf.predict_proba(X_bot_raw)[:, 1],
    }

    # 2. Decision Tree & Linear SVM (needed for Stacking meta-LR)
    dt = joblib.load(model_dir / "dt_model.pkl")
    dt_cal_p = dt.predict_proba(X_cal_raw)[:, 1]
    dt_eval_p = dt.predict_proba(X_eval_raw)[:, 1]
    dt_bot_p = dt.predict_proba(X_bot_raw)[:, 1]

    svm = joblib.load(model_dir / "svm_model.pkl")
    # SVM decision function sigmoid
    svm_cal_df = svm.decision_function(X_cal_std)
    svm_eval_df = svm.decision_function(X_eval_std)
    svm_bot_df = svm.decision_function(X_bot_std)
    svm_cal_p = 1.0 / (1.0 + np.exp(-svm_cal_df))
    svm_eval_p = 1.0 / (1.0 + np.exp(-svm_eval_df))
    svm_bot_p = 1.0 / (1.0 + np.exp(-svm_bot_df))

    # 3. IDSNet / MLP
    idsnet = IDSNet(input_dim=len(selected_features)).to(device)
    idsnet.load_state_dict(torch.load(model_dir / "nn_model.pt", map_location=device))
    idsnet.eval()
    with torch.no_grad():
        nn_cal_p = torch.sigmoid(idsnet(torch.tensor(X_cal_std, device=device))).cpu().numpy()
        nn_eval_p = torch.sigmoid(idsnet(torch.tensor(X_eval_std, device=device))).cpu().numpy()
        nn_bot_p = torch.sigmoid(idsnet(torch.tensor(X_bot_std, device=device))).cpu().numpy()
    scores["idsnet"] = {"cal": nn_cal_p, "eval": nn_eval_p, "bot": nn_bot_p}

    # 4. Stacking Ensemble
    meta_lr = joblib.load(model_dir / "meta_lr.pkl")
    stack_cal_X = np.column_stack([dt_cal_p, scores["random_forest"]["cal"], svm_cal_p, nn_cal_p])
    stack_eval_X = np.column_stack([dt_eval_p, scores["random_forest"]["eval"], svm_eval_p, nn_eval_p])
    stack_bot_X = np.column_stack([dt_bot_p, scores["random_forest"]["bot"], svm_bot_p, nn_bot_p])

    scores["stacking"] = {
        "cal": meta_lr.predict_proba(stack_cal_X)[:, 1],
        "eval": meta_lr.predict_proba(stack_eval_X)[:, 1],
        "bot": meta_lr.predict_proba(stack_bot_X)[:, 1],
    }

    # 5. Standard Autoencoder
    ae_std = Autoencoder(input_dim=len(selected_features)).to(device)
    ae_std.load_state_dict(torch.load(model_dir / "ae_standard_model.pt", map_location=device))
    ae_std.eval()
    with torch.no_grad():
        ae_std_cal_rec = ae_std(torch.tensor(X_cal_std, device=device)).cpu().numpy()
        ae_std_eval_rec = ae_std(torch.tensor(X_eval_std, device=device)).cpu().numpy()
        ae_std_bot_rec = ae_std(torch.tensor(X_bot_std, device=device)).cpu().numpy()
    scores["autoencoder_standard"] = {
        "cal": ((X_cal_std - ae_std_cal_rec) ** 2).mean(axis=1),
        "eval": ((X_eval_std - ae_std_eval_rec) ** 2).mean(axis=1),
        "bot": ((X_bot_std - ae_std_bot_rec) ** 2).mean(axis=1),
    }

    # 6. Log1p Autoencoder (Sensitivity Variant)
    ae_l1p = Autoencoder(input_dim=len(selected_features)).to(device)
    ae_l1p.load_state_dict(torch.load(model_dir / "ae_log1p_model.pt", map_location=device))
    ae_l1p.eval()
    with torch.no_grad():
        ae_l1p_cal_rec = ae_l1p(torch.tensor(X_cal_l1p, device=device)).cpu().numpy()
        ae_l1p_eval_rec = ae_l1p(torch.tensor(X_eval_l1p, device=device)).cpu().numpy()
        ae_l1p_bot_rec = ae_l1p(torch.tensor(X_bot_l1p, device=device)).cpu().numpy()
    scores["autoencoder_log1p"] = {
        "cal": ((X_cal_l1p - ae_l1p_cal_rec) ** 2).mean(axis=1),
        "eval": ((X_eval_l1p - ae_l1p_eval_rec) ** 2).mean(axis=1),
        "bot": ((X_bot_l1p - ae_l1p_bot_rec) ** 2).mean(axis=1),
    }

    # 7. Isolation Forest
    if_model = joblib.load(model_dir / "if_model.joblib")
    # Higher anomaly score = more anomalous
    scores["isolation_forest"] = {
        "cal": -if_model.score_samples(X_cal_std),
        "eval": -if_model.score_samples(X_eval_std),
        "bot": -if_model.score_samples(X_bot_std),
    }

    # 8. FT-Transformer (full K*=69)
    ft_dir = MODELS_DIR / "ft_transformer" / "full" / f"seed_{seed}"
    ft_scaler = joblib.load(ft_dir / "ft_scaler.pkl")
    X_cal_ft = ft_scaler.transform(X_cal_raw)
    X_eval_ft = ft_scaler.transform(X_eval_raw)
    X_bot_ft = ft_scaler.transform(X_bot_raw)

    ft_model = FTTransformerCIC(n_features=len(selected_features)).to(device)
    ft_model.load_state_dict(torch.load(ft_dir / "ft_model.pt", map_location=device))
    ft_model.eval()

    def ft_predict_batches(X_arr, batch_size=2048):
        preds = []
        with torch.no_grad():
            for i in range(0, len(X_arr), batch_size):
                xb = torch.tensor(X_arr[i:i + batch_size], device=device)
                pb = torch.sigmoid(ft_model(xb)).cpu().numpy()
                preds.append(pb)
        return np.concatenate(preds)

    scores["ft_transformer"] = {
        "cal": ft_predict_batches(X_cal_ft),
        "eval": ft_predict_batches(X_eval_ft),
        "bot": ft_predict_batches(X_bot_ft),
    }

    return scores


# ---------------------------------------------------------------------------
# Main Execution Pipeline
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 6 — STEP 1: MATCHED-FPR ANALYSIS PIPELINE")
    logger.info("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Compute device: %s", device)

    # 1. Load Splits
    logger.info("Loading dataset splits...")
    df_cal = pd.read_csv(SPLITS_DIR / "calibration.csv")
    df_eval = pd.read_csv(SPLITS_DIR / "eval_control.csv")
    df_bot = pd.read_csv(SPLITS_DIR / "protected_bot.csv")

    n_cal = len(df_cal)
    n_eval = len(df_eval)
    n_bot = len(df_bot)

    logger.info("Split sizes: CALIBRATION=%d  EVAL_CONTROL=%d  PROTECTED_BOT=%d", n_cal, n_eval, n_bot)
    assert n_cal == 18500, f"Expected 18,500 cal rows, got {n_cal}"
    assert n_eval == 18500, f"Expected 18,500 eval rows, got {n_eval}"
    assert n_bot == 1948, f"Expected 1,948 bot rows, got {n_bot}"

    pi_natural = n_bot / (n_bot + n_eval)
    logger.info("Natural zero-day evaluation prevalence pi_natural: %.6f (%.2f%%)", pi_natural, pi_natural * 100.0)
    logger.info("Standardized prevalence pi_std: %.4f (%.2f%%)", PI_STANDARDIZED, PI_STANDARDIZED * 100.0)

    # Load Selected Features
    with open(SEL_FEAT_PATH, "r", encoding="utf-8") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    logger.info("Loaded K*=%d selected features.", len(selected_features))
    assert len(selected_features) == 69, f"Expected 69 features, got {len(selected_features)}"

    table_rows = []
    c06_records = []

    for seed in SEEDS:
        scores = score_models_for_seed(seed, df_cal, df_eval, df_bot, selected_features, device)

        # Matched-FPR budget sweep for each model
        for model_name, model_scores in scores.items():
            cal_s = model_scores["cal"]
            eval_s = model_scores["eval"]
            bot_s = model_scores["bot"]

            # Compute overall AUCs on combined evaluation set (EVAL_CONTROL + PROTECTED_BOT)
            y_eval_true = np.zeros(n_eval, dtype=np.int32)
            y_bot_true = np.ones(n_bot, dtype=np.int32)
            y_combined_true = np.concatenate([y_eval_true, y_bot_true])
            scores_combined = np.concatenate([eval_s, bot_s])

            try:
                roc_auc = float(roc_auc_score(y_combined_true, scores_combined))
            except Exception:
                roc_auc = float("nan")

            try:
                prec_arr, rec_arr, _ = precision_recall_curve(y_combined_true, scores_combined)
                pr_auc = float(auc(rec_arr, prec_arr))
            except Exception:
                pr_auc = float("nan")

            for budget_str in BUDGETS:
                nominal_alpha = float(budget_str)
                k = compute_exact_k(budget_str, n_cal)
                t, cal_fp, realized_cal_fpr, tie_unattainable = calibrate_threshold(cal_s, k)

                # Realized performance on EVAL_CONTROL (benign false positives)
                eval_fp = int(np.sum(eval_s > t))
                realized_fpr = float(eval_fp / n_eval)
                fpr_ci_l, fpr_ci_u = clopper_pearson_ci(eval_fp, n_eval)

                # Realized performance on PROTECTED_BOT (detections / true positives)
                eval_tp = int(np.sum(bot_s > t))
                recall = float(eval_tp / n_bot)
                rec_ci_l, rec_ci_u = wilson_ci(eval_tp, n_bot)

                # Precision
                prec_natural = float(eval_tp / (eval_tp + eval_fp)) if (eval_tp + eval_fp) > 0 else 0.0
                if (recall * PI_STANDARDIZED + realized_fpr * (1.0 - PI_STANDARDIZED)) > 0:
                    prec_std = float((recall * PI_STANDARDIZED) /
                                     (recall * PI_STANDARDIZED + realized_fpr * (1.0 - PI_STANDARDIZED)))
                else:
                    prec_std = 0.0

                # F1 at natural prevalence
                f1_natural = (2.0 * prec_natural * recall / (prec_natural + recall)) if (prec_natural + recall) > 0 else 0.0

                alerts_per_10k = float(realized_fpr * 10000.0)

                # Resolution flag: < 20 expected false alarms on EVAL_CONTROL (18500 * 0.001 = 18.5)
                is_low_res = bool((nominal_alpha * n_eval) < 20.0)
                res_flag = "LOW_RESOLUTION" if is_low_res else "ADEQUATE_RESOLUTION"

                table_rows.append({
                    "model": model_name,
                    "seed": seed,
                    "nominal_budget": nominal_alpha,
                    "nominal_budget_str": budget_str,
                    "k_rational": k,
                    "threshold": t,
                    "cal_fp": cal_fp,
                    "realized_cal_fpr": realized_cal_fpr,
                    "tie_unattainable": tie_unattainable,
                    "n_eval_control": n_eval,
                    "eval_fp": eval_fp,
                    "realized_fpr": realized_fpr,
                    "fpr_ci_lower": fpr_ci_l,
                    "fpr_ci_upper": fpr_ci_u,
                    "n_protected_bot": n_bot,
                    "eval_tp": eval_tp,
                    "recall": recall,
                    "recall_ci_lower": rec_ci_l,
                    "recall_ci_upper": rec_ci_u,
                    "precision_natural": prec_natural,
                    "precision_standardized": prec_std,
                    "f1_natural": f1_natural,
                    "alerts_per_10k": alerts_per_10k,
                    "roc_auc": roc_auc,
                    "pr_auc": pr_auc,
                    "resolution_flag": res_flag,
                })

        # Evaluate Hybrid C06 marker for this seed
        # C06 = Stacking(p > 0.5) OR Standard AE(re > mu + 3*sigma on CALIBRATION)
        stack_p_eval = scores["stacking"]["eval"]
        stack_p_bot = scores["stacking"]["bot"]
        ae_rec_cal = scores["autoencoder_standard"]["cal"]
        ae_rec_eval = scores["autoencoder_standard"]["eval"]
        ae_rec_bot = scores["autoencoder_standard"]["bot"]

        ae_mu = float(np.mean(ae_rec_cal))
        ae_sigma = float(np.std(ae_rec_cal, ddof=0))
        ae_thresh_3sigma = ae_mu + 3.0 * ae_sigma

        # Binary decisions
        stack_det_eval = (stack_p_eval > 0.5)
        stack_det_bot = (stack_p_bot > 0.5)

        ae_det_eval = (ae_rec_eval > ae_thresh_3sigma)
        ae_det_bot = (ae_rec_bot > ae_thresh_3sigma)

        c06_det_eval = stack_det_eval | ae_det_eval
        c06_det_bot = stack_det_bot | ae_det_bot

        # Quadrants on PROTECTED_BOT
        q1 = int(np.sum(stack_det_bot & ae_det_bot))
        q2 = int(np.sum(stack_det_bot & (~ae_det_bot)))
        q3 = int(np.sum((~stack_det_bot) & ae_det_bot))
        q4 = int(np.sum((~stack_det_bot) & (~ae_det_bot)))
        assert q1 + q2 + q3 + q4 == n_bot

        c06_tp = int(np.sum(c06_det_bot))
        c06_rec = float(c06_tp / n_bot)
        c06_rec_ci_l, c06_rec_ci_u = wilson_ci(c06_tp, n_bot)

        c06_fp = int(np.sum(c06_det_eval))
        c06_fpr = float(c06_fp / n_eval)
        c06_fpr_ci_l, c06_fpr_ci_u = clopper_pearson_ci(c06_fp, n_eval)

        extra_fp = c06_fp - int(np.sum(stack_det_eval))
        alerts_10k = float(c06_fpr * 10000.0)

        prec_nat = float(c06_tp / (c06_tp + c06_fp)) if (c06_tp + c06_fp) > 0 else 0.0
        if (c06_rec * PI_STANDARDIZED + c06_fpr * (1.0 - PI_STANDARDIZED)) > 0:
            prec_std = float((c06_rec * PI_STANDARDIZED) /
                             (c06_rec * PI_STANDARDIZED + c06_fpr * (1.0 - PI_STANDARDIZED)))
        else:
            prec_std = 0.0

        c06_records.append({
            "seed": seed,
            "operating_point": "C01(p>0.5) OR AE(mu+3sigma)",
            "ae_threshold_3sigma": ae_thresh_3sigma,
            "Q1_both": q1,
            "Q2_stacking_only": q2,
            "Q3_ae_rescue": q3,
            "Q4_neither": q4,
            "total_bot": n_bot,
            "bot_detections": c06_tp,
            "recall": c06_rec,
            "recall_ci": [c06_rec_ci_l, c06_rec_ci_u],
            "control_fp": c06_fp,
            "extra_fp_over_stacking": extra_fp,
            "realized_fpr": c06_fpr,
            "fpr_ci": [c06_fpr_ci_l, c06_fpr_ci_u],
            "alerts_per_10k": alerts_10k,
            "precision_natural": prec_nat,
            "precision_standardized": prec_std,
        })

    # Save Results
    df_results = pd.DataFrame(table_rows)
    csv_path = OUT_DIR / "s23_matched_fpr_table.csv"
    df_results.to_csv(csv_path, index=False)
    logger.info("Saved matched-FPR table to %s (%d rows).", csv_path, len(df_results))

    c06_path = OUT_DIR / "s23_c06_hybrid_marker.json"
    with open(c06_path, "w", encoding="utf-8") as f:
        json.dump(c06_records, f, indent=2)
    logger.info("Saved C06 hybrid marker records to %s.", c06_path)

    # Build Summary Across Seeds
    summary = {
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 6,
        "step": "s23_matched_fpr_analysis",
        "dataset": "CIC-IDS-2017",
        "seeds": SEEDS,
        "budgets": BUDGETS,
        "n_cal": n_cal,
        "n_eval_control": n_eval,
        "n_protected_bot": n_bot,
        "pi_natural": pi_natural,
        "pi_standardized": PI_STANDARDIZED,
        "models_evaluated": list(scores.keys()),
        "low_resolution_budgets": ["0.001"],
        "hybrid_c06_reproduced_marker": c06_records,
    }

    # Model-by-model aggregated means across seeds
    summary["per_model_summary"] = {}
    for model_name in scores.keys():
        m_df = df_results[df_results["model"] == model_name]
        summary["per_model_summary"][model_name] = {}
        for b_str in BUDGETS:
            b_df = m_df[m_df["nominal_budget_str"] == b_str]
            summary["per_model_summary"][model_name][b_str] = {
                "realized_fpr_mean": float(b_df["realized_fpr"].mean()),
                "realized_fpr_std": float(b_df["realized_fpr"].std()),
                "recall_mean": float(b_df["recall"].mean()),
                "recall_std": float(b_df["recall"].std()),
                "alerts_per_10k_mean": float(b_df["alerts_per_10k"].mean()),
                "precision_natural_mean": float(b_df["precision_natural"].mean()),
                "precision_standardized_mean": float(b_df["precision_standardized"].mean()),
                "roc_auc_mean": float(b_df["roc_auc"].mean()),
                "pr_auc_mean": float(b_df["pr_auc"].mean()),
                "resolution_flag": str(b_df["resolution_flag"].iloc[0]),
                "any_tie_unattainable": bool(b_df["tie_unattainable"].any()),
            }

    summary_path = OUT_DIR / "s23_matched_fpr_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Saved summary JSON to %s.", summary_path)
    logger.info("STEP 1 (MATCHED-FPR ANALYSIS): COMPLETE")


if __name__ == "__main__":
    main()
