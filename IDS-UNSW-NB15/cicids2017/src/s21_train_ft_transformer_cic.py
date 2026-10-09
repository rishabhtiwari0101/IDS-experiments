"""
cicids2017/src/s21_train_ft_transformer_cic.py
-----------------------------------------------
Sprint 5 — Part B, Step 1: FT-Transformer Baseline on CIC-IDS-2017

Trains a compact native-PyTorch FT-Transformer on:
  (a) Full feature set: K*=69 selected features
  (b) Ablated feature set: D_ablated=67 (shortcuts removed)

Architecture (fixed — do NOT tune):
  d_model = 64
  n_heads = 4
  n_blocks = 3
  ffn_dim = 128
  dropout = 0.1
  CLS token: prepend one learned CLS embedding
  Sequence length: (K*+1) or (D_ablated+1)
  Output: LayerNorm → linear(64→1) on CLS position

Training:
  - Adam, lr=1e-4, weight_decay=1e-5
  - epochs=30, batch_size=512
  - Seeds: [42, 123, 2024]
  - Strictly TRAIN only (no DEV_TEST during training)
  - StandardScaler fitted on TRAIN only

Evaluation:
  - Reported on DEV_TEST (threshold=0.5)
  - FT-Transformer is a BASELINE REFERENCE — not a replacement for stacking

Output:
  results/cicids2017_revision_v1/ft_transformer/
  cicids2017/models/ft_transformer/
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import math
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR   = ROOT / "results" / "cicids2017_revision_v1" / "ft_transformer"
MODEL_DIR = ROOT / "cicids2017" / "models" / "ft_transformer"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s21_ft_transformer_cic.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR  = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR     = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
SHORTCUT_FILE = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"

EXPECTED_SHORTCUT_SHA256 = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
H1_SEEDS = [42, 123, 2024]

# FT-Transformer hyperparameters (FROZEN — do not tune)
FT_D_MODEL  = 64
FT_N_HEADS  = 4
FT_N_BLOCKS = 3
FT_FFN_DIM  = 128
FT_DROPOUT  = 0.1

# Training
FT_LR      = 1e-4
FT_WD      = 1e-5
FT_BATCH   = 512
FT_EPOCHS  = 30


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def set_all_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


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


# ---------------------------------------------------------------------------
# FT-Transformer Architecture
# ---------------------------------------------------------------------------

class FTTransformerBlock(nn.Module):
    """Single FT-Transformer block: Pre-LN → MHA → residual → Pre-LN → FFN → residual."""

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
        # Pre-LN self-attention
        h = self.norm1(x)
        h, _ = self.attn(h, h, h, need_weights=False)
        x = x + h
        # Pre-LN FFN
        h = self.norm2(x)
        h = self.ffn(h)
        x = x + h
        return x


class FTTransformerCIC(nn.Module):
    """
    Compact FT-Transformer for CIC-IDS-2017 binary classification.

    Input: (batch, n_features) float32 — already scaled
    Processing:
      1. Linear token embedding: (batch, n_features, d_model)
      2. Prepend CLS token: (batch, n_features+1, d_model)
      3. n_blocks of FTTransformerBlock
      4. Extract CLS → LayerNorm → Linear(d_model, 1) → scalar logit
    """

    def __init__(self, n_features: int, d_model: int = 64, n_heads: int = 4,
                 n_blocks: int = 3, ffn_dim: int = 128, dropout: float = 0.1):
        super().__init__()
        self.n_features = n_features
        self.d_model    = d_model

        # Feature token embedding: each feature → d_model via shared linear + individual bias
        self.feat_embed = nn.Linear(1, d_model)  # applied per-feature
        self.feat_bias  = nn.Parameter(torch.zeros(n_features, d_model))

        # CLS token
        self.cls_token  = nn.Parameter(torch.randn(1, 1, d_model))

        # Transformer blocks
        self.blocks = nn.ModuleList([
            FTTransformerBlock(d_model, n_heads, ffn_dim, dropout)
            for _ in range(n_blocks)
        ])

        self.norm_out = nn.LayerNorm(d_model)
        self.head     = nn.Linear(d_model, 1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, n_features) float32
        returns: (batch,) logits
        """
        B, F = x.shape
        assert F == self.n_features, f"Feature dim mismatch: {F} != {self.n_features}"

        # Embed each feature: (B, F) → (B, F, d_model)
        x_unsq = x.unsqueeze(-1)                       # (B, F, 1)
        tokens = self.feat_embed(x_unsq) + self.feat_bias.unsqueeze(0)  # (B, F, d_model)

        # Prepend CLS token
        cls = self.cls_token.expand(B, -1, -1)          # (B, 1, d_model)
        tokens = torch.cat([cls, tokens], dim=1)         # (B, F+1, d_model)

        # Transformer blocks
        for block in self.blocks:
            tokens = block(tokens)

        # Extract CLS (position 0)
        cls_out = tokens[:, 0, :]                        # (B, d_model)
        cls_out = self.norm_out(cls_out)
        logits  = self.head(cls_out).squeeze(-1)         # (B,)
        return logits


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_ft_transformer(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int,
    device: torch.device,
    label: str = "",
) -> tuple[FTTransformerCIC, StandardScaler]:
    set_all_seeds(seed)
    D = X_train.shape[1]
    logger.info("FT-Transformer | %s | seed=%d | D=%d | seq_len=%d+1 | device=%s",
                label, seed, D, D, device)

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X_train)

    X_t = torch.tensor(X_sc, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    dataset = TensorDataset(X_t, y_t)
    loader  = DataLoader(dataset, batch_size=FT_BATCH, shuffle=True, pin_memory=device.type == "cuda")

    model     = FTTransformerCIC(n_features=D, d_model=FT_D_MODEL, n_heads=FT_N_HEADS,
                                  n_blocks=FT_N_BLOCKS, ffn_dim=FT_FFN_DIM, dropout=FT_DROPOUT).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=FT_LR, weight_decay=FT_WD)

    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info("FT-Transformer params: %d", param_count)

    t0 = time.perf_counter()
    for epoch in range(1, FT_EPOCHS + 1):
        model.train()
        total_loss = 0.0
        n_batches  = 0
        for xb, yb in loader:
            xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches  += 1
        avg_loss = total_loss / max(n_batches, 1)
        if epoch % 10 == 0 or epoch == FT_EPOCHS:
            logger.info("  [%s] seed=%d epoch %d/%d | loss=%.6f",
                        label, seed, epoch, FT_EPOCHS, avg_loss)
    elapsed = time.perf_counter() - t0
    logger.info("FT-Transformer [%s] training done | %.2fs", label, elapsed)
    return model, scaler


