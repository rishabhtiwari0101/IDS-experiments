# Sprint 7 Execution Report: Verification, Reproducibility & Results Freeze
**Revision:** CIC-IDS-2017 Cross-Dataset Scientific Extension (Revision v1)  
**Sprint:** 7 (Verification, Reproducibility & Results Freeze)  
**Status:** PASS — ALL 12 VERIFICATION GATES SATISFIED  
**Date:** October 7, 2026  
**Master Verifier:** `cicids2017/verify_revision.py`  
**Pipeline Orchestrator:** `cicids2017/run_all.py`  

---

## 1. Step 0 — Preflight Verification

All preflight checks were executed and confirmed prior to verification suite execution:

1. **Shortcut Freeze Integrity:**
   - Path: `results/cicids2017_revision_v1/shortcut_list_frozen.json`
   - Expected SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2`
   - Actual SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2`
   - Frozen Features: `["Destination Port", "Init_Win_bytes_backward"]`
   - **Status:** **PASS**
2. **UNSW-NB15 Freeze Manifest:**
   - Path: `reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256`
   - Files Checked: 1,261
   - Missing: 0 | Mismatches: 0
   - **Status:** **PASS**
3. **Git Isolation:**
   - Command: `git diff unsw_final --name-only`
   - Output: Strictly empty (0 modified tracked files)
   - **Status:** **PASS**
4. **CIC-IDS-2017 Population Accounting:**
   - TRAIN = 340,464
   - DEV_TEST = 743,921
   - CALIBRATION = 18,500
   - EVAL_CONTROL = 18,500
   - PROTECTED_BOT = 1,948
   - UNSEEN_XSS = 652
   - UNSEEN_INFILTRATION = 36
   - EXCLUDED_SMALL = 32
   - Total Assigned Flows: 1,124,053
   - Logged Removals: 1,395,351
   - Cleaned Total: 2,519,404 ($1,124,053 + 1,395,351 = 2,519,404$)
   - **Status:** **PASS (Exact Conservation)**

---

## 2. 12-Gate Master Verification Suite (`verify_revision.py`)

The automated master verifier evaluated all 12 definitive quality gates with zero failures:

| Gate | Title | Target / Invariant | Status | Execution Time |
|:---|:---|:---|:---|:---|
| **Gate 1** | UNSW Manifest Integrity | 1,261 files verified via SHA-256 (0 missing, 0 mismatches) | **PASS** | 3.29s |
| **Gate 2** | Git Diff Isolation | `git diff unsw_final` is strictly empty | **PASS** | 0.10s |
| **Gate 3** | Shortcut Freeze Integrity | SHA-256 `5e2942...` and feature set match exactly | **PASS** | 0.00s |
| **Gate 4** | Population Conservation | 2.52M cleaned = 1.12M assigned + 1.40M removals | **PASS** | 1.70s |
| **Gate 5** | Row UID Disjointness | Pairwise disjointness across all 8 populations ($8 \times 7 / 2 = 28$ checks) | **PASS** | 8.43s |
| **Gate 6** | Fit-Boundary & Leakage | Strict training-only fitting, calibration-only thresholds, pure inference | **PASS** | 0.00s |
| **Gate 7** | Timestamp Ordering | Shortcut freeze ($06:44:46$) preceded zero-day eval ($09:39:06$) by $2\text{h } 54\text{m } 20\text{s}$ | **PASS** | 0.00s |
| **Gate 8** | Model Artifact Inventory | 75 checkpoints and scalers present and non-zero across seeds | **PASS** | 0.01s |
| **Gate 9** | Table-to-Result Reconciliation | 100% mechanical agreement between report metrics and JSON/CSV artifacts | **PASS** | 0.01s |
| **Gate 10** | Deployment Benchmark | 24 benchmark rows, 8 models, operational disclaimer verified | **PASS** | 0.01s |
| **Gate 11** | Figures & Deliverable Reports | 4 PNGs (300 DPI) + 4 PDFs, 9 sprint and domain reports verified | **PASS** | 0.00s |
| **Gate 12** | Hardcoded Paths Audit | `check_no_hardcoded_paths.py --allow-cross-dataset` passes with 0 violations | **PASS** | 0.61s |

