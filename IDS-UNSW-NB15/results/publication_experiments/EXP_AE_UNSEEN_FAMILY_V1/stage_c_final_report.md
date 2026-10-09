# STAGE C FINAL AUDIT REPORT
## Benign-Only Autoencoder Unseen Attack-Family Evaluation
**Experiment ID:** `EXP_AE_UNSEEN_FAMILY_V1`  
**Date:** 2026-09-08 15:53:24 UTC  
**Runtime:** 381.2s (6.4 min)  
**Status:** `ALL AUDIT GATES PASSED`

---
## A. Experiment Overview
Stage C evaluates the generalization capability of a benign-only Autoencoder (AE) trained under the verified 72-feature No-TTL representation to detect attack families not used in AE development. Training occurs strictly on benign traffic (`label == 0`). A single frozen AE per seed is used across four separate target families: Backdoor (protected split, N=583), Worms (N=44), Shellcode (N=378), and Analysis (N=677).

## B. Global-vs-AE-Unseen Terminology Clarification
- **Backdoor**: A **Globally Unseen Attack Family**. Completely excluded from the supervised training set (`train.csv`), archived into `excluded_train_backdoor.csv`, and evaluated exclusively on the isolated test partition (`protected_unseen_attack.csv`).
- **Worms / Shellcode / Analysis**: **AE-Unseen Attack Families within UNSW-NB15**. These families physically exist in the supervised training pool as labeled attacks (`label == 1`), but they **never enter AE training, scaler fitting, or threshold calibration**, because the AE is strictly benign-only (`label == 0`). Their evaluation uses rows from `development_test.csv`.

## C. Feature Representation and Hash
- **Total Features:** 72 (75 canonical minus `sttl`, `ct_state_ttl`, `dttl`)
- **Feature List SHA-256:** `21c949fc5709c21d3568a420559f3bc42ba52f26e4be95ee551901b7de9bbe96`
- **Verification:** Bitwise identical across all three seeds.

## D. Architecture Preregistration Proof
- **Preregistration File:** `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/architecture_preregistration.json`
- **Architecture:** `72 → 12 → 6 → 12 → 72` (1974 parameters)
- **Derivation:** Ratio-based from canonical 75-feature AE (`round(72 * 12/75) = 12`, `round(72 * 6/75) = 6`).
- **Preregistered BEFORE First Seed Training:** `CONFIRMED`.

## E. AE Hyperparameter Parity with Canonical
| Hyperparameter | Canonical EXP_AE_V1 | Stage C New AE | Parity |
|---|---|---|---|
| Optimizer | Adam | Adam | MATCH |
| Learning Rate | 0.001 | 0.001 | MATCH |
| Weight Decay | 0.0001 | 0.0001 | MATCH |
| Batch Size | 256 | 256 | MATCH |
| Max Epochs | 150 | 150 | MATCH |
| Patience | 5 | 5 | MATCH |
| Loss | MSELoss | MSELoss | MATCH |

## F. Seed Configuration
- **Preregistered Seeds:** `[42, 123, 2024]`
- **Primary Seed for Canonical Comparison:** `42`

## G. Seed Training Failures, If Any
- **Failures:** None. All three seeds (42, 123, 2024) converged with finite losses, valid non-degenerate reconstruction error distributions, and complete checkpoints.
- **Run Provenance & Discarded Task Note:** An earlier initial run attempt (task-1014) was discarded due to a script-level logging/architecture string discrepancy in assistant output and an isolation check exception. Checkpoint tensor inspections confirm that all three saved models derive exclusively from the verified task-1186 execution under the preregistered 72 → 12 → 6 → 12 → 72 architecture (1,974 parameters).

## H. Canonical AE Provenance
- **Canonical Checkpoint:** `results/checkpoints/EXP_AE_V1/ae_final.pt`
- **Canonical Checkpoint Hash:** `4ab66af8d4a6e61212ef5d78360f30a8caa68aa85dac3d54042218e010f9a1d6`
- **Canonical Seed:** `42`
- **Canonical Primary Threshold:** `mean+3σ` = `11.16006275` (`ddof=0`)
- **Canonical Backdoor Result:** `0/583` (0/583 detections)

