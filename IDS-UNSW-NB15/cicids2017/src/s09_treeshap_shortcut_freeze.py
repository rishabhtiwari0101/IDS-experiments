"""
cicids2017/src/s09_treeshap_shortcut_freeze.py
------------------------------------------------
Sprint 3 — Step 5: TreeSHAP Attribution & IMMUTABLE Shortcut Freeze

CRITICAL ORDER RULE:
  This script MUST execute and produce shortcut_list_frozen.json
  BEFORE any zero-day evaluation (PROTECTED_BOT, UNSEEN_XSS, UNSEEN_INFILTRATION).

Protocol:
  1. Load seed-42 Random Forest from cicids2017/models/seed_42/rf_model.pkl
  2. Load TRAIN; extract K* selected features
  3. Draw 2,000 stratified TRAIN rows (seed=42)
  4. Compute TreeSHAP using shap.TreeExplainer
  5. Compute mean absolute SHAP per feature
  6. Rank features descending
  7. Apply candidate-pool rule:
       Every candidate in top-10 → frozen shortcut set
       Fallback (none in top-10) → top-3 features overall + label ATTRIBUTION-CONCENTRATION ABLATION
  8. Write shortcut_list_frozen.json with SHA-256
  9. Verify SHA-256

ZERO-DAY BLINDING: This script NEVER opens, loads, or accesses:
  - protected_bot.csv
  - unseen_xss.csv
  - unseen_infiltration.csv
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

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_freeze"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s09_treeshap.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR  = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR     = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
MODEL_DIR   = ROOT / "cicids2017" / "models"

RF_SEED       = 42
SHAP_SEED     = 42
SHAP_N_SAMPLE = 2000
TOP_K         = 10
FALLBACK_K    = 3

# Preregistered candidate pool — MUST MATCH EXACTLY
CANDIDATE_POOL = [
    "Destination Port",
    "Init_Win_bytes_forward",
    "Init_Win_bytes_backward",
    "Flow Duration",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3 — STEP 5: TREESHAP ATTRIBUTION & SHORTCUT FREEZE")
    logger.info("ZERO-DAY BLINDING: NO zero-day files accessed in this script.")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)

    # --- Import shap ---
    try:
        import shap
        logger.info("shap version: %s", shap.__version__)
    except ImportError:
        logger.error("shap is NOT installed. Run: pip install shap")
        sys.exit(1)

    # --- Load frozen feature schema ---
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]

    # --- Load frozen selected features ---
    sel_path = SEL_DIR / "selected_features.json"
    with open(sel_path) as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]
    sel_sha = sha256_file(sel_path)

    logger.info("D=%d  K*=%d  selected_sha=%s", D, k_star, sel_sha[:16])

    # --- Verify candidate pool is a subset of selected features ---
    for cand in CANDIDATE_POOL:
        if cand not in selected_features:
            logger.warning("Candidate '%s' is NOT in selected K*=%d features! "
                           "It will not appear in SHAP results — expected.", cand, k_star)

    # --- Load TRAIN (for SHAP sampling from TRAIN only) ---
    train_path = SPLITS_DIR / "train.csv"
    logger.info("Loading TRAIN: %s", train_path)
    train_df = pd.read_csv(train_path)

    X_full = train_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in train_df.columns:
        y_full = (train_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_full = (train_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    sel_idx = [feature_list.index(f) for f in selected_features]
    X_sel   = X_full[:, sel_idx]

    logger.info("TRAIN rows: %d  X_sel shape: %s", len(y_full), X_sel.shape)

    # --- Stratified SHAP sample from TRAIN only (2,000 rows, seed=42) ---
    rng = np.random.RandomState(SHAP_SEED)
    classes = np.unique(y_full)
    sample_idx_list = []
    n_per_class = SHAP_N_SAMPLE // len(classes)
    for cls in classes:
        cls_idx = np.where(y_full == cls)[0]
        n_pick  = min(n_per_class, len(cls_idx))
        picked  = rng.choice(cls_idx, size=n_pick, replace=False)
        sample_idx_list.extend(picked.tolist())

    # Trim to exactly SHAP_N_SAMPLE
    sample_idx_list = sorted(sample_idx_list[:SHAP_N_SAMPLE])
    X_shap_sample  = X_sel[sample_idx_list]
    y_shap_sample  = y_full[sample_idx_list]
    actual_n_sample = len(sample_idx_list)

    logger.info("SHAP sample: n=%d  benign=%d  attack=%d  seed=%d",
                actual_n_sample,
                int((y_shap_sample == 0).sum()),
                int((y_shap_sample == 1).sum()),
                SHAP_SEED)

    # --- Load seed-42 RF ---
    rf_path = MODEL_DIR / "seed_42" / "rf_model.pkl"
    logger.info("Loading RF: %s", rf_path)
    with open(rf_path, "rb") as f:
        rf = pickle.load(f)
    rf_artifact_sha = sha256_file(rf_path)
    logger.info("RF loaded | artifact SHA-256: %s", rf_artifact_sha)

    # --- TreeSHAP ---
    logger.info("Initializing TreeExplainer (tree_path_dependent) ...")
    t0 = time.perf_counter()
    explainer = shap.TreeExplainer(
        rf,
        feature_perturbation="tree_path_dependent",
    )
    logger.info("Computing SHAP values for %d samples ...", actual_n_sample)
    shap_values = explainer.shap_values(X_shap_sample, check_additivity=False)

    # shap_values may be a list [class0_vals, class1_vals] or 3D array (n_samples, n_features, 2)
    if isinstance(shap_values, list):
        sv = shap_values[1]
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3 and shap_values.shape[2] >= 2:
        sv = shap_values[:, :, 1]
    else:
        sv = shap_values

    # Cache raw shap values immediately
    np.save(OUT_DIR / "raw_shap_values.npy", sv)
    logger.info("Saved raw_shap_values.npy | shape=%s", sv.shape)

    elapsed = time.perf_counter() - t0
    logger.info("TreeSHAP done | %.2fs | sv.shape=%s", elapsed, sv.shape)

    # --- Mean absolute SHAP per feature ---
    mean_abs_shap = np.abs(sv).mean(axis=0)  # shape (K*,)
    assert mean_abs_shap.ndim == 1, f"mean_abs_shap must be 1D, got {mean_abs_shap.shape}"
    assert len(mean_abs_shap) == len(selected_features), "SHAP dim mismatch!"

    # --- Full ranking (descending) ---
    rank_order = np.argsort(mean_abs_shap)[::-1]
    full_ranking = [
        {
            "rank":             int(i + 1),
            "feature":          selected_features[rank_order[i]],
            "mean_abs_shap":    float(mean_abs_shap[rank_order[i]]),
            "is_candidate":     selected_features[rank_order[i]] in CANDIDATE_POOL,
        }
        for i in range(len(selected_features))
    ]

    top_10_features = [r["feature"] for r in full_ranking[:TOP_K]]
    logger.info("Top-%d features by mean |SHAP|:", TOP_K)
    for r in full_ranking[:TOP_K]:
        logger.info("  Rank %2d | %-45s | mean|SHAP|=%.6f | candidate=%s",
                    r["rank"], r["feature"], r["mean_abs_shap"], r["is_candidate"])

    # --- Candidate pool rule ---
    candidates_in_top10 = [
        cand for cand in CANDIDATE_POOL if cand in top_10_features
    ]
    logger.info("Candidate pool check:")
    for cand in CANDIDATE_POOL:
        in_top10 = cand in top_10_features
        cand_rank = next((r["rank"] for r in full_ranking if r["feature"] == cand), None)
        cand_shap = next((r["mean_abs_shap"] for r in full_ranking if r["feature"] == cand), None)
        logger.info("  %s | in_top10=%s | rank=%s | mean|SHAP|=%s",
                    cand, in_top10, cand_rank, f"{cand_shap:.6f}" if cand_shap is not None else "NOT_IN_K*")

    if len(candidates_in_top10) > 0:
        frozen_shortcut_set = candidates_in_top10
        fallback_used = False
        fallback_label = None
        logger.info("SHORTCUT SET (from candidate pool, top-10 hit): %s", frozen_shortcut_set)
    else:
        # Fallback: top-3 overall
        frozen_shortcut_set = [full_ranking[i]["feature"] for i in range(FALLBACK_K)]
        fallback_used = True
        fallback_label = "ATTRIBUTION-CONCENTRATION ABLATION"
        logger.warning(
            "FALLBACK: No candidate appeared in top-%d. Using top-%d overall: %s",
            TOP_K, FALLBACK_K, frozen_shortcut_set
        )

    logger.info("FROZEN SHORTCUT SET: %s", frozen_shortcut_set)

    # --- Write immutable shortcut_list_frozen.json ---
    freeze_payload = {
        "creation_timestamp_utc":       run_ts.isoformat(),
        "sprint":                        3,
        "step":                          "s09_treeshap_shortcut_freeze",
        "ZERO_DAY_BLINDING_ASSERTION":   (
            "This file was created before any zero-day evaluation. "
            "Protected Bot, UNSEEN_XSS, UNSEEN_INFILTRATION files were "
            "NEVER opened or accessed during or before this script."
        ),
        "rf_seed":                       RF_SEED,
        "rf_artifact_sha256":            rf_artifact_sha,
        "shap_sample_seed":              SHAP_SEED,
        "shap_n_sample_requested":       SHAP_N_SAMPLE,
        "shap_n_sample_actual":          actual_n_sample,
        "shap_sample_n_benign":          int((y_shap_sample == 0).sum()),
        "shap_sample_n_attack":          int((y_shap_sample == 1).sum()),
        "shap_sample_source":            "TRAIN only",
        "shap_method":                   "TreeExplainer(feature_perturbation=tree_path_dependent)",
        "shap_version":                  shap.__version__,
        "shap_compute_time_seconds":     float(elapsed),
        "k_star":                        k_star,
        "selected_features_sha256":      sel_sha,
        "candidate_pool":                CANDIDATE_POOL,
        "top_k_checked":                 TOP_K,
        "candidates_in_top10":           candidates_in_top10,
        "fallback_used":                 fallback_used,
        "fallback_label":                fallback_label,
        "frozen_shortcut_set":           frozen_shortcut_set,
        "frozen_shortcut_count":         len(frozen_shortcut_set),
        "rule_applied": (
            f"Candidate pool ∩ Top-{TOP_K} by mean|SHAP|" if not fallback_used
            else f"Fallback: Top-{FALLBACK_K} overall (ATTRIBUTION-CONCENTRATION ABLATION)"
        ),
        "full_shap_ranking":             full_ranking,
        "candidate_pool_shap_details": [
            {
                "feature":       cand,
                "in_selected_k_star": cand in selected_features,
                "rank":          next((r["rank"] for r in full_ranking if r["feature"] == cand), None),
                "mean_abs_shap": next((r["mean_abs_shap"] for r in full_ranking if r["feature"] == cand), None),
                "in_top10":      cand in top_10_features,
            }
            for cand in CANDIDATE_POOL
        ],
    }

    freeze_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    freeze_bytes = json.dumps(freeze_payload, indent=2).encode("utf-8")
    with open(freeze_path, "wb") as f:
        f.write(freeze_bytes)

    freeze_sha256 = sha256_bytes(freeze_bytes)
    logger.info("shortcut_list_frozen.json saved: %s", freeze_path)
    logger.info("SHORTCUT FREEZE SHA-256: %s", freeze_sha256)

    # Verification read-back
    readback_sha = sha256_file(freeze_path)
    assert readback_sha == freeze_sha256, "SHA-256 verification FAILED!"
    logger.info("SHA-256 read-back verification: PASS")

    # Also save a copy in shortcut_freeze/ dir
    freeze_copy_path = OUT_DIR / "shortcut_list_frozen.json"
    with open(freeze_copy_path, "wb") as f:
        f.write(freeze_bytes)

    # Save SHA record
    sha_record = {
        "shortcut_list_frozen_path":   str(freeze_path.relative_to(ROOT)),
        "shortcut_list_frozen_sha256": freeze_sha256,
        "frozen_shortcut_set":         frozen_shortcut_set,
        "frozen_at_utc":               run_ts.isoformat(),
        "status":                      "IMMUTABLE — DO NOT MODIFY OR REGENERATE AFTER ZERO-DAY EVALUATION",
    }
    sha_record_path = OUT_DIR / "shortcut_freeze_sha256_record.json"
    with open(sha_record_path, "w") as f:
        json.dump(sha_record, f, indent=2)

    # --- Summary ---
    logger.info("=" * 70)
    logger.info("STEP 5 SUMMARY")
    logger.info("  RF seed:               %d", RF_SEED)
    logger.info("  SHAP samples:          %d (from TRAIN only)", actual_n_sample)
    logger.info("  Fallback used:         %s", fallback_used)
    logger.info("  Frozen shortcut set:   %s", frozen_shortcut_set)
    logger.info("  Freeze SHA-256:        %s", freeze_sha256)
    logger.info("  Read-back verified:    PASS")
    logger.info("  Zero-day accessed:     NEVER")
    logger.info("STEP 5: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 5 COMPLETE] Frozen shortcut set: {frozen_shortcut_set}")
    print(f"SHA-256: {freeze_sha256}")
    print(f"File: {freeze_path}")

    return {
        "frozen_shortcut_set": frozen_shortcut_set,
        "freeze_sha256":       freeze_sha256,
        "fallback_used":       fallback_used,
    }


if __name__ == "__main__":
    main()
