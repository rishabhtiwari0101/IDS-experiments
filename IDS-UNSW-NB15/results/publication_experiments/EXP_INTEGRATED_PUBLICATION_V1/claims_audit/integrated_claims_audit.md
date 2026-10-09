# Integrated Claims vs. Evidence Audit (Stage E)

This audit evaluates the scientific support, materiality, and precise allowed phrasing for all core publication claims.

## CLAIM_A_NO_TTL_SUPERVISED: No-TTL representation ablation has limited effect on ensemble supervised classification.
- **Evidence Source**: EXP_NO_TTL_V1 & EXP_STATS_ROBUSTNESS_V1
- **Metric**: Macro-F1 (N=81749) & Backdoor Detection (N=583)
- **Statistical Status**: `CRITERION_BASED_ANALYSIS_CONFIRMED`
- **Materiality Status**: `BELOW_PRACTICAL_MATERIALITY_THRESHOLD`
- **Comparability**: `DIRECTLY_COMPARABLE`
- **Limitation**: Ablation evaluated on UNSW-NB15 feature set and split; does not establish universal TTL irrelevance.
- **Allowed Wording**: *"The evaluated ensemble models showed relatively small observed changes under the controlled No-TTL representation ablation, falling below preregistered practical materiality thresholds."*
- **Forbidden Wording**: ❌ *"TTL features are proven completely irrelevant or causally unimportant across all intrusion detection domains."*

## CLAIM_B_SVM_SENSITIVITY: Linear SVM exhibited greater sensitivity to TTL feature removal than ensembles.
- **Evidence Source**: EXP_NO_TTL_V1 & EXP_STATS_ROBUSTNESS_V1
- **Metric**: Macro-F1 (delta=-0.0297) & Backdoor Detection (delta=-11)
- **Statistical Status**: `PREREGISTERED_MATERIALITY_CONFIRMED (Raw p=0.0127, Holm p=0.0636)`
- **Materiality Status**: `MATERIAL_DIFFERENCE_CONFIRMED`
- **Comparability**: `DIRECTLY_COMPARABLE`
- **Limitation**: Applies strictly to evaluated Linear SVM with L2 penalty; does not imply SVM is generally defective.
- **Allowed Wording**: *"The Linear SVM exhibited greater sensitivity to the evaluated No-TTL representation change than the ensemble models, consistent with the Stage-D criterion-based analysis."*
- **Forbidden Wording**: ❌ *"SVM is an inferior classifier or TTL features causally degrade linear models."*

## CLAIM_C_PRIMARY_AE_DETECTION: Primary Autoencoder threshold yielded no detections on AE-unseen attack families.
- **Evidence Source**: EXP_AE_UNSEEN_FAMILY_V1 & EXP_STATS_ROBUSTNESS_V1
- **Metric**: Detection Count x/N with Exact Clopper-Pearson 95% CIs
- **Statistical Status**: `EXACT_UNCERTAINTY_BOUNDED`
- **Materiality Status**: `ZERO_DETECTIONS_OBSERVED`
- **Comparability**: `COMPARABLE_WITHIN_EXPERIMENT`
- **Limitation**: Zero sample detections does not imply 0% true sensitivity; upper bounds reach up to 8.04% (Worms N=44).
- **Allowed Wording**: *"No detections were observed for the evaluated AE-unseen attack families under the primary mean+3σ operating point."*
- **Forbidden Wording**: ❌ *"The Autoencoder has 0% true sensitivity or is proven incapable of zero-day detection."*

## CLAIM_D_THRESHOLD_TRADEOFF: Relaxed threshold operating points increase detection at the cost of higher false-positive rates.
- **Evidence Source**: EXP_AE_UNSEEN_FAMILY_V1 & EXP_STATS_ROBUSTNESS_V1
- **Metric**: Detection Rate vs Benign FPR across 60 matrix cells
- **Statistical Status**: `EMPIRICALLY_CONFIRMED_IN_EVALUATED_MATRIX`
- **Materiality Status**: `DESCRIPTIVE ONLY`
- **Comparability**: `COMPARABLE_WITHIN_EXPERIMENT`
- **Limitation**: Exploratory sensitivity analysis; no optimal threshold was preregistered or established.
- **Allowed Wording**: *"Several relaxed threshold operating points increased observed detections for selected families, accompanied in corresponding evaluated settings by higher benign false-positive rates."*
- **Forbidden Wording**: ❌ *"Relaxing the threshold always improves detection or p95 is the optimal operating point."*

## CLAIM_E_OVERALL_DEFENSE: Universal robust defense against all unseen attacks.
- **Evidence Source**: Synthesis across all experiments
- **Metric**: All evaluated metrics
- **Statistical Status**: `REJECTED_BY_EMPIRICAL_EVIDENCE`
- **Materiality Status**: `UNSUPPORTED`
- **Comparability**: `NOT_DIRECTLY_COMPARABLE`
- **Limitation**: Neither supervised models nor the Autoencoder provide universal protection; empirical limitations documented.
- **Allowed Wording**: *"The evaluated systems provide complementary empirical insights under specific, rigorously bounded experimental conditions."*
- **Forbidden Wording**: ❌ *"The proposed architecture achieves robust defense against all unseen attacks or universal zero-day protection."*