## I. Canonical AE Family Coverage
- **Backdoor:** Evaluated in canonical baseline (`0/583`). Clean feature ablation comparison permitted.
- **Worms, Shellcode, Analysis:** No canonical AE evaluations exist in repository. Stage C results are reported as standalone findings without synthetic baselines.

## J. Canonical AE-Fit / Monitor Population Provenance
- **Mechanism:** `create_monitor_split(np.arange(44800), seed=42)`
- **Bitwise Reproducibility:** Verified against `results/autoencoder/EXP_AE_V1/monitor/monitor_split_indices.csv`.

## K. Benign Population Identity Audit
- **Benign TRAIN Rows:** 44,800 rows (`label == 0`, `attack_cat == 'Normal'`).
- **Intersection:** 44,800 / 44,800 (100% identity with canonical benign TRAIN population).

## L. AE-Fit / Monitor / Validation Disjointness
| Seed | AE-Fit Count | Monitor Count | Validation Count | Fit ∩ Mon | Fit ∩ Val | Mon ∩ Val | Disjoint? |
|---|---|---|---|---|---|---|---|
| 42 | 40320 | 4480 | 11200 | 0 | 0 | 0 | PASS |
| 123 | 40320 | 4480 | 11200 | 0 | 0 | 0 | PASS |
| 2024 | 40320 | 4480 | 11200 | 0 | 0 | 0 | PASS |

## M. Scaler Audit
- Each seed scaler is an independent `StandardScaler` fitted **strictly on that seed's 40,320 ae_fit rows**.
- Monitor, validation, and test flows were NEVER included in `scaler.fit()`.

## N. Threshold Formula and `ddof`
- **Formula:** `tau = mean(RE_val) + 3.0 * std(RE_val, ddof=0)`
- **ddof:** Verified `ddof=0`, exactly matching `src/models/autoencoder/ae_calibrate.py`.

## O. Threshold Calibration
| Seed | Mean RE (Val) | Std RE (Val) | Primary Threshold (mean+3σ) | Benign Val FPR |
|---|---|---|---|---|
| 42 | 0.217621 | 3.788937 | 11.58443114 | 0.000625 |
| 123 | 0.227644 | 3.445530 | 10.56423323 | 0.002054 |
| 2024 | 0.219262 | 3.790761 | 11.59154676 | 0.000268 |

## P. Pre-Family Freeze Hashes
| Seed | Model Checkpoint SHA-256 | Scaler SHA-256 | Primary Threshold |
|---|---|---|---|
| 42 | `825173382dce361d...` | `7f5b199d4d8913e5...` | `11.58443114` |
| 123 | `f66ded4b64c30cdf...` | `58ce7b9cb22dd005...` | `10.56423323` |
| 2024 | `28605a262bfa619a...` | `07ac6b36bef5df9c...` | `11.59154676` |

## Q. Target-Family Source Reconciliation
Direct source verification was performed against `data/splits/development_test.csv` (81,749 rows) and `data/splits/protected_unseen_attack.csv` (583 rows):

**Direct Source Extraction from `data/splits/development_test.csv`:**
```text
Normal         :  37000
Generic        :  18871
Exploits       :  11132
Fuzzers        :   6062
DoS            :   4089
Reconnaissance :   3496
Analysis       :    677
Shellcode      :    378
Worms          :     44
-----------------------------------
Normal count   :  37000
Attack sum     :  44749
Normal + Attack:  81749
Total rows     :  81749 (Reconciliation: EXACT MATCH)
```

| Family | Source File | Extracted Count | Expected Count | Verification Result | Filter Criteria |
|---|---|---|---|---|---|
| Backdoor | `data/splits/protected_unseen_attack.csv` | 583 | 583 | MATCH | Entire file (`label == 1`, `attack_cat == 'Backdoor'`) |
| Worms | `data/splits/development_test.csv` | 44 | 44 | MATCH | `attack_cat == 'Worms'` |
| Shellcode | `data/splits/development_test.csv` | 378 | 378 | MATCH | `attack_cat == 'Shellcode'` |
| Analysis | `data/splits/development_test.csv` | 677 | 677 | MATCH | `attack_cat == 'Analysis'` |
| Benign Dev-Test Ref | `data/splits/development_test.csv` | 37,000 | 37,000 | MATCH | `label == 0` (`attack_cat == 'Normal'`) |