**Master Verification Result:** **12/12 GATES PASSED (100.0%)**  
**Audit Artifact:** `results/cicids2017_revision_v1/audit/master_verification_report.json`

---

## 3. Fit Boundary & Leakage Audit

Machine learning data boundaries were validated against all saved pipeline metadata:
1. **Scaler Normalization:** Fit strictly on benign TRAIN flows ($N=44,800$ for AE/IF; $N=340,464$ for supervised models).
2. **Mutual Information Selection:** Feature scores computed strictly on TRAIN ($K^*=69$).
3. **Out-of-Fold Stacking:** 5-fold cross-validation executed strictly within TRAIN; zero exposure to DEV_TEST or evaluation sets.
4. **Early Stopping:** Monitored strictly on internal validation splits within TRAIN.
5. **Threshold Calibration:** Parametric and empirical thresholds calibrated strictly on CALIBRATION ($N=18,500$ benign flows).
6. **Zero-Day & Evaluation Control:** Evaluated via pure frozen inference without parameter updates.

---

## 4. UNSW Regression Audit

The frozen UNSW-NB15 benchmark was verified without retraining:
- Stacking Backdoor Detections: **582 / 583**
- Stacking Backdoor Recall: **99.83%**
- Stacking Benign False Positive Rate: **19.19%** ($7,100 / 37,000$)
- Autoencoder Standalone Backdoor Recall at $\mu + 3\sigma$: **0.00%** ($0 / 583$)
- Autoencoder Canonical Threshold: $\tau = \mathbf{11.160063}$
- Hybrid Fusion Incremental Cost: **+13 false positives** ($Q_3 = 0, p = 1.000$)

All values exactly match the canonical figures and reports.

---

## 5. Master Numbers Pack & Summary Table

1. **Numbers Pack:**
   - Path: `results/cicids2017_revision_v1/numbers_pack.md`
   - Total Metrics Mapped: **224 distinct metrics**
   - Schema: `| Metric ID | Dataset | Experiment / Domain | Source File | Exact Field / Row Query | Seed | Value | Unit / Definition |`
   - Coverage: 100% of manuscript-facing empirical quantities.
2. **Final Summary CSV:**
   - Path: `results/cicids2017_revision_v1/final_summary.csv`
   - Dimensions: 16 comparative dimensions spanning scale, feature representation, supervised performance, anomaly suppression, hybrid fusion, deep tabular architectures, and deployment latency.
   - Modality Caveat: Explicitly annotated ($K=75$ vs $K=50$ for UNSW, $K^*=69$ for CIC).

---

## 6. Pipeline Orchestration & Reproducibility (`run_all.py`)

A master orchestration script was created at `cicids2017/run_all.py` supporting:
- `--dry-run`: Validates the full dependency graph across all 25 stages without fitting models.
- `--eval-only`: Evaluates frozen checkpoints across test sets without retraining.
- `--from-step <step>`: Allows resumption from any pipeline stage.
- `--log-dir <dir>`: Captures stdout/stderr into unified execution logs.

Execution of `run_all.py --dry-run` succeeded with all 25 stages confirmed.

---

## 7. Master Checksum Manifest

All final CIC revision artifacts are deterministically hashed in:
- `reports/cicids2017_revision_v1/manifests/CIC_REVISION_V1_MANIFEST.sha256`

---

## 8. Final Freeze Status & Git Tag

- **Verification Result:** PASS (12/12 Gates Satisfied)
- **Freeze Status:** OFFICIALLY FROZEN & AUDITED
- **Git Tag:** `cicids2017-revision-v1-complete`
- **Target Commit SHA:** `9a746c425f20b1c097d42e5499c0fc323865c3b7`
- **Tag Type:** Annotated Tag
- **Authorization:** Experimental evidence permanently frozen. Sprint 8 (Manuscript Revision) is cleared to begin.
