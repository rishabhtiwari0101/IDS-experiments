# SPRINT 3 DISCOVERY REPORT — CIC-IDS-2017
## READ-ONLY RECONNAISSANCE & ARCHITECTURAL BLUEPRINT
**Repository**: `IDS-UNSW-NB15`  
**Execution Date**: 2026-10-06  
**Protocol Version**: Revision v1.0 / Master Config 2.0  
**Storage Compliance**: PAPERS-ONLY STRICT CONFINEMENT (`PASS`)  
**UNSW Frozen Tag**: `unsw_final` (commit `9a746c425f20b1c097d42e5499c0fc323865c3b7`)  
**UNSW Integrity**: 1,261 files checked, 0 mismatches (`PASS`)

---

## EXECUTIVE SUMMARY

Sprint 3 Discovery was executed as a strictly **READ-ONLY reconnaissance**. No models were trained, no parameters were fitted, no zero-day attack predictions were generated or inspected, and no files outside or within the frozen benchmark were modified.

The investigation confirms that the verified Sprint 2 population splits and data schema are ready for Sprint 3 execution. All computational dependencies (including `shap 0.51.0`, `torch 2.7.1+cu118` with CUDA enabled, `scikit-learn 1.9.0`, and `pandas 3.0.5`) are already installed and fully operational inside the repository's dedicated virtual environment (`.venv`).

A key architectural difference between UNSW-NB15 and CIC-IDS-2017 has been identified: **CIC-IDS-2017 contains zero categorical features** across its 70 predictive features. The legacy UNSW One-Hot Encoder (`src/preprocessing/encoding.py`) will crash if invoked on empty categorical lists (`ValueError: categorical_cols is empty`). Consequently, categorical encoding must be bypassed, with the 70 continuous numeric flow metrics feeding directly into the `StandardScaler` (`src/preprocessing/scaling.py`).

---

## A. SPRINT 2 STATE (ACTUAL POPULATIONS & HASHES)

### 1. Data Splits & Population Breakdown
All 8 split files in `cicids2017/DATA/splits/` were verified on disk. The population counts and SHA-256 hashes are:

| Population Split | Filename | Row Count | Benign Flows | Attack Flows | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **TRAIN** | `train.csv` | **340,464** | 44,800 | 295,664 | 145,805,510 | `baae4da2e2aaf66a604df6bf9b1aed7c830ddbf4f55ac2a5ab1bfadaecf4ff99` |
| **DEV_TEST** | `dev_test.csv` | **743,921** | 617,209 | 126,712 | 299,398,181 | `7adcc73ac9014aa612a048a9d7577ce0cdf71d555e49e047bf77b680387c9a39` |
| **CALIBRATION** | `calibration.csv` | **18,500** | 18,500 | 0 | 7,324,093 | `945c867d525a8e17f42643008911ebdf05087283a6b44493701f8b16f7c01034` |
| **EVAL_CONTROL** | `eval_control.csv` | **18,500** | 18,500 | 0 | 7,327,503 | `a72268d83996d780c8bbe9491b8423c4d57c19a7ac053f34a0a8a1c66c15bef7` |
| **PROTECTED_BOT** | `protected_bot.csv` | **1,948** | 0 | 1,948 | 743,659 | `8755a461308afd03c1978c45b8a128bf0a3f881876860ec0eebd7350e67e829e` |
| **UNSEEN_XSS** | `unseen_xss.csv` | **652** | 0 | 652 | 261,945 | `4622fdf32590930275cdf34f4aece4e9f47cf53fb12538c7415ccec7794b5aed` |
| **UNSEEN_INFILTRATION** | `unseen_infiltration.csv` | **36** | 0 | 36 | 20,540 | `6035857c265457b5eb961f8df4f64d477fe8808277b2410d3705e8bf6581f31d` |
| **EXCLUDED_SMALL** | `excluded_small.csv` | **32** | 0 | 32 | 16,379 | `ae87e08e039edecef7f864d166441140b001c52ec073691299cf1e92e8f3644d` |
| **UNSELECTED_BENIGN** | `unselected_train_benign_uids.json` | **1,395,351** | 1,395,351 | 0 | 54,420,086 | `868019623cf57d5cb46599298539655f46399990b7e289ec059d282e7bc58df1` |

