# SPRINT 4 DISCOVERY REPORT: AUTOENCODER, THRESHOLDS, ZERO-DAY EVALUATION & HYBRID FUSION

**Status:** PASS — NO BLOCKERS  
**Discovery Mode:** READ-ONLY RECONNAISSANCE (Zero training, zero scoring, zero file modifications)  
**Execution Timestamp (UTC):** 2026-10-06  
**Repository Root:** `IDS-UNSW-NB15` (`heavy_root = .`)  
**Evaluation Target:** CIC-IDS-2017 Dual-Benchmark Revision (Revision v1)  

---

## A. Sprint 3 Verification

All Sprint 3 artifacts were read-only verified for presence, non-emptiness, and cryptographic hash integrity:

1. **Immutable Shortcut Freeze:**
   - Artifact: [`results/cicids2017_revision_v1/shortcut_list_frozen.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/shortcut_list_frozen.json)
   - Verified SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2`
   - Creation Timestamp: `2026-10-06T06:44:46.095782+00:00` (strictly precedes zero-day evaluation)
   - Frozen Shortcut Set: `["Destination Port", "Init_Win_bytes_backward"]` ($k_{\text{shortcut}} = 2$)
   - Fallback Triggered: `False`
   - Candidate Pool Attribution:
     - `Destination Port`: Rank 2 (mean $|SHAP| = 0.061522$) $\to$ **INCLUDED**
     - `Init_Win_bytes_backward`: Rank 9 (mean $|SHAP| = 0.024426$) $\to$ **INCLUDED**
     - `Init_Win_bytes_forward`: Rank 17 (mean $|SHAP| = 0.010392$) $\to$ Excluded
     - `Flow Duration`: Rank 45 (mean $|SHAP| = 0.002166$) $\to$ Excluded

2. **Feature Schema & Selection:**
   - Schema: [`results/cicids2017_revision_v1/preprocessing/feature_schema.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/preprocessing/feature_schema.json) ($D=69$, SHA-256: `dd0f83ee...`)
   - Selected Features: [`results/cicids2017_revision_v1/feature_selection/selected_features.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/feature_selection/selected_features.json) ($K^*=69$, SHA-256: `6fc304d0...`)
   - Preprocessing Scaler: [`results/cicids2017_revision_v1/preprocessing/scaler_train_only.pkl`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/preprocessing/scaler_train_only.pkl) (SHA-256: `35e88077...`)

3. **Supervised Model & Stacking Checkpoints:**
   - Base Models: All 18 checkpoints across seeds `[42, 123, 2024]` present in `cicids2017/models/seed_<SEED>/` (`dt_model.pkl`, `rf_model.pkl`, `svm_model.pkl`, `svm_scaler.pkl`, `nn_model.pt`, `nn_scaler.pkl`).
   - Stacking Ensemble: 3 meta-learner models (`meta_lr.pkl`) and 3 OOF prediction CSVs (`oof_predictions_seed42.csv`, `oof_predictions_seed123.csv`, `oof_predictions_seed2024.csv`) present.
   - Leakage Assertions: 100% rows covered, 0 NaN, 0 index overlap verified.

4. **Audit & Report Artifacts:**
   - Verification Record: [`results/cicids2017_revision_v1/audit/sprint3_verification.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/audit/sprint3_verification.json) (`all_invariants_pass: true`).
   - Sprint 3 Report: [`reports/cicids2017_revision_v1/SPRINT_3_REPORT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/SPRINT_3_REPORT.md) (`Status: PASS`).

---

## B. Autoencoder Reuse Audit

The repository contains an established, validated PyTorch autoencoder implementation in `src/models/autoencoder/`:
- `ae_model.py`: Model architecture, forward pass, per-sample MSE reconstruction error.
- `ae_trainer.py`: 90/10 monitor split, Adam optimizer, early stopping, best weights restoration, final refit.
- `ae_calibrate.py`: Calibration error calculation, threshold candidate generation.
- `artifacts.py`: Serialization and artifact hashing.

### B.1 Reuse Classification
**Class B — Thin Adaptation:**
- In the UNSW implementation, input dimensionality was frozen to $D=75$.
- For CIC-IDS-2017, $D = K^* = 69$.
- Adaptation required:
  1. Parameterize `input_dim: int = 69` across `Autoencoder` and `AETrainer`.
  2. Maintain identical layer structure ($D \to 12 \to 6 \to 12 \to D$).
  3. Support arbitrary seeds `[42, 123, 2024]` (UNSW used seed 42 only).
  4. Preserve pure benign training data invariant (44,800 benign TRAIN flows).

### B.2 Architectural Details
- **Activation:** Hidden layers use `ReLU()`. Output layer uses Linear (no activation).
- **Regularization:** Zero BatchNorm, Zero Dropout, Zero VAE latent noise.
- **Loss:** `nn.MSELoss(reduction="mean")`.
- **Per-Sample Reconstruction Error:**
  $$\text{RE}(x) = \frac{1}{D} \sum_{j=1}^D (x_j - \hat{x}_j)^2$$
  *Scalar mean over features per row (NOT sum, NOT MAE, NOT max).*
- **Optimizer:** `Adam(lr=0.001, weight_decay=1e-4)`. Batch size = 256.
- **Early Stopping:** 90% benign fit ($N = 40,320$), 10% monitor ($N = 4,480$). Max epochs = 150, patience = 5. Best monitor MSE weights restored.
- **Phase 2 Refit:** Trained on all 44,800 benign TRAIN rows for exactly `best_epoch` epochs.

---

## C. Required AE Architecture & Exact Parameter Count Formula

The preregistered autoencoder architecture is:
$$\text{Input}(D) \to \text{Linear}(12) \to \text{ReLU} \to \text{Linear}(6) \to \text{ReLU} \to \text{Linear}(12) \to \text{ReLU} \to \text{Linear}(D)$$

### Parameter Count Formula
$$\text{Params}(D) = \underbrace{(12D + 12)}_{\text{Encoder 1}} + \underbrace{(12 \times 6 + 6)}_{\text{Encoder 2}} + \underbrace{(6 \times 12 + 12)}_{\text{Decoder 1}} + \underbrace{(12D + D)}_{\text{Decoder 2}} = 25D + 174$$

### Expected Parameter Counts
- For $D = 75$ (UNSW baseline): $25(75) + 174 = 2,049$ parameters.
- For $D = 69$ (CIC-IDS-2017 baseline):
  $$\text{Params}(69) = 25(69) + 174 = 1,725 + 174 = \mathbf{1,899}\text{ parameters}$$

Layer Breakdown for $D=69$:
- Encoder Layer 1: $69 \times 12 + 12 = 840$
- Encoder Layer 2: $12 \times 6 + 6 = 78$
- Decoder Layer 1: $6 \times 12 + 12 = 84$
- Decoder Layer 2: $12 \times 69 + 69 = 897$
- **Total:** $840 + 78 + 84 + 897 = \mathbf{1,899}$

---

## D. AE Threshold Reuse & Exact Definitions

Reusable threshold logic is located in:
- `src/models/autoencoder/ae_calibrate.py`
- `revision_v5/publication_experiments/scripts/run_mad_threshold.py`

### D.1 Calibration Rules & Population
- All thresholds must be derived **EXCLUSIVELY** on `CALIBRATION`:
  $$N_{\text{CAL}} = 18,500\text{ pure benign flows}$$
- Zero threshold derivations permitted from `DEV_TEST`, `EVAL_CONTROL`, `PROTECTED_BOT`, `UNSEEN_XSS`, or `UNSEEN_INFILTRATION`.

### D.2 Exact Threshold Definitions
Let $\mathcal{R} = \{\text{RE}(x_i)\}_{i=1}^{N_{\text{CAL}}}$ be the reconstruction errors on CALIBRATION:

1. **Primary Parametric Threshold ($\mu + 3\sigma$):**
   $$\tau_{\mu+3\sigma} = \bar{r} + 3 \cdot s, \quad \bar{r} = \frac{1}{N} \sum_{i=1}^N r_i, \quad s = \sqrt{\frac{1}{N} \sum_{i=1}^N (r_i - \bar{r})^2} \quad (\text{ddof}=0)$$
2. **Percentile Thresholds ($p_{95}, p_{99}, p_{99.9}$):**
   $$\tau_{p} = \text{Percentile}(\mathcal{R}, p, \text{method}='linear')$$
3. **Median Absolute Deviation Thresholds (MAD):**
   $$\text{Median} = \text{median}(\mathcal{R}), \quad \text{MAD} = \text{median}(|r_i - \text{Median}|)$$
   - **Raw MAD ($k=3$):** $\tau_{\text{raw\_mad\_k3}} = \text{Median} + 3 \cdot \text{MAD}$
   - **Scaled MAD ($k=3$):** $\tau_{\text{scaled\_mad\_k3}} = \text{Median} + 3 \cdot 1.4826 \cdot \text{MAD}$
   *(Consistency constant $c = 1.4826$ for asymptotic normal consistency).*

---

## E. Heavy-Tail Diagnostic Plan

### E.1 Rationale
In intrusion detection datasets, benign network flows often contain extreme outliers (e.g. massive file transfers, port scans, or keep-alive spikes) that severely inflate the standard deviation $s$, causing $\tau_{\mu+3\sigma}$ to be driven to extreme values and suppressing detection sensitivity.

### E.2 Implementation Structure (Class B / Thin Adaptation)
The diagnostic evaluates the calibration reconstruction error distribution:
1. Full distribution: $\bar{r}$ and $s$.
2. Trimmed distribution: $s_{\text{trimmed}}$ after excluding top 0.1% or top 1% extreme reconstruction errors.
3. Quantiles: $p_{95}$, $p_{99}$, $p_{99.9}$.
4. Diagnostic Ratio:
   $$\text{Ratio} = \frac{\tau_{\mu+3\sigma}}{\tau_{p_{99}}}$$
   - If $\text{Ratio} > 1.5$, severe heavy-tail inflation is diagnosed, demonstrating why $\mu+3\sigma$ fails and confirming the empirical necessity of robust thresholds (MAD, $p_{99}$) and log1p feature transformation.

---

## F. Log1p Sensitivity Analysis

### F.1 Frozen Heavy-Tail Feature Screen
In Sprint 3 Step 1, [`results/cicids2017_revision_v1/preprocessing/log1p_sensitivity_metadata.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/preprocessing/log1p_sensitivity_metadata.json) was generated strictly on TRAIN rows ($N = 340,464$):
- **Rule:** $\text{Skewness} > 5.0$ **AND** $\text{Minimum Value} \ge 0.0$
- **Total Qualifying Features:** **32 features** (e.g. `Total Fwd Packets`, `Total Backward Packets`, `Fwd Packet Length Max`, `Subflow Fwd Bytes`).
- Non-qualifying features: `Destination Port` ($\text{skew} = 4.38 < 5.0$), `Flow Duration` ($\text{min} = -12.0 < 0.0$).

### F.2 Log1p Transformation Protocol
- For the log1p sensitivity variant:
  $$x_j^{(\log1p)} = \begin{cases} \log(1 + x_j), & \text{if } f_j \in \mathcal{F}_{\text{heavy-tailed}} \\ x_j, & \text{otherwise} \end{cases}$$
- A separate `StandardScaler` is fitted **exclusively on log1p-transformed benign TRAIN rows**.
- The AE is retrained on the log1p-scaled benign TRAIN rows across seeds `[42, 123, 2024]`.
- Calibrated on log1p-transformed `CALIBRATION` flows.
- **Strict Isolation Guard:** Supervised models (DT, RF, SVM, IDSNet, Stacking) are **NOT** modified or retrained with log1p. Standard preprocessing remains the canonical headline policy; log1p is an explicit sensitivity analysis.

---

## G. Isolation Forest Reuse Audit

### G.1 Reference Implementation
Located at: `revision_v5/publication_experiments/stage_f/scripts/run_isolation_forest.py`.

### G.2 Configuration & Parameters
- **Algorithm:** `sklearn.ensemble.IsolationForest`
- **Canonical Hyperparameters:**
  - `n_estimators = 200`
  - `contamination = 'auto'`
  - `max_samples = 'auto'`
  - `max_features = 1.0`
  - `random_state = seed` ($[42, 123, 2024]$)
  - `n_jobs = -1`
- **Training Population:** Pure benign TRAIN flows ($N = 44,800$, label = 0).
- **Feature Space:** $D = 69$ features, scaled via the frozen TRAIN benign scaler.
- **Score Convention:**
  $$\text{Score}(x) = - \text{score\_samples}(x) \quad (\text{higher score } = \text{more anomalous})$$
- **Threshold Calibration:** Evaluated on `CALIBRATION` ($N = 18,500$) using $p_{95}, p_{99}, \mu+3\sigma$.

---

## H. Zero-Day Evaluation Data & Schema Audit

All zero-day evaluation files in `cicids2017/DATA/splits/` were verified read-only:

| Split Filename | Total Rows | Target Class | Verified SHA-256 | Features ($D$) | NaN / Inf Count |
| :--- | :---: | :--- | :--- | :---: | :---: |
| `protected_bot.csv` | 1,948 | `Bot` (1,948) | `8755a461308afd03c1978c45b8a128bf0a3f881876860ec0eebd7350e67e829e` | 69 clean | 0 |
| `unseen_xss.csv` | 652 | `Web Attack XSS` (652) | `4622fdf32590930275cdf34f4aece4e9f47cf53fb12538c7415ccec7794b5aed` | 69 clean | 0 |
| `unseen_infiltration.csv` | 36 | `Infiltration` (36) | `6035857c265457b5eb961f8df4f64d477fe8808277b2410d3705e8bf6581f31d` | 69 clean | 0 |
| `eval_control.csv` | 18,500 | `BENIGN` (18,500) | `a72268d83996d780c8bbe9491b8423c4d57c19a7ac053f34a0a8a1c66c15bef7` | 69 clean | 0 |

- **Schema Alignment:** All 4 splits contain identical 75 columns. After dropping `Fwd Header Length.1`, feature columns match the frozen $D=69$ schema perfectly.
- **Headline Zero-Day Mix:**
  $$\text{Headline Mix} = \text{PROTECTED\_BOT } (1,948) + \text{EVAL\_CONTROL } (18,500) = 20,448\text{ flows}$$

---

## I. Zero-Day Evaluation Protocol & Precision Conventions

### I.1 Primary Metrics
For any detector $M \in \{\text{DT}, \text{RF}, \text{SVM}, \text{IDSNet}, \text{Stacking}, \text{AE}, \text{IF}, \text{Hybrid}\}$ evaluated on the zero-day mix:
1. Detections ($k_{\text{det}}$) and Misses ($k_{\text{miss}}$) on zero-day attacks ($N_{\text{attack}}$).
2. **Zero-Day Recall (Detection Rate):** $\text{Recall} = \frac{k_{\text{det}}}{N_{\text{attack}}}$.
3. **Exact Clopper-Pearson 95% Confidence Interval:** $[\text{LB}_{95}, \text{UB}_{95}]$.
4. **Benign False Positive Rate (FPR):** $\text{FPR} = \frac{\text{FP}}{18,500}$ on `EVAL_CONTROL`.
5. **False Alarms per 10k Flows:** $\text{Alerts}/10\text{k} = \text{FPR} \times 10,000$.

### I.2 Dual Precision Reporting
To prevent distortion from artificial experimental class ratios:
1. **Natural-Mix Precision:**
   $$\text{Precision}_{\text{natural}} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
2. **Standardized Prevalence Precision ($\pi = 0.0306$):**
   $$\text{Precision}_{\text{std}} = \frac{\text{Recall} \times \pi}{\text{Recall} \times \pi + \text{FPR} \times (1 - \pi)}$$
   *Reflects the canonical baseline attack prevalence $\pi = 0.0306$ established across the benchmark.*

---

## J. Hybrid Fusion (C01 vs C06) & Partition Invariant

### J.1 Fusion Definitions
- **C01:** Supervised Stacking ensemble at decision threshold $\tau = 0.5$.
- **C06 (Inclusive Logical OR):**
  $$\hat{y}_{\text{C06}}(x) = \hat{y}_{\text{Stacking}}(x) \lor \left(\text{RE}_{\text{AE}}(x) > \tau_{\mu+3\sigma}\right)$$

### J.2 Zero-Day Attack Detections Partition
On `PROTECTED_BOT` ($N = 1,948$), every flow falls into exactly one quadrant:
- **$Q_1$ (Consensus Detect):** Both Stacking and AE detect.
- **$Q_2$ (Stacking Only):** Stacking detects, AE misses.
- **$Q_3$ (AE Rescue):** Stacking misses, AE detects (*the primary rescue metric*).
- **$Q_4$ (Dual Miss):** Both Stacking and AE miss.
- **Exact Conservation Invariant:**
  $$Q_1 + Q_2 + Q_3 + Q_4 = N(\text{PROTECTED\_BOT}) = 1,948$$

### J.3 Benign Control False Alarm Tradeoff
On `EVAL_CONTROL` ($N = 18,500$):
$$\text{FP}_{\text{C06}} = \text{FP}_{\text{Stacking}} \cup \text{FP}_{\text{AE}}$$
$$\text{Incremental False Alarms} = \text{FP}_{\text{C06}} - \text{FP}_{\text{Stacking}}$$

---

## K. Formal Hypothesis Testing (H3 & H4)

### K.1 Hypothesis H3 (AE Failure Under Distribution Shift)
> **Hypothesis H3:** Standalone Autoencoder recall on `PROTECTED_BOT` at $\tau_{\mu+3\sigma}$ is indistinguishable from zero.
- Reusable Tool: `clopper_pearson_ci(k, n, confidence=0.95)`.
- Protocol: Compute observed detections $k$ on $N = 1,948$ Bot flows.
- Reporting Rule: Report $k$, $\text{Recall}$, and exact two-sided 95% Clopper-Pearson interval $[0, \text{UB}_{95\%}]$. If $k=0$, the upper bound $\text{UB}_{95\%}$ defines the maximum plausible detection rate. Never assert true rate is zero without stating the confidence bound.

### K.2 Hypothesis H4 (Hybrid OR-Fusion Rescue Gain)
> **Hypothesis H4:** Inclusive logical OR fusion (C06) adds statistically significant rescue gain over supervised stacking alone ($Q_3 > 0$).
- Reusable Tool: Exact binomial test (`scipy.stats.binomtest(Q3, N, p0=...)`) and McNemar discordant test.
- Primary Quantity: $Q_3$ (number of unobserved attacks rescued by AE).
- Decision Rule: Evaluates whether $Q_3$ provides statistically significant incremental detection beyond the benign false alarm penalty.

---

## L. Statistical Utilities Reuse Matrix

| Capability | Existing Source File | Class | Exact Function / Adaptation |
| :--- | :--- | :---: | :--- |
| **Autoencoder Architecture** | `src/models/autoencoder/ae_model.py` | **B** | Make $D=69$ dynamic; keep $D \to 12 \to 6 \to 12 \to D$ |
| **AE Training Loop** | `src/models/autoencoder/ae_trainer.py` | **B** | 90/10 monitor split on 44,800 benign TRAIN; seeds `[42, 123, 2024]` |
| **AE Thresholds ($\mu+3\sigma, p95, p99$)** | `src/models/autoencoder/ae_calibrate.py` | **B** | Adapt input dimension to 69; calibrate on 18,500 CALIBRATION flows |
| **MAD Threshold Rule** | `revision_v5/.../run_mad_threshold.py` | **A** | Direct reuse: $\text{median} + 3 \cdot \text{MAD}$ and scaled variant ($c=1.4826$) |
| **Heavy-Tail Diagnostic** | New script in Sprint 4 | **C** | Compare $\sigma$ vs trimmed $\sigma$, $p_{99}$, $\mu+3\sigma$, compute ratio |
| **Log1p Transform** | `s05_preflight_and_preprocessing.py` | **B** | Transform the 32 heavy-tailed features; refit scaler on benign TRAIN |
| **Isolation Forest Baseline** | `revision_v5/.../run_isolation_forest.py` | **B** | Reuse `IsolationForest(200, 'auto', 'auto', 1.0)`; seeds 42, 123, 2024 |
| **Zero-Day Evaluator** | `scripts/run_sprint13_zero_day.py` | **B** | Evaluate on `PROTECTED_BOT` (1,948) + `EVAL_CONTROL` (18,500) |
| **Standardized Precision** | `scripts/run_sprint13_zero_day.py` | **A** | Direct reuse: $(\text{Recall} \cdot \pi) / (\text{Recall} \cdot \pi + \text{FPR} \cdot (1-\pi))$ with $\pi=0.0306$ |
| **OR Fusion & Quadrants** | `scripts/run_sprint13_zero_day.py` | **A** | Direct reuse: C01 $\lor$ AE; evaluate $Q_1, Q_2, Q_3, Q_4$ |
| **Clopper-Pearson CI** | `revision_v5/.../run_isolation_forest.py` | **A** | Direct reuse: `scipy.stats.beta.ppf` exact binomial interval |
| **Wilson Score CI** | `scripts/run_sprint13_zero_day.py` | **A** | Direct reuse: `compute_wilson_ci(k, n, alpha=0.05)` |
| **Exact Binomial Test** | `scripts/run_sprint13_zero_day.py` | **A** | Direct reuse: `scipy.stats.binomtest` |
| **McNemar Test** | `revision_v5/.../run_tost_analysis.py` | **A** | Direct reuse: paired discordant contingency test |
| **Holm-Bonferroni Correction**| `revision_v5/.../run_stats_robustness.py`| **A** | Direct reuse: step-down family-wise error adjustment |

---

## M. Model Input Compatibility & Feature Order Verification

All Sprint 4 models and evaluators consume the exact frozen $D=69$ feature order defined in [`results/cicids2017_revision_v1/preprocessing/feature_schema.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/preprocessing/feature_schema.json):
1. **AE Standard:** $D=69$ features transformed by `StandardScaler` fitted on benign TRAIN rows.
2. **AE Log1p:** 32 heavy-tailed features transformed with $\log(1+x)$, remaining 37 untransformed, scaled via a log1p benign TRAIN scaler.
3. **Isolation Forest:** $D=69$ features scaled via the standard benign TRAIN scaler.
4. **Supervised Base Models & Stacking:** Reused from Sprint 3 checkpoints without modification.

---

## N. Environment & Hardware Inventory

- **Python:** 3.11.9 (64-bit AMD64)
- **PyTorch:** 2.7.1+cu118 (CUDA available: `True`)
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM)
- **CPU:** 14 physical cores, 20 logical threads
- **Host RAM:** 15.63 GB Total (3.65 GB Available)
- **Key Packages:** `scikit-learn 1.9.0`, `pandas 3.0.5`, `numpy 2.4.6`, `shap 0.51.0`, `scipy 1.15.2`

