# Canonical Experiment Configuration Report
**Sprint:** Sprint 1 — Repository Freeze, Pre-Registration & Reuse Audit  
**Document:** `reports/cicids2017_revision_v1/CANONICAL_EXPERIMENT_CONFIG.md`  
**Governing Rule:** Rule G1 (UNSW Frozen), Rule G6 (No Tuning Toward UNSW Story), Rule G7 (Pre-Registration)  

---

## 1. Structure Overview

This document defines the side-by-side specification between:
1. **Frozen UNSW Baseline:** The exact parameters extracted from code and manifests that generated the accepted paper's numbers.
2. **CIC-IDS2017 Pre-Registered Protocol:** The frozen configuration written to `configs/cicids2017_revision_v1.yaml` prior to touching CIC data.
3. **Pending User Pre-Flight Decisions:** Explicit items awaiting confirmation before subsequent sprints.

---

## 2. Model & Algorithm Specifications

| Component | Frozen UNSW Baseline | CIC-IDS2017 Pre-Registered Protocol | Status / Note |
|---|---|---|:---:|
| **Decision Tree ($M_1$)** | `criterion='entropy'`<br>`max_depth=None`<br>`class_weight='balanced'`<br>`random_state=42` | `criterion='entropy'`<br>`max_depth=None`<br>`class_weight='balanced'`<br>`random_state=42` | Identical (Unchanged) |
| **Random Forest ($M_2$)** | `n_estimators=300`<br>`criterion='gini'`<br>`max_features=0.3` ($mtry = 0.3 \times D$)<br>`bootstrap=True`<br>`class_weight='balanced'`<br>`random_state=42` | `n_estimators=300`<br>`criterion='gini'`<br>`max_features=0.3`<br>`bootstrap=True`<br>`class_weight='balanced'`<br>`random_state=42` | Identical (Unchanged) |
| **Linear SVM ($M_3$)** | `C=0.1`<br>`loss='squared_hinge'`<br>`penalty='l2'`<br>`dual=True/auto`<br>`max_iter=2000`<br>`class_weight='balanced'`<br>`random_state=42` | `C=0.1`<br>`loss='squared_hinge'`<br>`penalty='l2'`<br>`dual='auto'`<br>`max_iter=2000`<br>`class_weight='balanced'`<br>`random_state=42` | Identical (Unchanged) |
| **IDSNet ($M_4$)** | PyTorch MLP: $75 \to 128 \to 64 \to 1$<br>BatchNorm1d + ReLU + Dropout(0.3, 0.2)<br>`Adam(lr=0.001, weight_decay=1e-5)`<br>Loss: `BCELoss`<br>Batch: 256, Epochs: 18 | PyTorch MLP: $D_{\text{in}} \to 128 \to 64 \to 1$<br>BatchNorm1d + ReLU + Dropout(0.3, 0.2)<br>`Adam(lr=0.001, weight_decay=1e-5)`<br>Loss: `BCELoss`<br>Batch: 256, Epochs: 18 | Architecture identical; input dimension parameterized |
| **FT-Transformer ($M_5$)** | Not evaluated in original paper | PyTorch Feature Tokenizer Transformer<br>Evaluated on both UNSW & CIC in Sprint 5 Part B | New comparison for Reviewer Request 2 |
| **OOF Stacking ($C01$)** | 5-fold `StratifiedKFold(shuffle=True, seed=42)`<br>Meta-Learner: `LogisticRegression(C=1.0, balanced)`<br>Threshold: 0.5 | 5-fold `StratifiedKFold(shuffle=True, seed=42)`<br>Meta-Learner: `LogisticRegression(C=1.0, balanced)`<br>Threshold: 0.5 | Identical (Unchanged) |
| **Autoencoder ($C02$)** | Symmetrical bottleneck: $75 \to 12 \to 6 \to 12 \to 75$<br>Loss: `MSELoss`<br>Optimizer: `Adam(lr=0.001, weight_decay=1e-5)`<br>Batch: 128, Max epochs: 150 (patience 15)<br>Internal 90/10 split on benign TRAIN (40,320 fit / 4,480 monitor) | Symmetrical bottleneck: $D_{\text{in}} \to 12 \to 6 \to 12 \to D_{\text{in}}$<br>Loss: `MSELoss`<br>Optimizer: `Adam(lr=0.001, weight_decay=1e-5)`<br>Batch: 128, Max epochs: 150 (patience 15)<br>Internal 90/10 split on benign TRAIN | Architecture identical; input/output dimension parameterized |
| **AE Thresholds** | Primary: $\mu + 3\sigma$ on validation ($\tau = 11.160063$)<br>Quantile: p95 ($\tau = 0.584387$), p99 | Primary: $\mu + 3\sigma$ on CALIBRATION<br>Quantile: p95, p99, robust MAD | Pre-registered methodology identical |
| **Isolation Forest** | `n_estimators=200`, `contamination='auto'`, `seed=42`<br>Fitted on 44,800 pure benign TRAIN | `n_estimators=200`, `contamination='auto'`, `seed=42`<br>Fitted on pure benign TRAIN | Identical (Unchanged) |