### 2. Global Row Conservation Proof
- Assigned population rows: $340,464 + 743,921 + 18,500 + 18,500 + 1,948 + 652 + 36 + 32 = \mathbf{1,124,053}$
- Explicitly logged unselected benign removals: $\mathbf{1,395,351}$
- Total accounted flows: $1,124,053 + 1,395,351 = \mathbf{2,519,404}$
- Cleaned dataset rows in `cleaned_cicids2017.csv`: $\mathbf{2,519,404}$
- Discrepancy ($\Delta$): **0 rows (Exact conservation verified)**

### 3. Cleaning Audit Verification
- Raw ingested rows: 2,830,743
- Infinite / NaN rows removed: 2,867 (rows after NaN removal: 2,827,876)
- Exact duplicates removed (features + label identical): 307,078 (rows after exact dedup: 2,520,798)
- Conflicting feature duplicates removed (same features, conflicting labels): 1,394
- Final cleaned rows: 2,519,404
- Global constant zero-variance features dropped (8):
  `['Bwd Avg Packets/Bulk', 'Bwd PSH Flags', 'Bwd Avg Bulk Rate', 'Bwd URG Flags', 'Fwd Avg Bulk Rate', 'Fwd Avg Bytes/Bulk', 'Fwd Avg Packets/Bulk', 'Bwd Avg Bytes/Bulk']`
- Duplicate column `' Fwd Header Length'`: present in raw CSV at columns 34 and 55. Ingested via pandas as `'Fwd Header Length'` and `'Fwd Header Length.1'`.
- Cleaned feature count: **70 predictive features**.

---

## B. PREPROCESSING COMPATIBILITY & REUSE STATUS

### 1. Categorical Encoding (`src/preprocessing/encoding.py`)
- **Inspection Finding**: `fit_encoder` enforces line 93:
  ```python
  if len(categorical_cols) == 0:
      raise ValueError("categorical_cols is empty. At least one categorical column must be specified...")
  ```
- **CIC Schema Fact**: CIC-IDS-2017 has **0 categorical features**. All 70 features are continuous or discrete flow metrics.
- **Handling**: Calling `fit_encoder` will raise an unhandled exception. The CIC pipeline will bypass categorical encoding entirely. The 70 features pass directly into scaling and feature selection.

### 2. Feature Scaling (`src/preprocessing/scaling.py`)
- **Reuse Status**: **Class A (Direct Reuse)**
- **Behavior**:
  - `fit_scaler(X_train, feature_names)` fits `sklearn.preprocessing.StandardScaler` strictly on TRAIN data.
  - Returns `FittedScaler` recording `train_mean` and `train_scale` per feature.
  - `transform_scaler(fitted_scaler, X_val)` applies the TRAIN-fitted transformation without refitting.
  - Fully compliant with TRAIN-only isolation.

---

## C. FEATURE DIMENSIONALITY ACROSS THE PIPELINE

The exact feature dimensions at each stage are:

1. **Raw CSV Columns Ingested**: 78 flow features + 1 raw `'Label'` + metadata = 85 columns.
2. **Post-Cleaning Feature Count**: **70 predictive features**
   - 8 zero-variance features dropped.
   - Duplicate header retained as distinct numeric column (`Fwd Header Length.1`).
   - `Destination Port` retained as predictive feature (index 0).
   - `Timestamp`, `Flow ID`, `Source IP`, `Destination IP`, `Source Port`, `Protocol` confirmed absent.
3. **Scaler Input Dimension**: **70 features** ($D_{\text{raw}} = 70$).
4. **MI Selector Input Dimension**: **70 features** (all continuous; discrete mask = all False).
5. **Inner-CV MI Grid Candidates**: $K \in \{10, 20, 30, 40, 50, 60, \text{'ALL'} (70)\}$.
6. **Post-MI Dimensionality ($D_{\text{selected}}$)**: Determined dynamically by the plateau rule ($\Delta < 0.005$ on inner 5-fold CV). Will be $K^* \in \{10, 20, 30, 40, 50, 60, 70\}$.
7. **Base Model Input Dimension**:
   - Decision Tree: $K^*$ unscaled features.
   - Random Forest: $K^*$ unscaled features.
   - Linear SVM: $K^*$ scaled features.
   - IDSNet (MLP): $K^*$ scaled features.