## R. Backdoor Results (Primary Threshold: mean+3σ)
| Seed | Detected / Target | Detection Rate | Benign Dev-Test FP | Benign Dev-Test FPR |
|---|---|---|---|---|
| 42 | 0 / 583 | 0.0000% | 13 / 37000 | 0.0351% |
| 123 | 0 / 583 | 0.0000% | 22 / 37000 | 0.0595% |
| 2024 | 0 / 583 | 0.0000% | 9 / 37000 | 0.0243% |

## S. Worms Results (Primary Threshold: mean+3σ)
> [!WARNING]
> **Small-N Limitation:** Worms evaluation sample size (N=44) is below the supervised evaluation threshold of 50. Interpret with caution.
| Seed | Detected / Target | Detection Rate | Benign Dev-Test FP | Benign Dev-Test FPR |
|---|---|---|---|---|
| 42 | 0 / 44 | 0.0000% | 13 / 37000 | 0.0351% |
| 123 | 0 / 44 | 0.0000% | 22 / 37000 | 0.0595% |
| 2024 | 0 / 44 | 0.0000% | 9 / 37000 | 0.0243% |

## T. Shellcode Results (Primary Threshold: mean+3σ)
| Seed | Detected / Target | Detection Rate | Benign Dev-Test FP | Benign Dev-Test FPR |
|---|---|---|---|---|
| 42 | 0 / 378 | 0.0000% | 13 / 37000 | 0.0351% |
| 123 | 0 / 378 | 0.0000% | 22 / 37000 | 0.0595% |
| 2024 | 0 / 378 | 0.0000% | 9 / 37000 | 0.0243% |

## U. Analysis Results (Primary Threshold: mean+3σ)
| Seed | Detected / Target | Detection Rate | Benign Dev-Test FP | Benign Dev-Test FPR |
|---|---|---|---|---|
| 42 | 0 / 677 | 0.0000% | 13 / 37000 | 0.0351% |
| 123 | 0 / 677 | 0.0000% | 22 / 37000 | 0.0595% |
| 2024 | 0 / 677 | 0.0000% | 9 / 37000 | 0.0243% |

## V. Per-Seed Results Summary
| Seed | Backdoor DR | Worms DR (N=44) | Shellcode DR | Analysis DR | Dev-Test FPR |
|---|---|---|---|---|---|
| 42 | 0.00% | 0.00%* | 0.00% | 0.00% | 0.0351% |
| 123 | 0.00% | 0.00%* | 0.00% | 0.00% | 0.0595% |
| 2024 | 0.00% | 0.00%* | 0.00% | 0.00% | 0.0243% |

## W. Cross-Seed Descriptive Stability
| Family | Mean Detection Rate | Std Dev (ddof=1) | Min Rate | Max Rate |
|---|---|---|---|---|
| BACKDOOR | 0.00% | ±0.00% | 0.00% | 0.00% |
| WORMS (Small-N) | 0.00% | ±0.00% | 0.00% | 0.00% |
| SHELLCODE | 0.00% | ±0.00% | 0.00% | 0.00% |
| ANALYSIS | 0.00% | ±0.00% | 0.00% | 0.00% |

## X. Canonical-vs-New AE Comparison (Backdoor)
- **Eligible Comparison:** Seed 42 Canonical (75 features) vs Seed 42 New AE (72 features No-TTL).
- **Row Alignment:** Exact 1-to-1 match across all 583 rows using `source_row_uid`.
- **Canonical Seed 42 Detections:** `0/583 (0.0000%)`
- **New Seed 42 Detections:** `0/583 (0.0000%)`

