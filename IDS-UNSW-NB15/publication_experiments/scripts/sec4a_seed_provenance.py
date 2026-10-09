"""
Section 4a: Seed Provenance Gate
Reproduce the canonical 582/583 stacking score using Seed-42 vs Seed-123 meta-learner.
"""
import hashlib
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

REPO = Path(".")
ZD_PRED_FILE = REPO / "results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv"
CANON_BK_SPLIT = REPO / "data/splits/protected_unseen_attack.csv"

# 1. Load the zero-day prediction file (canonical result)
zd_df = pd.read_csv(ZD_PRED_FILE)
print("ZD stacking predictions from file:")
print(f"  Total: {len(zd_df)}")
print(f"  Detected: {int(zd_df['stacking_prediction'].sum())}")
print(f"  stacking_score sample (first 3): {zd_df['stacking_score'].head(3).tolist()}")

# 2. The canonical base-model meta-features for protected backdoor
# Find what predictions the canonical supervised models made on backdoor
# Available from EXP_FINAL_REPRO_V1 run but only for dev-test. For backdoor:
# The zero-day file itself has per-model columns — use them to reconstruct meta-input
# dt_prediction/score, rf_prediction/score, svm_prediction/score, nn_prediction/score
# -> that IS the [dt_prob, rf_prob, svm_score, nn_prob] vector

# Build meta-feature matrix from the zero_day prediction columns
X_meta = zd_df[["dt_score", "rf_score", "svm_score", "nn_score"]].values
print(f"\nMeta-feature matrix shape: {X_meta.shape}")
print(f"Meta-feature sample row 0: {X_meta[0]}")

# 3. Load seed-42 canonical meta-learner and predict
meta42  = joblib.load(REPO / "results/checkpoints/EXP_OOF_STACK_V1/seed_42/meta_learner.joblib")
meta123 = joblib.load(REPO / "results/checkpoints/EXP_OOF_STACK_V1/seed_123/meta_learner.joblib")
meta2024 = joblib.load(REPO / "results/checkpoints/EXP_OOF_STACK_V1/seed_2024/meta_learner.joblib")

pred42   = meta42.predict(X_meta)
pred123  = meta123.predict(X_meta)
pred2024 = meta2024.predict(X_meta)

prob42   = meta42.predict_proba(X_meta)[:, 1]
prob123  = meta123.predict_proba(X_meta)[:, 1]
prob2024 = meta2024.predict_proba(X_meta)[:, 1]

print(f"\nCanonical meta-learner reproduced predictions on ZD backdoor:")
print(f"  Seed 42  : {int(pred42.sum())}/583 detected")
print(f"  Seed 123 : {int(pred123.sum())}/583 detected")
print(f"  Seed 2024: {int(pred2024.sum())}/583 detected")

# Compare score distributions to the file's stacking_score column
from scipy.stats import spearmanr

r42,   _ = spearmanr(zd_df["stacking_score"].values, prob42)
r123,  _ = spearmanr(zd_df["stacking_score"].values, prob123)
r2024, _ = spearmanr(zd_df["stacking_score"].values, prob2024)

corr42   = np.corrcoef(zd_df["stacking_score"].values, prob42)[0, 1]
corr123  = np.corrcoef(zd_df["stacking_score"].values, prob123)[0, 1]
corr2024 = np.corrcoef(zd_df["stacking_score"].values, prob2024)[0, 1]

print(f"\nPearson correlation of file stacking_score vs meta-learner proba:")
print(f"  Seed 42  : r={corr42:.6f}")
print(f"  Seed 123 : r={corr123:.6f}")
print(f"  Seed 2024: r={corr2024:.6f}")

print(f"\nSpearman rho of file stacking_score vs meta-learner proba:")
print(f"  Seed 42  : rho={r42:.6f}")
print(f"  Seed 123 : rho={r123:.6f}")
print(f"  Seed 2024: rho={r2024:.6f}")

# 4. Check column names — does the meta-learner expect dt_attack_probability or dt_score?
print("\nMeta-learner feature_names_in_:", getattr(meta42, "feature_names_in_", "NOT STORED"))

# 5. Verify config file confirms explainability_seed = 42 (as a corroborating signal)
cfg = open(REPO / "results/zero_day/EXP_ZERODAY_V1/config.yaml").read()
print("\nZD Config explainability_seed line:")
for line in cfg.split("\n"):
    if "seed" in line.lower() or "training" in line.lower():
        print(f"  {line}")

# 6. Conclusion
print("\n=== SECTION 4a DETERMINATION ===")
if abs(corr42 - 1.0) < 1e-6:
    print("CONFIRMED: Seed-42 stacking_score exactly matches file. Provenance = Seed-42.")
elif abs(corr123 - 1.0) < 1e-6:
    print("MISMATCH: Seed-123 stacking_score matches, not Seed-42!")
elif abs(corr2024 - 1.0) < 1e-6:
    print("MISMATCH: Seed-2024 stacking_score matches, not Seed-42!")
else:
    best = max([(corr42, 42), (corr123, 123), (corr2024, 2024)])
    print(f"Best correlation: Seed {best[1]} (r={best[0]:.6f}) — checking diff vs file:")
    # Check exact score match
    exact42   = np.allclose(zd_df["stacking_score"].values, prob42, atol=1e-5)
    exact123  = np.allclose(zd_df["stacking_score"].values, prob123, atol=1e-5)
    exact2024 = np.allclose(zd_df["stacking_score"].values, prob2024, atol=1e-5)
    print(f"  Exact match (tol=1e-5): Seed42={exact42}, Seed123={exact123}, Seed2024={exact2024}")
    max_diff42   = float(np.max(np.abs(zd_df["stacking_score"].values - prob42)))
    max_diff123  = float(np.max(np.abs(zd_df["stacking_score"].values - prob123)))
    max_diff2024 = float(np.max(np.abs(zd_df["stacking_score"].values - prob2024)))
    print(f"  Max abs diff: Seed42={max_diff42:.8f}, Seed123={max_diff123:.8f}, Seed2024={max_diff2024:.8f}")
