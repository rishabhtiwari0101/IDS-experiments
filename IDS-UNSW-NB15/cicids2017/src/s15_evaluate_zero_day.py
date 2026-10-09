"""
cicids2017/src/s15_evaluate_zero_day.py
----------------------------------------
Sprint 4 — Step 5: Pure Inference Zero-Day Evaluation

PRECONDITIONS:
- All models (Base, Stacking, Standard AE, Log1p AE, IF) and thresholds are frozen.
- No model is retrained, no scaler fit, no threshold calibrated in this script.
- Evaluates:
    - Primary: PROTECTED_BOT (N = 1,948) + EVAL_CONTROL (N = 18,500)
    - Secondary: UNSEEN_XSS (N = 652) + EVAL_CONTROL
    - Secondary: UNSEEN_INFILTRATION (N = 36) + EVAL_CONTROL
- Detectors:
    - DT, RF, Linear SVM, IDSNet, Stacking (Meta-LR)
    - Standard AE (tau_mu3sigma)
    - Log1p AE (tau_mu3sigma)
    - Isolation Forest (tau_mu3sigma)
- Metrics:
    - detections, misses, recall, exact 95% Clopper-Pearson CI
    - benign FPR on EVAL_CONTROL, alerts / 10,000 benign flows
    - natural precision
    - standardized precision using pi = 0.0306:
        Precision_std = (Recall * pi) / (Recall * pi + FPR * (1 - pi))

Output:
    results/cicids2017_revision_v1/zero_day/
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy.stats as st
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from cicids2017.src.s12_train_autoencoder import Autoencoder, INPUT_DIM

# Directories
ZERO_DAY_DIR = ROOT / "results" / "cicids2017_revision_v1" / "zero_day"
MODEL_DIR    = ROOT / "cicids2017" / "models"
SPLITS_DIR   = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
CALIB_DIR    = ROOT / "results" / "cicids2017_revision_v1" / "calibration"
AE_DIR       = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder"

ZERO_DAY_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ZERO_DAY_DIR / "s15_zero_day_eval.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SEEDS = [42, 123, 2024]
PI_PREVALENCE = 0.0306
SUPERVISED_THRESHOLD = 0.5
BATCH_SIZE = 256


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided Clopper-Pearson confidence interval."""
    if n == 0:
        return (0.0, 0.0)
    res = st.binomtest(k, n).proportion_ci(confidence_level=1.0 - alpha, method="exact")
    return float(res.low), float(res.high)


class IDSNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def predict_idsnet(net: IDSNet, scaler: StandardScaler,
                   X: np.ndarray, device: torch.device,
                   threshold: float = SUPERVISED_THRESHOLD) -> tuple[np.ndarray, np.ndarray]:
    net.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    proba = 1.0 / (1.0 + np.exp(-logits))
    pred  = (proba >= threshold).astype(np.int64)
    return pred, proba


