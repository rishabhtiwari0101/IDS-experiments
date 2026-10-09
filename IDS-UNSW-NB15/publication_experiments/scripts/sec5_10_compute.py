"""
Full Section 5/6/7/8/9 computation for Revision 2 audit report.
"""
import json, hashlib, joblib, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import binomtest

REPO = Path(".")
EXP  = REPO / "results/publication_experiments/EXP_NO_TTL_V1"

results = {}

# ── SECTION 5: Primary canonical vs No-TTL comparison (Seed-42) ───────────
# Load canonical backdoor predictions (Seed-42)
canon_bk = pd.read_csv(REPO / "results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv")
nottl_bk = pd.read_csv(EXP / "predictions/seed_42/predictions_protected_backdoor.csv")

# Row alignment: merge on id
# canon_bk uses source_row_uid like "UNSW_NB15_testing-set.csv:246"
canon_bk["id"] = canon_bk["source_row_uid"].apply(lambda s: int(s.split(":")[-1]))
merged_bk = canon_bk.merge(nottl_bk, on="id", suffixes=("_c", "_n"))
print(f"Merged backdoor rows: {len(merged_bk)} (should be 583)")
assert len(merged_bk) == 583, "ROW COUNT MISMATCH!"

y_bk = merged_bk["label"].values  # 'label' from canon (no suffix conflict)
canon_stack_bk = merged_bk["stacking_prediction"].values
nottl_stack_bk  = merged_bk["stacking_pred"].values

A = int(((canon_stack_bk == 1) & (nottl_stack_bk == 1)).sum())  # both detect
B = int(((canon_stack_bk == 1) & (nottl_stack_bk == 0)).sum())  # canon OK / nottl miss
C = int(((canon_stack_bk == 0) & (nottl_stack_bk == 1)).sum())  # canon miss / nottl OK
D = int(((canon_stack_bk == 0) & (nottl_stack_bk == 0)).sum())  # both miss

print(f"\n=== BACKDOOR CONTINGENCY TABLE (Stacking, Seed-42) ===")
print(f"A (both detect): {A}")
print(f"B (canon OK / nottl miss): {B}")
print(f"C (canon miss / nottl OK): {C}")
print(f"D (both miss): {D}")

# McNemar exact test (binomial on B and B+C)
discordant = B + C
if discordant > 0:
    p_val = float(binomtest(B, discordant, 0.5, alternative="two-sided").pvalue)
else:
    p_val = 1.0
print(f"Discordant pairs: {discordant}")
print(f"p-value (exact binomial): {p_val:.6f}")
print(f"Significant at alpha=0.05: {p_val < 0.05}")
results["backdoor_mcnemar_seed42"] = {"A": A, "B": B, "C": C, "D": D, "discordant": discordant, "p_value": p_val}

# ── Multi-seed paired McNemar (from comparison file) ──────────────────────
comp = json.load(open(EXP / "comparison/canonical_vs_no_ttl_comparison.json"))

# ── DEV TEST comparison ────────────────────────────────────────────────────
from sklearn.metrics import f1_score, precision_score, recall_score

# Load canonical dev-test predictions
stack_dev = pd.read_csv(REPO / "results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/predictions_dev_test.csv")
base_dev  = pd.read_csv(REPO / "results/final_reproducibility/EXP_FINAL_REPRO_V1/base_models/predictions_dev_test.csv")

y_dev = stack_dev["true_label"].values
n_dev = len(y_dev)
n_benign = int((y_dev == 0).sum())
n_attack = int((y_dev == 1).sum())
print(f"\nDEV TEST: {n_dev} rows = {n_benign} benign + {n_attack} attack")

# Canonical per-model for seed 42
canon_stk_pred = stack_dev["stack_pred_seed_42"].values
canon_dt_pred  = base_dev["dt_pred"].values
canon_rf_pred  = base_dev["rf_pred"].values
canon_svm_pred = base_dev["svm_pred"].values
canon_nn_pred  = base_dev["nn_pred"].values

def eval_model(y_true, y_pred, label):
    f1 = f1_score(y_true, y_pred, average="macro")
    prec = precision_score(y_true, y_pred, average="macro")
    rec  = recall_score(y_true, y_pred, average="macro")
    FP = int(((y_true==0)&(y_pred==1)).sum())
    TP = int(((y_true==1)&(y_pred==1)).sum())
    FN = int(((y_true==1)&(y_pred==0)).sum())
    TN = int(((y_true==0)&(y_pred==0)).sum())
    fpr = FP / n_benign
    return {"model": label, "macro_f1": f1, "macro_prec": prec, "macro_rec": rec,
            "TP": TP, "TN": TN, "FP": FP, "FN": FN, "FPR": fpr, "n": n_dev}