---

## O. Compute & Resource Risk Assessment

| Stage | Operation | Workload / Samples | Estimated Compute Time | Memory Risk |
| :--- | :--- | :--- | :---: | :---: |
| **1. AE Training (Standard)** | 3 seeds (42, 123, 2024) | 44,800 rows $\times 69$ features, 150 epochs | ~1.5 – 2.0 min (GPU) | Very Low (< 500 MB) |
| **2. AE Training (Log1p)** | 3 seeds (42, 123, 2024) | 44,800 rows $\times 69$ features, 150 epochs | ~1.5 – 2.0 min (GPU) | Very Low (< 500 MB) |
| **3. Isolation Forest Training**| 3 seeds (42, 123, 2024) | 44,800 rows $\times 69$ features, 200 trees | ~15 – 25 sec (CPU multi-core) | Low (< 1 GB) |
| **4. Threshold Calibration** | CALIBRATION ($N=18,500$) | Forward pass + summary statistics | ~3 – 5 sec | Negligible |
| **5. Zero-Day Inference** | Bot, XSS, Infiltration, Eval | $\approx 21,136$ flows total across models | ~5 – 10 sec | Negligible |
| **6. Hybrid Fusion & Stats** | Quadrants, CIs, Tests | Mathematical summaries | ~2 – 3 sec | Negligible |
| **Total Pipeline** | Full Sprint 4 execution | All steps combined | **~4.0 – 5.5 minutes** | **Zero Risk** |

