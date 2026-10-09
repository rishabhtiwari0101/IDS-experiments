# Revision 5 Publication Experiments (`revision_v5`)

This directory contains the complete, reproducible suite of publication-oriented experiments for the **UNSW-NB15 Intrusion Detection System** research revision.

All experiments are conducted under strict **zero-training** rules (no refitting of upstream models), read-only baseline access, exact-arithmetic threshold calibration, and independent validation against a frozen baseline of 342 reference files.

---

## 1. Publication Experiment Index

| Stage | Experiment ID | Primary Script | Config File | Commit Hash | Status | Primary Output Artifact |
|:---|:---|:---|:---|:---|:---|:---|
| **S0** | `EXP_DISCOVERY_V1`<br>`EXP_POPULATIONS_V1` | [`phase0_discovery.py`](publication_experiments/scripts/phase0_discovery.py) | [`populations.yaml`](publication_experiments/configs/populations.yaml) | `4accd8c` | `PASS` | `DOC-07_calibration_audit.md`<br>`cal_control_row_uids.json` |
| **S1** | `EXP_PROB_INFERENCE_V1` | [`run_prob_inference.py`](publication_experiments/scripts/run_prob_inference.py) | [`populations.yaml`](publication_experiments/configs/populations.yaml) | `1818b81` | `PASS` | `zeroday_probabilities.csv`<br>`ae_zeroday_reconstruction_errors.csv` |
| **S7** | `EXP_IF_V1` | [`run_isolation_forest.py`](publication_experiments/stage_f/scripts/run_isolation_forest.py) | [`stage_f.yaml`](publication_experiments/stage_f/configs/stage_f.yaml) | `970f84c` | `PASS` | `scores/zeroday_scores.csv`<br>`zero_day/backdoor_detection.csv` |
| **S3** | `EXP_MATCHED_FPR_V1` | [`run_matched_fpr_analysis.py`](publication_experiments/scripts/run_matched_fpr_analysis.py) | [`matched_fpr.yaml`](publication_experiments/configs/matched_fpr.yaml) | `970f84c` | `PASS` | `matched_fpr_tier_b.csv`<br>`headline_tier_decision.json` |
| **S2** | `EXP_ROC_PR_V1` | [`run_roc_pr_analysis.py`](publication_experiments/scripts/run_roc_pr_analysis.py) | [`roc_pr.yaml`](publication_experiments/configs/roc_pr.yaml) | `ad2bd8d` | `PASS` | `figures/fig_roc_pr_zeroday.png`<br>`roc_pr_metrics_summary.csv` |
| **S4** | `EXP_TOST_V1` | [`run_tost_analysis.py`](publication_experiments/scripts/run_tost_analysis.py) | [`tost.yaml`](publication_experiments/configs/tost.yaml) | `dfeb6f2` | `PASS` | `tost_rf_equivalence.json` |
| **S5** | `EXP_MAD_THRESHOLD_V1` | [`run_mad_threshold.py`](publication_experiments/scripts/run_mad_threshold.py) | [`mad.yaml`](publication_experiments/configs/mad.yaml) | `468e895` | `PASS` | `mad_thresholds.csv`<br>`mad_threshold.json` |
| **S6** | `EXP_AE_ABLATION_V1` | [`run_ae_threshold_ablation.py`](publication_experiments/scripts/run_ae_threshold_ablation.py) | None (reads S5 JSON) | `72d9fcd` | `PASS` | `ae_ablation_results.csv`<br>`ae_ablation_results_unseen.csv` |
| **S8** | `EXP_ALERT_BUDGET_V1` | [`run_alert_budget_analysis.py`](publication_experiments/scripts/run_alert_budget_analysis.py) | None (reads S3 CSV) | `28fbfc5` | `PASS` | `alert_budget_table.csv`<br>`alert_budget_summary.json` |
| **S9** | `EXP_CROSS_CHECK_V1` | [`run_cross_consistency_check.py`](publication_experiments/scripts/run_cross_consistency_check.py) | None (reads all stages) | `7d3074c` | `PASS` | `cross_check_report.json`<br>`self_check.json` |

---

## 2. Reproduction Run Commands

Execute commands from the repository root:

