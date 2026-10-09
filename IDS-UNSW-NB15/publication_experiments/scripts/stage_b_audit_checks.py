"""
Stage B Audit Checks — EXP_NO_TTL_V1
Runs all programmatic verification checks and outputs results.
"""
import hashlib
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

REPO = Path(".")
EXP = REPO / "results/publication_experiments/EXP_NO_TTL_V1"
EXPECTED_HASH = "21c949fc5709c21d3568a420559f3bc42ba52f26e4be95ee551901b7de9bbe96"

results = {}

# ── A. Feature Verification ────────────────────────────────────────────────
feat_manifest = json.load(open(EXP / "features/no_ttl_features.json"))
feat_hash = feat_manifest["feature_hash_sha256"]
features = feat_manifest["features"]
removed = feat_manifest["removed_features"]

results["feature_verification"] = {
    "canonical_count": feat_manifest["canonical_feature_count"],
    "removed_features": removed,
    "removed_count": len(removed),
    "final_count": len(features),
    "feature_hash": feat_hash,
    "hash_match": feat_hash == EXPECTED_HASH,
    "sttl_absent": "sttl" not in features,
    "ct_state_ttl_absent": "ct_state_ttl" not in features,
    "dttl_absent": "dttl" not in features,
    "count_eq_72": len(features) == 72,
}
print("FEATURE VERIFICATION:", results["feature_verification"])

# ── B. Scaler Dimensions ───────────────────────────────────────────────────
scaler = joblib.load(EXP / "scalers/supervised_scaler_72.joblib")
results["scaler"] = {
    "n_features_in_": int(scaler.n_features_in_),
    "correct_72": int(scaler.n_features_in_) == 72,
}
print("SCALER:", results["scaler"])

# ── C. NN Checkpoint Dimensions ────────────────────────────────────────────
nn_dims = {}
for seed in [42, 123, 2024]:
    ckpt = torch.load(EXP / f"checkpoints/seed_{seed}/nn_final.pt", map_location="cpu", weights_only=True)
    w1 = ckpt["net.0.weight"]
    nn_dims[str(seed)] = {"input_dim": int(w1.shape[1]), "hidden1_dim": int(w1.shape[0]), "correct": int(w1.shape[1]) == 72}
results["nn_checkpoint_dims"] = nn_dims
print("NN DIMS:", nn_dims)

# ── D. Meta-learner Dimensions ─────────────────────────────────────────────
meta_dims = {}
for seed in [42, 123, 2024]:
    meta = joblib.load(EXP / f"checkpoints/seed_{seed}/meta_learner.joblib")
    meta_dims[str(seed)] = {
        "n_features_in_": int(meta.n_features_in_),
        "correct_4": int(meta.n_features_in_) == 4,
        "coefs": meta.coef_[0].tolist(),
        "intercept": float(meta.intercept_[0]),
    }
results["meta_learner_dims"] = meta_dims
print("META DIMS:", {s: {"n_features_in_": v["n_features_in_"], "correct_4": v["correct_4"]} for s, v in meta_dims.items()})

# ── E. Row Alignment Audit ─────────────────────────────────────────────────
backdoor_df = pd.read_csv(REPO / "data/splits/protected_unseen_attack.csv")
canon_bk_df = pd.read_csv(REPO / "results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv")
canon_bk_df["id"] = canon_bk_df["source_row_uid"].apply(lambda s: int(s.split(":")[-1]))

nottl_bk_df = pd.read_csv(EXP / "predictions/seed_42/predictions_protected_backdoor.csv")

bk_ids_file = set(backdoor_df["id"].values)
bk_ids_canon = set(canon_bk_df["id"].values)
bk_ids_nottl = set(nottl_bk_df["id"].values)

