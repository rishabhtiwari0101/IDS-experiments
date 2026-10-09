#!/usr/bin/env python3
"""
Stage D — Comprehensive 20-Point Static Validation Audit
UNSW-NB15 Publication Extension Research

Audits the Stage-D analysis master script, configs, preregistration, and implementation plan
against all 20 required verification criteria defined in Section 11 of the Master Prompt:
 1. RF A/B/C/D is computed from raw aligned predictions.
 2. Family-2 A/B/C/D is computed from raw aligned predictions.
 3. Neither RF nor Family 2 has predeclared B/C values in executable logic.
 4. RF remains present in the five-row Family-1 multiple-testing inventory.
 5. Holm uses exactly five Family-1 p-values.
 6. Family 2 is excluded from Holm correction.
 7. Three-seed "consistency" is descriptive-only.
 8. Threshold trade-off is descriptive-only and limited to observed cells.
 9. Figure D5 does not imply continuous uniformly spaced thresholds.
10. Stage-B source resolution remains repository-verified.
11. Prediction semantics remain validated before paired analysis.
12. Canonical historical seed coverage remains restricted to actually evaluated data.
13. Materiality thresholds remain preregistered and unchanged.
14. Clopper-Pearson remains restricted to binomial proportions.
15. Small-N warnings remain present.
16. Stage-C frozen-language issues remain FLAG ONLY.
17. Final scientific decisions are dynamically computed.
18. Final status is dynamically computed.
19. No frozen artifact is modified.
20. No Stage-B or Stage-C artifact is modified.
"""

import re
import sys
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "publication_experiments" / "stage_d" / "scripts" / "run_stage_d_analysis.py"
CONFIG_PATH = REPO_ROOT / "publication_experiments" / "stage_d" / "configs" / "stage_d.yaml"
PREREG_PATH = REPO_ROOT / "publication_experiments" / "stage_d" / "materiality_preregistration.json"
PLAN_PATH = Path(r"C:\Users\Atul2\.gemini\antigravity-ide\brain\2fedcec1-8be2-445c-80ab-dab6785595cf\implementation_plan.md")

with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
    script_text = f.read()

with open(PLAN_PATH, "r", encoding="utf-8") as f:
    plan_text = f.read()

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config_text = f.read()

with open(PREREG_PATH, "r", encoding="utf-8") as f:
    prereg_text = f.read()

checks = {}

# 1. RF A/B/C/D is computed from raw aligned predictions
checks["1_rf_abcd_computed_from_aligned_preds"] = (
    '("RF", "rf_prediction", "rf_pred")' in script_text and
    "A = int(((c_corr) & (n_corr)).sum())" in script_text and
    "B = int(((c_corr) & (~n_corr)).sum())" in script_text and
    "C = int(((~c_corr) & (n_corr)).sum())" in script_text and
    "D = int(((~c_corr) & (~n_corr)).sum())" in script_text and
    "if A + B + C + D != 583:" in script_text
)

# 2. Family-2 A/B/C/D is computed from raw aligned predictions
checks["2_family2_abcd_computed_from_aligned_preds"] = (
    "merged_ae = pd.merge(df_canon, df_ae_new, left_on=\"id\", right_on=\"raw_id\")" in script_text and
    "c_ae_corr = (merged_ae[\"ae_flag\"] == 1)" in script_text and
    "n_ae_corr = (merged_ae[\"ae_prediction\"] == 1)" in script_text and
    "A_ae = int(((c_ae_corr) & (n_ae_corr)).sum())" in script_text and
    "B_ae = int(((c_ae_corr) & (~n_ae_corr)).sum())" in script_text and
    "C_ae = int(((~c_ae_corr) & (n_ae_corr)).sum())" in script_text and
    "D_ae = int(((~c_ae_corr) & (~n_ae_corr)).sum())" in script_text and
    "if A_ae + B_ae + C_ae + D_ae != 583:" in script_text
)

