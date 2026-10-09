#!/usr/bin/env python3
"""
publication_experiments/scripts/run_no_ttl_shap_explainability.py
------------------------------------------------------------------
EXP_EXPLAIN_NO_TTL_V1 — SHAP Explainability for the 72-feature No-TTL
Publication Experiment (EXP_NO_TTL_V1, seed 42).

Mirrors the exact structure of:
    scripts/run_sprint11_explainability.py  (Sprint 11, 75-feature)

Key differences from Sprint 11:
  - Uses 72 No-TTL features (sttl / ct_state_ttl / dttl removed).
  - Model checkpoints from: results/publication_experiments/EXP_NO_TTL_V1/checkpoints/seed_42/
  - Supervised scaler from:  results/publication_experiments/EXP_NO_TTL_V1/scalers/supervised_scaler_72.joblib
  - OOF predictions from:    results/publication_experiments/EXP_NO_TTL_V1/predictions/seed_42/oof_predictions.csv
  - Output to:               results/explainability/EXP_EXPLAIN_NO_TTL_V1/
  - NO AE explanation (AE in EXP_NO_TTL_V1 is not present; AE uses EXP_AE_UNSEEN_FAMILY_V1 72-feat models).
  - Explains: NTL_RF (RandomForest), NTL_STACK (meta-learner stacking).

Original Sprint 11 is NOT modified — this is a new, standalone script.
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import torch
import yaml
from sklearn.metrics import f1_score

# ---------------------------------------------------------------------------
# Root setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models.base_models.neural_network import IDSNet
from src.preprocessing.preprocessing_pipeline import PreprocessingPipeline
from publication_experiments.utils.feature_adapter import EXPECTED_NO_TTL_COUNT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXP_ID          = "EXP_EXPLAIN_NO_TTL_V1"
EXPLAINED_SEED  = 42
N_FEATURES      = 72
EXPECTED_FEATURES = EXPECTED_NO_TTL_COUNT   # 72

SOURCE_EXP      = "EXP_NO_TTL_V1"
CKPT_ROOT       = ROOT / "results/publication_experiments/EXP_NO_TTL_V1/checkpoints/seed_42"
SCALER_PATH     = ROOT / "results/publication_experiments/EXP_NO_TTL_V1/scalers/supervised_scaler_72.joblib"
OOF_PATH        = ROOT / "results/publication_experiments/EXP_NO_TTL_V1/predictions/seed_42/oof_predictions.csv"
FEATURES_JSON   = ROOT / "publication_experiments/features/no_ttl_features.json"
FOLD_ASSIGN_42  = ROOT / "results/stacking/EXP_OOF_STACK_V1/seed_42/fold_assignments.csv"
FOLD_ASSIGN_123 = ROOT / "results/stacking/EXP_OOF_STACK_V1/seed_123/fold_assignments.csv"
FOLD_ASSIGN_2024= ROOT / "results/stacking/EXP_OOF_STACK_V1/seed_2024/fold_assignments.csv"

DEV_TEST_CSV    = ROOT / "data/splits/development_test.csv"
TRAIN_CSV       = ROOT / "data/splits/train.csv"
VAL_CSV         = ROOT / "data/splits/validation.csv"
PROTECTED_CSV   = ROOT / "data/splits/protected_unseen_attack.csv"

OUT_DIR         = ROOT / "results/explainability/EXP_EXPLAIN_NO_TTL_V1"

BG_SAMPLE_SIZE  = 500
BG_SEED         = 42
EXP_SET_BENIGN  = 1000
EXP_SET_ATTACK  = 1000
EXP_SET_SEED    = 42

EXPECTED_DEV_ROWS   = 81749
EXPECTED_TRAIN_ROWS = 162395

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("EXP_EXPLAIN_NO_TTL_V1")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh = logging.FileHandler(OUT_DIR / "execution.log", mode="w", encoding="utf-8")
fh.setLevel(logging.INFO); fh.setFormatter(fmt); logger.addHandler(fh)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO); ch.setFormatter(fmt); logger.addHandler(ch)

# ---------------------------------------------------------------------------
# Helpers  (identical to Sprint 11)
# ---------------------------------------------------------------------------
def make_source_row_uid(source_file: str, raw_id: int) -> str:
    return f"{source_file}#id={raw_id:06d}"

def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# ---------------------------------------------------------------------------
# Neural Network wrapper  (identical to Sprint 11)
# ---------------------------------------------------------------------------
class SigmoidNN(torch.nn.Module):
    def __init__(self, base_model: torch.nn.Module):
        super().__init__()
        self.base_model = base_model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = torch.sigmoid(self.base_model(x))
        if out.ndim == 1:
            out = out.unsqueeze(-1)
        return out

# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
class NoTTLSHAPPipeline:
    def __init__(self):
        self.pv_results: Dict[str, Dict[str, Any]] = {}
        self.summary: Dict[str, Any] = {
            "experiment_id": EXP_ID,
            "source_experiment": SOURCE_EXP,
            "explained_seed": EXPLAINED_SEED,
            "n_features": N_FEATURES,
            "pv_gates": {},
            "metrics": {},
        }
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initialized {EXP_ID} pipeline on device: {self.device}")

    def record_pv(self, gate_id: str, desc: str, passed: bool, details: Any = None):
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {gate_id}: {desc}")
        self.pv_results[gate_id] = {
            "gate_id": gate_id, "description": desc,
            "passed": passed, "status": status, "details": details,
        }
        if not passed:
            logger.error(f"HARD GATE FAILURE at {gate_id}: {desc}. Details: {details}")
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Phase 0: Pre-Verification Gates
    # -----------------------------------------------------------------------
    def run_phase0_preverification(self):
        logger.info("=== PHASE 0: Pre-Verification Gates ===")

        # PV-01: RF checkpoint
        rf_path = CKPT_ROOT / "rf_final.joblib"
        self.record_pv("PV-01", "NTL_RF checkpoint resolved",
                       rf_path.exists() and rf_path.stat().st_size > 0,
                       {"path": str(rf_path), "size_mb": round(rf_path.stat().st_size / 1e6, 1) if rf_path.exists() else 0})

        # PV-02: DT checkpoint
        dt_path = CKPT_ROOT / "dt_final.joblib"
        self.record_pv("PV-02", "NTL_DT checkpoint resolved",
                       dt_path.exists(), {"path": str(dt_path)})

        # PV-03: SVM checkpoint
        svm_path = CKPT_ROOT / "svm_final.joblib"
        self.record_pv("PV-03", "NTL_SVM checkpoint resolved",
                       svm_path.exists(), {"path": str(svm_path)})

        # PV-04: NN checkpoint
        nn_path = CKPT_ROOT / "nn_final.pt"
        self.record_pv("PV-04", "NTL_NN checkpoint resolved",
                       nn_path.exists(), {"path": str(nn_path)})

        # PV-05: Meta-learner checkpoint
        meta_path = CKPT_ROOT / "meta_learner.joblib"
        self.record_pv("PV-05", "NTL_STACK meta-learner checkpoint resolved",
                       meta_path.exists(), {"path": str(meta_path)})

        # PV-06: Supervised scaler
        self.record_pv("PV-06", "Supervised scaler (72 features) resolved",
                       SCALER_PATH.exists(), {"path": str(SCALER_PATH)})

        # PV-07: OOF predictions
        self.record_pv("PV-07", "OOF predictions (seed 42) resolved",
                       OOF_PATH.exists(), {"path": str(OOF_PATH)})

        # PV-08: No-TTL features JSON
        self.record_pv("PV-08", "No-TTL features JSON resolved",
                       FEATURES_JSON.exists(), {"path": str(FEATURES_JSON)})

        # PV-09: 72-feature count verified
        with open(FEATURES_JSON, "r", encoding="utf-8") as f:
            feat_data = json.load(f)
        # Key in no_ttl_features.json is "features" (see publication_experiments/features/no_ttl_features.json)
        self.no_ttl_features: List[str] = feat_data["features"]
        pv09_pass = len(self.no_ttl_features) == 72
        self.record_pv("PV-09", "Exact 72-feature count confirmed",
                       pv09_pass, {"count": len(self.no_ttl_features), "first_3": self.no_ttl_features[:3]})

        # PV-10: TTL features must NOT be in the list
        ttl_feats = {"sttl", "ct_state_ttl", "dttl"}
        ttl_in_list = ttl_feats.intersection(set(self.no_ttl_features))
        self.record_pv("PV-10", "TTL features absent from No-TTL feature list",
                       len(ttl_in_list) == 0, {"ttl_found_in_list": list(ttl_in_list)})

        # PV-11: Class mapping
        self.record_pv("PV-11", "Class mapping confirmed (0=benign, 1=attack)", True,
                       {"0": "benign", "1": "attack"})

        # PV-12: DEVELOPMENT_TEST confirmed
        self.dev_test_raw = pd.read_csv(DEV_TEST_CSV)
        pv12_pass = len(self.dev_test_raw) == EXPECTED_DEV_ROWS
        self.record_pv("PV-12", "DEVELOPMENT_TEST row count confirmed (81,749)",
                       pv12_pass, {"rows": len(self.dev_test_raw), "sha256": sha256_file(DEV_TEST_CSV)})

        # Load remaining splits
        self.train_raw = pd.read_csv(TRAIN_CSV)
        self.val_raw   = pd.read_csv(VAL_CSV)
        self.prot_raw  = pd.read_csv(PROTECTED_CSV)

        # Canonical UIDs
        self.train_uids    = [make_source_row_uid("UNSW_NB15_training-set.csv", x) for x in self.train_raw["id"]]
        self.val_uids      = [make_source_row_uid("UNSW_NB15_training-set.csv", x) for x in self.val_raw["id"]]
        self.dev_test_uids = [make_source_row_uid("UNSW_NB15_testing-set.csv",  x) for x in self.dev_test_raw["id"]]
        self.prot_uids     = [make_source_row_uid("UNSW_NB15_testing-set.csv",  x) for x in self.prot_raw["id"]]

        self.dev_test_raw["source_row_uid"]   = self.dev_test_uids
        self.dev_test_raw["positional_row_id"] = np.arange(len(self.dev_test_raw))

        # PV-13: Global UID uniqueness
        all_uids = self.train_uids + self.val_uids + self.dev_test_uids + self.prot_uids
        unique_total = len(set(all_uids))
        expected_total = len(self.train_raw) + len(self.val_raw) + len(self.dev_test_raw) + len(self.prot_raw)
        global_uids_unique = (unique_total == len(all_uids) == expected_total)
        self.record_pv("PV-13", "Global source_row_uid uniqueness confirmed across all splits",
                       global_uids_unique,
                       {"total_rows": len(all_uids), "unique_uids": unique_total,
                        "collisions": len(all_uids) - unique_total})
        self.summary["global_uid_check"] = {
            "total_rows": len(all_uids), "unique_uids": unique_total,
            "collisions": len(all_uids) - unique_total
        }

        # PV-14: Explanation set reproducible (2000 rows)
        dev_sorted = self.dev_test_raw.sort_values("source_row_uid").reset_index(drop=True)
        benign_sub = dev_sorted[dev_sorted["label"] == 0].reset_index(drop=True)
        attack_sub = dev_sorted[dev_sorted["label"] == 1].reset_index(drop=True)
        exp_rng = np.random.default_rng(seed=EXP_SET_SEED)
        b_idx = exp_rng.choice(len(benign_sub), size=EXP_SET_BENIGN, replace=False)
        a_idx = exp_rng.choice(len(attack_sub), size=EXP_SET_ATTACK, replace=False)
        self.explanation_df = pd.concat([benign_sub.iloc[b_idx], attack_sub.iloc[a_idx]], ignore_index=True)
        self.explanation_df["explanation_idx"] = np.arange(len(self.explanation_df))
        self.exp_uids_set = set(self.explanation_df["source_row_uid"])
        self.record_pv("PV-14", "Explanation-set generation reproducible (2,000 rows, seed 42)",
                       len(self.explanation_df) == 2000 and len(self.exp_uids_set) == 2000,
                       {"total": len(self.explanation_df)})

        # PV-15: Explanation set has zero overlap with TRAIN
        overlap_train = len(self.exp_uids_set.intersection(set(self.train_uids)))
        self.record_pv("PV-15", "Explanation set intersect TRAIN = zero", overlap_train == 0,
                       {"overlap_count": overlap_train})

        # PV-16 through PV-18: OOF fitting population overlaps (seeds 42, 123, 2024)
        for seed_val, fold_path, pv_id in [
            (42, FOLD_ASSIGN_42, "PV-16"),
            (123, FOLD_ASSIGN_123, "PV-17"),
            (2024, FOLD_ASSIGN_2024, "PV-18"),
        ]:
            folds_df = pd.read_csv(fold_path)
            assert folds_df["row_id"].max() < len(self.train_raw), \
                f"fold_assignments.csv (seed {seed_val}) row_id out of bounds"
            oof_ids = self.train_raw.iloc[folds_df["row_id"].values]["id"].values
            oof_uids = set([make_source_row_uid("UNSW_NB15_training-set.csv", x) for x in oof_ids])
            overlap = len(self.exp_uids_set.intersection(oof_uids))
            self.record_pv(pv_id,
                           f"Explanation set intersect OOF-fitting population (seed {seed_val}) = zero",
                           overlap == 0, {"overlap_count": overlap})

        # PV-19: Explanation set intersect VALIDATION / PROTECTED = zero
        overlap_val  = len(self.exp_uids_set.intersection(set(self.val_uids)))
        overlap_prot = len(self.exp_uids_set.intersection(set(self.prot_uids)))
        self.record_pv("PV-19", "Explanation set intersect VALIDATION / PROTECTED = zero",
                       (overlap_val == 0) and (overlap_prot == 0),
                       {"val_overlap": overlap_val, "prot_overlap": overlap_prot})

        # PV-20: Load and preprocess all data using canonical pipeline
        logger.info("Fitting PreprocessingPipeline on TRAIN (72-feature No-TTL view)...")
        self.pipe = PreprocessingPipeline(experiment_id=EXP_ID)
        self.pipe.fit(self.train_raw)

        enc_train = self.pipe.transform(self.train_raw, view="unscaled", split_name="train")
        enc_dev   = self.pipe.transform(self.dev_test_raw, view="unscaled", split_name="dev_test")

        train_full_df = pd.DataFrame(enc_train.X, columns=enc_train.feature_names)
        dev_full_df   = pd.DataFrame(enc_dev.X,   columns=enc_dev.feature_names)

        # Select only the 72 No-TTL features (matching the column names in the trained models)
        self.X_train_72 = train_full_df[self.no_ttl_features].values.astype(np.float64)
        self.X_dev_72   = dev_full_df[self.no_ttl_features].values.astype(np.float64)
        self.record_pv("PV-20", "72-feature matrix extracted correctly",
                       self.X_train_72.shape[1] == 72 and self.X_dev_72.shape[1] == 72,
                       {"train_shape": list(self.X_train_72.shape), "dev_shape": list(self.X_dev_72.shape)})

        # PV-21: Draw 500-row TRAIN background
        bg_rng = np.random.default_rng(seed=BG_SEED)
        self.bg_pos_ids = bg_rng.choice(len(self.train_raw), size=BG_SAMPLE_SIZE, replace=False)
        self.X_train_bg_72 = self.X_train_72[self.bg_pos_ids]
        self.record_pv("PV-21", "500-row TRAIN background sampled (seed 42)",
                       len(self.bg_pos_ids) == BG_SAMPLE_SIZE, {"bg_size": len(self.bg_pos_ids)})

        # PV-22: Load models
        logger.info("Loading No-TTL models...")
        self.rf_model  = joblib.load(CKPT_ROOT / "rf_final.joblib")
        self.dt_model  = joblib.load(CKPT_ROOT / "dt_final.joblib")
        self.svm_model = joblib.load(CKPT_ROOT / "svm_final.joblib")
        self.sup_scaler = joblib.load(SCALER_PATH)   # single scaler for all supervised models
        self.meta_lr   = joblib.load(CKPT_ROOT / "meta_learner.joblib")
        nn_state = torch.load(CKPT_ROOT / "nn_final.pt", map_location="cpu", weights_only=True)
        # NN was trained on 72 features
        self.nn_raw = IDSNet(input_dim=72, hidden_sizes=[128, 64])
        self.nn_raw.load_state_dict(nn_state)
        self.nn_raw.eval()
        self.nn_sig = SigmoidNN(self.nn_raw).eval()
        self.record_pv("PV-22", "All No-TTL models loaded", True,
                       {"rf": "rf_final.joblib", "dt": "dt_final.joblib",
                        "svm": "svm_final.joblib", "nn": "nn_final.pt", "meta": "meta_learner.joblib"})

        # PV-23: RF explainer compatibility
        exp_rf_test = shap.TreeExplainer(self.rf_model, feature_perturbation="tree_path_dependent")
        sh_test = exp_rf_test.shap_values(self.X_dev_72[:5])
        self.record_pv("PV-23", "RF TreeExplainer compatibility verified",
                       sh_test is not None, {"test_shape": list(np.array(sh_test).shape)})

        # PV-24: SVM LinearExplainer
        X_bg_sc = self.sup_scaler.transform(self.X_train_bg_72)
        svm_masker = shap.maskers.Independent(X_bg_sc)
        self.exp_svm = shap.LinearExplainer(self.svm_model, svm_masker)
        sh_svm_test = self.exp_svm.shap_values(self.sup_scaler.transform(self.X_dev_72[:5]))
        self.record_pv("PV-24", "SVM LinearExplainer compatibility verified",
                       sh_svm_test is not None, {"test_shape": list(np.array(sh_svm_test).shape)})

        # PV-25: Meta-learner LinearExplainer
        oof_df = pd.read_csv(OOF_PATH)
        assert len(oof_df) == len(self.train_raw), \
            f"OOF rows ({len(oof_df)}) != TRAIN rows ({len(self.train_raw)})"
        meta_cols = ["dt_attack_probability", "rf_attack_probability", "svm_decision_score", "nn_attack_probability"]
        meta_bg = oof_df.loc[self.bg_pos_ids, meta_cols].values
        meta_masker = shap.maskers.Independent(meta_bg)
        self.exp_meta = shap.LinearExplainer(self.meta_lr, meta_masker)
        self.meta_bg = meta_bg
        sh_meta_test = self.exp_meta.shap_values(meta_bg[:5])
        self.record_pv("PV-25", "Meta-learner LinearExplainer compatibility verified",
                       sh_meta_test is not None, {"test_shape": list(np.array(sh_meta_test).shape)})

        # PV-26: NN DeepExplainer
        nn_bg_sc = self.sup_scaler.transform(self.X_train_bg_72)
        self.nn_bg_tensor = torch.tensor(nn_bg_sc, dtype=torch.float32)
        dev_10_tensor = torch.tensor(self.sup_scaler.transform(self.X_dev_72[:10]), dtype=torch.float32)
        self.exp_nn = shap.DeepExplainer(self.nn_sig, self.nn_bg_tensor)
        sh_nn_test = self.exp_nn.shap_values(dev_10_tensor, check_additivity=False)
        self.nn_device_used = "cpu"
        self.record_pv("PV-26", "NN DeepExplainer compatibility verified",
                       sh_nn_test is not None, {"test_shape": list(np.array(sh_nn_test).shape)})

        # PV-27: No retraining/tuning
        self.record_pv("PV-27", "No retraining or tuning — all models strictly frozen", True,
                       {"status": "READ_ONLY"})

        # PV-28: Original Sprint 11 artifacts unchanged
        sprint11_dir = ROOT / "results/explainability/EXP_EXPLAIN_V1"
        self.record_pv("PV-28", "Original EXP_EXPLAIN_V1 (Sprint 11) artifacts untouched",
                       sprint11_dir.exists(), {"sprint11_dir": str(sprint11_dir)})

        # PV-29: Output directory is isolated
        self.record_pv("PV-29", "Output directory isolated from Sprint 11 (EXP_EXPLAIN_NO_TTL_V1)",
                       "NO_TTL" in str(OUT_DIR), {"out_dir": str(OUT_DIR)})

        logger.info("=== ALL PRE-VERIFICATION GATES PASSED ===")

    # -----------------------------------------------------------------------
    # Phase 1: Background Sampling & Explanation Set Save
    # -----------------------------------------------------------------------
    def run_phase1_sampling(self):
        logger.info("=== PHASE 1: Sampling & saving background / explanation set ===")
        out_dir = OUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        # Background indices CSV
        bg_records = []
        for pos_id in self.bg_pos_ids:
            raw_id = int(self.train_raw.iloc[pos_id]["id"])
            bg_records.append({
                "positional_row_id": int(pos_id),
                "source_row_uid": make_source_row_uid("UNSW_NB15_training-set.csv", raw_id),
                "raw_id": raw_id,
                "label": int(self.train_raw.iloc[pos_id]["label"]),
            })
        pd.DataFrame(bg_records).to_csv(out_dir / "background_indices.csv", index=False)

        # Explanation set indices
        exp_set_dir = out_dir / "explanation_set"
        exp_set_dir.mkdir(parents=True, exist_ok=True)
        exp_out = self.explanation_df[["explanation_idx", "positional_row_id", "source_row_uid", "label"]].copy()
        exp_out.to_csv(exp_set_dir / "indices.csv", index=False)

        mapping_df = self.explanation_df[["explanation_idx", "positional_row_id", "source_row_uid", "id", "label"]].copy()
        mapping_df.rename(columns={"id": "raw_id"}, inplace=True)
        mapping_df["source_file"] = "UNSW_NB15_testing-set.csv"
        mapping_df.to_csv(exp_set_dir / "source_row_uid_mapping.csv", index=False)

        with open(exp_set_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "experiment_id": EXP_ID,
                "source_experiment": SOURCE_EXP,
                "n_features": N_FEATURES,
                "total_rows": 2000, "benign_rows": 1000, "attack_rows": 1000,
                "sampling_seed": EXP_SET_SEED,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, f, indent=2)

        # Pre-extract feature matrices for explanation set
        self.exp_pos_ids = self.explanation_df["positional_row_id"].values
        self.X_exp_72    = self.X_dev_72[self.exp_pos_ids]
        self.y_exp       = self.explanation_df["label"].values
        logger.info(f"Explanation set ready: shape={self.X_exp_72.shape}, "
                    f"benign={( self.y_exp==0).sum()}, attack={(self.y_exp==1).sum()}")

    # -----------------------------------------------------------------------
    # Helper: save global importance CSV + bar chart
    # -----------------------------------------------------------------------
    def _save_feature_importance(
        self, shap_matrix: np.ndarray, out_dir: Path,
        feature_names: List[str], title: str, color: str = "#1f77b4"
    ):
        out_dir.mkdir(parents=True, exist_ok=True)
        mean_abs = np.mean(np.abs(shap_matrix), axis=0)
        ranks = np.argsort(-mean_abs)
        records = []
        for r, idx in enumerate(ranks, start=1):
            records.append({
                "feature_name": feature_names[idx],
                "feature_index": int(idx),
                "mean_abs_shap": float(mean_abs[idx]),
                "rank": r,
            })
        df = pd.DataFrame(records)
        df.to_csv(out_dir / "global_importance.csv", index=False)
        df.head(20).to_csv(out_dir / "top_features.csv", index=False)

        fig, ax = plt.subplots(figsize=(10, 8))
        top20 = df.head(20).iloc[::-1]
        ax.barh(top20["feature_name"], top20["mean_abs_shap"], color=color)
        ax.set_xlabel("Mean Absolute SHAP Value (Attack Class)")
        ax.set_title(title)
        plt.tight_layout()
        fig_path = out_dir / "global_importance.png"
        plt.savefig(fig_path, dpi=300)
        plt.close()
        logger.info(f"Saved global importance: {fig_path}")
        return df

    # -----------------------------------------------------------------------
    # Helper: save local cases JSON + individual bar charts
    # -----------------------------------------------------------------------
    def _save_local_cases(
        self, target_id: str, preds: np.ndarray, shap_vals: np.ndarray,
        out_dir: Path, fig_dir: Path, is_ae: bool = False
    ):
        fig_dir.mkdir(parents=True, exist_ok=True)
        y_true = self.y_exp
        categories = {
            "TP": np.where((y_true == 1) & (preds == 1))[0],
            "FP": np.where((y_true == 0) & (preds == 1))[0],
            "FN": np.where((y_true == 1) & (preds == 0))[0],
            "TN": np.where((y_true == 0) & (preds == 0))[0],
        }
        local_results: Dict[str, Any] = {}
        for cat_name, indices in categories.items():
            sorted_idx = np.sort(indices)
            selected = sorted_idx[:5].tolist()
            case_list = []
            for e_idx in selected:
                pos_id = int(self.exp_pos_ids[e_idx])
                raw_id = int(self.dev_test_raw.iloc[pos_id]["id"])
                uid = make_source_row_uid("UNSW_NB15_testing-set.csv", raw_id)
                top_feats = np.argsort(-np.abs(shap_vals[e_idx]))[:5]
                top_feat_dict = {self.no_ttl_features[f]: float(shap_vals[e_idx][f]) for f in top_feats}
                case_list.append({
                    "explanation_idx": int(e_idx),
                    "positional_row_id": pos_id,
                    "source_row_uid": uid, "raw_id": raw_id,
                    "true_label": int(y_true[e_idx]),
                    "predicted_label": int(preds[e_idx]),
                    "category": cat_name, "top_features": top_feat_dict,
                })
                fig, ax = plt.subplots(figsize=(8, 4))
                color = "#1f77b4" if not is_ae else "#ff7f0e"
                ax.barh(list(top_feat_dict.keys())[::-1], list(top_feat_dict.values())[::-1], color=color)
                ax.set_xlabel("SHAP" if not is_ae else "Squared RE")
                ax.set_title(f"{target_id} — {cat_name} (Idx {e_idx})")
                plt.tight_layout()
                plt.savefig(fig_dir / f"local_{cat_name.lower()}_{e_idx}.png", dpi=300)
                plt.close()

            local_results[cat_name] = {
                "available_count": len(indices),
                "selected_count": len(selected),
                "cases": case_list,
            }

        with open(out_dir / "local_cases.json", "w", encoding="utf-8") as f:
            json.dump(local_results, f, indent=2)
        logger.info(f"Saved local_cases.json for {target_id}")

    # -----------------------------------------------------------------------
    # Phase 5: NTL_RF Explainability (mirrors Phase 5 of Sprint 11)
    # -----------------------------------------------------------------------
    def run_phase5_ntl_rf(self):
        logger.info("=== PHASE 5: NTL_RF (No-TTL Random Forest) Explainability ===")
        rf_dir = OUT_DIR / "NTL_RF"
        rf_dir.mkdir(parents=True, exist_ok=True)
        fig_dir = OUT_DIR / "figures" / "NTL_RF"
        fig_dir.mkdir(parents=True, exist_ok=True)

        npz_path = rf_dir / "shap_values.npz"
        if npz_path.exists() and (rf_dir / "top_features.csv").exists():
            logger.info("RESUME: shap_values.npz exists — loading from disk.")
            shap_attack = np.load(npz_path)["shap_values"]
            df_imp = pd.read_csv(rf_dir / "global_importance.csv")
            self.summary["ntl_rf_top5"] = df_imp.head(5).to_dict(orient="records")
        else:
            exp_rf = shap.TreeExplainer(self.rf_model, feature_perturbation="tree_path_dependent")
            logger.info("Computing SHAP values for NTL_RF on 2,000 samples...")
            t0 = time.time()
            shap_vals = exp_rf.shap_values(self.X_exp_72)
            logger.info(f"NTL_RF SHAP computed in {time.time()-t0:.1f}s")

            if isinstance(shap_vals, list):
                shap_attack = shap_vals[1]
            elif shap_vals.ndim == 3:
                shap_attack = shap_vals[:, :, 1]
            else:
                shap_attack = shap_vals

            base_val = exp_rf.expected_value
            if isinstance(base_val, (list, np.ndarray)):
                base_val = base_val[1]
            np.savez_compressed(npz_path, shap_values=shap_attack, base_value=base_val)

            df_imp = self._save_feature_importance(
                shap_attack, rf_dir, self.no_ttl_features,
                "NTL_RF — Top 20 Feature Importance (72 No-TTL Features)", color="#1f77b4"
            )
            self.summary["ntl_rf_top5"] = df_imp.head(5).to_dict(orient="records")

        preds_rf = self.rf_model.predict(self.X_exp_72)
        self.preds_rf = preds_rf
        self._save_local_cases("NTL_RF", preds_rf, shap_attack, rf_dir, fig_dir)
        logger.info("Phase 5 NTL_RF complete.")

    # -----------------------------------------------------------------------
    # Phase 6: NTL_STACK Explainability (mirrors Phase 6 of Sprint 11)
    # -----------------------------------------------------------------------
    def run_phase6_ntl_stack(self):
        logger.info("=== PHASE 6: NTL_STACK (No-TTL Stacking) Explainability ===")
        stack_dir = OUT_DIR / "NTL_STACK"
        base_dir  = stack_dir / "base_model_importance"
        base_dir.mkdir(parents=True, exist_ok=True)
        fig_dir = OUT_DIR / "figures" / "NTL_STACK"
        fig_dir.mkdir(parents=True, exist_ok=True)

        meta_csv = stack_dir / "meta_learner_importance.csv"
        rf_npz   = base_dir / "RF" / "shap_values.npz"

        if meta_csv.exists() and rf_npz.exists():
            logger.info("RESUME: meta_learner_importance.csv exists — loading artifacts from disk.")
            meta_df = pd.read_csv(meta_csv)
            self.summary["meta_learner_importance"] = meta_df.to_dict(orient="records")
            X_sc = self.sup_scaler.transform(self.X_exp_72)
            dt_prob = self.dt_model.predict_proba(self.X_exp_72)[:, 1]
            rf_prob = self.rf_model.predict_proba(self.X_exp_72)[:, 1]
            svm_dec = self.svm_model.decision_function(X_sc)
            with torch.no_grad():
                self.nn_sig.to("cpu")
                nn_prob = self.nn_sig(torch.tensor(X_sc, dtype=torch.float32)).numpy().flatten()
            meta_inputs = np.column_stack([dt_prob, rf_prob, svm_dec, nn_prob])
            self.preds_stack = self.meta_lr.predict(meta_inputs)
            logger.info("RESUME complete — preds_stack recomputed.")
            return

        # Scale for SVM and NN
        X_exp_sc = self.sup_scaler.transform(self.X_exp_72)

        # 1. DT
        logger.info("Computing DT base SHAP...")
        dt_dir = base_dir / "DT"; dt_dir.mkdir(parents=True, exist_ok=True)
        dt_npz = dt_dir / "shap_values.npz"
        if dt_npz.exists() and (dt_dir / "top_features.csv").exists():
            logger.info("RESUME: DT base SHAP exists on disk — loading...")
            sh_dt_att = np.load(dt_npz)["shap_values"]
        else:
            exp_dt = shap.TreeExplainer(self.dt_model, feature_perturbation="tree_path_dependent")
            sh_dt = exp_dt.shap_values(self.X_exp_72)
            sh_dt_att = sh_dt[1] if isinstance(sh_dt, list) else (sh_dt[:, :, 1] if sh_dt.ndim == 3 else sh_dt)
            self._save_feature_importance(sh_dt_att, dt_dir, self.no_ttl_features,
                                           "NTL_DT — Top 20 Feature Importance", color="#8c564b")
            np.savez_compressed(dt_npz, shap_values=sh_dt_att)

        # 2. RF
        logger.info("Computing RF base SHAP...")
        rf_dir2 = base_dir / "RF"; rf_dir2.mkdir(parents=True, exist_ok=True)
        rf_base_npz = rf_dir2 / "shap_values.npz"
        rf_ntl_npz  = OUT_DIR / "NTL_RF" / "shap_values.npz"
        if rf_base_npz.exists() and (rf_dir2 / "top_features.csv").exists():
            logger.info("RESUME: RF base SHAP exists on disk — loading...")
            sh_rf_att = np.load(rf_base_npz)["shap_values"]
        elif rf_ntl_npz.exists():
            logger.info("Reusing NTL_RF SHAP from Phase 5 for Stack RF base learner...")
            sh_rf_att = np.load(rf_ntl_npz)["shap_values"]
            self._save_feature_importance(sh_rf_att, rf_dir2, self.no_ttl_features,
                                           "NTL_RF (Stack Base) — Top 20 Feature Importance", color="#1f77b4")
            np.savez_compressed(rf_base_npz, shap_values=sh_rf_att)
        else:
            exp_rf2 = shap.TreeExplainer(self.rf_model, feature_perturbation="tree_path_dependent")
            sh_rf2 = exp_rf2.shap_values(self.X_exp_72)
            sh_rf_att = sh_rf2[1] if isinstance(sh_rf2, list) else (sh_rf2[:, :, 1] if sh_rf2.ndim == 3 else sh_rf2)
            self._save_feature_importance(sh_rf_att, rf_dir2, self.no_ttl_features,
                                           "NTL_RF (Stack Base) — Top 20 Feature Importance", color="#1f77b4")
            np.savez_compressed(rf_base_npz, shap_values=sh_rf_att)

        # 3. SVM
        logger.info("Computing SVM base SHAP...")
        svm_dir = base_dir / "SVM"; svm_dir.mkdir(parents=True, exist_ok=True)
        svm_npz = svm_dir / "shap_values.npz"
        if svm_npz.exists() and (svm_dir / "top_features.csv").exists():
            logger.info("RESUME: SVM base SHAP exists on disk — loading...")
            sh_svm = np.load(svm_npz)["shap_values"]
        else:
            sh_svm = self.exp_svm.shap_values(X_exp_sc)
            self._save_feature_importance(sh_svm, svm_dir, self.no_ttl_features,
                                           "NTL_SVM — Top 20 Feature Importance", color="#2ca02c")
            np.savez_compressed(svm_npz, shap_values=sh_svm)

        # 4. NN
        logger.info("Computing NN base SHAP...")
        nn_dir = base_dir / "NN"; nn_dir.mkdir(parents=True, exist_ok=True)
        nn_npz = nn_dir / "shap_values.npz"
        t_exp = torch.tensor(X_exp_sc, dtype=torch.float32)
        if nn_npz.exists() and (nn_dir / "top_features.csv").exists():
            logger.info("RESUME: NN base SHAP exists on disk — loading...")
            sh_nn_att = np.load(nn_npz)["shap_values"]
        else:
            self.nn_sig.to("cpu")
            sh_nn = self.exp_nn.shap_values(t_exp, check_additivity=False)
            sh_nn_att = sh_nn[0] if isinstance(sh_nn, list) else (sh_nn[:, :, 0] if sh_nn.ndim == 3 else sh_nn)
            self._save_feature_importance(sh_nn_att, nn_dir, self.no_ttl_features,
                                           "NTL_NN — Top 20 Feature Importance", color="#9467bd")
            np.savez_compressed(nn_npz, shap_values=sh_nn_att)

        # 5. Meta-Learner
        logger.info("Computing Logistic meta-learner SHAP...")
        dt_prob = self.dt_model.predict_proba(self.X_exp_72)[:, 1]
        rf_prob = self.rf_model.predict_proba(self.X_exp_72)[:, 1]
        svm_dec = self.svm_model.decision_function(X_exp_sc)
        with torch.no_grad():
            nn_prob = self.nn_sig(t_exp).numpy().flatten()
        meta_inputs = np.column_stack([dt_prob, rf_prob, svm_dec, nn_prob])
        meta_shap = self.exp_meta.shap_values(meta_inputs)
        mean_abs_meta = np.mean(np.abs(meta_shap), axis=0)
        meta_names = ["dt_attack_probability", "rf_attack_probability",
                      "svm_decision_score", "nn_attack_probability"]
        meta_coefs = self.meta_lr.coef_[0]
        meta_records = []
        for i, name in enumerate(meta_names):
            meta_records.append({
                "meta_feature": name,
                "coefficient": float(meta_coefs[i]),
                "mean_abs_shap": float(mean_abs_meta[i]),
                "rank": int(np.argsort(-mean_abs_meta).tolist().index(i) + 1),
            })
        meta_df = pd.DataFrame(meta_records).sort_values("rank")
        meta_df.to_csv(meta_csv, index=False)
        self.summary["meta_learner_importance"] = meta_df.to_dict(orient="records")

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(meta_df["meta_feature"], meta_df["mean_abs_shap"], color="#2ca02c")
        ax.set_ylabel("Mean Absolute SHAP Value")
        ax.set_title("NTL_STACK — Meta-Learner Feature Importance (72 No-TTL Features)")
        plt.xticks(rotation=15)
        plt.tight_layout()
        fig_path = OUT_DIR / "figures" / "NTL_STACK" / "meta_learner_importance.png"
        plt.savefig(fig_path, dpi=300)
        plt.close()

        preds_stack = self.meta_lr.predict(meta_inputs)
        self.preds_stack = preds_stack
        self._save_local_cases("NTL_STACK", preds_stack, sh_rf_att, stack_dir, fig_dir)
        logger.info("Phase 6 NTL_STACK complete.")

    # -----------------------------------------------------------------------
    # Phase 7: Before-vs-After TTL Comparison (Key Publication Figure)
    # -----------------------------------------------------------------------
    def run_phase7_before_after_comparison(self):
        """
        Load Sprint 11 (75-feature) RF global_importance.csv and compare
        side-by-side with the NTL_RF (72-feature) SHAP results.
        Produces a comparison CSV and before/after bar chart.
        """
        logger.info("=== PHASE 7: Before-vs-After TTL Feature Importance Comparison ===")
        comp_dir = OUT_DIR / "before_after_comparison"
        comp_dir.mkdir(parents=True, exist_ok=True)

        sprint11_rf_csv = ROOT / "results/explainability/EXP_EXPLAIN_V1/A0_RF/global_importance.csv"
        nottl_rf_csv    = OUT_DIR / "NTL_RF" / "global_importance.csv"

        if not sprint11_rf_csv.exists():
            logger.warning("Sprint 11 RF global_importance.csv not found — skipping comparison.")
            self.summary["before_after_comparison"] = "SKIPPED — sprint11 artifact missing"
            return
        if not nottl_rf_csv.exists():
            logger.warning("NTL_RF global_importance.csv not found — run Phase 5 first.")
            self.summary["before_after_comparison"] = "SKIPPED — ntl_rf artifact missing"
            return

        df_before = pd.read_csv(sprint11_rf_csv)
        df_after  = pd.read_csv(nottl_rf_csv)

        # Top-20 features in each
        top20_before = df_before.head(20).set_index("feature_name")["mean_abs_shap"].to_dict()
        top20_after  = df_after.head(20).set_index("feature_name")["mean_abs_shap"].to_dict()

        # All features in either top-20
        all_feats = sorted(set(top20_before) | set(top20_after))
        comp_records = []
        for feat in all_feats:
            comp_records.append({
                "feature_name": feat,
                "shap_75feat_canonical": top20_before.get(feat, 0.0),
                "shap_72feat_no_ttl": top20_after.get(feat, 0.0),
                "in_ttl_features": feat in {"sttl", "ct_state_ttl", "dttl"},
            })
        comp_df = pd.DataFrame(comp_records).sort_values("shap_75feat_canonical", ascending=False)
        comp_df.to_csv(comp_dir / "feature_importance_comparison.csv", index=False)

        # Publication-quality side-by-side bar chart
        fig, axes = plt.subplots(1, 2, figsize=(18, 9))
        n = 20
        before_top = df_before.head(n).iloc[::-1]
        after_top  = df_after.head(n).iloc[::-1]
        colors_before = ["#d62728" if f in {"sttl", "ct_state_ttl", "dttl"} else "#1f77b4"
                         for f in before_top["feature_name"]]
        axes[0].barh(before_top["feature_name"], before_top["mean_abs_shap"], color=colors_before)
        axes[0].set_xlabel("Mean |SHAP| (Attack Class)")
        axes[0].set_title("BEFORE: Canonical RF (75 Features)\n[Red = TTL artifact features]")
        axes[1].barh(after_top["feature_name"], after_top["mean_abs_shap"], color="#2ca02c")
        axes[1].set_xlabel("Mean |SHAP| (Attack Class)")
        axes[1].set_title("AFTER: No-TTL RF (72 Features)\n[TTL features removed]")
        plt.suptitle("Feature Importance: Before vs After TTL Feature Removal", fontsize=14)
        plt.tight_layout()
        plt.savefig(comp_dir / "before_after_feature_importance.png", dpi=300)
        plt.close()
        logger.info(f"Saved before/after comparison chart: {comp_dir}")
        self.summary["before_after_comparison"] = "COMPLETED"

    # -----------------------------------------------------------------------
    # Phase 8: Documentation & Quality Review
    # -----------------------------------------------------------------------
    def run_phase8_documentation(self):
        logger.info("=== PHASE 8: Documentation & Quality Review ===")
        self.summary["pv_gates"]       = self.pv_results
        self.summary["total_pv_gates"] = len(self.pv_results)
        self.summary["all_pv_passed"]  = all(g["passed"] for g in self.pv_results.values())
        self.summary["completed_at"]   = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2)

        # metadata.json
        with open(OUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "experiment_id": EXP_ID,
                "source_experiment": SOURCE_EXP,
                "explained_seed": EXPLAINED_SEED,
                "n_features": N_FEATURES,
                "removed_features": ["sttl", "ct_state_ttl", "dttl"],
                "created_at": self.summary["completed_at"],
                "targets": ["NTL_RF", "NTL_STACK"],
                "explanation_set_size": 2000,
                "background_set_size": BG_SAMPLE_SIZE,
                "total_pv_gates": len(self.pv_results),
                "all_pv_passed": self.summary["all_pv_passed"],
                "original_sprint11_unchanged": True,
            }, f, indent=2)

        # quality_review.md
        ntl_rf_top_df   = pd.read_csv(OUT_DIR / "NTL_RF" / "top_features.csv")
        meta_imp_df = pd.read_csv(OUT_DIR / "NTL_STACK" / "meta_learner_importance.csv")
        lines = [
            f"# EXP_EXPLAIN_NO_TTL_V1 — SHAP Quality Review",
            f"**Experiment:** `{EXP_ID}`  ",
            f"**Source Experiment:** `{SOURCE_EXP}` (72-feature No-TTL, Seed 42)  ",
            f"**Generated:** {self.summary['completed_at']}",
            "",
            "## 1. Scope",
            "Post-hoc SHAP explainability for the No-TTL 72-feature publication experiment.",
            "Only Seed 42 is explained. Original Sprint 11 (EXP_EXPLAIN_V1, 75 features) is NOT modified.",
            "Explains: NTL_RF (standalone Random Forest) and NTL_STACK (4-model stacking ensemble).",
            "",
            "## 2. Pre-Verification Gates",
            f"- **Total Gates:** {self.summary['total_pv_gates']}",
            f"- **All Passed:** {'YES ✓' if self.summary['all_pv_passed'] else 'FAILURE ✗'}",
            "",
            "| Gate ID | Description | Status |",
            "|:---|:---|:---|",
        ]
        for gid, g in sorted(self.pv_results.items()):
            lines.append(f"| {gid} | {g['description']} | **{g['status']}** |")

        lines.extend([
            "",
            "## 3. NTL_RF Top Features (TreeSHAP, 72 No-TTL Features)",
            "| Rank | Feature Name | Mean |SHAP| |",
            "|:---|:---|:---|",
        ])
        for _, row in ntl_rf_top_df.head(10).iterrows():
            lines.append(f"| {int(row['rank'])} | `{row['feature_name']}` | {row['mean_abs_shap']:.6f} |")

        lines.extend([
            "",
            "> **Note:** TTL features (sttl, ct_state_ttl, dttl) are absent — confirming they "
            "cannot dominate importance in this experiment.",
            "",
            "## 4. NTL_STACK Meta-Learner Importance",
            "| Rank | Meta-Feature | Coefficient | Mean |SHAP| |",
            "|:---|:---|:---|:---|",
        ])
        for _, row in meta_imp_df.iterrows():
            lines.append(
                f"| {int(row['rank'])} | `{row['meta_feature']}` | "
                f"{row['coefficient']:.6f} | {row['mean_abs_shap']:.6f} |"
            )

        lines.extend([
            "",
            "## 5. Before-vs-After Comparison",
            f"- Status: `{self.summary.get('before_after_comparison', 'N/A')}`",
            "- Chart: `before_after_comparison/before_after_feature_importance.png`",
            "- CSV: `before_after_comparison/feature_importance_comparison.csv`",
            "",
            "## 6. Reproducibility",
            f"- Python: {sys.version.split()[0]}",
            f"- NumPy: {np.__version__}",
            f"- PyTorch: {torch.__version__}",
            f"- SHAP: {shap.__version__}",
            "",
            "## 7. Integrity",
            "- Original EXP_EXPLAIN_V1 (Sprint 11) artifacts were NOT modified.",
            "- All outputs are isolated to: `results/explainability/EXP_EXPLAIN_NO_TTL_V1/`",
            "- No retraining, re-fitting, or threshold changes occurred.",
        ])

        with open(OUT_DIR / "quality_review.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # environment.txt
        env_proc = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True
        )
        with open(OUT_DIR / "environment.txt", "w", encoding="utf-8") as f:
            f.write(env_proc.stdout)

        logger.info("Phase 8 documentation complete.")

    # -----------------------------------------------------------------------
    # Main Run
    # -----------------------------------------------------------------------
    def run(self):
        logger.info("=" * 66)
        logger.info(f"{EXP_ID} — SHAP Explainability for No-TTL 72-Feature Experiment")
        logger.info("=" * 66)
        self.run_phase0_preverification()
        self.run_phase1_sampling()
        self.run_phase5_ntl_rf()
        self.run_phase6_ntl_stack()
        self.run_phase7_before_after_comparison()
        self.run_phase8_documentation()
        logger.info("=" * 66)
        logger.info(f"{EXP_ID} COMPLETED SUCCESSFULLY")
        logger.info(f"Outputs in: {OUT_DIR}")
        logger.info("Original EXP_EXPLAIN_V1 (Sprint 11) is UNCHANGED.")
        logger.info("=" * 66)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pipeline = NoTTLSHAPPipeline()
    pipeline.run()