8. **Stacking Meta-Feature Dimension**: **4 columns** (`dt_attack_probability`, `rf_attack_probability`, `svm_decision_score`, `nn_attack_probability`).
9. **TreeSHAP Input Dimension**: $K^*$ features evaluated on 2,000 stratified TRAIN rows.

> [!IMPORTANT]
> The legacy UNSW codebase contained hardcoded dimensions ($D=75$) in `src/models/base_models/neural_network.py` and `src/models/stacking/oof_runner.py`. The CIC pipeline under `cicids2017/src/` will use **dynamically parameterized input dimensions** derived directly from `X.shape[1]`.

---

## D. MUTUAL INFORMATION FEATURE SELECTION AUDIT

### 1. Components Inspected
- `src/feature_selection/mi_selector.py`
- `src/feature_selection/k_selector.py`
- `scripts/run_mi_feature_selection_v1_1.py`

### 2. Mathematical & Algorithmic Conformance
- **Estimator**: `sklearn.feature_selection.mutual_info_classif(n_neighbors=3, random_state=42)`
- **Discrete Mask**: `build_discrete_mask` in UNSW looked for prefixes `proto_`, `service_`, `state_`. In CIC, no feature has these prefixes, so all 70 features are treated as continuous. This is strictly valid.
- **Subsampling**: Maximum 100,000 rows drawn from TRAIN using a fixed documented seed (seed 42), stratified by binary label.
- **Leakage Isolation**: MI is computed strictly on TRAIN (or inner-train folds). Neither `DEV_TEST`, `CALIBRATION`, nor `EVAL_CONTROL` enter the MI pipeline.
- **Candidate Grid**: $K \in \{10, 20, 30, 40, 50, 60, \text{'ALL'} (70)\}$.
- **Plateau Rule**: Evaluated via 5-fold StratifiedKFold on TRAIN. If $\text{Macro-F1}(K_{i+1}) - \text{Macro-F1}(K_i) < 0.005$, the plateau rule triggers, selecting $K_i$ (parsimony preference). Tie-break chooses smaller $K$.

---

## E. FOUR BASE MODELS: COMPATIBILITY & REQUIRED ADAPTATIONS

| Model | UNSW Implementation Source | Classification | Required Adaptation |
| :--- | :--- | :---: | :--- |
| **Decision Tree** | `src/models/base_models/decision_tree.py` | **Class A** | Reused unchanged. Canonical parameters: `criterion="entropy"`, `class_weight="balanced"`, seeds `[42, 123, 2024]`. |
| **Random Forest** | `src/models/base_models/random_forest.py` | **Class A** | Reused unchanged. Canonical parameters: `n_estimators=300`, `criterion="gini"`, `max_features=0.3`, `bootstrap=True`, `class_weight="balanced"`, `n_jobs=-1`, seeds `[42, 123, 2024]`. |
| **Linear SVM** | `src/models/base_models/linear_svc.py` | **Class A** | Reused unchanged. Canonical parameters: `C=0.1`, `loss="squared_hinge"`, `penalty="l2"`, `class_weight="balanced"`, `max_iter=2000`, seeds `[42, 123, 2024]`. Accepts scaled inputs. |
| **IDSNet / MLP** | `src/models/base_models/neural_network.py` | **Class B** | **Thin Adaptation Required**: UNSW hardcoded `NN_INPUT_DIM = 75` and `TRAIN_POS_WEIGHT = 44800 / 117595`. For CIC, $D_{\text{in}}$ is dynamic ($K^*$), and `pos_weight` is computed from CIC TRAIN counts: $44,800 / 295,664 \approx 0.151523$. Architecture: Input($D$) $\to$ Linear(128) $\to$ BatchNorm $\to$ ReLU $\to$ Dropout(0.3) $\to$ Linear(64) $\to$ BatchNorm $\to$ ReLU $\to$ Dropout(0.2) $\to$ Linear(1) $\to$ Sigmoid. Training: Adam, lr=0.001, weight_decay=1e-5, epochs=18, batch_size=256. |

---

## F. OUT-OF-FOLD (OOF) STACKING & LEAKAGE ASSESSMENT

### 1. Protocol Inspection (`src/models/stacking/oof_runner.py` & `meta_learner.py`)
- **Folds**: 5-fold `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` on full TRAIN.
- **Base Model Outputs**:
  - Decision Tree: `predict_proba()[:, 1]`
  - Random Forest: `predict_proba()[:, 1]`
  - Linear SVM: `decision_function()` (raw unbounded score)
  - IDSNet: `torch.sigmoid(logits)`
