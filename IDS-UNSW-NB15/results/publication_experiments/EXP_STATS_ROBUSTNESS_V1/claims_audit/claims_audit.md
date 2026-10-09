# Stage D Claims-vs-Evidence Audit Matrix

Evaluation of candidate claims against preregistered materiality thresholds and exact statistical evidence.

| Claim ID | Candidate Claim | Evidence / Effect Size | Materiality Status | Stage-D Action | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CLAIM_A | No-TTL removal materially harms ensemble performance. | |delta_Backdoor|=2 < 6, |delta_Macro-F1|=0.0017 < 0.01 | BELOW_PREDECLARED_MATERIALITY_THRESHOLD | EVALUATED_AGAINST_PREREGISTERED_MATERIALITY | **NOT SUPPORTED** |
| CLAIM_B | No-TTL removal has little effect on RF. | |delta_Backdoor|=0 < 6 | BELOW_PREDECLARED_MATERIALITY_THRESHOLD | EVALUATED_AGAINST_PREREGISTERED_MATERIALITY | **SUPPORTED (DESCRIPTIVELY)** |
| CLAIM_C | SVM is more sensitive to TTL-related representation changes. | |delta_Backdoor|=11 >= 6 (MATERIAL), |delta_Macro-F1|=0.0184 >= 0.01 (MATERIAL) | MATERIAL_DIFFERENCE_CONFIRMED | EVALUATED_AGAINST_PREREGISTERED_MATERIALITY | **SUPPORTED DESCRIPTIVELY** |
| CLAIM_D | AE robustly detects unseen attack families. | Detection rate = 0.0% across all evaluated families. | ZERO_DETECTIONS_OBSERVED | REJECTED_BASED_ON_EMPIRICAL_DATA | **NOT SUPPORTED** |
| CLAIM_E | Relaxed thresholds recover some anomaly signal. | Detection rates increased up to 6.0% (Backdoor), 13.6% (Worms), 4.0% (Analysis). | EMPIRICALLY_CONFIRMED_IN_SECONDARY_ANALYSIS | DESCRIPTIVELY_CONFIRMED | **SUPPORTED DESCRIPTIVELY** |
| CLAIM_F | Relaxed thresholds improve detection at an FPR cost. | FPR increases up to 8.60% (3,182 false alarms per 37,000 flows). | TRADE_OFF_CONFIRMED_DESCRIPTIVELY | CONFIRMED_BY_TRADE_OFF_ANALYSIS | **SUPPORTED DESCRIPTIVELY** |
| CLAIM_G | The AE has zero sensitivity. | Non-zero upper confidence bounds. | STATISTICAL_UNCERTAINTY_PRESERVED | FORBIDDEN_WORDING_REPLACED | **REPLACED WITH EXACT UNCERTAINTY** |
| CLAIM_H | The canonical and No-TTL AEs are equivalent. | Discordant pairs = 0. | COMPUTED_CONTINGENCY_EVALUATED | FORBIDDEN_WORDING_REPLACED | **NOT ESTABLISHED — STRUCTURAL DEGENERACY** |
| CLAIM_I | mean+3sigma is outlier-resistant. | High threshold driven by benign reconstruction variance. | METHODOLOGICALLY_INACCURATE_PHRASING | FORBIDDEN_WORDING_REPLACED | **REPLACED WITH METHODOLOGICALLY ACCURATE LANGUAGE** |
| PRE_C_LANGUAGE_001 | Stage-C frozen report uses 'outlier-resistant mean+3sigma' wording. | N/A | PRE_EXISTING_STAGE_C_WORDING_ISSUE | FLAG ONLY (FROZEN ARTIFACT UNTOUCHED) | **PRE-EXISTING STAGE-C LANGUAGE — FUTURE MANUSCRIPT FIX REQUIRED** |
| PRE_C_LANGUAGE_002 | Stage-C frozen report phrasing potentially interpreted as asserting 0% true sensitivity. | N/A | PRE_EXISTING_STAGE_C_WORDING_ISSUE | FLAG ONLY (FROZEN ARTIFACT UNTOUCHED) | **PRE-EXISTING STAGE-C LANGUAGE — FUTURE MANUSCRIPT FIX REQUIRED** |
| THREE_SEED_CLAIM | Supervised model performance is consistent across seeds. | Macro-F1 ranges: DT 0.0017, RF 0.0012, SVM 0.0055, NN 0.0044, Stacking 0.0006. | DESCRIPTIVE_ONLY | REVISED_FROM_CONSISTENCY_CLAIM_TO_DESCRIPTIVE_CHARACTERIZATION | **DESCRIPTIVE ONLY** |
| THRESHOLD_TRADEOFF_CLAIM | Relaxing threshold increases detection at the cost of FPR. | FPR increases up to 8.60% (3,182 false alarms / 37,000 flows). | DESCRIPTIVE_TRADE_OFF_AT_OBSERVED_POINTS | QUALIFIED_AS_DESCRIPTIVE_AND_LIMITED_TO_OBSERVED_OPERATING_POINTS | **SUPPORTED DESCRIPTIVELY** |
| RF_DEGENERACY | Random Forest McNemar paired test is structurally non-informative. | Discordant pairs = 0. Raw p = 1.00000, Holm-adjusted p = 1.00000. | DATA_DERIVED_STRUCTURAL_DEGENERACY_NOT_NET_DIFFERENCE | RECONSTRUCTED_FROM_ROW_LEVEL_PREDICTIONS | **STRUCTURALLY_NON_INFORMATIVE (CONFIRMED VIA ROW ALIGNMENT)** |

## Pre-Existing Stage-C Language Flags

### PRE_C_LANGUAGE_001
- **Source**: Stage-C frozen final report
- **Issue**: Uses 'outlier-resistant mean+3sigma' phrasing.
- **Treatment**: FLAG ONLY (Frozen artifact unchanged).
- **Future Action**: Replace in manuscript with technically accurate description of conservative empirical error distribution dependence.

### PRE_C_LANGUAGE_002
- **Source**: Stage-C frozen final report
- **Issue**: Phrasing potentially interpreted as claiming true sensitivity is exactly zero (0.00%).
- **Treatment**: FLAG ONLY (Frozen artifact unchanged).
- **Future Action**: Report sample observations (0/N) accompanied by exact Clopper-Pearson confidence intervals.

## Seed and Threshold Claim Clarifications

### THREE_SEED_CLAIM
- **Former Wording**: Three-seed consistency supported descriptively.
- **Revised Characterization**: DESCRIPTIVE ONLY. The three evaluated seeds (42, 123, 2024) are summarized descriptively. No formal preregistered criterion for seed 'consistency' was defined; therefore the analysis does not establish formal seed robustness.

### THRESHOLD_TRADEOFF_CLAIM
- **Former Wording**: Threshold trade-off supported.
- **Revised Characterization**: SUPPORTED DESCRIPTIVELY. Several relaxed threshold operating points increased observed detections for selected AE-unseen attack families, accompanied in the corresponding evaluated settings by higher benign false-positive rates. Limited to evaluated matrix cells.

### RF_DEGENERACY
- **Row-Level Reconstruction**: For RF, A=582, B=0, C=0, D=1 (discordant B+C=0) computed directly from row predictions on protected Backdoor N=583. Degeneracy is data-derived, not inferred from net count differences.