def compute_detector_metrics(y_pred_attack: np.ndarray,
                             y_pred_control: np.ndarray,
                             n_attack: int,
                             n_control: int,
                             detector_name: str,
                             seed: int,
                             attack_set_name: str) -> dict[str, Any]:
    """
    Computes detections, misses, recall, Clopper-Pearson CI, FPR, alerts/10k,
    natural precision, and standardized precision (pi = 0.0306).
    """
    det = int(np.sum(y_pred_attack == 1))
    miss = int(n_attack - det)
    recall = float(det / n_attack) if n_attack > 0 else 0.0
    rec_ci_l, rec_ci_u = clopper_pearson_ci(det, n_attack)

    fp = int(np.sum(y_pred_control == 1))
    fpr = float(fp / n_control) if n_control > 0 else 0.0
    fpr_ci_l, fpr_ci_u = clopper_pearson_ci(fp, n_control)
    alerts_per_10k = float(fpr * 10000.0)

    # Natural precision on test mix (TP / (TP + FP))
    tp = det
    if (tp + fp) > 0:
        prec_natural = float(tp / (tp + fp))
    else:
        prec_natural = 0.0

    # Standardized prevalence precision (pi = 0.0306)
    # Precision_std = (Recall * pi) / (Recall * pi + FPR * (1 - pi))
    denom_std = (recall * PI_PREVALENCE) + (fpr * (1.0 - PI_PREVALENCE))
    if denom_std > 0.0:
        prec_std = float((recall * PI_PREVALENCE) / denom_std)
    else:
        prec_std = 0.0

    return {
        "detector": detector_name,
        "seed": seed,
        "attack_set": attack_set_name,
        "n_attack": n_attack,
        "n_control": n_control,
        "detections": det,
        "misses": miss,
        "recall": recall,
        "recall_ci_lower_95": rec_ci_l,
        "recall_ci_upper_95": rec_ci_u,
        "control_fps": fp,
        "control_fpr": fpr,
        "control_fpr_ci_lower_95": fpr_ci_l,
        "control_fpr_ci_upper_95": fpr_ci_u,
        "alerts_per_10k": alerts_per_10k,
        "precision_natural": prec_natural,
        "precision_standardized": prec_std,
        "pi_prevalence": PI_PREVALENCE,
    }


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4 — STEP 5: PURE INFERENCE ZERO-DAY EVALUATION")
    logger.info("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Inference Device: %s", device)

    # 1. Load feature schemas
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = len(feature_list)

    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]
    sel_idx = [feature_list.index(f) for f in selected_features]

    with open(PREPROC_DIR / "log1p_sensitivity_metadata.json") as f:
        log1p_meta = json.load(f)
    heavy_tail_features = log1p_meta["qualifying_features"]
    heavy_tail_indices = [feature_list.index(f) for f in heavy_tail_features]

    # 2. Load calibration thresholds
    with open(CALIB_DIR / "calibration_thresholds.json") as f:
        calib_thresholds = json.load(f)

    # 3. Load datasets
    logger.info("Loading evaluation datasets...")
    bot_df = pd.read_csv(SPLITS_DIR / "protected_bot.csv")
    ctrl_df = pd.read_csv(SPLITS_DIR / "eval_control.csv")
    xss_df = pd.read_csv(SPLITS_DIR / "unseen_xss.csv")
    infil_df = pd.read_csv(SPLITS_DIR / "unseen_infiltration.csv")

    n_bot = len(bot_df)
    n_ctrl = len(ctrl_df)
    n_xss = len(xss_df)
    n_infil = len(infil_df)

    logger.info("Dataset counts: Bot=%d, Eval_Control=%d, XSS=%d, Infiltration=%d",
                n_bot, n_ctrl, n_xss, n_infil)

    # Verify counts match expected invariants
    assert n_bot == 1948, f"Bot count mismatch: {n_bot} != 1948"
    assert n_ctrl == 18500, f"Control count mismatch: {n_ctrl} != 18500"
    assert n_xss == 652, f"XSS count mismatch: {n_xss} != 652"
    assert n_infil == 36, f"Infiltration count mismatch: {n_infil} != 36"

    # Extract raw arrays
    X_bot_raw = bot_df[feature_list].to_numpy(dtype=np.float64)
    X_ctrl_raw = ctrl_df[feature_list].to_numpy(dtype=np.float64)
    X_xss_raw = xss_df[feature_list].to_numpy(dtype=np.float64)
    X_infil_raw = infil_df[feature_list].to_numpy(dtype=np.float64)

    # Supervised feature slices (k_star = 33)
    X_bot_sel = X_bot_raw[:, sel_idx]
    X_ctrl_sel = X_ctrl_raw[:, sel_idx]
    X_xss_sel = X_xss_raw[:, sel_idx]
    X_infil_sel = X_infil_raw[:, sel_idx]

    # Scalers for Autoencoders
    with open(AE_DIR / "scaler_benign_train.pkl", "rb") as f:
        std_scaler = pickle.load(f)
    with open(AE_DIR / "scaler_benign_train_log1p.pkl", "rb") as f:
        log1p_scaler = pickle.load(f)

    # Scale for standard AE / IF
    X_bot_std = std_scaler.transform(X_bot_raw)
    X_ctrl_std = std_scaler.transform(X_ctrl_raw)
    X_xss_std = std_scaler.transform(X_xss_raw)
    X_infil_std = std_scaler.transform(X_infil_raw)

    # Log1p transforms and scaling
    def apply_log1p(X_mat: np.ndarray) -> np.ndarray:
        X_out = X_mat.copy()
        for idx in heavy_tail_indices:
            X_out[:, idx] = np.log1p(np.maximum(0.0, X_out[:, idx]))
        return log1p_scaler.transform(X_out)

    X_bot_log1p = apply_log1p(X_bot_raw)
    X_ctrl_log1p = apply_log1p(X_ctrl_raw)
    X_xss_log1p = apply_log1p(X_xss_raw)
    X_infil_log1p = apply_log1p(X_infil_raw)

    # DataLoaders for AE inference
    def make_loader(X_mat: np.ndarray) -> DataLoader:
        t = torch.tensor(X_mat, dtype=torch.float32)
        return DataLoader(TensorDataset(t), batch_size=BATCH_SIZE, shuffle=False)

    loader_bot_std = make_loader(X_bot_std)
    loader_ctrl_std = make_loader(X_ctrl_std)
    loader_xss_std = make_loader(X_xss_std)
    loader_infil_std = make_loader(X_infil_std)

    loader_bot_log1p = make_loader(X_bot_log1p)
    loader_ctrl_log1p = make_loader(X_ctrl_log1p)
    loader_xss_log1p = make_loader(X_xss_log1p)
    loader_infil_log1p = make_loader(X_infil_log1p)

    def compute_ae_re(model: nn.Module, loader: DataLoader) -> np.ndarray:
        model.eval()
        errs = []
        with torch.no_grad():
            for (xb,) in loader:
                xb = xb.to(device)
                re = model.reconstruction_error(xb)
                errs.append(re.cpu().numpy())
        return np.concatenate(errs, axis=0)

    # Prepare tracking structures
    all_metrics = []
    bot_preds_df = pd.DataFrame({"row_uid": bot_df["row_uid"], "label_clean": bot_df["label_clean"]})
    ctrl_preds_df = pd.DataFrame({"row_uid": ctrl_df["row_uid"], "label_clean": ctrl_df["label_clean"]})
    xss_preds_df = pd.DataFrame({"row_uid": xss_df["row_uid"], "label_clean": xss_df["label_clean"]})
    infil_preds_df = pd.DataFrame({"row_uid": infil_df["row_uid"], "label_clean": infil_df["label_clean"]})

    for seed in SEEDS:
        logger.info("-" * 60)
        logger.info("EVALUATING ZERO-DAY MODELS FOR SEED %d", seed)
        logger.info("-" * 60)

        seed_dir = MODEL_DIR / f"seed_{seed}"

        # -------------------------------------------------------------
        # 1. Supervised Base Models & Stacking
        # -------------------------------------------------------------
        # (a) DT
        with open(seed_dir / "dt_model.pkl", "rb") as f:
            dt = pickle.load(f)
        p_bot_dt = (dt.predict_proba(X_bot_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_ctrl_dt = (dt.predict_proba(X_ctrl_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_xss_dt = (dt.predict_proba(X_xss_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_infil_dt = (dt.predict_proba(X_infil_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)

        bot_preds_df[f"dt_pred_seed_{seed}"] = p_bot_dt
        ctrl_preds_df[f"dt_pred_seed_{seed}"] = p_ctrl_dt
        all_metrics.append(compute_detector_metrics(p_bot_dt, p_ctrl_dt, n_bot, n_ctrl, "DT", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_dt, p_ctrl_dt, n_xss, n_ctrl, "DT", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_dt, p_ctrl_dt, n_infil, n_ctrl, "DT", seed, "UNSEEN_INFILTRATION"))

        # (b) RF
        with open(seed_dir / "rf_model.pkl", "rb") as f:
            rf = pickle.load(f)
        p_bot_rf = (rf.predict_proba(X_bot_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_ctrl_rf = (rf.predict_proba(X_ctrl_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_xss_rf = (rf.predict_proba(X_xss_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_infil_rf = (rf.predict_proba(X_infil_sel)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)

        bot_preds_df[f"rf_pred_seed_{seed}"] = p_bot_rf
        ctrl_preds_df[f"rf_pred_seed_{seed}"] = p_ctrl_rf
        all_metrics.append(compute_detector_metrics(p_bot_rf, p_ctrl_rf, n_bot, n_ctrl, "RF", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_rf, p_ctrl_rf, n_xss, n_ctrl, "RF", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_rf, p_ctrl_rf, n_infil, n_ctrl, "RF", seed, "UNSEEN_INFILTRATION"))

        # (c) SVM
        with open(seed_dir / "svm_model.pkl", "rb") as f:
            svm = pickle.load(f)
        with open(seed_dir / "svm_scaler.pkl", "rb") as f:
            svm_scaler = pickle.load(f)
        X_bot_svm = svm_scaler.transform(X_bot_sel)
        X_ctrl_svm = svm_scaler.transform(X_ctrl_sel)
        X_xss_svm = svm_scaler.transform(X_xss_sel)
        X_infil_svm = svm_scaler.transform(X_infil_sel)

        p_bot_svm = svm.predict(X_bot_svm).astype(int)
        p_ctrl_svm = svm.predict(X_ctrl_svm).astype(int)
        p_xss_svm = svm.predict(X_xss_svm).astype(int)
        p_infil_svm = svm.predict(X_infil_svm).astype(int)

        bot_preds_df[f"svm_pred_seed_{seed}"] = p_bot_svm
        ctrl_preds_df[f"svm_pred_seed_{seed}"] = p_ctrl_svm
        all_metrics.append(compute_detector_metrics(p_bot_svm, p_ctrl_svm, n_bot, n_ctrl, "SVM", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_svm, p_ctrl_svm, n_xss, n_ctrl, "SVM", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_svm, p_ctrl_svm, n_infil, n_ctrl, "SVM", seed, "UNSEEN_INFILTRATION"))

        # (d) IDSNet
        with open(seed_dir / "nn_scaler.pkl", "rb") as f:
            nn_scaler = pickle.load(f)
        net = IDSNet(input_dim=k_star).to(device)
        net.load_state_dict(torch.load(seed_dir / "nn_model.pt", map_location=device))

        p_bot_nn, prob_bot_nn = predict_idsnet(net, nn_scaler, X_bot_sel, device)
        p_ctrl_nn, prob_ctrl_nn = predict_idsnet(net, nn_scaler, X_ctrl_sel, device)
        p_xss_nn, prob_xss_nn = predict_idsnet(net, nn_scaler, X_xss_sel, device)
        p_infil_nn, prob_infil_nn = predict_idsnet(net, nn_scaler, X_infil_sel, device)

        bot_preds_df[f"idsnet_pred_seed_{seed}"] = p_bot_nn
        ctrl_preds_df[f"idsnet_pred_seed_{seed}"] = p_ctrl_nn
        all_metrics.append(compute_detector_metrics(p_bot_nn, p_ctrl_nn, n_bot, n_ctrl, "IDSNet", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_nn, p_ctrl_nn, n_xss, n_ctrl, "IDSNet", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_nn, p_ctrl_nn, n_infil, n_ctrl, "IDSNet", seed, "UNSEEN_INFILTRATION"))
        del net
        gc.collect()

        # (e) Frozen Stacking (Meta-LR)
        with open(seed_dir / "meta_lr.pkl", "rb") as f:
            meta_lr = pickle.load(f)

        def make_meta_X(dt_m, rf_m, svm_m, nn_prob, X_s, X_svm_s):
            dt_p = dt_m.predict_proba(X_s)[:, 1]
            rf_p = rf_m.predict_proba(X_s)[:, 1]
            svm_s = svm_m.decision_function(X_svm_s)
            return np.column_stack([dt_p, rf_p, svm_s, nn_prob])

        meta_bot = make_meta_X(dt, rf, svm, prob_bot_nn, X_bot_sel, X_bot_svm)
        meta_ctrl = make_meta_X(dt, rf, svm, prob_ctrl_nn, X_ctrl_sel, X_ctrl_svm)
        meta_xss = make_meta_X(dt, rf, svm, prob_xss_nn, X_xss_sel, X_xss_svm)
        meta_infil = make_meta_X(dt, rf, svm, prob_infil_nn, X_infil_sel, X_infil_svm)

        p_bot_stack = (meta_lr.predict_proba(meta_bot)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_ctrl_stack = (meta_lr.predict_proba(meta_ctrl)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_xss_stack = (meta_lr.predict_proba(meta_xss)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)
        p_infil_stack = (meta_lr.predict_proba(meta_infil)[:, 1] >= SUPERVISED_THRESHOLD).astype(int)

        bot_preds_df[f"stacking_pred_seed_{seed}"] = p_bot_stack
        ctrl_preds_df[f"stacking_pred_seed_{seed}"] = p_ctrl_stack
        all_metrics.append(compute_detector_metrics(p_bot_stack, p_ctrl_stack, n_bot, n_ctrl, "Stacking", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_stack, p_ctrl_stack, n_xss, n_ctrl, "Stacking", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_stack, p_ctrl_stack, n_infil, n_ctrl, "Stacking", seed, "UNSEEN_INFILTRATION"))

        # -------------------------------------------------------------
        # 2. Standard Autoencoder (tau_mu3sigma)
        # -------------------------------------------------------------
        tau_ae_std = calib_thresholds["autoencoder_thresholds"]["standard"][str(seed)]["thresholds"]["mu_plus_3sigma"]["threshold_value"]
        ae_std_model = Autoencoder(input_dim=D).to(device)
        ae_std_model.load_state_dict(torch.load(seed_dir / "ae_standard_model.pt", map_location=device))

        re_bot_std = compute_ae_re(ae_std_model, loader_bot_std)
        re_ctrl_std = compute_ae_re(ae_std_model, loader_ctrl_std)
        re_xss_std = compute_ae_re(ae_std_model, loader_xss_std)
        re_infil_std = compute_ae_re(ae_std_model, loader_infil_std)

        p_bot_ae_std = (re_bot_std > tau_ae_std).astype(int)
        p_ctrl_ae_std = (re_ctrl_std > tau_ae_std).astype(int)
        p_xss_ae_std = (re_xss_std > tau_ae_std).astype(int)
        p_infil_ae_std = (re_infil_std > tau_ae_std).astype(int)

        bot_preds_df[f"ae_std_pred_seed_{seed}"] = p_bot_ae_std
        ctrl_preds_df[f"ae_std_pred_seed_{seed}"] = p_ctrl_ae_std
        all_metrics.append(compute_detector_metrics(p_bot_ae_std, p_ctrl_ae_std, n_bot, n_ctrl, "Autoencoder_Standard", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_ae_std, p_ctrl_ae_std, n_xss, n_ctrl, "Autoencoder_Standard", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_ae_std, p_ctrl_ae_std, n_infil, n_ctrl, "Autoencoder_Standard", seed, "UNSEEN_INFILTRATION"))
        del ae_std_model
        gc.collect()

        # -------------------------------------------------------------
        # 3. Log1p Sensitivity Autoencoder (tau_mu3sigma)
        # -------------------------------------------------------------
        tau_ae_log1p = calib_thresholds["autoencoder_thresholds"]["log1p"][str(seed)]["thresholds"]["mu_plus_3sigma"]["threshold_value"]
        ae_log1p_model = Autoencoder(input_dim=D).to(device)
        ae_log1p_model.load_state_dict(torch.load(seed_dir / "ae_log1p_model.pt", map_location=device))

        re_bot_log1p = compute_ae_re(ae_log1p_model, loader_bot_log1p)
        re_ctrl_log1p = compute_ae_re(ae_log1p_model, loader_ctrl_log1p)
        re_xss_log1p = compute_ae_re(ae_log1p_model, loader_xss_log1p)
        re_infil_log1p = compute_ae_re(ae_log1p_model, loader_infil_log1p)

        p_bot_ae_log1p = (re_bot_log1p > tau_ae_log1p).astype(int)
        p_ctrl_ae_log1p = (re_ctrl_log1p > tau_ae_log1p).astype(int)
        p_xss_ae_log1p = (re_xss_log1p > tau_ae_log1p).astype(int)
        p_infil_ae_log1p = (re_infil_log1p > tau_ae_log1p).astype(int)

        bot_preds_df[f"ae_log1p_pred_seed_{seed}"] = p_bot_ae_log1p
        ctrl_preds_df[f"ae_log1p_pred_seed_{seed}"] = p_ctrl_ae_log1p
        all_metrics.append(compute_detector_metrics(p_bot_ae_log1p, p_ctrl_ae_log1p, n_bot, n_ctrl, "Autoencoder_Log1p", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_ae_log1p, p_ctrl_ae_log1p, n_xss, n_ctrl, "Autoencoder_Log1p", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_ae_log1p, p_ctrl_ae_log1p, n_infil, n_ctrl, "Autoencoder_Log1p", seed, "UNSEEN_INFILTRATION"))
        del ae_log1p_model
        gc.collect()

        # -------------------------------------------------------------
        # 4. Isolation Forest (tau_mu3sigma)
        # -------------------------------------------------------------
        tau_if = calib_thresholds["isolation_forest_thresholds"][str(seed)]["thresholds"]["mu_plus_3sigma"]["threshold_value"]
        if_model = joblib.load(seed_dir / "if_model.joblib")

        sc_bot_if = -if_model.score_samples(X_bot_std)
        sc_ctrl_if = -if_model.score_samples(X_ctrl_std)
        sc_xss_if = -if_model.score_samples(X_xss_std)
        sc_infil_if = -if_model.score_samples(X_infil_std)

        p_bot_if = (sc_bot_if > tau_if).astype(int)
        p_ctrl_if = (sc_ctrl_if > tau_if).astype(int)
        p_xss_if = (sc_xss_if > tau_if).astype(int)
        p_infil_if = (sc_infil_if > tau_if).astype(int)

        bot_preds_df[f"if_pred_seed_{seed}"] = p_bot_if
        ctrl_preds_df[f"if_pred_seed_{seed}"] = p_ctrl_if
        all_metrics.append(compute_detector_metrics(p_bot_if, p_ctrl_if, n_bot, n_ctrl, "Isolation_Forest", seed, "PROTECTED_BOT"))
        all_metrics.append(compute_detector_metrics(p_xss_if, p_ctrl_if, n_xss, n_ctrl, "Isolation_Forest", seed, "UNSEEN_XSS"))
        all_metrics.append(compute_detector_metrics(p_infil_if, p_ctrl_if, n_infil, n_ctrl, "Isolation_Forest", seed, "UNSEEN_INFILTRATION"))

        # Log primary Bot summary for this seed
        logger.info("[Seed %d Summary on PROTECTED_BOT (N=%d, Control N=%d)]", seed, n_bot, n_ctrl)
        for m in all_metrics[-24:]:
            if m["attack_set"] == "PROTECTED_BOT" and m["seed"] == seed:
                logger.info("  %-22s | Det=%4d | Rec=%.4f [%.4f, %.4f] | Ctrl_FPR=%.4f | Alerts/10k=%5.1f | Prec_std=%.4f",
                            m["detector"], m["detections"], m["recall"],
                            m["recall_ci_lower_95"], m["recall_ci_upper_95"],
                            m["control_fpr"], m["alerts_per_10k"], m["precision_standardized"])

    # 4. Save Prediction Tables
    bot_preds_path = ZERO_DAY_DIR / "protected_bot_predictions.csv"
    ctrl_preds_path = ZERO_DAY_DIR / "eval_control_predictions.csv"
    bot_preds_df.to_csv(bot_preds_path, index=False)
    ctrl_preds_df.to_csv(ctrl_preds_path, index=False)
    logger.info("Saved prediction tables: %s and %s", bot_preds_path.name, ctrl_preds_path.name)

    # 5. Save Full Evaluation Metrics
    metrics_df = pd.DataFrame(all_metrics)
    csv_table_path = ZERO_DAY_DIR / "zero_day_evaluation_table.csv"
    metrics_df.to_csv(csv_table_path, index=False)

    summary_json_path = ZERO_DAY_DIR / "zero_day_evaluation_summary.json"
    summary_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "prevalence_pi": PI_PREVALENCE,
        "n_populations": {
            "protected_bot": n_bot,
            "eval_control": n_ctrl,
            "unseen_xss": n_xss,
            "unseen_infiltration": n_infil,
        },
        "seeds": SEEDS,
        "results": all_metrics,
    }
    with open(summary_json_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    logger.info("Saved zero-day evaluation metrics: %s and %s", csv_table_path.name, summary_json_path.name)
    logger.info("=" * 70)
    logger.info("STEP 5: PASS — PURE INFERENCE ZERO-DAY EVALUATION COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