- **Meta-Learner**: Fresh `LogisticRegression(C=1.0, solver="lbfgs", class_weight="balanced", max_iter=1000)`.
- **Classification**: **Class B**. The legacy UNSW script hardcoded `OOF_SEED = 7`, `OOF_POS_WEIGHT = 44800 / 117595`, and `NN_INPUT_DIM = 75`. A parameterized script `cicids2017/src/s08_oof_stacking.py` will enforce `seed=42`, dynamic $D_{\text{in}}$, and fresh CIC meta-learner fitting.
- **Leakage Assessment**:
  - Meta-learner is trained **strictly on OOF predictions** generated from out-of-fold partitions.
  - Base models are refitted on 4/5 folds during OOF generation.
  - Final base models are refitted on full TRAIN for subsequent inference.
  - Zero target or evaluation leakage.

---

## G. TREE SHAP COMPATIBILITY

### 1. Implementation Inspection (`scripts/run_sprint11_explainability.py`)
- **Model Supported**: Scikit-learn `RandomForestClassifier` (300 trees).
- **Explainer**: `shap.TreeExplainer(rf_model, feature_perturbation="tree_path_dependent")`.
- **Sampling Specification**: 2,000 stratified rows drawn from TRAIN (seed 42).
- **Execution Speed**: TreeExplainer with tree-path-dependent perturbation operates directly on decision trees without background data permutations, completing in ~2–4 minutes.
- **Package Status**: `shap 0.51.0` is verified installed and functioning in `.venv`.

---

## H. SHORTCUT CANDIDATE POOL & FREEZE RULE

### 1. Predeclared Candidate Pool
The candidate pool is strictly locked to 4 features matching the exact processed CIC column names:
1. `Destination Port` (column 0)
2. `Init_Win_bytes_forward` (column 58)
3. `Init_Win_bytes_backward` (column 59)
4. `Flow Duration` (column 1)

### 2. Deterministic Freeze Algorithm
1. Fit seed-42 Random Forest on full TRAIN ($K^*$ features).
2. Draw 2,000 stratified TRAIN rows using seed 42.
3. Compute TreeSHAP values for all 2,000 samples.
4. Calculate mean absolute SHAP value per feature: $I_j = \frac{1}{2000} \sum_{i=1}^{2000} |\phi_{i,j}|$.
5. Rank features descending by $I_j$.
6. Inspect the top-10 ranked features against the 4 predeclared candidate features.
7. Any candidate feature present in the top-10 is included in the frozen shortcut set.
8. If no candidate feature appears in the top-10, fallback rule selects the top-3 overall features.
9. Serialize the result to `results/cicids2017_revision_v1/shortcut_list_frozen.json` along with its SHA-256 hash.
10. **Zero-Day Blinding Rule**: This freeze occurs **strictly before** evaluating any zero-day set (`PROTECTED_BOT`, `UNSEEN_XSS`, `UNSEEN_INFILTRATION`).

---

## I. REQUIRED NEW CODE & REUSE CLASSIFICATION

All code created for Sprint 3 execution will reside exclusively within `cicids2017/src/` to guarantee that the frozen UNSW codebase (`src/`, `scripts/`, `tests/`) remains completely untouched.

| Target Script Path | Purpose | Source Module Reused | Classification | Safe to Create |
| :--- | :--- | :--- | :---: | :---: |
| `cicids2017/src/s05_train_preprocessing.py` | Fit `StandardScaler` on TRAIN (70 features); serialize scaler & metadata. | `src/preprocessing/scaling.py` | **A / B** | Yes |
| `cicids2017/src/s06_mutual_information.py` | Subsample $\le 100\text{k}$ TRAIN; run 5-fold inner CV; select $K^*$ via plateau rule; export ranking. | `src/feature_selection/mi_selector.py` & `k_selector.py` | **B** | Yes |
| `cicids2017/src/s07_base_models_training.py` | Train DT, RF, SVM, IDSNet on full TRAIN across seeds `[42, 123, 2024]`; serialize checkpoints. | `src/models/base_models/*` | **A (DT/RF/SVM)<br>B (IDSNet)** | Yes |
| `cicids2017/src/s08_oof_stacking.py` | 5-fold StratifiedKFold OOF generation; train fresh LogisticRegression meta-learner across 3 seeds. | `src/models/stacking/*` | **B** | Yes |
| `cicids2017/src/s09_treeshap_shortcut_freeze.py` | Sample 2,000 TRAIN rows; compute TreeSHAP on RF seed 42; apply candidate pool rule; freeze shortcut JSON. | `scripts/run_sprint11_explainability.py` | **B** | Yes |
| `cicids2017/src/s10_evaluate_dev_test.py` | Descriptive evaluation of base models and stacked ensemble on `dev_test.csv` (F1, FPR, confusion matrices). | `src/models/stacking/meta_learner.py` | **A** | Yes |

