# Sprint 1 Final Report — Repository Freeze, UNSW Reconciliation, Pre-Registration & Reuse Audit
**Sprint:** Sprint 1 — Execution Complete  
**Document:** `reports/cicids2017_revision_v1/SPRINT_1_REPORT.md`  
**Execution Timestamp:** 2026-10-05T20:43:00+05:30  
**Overall Status:** **GATE PASSED (16 / 16 Invariants Satisfied)**  

---

## 1. Objective

Sprint 1 was authorized to:
1. Reconcile all historical and on-disk UNSW partition counts and manuscript claims;
2. Formally freeze the completed UNSW study using both a cryptographic SHA-256 manifest and a permanent Git tag;
3. Pre-register all CIC-IDS2017 experimental parameters in YAML prior to acquiring any revision data;
4. Formulate the comprehensive code reuse matrix and path reference audit;
5. Implement and verify the automated hardcoded-reference checker (Rule G4);
6. Document manuscript corrections and environment specs without altering original files.

---

## 2. Repository State at Freeze

- **Repository Root:** `c:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15`
- **Active Branch:** `main`
- **HEAD Commit SHA:** `9a746c425f20b1c097d42e5499c0fc323865c3b7`
- **Commit Message:** `docs(revision_v5): correction 4 -- unverified reflog hash note, excerpt label, blueprint hash typo`
- **Tracked Working Tree Status:** Completely clean (zero unstaged or uncommitted changes on tracked files).
- **Untracked Directories:** `Review_Exp/` (revision master plan).
- **Remote Origin:** `https://github.com/Atulyaam/Papers.git`

---

## 3. UNSW Forensic Reconciliation Results

All historical ambiguities and draft discrepancies have been resolved from primary repository evidence:

1. **Partition Structure Reconciled:**
   - On-disk splits: `train.csv` (162,395 rows), `validation.csv` (11,200 rows), `excluded_train_backdoor.csv` (1,746 rows), `development_test.csv` (81,749 rows), `protected_unseen_attack.csv` (583 rows). Total benchmark: **257,673 rows** (93,000 normal + 164,673 attacks).
   - Proven to match Table I of `publication/main_6page.tex` (Lines 110–126) and audit metadata bit-for-bit.
   - The 119,341 figure in draft notes was traced to `data/audit/label_distribution.json:5` (raw training attack count), which becomes 162,395 once merged with 44,800 benign flows.
2. **Autoencoder Training Size Reconciled:**
   - 44,800 is the total benign partition in `train.csv`.
   - `scripts/run_ae_training.py` applies a 90/10 split: **40,320** rows for gradient fitting, **4,480** rows for early stopping monitoring. Both figures are accurate.
3. **Analysis Family Reconciled:**
   - Canonical Three-Sigma ($\tau = 11.160063$) yields **0 / 677** detected ($0.00\%$, 95% CI $[0.00\%, 0.54\%]$).
   - Exploratory $\mu + 2\sigma$ ($\tau = 7.515109$) yielded **8 / 677** ($1.18\%$).
4. **p95 False Alarm Count Reconciled:**
   - **1,850** was the theoretical nominal budget ($5\% \times 37,000$).
   - **2,080** was the realized empirical false alarm count on EVAL_CONTROL under Seed 42 with $\tau = 0.584387$, detecting 35/583 Backdoors ($6.00\%$).
5. **Stacking Precision Reconciled:**
   - Empirical counts: $582 / (582 + 7,100) = 582 / 7,682 \approx 7.57615\%$.
   - Truncation = 7.57%; standard half-up rounding = **7.58%** (canonical).
6. **Canonical Hyperparameters Confirmed:**
   - DT: `criterion='entropy'`, `balanced`, `seed=42`.
   - RF: `300` trees, `gini`, `max_features=0.3`, `balanced`, `seed=42`.
   - Linear SVM: `C=0.1`, `loss='squared_hinge'`, `penalty='l2'`.
   - IDSNet: 3-layer MLP ($D \to 128 \to 64 \to 1$), `Adam(lr=0.001)`, 18 epochs.
7. **Random Seed Hierarchy Confirmed:**
   - `42` (primary), `123` & `2024` (stability), `20260928` (Tier B partition / block split).

---

## 4. Cryptographic Freeze Manifest & Git Tag

