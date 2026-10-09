"""
cicids2017/src/s22_train_ft_transformer_unsw.py
------------------------------------------------
Sprint 5 — Part B, Step 2: FT-Transformer Baseline on UNSW-NB15

Trains the IDENTICAL compact FT-Transformer architecture on UNSW-NB15.
Uses the frozen UNSW K=50 selected features from the UNSW pipeline.

UNSW is a FROZEN benchmark. This script:
  - Uses ONLY UNSW data/splits/train.csv for fitting
  - Evaluates on UNSW data/splits/development_test.csv
  - Does NOT modify any UNSW results, models, or artifacts
  - Does NOT overwrite any UNSW frozen checkpoint

Architecture (IDENTICAL to s21 — fixed):
  d_model=64, n_heads=4, n_blocks=3, ffn_dim=128, dropout=0.1
  CLS token, seq_len=50+1=51
  StandardScaler on TRAIN only

Output:
  results/unsw_revision_v1/ft_transformer/s22_ft_transformer_unsw_results.json
  cicids2017/models/ft_transformer_unsw/
  (stored under cicids2017/ to keep all sprint5 models together)
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
OUT_DIR   = ROOT / "results" / "cicids2017_revision_v1" / "transformer" / "unsw"
MODEL_DIR = ROOT / "cicids2017" / "models" / "transformer" / "unsw"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s22_ft_transformer_unsw.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UNSW_SPLITS_DIR = ROOT / "data" / "splits"
UNSW_SEL_FEAT   = ROOT / "results" / "feature_selection" / "EXP_MI_V1" / "selected_features.json"

H1_SEEDS = [42, 123, 2024]

# Identical architecture to s21
FT_D_MODEL  = 64
FT_N_HEADS  = 4
FT_N_BLOCKS = 3
FT_FFN_DIM  = 128
FT_DROPOUT  = 0.1

FT_LR     = 1e-4
FT_WD     = 1e-5
FT_BATCH  = 512
FT_EPOCHS = 30


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
# FT-Transformer (IDENTICAL to s21)
# ---------------------------------------------------------------------------

class FTTransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, ffn_dim, dropout):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn  = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn   = nn.Sequential(
            nn.Linear(d_model, ffn_dim), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(ffn_dim, d_model), nn.Dropout(dropout),
        )

    def forward(self, x):
        h = self.norm1(x)
        h, _ = self.attn(h, h, h, need_weights=False)
        x = x + h
        h = self.norm2(x)
        h = self.ffn(h)
        return x + h


class FTTransformerUNSW(nn.Module):
    def __init__(self, n_features, d_model=64, n_heads=4, n_blocks=3, ffn_dim=128, dropout=0.1):
        super().__init__()
        self.n_features = n_features
        self.feat_embed = nn.Linear(1, d_model)
        self.feat_bias  = nn.Parameter(torch.zeros(n_features, d_model))
        self.cls_token  = nn.Parameter(torch.randn(1, 1, d_model))
        self.blocks     = nn.ModuleList([
            FTTransformerBlock(d_model, n_heads, ffn_dim, dropout) for _ in range(n_blocks)
        ])
        self.norm_out = nn.LayerNorm(d_model)
        self.head     = nn.Linear(d_model, 1)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x):
        B, F = x.shape
        tokens = self.feat_embed(x.unsqueeze(-1)) + self.feat_bias.unsqueeze(0)
        cls    = self.cls_token.expand(B, -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)
        for block in self.blocks:
            tokens = block(tokens)
        cls_out = self.norm_out(tokens[:, 0, :])
        return self.head(cls_out).squeeze(-1)


def train_ft_transformer(X_train, y_train, seed, device, D):
    set_all_seeds(seed)
    logger.info("FT-Transformer UNSW | seed=%d | D=%d | seq_len=%d+1 | device=%s",
                seed, D, D, device)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X_train)

    X_t = torch.tensor(X_sc, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    loader = DataLoader(TensorDataset(X_t, y_t), batch_size=FT_BATCH,
                        shuffle=True, pin_memory=device.type == "cuda")

    model = FTTransformerUNSW(n_features=D, d_model=FT_D_MODEL, n_heads=FT_N_HEADS,
                               n_blocks=FT_N_BLOCKS, ffn_dim=FT_FFN_DIM,
                               dropout=FT_DROPOUT).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=FT_LR, weight_decay=FT_WD)
    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info("FT-Transformer UNSW params: %d", param_count)

    t0 = time.perf_counter()
    for epoch in range(1, FT_EPOCHS + 1):
        model.train()
        total_loss, n_batches = 0.0, 0
        for xb, yb in loader:
            xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches  += 1
        if epoch % 10 == 0 or epoch == FT_EPOCHS:
            logger.info("  seed=%d epoch %d/%d | loss=%.6f",
                        seed, epoch, FT_EPOCHS, total_loss / max(n_batches, 1))
    logger.info("FT-Transformer UNSW training done | %.2fs", time.perf_counter() - t0)
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
    logger.info("SPRINT 5 — PART B STEP 2: FT-TRANSFORMER UNSW-NB15")
    logger.info("UNSW IS FROZEN — no UNSW files modified.")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Load UNSW selected features
    if not UNSW_SEL_FEAT.exists():
        logger.error("UNSW selected features not found: %s", UNSW_SEL_FEAT)
        sys.exit(1)
    with open(UNSW_SEL_FEAT) as f:
        sel_json = json.load(f)
    unsw_features = sel_json["features"]
    K_unsw = len(unsw_features)
    logger.info("UNSW selected features: K=%d", K_unsw)
    logger.info("Features: %s", unsw_features[:5])

    from src.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    from scipy import stats as st

    def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
        if n == 0:
            return (0.0, 0.0)
        res = st.binomtest(k, n).proportion_ci(confidence_level=1.0 - alpha, method="wilson")
        return float(res.low), float(res.high)

    # Load UNSW TRAIN and fit PreprocessingPipeline (TRAIN only — strictly leakage-free)
    train_path = UNSW_SPLITS_DIR / "train.csv"
    logger.info("Loading UNSW TRAIN: %s", train_path)
    train_df = pd.read_csv(train_path)

    logger.info("Fitting UNSW PreprocessingPipeline on TRAIN...")
    pipeline = PreprocessingPipeline(experiment_id="FT_TRANSFORMER_UNSW")
    pipeline.fit(train_df)

    proc_train = pipeline.transform(train_df, view="unscaled", split_name="train")
    feat_indices = [proc_train.feature_names.index(f) for f in unsw_features]

    X_train = proc_train.X[:, feat_indices]
    y_train = proc_train.y.to_numpy(dtype=np.int64)
    logger.info("UNSW TRAIN (encoded): shape=%s  benign=%d  attack=%d",
                X_train.shape, int((y_train == 0).sum()), int((y_train == 1).sum()))

    # Load UNSW DEV_TEST (for evaluation only — no fitting)
    dev_test_path = UNSW_SPLITS_DIR / "development_test.csv"
    logger.info("Loading UNSW DEV_TEST: %s", dev_test_path)
    dev_df  = pd.read_csv(dev_test_path)
    proc_dev = pipeline.transform(dev_df, view="unscaled", split_name="development_test")
    X_dev   = proc_dev.X[:, feat_indices]
    y_dev   = proc_dev.y.to_numpy(dtype=np.int64)
    logger.info("UNSW DEV_TEST (encoded): shape=%s  benign=%d  attack=%d",
                X_dev.shape, int((y_dev == 0).sum()), int((y_dev == 1).sum()))

    # Load UNSW PROTECTED BACKDOOR (zero-day evaluation — no fitting)
    prot_path = UNSW_SPLITS_DIR / "protected_unseen_attack.csv"
    logger.info("Loading UNSW PROTECTED BACKDOOR: %s", prot_path)
    prot_df = pd.read_csv(prot_path)
    proc_prot = pipeline.transform(prot_df, view="unscaled", split_name="protected_unseen_attack")
    X_prot  = proc_prot.X[:, feat_indices]
    y_prot  = proc_prot.y.to_numpy(dtype=np.int64)
    n_prot  = len(y_prot)
    logger.info("UNSW PROTECTED BACKDOOR (encoded): shape=%s  rows=%d", X_prot.shape, n_prot)

    all_seed_results = {}

    for seed in H1_SEEDS:
        logger.info("-" * 50)
        logger.info("UNSW FT-Transformer | seed=%d", seed)
        logger.info("-" * 50)

        t_tr0 = time.perf_counter()
        model, scaler = train_ft_transformer(X_train, y_train, seed, device, D=K_unsw)
        train_elapsed = time.perf_counter() - t_tr0

        # Evaluate DEV_TEST
        y_pred, y_proba = predict_ft(model, scaler, X_dev, device)
        metrics = compute_metrics(y_dev, y_pred)
        logger.info("UNSW DEV_TEST seed=%d: macro_f1=%.4f  fpr=%.6f  prec=%.4f  rec=%.4f",
                    seed, metrics["macro_f1"], metrics["fpr"], metrics["precision"], metrics["recall"])

        # Evaluate PROTECTED BACKDOOR (zero-day)
        y_prot_pred, _ = predict_ft(model, scaler, X_prot, device)
        det_prot = int(np.sum(y_prot_pred == 1))
        miss_prot = n_prot - det_prot
        rec_prot = float(det_prot / n_prot) if n_prot > 0 else 0.0
        rec_ci_l, rec_ci_u = wilson_ci(det_prot, n_prot)
        logger.info("UNSW PROTECTED BACKDOOR seed=%d: %d/%d (%.2f%%) [Wilson 95%% CI: %.4f, %.4f]",
                    seed, det_prot, n_prot, rec_prot * 100.0, rec_ci_l, rec_ci_u)

        # Save
        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        model_path  = seed_dir / "ft_model.pt"
        scaler_path = seed_dir / "ft_scaler.pkl"
        torch.save(model.state_dict(), model_path)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        model_sha = sha256_file(model_path)

        all_seed_results[str(seed)] = {
            "dev_test_metrics": metrics,
            "zero_day_backdoor": {
                "n_attack": n_prot,
                "detected": det_prot,
                "missed": miss_prot,
                "recall": rec_prot,
                "wilson_ci_95": [rec_ci_l, rec_ci_u],
            },
            "training_time_seconds": float(train_elapsed),
            "model_sha256": model_sha,
            "artifact": str(model_path.relative_to(ROOT)),
            "D": K_unsw,
            "seq_len": K_unsw + 1,
        }

        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    f1_list = [all_seed_results[str(s)]["dev_test_metrics"]["macro_f1"] for s in H1_SEEDS]
    rec_list = [all_seed_results[str(s)]["zero_day_backdoor"]["recall"] for s in H1_SEEDS]
    logger.info("UNSW FT-Transformer macro_f1: seeds=%s  mean=%.4f  std=%.4f",
                [f"{v:.4f}" for v in f1_list], np.mean(f1_list), np.std(f1_list))
    logger.info("UNSW FT-Transformer zero-day backdoor recall: seeds=%s  mean=%.4f",
                [f"{v:.4f}" for v in rec_list], np.mean(rec_list))

    output = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 5,
        "step": "s22_train_ft_transformer_unsw",
        "dataset": "UNSW-NB15",
        "unsw_frozen_status": "READ-ONLY — no UNSW models or data were modified",
        "seeds": H1_SEEDS,
        "K_unsw": K_unsw,
        "unsw_features": unsw_features,
        "architecture": {
            "d_model": FT_D_MODEL, "n_heads": FT_N_HEADS, "n_blocks": FT_N_BLOCKS,
            "ffn_dim": FT_FFN_DIM, "dropout": FT_DROPOUT,
            "cls_token": True, "input_norm": "StandardScaler",
            "seq_len": K_unsw + 1,
            "note": "Architecture identical to s21 CIC FT-Transformer",
        },
        "training": {"lr": FT_LR, "wd": FT_WD, "batch": FT_BATCH, "epochs": FT_EPOCHS},
        "device": str(device),
        "per_seed_results": all_seed_results,
        "mean_dev_test_macro_f1": float(np.mean(f1_list)),
        "std_dev_test_macro_f1":  float(np.std(f1_list)),
        "note": (
            "FT-Transformer reported as representative modern deep tabular baseline. "
            "Not an exhaustive NIDS survey. Hyperparameters fixed; not tuned. "
            "Evaluated on UNSW development_test (threshold=0.5) for cross-dataset reference."
        ),
    }

    out_path = OUT_DIR / "s22_ft_transformer_unsw_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Results saved: %s", out_path)
    logger.info("STEP (FT-TRANSFORMER UNSW): PASS")
    logger.info("=" * 70)
    print(f"\n[S22 COMPLETE] UNSW FT-Transformer mean macro_f1={np.mean(f1_list):.4f}")
    return output


if __name__ == "__main__":
    main()
