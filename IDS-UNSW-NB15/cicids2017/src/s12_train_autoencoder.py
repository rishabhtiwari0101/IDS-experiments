"""
cicids2017/src/s12_train_autoencoder.py
---------------------------------------
Sprint 4 — Step 1 & Step 2: Autoencoder Training (Standard & Log1p Sensitivity)

Requirements:
- Architecture: 69 -> 12 -> 6 -> 12 -> 69 (Linear + ReLU, linear output, no BN, no dropout)
- Total parameters: 25 * 69 + 174 = 1,899 (asserted)
- Training population: Benign TRAIN rows ONLY (label_clean == 'BENIGN', N = 44,800)
- Protocol:
    Phase 1: 90% fit (40,320), 10% monitor (4,480) for early stopping (patience=5, max_epochs=150)
    Phase 2: Refit on ALL 44,800 benign TRAIN rows for best_epoch epochs
- Reconstruction error: RE(x) = mean((x - x_hat)^2) across features
- Seeds: [42, 123, 2024]
- Standard variant: StandardScaler fitted on benign TRAIN rows
- Log1p sensitivity variant:
    Log1p applied to 32 qualifying heavy-tailed features (from log1p_sensitivity_metadata.json)
    Separate StandardScaler fitted on log1p benign TRAIN rows
    Same AE architecture and seeds
- Artifacts saved under:
    cicids2017/models/seed_<SEED>/
    results/cicids2017_revision_v1/autoencoder/standard/
    results/cicids2017_revision_v1/autoencoder/log1p/
"""

from __future__ import annotations

import copy
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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Setup Logging & Directories
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder"
STD_OUT_DIR = OUT_DIR / "standard"
LOG1P_OUT_DIR = OUT_DIR / "log1p"
MODEL_DIR = ROOT / "cicids2017" / "models"
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"

OUT_DIR.mkdir(parents=True, exist_ok=True)
STD_OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG1P_OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s12_autoencoder.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEEDS = [42, 123, 2024]
INPUT_DIM = 69
EXPECTED_PARAMS = 1899
LR = 0.001
WEIGHT_DECAY = 1e-4
BATCH_SIZE = 256
MAX_EPOCHS = 150
PATIENCE = 5
MONITOR_FRACTION = 0.10


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