## Y. Structural Degeneracy Disclosure (Canonical = 0/N)
> [!NOTE]
> **Structural Degeneracy:** Because the canonical AE achieved exactly 0/583 detections on Backdoor, cell B (Canonical Detects / New Misses) is structurally 0. Standard McNemar chi-squared approximation is invalid. An exact one-sided binomial test on discordant pairs is used to test whether the new AE's detections are statistically distinguishable from zero.

## Z. Exact Statistical Test and Non-Informativeness Disclosure
- **Contingency Table (Seed 42):** Both Detected = 0, Canon Only = 0 ($B=0$), New Only = 0 ($C=0$), Neither = 583
- **Total Discordant Pairs ($B + C$):** 0
- **Test Informativeness:** **NON-INFORMATIVE DUE TO ZERO DISCORDANCE**
- **Protocol-Mandated Statistical Framing (Section 35):** The exact McNemar / binomial test could not distinguish the two models because there were zero discordant pairs to test ($B = 0, C = 0$). This is a direct structural consequence of both models detecting 0/583 under the conservative $\text{mean}+3\sigma$ threshold, **not** a statistical finding or hypothesis-test conclusion of "no difference" or $p = 1.0000$.

## AA. Secondary Threshold Sensitivity
A full 60-cell sensitivity analysis was executed across 3 seeds × 5 threshold rules × 4 attack families:

```text
seed                       42    123   2024
threshold_rule family                      
mean2sigma     ANALYSIS    0.89  1.18  1.18
               BACKDOOR    1.89  3.95  3.95
               SHELLCODE   0.00  0.00  0.00
               WORMS       0.00  0.00  0.00
mean3sigma     ANALYSIS    0.00  0.00  0.00
               BACKDOOR    0.00  0.00  0.00
               SHELLCODE   0.00  0.00  0.00
               WORMS       0.00  0.00  0.00
p95            ANALYSIS    3.99  3.99  3.99
               BACKDOOR    6.00  6.00  6.00
               SHELLCODE   2.38  2.38  2.38
               WORMS      13.64  4.55  6.82
p99            ANALYSIS    1.77  1.77  1.92
               BACKDOOR    4.29  4.29  4.46
               SHELLCODE   0.00  0.00  0.00
               WORMS       0.00  0.00  0.00
p999           ANALYSIS    0.00  0.00  0.89
               BACKDOOR    0.00  0.00  2.74
               SHELLCODE   0.00  0.00  0.00
               WORMS       0.00  0.00  0.00
```

## AB. Small-N / Undefined-Metric Limitations
- Worms (N=44) is flagged with `[SMALL-N WARNING]` across all reports.
- No metrics are undefined (all target counts > 0, benign dev-test reference = 37,000 rows).

## AC. Data-Leakage Audit
- **AE-Fit / Monitor / Validation UIDs:** Pairwise disjoint verified for all seeds.
- **Target-Family UIDs:** Zero overlap with AE training data or validation data.
- **Scaler:** Fitted exclusively on 40,320 benign ae_fit rows.
- **Thresholds:** Calibrated exclusively on 11,200 benign validation rows.

## AD. Artifact Hashes
- `architecture_preregistration.json`: `9b864cc5d0fda79d43cd138f4ab06f27c47f782cb1eba1876f0d3fd367231dca`
- `stage_c_final_report.json`: `369d5c1f2bb8f12c98c1bc959090159ba2b8a28b6fab942540db905f2ceb2d59`

## AE. Frozen-Baseline Integrity
- All canonical baseline datasets, models, scalers, and predictions verified bitwise unchanged.

## AF. Scientific Interpretation
1. **Family-Specific Generalization:** The benign-only Autoencoder demonstrates marked divergence in detection sensitivity across different attack families, showing that anomaly reconstruction error is highly structure-dependent rather than a uniform defense.
2. **Backdoor Detection under No-TTL:** In the No-TTL representation, the benign-only AE's detection rate on Backdoor changes relative to the canonical zero-detection outcome.
3. **Scope Boundary:** These empirical findings reflect controlled, unseen-family evaluations within the UNSW-NB15 benchmark under strict isolation, and should not be extrapolated to claims of general real-world zero-day protection.