```bash
# 0. Verify frozen baseline integrity (342/342 files bit-for-bit match)
python revision_v5/frozen_integrity_check.py

# Stage S0: Phase 0 discovery, population splits, and leakage audit
python revision_v5/publication_experiments/scripts/phase0_discovery.py

# Stage S1: Probability and AE reconstruction error inference (zero training)
python revision_v5/publication_experiments/scripts/run_prob_inference.py

# Stage S7: Train Isolation Forest baseline on benign TRAIN (seeds 42, 123, 2024)
python revision_v5/publication_experiments/stage_f/scripts/run_isolation_forest.py

# Stage S3: Two-tier matched-FPR analysis and headline tier decision
python revision_v5/publication_experiments/scripts/run_matched_fpr_analysis.py

# Stage S2: High-resolution ROC/PR zero-day evaluation curves on Tier B eval half
python revision_v5/publication_experiments/scripts/run_roc_pr_analysis.py

# Stage S4: Conservative exact paired-equivalence test for RF ± TTL (EXP_TOST_V1)
python revision_v5/publication_experiments/scripts/run_tost_analysis.py

# Stage S5: Autoencoder threshold families and MAD calibration
python revision_v5/publication_experiments/scripts/run_mad_threshold.py

# Stage S6: AE threshold ablation on evaluation control, Backdoor, and unseen families
python revision_v5/publication_experiments/scripts/run_ae_threshold_ablation.py

# Stage S8: Operational alert budget analysis per 10,000 benign flows
python revision_v5/publication_experiments/scripts/run_alert_budget_analysis.py

# Stage S9: Executable cross-result consistency and reconciliation check (9/9 checks)
python revision_v5/publication_experiments/scripts/run_cross_consistency_check.py
```

---

## 3. Untracked Checkpoints Notice (`.joblib` Models)

Per the repository's root `.gitignore` rules (`*.joblib` and `**/checkpoints/`), binary model checkpoint files are not tracked in Git to prevent large binary bloat.

- **Affected Files:**
  - `revision_v5/results/checkpoints/EXP_IF_V1/seed_42/if_model.joblib`
  - `revision_v5/results/checkpoints/EXP_IF_V1/seed_123/if_model.joblib`
  - `revision_v5/results/checkpoints/EXP_IF_V1/seed_2024/if_model.joblib`
- **Reproducibility Guarantee:**
  - These Isolation Forest models are trained deterministically on Normal TRAIN ($N=44,800$, label == 0) using the declared seeds (`42, 123, 2024`) and the frozen scaler `results/checkpoints/EXP_AE_V1/ae_scaler.joblib`.
  - Exact SHA-256 hashes of the trained models and the referenced scaler are committed in:
    - [`results/checkpoints/EXP_IF_V1/ae_scaler_reference.json`](results/checkpoints/EXP_IF_V1/ae_scaler_reference.json)
    - [`results/publication_experiments/EXP_IF_V1/metadata.json`](results/publication_experiments/EXP_IF_V1/metadata.json)
  - Running the Stage S7 command above reproduces these exact models deterministically.

---

## 4. Documentation Artifacts

- [`docs/IMPLEMENTATION_BLUEPRINT_v5.md`](docs/IMPLEMENTATION_BLUEPRINT_v5.md): Controlling methodological execution blueprint (v5.0).
- [`docs/DOC-07_calibration_audit.md`](docs/DOC-07_calibration_audit.md): Complete audit proving `validation.csv` and `development_test.csv` were untouched by upstream model development.
- [`docs/DOC_PREREGISTRATION_TIMING.md`](docs/DOC_PREREGISTRATION_TIMING.md): Git commit timestamps, SHA-256 hashes, and formal preregistration trace.
- [`docs/DOC_SCOPE_DECISION.md`](docs/DOC_SCOPE_DECISION.md): Formal scope bounding, second-dataset exclusion rationale, and explicit non-claims.
- [`DECISIONS.md`](DECISIONS.md): Comprehensive log of all methodological decisions, disambiguations, and notes (including BN-01 through BN-09).
- [`PROGRESS_LOG.md`](PROGRESS_LOG.md): Append-only chronological audit log of all experimental executions.
