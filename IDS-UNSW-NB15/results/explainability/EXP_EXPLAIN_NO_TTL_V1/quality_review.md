# EXP_EXPLAIN_NO_TTL_V1 — SHAP Quality Review
**Experiment:** `EXP_EXPLAIN_NO_TTL_V1`  
**Source Experiment:** `EXP_NO_TTL_V1` (72-feature No-TTL, Seed 42)  
**Generated:** 2026-09-09T05:04:11Z

## 1. Scope
Post-hoc SHAP explainability for the No-TTL 72-feature publication experiment.
Only Seed 42 is explained. Original Sprint 11 (EXP_EXPLAIN_V1, 75 features) is NOT modified.
Explains: NTL_RF (standalone Random Forest) and NTL_STACK (4-model stacking ensemble).

## 2. Pre-Verification Gates
- **Total Gates:** 29
- **All Passed:** YES ✓

| Gate ID | Description | Status |
|:---|:---|:---|
| PV-01 | NTL_RF checkpoint resolved | **PASS** |
| PV-02 | NTL_DT checkpoint resolved | **PASS** |
| PV-03 | NTL_SVM checkpoint resolved | **PASS** |
| PV-04 | NTL_NN checkpoint resolved | **PASS** |
| PV-05 | NTL_STACK meta-learner checkpoint resolved | **PASS** |
| PV-06 | Supervised scaler (72 features) resolved | **PASS** |
| PV-07 | OOF predictions (seed 42) resolved | **PASS** |
| PV-08 | No-TTL features JSON resolved | **PASS** |
| PV-09 | Exact 72-feature count confirmed | **PASS** |
| PV-10 | TTL features absent from No-TTL feature list | **PASS** |
| PV-11 | Class mapping confirmed (0=benign, 1=attack) | **PASS** |
| PV-12 | DEVELOPMENT_TEST row count confirmed (81,749) | **PASS** |
| PV-13 | Global source_row_uid uniqueness confirmed across all splits | **PASS** |
| PV-14 | Explanation-set generation reproducible (2,000 rows, seed 42) | **PASS** |
| PV-15 | Explanation set intersect TRAIN = zero | **PASS** |
| PV-16 | Explanation set intersect OOF-fitting population (seed 42) = zero | **PASS** |
| PV-17 | Explanation set intersect OOF-fitting population (seed 123) = zero | **PASS** |
| PV-18 | Explanation set intersect OOF-fitting population (seed 2024) = zero | **PASS** |
| PV-19 | Explanation set intersect VALIDATION / PROTECTED = zero | **PASS** |
| PV-20 | 72-feature matrix extracted correctly | **PASS** |
| PV-21 | 500-row TRAIN background sampled (seed 42) | **PASS** |
| PV-22 | All No-TTL models loaded | **PASS** |
| PV-23 | RF TreeExplainer compatibility verified | **PASS** |
| PV-24 | SVM LinearExplainer compatibility verified | **PASS** |
| PV-25 | Meta-learner LinearExplainer compatibility verified | **PASS** |
| PV-26 | NN DeepExplainer compatibility verified | **PASS** |
| PV-27 | No retraining or tuning — all models strictly frozen | **PASS** |
| PV-28 | Original EXP_EXPLAIN_V1 (Sprint 11) artifacts untouched | **PASS** |
| PV-29 | Output directory isolated from Sprint 11 (EXP_EXPLAIN_NO_TTL_V1) | **PASS** |

## 3. NTL_RF Top Features (TreeSHAP, 72 No-TTL Features)
| Rank | Feature Name | Mean |SHAP| |
|:---|:---|:---|
| 1 | `ackdat` | 0.060974 |
| 2 | `dload` | 0.050960 |
| 3 | `state_INT` | 0.044827 |
| 4 | `sload` | 0.041039 |
| 5 | `rate` | 0.035643 |
| 6 | `dbytes` | 0.032475 |
| 7 | `tcprtt` | 0.032229 |
| 8 | `sbytes` | 0.031492 |
| 9 | `ct_dst_sport_ltm` | 0.027753 |
| 10 | `ct_srv_dst` | 0.023824 |

> **Note:** TTL features (sttl, ct_state_ttl, dttl) are absent — confirming they cannot dominate importance in this experiment.

## 4. NTL_STACK Meta-Learner Importance
| Rank | Meta-Feature | Coefficient | Mean |SHAP| |
|:---|:---|:---|:---|
| 1 | `rf_attack_probability` | 6.715306 | 2.595261 |
| 2 | `svm_decision_score` | 0.657141 | 1.045329 |
| 3 | `nn_attack_probability` | 1.544066 | 0.616223 |
| 4 | `dt_attack_probability` | 0.194577 | 0.086058 |

## 5. Before-vs-After Comparison
- Status: `COMPLETED`
- Chart: `before_after_comparison/before_after_feature_importance.png`
- CSV: `before_after_comparison/feature_importance_comparison.csv`

## 6. Reproducibility
- Python: 3.11.9
- NumPy: 2.4.6
- PyTorch: 2.7.1+cu118
- SHAP: 0.51.0

## 7. Integrity
- Original EXP_EXPLAIN_V1 (Sprint 11) artifacts were NOT modified.
- All outputs are isolated to: `results/explainability/EXP_EXPLAIN_NO_TTL_V1/`
- No retraining, re-fitting, or threshold changes occurred.