---

## J. FILES TO BE CREATED / MODIFIED DURING SPRINT 3 EXECUTION

### 1. Files to be Created
- `cicids2017/src/s05_train_preprocessing.py`
- `cicids2017/src/s06_mutual_information.py`
- `cicids2017/src/s07_base_models_training.py`
- `cicids2017/src/s08_oof_stacking.py`
- `cicids2017/src/s09_treeshap_shortcut_freeze.py`
- `cicids2017/src/s10_evaluate_dev_test.py`
- Artifacts under `results/cicids2017_revision_v1/`:
  - `preprocessing/scaler.pkl`
  - `feature_selection/mi_scores.csv`
  - `feature_selection/selected_features.json`
  - `models/` (model weights and checkpoints across seeds 42, 123, 2024)
  - `stacking/oof_predictions.csv`
  - `shortcut_list_frozen.json`
  - `eval_dev_test_results.json`
- Report: `reports/cicids2017_revision_v1/SPRINT_3_REPORT.md`

### 2. Files to be Modified
- **NONE**. No existing file in `src/`, `scripts/`, `configs/`, or `data/` will be modified.

---

## K. COMPUTE ENVIRONMENT & HARDWARE AUDIT

- **Interpreter**: Python 3.11.9 (`.venv\Scripts\python.exe`)
- **Key Packages**:
  - `scikit-learn`: **1.9.0**
  - `torch`: **2.7.1+cu118**
  - `shap`: **0.51.0**
  - `pandas`: **3.0.5**
  - `numpy`: **2.4.6**
- **Hardware**:
  - **CPU**: 13th Gen Intel Core i7-13700H (14 physical cores, 20 logical threads)
  - **System RAM**: 15.63 GB (~16 GB physical RAM)
  - **GPU**: NVIDIA GeForce RTX 3050 Laptop GPU (CUDA available: `True`, 1 device)
  - **Operating System**: Windows 11 64-bit

---

## L. PERFORMANCE & MEMORY RISK ASSESSMENT

1. **In-Memory TRAIN Feature Matrix**:
   - $340,464 \text{ rows} \times 70 \text{ float64 columns} \times 8 \text{ bytes} \approx 190.6 \text{ MB}$.
   - Entire dataset occupies $< 200 \text{ MB}$ of RAM. Multiple in-memory copies take $< 1.5 \text{ GB}$.
2. **Mutual Information (100,000 rows)**:
   - $100,000 \text{ rows} \times 70 \text{ columns} \approx 56 \text{ MB}$.
   - Scikit-learn's `mutual_info_classif` with $n\_neighbors=3$ on 14 CPU cores takes ~1.5 minutes per fold.
   - Total 5-fold inner CV runtime: ~7.5 minutes. RAM footprint: $< 1 \text{ GB}$.
3. **Random Forest (300 trees, 340,464 rows)**:
   - Scikit-learn multi-threaded training (`n_jobs=-1`) takes ~1.5–2 minutes per fit.
   - Memory footprint for 300 deep trees: ~1.5–2 GB. Fits comfortably within 15.6 GB RAM.
4. **IDSNet Training (PyTorch)**:
   - 18 epochs at batch size 256 on RTX 3050 takes ~1 minute. VRAM footprint: $< 200 \text{ MB}$.
5. **5-Fold OOF Stacking**:
   - Sequential fold execution with garbage collection (`gc.collect()`) takes ~15–20 minutes per seed.
   - Peak RAM: ~3.5 GB (out of 15.6 GB).
6. **TreeSHAP on 2,000 Samples**:
   - TreeExplainer on 300 trees across 2,000 rows takes ~2–4 minutes. RAM footprint: $< 500 \text{ MB}$.

