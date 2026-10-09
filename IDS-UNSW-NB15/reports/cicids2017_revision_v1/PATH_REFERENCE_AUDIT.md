# Path and Reference Audit Report
**Sprint:** Sprint 1 — Repository Freeze, Pre-Registration & Reuse Audit  
**Document:** `reports/cicids2017_revision_v1/PATH_REFERENCE_AUDIT.md`  
**Governing Rule:** Rule G4 (Hardcoded-Path Checker & Decoupling)  

---

## 1. Audit Scope & Methodology

A complete forensic search was conducted across all executable scripts, source modules, and configurations to identify references to UNSW-specific identifiers, sample sizes, thresholds, feature sets, and absolute paths.

Every hit is classified into one of five categories:
1. **Frozen UNSW Execution Logic:** Intentionally retained in legacy UNSW scripts; left unmodified under Rule G1.
2. **Frozen Verification / Replication Metadata:** Test and verification scripts that assert historical correctness; retained as-is.
3. **Documentation / Artifact Text:** Markdown reports and scientific papers describing historical experiments; valid by definition.
4. **Environment / System Artifacts:** Git and IDE configurations containing host paths; excluded from code scans.
5. **Reusable Logic Requiring Parameterization:** Logic copied into `cicids2017/src/` where hardcoded references would cause leakage or runtime failure.

---

## 2. Hardcoded Literal and Identifier Audit

| Identifier / Literal | File Location | Line(s) | Category | Context / Why Present | CIC Adaptation & Recommended Handling |
|---|---|---:|---|---|---|
| `data/raw/UNSW-NB15_*.csv` | `scripts/run_preprocessing.py` | 34 | Frozen UNSW Execution | Ingests 4 raw CSV files of UNSW benchmark. | **Parameterize:** Read from `config['raw_data_dir']` in `cicids2017/src/s02_clean_and_split.py`. |
| `Backdoor` | `scripts/run_train_val_split.py`<br>`scripts/run_base_models.py` | 52<br>88 | Frozen UNSW Execution | Identifies the isolated zero-day family for UNSW. | **Parameterize:** Use `config['populations']['protected_family']` (`PROTECTED_BOT`). |
| `Analysis` | `scripts/run_train_val_split.py` | 54 | Frozen UNSW Execution | Identifies the withheld unseen family for ablation. | **Parameterize:** Use `config['populations']['unseen_families']`. |
| `sttl`, `dttl`, `ct_state_ttl` | `src/features/shortcut_audit.py`<br>`scripts/run_shortcut_analysis.py` | 18<br>42 | Frozen UNSW Execution | UNSW TTL shortcut features identified by TreeSHAP. | **Decouple:** Candidate shortcut pool defined dynamically per Section 4.7 (`Destination Port`, `Init_Win_bytes`, `Flow Duration`). |
| `attack_cat` | `src/preprocessing/cleaner.py`<br>`scripts/run_train_val_split.py` | 48<br>62 | Frozen UNSW Execution | Multiclass column name in UNSW-NB15 schema. | **Parameterize:** Use `config['label_column']` (CIC uses `Label`). |
| `583` | `scripts/verify_publication.py`<br>`scripts/run_fusion_evaluation.py` | 42<br>88 | Frozen Verification / Script | Size of UNSW `protected_unseen_attack.csv` split. | **Dynamic:** Read directly from `len(protected_bot_df)` in evaluation scripts. Flagged by Rule G4. |
| `11.160063` | `scripts/verify_publication.py`<br>`results/.../ae_thresholds.json` | 112<br>5 | Frozen Verification / Result | Parametric Three-Sigma threshold for UNSW AE. | **Dynamic:** Calibrate dynamically on CALIBRATION benign split; save to JSON. Flagged by Rule G4. |
| `37000` | `scripts/run_train_val_split.py`<br>`src/evaluation/thresholds.py` | 88<br>34 | Frozen UNSW Execution | Benign evaluation control size in UNSW `dev_test.csv`. | **Parameterize:** Enforce `min_eval_control_benign: 18500` via YAML. |
| `44800` | `scripts/run_ae_training.py`<br>`publication/main_6page.tex` | 120<br>118 | Frozen UNSW Execution | Total benign flows in UNSW `train.csv`. | **Dynamic:** Use `len(train_benign_df)`. |
| `40320` | `scripts/run_ae_training.py` | 133 | Frozen UNSW Execution | 90% optimization subset for AE fitting. | **Dynamic:** Calculate dynamically via `int(0.9 * len(train_benign))`. Flagged by Rule G4. |
| `162395`, `81749` | `data/audit/split_manifest.json`<br>`scripts/verify_publication.py` | 14<br>28 | Frozen Verification / Manifest | Total rows in UNSW `train.csv` and `dev_test.csv`. | **Dynamic:** Counted at runtime from split manifests. Flagged by Rule G4. |
| `20260928` | `scripts/run_train_val_split.py` | 45 | Frozen UNSW Execution | Seed used for Tier B 18.5k/18.5k control split. | **Preserved:** Reused in `configs/cicids2017_revision_v1.yaml` for cross-dataset methodology parity. |
| `75`, `72` | `src/models/mlp.py`<br>`src/models/autoencoder.py` | 22<br>18 | Reusable Logic (Hardcoded Dim) | Number of one-hot encoded features in UNSW. | **Dynamic Dimension:** Parameterize `d_in = X.shape[1]`. Rule G4 flags assignments `n_features = 75` or `D = 75`. |
| `C:/Users/...` | `.git/config`<br>Scratch logs | 9<br>— | Environment / Metadata | Local user file path on Windows host. | **Decoupled:** All CIC paths constructed via `Path(config['heavy_root'])` or relative to repo root. Rule G4 fails on absolute paths in `cicids2017/src/**/*.py`. |

---

## 3. Enforcement via Automated Checker

To guarantee that no legacy UNSW constants, dataset names, or absolute paths leak into the new revision pipeline, `cicids2017/check_no_hardcoded_paths.py` was constructed and verified.

- **Target Scope:** Scans strictly `cicids2017/src/**/*.py`.
- **Exclusions:** Excludes itself, `configs/`, `reports/`, `tests/`, and legacy UNSW code in `src/` and `scripts/`.
- **Exit Criteria:** Returns exit code `0` on clean trees and exit code `1` with exact line citations whenever a forbidden token or hardcoded dimension literal is detected.
- **Verification Status:** Passed self-test and clean baseline scan.
