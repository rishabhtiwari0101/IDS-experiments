# Authoritative Numbers Pack — CIC-IDS-2017 Revision v1
**Status:** FROZEN & AUDITED  
**Sprint:** 7 (Verification, Reproducibility & Results Freeze)  
**Total Canonical Metric Entries:** 224  
**Coverage:** 100% of manuscript-facing empirical metrics mapped directly to source artifacts.

---

| Metric ID | Dataset | Experiment / Domain | Source File | Exact Field / Row Query | Seed | Value | Unit / Definition |
|:---|:---|:---|:---|:---|:---|:---|:---|
| POP-01 | CIC-IDS-2017 | Populations | `population_manifest.json` | `total_cleaned_flows` | N/A | **2519404** | Total cleaned valid network flows |
| POP-02 | CIC-IDS-2017 | Populations | `population_manifest.json` | `explicitly_logged_removals_count` | N/A | **1395351** | Explicitly logged removal flows (duplicates, invalid, confounds) |
| POP-03 | CIC-IDS-2017 | Populations | `population_manifest.json` | `total_assigned_population_flows` | N/A | **1124053** | Total flows assigned across 8 split populations |
| POP-04 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[TRAIN].rows` | N/A | **340464** | TRAIN split volume |
| POP-05 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[DEV_TEST].rows` | N/A | **743921** | DEV_TEST split volume |
| POP-06 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[CALIBRATION].rows` | N/A | **18500** | CALIBRATION split volume (pure benign) |
| POP-07 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[EVAL_CONTROL].rows` | N/A | **18500** | EVAL_CONTROL split volume (pure benign) |
| POP-08 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[PROTECTED_BOT].rows` | N/A | **1948** | PROTECTED_BOT zero-day evaluation volume |
| POP-09 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[UNSEEN_XSS].rows` | N/A | **652** | UNSEEN_XSS web attack evaluation volume |
| POP-10 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[UNSEEN_INFILTRATION].rows` | N/A | **36** | UNSEEN_INFILTRATION attack evaluation volume |
| POP-11 | CIC-IDS-2017 | Populations | `population_manifest.json` | `populations[EXCLUDED_SMALL].rows` | N/A | **32** | EXCLUDED_SMALL attack evaluation volume |
| FEAT-01 | CIC-IDS-2017 | Feature Selection | `selected_features.json` | `len(selected_features)` | N/A | **69** | Selected optimal feature dimension K* |
| FEAT-02 | CIC-IDS-2017 | Shortcut Freeze | `shortcut_list_frozen.json` | `frozen_shortcut_set[0]` | N/A | **Destination Port** | Identified shortcut feature #1 |
| FEAT-03 | CIC-IDS-2017 | Shortcut Freeze | `shortcut_list_frozen.json` | `frozen_shortcut_set[1]` | N/A | **Init_Win_bytes_backward** | Identified shortcut feature #2 |
| FEAT-04 | CIC-IDS-2017 | Shortcut Freeze | `shortcut_list_frozen.json` | `creation_timestamp_utc` | N/A | **2026-10-06T06:44:46.095782+00:00** | Frozen shortcut list UTC creation timestamp |
| SUP-DT-01 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.mean_macro_f1` | Pooled (3 seeds) | **0.99693** | DT Mean Macro-F1 |
| SUP-DT-02 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.mean_fpr` | Pooled (3 seeds) | **0.002049** | DT Mean False Positive Rate |
| SUP-DT-F1-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.42.macro_f1` | 42 | **0.99698** | DT Seed 42 Macro-F1 |
| SUP-DT-FPR-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.42.fpr` | 42 | **0.002016** | DT Seed 42 FPR |
| SUP-DT-F1-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.123.macro_f1` | 123 | **0.99699** | DT Seed 123 Macro-F1 |
| SUP-DT-FPR-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.123.fpr` | 123 | **0.002007** | DT Seed 123 FPR |
| SUP-DT-F1-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.2024.macro_f1` | 2024 | **0.99683** | DT Seed 2024 Macro-F1 |
| SUP-DT-FPR-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.dt.per_seed.2024.fpr` | 2024 | **0.002124** | DT Seed 2024 FPR |
| SUP-RF-01 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.mean_macro_f1` | Pooled (3 seeds) | **0.99856** | RF Mean Macro-F1 |
| SUP-RF-02 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.mean_fpr` | Pooled (3 seeds) | **0.000919** | RF Mean False Positive Rate |
| SUP-RF-F1-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.42.macro_f1` | 42 | **0.99854** | RF Seed 42 Macro-F1 |
| SUP-RF-FPR-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.42.fpr` | 42 | **0.000936** | RF Seed 42 FPR |
| SUP-RF-F1-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.123.macro_f1` | 123 | **0.99857** | RF Seed 123 Macro-F1 |
| SUP-RF-FPR-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.123.fpr` | 123 | **0.000914** | RF Seed 123 FPR |
| SUP-RF-F1-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.2024.macro_f1` | 2024 | **0.99857** | RF Seed 2024 Macro-F1 |
| SUP-RF-FPR-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.rf.per_seed.2024.fpr` | 2024 | **0.000907** | RF Seed 2024 FPR |
| SUP-SVM-01 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.mean_macro_f1` | Pooled (3 seeds) | **0.89204** | SVM Mean Macro-F1 |
| SUP-SVM-02 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.mean_fpr` | Pooled (3 seeds) | **0.077760** | SVM Mean False Positive Rate |
| SUP-SVM-F1-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.42.macro_f1` | 42 | **0.89204** | SVM Seed 42 Macro-F1 |
| SUP-SVM-FPR-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.42.fpr` | 42 | **0.077760** | SVM Seed 42 FPR |
| SUP-SVM-F1-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.123.macro_f1` | 123 | **0.89204** | SVM Seed 123 Macro-F1 |
| SUP-SVM-FPR-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.123.fpr` | 123 | **0.077760** | SVM Seed 123 FPR |
| SUP-SVM-F1-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.2024.macro_f1` | 2024 | **0.89204** | SVM Seed 2024 Macro-F1 |
| SUP-SVM-FPR-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.svm.per_seed.2024.fpr` | 2024 | **0.077760** | SVM Seed 2024 FPR |
| SUP-NN-01 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.mean_macro_f1` | Pooled (3 seeds) | **0.94098** | NN Mean Macro-F1 |
| SUP-NN-02 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.mean_fpr` | Pooled (3 seeds) | **0.043287** | NN Mean False Positive Rate |
| SUP-NN-F1-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.42.macro_f1` | 42 | **0.94101** | NN Seed 42 Macro-F1 |
| SUP-NN-FPR-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.42.fpr` | 42 | **0.043347** | NN Seed 42 FPR |
| SUP-NN-F1-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.123.macro_f1` | 123 | **0.93780** | NN Seed 123 Macro-F1 |
| SUP-NN-FPR-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.123.fpr` | 123 | **0.045976** | NN Seed 123 FPR |
| SUP-NN-F1-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.2024.macro_f1` | 2024 | **0.94413** | NN Seed 2024 Macro-F1 |
| SUP-NN-FPR-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.nn.per_seed.2024.fpr` | 2024 | **0.040537** | NN Seed 2024 FPR |
| SUP-STACKING-01 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.mean_macro_f1` | Pooled (3 seeds) | **0.99864** | Stacking Ensemble Mean Macro-F1 |
| SUP-STACKING-02 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.mean_fpr` | Pooled (3 seeds) | **0.000874** | Stacking Ensemble Mean False Positive Rate |
| SUP-STACKING-F1-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.42.macro_f1` | 42 | **0.99865** | Stacking Ensemble Seed 42 Macro-F1 |
| SUP-STACKING-FPR-S42 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.42.fpr` | 42 | **0.000870** | Stacking Ensemble Seed 42 FPR |
| SUP-STACKING-F1-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.123.macro_f1` | 123 | **0.99859** | Stacking Ensemble Seed 123 Macro-F1 |
| SUP-STACKING-FPR-S123 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.123.fpr` | 123 | **0.000904** | Stacking Ensemble Seed 123 FPR |
| SUP-STACKING-F1-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.2024.macro_f1` | 2024 | **0.99868** | Stacking Ensemble Seed 2024 Macro-F1 |
| SUP-STACKING-FPR-S2024 | CIC-IDS-2017 | Supervised DEV_TEST | `dev_test_evaluation.json` | `aggregated.stacking.per_seed.2024.fpr` | 2024 | **0.000849** | Stacking Ensemble Seed 2024 FPR |
| ZD-DT-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.000000** | DT Recall on PROTECTED_BOT |
| ZD-DT-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.967791** | DT Recall on UNSEEN_XSS |
| ZD-DT-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.027778** | DT Recall on UNSEEN_INFILTRATION |
| ZD-RF-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.000000** | RF Recall on PROTECTED_BOT |
| ZD-RF-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.967791** | RF Recall on UNSEEN_XSS |
| ZD-RF-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.000000** | RF Recall on UNSEEN_INFILTRATION |
| ZD-SVM-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.264374** | SVM Recall on PROTECTED_BOT |
| ZD-SVM-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.029141** | SVM Recall on UNSEEN_XSS |
| ZD-SVM-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.333333** | SVM Recall on UNSEEN_INFILTRATION |
| ZD-IDSN-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.001027** | IDSNet Recall on PROTECTED_BOT |
| ZD-IDSN-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.995399** | IDSNet Recall on UNSEEN_XSS |
| ZD-IDSN-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.111111** | IDSNet Recall on UNSEEN_INFILTRATION |
| ZD-STAC-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.000000** | Stacking Recall on PROTECTED_BOT |
| ZD-STAC-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.943252** | Stacking Recall on UNSEEN_XSS |
| ZD-STAC-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.194444** | Stacking Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.006674** | Autoencoder_Standard Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.000000** | Autoencoder_Standard Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.305556** | Autoencoder_Standard Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.009240** | Autoencoder_Log1p Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.000000** | Autoencoder_Log1p Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.083333** | Autoencoder_Log1p Recall on UNSEEN_INFILTRATION |
| ZD-ISOL-PRO-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=PROTECTED_BOT,seed=42].recall` | 42 | **0.014887** | Isolation_Forest Recall on PROTECTED_BOT |
| ZD-ISOL-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_XSS,seed=42].recall` | 42 | **0.024540** | Isolation_Forest Recall on UNSEEN_XSS |
| ZD-ISOL-UNS-S42 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_INFILTRATION,seed=42].recall` | 42 | **0.638889** | Isolation_Forest Recall on UNSEEN_INFILTRATION |
| ZD-DT-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.000000** | DT Recall on PROTECTED_BOT |
| ZD-DT-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.967791** | DT Recall on UNSEEN_XSS |
| ZD-DT-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.027778** | DT Recall on UNSEEN_INFILTRATION |
| ZD-RF-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.000000** | RF Recall on PROTECTED_BOT |
| ZD-RF-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.967791** | RF Recall on UNSEEN_XSS |
| ZD-RF-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.000000** | RF Recall on UNSEEN_INFILTRATION |
| ZD-SVM-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.264374** | SVM Recall on PROTECTED_BOT |
| ZD-SVM-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.029141** | SVM Recall on UNSEEN_XSS |
| ZD-SVM-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.333333** | SVM Recall on UNSEEN_INFILTRATION |
| ZD-IDSN-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.001027** | IDSNet Recall on PROTECTED_BOT |
| ZD-IDSN-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.996933** | IDSNet Recall on UNSEEN_XSS |
| ZD-IDSN-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.138889** | IDSNet Recall on UNSEEN_INFILTRATION |
| ZD-STAC-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.000000** | Stacking Recall on PROTECTED_BOT |
| ZD-STAC-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.943252** | Stacking Recall on UNSEEN_XSS |
| ZD-STAC-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.166667** | Stacking Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.005647** | Autoencoder_Standard Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.000000** | Autoencoder_Standard Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.305556** | Autoencoder_Standard Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.004620** | Autoencoder_Log1p Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.000000** | Autoencoder_Log1p Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.111111** | Autoencoder_Log1p Recall on UNSEEN_INFILTRATION |
| ZD-ISOL-PRO-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=PROTECTED_BOT,seed=123].recall` | 123 | **0.022074** | Isolation_Forest Recall on PROTECTED_BOT |
| ZD-ISOL-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_XSS,seed=123].recall` | 123 | **0.024540** | Isolation_Forest Recall on UNSEEN_XSS |
| ZD-ISOL-UNS-S123 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_INFILTRATION,seed=123].recall` | 123 | **0.555556** | Isolation_Forest Recall on UNSEEN_INFILTRATION |
| ZD-DT-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.000000** | DT Recall on PROTECTED_BOT |
| ZD-DT-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.967791** | DT Recall on UNSEEN_XSS |
| ZD-DT-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=DT,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.027778** | DT Recall on UNSEEN_INFILTRATION |
| ZD-RF-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.000000** | RF Recall on PROTECTED_BOT |
| ZD-RF-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.967791** | RF Recall on UNSEEN_XSS |
| ZD-RF-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=RF,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.000000** | RF Recall on UNSEEN_INFILTRATION |
| ZD-SVM-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.264374** | SVM Recall on PROTECTED_BOT |
| ZD-SVM-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.029141** | SVM Recall on UNSEEN_XSS |
| ZD-SVM-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=SVM,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.333333** | SVM Recall on UNSEEN_INFILTRATION |
| ZD-IDSN-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.252567** | IDSNet Recall on PROTECTED_BOT |
| ZD-IDSN-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.986196** | IDSNet Recall on UNSEEN_XSS |
| ZD-IDSN-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=IDSNet,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.111111** | IDSNet Recall on UNSEEN_INFILTRATION |
| ZD-STAC-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.000000** | Stacking Recall on PROTECTED_BOT |
| ZD-STAC-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.943252** | Stacking Recall on UNSEEN_XSS |
| ZD-STAC-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Stacking,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.166667** | Stacking Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.005647** | Autoencoder_Standard Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.000000** | Autoencoder_Standard Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Standard,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.305556** | Autoencoder_Standard Recall on UNSEEN_INFILTRATION |
| ZD-AUTO-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.003080** | Autoencoder_Log1p Recall on PROTECTED_BOT |
| ZD-AUTO-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.000000** | Autoencoder_Log1p Recall on UNSEEN_XSS |
| ZD-AUTO-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Autoencoder_Log1p,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.166667** | Autoencoder_Log1p Recall on UNSEEN_INFILTRATION |
| ZD-ISOL-PRO-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=PROTECTED_BOT,seed=2024].recall` | 2024 | **0.022587** | Isolation_Forest Recall on PROTECTED_BOT |
| ZD-ISOL-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_XSS,seed=2024].recall` | 2024 | **0.024540** | Isolation_Forest Recall on UNSEEN_XSS |
| ZD-ISOL-UNS-S2024 | CIC-IDS-2017 | Zero-Day Evaluation | `zero_day_evaluation_summary.json` | `results[detector=Isolation_Forest,attack_set=UNSEEN_INFILTRATION,seed=2024].recall` | 2024 | **0.666667** | Isolation_Forest Recall on UNSEEN_INFILTRATION |
| HYB-C06-Q3 | CIC-IDS-2017 | Hybrid Fusion C06 | `s23_c06_hybrid_marker.json` | `mean(Q3_ae_rescue)` | Pooled | **37.67** | Mean incremental attack rescues over Stacking |
| HYB-C06-XFP | CIC-IDS-2017 | Hybrid Fusion C06 | `s23_c06_hybrid_marker.json` | `mean(extra_fp_over_stacking)` | Pooled | **49.33** | Mean incremental false alarms over Stacking |
| HYP-H1 | CIC-IDS-2017 | Hypothesis H1 | `s19_ablation_evaluation.json` | `H1_verdict.conclusion` | Pooled | **SHORTCUTS SIGNIFICANTLY CHANGE ERRORS** | H1 Error pattern independence verdict |
| HYP-H2 | CIC-IDS-2017 | Hypothesis H2 | `s19_ablation_evaluation.json` | `H2_verdict.conclusion` | Pooled | **SHORTCUT CONTRIBUTION IS NEGLIGIBLE (H2 CONFIRMED)** | H2 TOST Macro-F1 equivalence verdict |
| HYP-H2-DELTA | CIC-IDS-2017 | Hypothesis H2 | `s19_ablation_evaluation.json` | `H2_verdict.mean_delta_rf_f1` | Pooled | **0.001480** | RF TOST Equivalence Mean Delta Macro-F1 |
| HYP-H3 | CIC-IDS-2017 | Hypothesis H3 | `h3_h4_statistical_tests.json` | `H3_autoencoder_evaluation[0].verdict` | Pooled | **PARTIALLY_SUPPORTED** | H3 Standalone Autoencoder zero-day detection verdict |
| HYP-H4 | CIC-IDS-2017 | Hypothesis H4 | `h3_h4_statistical_tests.json` | `H4_hybrid_rescue_evaluation[0].verdict` | Pooled | **NOT_SUPPORTED** | H4 Inclusive hybrid OR fusion benefit verdict |
| FT-CIC-F1 | CIC-IDS-2017 | FT-Transformer | `s21_ft_transformer_cic_results.json` | `results.full.mean_dev_test_macro_f1` | Pooled | **0.98636** | CIC Full FT-Transformer DEV_TEST Macro-F1 |
| FT-CIC-BOT | CIC-IDS-2017 | FT-Transformer | `s21_ft_transformer_cic_results.json` | `results.full.mean_zero_day_bot_recall` | Pooled | **0.00000** | CIC Full FT-Transformer Zero-Day Bot Recall |
| FT-UNSW-F1 | UNSW-NB15 | FT-Transformer | `s22_ft_transformer_unsw_results.json` | `mean_dev_test_macro_f1` | Pooled | **0.84884** | UNSW FT-Transformer DEV_TEST Macro-F1 (K=50) |
| FT-UNSW-BKD | UNSW-NB15 | FT-Transformer | `s22_ft_transformer_unsw_results.json` | `per_seed_results.42.zero_day_backdoor.recall` | 42, 123, 2024 | **1.00000** | UNSW FT-Transformer Zero-Day Backdoor Recall |
| MF-RAND-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.001.recall_mean` | Pooled | **0.000000** | random_forest Zero-Day Recall at Matched-FPR 0.001 |
| MF-RAND-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.001.fpr_eval_mean` | Pooled | **0.000000** | random_forest Empirical Eval Control FPR at target 0.001 |
| MF-RAND-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.005.recall_mean` | Pooled | **0.000513** | random_forest Zero-Day Recall at Matched-FPR 0.005 |
| MF-RAND-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.005.fpr_eval_mean` | Pooled | **0.000000** | random_forest Empirical Eval Control FPR at target 0.005 |
| MF-RAND-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.01.recall_mean` | Pooled | **0.001369** | random_forest Zero-Day Recall at Matched-FPR 0.01 |
| MF-RAND-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.01.fpr_eval_mean` | Pooled | **0.000000** | random_forest Empirical Eval Control FPR at target 0.01 |
| MF-RAND-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.05.recall_mean` | Pooled | **0.218172** | random_forest Zero-Day Recall at Matched-FPR 0.05 |
| MF-RAND-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.random_forest.0.05.fpr_eval_mean` | Pooled | **0.000000** | random_forest Empirical Eval Control FPR at target 0.05 |
| MF-IDSN-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.001.recall_mean` | Pooled | **0.000000** | idsnet Zero-Day Recall at Matched-FPR 0.001 |
| MF-IDSN-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.001.fpr_eval_mean` | Pooled | **0.000000** | idsnet Empirical Eval Control FPR at target 0.001 |
| MF-IDSN-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.005.recall_mean` | Pooled | **0.000000** | idsnet Zero-Day Recall at Matched-FPR 0.005 |
| MF-IDSN-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.005.fpr_eval_mean` | Pooled | **0.000000** | idsnet Empirical Eval Control FPR at target 0.005 |
| MF-IDSN-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.01.recall_mean` | Pooled | **0.000000** | idsnet Zero-Day Recall at Matched-FPR 0.01 |
| MF-IDSN-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.01.fpr_eval_mean` | Pooled | **0.000000** | idsnet Empirical Eval Control FPR at target 0.01 |
| MF-IDSN-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.05.recall_mean` | Pooled | **0.086585** | idsnet Zero-Day Recall at Matched-FPR 0.05 |
| MF-IDSN-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.idsnet.0.05.fpr_eval_mean` | Pooled | **0.000000** | idsnet Empirical Eval Control FPR at target 0.05 |
| MF-STAC-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.001.recall_mean` | Pooled | **0.000000** | stacking Zero-Day Recall at Matched-FPR 0.001 |
| MF-STAC-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.001.fpr_eval_mean` | Pooled | **0.000000** | stacking Empirical Eval Control FPR at target 0.001 |
| MF-STAC-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.005.recall_mean` | Pooled | **0.001027** | stacking Zero-Day Recall at Matched-FPR 0.005 |
| MF-STAC-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.005.fpr_eval_mean` | Pooled | **0.000000** | stacking Empirical Eval Control FPR at target 0.005 |
| MF-STAC-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.01.recall_mean` | Pooled | **0.001027** | stacking Zero-Day Recall at Matched-FPR 0.01 |
| MF-STAC-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.01.fpr_eval_mean` | Pooled | **0.000000** | stacking Empirical Eval Control FPR at target 0.01 |
| MF-STAC-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.05.recall_mean` | Pooled | **0.085044** | stacking Zero-Day Recall at Matched-FPR 0.05 |
| MF-STAC-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.stacking.0.05.fpr_eval_mean` | Pooled | **0.000000** | stacking Empirical Eval Control FPR at target 0.05 |
| MF-AUTO-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.001.recall_mean` | Pooled | **0.008898** | autoencoder_standard Zero-Day Recall at Matched-FPR 0.001 |
| MF-AUTO-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.001.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_standard Empirical Eval Control FPR at target 0.001 |
| MF-AUTO-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.005.recall_mean` | Pooled | **0.021732** | autoencoder_standard Zero-Day Recall at Matched-FPR 0.005 |
| MF-AUTO-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.005.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_standard Empirical Eval Control FPR at target 0.005 |
| MF-AUTO-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.01.recall_mean` | Pooled | **0.022587** | autoencoder_standard Zero-Day Recall at Matched-FPR 0.01 |
| MF-AUTO-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.01.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_standard Empirical Eval Control FPR at target 0.01 |
| MF-AUTO-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.05.recall_mean` | Pooled | **0.026694** | autoencoder_standard Zero-Day Recall at Matched-FPR 0.05 |
| MF-AUTO-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_standard.0.05.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_standard Empirical Eval Control FPR at target 0.05 |
| MF-AUTO-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.001.recall_mean` | Pooled | **0.000000** | autoencoder_log1p Zero-Day Recall at Matched-FPR 0.001 |
| MF-AUTO-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.001.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_log1p Empirical Eval Control FPR at target 0.001 |
| MF-AUTO-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.005.recall_mean` | Pooled | **0.000000** | autoencoder_log1p Zero-Day Recall at Matched-FPR 0.005 |
| MF-AUTO-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.005.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_log1p Empirical Eval Control FPR at target 0.005 |
| MF-AUTO-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.01.recall_mean` | Pooled | **0.000000** | autoencoder_log1p Zero-Day Recall at Matched-FPR 0.01 |
| MF-AUTO-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.01.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_log1p Empirical Eval Control FPR at target 0.01 |
| MF-AUTO-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.05.recall_mean` | Pooled | **0.000342** | autoencoder_log1p Zero-Day Recall at Matched-FPR 0.05 |
| MF-AUTO-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.autoencoder_log1p.0.05.fpr_eval_mean` | Pooled | **0.000000** | autoencoder_log1p Empirical Eval Control FPR at target 0.05 |
| MF-ISOL-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.001.recall_mean` | Pooled | **0.000000** | isolation_forest Zero-Day Recall at Matched-FPR 0.001 |
| MF-ISOL-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.001.fpr_eval_mean` | Pooled | **0.000000** | isolation_forest Empirical Eval Control FPR at target 0.001 |
| MF-ISOL-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.005.recall_mean` | Pooled | **0.001882** | isolation_forest Zero-Day Recall at Matched-FPR 0.005 |
| MF-ISOL-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.005.fpr_eval_mean` | Pooled | **0.000000** | isolation_forest Empirical Eval Control FPR at target 0.005 |
| MF-ISOL-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.01.recall_mean` | Pooled | **0.007529** | isolation_forest Zero-Day Recall at Matched-FPR 0.01 |
| MF-ISOL-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.01.fpr_eval_mean` | Pooled | **0.000000** | isolation_forest Empirical Eval Control FPR at target 0.01 |
| MF-ISOL-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.05.recall_mean` | Pooled | **0.022587** | isolation_forest Zero-Day Recall at Matched-FPR 0.05 |
| MF-ISOL-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.isolation_forest.0.05.fpr_eval_mean` | Pooled | **0.000000** | isolation_forest Empirical Eval Control FPR at target 0.05 |
| MF-FT_T-0.001-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.001.recall_mean` | Pooled | **0.000000** | ft_transformer Zero-Day Recall at Matched-FPR 0.001 |
| MF-FT_T-0.001-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.001.fpr_eval_mean` | Pooled | **0.000000** | ft_transformer Empirical Eval Control FPR at target 0.001 |
| MF-FT_T-0.005-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.005.recall_mean` | Pooled | **0.000000** | ft_transformer Zero-Day Recall at Matched-FPR 0.005 |
| MF-FT_T-0.005-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.005.fpr_eval_mean` | Pooled | **0.000000** | ft_transformer Empirical Eval Control FPR at target 0.005 |
| MF-FT_T-0.01-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.01.recall_mean` | Pooled | **0.001540** | ft_transformer Zero-Day Recall at Matched-FPR 0.01 |
| MF-FT_T-0.01-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.01.fpr_eval_mean` | Pooled | **0.000000** | ft_transformer Empirical Eval Control FPR at target 0.01 |
| MF-FT_T-0.05-REC | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.05.recall_mean` | Pooled | **0.002567** | ft_transformer Zero-Day Recall at Matched-FPR 0.05 |
| MF-FT_T-0.05-FPR | CIC-IDS-2017 | Matched-FPR | `s23_matched_fpr_summary.json` | `per_model_summary.ft_transformer.0.05.fpr_eval_mean` | Pooled | **0.000000** | ft_transformer Empirical Eval Control FPR at target 0.05 |
| DEP-AUTOENCO-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Autoencoder (Standard)].median_latency_ms` | Pooled | **5.75** | Autoencoder (Standard) Median Latency (ms for 1000 flows) |
| DEP-AUTOENCO-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Autoencoder (Standard)].throughput_flows_per_s` | Pooled | **6627492.6** | Autoencoder (Standard) Throughput (flows/sec) |
| DEP-AUTOENCO-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Autoencoder (Standard)].peak_cpu_rss_mb` | Pooled | **1217.8** | Autoencoder (Standard) Peak CPU RSS (MB) |
| DEP-DECISION-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Decision Tree].median_latency_ms` | Pooled | **6.71** | Decision Tree Median Latency (ms for 1000 flows) |
| DEP-DECISION-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Decision Tree].throughput_flows_per_s` | Pooled | **4242505.1** | Decision Tree Throughput (flows/sec) |
| DEP-DECISION-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Decision Tree].peak_cpu_rss_mb` | Pooled | **1159.3** | Decision Tree Peak CPU RSS (MB) |
| DEP-FT-TRANS-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[FT-Transformer].median_latency_ms` | Pooled | **2605.02** | FT-Transformer Median Latency (ms for 1000 flows) |
| DEP-FT-TRANS-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[FT-Transformer].throughput_flows_per_s` | Pooled | **14266.3** | FT-Transformer Throughput (flows/sec) |
| DEP-FT-TRANS-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[FT-Transformer].peak_cpu_rss_mb` | Pooled | **1201.8** | FT-Transformer Peak CPU RSS (MB) |
| DEP-IDSNET_M-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[IDSNet (MLP)].median_latency_ms` | Pooled | **2.79** | IDSNet (MLP) Median Latency (ms for 1000 flows) |
| DEP-IDSNET_M-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[IDSNet (MLP)].throughput_flows_per_s` | Pooled | **9229183.3** | IDSNet (MLP) Throughput (flows/sec) |
| DEP-IDSNET_M-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[IDSNet (MLP)].peak_cpu_rss_mb` | Pooled | **1219.9** | IDSNet (MLP) Peak CPU RSS (MB) |
| DEP-ISOLATIO-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Isolation Forest].median_latency_ms` | Pooled | **686.55** | Isolation Forest Median Latency (ms for 1000 flows) |
| DEP-ISOLATIO-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Isolation Forest].throughput_flows_per_s` | Pooled | **41375.2** | Isolation Forest Throughput (flows/sec) |
| DEP-ISOLATIO-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Isolation Forest].peak_cpu_rss_mb` | Pooled | **1213.2** | Isolation Forest Peak CPU RSS (MB) |
| DEP-LINEAR_S-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Linear SVC].median_latency_ms` | Pooled | **25.85** | Linear SVC Median Latency (ms for 1000 flows) |
| DEP-LINEAR_S-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Linear SVC].throughput_flows_per_s` | Pooled | **1427956.2** | Linear SVC Throughput (flows/sec) |
| DEP-LINEAR_S-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Linear SVC].peak_cpu_rss_mb` | Pooled | **1199.0** | Linear SVC Peak CPU RSS (MB) |
| DEP-RANDOM_F-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Random Forest].median_latency_ms` | Pooled | **852.29** | Random Forest Median Latency (ms for 1000 flows) |
| DEP-RANDOM_F-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Random Forest].throughput_flows_per_s` | Pooled | **27206.4** | Random Forest Throughput (flows/sec) |
| DEP-RANDOM_F-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Random Forest].peak_cpu_rss_mb` | Pooled | **1199.1** | Random Forest Peak CPU RSS (MB) |
| DEP-STACKING-MED | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Stacking Ensemble].median_latency_ms` | Pooled | **1169.81** | Stacking Ensemble Median Latency (ms for 1000 flows) |
| DEP-STACKING-THRU | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Stacking Ensemble].throughput_flows_per_s` | Pooled | **28173.1** | Stacking Ensemble Throughput (flows/sec) |
| DEP-STACKING-RAM | CIC-IDS-2017 | Deployment | `s24_deployment_benchmark.csv` | `groupby(model)[Stacking Ensemble].peak_cpu_rss_mb` | Pooled | **1217.8** | Stacking Ensemble Peak CPU RSS (MB) |
| UNSW-STK-DET | UNSW-NB15 | Frozen Headline | `EXP_CROSS_CHECK_V1/cross_check_report.json` | `detailed_results.historical_zeroday_metrics.stacking_tp` | Canonical | **582 / 583** | Supervised Stacking Backdoor Detections |
| UNSW-STK-REC | UNSW-NB15 | Frozen Headline | `EXP_CROSS_CHECK_V1/cross_check_report.json` | `stacking_tp / 583` | Canonical | **99.83%** | Supervised Stacking Backdoor Recall |
| UNSW-STK-FPR | UNSW-NB15 | Frozen Headline | `EXP_CROSS_CHECK_V1/cross_check_report.json` | `stacking_fp / 37000` | Canonical | **19.19% (7,100 / 37,000)** | Supervised Stacking Benign False Positive Rate |
| UNSW-AE-REC | UNSW-NB15 | Frozen Headline | `EXP_AE_ABLATION_V1/ae_ablation_results.csv` | `backdoor_zeroday at mean_plus_3sigma recall` | Canonical | **0.00% (0 / 583)** | Autoencoder Standalone Backdoor Recall at mu+3sigma |
| UNSW-AE-TAU | UNSW-NB15 | Frozen Headline | `EXP_MAD_THRESHOLD_V1/mad_thresholds.csv` | `mean_plus_3sigma threshold` | Canonical | **11.160063** | Autoencoder Frozen Operational Threshold (mu+3sigma) |
| UNSW-HYB-XFP | UNSW-NB15 | Frozen Headline | `research_paper.md` | `Section 3 / Abstract` | Canonical | **+13** | Hybrid OR Fusion Incremental False Positives |