---

## P. Storage & Path Structure Plan

All outputs will be written strictly inside the workspace repository:
```text
IDS-UNSW-NB15/
├── cicids2017/
│   ├── models/
│   │   ├── seed_42/    (ae_standard.pt, ae_scaler.pkl, ae_log1p.pt, ae_log1p_scaler.pkl, if_model.joblib)
│   │   ├── seed_123/   (ae_standard.pt, ae_scaler.pkl, ae_log1p.pt, ae_log1p_scaler.pkl, if_model.joblib)
│   │   └── seed_2024/  (ae_standard.pt, ae_scaler.pkl, ae_log1p.pt, ae_log1p_scaler.pkl, if_model.joblib)
│   └── src/
│       ├── s12_train_autoencoder.py
│       ├── s13_train_isolation_forest.py
│       ├── s14_calibrate_thresholds_and_heavy_tail.py
│       ├── s15_evaluate_zero_day.py
│       └── s16_hybrid_fusion_and_hypotheses.py
└── results/cicids2017_revision_v1/
    ├── autoencoder/
    ├── isolation_forest/
    ├── heavy_tail/
    ├── zero_day_bot/
    ├── zero_day_unseen/
    ├── hybrid/
    └── statistics/
```

- **UNSW Freeze Status:** **1,261 files, 0 mismatches (PASS)**.
- **Papers-Only Storage Status:** **PASS** (Zero external paths or writes).