**Conclusion**: Memory and compute headroom are abundant. No streaming, memory mapping, or out-of-core chunking is required.

---

## M. LEAKAGE RISKS AUDIT

1. **Scaler Fitting**: Scaler must be fit strictly on `train.csv`. Transforming other splits uses the frozen TRAIN scaler.
2. **MI Feature Selection**: Selection must use inner 5-fold CV on TRAIN rows only. Outer splits are strictly forbidden.
3. **Stacking Meta-Learner**: Meta-learner must be fit strictly on genuine out-of-fold predictions.
4. **TreeSHAP Sampling**: Must sample strictly from TRAIN rows.
5. **Zero-Day Blinding**: Neither `PROTECTED_BOT`, `UNSEEN_XSS`, nor `UNSEEN_INFILTRATION` may be evaluated or inspected before the shortcut list is frozen.

---

## N. BLOCKERS

- **Technical Blockers**: **NONE**.
- **Dependency Blockers**: **NONE** (`shap`, `torch`, `cuda`, `scikit-learn` are fully operational).
- **Integrity Blockers**: **NONE** (UNSW frozen manifest verified with 0 mismatches).

---

## O. RECOMMENDED SPRINT 3 EXECUTION SEQUENCE

When authorized to execute Sprint 3, the execution must proceed in the following strict sequential order:

1. **Step 1: TRAIN Preprocessing** (`cicids2017/src/s05_train_preprocessing.py`)
   - Load `train.csv` (70 features).
   - Fit `StandardScaler` on TRAIN only.
   - Save fitted scaler and feature schema metadata to `results/cicids2017_revision_v1/preprocessing/`.
2. **Step 2: Mutual Information Feature Selection** (`cicids2017/src/s06_mutual_information.py`)
   - Stratified subsample of $\le 100,000$ rows from TRAIN (seed 42).
   - Run 5-fold inner CV across candidate grid $K \in \{10, 20, 30, 40, 50, 60, 70\}$.
   - Apply plateau stopping rule ($\Delta < 0.005$) to select optimal $K^*$.
   - Compute final MI ranking on 100k TRAIN sample; serialize `selected_features.json` and `mi_scores.csv`.
3. **Step 3: Base Models Training Across 3 Seeds** (`cicids2017/src/s07_base_models_training.py`)
   - Train Decision Tree, Random Forest, Linear SVM, and IDSNet on full TRAIN for seeds `42`, `123`, `2024`.
   - Save fitted model checkpoints to `results/cicids2017_revision_v1/models/`.
4. **Step 4: Genuine 5-Fold OOF Stacking** (`cicids2017/src/s08_oof_stacking.py`)
   - Perform 5-fold StratifiedKFold on full TRAIN (seed 42).
   - Generate out-of-fold probability / score predictions for DT, RF, SVM, and IDSNet.
   - Train fresh Logistic Regression meta-learner on assembled OOF matrix for seeds `42`, `123`, `2024`.
   - Save OOF predictions and meta-learner checkpoints to `results/cicids2017_revision_v1/stacking/`.
5. **Step 5: TreeSHAP Shortcut Attribution & Immutable Freeze** (`cicids2017/src/s09_treeshap_shortcut_freeze.py`)
   - Draw 2,000 stratified rows from TRAIN (seed 42).
   - Run `shap.TreeExplainer` on seed-42 Random Forest model.
   - Compute mean absolute attributions and rank features.
   - Check candidate pool (`Destination Port`, `Init_Win_bytes_forward`, `Init_Win_bytes_backward`, `Flow Duration`) against top-10.
   - Determine shortcut set (or top-3 fallback).
   - Save immutable `results/cicids2017_revision_v1/shortcut_list_frozen.json` with SHA-256 hash.
6. **Step 6: Descriptive Base-Model & Stacked Evaluation on DEV_TEST** (`cicids2017/src/s10_evaluate_dev_test.py`)
   - Evaluate base models and stacked ensemble on `dev_test.csv`.
   - Compute Macro-F1, FPR, and confusion matrices across 3 seeds.
7. **Step 7: Verification & Report Generation**
   - Verify all file outputs, SHA-256 hashes, and execution logs.
   - Generate `reports/cicids2017_revision_v1/SPRINT_3_REPORT.md`.
