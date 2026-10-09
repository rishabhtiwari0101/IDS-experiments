"""
cicids2017/src/s24_deployment_benchmark.py
--------------------------------------------
Sprint 6 — Step 2: Deployment Inference Benchmark.

Measures local host inference latency, throughput, CPU memory, and GPU memory
across 8 model families on batch volumes of 1k, 10k, and 100k flows sampled
from DEV_TEST.

Mandatory disclaimer:
"Local host inference benchmarks, not production gateway throughput."
"""

from __future__ import annotations

import gc
import json
import logging
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
import joblib

import numpy as np
import pandas as pd
import psutil
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
MODELS_DIR = ROOT / "cicids2017" / "models"
SEL_FEAT_PATH = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection" / "selected_features.json"
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "deployment"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT_DIR / "s24_deployment.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("s24_deployment")

BATCH_VOLUMES = [1000, 10000, 100000]
N_REPEATS = 5
BENCH_SEED = 42
DISCLAIMER = "Local host inference benchmarks, not production gateway throughput."


# ---------------------------------------------------------------------------
# Model Architectures
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
# Benchmark Runner
# ---------------------------------------------------------------------------

def run_timed_inference(predict_fn, n_repeats: int = 5):
    """Executes 1 warm-up run, followed by n_repeats timed runs. Returns timing list."""
    # Warm-up run
    predict_fn()
    if torch.cuda.is_available():
        torch.cuda.synchronize()

    timings = []
    for _ in range(n_repeats):
        t0 = time.perf_counter()
        predict_fn()
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        timings.append(elapsed)

    return timings


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 6 — STEP 2: DEPLOYMENT INFERENCE BENCHMARK")
    logger.info("=" * 70)
    logger.info(DISCLAIMER)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Host compute device: %s", device)

    # Hardware Metadata
    process = psutil.Process()
    hw_info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "cuda_available": torch.cuda.is_available(),
        "gpu_model": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None",
        "gpu_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2) if torch.cuda.is_available() else 0.0,
        "disclaimer": DISCLAIMER,
    }
    logger.info("Hardware info: CPU=%s | RAM=%.1f GB | GPU=%s",
                hw_info["processor"], hw_info["ram_total_gb"], hw_info["gpu_model"])

    # Load Features
    with open(SEL_FEAT_PATH, "r", encoding="utf-8") as f:
        selected_features = json.load(f)["selected_features"]
    n_features = len(selected_features)

    # Load DEV_TEST Sample Pool
    logger.info("Loading DEV_TEST flows for subsampling...")
    df_dev = pd.read_csv(SPLITS_DIR / "dev_test.csv")
    logger.info("Loaded DEV_TEST total: %d flows", len(df_dev))

    # Deterministic Subsamples
    np.random.seed(BENCH_SEED)
    dev_indices = np.random.permutation(len(df_dev))

    batches = {}
    for vol in BATCH_VOLUMES:
        idx = dev_indices[:vol]
        batches[vol] = df_dev.iloc[idx][selected_features].values.astype(np.float32)
        logger.info("Prepared volume N=%d flows, shape=%s", vol, batches[vol].shape)

    # Models from Seed 42
    seed = 42
    model_dir = MODELS_DIR / f"seed_{seed}"
    ft_dir = MODELS_DIR / "ft_transformer" / "full" / f"seed_{seed}"

    logger.info("Loading models from %s...", model_dir)
    dt_model = joblib.load(model_dir / "dt_model.pkl")
    rf_model = joblib.load(model_dir / "rf_model.pkl")
    svm_model = joblib.load(model_dir / "svm_model.pkl")
    svm_scaler = joblib.load(model_dir / "svm_scaler.pkl")

    nn_scaler = joblib.load(model_dir / "nn_scaler.pkl")
    idsnet_model = IDSNet(input_dim=n_features).to(device)
    idsnet_model.load_state_dict(torch.load(model_dir / "nn_model.pt", map_location=device))
    idsnet_model.eval()

    meta_lr = joblib.load(model_dir / "meta_lr.pkl")

    ae_std_scaler = joblib.load(model_dir / "ae_standard_scaler.pkl")
    ae_model = Autoencoder(input_dim=n_features).to(device)
    ae_model.load_state_dict(torch.load(model_dir / "ae_standard_model.pt", map_location=device))
    ae_model.eval()

    if_model = joblib.load(model_dir / "if_model.joblib")

    ft_scaler = joblib.load(ft_dir / "ft_scaler.pkl")
    ft_model = FTTransformerCIC(n_features=n_features).to(device)
    ft_model.load_state_dict(torch.load(ft_dir / "ft_model.pt", map_location=device))
    ft_model.eval()

    results = []

    # Model evaluation definitions
    model_names = [
        "Decision Tree",
        "Random Forest",
        "Linear SVC",
        "IDSNet (MLP)",
        "Stacking Ensemble",
        "Autoencoder (Standard)",
        "Isolation Forest",
        "FT-Transformer",
    ]

    for vol in BATCH_VOLUMES:
        X_raw = batches[vol]
        logger.info("-" * 60)
        logger.info("BENCHMARKING BATCH VOLUME N=%d FLOWS", vol)
        logger.info("-" * 60)

        # Pre-scale inputs once
        X_std = nn_scaler.transform(X_raw)
        X_ft = ft_scaler.transform(X_raw)

        for model_name in model_names:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()

            initial_rss = process.memory_info().rss / (1024 ** 2)

            # Define inference function per model
            if model_name == "Decision Tree":
                predict_fn = lambda: dt_model.predict_proba(X_raw)
                compute_target = "CPU"
            elif model_name == "Random Forest":
                predict_fn = lambda: rf_model.predict_proba(X_raw)
                compute_target = "CPU"
            elif model_name == "Linear SVC":
                predict_fn = lambda: svm_model.decision_function(X_std)
                compute_target = "CPU"
            elif model_name == "IDSNet (MLP)":
                tensor_x = torch.tensor(X_std, device=device)
                predict_fn = lambda: idsnet_model(tensor_x)
                compute_target = "GPU" if device.type == "cuda" else "CPU"
            elif model_name == "Stacking Ensemble":
                tensor_x = torch.tensor(X_std, device=device)
                def stack_infer():
                    p_dt = dt_model.predict_proba(X_raw)[:, 1]
                    p_rf = rf_model.predict_proba(X_raw)[:, 1]
                    df_svm = svm_model.decision_function(X_std)
                    p_svm = 1.0 / (1.0 + np.exp(-df_svm))
                    with torch.no_grad():
                        p_nn = torch.sigmoid(idsnet_model(tensor_x)).cpu().numpy()
                    stacked = np.column_stack([p_dt, p_rf, p_svm, p_nn])
                    return meta_lr.predict_proba(stacked)
                predict_fn = stack_infer
                compute_target = "Hybrid (CPU+GPU)"
            elif model_name == "Autoencoder (Standard)":
                tensor_x = torch.tensor(X_std, device=device)
                predict_fn = lambda: ae_model(tensor_x)
                compute_target = "GPU" if device.type == "cuda" else "CPU"
            elif model_name == "Isolation Forest":
                predict_fn = lambda: if_model.score_samples(X_std)
                compute_target = "CPU"
            elif model_name == "FT-Transformer":
                # Chunked mini-batches for safety to avoid OOM on 100k
                batch_chunk = 4096 if vol == 100000 else vol
                def ft_infer():
                    preds = []
                    with torch.no_grad():
                        for i in range(0, vol, batch_chunk):
                            xb = torch.tensor(X_ft[i:i + batch_chunk], device=device)
                            preds.append(ft_model(xb))
                    return preds
                predict_fn = ft_infer
                compute_target = "GPU (Chunked 4096)" if device.type == "cuda" else "CPU (Chunked 4096)"

            timings_sec = run_timed_inference(predict_fn, n_repeats=N_REPEATS)
            median_sec = float(np.median(timings_sec))
            median_ms = median_sec * 1000.0
            throughput = float(vol / median_sec) if median_sec > 0 else 0.0

            peak_rss = process.memory_info().rss / (1024 ** 2)
            cpu_mem_delta = max(0.0, peak_rss - initial_rss)
            gpu_peak_mb = (torch.cuda.max_memory_allocated() / (1024 ** 2)) if torch.cuda.is_available() else 0.0

            logger.info("  %-25s | median: %8.2f ms | throughput: %10.1f flows/s | CPU RSS: %6.1f MB | GPU VRAM: %6.1f MB",
                        model_name, median_ms, throughput, peak_rss, gpu_peak_mb)

            results.append({
                "model": model_name,
                "n_flows": vol,
                "compute_target": compute_target,
                "median_latency_ms": round(median_ms, 2),
                "throughput_flows_per_s": round(throughput, 1),
                "min_latency_ms": round(float(np.min(timings_sec)) * 1000.0, 2),
                "max_latency_ms": round(float(np.max(timings_sec)) * 1000.0, 2),
                "peak_cpu_rss_mb": round(peak_rss, 1),
                "gpu_peak_vram_mb": round(gpu_peak_mb, 1),
                "disclaimer": DISCLAIMER,
            })

    # Save Tables & Metadata
    df_bench = pd.DataFrame(results)
    csv_path = OUT_DIR / "s24_deployment_benchmark.csv"
    df_bench.to_csv(csv_path, index=False)
    logger.info("Saved benchmark CSV to %s (%d records).", csv_path, len(df_bench))

    json_payload = {
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 6,
        "step": "s24_deployment_benchmark",
        "dataset": "CIC-IDS-2017",
        "benchmark_disclaimer": DISCLAIMER,
        "hardware_environment": hw_info,
        "volumes_evaluated": BATCH_VOLUMES,
        "repeats_per_measurement": N_REPEATS,
        "results": results,
    }

    json_path = OUT_DIR / "s24_deployment_benchmark.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)
    logger.info("Saved benchmark JSON to %s.", json_path)
    logger.info("STEP 2 (DEPLOYMENT BENCHMARK): COMPLETE")


if __name__ == "__main__":
    main()