---

## 3. Data Engineering & Pre-Registration Protocol

| Dimension | Frozen UNSW Baseline | CIC-IDS2017 Pre-Registered Protocol | Notes / Rationale |
|---|---|---|---|
| **Primary Random Seeds** | Model: `42`, Robustness: `123`, `2024`<br>Partition Split Seed: `20260928` | Model: `42`, Robustness: `123`, `2024`<br>Block Split Seed: `20260928` | Methodological consistency |
| **Partitioning Method** | Deterministic target withholding + Stratified random split | Contiguous 10-minute time-blocks by Timestamp within each day (seeded 20260928) | Prevents temporal leakage across contiguous flows |
| **Headline Zero-Day Family** | Backdoor (583 flows in test set) | PROTECTED_BOT ($\ge 200$ samples required) | Target zero-day test analogue |
| **Supplementary Unseen Families** | Analysis (677 flows, ablation) | UNSEEN_XSS, UNSEEN_INFILTRATION ($\ge 30$ samples) | Evaluated with Clopper-Pearson CIs |
| **Excluded Small Families** | Worms (44 flows in test set, count-only) | EXCLUDED_SMALL ($< 30$ samples, e.g. SQLi, Heartbleed) | Count-only; never trained or thresholded |
| **FPR Operating Budgets** | Empirical validation $\mu+3\sigma$ ($0.0625\%$), p95, p99 | Matched-FPR $\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$<br>Calibrate on CALIBRATION, evaluate on EVAL_CONTROL | Rule G4/Section 4.4 |
| **Operational Metric** | Precision (7.58%), Macro-F1 | Alerts per 10,000 benign flows<br>Standardized precision at natural $\pi = 0.0306$ | Primary cross-dataset operational metric |
| **Feature Selection** | $k$-NN Mutual Information on subsample (seed 42)<br>Selected $K=75$ at complexity plateau ($\Delta < 0.005$) | $k$-NN MI on subsampled TRAIN ($\le 100\text{k}$ rows)<br>Grid: $K \in \{10, 20, 30, 40, 50, 60, \text{ALL}\}$ | Reuses UNSW plateau rule identically |
| **Shortcut Rule** | TTL attributes (`sttl`, `dttl`, `ct_state_ttl`) excised post-hoc | Candidate pool: `Destination Port`, `Init_Win_bytes_forward`, `Init_Win_bytes_backward`, `Flow Duration`. Pre-registered TreeSHAP top-10 rule. | Completely declared and frozen before seeing Bot results |
| **AE Sensitivity Policy** | Standard z-score scaling only | Standard z-score scaling + mandatory `log1p` on heavy-tailed features (skewness > 5, min $\ge 0$) | Controls for massive feature ranges in CIC |

---

## 4. Pending Pre-Flight Decisions

The following parameters are designated `PENDING_USER_CONFIRMATION` in `configs/cicids2017_revision_v1.yaml` to prevent unapproved assumptions:

1. **Decision P2 (Active Submission Format):**
   - LaTeX source (`publication/main_6page.tex`) versus Word document (`FINAL_PAPER.docx`). Needed before Sprint 8 manuscript revision copy is created.
2. **Decision P3 (`heavy_root` Path):**
   - High-capacity directory outside OneDrive (e.g. `D:/ids_data/cicids2017_revision_v1/` or `C:/ids_data/cicids2017_revision_v1/`). Mandatory before Sprint 2 dataset acquisition.
3. **Decision P4 (CIC-IDS2017 Dataset Version):**
   - Engelen et al. corrected CSVs versus original flow CSVs with Timestamp. Mandatory before Sprint 2 download.
4. **Decision P5 (Venue Constraints):**
   - Venue page limit (default 6 pages IEEE format) and revision deadline date.
5. **Author Email Confirmation:**
   - Confirmation of Dr. Juily Tarade's contact email in the manuscript revision copy.