print("\n=== CANONICAL DEV TEST (Seed-42) ===")
for name, pred in [("Stacking", canon_stk_pred), ("RF", canon_rf_pred),
                   ("DT", canon_dt_pred), ("SVM", canon_svm_pred), ("NN", canon_nn_pred)]:
    r = eval_model(y_dev, pred, name)
    print(f"  {name}: Macro-F1={r['macro_f1']:.4f}, FPR={r['FPR']:.4f}, FP={r['FP']}, FN={r['FN']}")

# Load No-TTL dev-test predictions
print("\n=== NO-TTL DEV TEST (Seed-42) ===")
nottl_dev = {}
for seed in [42, 123, 2024]:
    df = pd.read_csv(EXP / f"predictions/seed_{seed}/predictions_dev_test.csv")
    nottl_dev[seed] = df

nottl_d42 = nottl_dev[42]
y_nottl = nottl_d42["true_label"].values
for name, col in [("Stacking", "stacking_pred"), ("RF", "rf_pred"),
                  ("DT", "dt_pred"), ("SVM", "svm_pred"), ("NN", "nn_pred")]:
    pred = nottl_d42[col].values
    r = eval_model(y_nottl, pred, name)
    print(f"  {name}: Macro-F1={r['macro_f1']:.4f}, FPR={r['FPR']:.4f}, FP={r['FP']}, FN={r['FN']}")

# ── Section 10: Threshold arithmetic ──────────────────────────────────────
print("\n=== SECTION 10: THRESHOLD ARITHMETIC ===")

# Primary: Stacking Seed-42
canon_stk_f1 = f1_score(y_dev, canon_stk_pred, average="macro")
nottl_stk_f1 = f1_score(y_nottl, nottl_d42["stacking_pred"].values, average="macro")
delta_f1 = canon_stk_f1 - nottl_stk_f1

canon_bk_rate = 582/583
nottl_bk_rate = 580/583
delta_bk_pp = (canon_bk_rate - nottl_bk_rate) * 100

print(f"  Stacking Macro-F1: canon={canon_stk_f1:.4f}, nottl={nottl_stk_f1:.4f}, delta={delta_f1*100:.4f} pp")
print(f"  Stacking Backdoor rate: canon={canon_bk_rate:.4%}, nottl={nottl_bk_rate:.4%}, delta={delta_bk_pp:.4f} pp")
print(f"  |delta_Macro-F1| = {abs(delta_f1*100):.4f} pp")
print(f"  |delta_detection rate| = {abs(delta_bk_pp):.4f} pp")
print()

thresholds = [
    ("|ΔMacro-F1| < 1.0 pp AND |Δ detection rate| < 1.0 pp", "Similar performance"),
    ("1.0-5.0 pp drop in Macro-F1 OR 1.0-5.0 pp drop in detection rate", "Moderate degradation"),
    ("> 5.0 pp drop in Macro-F1 OR > 5.0 pp drop in detection rate", "Dramatic degradation"),
]
abs_df1 = abs(delta_f1 * 100)
abs_dbk = abs(delta_bk_pp)

if abs_df1 < 1.0 and abs_dbk < 1.0:
    bucket = "Similar performance"
elif (1.0 <= abs_df1 <= 5.0) or (1.0 <= abs_dbk <= 5.0):
    bucket = "Moderate degradation"
elif abs_df1 > 5.0 or abs_dbk > 5.0:
    bucket = "Dramatic degradation"
else:
    bucket = "Indeterminate"

print(f"  VERDICT: {bucket}")
print(f"  Arithmetic: |ΔF1|={abs_df1:.4f} pp (threshold <1.0), |ΔBK|={abs_dbk:.4f} pp (threshold <1.0)")

# Save full computation result
results["section10_threshold"] = {
    "delta_macro_f1_pp": delta_f1 * 100,
    "abs_delta_macro_f1_pp": abs_df1,
    "delta_backdoor_rate_pp": delta_bk_pp,
    "abs_delta_backdoor_rate_pp": abs_dbk,
    "verdict": bucket
}
print("\nAll computations complete.")