# 3. Neither RF nor Family 2 has predeclared B/C values in executable logic
checks["3_neither_rf_nor_family2_has_predeclared_bc"] = (
    not re.search(r"^\s*B\s*=\s*0\s*$", script_text, re.MULTILINE) and
    not re.search(r"^\s*C\s*=\s*0\s*$", script_text, re.MULTILINE) and
    not re.search(r"^\s*B_ae\s*=\s*0\s*$", script_text, re.MULTILINE) and
    not re.search(r"^\s*C_ae\s*=\s*0\s*$", script_text, re.MULTILINE) and
    "A = int(((c_corr) & (n_corr)).sum())" in script_text and
    "B = int(((c_corr) & (~n_corr)).sum())" in script_text and
    "C = int(((~c_corr) & (n_corr)).sum())" in script_text and
    "D = int(((~c_corr) & (~n_corr)).sum())" in script_text and
    "A_ae = int(((c_ae_corr) & (n_ae_corr)).sum())" in script_text and
    "B_ae = int(((c_ae_corr) & (~n_ae_corr)).sum())" in script_text and
    "C_ae = int(((~c_ae_corr) & (n_ae_corr)).sum())" in script_text and
    "D_ae = int(((~c_ae_corr) & (~n_ae_corr)).sum())" in script_text and
    "if discordant == 0:" in script_text and
    "if ae_discordant == 0:" in script_text
)

# 4. RF remains present in the five-row Family-1 multiple-testing inventory
checks["4_rf_present_in_five_row_family1_inventory"] = (
    'inventory.append({' in script_text and
    '"analysis_id": f"PAIRED_SUP_{res[\'model\']}"' in script_text and
    '"model": res["model"]' in script_text and
    '"A": res["A_both_correct"]' in script_text and
    '"B": res["B_canon_only"]' in script_text and
    '"C": res["C_nottl_only"]' in script_text and
    '"D": res["D_neither_correct"]' in script_text and
    '"discordant_pairs": res["discordant_pairs"]' in script_text and
    '"test_status": res["test_status"]' in script_text
)

# 5. Holm uses exactly five Family-1 p-values
checks["5_holm_uses_exactly_five_family1_pvalues"] = (
    "if len(raw_p_values) != 5:" in script_text and
    "holm_p = holm_bonferroni(raw_p_values)" in script_text
)

# 6. Family 2 is excluded from Holm correction
checks["6_family2_excluded_from_holm_correction"] = (
    '"analysis_id": "PAIRED_AE_CANON_VS_NEW"' in script_text and
    '"test_family": "Family 2 (Canonical AE vs New AE Backdoor)"' in script_text and
    '"correction_method": "None (unpooled' in script_text and
    '"adjusted_p": "N/A"' in script_text
)

# 7. Three-seed “consistency” is descriptive-only
checks["7_three_seed_is_descriptive_only"] = (
    '"three_seed_characterization"' in script_text and
    '"verdict": "DESCRIPTIVE ONLY"' in script_text and
    "No formal preregistered criterion for seed “consistency” was defined" in script_text and
    "THREE_SEED_CLAIM" in script_text and
    not re.search(r'"three_seed_consistency"\s*:\s*\{\s*"verdict":\s*"SUPPORTED"', script_text)
)

# 8. Threshold trade-off is descriptive-only and limited to observed cells
checks["8_threshold_tradeoff_is_descriptive_only"] = (
    '"threshold_tradeoff"' in script_text and
    '"verdict": "SUPPORTED DESCRIPTIVELY"' in script_text and
    "Several relaxed threshold operating points increased observed detections" in script_text and
    "THRESHOLD_TRADEOFF_CLAIM" in script_text
)

# 9. Figure D5 does not imply continuous uniformly spaced thresholds
checks["9_figure_d5_discrete_operating_points"] = (
    'rules_order = ["p95", "p99", "mean2sigma", "p999", "mean3sigma"]' in script_text and
    "x_cat = np.arange(len(rules_order))" in script_text and
    "ax.set_xticks(x_cat)" in script_text and
    "Figure D5: Observed Operating-Point Comparison Across Predefined Threshold Rules" in script_text
)

# 10. Stage-B source resolution remains repository-verified
checks["10_stage_b_source_resolution_verified"] = (
    "verify_and_resolve_sources" in script_text and
    'manifest_dir / "stage_b_source_resolution.json"' in script_text and
    "source_manifest/stage_b_source_resolution.json" in plan_text and
    'stage_b_dir = REPO_ROOT / "results" / "publication_experiments" / "EXP_NO_TTL_V1"' in script_text
)

# 11. Prediction semantics remain validated before paired analysis
checks["11_prediction_semantics_validated_before_paired"] = (
    "verify_prediction_artifact_semantics" in script_text and
    "semantics_audit = verify_prediction_artifact_semantics(sources, config)" in script_text and
    '"prediction_artifact_semantics.json"' in script_text and
    "unique_ids != gt_ids" in script_text
)

