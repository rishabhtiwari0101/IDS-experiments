# Code Reuse Matrix — CIC-IDS2017 Revision Pipeline
**Sprint:** Sprint 1 — Repository Freeze, Pre-Registration & Reuse Audit  
**Document:** `reports/cicids2017_revision_v1/CODE_REUSE_MATRIX.md`  
**Governing Rule:** Rule G2 (Reuse-First Policy) & Rule G3 (Copy, never edit in place)  

---

## 1. Classification Scheme

- **Class A (Direct Reuse / Config Only):** The module is mathematically or architecturally dataset-agnostic. Reused via import or configuration parameter change only.
- **Class B (Small Safe Adaptation):** The algorithm and structure are preserved, but thin adaptations are needed for input dimensions, column mappings, or format differences. Copied into `cicids2017/src/` and parameterized.
- **Class C (Genuinely New Implementation):** No reusable code exists in the repository for this capability. Implemented cleanly from scratch under `cicids2017/src/`.

---

## 2. Complete Capabilities Reuse Matrix

| Capability | Existing UNSW File | Function / Class | Class | Rationale for Classification | CIC Adaptation Required |
|---|---|---|:---:|---|---|
| **Raw Ingestion & Multi-CSV Merging** | `src/preprocessing/cleaner.py` | `load_raw_data` | **B** | Ingestion logic is standard pandas, but CIC has 8 separate daily CSVs with header whitespace and non-UTF-8 characters. | Read daily CSVs, strip column whitespace, handle encoding anomalies, generate deterministic `row_uid`. |
| **Data Cleaning & Duplicate Removal** | `src/preprocessing/cleaner.py` | `drop_duplicates_and_nans` | **B** | Standard NaN and duplicate drops, but CIC has `Infinity` in flow rate features and duplicate column names (`Fwd Header Length`). | Replace `+inf/-inf` with NaN, drop conflicting duplicate feature vectors, log audit statistics. |
| **Contiguous Time-Block Splitter** | None | `build_block_splits` | **B** | UNSW used stratified row split; Section 4.3 mandates 10-minute contiguous time blocks by Timestamp. | Group flows by 10-min windows within each day, assign whole blocks via seed 20260928, implement row-level fallback audit. |
| **Categorical OneHotEncoder** | `src/preprocessing/encoder.py` | `FitOneHotEncoder` | **A** | Generic scikit-learn OneHotEncoder wrapper (`handle_unknown='ignore'`). | Configure categorical column names from CIC schema via YAML. |
| **Feature Standardization** | `src/preprocessing/scaler.py` | `StandardScalerWrapper` | **A** | Standard z-score normalization (`StandardScaler`), fitted strictly on TRAIN. | None; pure path/config driven execution. |
| **Heavy-Tail log1p Check** | None | `check_heavy_tail_sensitivity` | **C** | Mandatory AE sensitivity rule (Section 4.8: skewness > 5 and min $\ge 0$). No existing UNSW diagnostic. | Compute skewness on TRAIN numeric features; refit AE pipeline on `log1p` transformed data. |
| **Mutual Information Estimation** | `src/features/mutual_info.py` | `compute_mutual_info` | **A** | Implements $k$-NN mutual information against binary labels on subsampled TRAIN. | Pass $K \in \{10, 20, 30, 40, 50, 60, \text{ALL}\}$ grid via YAML. Subsample $\le 100\text{k}$ rows with seed 42. |
| **Feature Selection (Plateau Rule)** | `src/features/selector.py` | `MutualInfoSelector` | **A** | Evaluates marginal Macro-F1 improvement with stopping rule $\Delta < 0.005$. | Dataset-agnostic; consume MI scores and return selected feature subset. |
| **Decision Tree Classifier** | `src/models/decision_tree.py` | `train_decision_tree` | **A** | Canonical parameters (`criterion='entropy'`, `class_weight='balanced'`, `seed=42`) reused unchanged. | Consume input path and save directory from YAML config. |
| **Random Forest Classifier** | `src/models/random_forest.py` | `train_random_forest` | **A** | Canonical parameters (`300` trees, `gini`, `max_features=0.3`, `bootstrap=True`) reused unchanged. | Consume input path and save directory from YAML config. |
| **Linear SVM Classifier** | `src/models/linear_svm.py` | `train_linear_svm` | **A** | Canonical parameters (`C=0.1`, `loss='squared_hinge'`, `max_iter=2000`) reused unchanged. | Consume input path and save directory from YAML config. |
| **IDSNet / PyTorch MLP** | `src/models/mlp.py` | `IDSNet`, `train_idsnet` | **B** | Architecture (Linear-BN-ReLU-Dropout $\times 2 \to$ Linear-Sigmoid) is generic, but input dimension was hardcoded to 75. | Parameterize input layer dimension $D_{\text{in}} = X_{\text{train}}.\text{shape}[1]$ dynamically. |
| **FT-Transformer Classifier** | None | `FTTransformerClassifier` | **C** | Mandated by Reviewer Request 2 (deep learning / transformer NIDS comparison). No existing implementation. | Implement Feature Tokenizer Transformer in PyTorch for tabular data. Train on both UNSW and CIC for Sprint 5. |
| **OOF Stacking & Meta-Learner** | `src/models/stacking.py` | `train_oof_stacking` | **A** | 5-fold StratifiedKFold + LogisticRegression meta-learner (`C=1.0`, balanced). | Base model inputs dynamically match trained base model outputs. |
| **Bottleneck Autoencoder** | `src/models/autoencoder.py` | `DenseAutoencoder` | **B** | Symmetrical bottleneck architecture is generic, but input/output dimensions were hardcoded to 75. | Parameterize $D_{\text{in}} \to 12 \to 6 \to 12 \to D_{\text{in}}$ dynamically from feature count. |
| **AE Monitor Split** | `scripts/run_ae_training.py` | Lines 120–147 | **A** | Internal 90/10 split on benign TRAIN using `seed=42` for early stopping. | Reused identically on CIC benign TRAIN partition. |
| **Parametric & Quantile Thresholds** | `src/evaluation/thresholds.py` | `compute_parametric_threshold`, `compute_quantile_threshold` | **A** | Computes $\mu+3\sigma$, p95, p99, and robust MAD thresholds. | Pure mathematical functions; evaluate on CALIBRATION benign split. |
| **Isolation Forest Scorer** | `src/models/isolation_forest.py` | `train_isolation_forest` | **A** | Canonical parameters (`200` trees, `contamination='auto'`, `seed=42`) reused unchanged. | Path/config driven. Evaluates out-of-sample anomaly scores. |
| **Matched-FPR Calibration** | `src/evaluation/thresholds.py` | `calibrate_matched_fpr` | **A** | Calibrates thresholds on CALIBRATION for $\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$, computes realized FPR on EVAL_CONTROL. | Generic calibration logic; report low resolution flag if expected false alarms $< 20$. |
| **Operational Alert Burden** | `src/evaluation/metrics.py` | `alerts_per_10k_benign` | **A** | Computes false alarms per 10,000 benign flows and standardized precision at $\pi = 0.0306$. | Pure arithmetic evaluation functions. |
| **ROC & PR Curves** | `src/evaluation/metrics.py` | `evaluate_binary_metrics` | **A** | Generates AUROC, AUPRC, Macro-F1, Precision, Recall, FPR. | Pure evaluation functions; completely dataset-agnostic. |
| **Statistical Hypothesis Tests** | `src/evaluation/statistical_tests.py` | `mcnemar_exact_test`, `holm_bonferroni_correction`, `clopper_pearson_ci`, `wilson_score_interval`, `tost_equivalence_test` | **A** | Mathematical testing functions for H1–H4 (exact McNemar, Holm correction, exact Clopper-Pearson, Wilson score, TOST). | Import directly; zero modification needed. |
| **TreeSHAP Feature Attribution** | `src/explainability/tree_shap.py` | `compute_tree_shap_importances` | **B** | Computes SHAP attributions using `shap.TreeExplainer` on Random Forest background sample of 2,000 rows. | Apply Section 4.7 candidate pool rule (`Destination Port`, `Init_Win_bytes`, `Flow Duration`) to determine frozen shortcuts. |
| **Local Inference Benchmark** | None | `run_inference_benchmark` | **C** | Mandated by Reviewer Request 3 (real-world deployment latency and throughput benchmark). | Measure single-flow latency (p50, p99) and batch-64 throughput (flows/s) on host CPU. |
| **Revision Verification Script** | `scripts/verify_publication.py` | Verification logic | **B** | Asserts all paper numbers against saved result JSON/CSVs. | Replaced by `cicids2017/verify_revision.py` in Sprint 7 to audit CIC results. |
| **Hardcoded Reference Checker** | None | `check_no_hardcoded_paths.py` | **C** | Mandated by Rule G4 to enforce clean decoupling of paths and constants. | Implemented AST-based scanner in `cicids2017/check_no_hardcoded_paths.py`. |

---

## 3. Summary of Reusability

- **Class A (Direct Reuse):** 16 capabilities ($61.5\%$)
- **Class B (Thin Adaptation):** 6 capabilities ($23.1\%$)
- **Class C (New Implementation):** 4 capabilities ($15.4\%$) — specifically: Heavy-Tail log1p Sensitivity Check, FT-Transformer, Deployment Benchmark, and Hardcoded Path Checker.
- **Compliance:** Rule G2 is strictly satisfied; maximum code reuse is achieved without altering any frozen UNSW files.