---

## Q. Blockers & Preconditions

- **Blockers Identified:** **NONE**.
- **Preconditions Satisfied:**
  - Shortcut freeze sealed and immutable: **YES** (`5e2942c8...`).
  - Zero-day blinding preserved throughout Sprints 1–3: **YES**.
  - All 8 split populations present with verified bit-level hashes: **YES**.
  - Reusable architectures and mathematical formulas audited and verified: **YES**.

---

## R. Recommended Sprint 4 Execution Order

1. **Step 1 — Autoencoder Training (`s12_train_autoencoder.py`):**
   - Fit benign TRAIN scaler on 44,800 benign flows.
   - Train standard AE ($D=69 \to 12 \to 6 \to 12 \to 69$, 1,899 params) across seeds `[42, 123, 2024]`.
   - Fit log1p benign TRAIN scaler (transforming 32 heavy-tailed features).
   - Train log1p sensitivity AE across seeds `[42, 123, 2024]`.
   - Serialize all models, scalers, and training logs.
2. **Step 2 — Isolation Forest Training (`s13_train_isolation_forest.py`):**
   - Train Isolation Forest (`n_estimators=200`, `max_features=1.0`) on standard scaled benign TRAIN across seeds `[42, 123, 2024]`.
   - Serialize models to `cicids2017/models/seed_<SEED>/if_model.joblib`.