# ---------------------------------------------------------------------------
# Autoencoder Architecture
# ---------------------------------------------------------------------------
class Autoencoder(nn.Module):
    """
    Preregistered Autoencoder for CIC-IDS-2017:
    69 -> 12 -> 6 -> 12 -> 69 (ReLU hidden, Linear output, no BN, no Dropout).
    Total parameter count: 1,899.
    """
    def __init__(self, input_dim: int = INPUT_DIM):
        super().__init__()
        self.input_dim = input_dim

        # Encoder: 69 -> 12 -> 6
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 12),
            nn.ReLU(),
            nn.Linear(12, 6),
            nn.ReLU(),
        )

        # Decoder: 6 -> 12 -> 69
        self.decoder = nn.Sequential(
            nn.Linear(6, 12),
            nn.ReLU(),
            nn.Linear(12, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Per-sample MSE: mean over features, shape [N]."""
        x_hat = self.forward(x)
        return torch.mean((x - x_hat) ** 2, dim=1)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ---------------------------------------------------------------------------
# Training Logic
# ---------------------------------------------------------------------------
def train_ae_single_seed(
    X_benign_scaled: np.ndarray,
    seed: int,
    variant_name: str,
    device: torch.device,
) -> dict:
    """
    Trains AE on pure benign TRAIN rows with 90/10 monitor split + final refit.
    """
    logger.info("  [%s] Starting training for seed %d (N=%d, D=%d)...",
                variant_name, seed, len(X_benign_scaled), X_benign_scaled.shape[1])
    set_all_seeds(seed)

    n_total = len(X_benign_scaled)
    indices = np.arange(n_total)
    fit_idx, mon_idx = train_test_split(
        indices,
        test_size=MONITOR_FRACTION,
        random_state=seed,
        shuffle=True,
    )

    X_fit = X_benign_scaled[fit_idx]
    X_mon = X_benign_scaled[mon_idx]

    # Data loaders
    t_fit = torch.tensor(X_fit, dtype=torch.float32)
    t_mon = torch.tensor(X_mon, dtype=torch.float32)

    gen = torch.Generator().manual_seed(seed)
    fit_loader = DataLoader(TensorDataset(t_fit), batch_size=BATCH_SIZE, shuffle=True, generator=gen)
    mon_loader = DataLoader(TensorDataset(t_mon), batch_size=BATCH_SIZE, shuffle=False)

    # Initialize model
    model = Autoencoder(input_dim=INPUT_DIM).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    criterion = nn.MSELoss(reduction="mean")

    best_mon_mse = float("inf")
    best_epoch = 0
    best_weights = copy.deepcopy(model.state_dict())
    patience_counter = 0
    history = []

    t0 = time.perf_counter()

    # --- Phase 1: Fit with early stopping ---
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        for (xb,) in fit_loader:
            xb = xb.to(device)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, xb)
            loss.backward()
            optimizer.step()

        # Evaluation on fit and monitor
        model.eval()
        with torch.no_grad():
            fit_mse = sum(criterion(model(xb.to(device)), xb.to(device)).item() * len(xb) for xb, in fit_loader) / len(X_fit)
            mon_mse = sum(criterion(model(xb.to(device)), xb.to(device)).item() * len(xb) for xb, in mon_loader) / len(X_mon)

        history.append({
            "epoch": epoch,
            "fit_mse": float(fit_mse),
            "monitor_mse": float(mon_mse),
        })

        if mon_mse < best_mon_mse:
            best_mon_mse = mon_mse
            best_epoch = epoch
            best_weights = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                logger.info("    [%s Seed %d] Early stopping triggered at epoch %d (best_epoch=%d, min_mon_mse=%.6f)",
                            variant_name, seed, epoch, best_epoch, best_mon_mse)
                break

    phase1_time = time.perf_counter() - t0

    # --- Phase 2: Final refit on ALL benign TRAIN rows for best_epoch epochs ---
    logger.info("    [%s Seed %d] Phase 2: Refitting on ALL %d benign rows for %d epochs...",
                variant_name, seed, n_total, best_epoch)
    set_all_seeds(seed)
    final_model = Autoencoder(input_dim=INPUT_DIM).to(device)
    final_optimizer = torch.optim.Adam(final_model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    t_all = torch.tensor(X_benign_scaled, dtype=torch.float32)
    all_gen = torch.Generator().manual_seed(seed)
    all_loader = DataLoader(TensorDataset(t_all), batch_size=BATCH_SIZE, shuffle=True, generator=all_gen)

    t_refit_start = time.perf_counter()
    for ep in range(1, best_epoch + 1):
        final_model.train()
        for (xb,) in all_loader:
            xb = xb.to(device)
            final_optimizer.zero_grad()
            out = final_model(xb)
            loss = criterion(out, xb)
            loss.backward()
            final_optimizer.step()

    total_time = time.perf_counter() - t0
    final_model.eval()

    # Final reconstruction error on full benign TRAIN
    with torch.no_grad():
        final_mse = sum(criterion(final_model(xb.to(device)), xb.to(device)).item() * len(xb) for xb, in all_loader) / n_total

    logger.info("    [%s Seed %d] Complete: best_epoch=%d | final_mse=%.6f | total_time=%.1fs",
                variant_name, seed, best_epoch, final_mse, total_time)

    return {
        "variant": variant_name,
        "seed": seed,
        "best_epoch": best_epoch,
        "min_monitor_mse": float(best_mon_mse),
        "final_refit_mse": float(final_mse),
        "history": history,
        "phase1_time_s": float(phase1_time),
        "total_time_s": float(total_time),
        "model_state": final_model.state_dict(),
        "final_model": final_model,
    }


# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4 — STEP 1 & 2: AUTOENCODER TRAINING (STANDARD & LOG1P)")
    logger.info("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Compute Device: %s", device)

    # 1. Verify model architecture and parameter count
    dummy_model = Autoencoder(input_dim=INPUT_DIM)
    n_params = count_parameters(dummy_model)
    logger.info("AE Architecture: %s", dummy_model)
    logger.info("AE Parameter Count: %d (Expected: %d)", n_params, EXPECTED_PARAMS)
    assert n_params == EXPECTED_PARAMS, f"Parameter count mismatch: {n_params} != {EXPECTED_PARAMS}"
    del dummy_model

    # 2. Load feature schema
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    assert len(feature_list) == INPUT_DIM, f"Schema features {len(feature_list)} != {INPUT_DIM}"

    # 3. Load log1p metadata for Step 2
    with open(PREPROC_DIR / "log1p_sensitivity_metadata.json") as f:
        log1p_meta = json.load(f)
    heavy_tail_features = log1p_meta["qualifying_features"]
    logger.info("Loaded %d qualifying heavy-tailed features for log1p sensitivity", len(heavy_tail_features))
    assert len(heavy_tail_features) == 32, f"Expected 32 heavy-tailed features, got {len(heavy_tail_features)}"

    # 4. Load TRAIN dataset and filter to benign rows only
    train_path = SPLITS_DIR / "train.csv"
    logger.info("Loading TRAIN dataset: %s", train_path)
    train_df = pd.read_csv(train_path)
    logger.info("TRAIN total rows: %d", len(train_df))

    benign_mask = (train_df["label_clean"] == "BENIGN")
    benign_train_df = train_df[benign_mask].copy()
    n_benign = len(benign_train_df)
    logger.info("Benign TRAIN rows: %d", n_benign)
    assert n_benign > 0, "No benign rows found in TRAIN!"

    # Extract raw feature matrix for benign TRAIN
    X_benign_raw = benign_train_df[feature_list].to_numpy(dtype=np.float64)
    assert X_benign_raw.shape == (n_benign, INPUT_DIM)

    # Check for NaNs or Infs
    assert not np.isnan(X_benign_raw).any(), "NaN found in benign TRAIN features!"
    assert not np.isinf(X_benign_raw).any(), "Inf found in benign TRAIN features!"

    metadata_records = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "input_dim": INPUT_DIM,
        "parameter_count": n_params,
        "benign_train_rows": n_benign,
        "seeds": SEEDS,
        "device": str(device),
        "standard_results": {},
        "log1p_results": {},
    }

    # =======================================================================
    # STEP 1: Standard Autoencoder Training
    # =======================================================================
    logger.info("-" * 70)
    logger.info("STEP 1: Training STANDARD Autoencoder (Seeds: %s)", SEEDS)
    logger.info("-" * 70)

    # Fit standard scaler strictly on benign TRAIN rows
    std_scaler = StandardScaler()
    X_std_scaled = std_scaler.fit_transform(X_benign_raw)

    # Save standard scaler
    std_scaler_path = OUT_DIR / "scaler_benign_train.pkl"
    with open(std_scaler_path, "wb") as f:
        pickle.dump(std_scaler, f)
    std_scaler_sha = sha256_file(std_scaler_path)
    logger.info("Standard benign scaler saved: %s | SHA-256: %s", std_scaler_path.name, std_scaler_sha)

    for seed in SEEDS:
        res = train_ae_single_seed(X_std_scaled, seed, "Standard", device)

        # Save model checkpoint
        seed_model_dir = MODEL_DIR / f"seed_{seed}"
        seed_model_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = seed_model_dir / "ae_standard_model.pt"
        torch.save(res["model_state"], ckpt_path)
        ckpt_sha = sha256_file(ckpt_path)

        # Also save scaler in seed dir for modular access
        seed_scaler_path = seed_model_dir / "ae_standard_scaler.pkl"
        with open(seed_scaler_path, "wb") as f:
            pickle.dump(std_scaler, f)

        # Save training summary in results
        seed_res_dir = STD_OUT_DIR / f"seed_{seed}"
        seed_res_dir.mkdir(parents=True, exist_ok=True)
        summary_path = seed_res_dir / "training_summary.json"
        summary_data = {
            "seed": seed,
            "best_epoch": res["best_epoch"],
            "min_monitor_mse": res["min_monitor_mse"],
            "final_refit_mse": res["final_refit_mse"],
            "phase1_time_s": res["phase1_time_s"],
            "total_time_s": res["total_time_s"],
            "checkpoint_path": str(ckpt_path.relative_to(ROOT)),
            "checkpoint_sha256": ckpt_sha,
            "history": res["history"],
        }
        with open(summary_path, "w") as f:
            json.dump(summary_data, f, indent=2)

        metadata_records["standard_results"][str(seed)] = {
            "best_epoch": res["best_epoch"],
            "min_monitor_mse": res["min_monitor_mse"],
            "final_refit_mse": res["final_refit_mse"],
            "total_time_s": res["total_time_s"],
            "checkpoint_sha256": ckpt_sha,
        }

    # =======================================================================
    # STEP 2: Log1p Sensitivity Autoencoder Training
    # =======================================================================
    logger.info("-" * 70)
    logger.info("STEP 2: Training LOG1P SENSITIVITY Autoencoder (Seeds: %s)", SEEDS)
    logger.info("-" * 70)

    # Apply log1p transform strictly to qualifying heavy-tailed features
    heavy_tail_indices = [feature_list.index(f) for f in heavy_tail_features]
    X_benign_log1p = X_benign_raw.copy()
    for idx in heavy_tail_indices:
        X_benign_log1p[:, idx] = np.log1p(np.maximum(0.0, X_benign_log1p[:, idx]))

    # Fit log1p scaler strictly on log1p-transformed benign TRAIN rows
    log1p_scaler = StandardScaler()
    X_log1p_scaled = log1p_scaler.fit_transform(X_benign_log1p)

    log1p_scaler_path = OUT_DIR / "scaler_benign_train_log1p.pkl"
    with open(log1p_scaler_path, "wb") as f:
        pickle.dump(log1p_scaler, f)
    log1p_scaler_sha = sha256_file(log1p_scaler_path)
    logger.info("Log1p benign scaler saved: %s | SHA-256: %s", log1p_scaler_path.name, log1p_scaler_sha)

    for seed in SEEDS:
        res = train_ae_single_seed(X_log1p_scaled, seed, "Log1p", device)

        # Save model checkpoint
        seed_model_dir = MODEL_DIR / f"seed_{seed}"
        ckpt_path = seed_model_dir / "ae_log1p_model.pt"
        torch.save(res["model_state"], ckpt_path)
        ckpt_sha = sha256_file(ckpt_path)

        seed_scaler_path = seed_model_dir / "ae_log1p_scaler.pkl"
        with open(seed_scaler_path, "wb") as f:
            pickle.dump(log1p_scaler, f)

        # Save training summary in results
        seed_res_dir = LOG1P_OUT_DIR / f"seed_{seed}"
        seed_res_dir.mkdir(parents=True, exist_ok=True)
        summary_path = seed_res_dir / "training_summary.json"
        summary_data = {
            "seed": seed,
            "best_epoch": res["best_epoch"],
            "min_monitor_mse": res["min_monitor_mse"],
            "final_refit_mse": res["final_refit_mse"],
            "phase1_time_s": res["phase1_time_s"],
            "total_time_s": res["total_time_s"],
            "checkpoint_path": str(ckpt_path.relative_to(ROOT)),
            "checkpoint_sha256": ckpt_sha,
            "history": res["history"],
        }
        with open(summary_path, "w") as f:
            json.dump(summary_data, f, indent=2)

        metadata_records["log1p_results"][str(seed)] = {
            "best_epoch": res["best_epoch"],
            "min_monitor_mse": res["min_monitor_mse"],
            "final_refit_mse": res["final_refit_mse"],
            "total_time_s": res["total_time_s"],
            "checkpoint_sha256": ckpt_sha,
        }

    # Save overall metadata
    meta_path = OUT_DIR / "autoencoder_training_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata_records, f, indent=2)
    logger.info("Overall Autoencoder metadata saved: %s", meta_path.name)

    logger.info("=" * 70)
    logger.info("STEPS 1 & 2: PASS — ALL AUTOENCODER MODELS TRAINED SUCCESSFULLY")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