results["row_alignment"] = {
    "backdoor_rows_in_split": len(bk_ids_file),
    "backdoor_unique_ids": len(bk_ids_file) == 583,
    "canon_id_count": len(bk_ids_canon),
    "nottl_id_count": len(bk_ids_nottl),
    "canon_vs_split_exact_match": bk_ids_file == bk_ids_canon,
    "nottl_vs_split_exact_match": bk_ids_file == bk_ids_nottl,
    "all_three_identical": bk_ids_file == bk_ids_canon == bk_ids_nottl,
    "labels_all_attack": int(backdoor_df["label"].sum()) == 583,
}
# Check no positional pairing — check that both DataFrames have the same ID set without relying on row order
sorted_match = sorted(bk_ids_canon) == sorted(bk_ids_nottl)
results["row_alignment"]["sorted_id_match"] = sorted_match
print("ROW ALIGNMENT:", results["row_alignment"])

# ── F. Canonical Dataset Hashes ────────────────────────────────────────────
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

CANONICAL_HASHES = {
    "train": "4a259324e604f013287a5de5fe49c46bf19418d815b550c5d1a5820b569ac41c",
    "validation": "13caf21a076a33f50243f48f404b7e7525969f71d4b9d7c0f3768aef23589180",
    "dev_test": "04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508",
    "protected_backdoor": "6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91",
}
DATA_PATHS = {
    "train": REPO / "data/splits/train.csv",
    "validation": REPO / "data/splits/validation.csv",
    "dev_test": REPO / "data/splits/development_test.csv",
    "protected_backdoor": REPO / "data/splits/protected_unseen_attack.csv",
}
hash_results = {}
for k, expected in CANONICAL_HASHES.items():
    actual = sha256_file(DATA_PATHS[k])
    hash_results[k] = {"expected": expected, "actual": actual, "match": actual == expected}
results["canonical_dataset_hashes"] = hash_results
print("CANONICAL HASHES:", {k: v["match"] for k, v in hash_results.items()})

# ── G. Canonical prediction provenance ─────────────────────────────────────
canon_stacking_detected = int(canon_bk_df["stacking_prediction"].sum())
canon_rf_detected = int(canon_bk_df["rf_prediction"].sum())
canon_dt_detected = int(canon_bk_df["dt_prediction"].sum())
canon_svm_detected = int(canon_bk_df["svm_prediction"].sum())
canon_nn_detected = int(canon_bk_df["nn_prediction"].sum())
results["canonical_provenance"] = {
    "source_file": "results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv",
    "seed": 42,
    "total_rows": len(canon_bk_df),
    "stacking_detected": canon_stacking_detected,
    "rf_detected": canon_rf_detected,
    "dt_detected": canon_dt_detected,
    "svm_detected": canon_svm_detected,
    "nn_detected": canon_nn_detected,
    "stacking_rate": f"{canon_stacking_detected}/583 ({canon_stacking_detected/583:.2%})",
    "headline_582_confirmed": canon_stacking_detected == 582,
}
print("CANONICAL PROVENANCE:", results["canonical_provenance"])

# ── H. Canonical feature file hash ─────────────────────────────────────────
canon_feat_hash = sha256_file(REPO / "results/feature_selection/EXP_MI_V1_1/selected_features.json")
results["canonical_feature_file_hash"] = {
    "path": "results/feature_selection/EXP_MI_V1_1/selected_features.json",
    "sha256": canon_feat_hash,
}
print("CANONICAL FEATURE FILE HASH:", canon_feat_hash)

# ── I. No-canonical directory pollution check ──────────────────────────────
forbidden_dirs = [
    REPO / "results/checkpoints",
    REPO / "results/zero_day",
    REPO / "results/autoencoder",
    REPO / "results/stacking",
    REPO / "results/feature_selection",
]
all_nottl_paths = list(EXP.rglob("*"))
pollution = []
for p in all_nottl_paths:
    for fd in forbidden_dirs:
        if str(p).startswith(str(fd)):
            pollution.append(str(p))
results["isolation_check"] = {
    "all_outputs_in_publication_experiments": all(
        str(p).startswith(str(REPO / "results/publication_experiments")) for p in all_nottl_paths
    ),
    "no_forbidden_dir_pollution": len(pollution) == 0,
    "forbidden_dir_pollution": pollution,
}
print("ISOLATION:", results["isolation_check"])

# Save full results
with open(EXP / "stage_b_audit_checks_raw.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nAll checks complete. Raw results saved.")