3. **Step 3 — Threshold Calibration & Heavy-Tail Diagnostic (`s14_calibrate_thresholds_and_heavy_tail.py`):**
   - Compute reconstruction errors on `CALIBRATION` ($N = 18,500$ pure benign flows).
   - Derive $\tau_{\mu+3\sigma}, \tau_{p95}, \tau_{p99}, \tau_{p99.9}, \tau_{\text{raw\_mad\_k3}}, \tau_{\text{scaled\_mad\_k3}}$.
   - Run heavy-tail diagnostic (ratio of $\mu+3\sigma$ to $p_{99}$, trimmed $\sigma$).
   - Derive Isolation Forest calibration thresholds.
4. **Step 4 — Zero-Day Evaluation (`s15_evaluate_zero_day.py`):**
   - Evaluate base models, Stacking, AE (standard & log1p), and Isolation Forest on `PROTECTED_BOT` (1,948) + `EVAL_CONTROL` (18,500).
   - Also evaluate on `UNSEEN_XSS` (652) and `UNSEEN_INFILTRATION` (36).
   - Compute detection counts, recall, Clopper-Pearson 95% CIs, FPR, alerts/10k, natural precision, and standardized precision ($\pi = 0.0306$).
5. **Step 5 — Hybrid Fusion & Hypothesis Testing (`s16_hybrid_fusion_and_hypotheses.py`):**
   - Evaluate C01 (Stacking @ 0.5) vs C06 (Stacking OR AE @ $\mu+3\sigma$).
   - Compute confusion matrix partition $Q_1, Q_2, Q_3, Q_4$ on `PROTECTED_BOT`.
   - Formal test for H3 (AE recall upper bound) and H4 (rescue gain $Q_3$, binomial/McNemar test).
6. **Step 6 — Post-Execution Invariant Verification & Sprint 4 Report:**
   - Verify UNSW frozen manifest (1,261 files, 0 mismatches).
   - Run Rule G4 code audit on all created scripts.
   - Generate [`reports/cicids2017_revision_v1/SPRINT_4_REPORT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/SPRINT_4_REPORT.md).