# 12. Canonical historical seed coverage remains restricted to actually evaluated data
checks["12_canonical_seed_coverage_restricted"] = (
    '"canonical_supervised_backdoor_seed_count": 1' in script_text and
    '"canonical_seed_coverage.json"' in script_text and
    "Seed 123 and Seed 2024 canonical Backdoor evaluations were never performed historically" in script_text
)

# 13. Materiality thresholds remain preregistered and unchanged
checks["13_materiality_thresholds_preregistered"] = (
    "macro_f1_absolute_delta: 0.01" in config_text and
    "backdoor_detection_count: 6" in config_text and
    '"count_threshold": 6' in prereg_text and
    '"absolute_delta_threshold": 0.01' in prereg_text and
    "PREREG_PATH" in script_text
)

# 14. Clopper-Pearson remains restricted to binomial proportions
checks["14_clopper_pearson_binomial_only"] = (
    "st.binomtest(k, n).proportion_ci" in script_text and
    "Applied strictly to binomial proportions" in script_text and
    "clopper_pearson_ci" in script_text
)

# 15. Small-N warnings remain present
checks["15_small_n_warnings_present"] = (
    '"[SMALL-N WARNING]" if n < 50 else "NONE"' in script_text and
    "WORMS" in script_text and
    "small_n_warning" in script_text
)

# 16. Stage-C frozen-language issues remain FLAG ONLY
checks["16_stage_c_frozen_language_flag_only"] = (
    '"PRE_C_LANGUAGE_001"' in script_text and
    '"PRE_C_LANGUAGE_002"' in script_text and
    '"FLAG ONLY (FROZEN ARTIFACT UNTOUCHED)"' in script_text
)

# 17. Final scientific decisions are dynamically computed
checks["17_scientific_decisions_dynamically_computed"] = (
    'decisions = {' in script_text and
    'f"Stacking and RF changes fell below practical materiality thresholds' in script_text and
    'f"Linear SVM exhibited material drops' in script_text and
    'ae_p["discordant_pairs"] == 0' in script_text
)

# 18. Final status is dynamically computed
checks["18_final_status_dynamically_computed"] = (
    'final_status = "PASS WITH EXPLICIT LIMITATIONS" if has_limitations else "PASS"' in script_text and
    '"computed_final_status": final_status' in script_text
)

# 19. No frozen artifact is modified
def check_git_isolation():
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode("utf-8")
        frozen_dirs = [
            "results/zero_day",
            "results/stacking",
            "results/autoencoder",
            "results/checkpoints",
            "results/feature_selection",
            "data/raw",
            "data/splits",
            "results/publication_experiments/EXP_NO_TTL_V1",
            "results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1",
        ]
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            for fd in frozen_dirs:
                if path.startswith(fd):
                    return False, f"Modified frozen path: {path}"
            if path == "RESEARCH_PAPER_MANUSCRIPT.md" and ("M" in code or "D" in code):
                return False, f"Modified manuscript: {path}"
        return True, "All frozen paths untouched"
    except Exception as e:
        return False, str(e)

iso_ok, iso_msg = check_git_isolation()
checks["19_no_frozen_artifact_modified"] = iso_ok

# 20. No Stage-B or Stage-C artifact is modified
def check_stage_b_c_isolation():
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode("utf-8")
        for line in out.strip().split("\n"):
            if "EXP_NO_TTL_V1" in line or "EXP_AE_UNSEEN_FAMILY_V1" in line:
                return False
        return True
    except Exception:
        return False

checks["20_no_stage_b_or_stage_c_modified"] = check_stage_b_c_isolation()


print("=" * 70)
print("STAGE D MASTER 20-POINT STATIC VALIDATION AUDIT")
print("=" * 70)
all_pass = True
for k, v in checks.items():
    status = "PASS" if v else "FAIL"
    print(f"  [{status}] {k}")
    if not v:
        all_pass = False

print("-" * 70)
if all_pass:
    print("ALL 20 STATIC VALIDATION CHECKS PASSED PERFECTLY!")
    sys.exit(0)
else:
    print("ONE OR MORE STATIC VALIDATION CHECKS FAILED!")
    sys.exit(1)