1. **SHA-256 Manifest Created:**
   - Path: [`reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256)
   - Scope: 1,261 files hashed (1.27 GB total), including all gitignored raw data, partition CSVs, model weights, and result logs.
   - Verification Pass: Immediate re-hash confirmed **0 mismatches**.
2. **Git Tag Created:**
   - Tag Name: `unsw_final`
   - Target Commit: `9a746c425f20b1c097d42e5499c0fc323865c3b7`
   - Creation Timestamp: `2026-10-05T20:38:14+05:30`
   - Tag Status: Local tag created; unpushed per protocol.

---

## 5. Summary of Files Created and Untouched

### 5.1 Files Created in Sprint 1
1. [`reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256) (1,261 verified file hashes)
2. [`reports/cicids2017_revision_v1/UNSW_RECONCILIATION.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/UNSW_RECONCILIATION.md) (Full forensic evidence log)
3. [`reports/cicids2017_revision_v1/CODE_REUSE_MATRIX.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/CODE_REUSE_MATRIX.md) (26 capabilities classified A/B/C)
4. [`reports/cicids2017_revision_v1/PATH_REFERENCE_AUDIT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/PATH_REFERENCE_AUDIT.md) (Audit of all UNSW identifiers and literals)
5. [`reports/cicids2017_revision_v1/CANONICAL_EXPERIMENT_CONFIG.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/CANONICAL_EXPERIMENT_CONFIG.md) (UNSW vs CIC side-by-side config)
6. [`reports/cicids2017_revision_v1/MANUSCRIPT_CORRECTIONS.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/MANUSCRIPT_CORRECTIONS.md) (12 staged corrections; zero edits applied)
7. [`reports/cicids2017_revision_v1/ENV.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/ENV.md) (Hardware, host Python 3.13, and .venv diagnostic)
8. [`reports/cicids2017_revision_v1/SPRINT_1_REPORT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/SPRINT_1_REPORT.md) (This summary report)
9. [`configs/cicids2017_revision_v1.yaml`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/configs/cicids2017_revision_v1.yaml) (Master pre-registration YAML)
10. [`cicids2017/check_no_hardcoded_paths.py`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/cicids2017/check_no_hardcoded_paths.py) (Rule G4 AST enforcement tool)

### 5.2 Files Intentionally Untouched (Frozen Scope)
- All original UNSW scripts in `scripts/*.py`
- All original source code in `src/**/*.py`
- All original split files in `data/splits/*.csv`
- All original model checkpoints in `models/checkpoints/*`
- All original experiment results in `publication_experiments/`, `revision_v5/`, and `results/`
- All manuscript sources in `publication/main_6page.tex` and `main_6page.docx`
- Zero CIC data downloaded or processed

---

## 6. Path Checker Verification (Rule G4)

The AST-based path checker was executed and verified:
```bash
python cicids2017/check_no_hardcoded_paths.py --self-test
# Result: Running self-test...
# Self-test passed successfully (self-exclusion verified, test fixture flagged as expected).

python cicids2017/check_no_hardcoded_paths.py
# Result: Files scanned: 0
# PASS: Zero hardcoded paths or forbidden constants found.
```

---

## 7. Pending User Decisions Staged for Later Sprints

In accordance with Section 10, the following items remain explicitly marked `PENDING_USER_CONFIRMATION` in `configs/cicids2017_revision_v1.yaml`:
- **P2:** Active submission format (LaTeX `publication/main_6page.tex` vs Word `FINAL_PAPER.docx`). Staged for Sprint 8.
- **P3:** `heavy_root` directory outside OneDrive (e.g. `D:/ids_data/cicids2017_revision_v1/`). Mandatory before Sprint 2.
- **P4:** CIC-IDS2017 dataset version (Engelen et al. corrected vs original with Timestamp). Mandatory before Sprint 2.
- **P5:** Target venue page limit and revision deadline. Staged for Sprint 8.
- **Author Email:** Confirmation of Dr. Juily Tarade's email address. Staged for Sprint 8.

---

## 8. Sprint 1 Gate Verification

| Check | Requirement | Result | Evidence |
|---|---|:---:|---|
| **1** | Current UNSW state reconciled against final evidence | **PASS** | `train.csv` (162,395), `val` (11,200), `dev` (81,749), `protected` (583) match Table I bit-for-bit. |
| **2** | No UNSW data, model, or result modified | **PASS** | Zero modified files in git status. |
| **3** | Frozen SHA-256 manifest created and re-verified | **PASS** | `reports/.../UNSW_FROZEN_MANIFEST.sha256` verified (1,261 files, 0 mismatches). |
| **4** | `unsw_final` tag created | **PASS** | Tag points to commit `9a746c425f20b1c097d42e5499c0fc323865c3b7`. |
| **5** | `CODE_REUSE_MATRIX.md` complete | **PASS** | 26 capabilities audited (16 A, 6 B, 4 C). |
| **6** | `PATH_REFERENCE_AUDIT.md` complete | **PASS** | Complete audit table distinguishing frozen UNSW from future CIC. |
| **7** | `UNSW_RECONCILIATION.md` complete | **PASS** | All 7 discrepancies forensically resolved with code & manifest citations. |
| **8** | `CANONICAL_EXPERIMENT_CONFIG.md` complete | **PASS** | Baseline UNSW vs pre-registered CIC documented side-by-side. |
| **9** | `MANUSCRIPT_CORRECTIONS.md` complete | **PASS** | 12 staged corrections recorded; zero edits made to manuscript. |
| **10** | `ENV.md` complete | **PASS** | Hardware recorded; host Python 3.13 documented; .venv status noted. |
| **11** | Pre-registration config created in YAML | **PASS** | `configs/cicids2017_revision_v1.yaml` with pending values marked. |
| **12** | Hardcoded reference checker created | **PASS** | `cicids2017/check_no_hardcoded_paths.py` implemented. |
| **13** | Checker self-test passes | **PASS** | Tested self-exclusion and test fixture detection cleanly. |
| **14** | No original UNSW source file edited | **PASS** | Verified via git diff (empty). |
| **15** | No manuscript edited | **PASS** | Verified via git diff (empty). |
| **16** | No dataset downloaded or models trained | **PASS** | Strict execution boundary maintained. |

**SPRINT 1 GATE VERDICT: PASSED**