def predict_ft(model, scaler, X, device, threshold=0.5):
    model.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32)
    preds, probas = [], []
    bs = 2048
    with torch.no_grad():
        for i in range(0, len(X_t), bs):
            xb = X_t[i:i+bs].to(device)
            logits = model(xb).cpu().numpy()
            pr = 1.0 / (1.0 + np.exp(-logits))
            preds.append((pr >= threshold).astype(np.int64))
            probas.append(pr)
    return np.concatenate(preds), np.concatenate(probas)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 5 — PART B STEP 1: FT-TRANSFORMER CIC-IDS-2017")
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

    # Load TRAIN
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    X_full = train_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in train_df.columns:
        y_train = (train_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_train = (train_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    sel_idx = [feature_list.index(f) for f in selected_features]
    abl_idx = [feature_list.index(f) for f in ablated_features]
    X_train_sel = X_full[:, sel_idx]   # (N, 69)
    X_train_abl = X_full[:, abl_idx]   # (N, 67)

    logger.info("TRAIN: rows=%d  benign=%d  attack=%d",
                len(y_train), int((y_train == 0).sum()), int((y_train == 1).sum()))

    # Load DEV_TEST
    dev_df = pd.read_csv(SPLITS_DIR / "dev_test.csv")
    X_dev_full = dev_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in dev_df.columns:
        y_dev = (dev_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_dev = (dev_df["Label"] != "BENIGN").astype(np.int64).to_numpy()
    X_dev_sel = X_dev_full[:, sel_idx]
    X_dev_abl = X_dev_full[:, abl_idx]
    logger.info("DEV_TEST: rows=%d  benign=%d  attack=%d",
                len(y_dev), int((y_dev == 0).sum()), int((y_dev == 1).sum()))

    from scipy import stats as st

    def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
        if n == 0:
            return (0.0, 0.0)
        res = st.binomtest(k, n).proportion_ci(confidence_level=1.0 - alpha, method="wilson")
        return float(res.low), float(res.high)

    # Load PROTECTED_BOT (1,948 instances)
    bot_df = pd.read_csv(SPLITS_DIR / "protected_bot.csv")
    X_bot_full = bot_df[feature_list].to_numpy(dtype=np.float64)
    X_bot_sel  = X_bot_full[:, sel_idx]
    X_bot_abl  = X_bot_full[:, abl_idx]
    n_bot = len(bot_df)
    logger.info("PROTECTED_BOT: rows=%d", n_bot)

    # Load EVAL_CONTROL (10,000 instances)
    ctrl_df = pd.read_csv(SPLITS_DIR / "eval_control.csv")
    X_ctrl_full = ctrl_df[feature_list].to_numpy(dtype=np.float64)
    X_ctrl_sel  = X_ctrl_full[:, sel_idx]
    X_ctrl_abl  = X_ctrl_full[:, abl_idx]
    n_ctrl = len(ctrl_df)
    logger.info("EVAL_CONTROL: rows=%d", n_ctrl)

    all_results = {}

    for variant, (X_tr, X_dev, X_bot, X_ctrl, D, feat_label) in [
        ("full",    (X_train_sel, X_dev_sel, X_bot_sel, X_ctrl_sel, k_star,   "K*=69")),
        ("ablated", (X_train_abl, X_dev_abl, X_bot_abl, X_ctrl_abl, D_ablated, "D=67")),
    ]:
        logger.info("-" * 60)
        logger.info("FT-Transformer variant: %s (%s)", variant, feat_label)
        logger.info("-" * 60)
        variant_results = {}

        for seed in H1_SEEDS:
            logger.info("Training seed=%d  variant=%s", seed, variant)
            t_tr0 = time.perf_counter()
            model, scaler = train_ft_transformer(X_tr, y_train, seed, device, label=variant)
            train_elapsed = time.perf_counter() - t_tr0

            # Evaluate on DEV_TEST
            y_pred, y_proba = predict_ft(model, scaler, X_dev, device)
            metrics = compute_metrics(y_dev, y_pred)
            logger.info("[%s] seed=%d DEV_TEST macro_f1=%.4f  fpr=%.6f  prec=%.4f  rec=%.4f",
                        variant, seed, metrics["macro_f1"], metrics["fpr"], metrics["precision"], metrics["recall"])

            # Evaluate on PROTECTED_BOT (zero-day)
            y_bot_pred, _ = predict_ft(model, scaler, X_bot, device)
            det_bot = int(np.sum(y_bot_pred == 1))
            miss_bot = n_bot - det_bot
            rec_bot = float(det_bot / n_bot) if n_bot > 0 else 0.0
            rec_ci_l, rec_ci_u = wilson_ci(det_bot, n_bot)
            logger.info("[%s] seed=%d PROTECTED_BOT: %d/%d (%.2f%%) [Wilson 95%% CI: %.4f, %.4f]",
                        variant, seed, det_bot, n_bot, rec_bot * 100.0, rec_ci_l, rec_ci_u)

            # Evaluate on EVAL_CONTROL
            y_ctrl_pred, _ = predict_ft(model, scaler, X_ctrl, device)
            fp_ctrl = int(np.sum(y_ctrl_pred == 1))
            fpr_ctrl = float(fp_ctrl / n_ctrl) if n_ctrl > 0 else 0.0
            alerts_10k = float(fpr_ctrl * 10000.0)

            # Precision conventions
            prec_nat = float(det_bot / (det_bot + fp_ctrl)) if (det_bot + fp_ctrl) > 0 else 0.0
            pi = 0.0306
            denom_std = (rec_bot * pi) + (fpr_ctrl * (1.0 - pi))
            prec_std = float((rec_bot * pi) / denom_std) if denom_std > 0 else 0.0

            # Save model
            seed_dir = MODEL_DIR / variant / f"seed_{seed}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            model_path  = seed_dir / "ft_model.pt"
            scaler_path = seed_dir / "ft_scaler.pkl"
            torch.save(model.state_dict(), model_path)
            with open(scaler_path, "wb") as f:
                pickle.dump(scaler, f)
            model_sha = sha256_file(model_path)

            variant_results[str(seed)] = {
                "dev_test_metrics": metrics,
                "zero_day_bot": {
                    "n_attack": n_bot,
                    "detected": det_bot,
                    "missed": miss_bot,
                    "recall": rec_bot,
                    "wilson_ci_95": [rec_ci_l, rec_ci_u],
                },
                "eval_control": {
                    "n_control": n_ctrl,
                    "fp": fp_ctrl,
                    "fpr": fpr_ctrl,
                    "alerts_per_10k": alerts_10k,
                },
                "precision_natural": prec_nat,
                "precision_standardized_pi0306": prec_std,
                "training_time_seconds": float(train_elapsed),
                "model_sha256": model_sha,
                "artifact": str(model_path.relative_to(ROOT)),
                "D": D,
                "seq_len": D + 1,
            }

            del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # Summary across seeds
        f1_list = [variant_results[str(s)]["dev_test_metrics"]["macro_f1"] for s in H1_SEEDS]
        rec_list = [variant_results[str(s)]["zero_day_bot"]["recall"] for s in H1_SEEDS]
        logger.info("[%s] macro_f1: seeds=%s  mean=%.4f  std=%.4f",
                    variant, [f"{v:.4f}" for v in f1_list], np.mean(f1_list), np.std(f1_list))
        logger.info("[%s] bot recall: seeds=%s  mean=%.4f",
                    variant, [f"{v:.4f}" for v in rec_list], np.mean(rec_list))
        all_results[variant] = {
            "variant": variant,
            "feat_label": feat_label,
            "D": D,
            "per_seed": variant_results,
            "mean_dev_test_macro_f1": float(np.mean(f1_list)),
            "std_dev_test_macro_f1":  float(np.std(f1_list)),
            "mean_zero_day_bot_recall": float(np.mean(rec_list)),
        }

    # Save
    output = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 5,
        "step": "s21_train_ft_transformer_cic",
        "dataset": "CIC-IDS-2017",
        "seeds": H1_SEEDS,
        "frozen_shortcuts": frozen_shortcuts,
        "shortcut_sha256_verified": EXPECTED_SHORTCUT_SHA256,
        "k_star_original": k_star,
        "D_ablated": D_ablated,
        "architecture": {
            "d_model": FT_D_MODEL, "n_heads": FT_N_HEADS, "n_blocks": FT_N_BLOCKS,
            "ffn_dim": FT_FFN_DIM, "dropout": FT_DROPOUT,
            "cls_token": True, "input_norm": "StandardScaler",
            "seq_len_full": k_star + 1, "seq_len_ablated": D_ablated + 1,
        },
        "training": {"lr": FT_LR, "wd": FT_WD, "batch": FT_BATCH, "epochs": FT_EPOCHS},
        "device": str(device),
        "results": all_results,
        "note": (
            "FT-Transformer reported as representative modern deep tabular baseline. "
            "Not an exhaustive NIDS survey. Hyperparameters fixed; not tuned. "
            "Evaluated on DEV_TEST (threshold=0.5) for informational comparison only."
        ),
    }

    out_path = OUT_DIR / "s21_ft_transformer_cic_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Results saved: %s", out_path)

    logger.info("=" * 70)
    logger.info("PART B STEP 1 (FT-TRANSFORMER CIC) SUMMARY")
    for variant, res in all_results.items():
        logger.info("  [%s] mean DEV_TEST macro_f1=%.4f ± %.4f",
                    variant, res["mean_dev_test_macro_f1"], res["std_dev_test_macro_f1"])
    logger.info("STEP: PASS")
    logger.info("=" * 70)
    print(f"\n[S21 COMPLETE] FT-Transformer CIC done. Variants: {list(all_results.keys())}")
    return output


if __name__ == "__main__":
    main()
