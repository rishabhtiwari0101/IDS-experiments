"""
cicids2017/src/s06_mutual_information.py
-----------------------------------------
Sprint 3 — Step 2: Mutual Information Feature Selection

Protocol:
  - Estimator: mutual_info_classif(n_neighbors=3, random_state=42)
  - Subsample: ≤100,000 TRAIN rows (stratified, seed=42)
  - Grid: K ∈ {10, 20, 30, 40, 50, 60, ALL}
  - Inner CV: 5-fold StratifiedKFold(shuffle=True, random_state=42)
  - Plateau rule: Δ < 0.005 triggers selection of smaller K
  - Tie-break: smallest K
  - Target: binary label (0=benign, 1=attack)

LEAKAGE RULE: MI computed strictly on TRAIN rows (or inner folds thereof).
DEV_TEST, CALIBRATION, EVAL_CONTROL, protected/unseen data NEVER accessed here.

Output: results/cicids2017_revision_v1/feature_selection/
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s06_mi_selection.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR       = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
META_COLS        = {"Label", "shard_source", "label_clean", "attack_family", "row_uid"}

MI_N_NEIGHBORS   = 3
MI_SEED          = 42
SUBSAMPLE_MAX    = 100_000
SUBSAMPLE_SEED   = 42
PLATEAU_DELTA    = 0.005

CV_N_SPLITS      = 5
CV_SEED          = 42

# LR evaluator for K selection (NOT a research model)
LR_SOLVER        = "liblinear"
LR_C             = 1.0
LR_MAX_ITER      = 1000
LR_CLASS_WEIGHT  = "balanced"
LR_SEED          = 42


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Load frozen feature schema
# ---------------------------------------------------------------------------

def load_feature_schema() -> tuple[list[str], int]:
    schema_path = PREPROC_DIR / "feature_schema.json"
    with open(schema_path) as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]
    logger.info("Loaded frozen feature schema: D=%d from %s", D, schema_path.name)
    return feature_list, D


# ---------------------------------------------------------------------------
# Subsampling
# ---------------------------------------------------------------------------

def subsample_train(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_total = len(y)
    if n_total <= SUBSAMPLE_MAX:
        logger.info("No subsampling needed (n=%d ≤ %d)", n_total, SUBSAMPLE_MAX)
        return X, y

    rng = np.random.RandomState(SUBSAMPLE_SEED)
    classes, counts = np.unique(y, return_counts=True)
    fractions = counts / n_total
    indices = []
    for cls, frac in zip(classes, fractions):
        cls_idx = np.where(y == cls)[0]
        n_pick = max(1, int(round(SUBSAMPLE_MAX * frac)))
        n_pick = min(n_pick, len(cls_idx))
        picked = rng.choice(cls_idx, size=n_pick, replace=False)
        indices.extend(picked.tolist())

    # Trim to exactly SUBSAMPLE_MAX
    rng.shuffle(indices)
    indices = indices[:SUBSAMPLE_MAX]

    logger.info("Subsampled %d → %d rows (seed=%d, stratified)", n_total, len(indices), SUBSAMPLE_SEED)
    return X[indices], y[indices]


# ---------------------------------------------------------------------------
# MI computation
# ---------------------------------------------------------------------------

def compute_mi(X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> np.ndarray:
    """Compute MI scores — all features treated as continuous (no OHE in CIC)."""
    discrete_features = False  # All 70 CIC features are continuous
    t0 = time.perf_counter()
    scores = mutual_info_classif(
        X, y,
        discrete_features=discrete_features,
        n_neighbors=MI_N_NEIGHBORS,
        random_state=MI_SEED,
    )
    elapsed = time.perf_counter() - t0
    logger.info("MI computed: %d features | %.2fs", len(scores), elapsed)
    return scores


# ---------------------------------------------------------------------------
# Inner CV K evaluation
# ---------------------------------------------------------------------------

def evaluate_k_inner_cv(X_train: np.ndarray, y_train: np.ndarray,
                         feature_names: list[str], candidate_k: list[int]) -> pd.DataFrame:
    """
    5-fold StratifiedKFold inner CV to evaluate each K.
    MI and scaling are fit strictly on each inner_train fold.
    """
    logger.info("Starting inner CV | n_splits=%d | candidate_k=%s", CV_N_SPLITS, candidate_k)

    skf = StratifiedKFold(n_splits=CV_N_SPLITS, shuffle=True, random_state=CV_SEED)
    records = []

    for fold_idx, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
        fold_num = fold_idx + 1
        X_tr, y_tr = X_train[tr_idx], y_train[tr_idx]
        X_val, y_val = X_train[val_idx], y_train[val_idx]

        logger.info("  Fold %d/%d | inner_train=%d | inner_val=%d",
                    fold_num, CV_N_SPLITS, len(tr_idx), len(val_idx))

        # Compute MI ONCE per fold on inner_train only
        mi_scores_fold = mutual_info_classif(
            X_tr, y_tr,
            discrete_features=False,
            n_neighbors=MI_N_NEIGHBORS,
            random_state=MI_SEED,
        )
        sorted_idx = np.argsort(mi_scores_fold)[::-1]  # descending MI

        # Evaluate each K using the pre-sorted ranking
        for k in candidate_k:
            top_k_idx = sorted_idx[:k]
            X_tr_k  = X_tr[:, top_k_idx]
            X_val_k = X_val[:, top_k_idx]

            # Fit scaler on inner_train ONLY
            scaler = StandardScaler()
            X_tr_k_sc  = scaler.fit_transform(X_tr_k)
            X_val_k_sc = scaler.transform(X_val_k)

            # Fit LR evaluator on inner_train ONLY
            lr = LogisticRegression(
                solver=LR_SOLVER, C=LR_C, max_iter=LR_MAX_ITER,
                class_weight=LR_CLASS_WEIGHT, random_state=LR_SEED,
            )
            lr.fit(X_tr_k_sc, y_tr)
            y_pred = lr.predict(X_val_k_sc)
            macro_f1 = float(f1_score(y_val, y_pred, average="macro", zero_division=0))

            logger.info("    K=%d | fold=%d | macro_f1=%.6f", k, fold_num, macro_f1)
            records.append({"k": k, "fold": fold_num, "macro_f1": macro_f1})

    df = pd.DataFrame(records)
    summary = (
        df.groupby("k")["macro_f1"]
        .agg(mean_macro_f1="mean", std_macro_f1="std")
        .reset_index()
        .sort_values("k")
        .reset_index(drop=True)
    )
    logger.info("Inner CV summary:\n%s", summary.to_string(index=False))
    return summary


# ---------------------------------------------------------------------------
# Plateau rule & K* selection
# ---------------------------------------------------------------------------

def select_k_star(summary_df: pd.DataFrame, candidate_k_sorted: list[int]) -> tuple[int, str]:
    """
    Apply plateau rule: select the smallest K where adding more features
    yields Δ < 0.005 improvement.

    If no plateau is found (F1 still rising at maximum K), select ALL.
    """
    means = summary_df.set_index("k")["mean_macro_f1"].to_dict()
    sorted_k = sorted(candidate_k_sorted)

    logger.info("Applying plateau rule (Δ < %.4f):", PLATEAU_DELTA)
    k_star = sorted_k[-1]  # default = largest K (ALL)
    rule_applied = "NO_PLATEAU_DETECTED_USE_ALL"

    for i in range(1, len(sorted_k)):
        k_prev = sorted_k[i - 1]
        k_curr = sorted_k[i]
        delta = means[k_curr] - means[k_prev]
        logger.info("  K=%d → K=%d : Δ = %.6f (%s)",
                    k_prev, k_curr, delta,
                    "PLATEAU" if delta < PLATEAU_DELTA else "continue")
        if delta < PLATEAU_DELTA:
            k_star = k_prev
            rule_applied = f"PLATEAU_AT_K={k_prev}_DELTA={delta:.6f}_vs_K={k_curr}"
            break

    logger.info("K* SELECTED: %d | Rule: %s", k_star, rule_applied)
    return k_star, rule_applied


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3 — STEP 2: MUTUAL INFORMATION FEATURE SELECTION")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)

    # Load frozen feature schema
    feature_list, D = load_feature_schema()

    # Build candidate_k grid: {10, 20, 30, 40, 50, 60, ALL=D}
    candidate_k_raw = [10, 20, 30, 40, 50, 60, D]
    candidate_k = sorted(list(set(candidate_k_raw)))  # remove duplicates
    logger.info("MI K candidate grid: %s", candidate_k)

    # Load TRAIN — MI uses TRAIN only
    train_path = SPLITS_DIR / "train.csv"
    logger.info("Loading TRAIN: %s", train_path)
    train_df = pd.read_csv(train_path)

    # Build X, y
    X_full = train_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in train_df.columns:
        y_full = (train_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_full = (train_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    n_benign = int((y_full == 0).sum())
    n_attack = int((y_full == 1).sum())
    logger.info("TRAIN: benign=%d  attack=%d  total=%d", n_benign, n_attack, len(y_full))

    # Stratified subsample ≤100k for MI
    X_sub, y_sub = subsample_train(X_full, y_full)
    logger.info("Subsample size: %d (max=%d)", len(y_sub), SUBSAMPLE_MAX)

    # --- Inner CV for K selection ---
    cv_summary = evaluate_k_inner_cv(X_sub, y_sub, feature_list, candidate_k)

    # Save plateau table
    plateau_path = OUT_DIR / "mi_plateau_table.csv"
    cv_summary.to_csv(plateau_path, index=False)
    logger.info("Plateau table saved: %s", plateau_path.name)

    # --- Select K* via plateau rule ---
    k_star, rule_applied = select_k_star(cv_summary, candidate_k)

    # --- Final MI computation on full subsample ---
    logger.info("Computing final MI scores on subsample (n=%d)...", len(X_sub))
    mi_scores_final = compute_mi(X_sub, y_sub, feature_list)

    # Build ranking DataFrame
    ranking_df = pd.DataFrame({
        "rank":       np.argsort(mi_scores_final)[::-1].argsort() + 1,
        "feature":    feature_list,
        "mi_score":   mi_scores_final,
    }).sort_values("rank").reset_index(drop=True)

    # Mark selected features (top K* by MI score)
    top_k_idx_global = np.argsort(mi_scores_final)[::-1][:k_star]
    selected_set = {feature_list[i] for i in top_k_idx_global}
    ranking_df["selected"] = ranking_df["feature"].isin(selected_set)

    # Ordered selected features (by MI score descending)
    selected_features_ordered = [
        feature_list[i] for i in np.argsort(mi_scores_final)[::-1][:k_star]
    ]

    logger.info("Selected K*=%d features (top MI):", k_star)
    for i, feat in enumerate(selected_features_ordered, 1):
        idx = feature_list.index(feat)
        logger.info("  %2d. %-45s MI=%.6f", i, feat, mi_scores_final[idx])

    # Save mi_scores.csv
    scores_path = OUT_DIR / "mi_scores.csv"
    ranking_df.to_csv(scores_path, index=False)
    logger.info("MI scores saved: %s", scores_path.name)

    # --- Candidate pool MI check (for shortcut freeze transparency) ---
    shortcut_candidates = [
        "Destination Port", "Init_Win_bytes_forward",
        "Init_Win_bytes_backward", "Flow Duration",
    ]
    candidate_mi = {}
    for cand in shortcut_candidates:
        if cand in feature_list:
            idx = feature_list.index(cand)
            candidate_mi[cand] = {
                "mi_score": float(mi_scores_final[idx]),
                "rank":     int(ranking_df.loc[ranking_df["feature"] == cand, "rank"].values[0]),
            }
    logger.info("Shortcut candidate MI scores: %s", candidate_mi)

    # --- selected_features.json ---
    selected_json = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 3,
        "step": "s06_mutual_information",
        "estimator": "mutual_info_classif",
        "n_neighbors": MI_N_NEIGHBORS,
        "mi_seed": MI_SEED,
        "subsample_max_rows": SUBSAMPLE_MAX,
        "subsample_seed": SUBSAMPLE_SEED,
        "subsample_actual_rows": int(len(y_sub)),
        "cv_n_splits": CV_N_SPLITS,
        "cv_seed": CV_SEED,
        "candidate_k_grid": candidate_k,
        "plateau_delta_threshold": PLATEAU_DELTA,
        "k_star": k_star,
        "rule_applied": rule_applied,
        "selected_feature_count": len(selected_features_ordered),
        "selected_features": selected_features_ordered,
        "feature_ordering": "by MI score descending (rank 1 = highest MI)",
        "all_features_D": D,
        "k_selection_summary": cv_summary.to_dict(orient="records"),
        "candidate_pool_mi": candidate_mi,
        "train_file": str(train_path.relative_to(ROOT)),
        "train_sha256": sha256_file(train_path),
        "train_rows": len(train_df),
    }

    sel_path = OUT_DIR / "selected_features.json"
    sel_bytes = json.dumps(selected_json, indent=2).encode("utf-8")
    with open(sel_path, "wb") as f:
        f.write(sel_bytes)
    selected_sha256 = sha256_bytes(sel_bytes)
    logger.info("selected_features.json saved: SHA-256=%s", selected_sha256)

    # --- selection_metadata.json ---
    sel_meta = {
        "selected_features_sha256": selected_sha256,
        "selected_features_path": str(sel_path.relative_to(ROOT)),
        "plateau_table_path": str(plateau_path.relative_to(ROOT)),
        "mi_scores_path": str(scores_path.relative_to(ROOT)),
        "D_original": D,
        "K_star": k_star,
        "reduction_achieved": k_star < D,
    }
    meta_path = OUT_DIR / "selection_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(sel_meta, f, indent=2)

    # --- Summary ---
    logger.info("=" * 70)
    logger.info("STEP 2 SUMMARY")
    logger.info("  D_original:    %d", D)
    logger.info("  K*:            %d", k_star)
    logger.info("  Rule:          %s", rule_applied)
    logger.info("  Selected SHA:  %s", selected_sha256)
    logger.info("STEP 2: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 2 COMPLETE] K*={k_star}  selected_SHA={selected_sha256[:16]}...")
    print(f"Plateau table: {plateau_path}")
    print(f"Selected features: {sel_path}")

    return {
        "k_star": k_star,
        "selected_features": selected_features_ordered,
        "selected_sha256": selected_sha256,
        "mi_scores_final": mi_scores_final,
        "ranking_df": ranking_df,
        "cv_summary": cv_summary,
    }


if __name__ == "__main__":
    main()
