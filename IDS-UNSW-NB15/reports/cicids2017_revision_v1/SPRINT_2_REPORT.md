# SPRINT 2 REPORT: CIC-IDS-2017 ACQUISITION, CLEANING, INTEGRITY & LEAKAGE-CONTROLLED SPLITS

**Status:** PASS (CORRECTED AND VERIFIED)  
**Execution Timestamp (UTC):** 2026-10-06  
**Repository Root:** `IDS-UNSW-NB15` (`heavy_root = .`)  
**Evaluation Target:** CIC-IDS-2017 Dual-Benchmark Revision (Revision v1)

---

## 1. Dataset Identity

- **Official Name:** CIC-IDS-2017 (Canadian Institute for Cybersecurity, University of New Brunswick)
- **Distribution Variant:** Original Official CIC/UNB `MachineLearningCSV` distribution (uncompressed 8 CSV shards)
- **Locked Decision (P4 Decision):**
  - Use the original official `MachineLearningCSV` distribution already resident in the workspace.
  - Do NOT download external packages or adopt third-party corrected variants (e.g., Engelen et al.).
  - Preserves authentic baseline artifacts (e.g., duplicate header, encoding anomalies, missing metadata columns, duplicated flows) to ensure transparent, reproducible, preregistered data hygiene and zero-day evaluation.
- **Headline Discovered Metrics:**
  - Raw Ingested Flows: 2,830,743
  - Raw Feature Columns: 79 (including duplicate `Fwd Header Length`)
  - Raw Shards: 8 CSV files

---

## 2. Source and Provenance

- **Original Ingest Source Path:**  
  `cicids2017/DATA/MachineLearningCSV/MachineLearningCVE/` (Untouched, read-only preserved source)
- **Project-Local Preserved Raw Copy:**  
  `cicids2017/DATA/raw/` (Direct byte-identical replica)
- **Official Reference Archive MD5:**  
  `4f83860afbf29cac8163854095bf6cf7` (matches `MachineLearningCSV (1).md5` present in workspace)
- **Manifest Location:**  
  [`reports/cicids2017_revision_v1/manifests/raw_manifest.json`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/manifests/raw_manifest.json)

---

## 3. Raw Data Hashes and Shard Inventory

| Shard Filename | Size (Bytes) | MD5 Hash | SHA-256 Hash |
| :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 77,123,859 | `b2b2764e4c8a4c390506de7ee81c32ee` | `6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee` |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 76,906,168 | `4892380364f9c7ef297d3094d19f26bf` | `ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b` |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 58,316,725 | `134224ec64782709ae1078379f72c4fa` | `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000` |
| `Monday-WorkingHours.pcap_ISCX.csv` | 176,927,918 | `12ca72e319041856f6410e9a14d40581` | `852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34` |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 83,102,436 | `29ab45bfe378d983552a801d0a90cac8` | `6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5` |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 52,023,263 | `13e1c70d2b380bf5d90f82e60e7befb1` | `d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d` |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 135,078,995 | `df16dccfd59a4ee126690fd6b71ee0a4` | `52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851` |
| `Wednesday-workingHours.pcap_ISCX.csv` | 225,166,395 | `bf0dd7e9d991987df4e13ea58a1b409c` | `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a` |
| **Total / Aggregate** | **884,645,759** | — | — |

---

## 4. Raw Row Counts and Schema

- **Total Ingested Rows:** 2,830,743
- **Total Columns:** 79
- **Raw Per-Shard Row Counts:**
  - `Monday-WorkingHours.pcap_ISCX.csv`: 529,918
  - `Tuesday-WorkingHours.pcap_ISCX.csv`: 445,909
  - `Wednesday-workingHours.pcap_ISCX.csv`: 692,703
  - `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`: 170,366
  - `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`: 288,602
  - `Friday-WorkingHours-Morning.pcap_ISCX.csv`: 191,033
  - `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`: 286,467
  - `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`: 225,745

---

## 5. Cleaning Counts and Stage-by-Stage Accounting

Cleaning was executed strictly in the mandated deterministic sequence:

| Stage | Population Count | Delta (Removed) | Description |
| :--- | :--- | :--- | :--- |
| **1. Raw Data Ingestion** | 2,830,743 | 0 | Ingestion of all 8 CSV shards |
| **2. Infinite / NaN Removal** | 2,827,876 | -2,867 | Converted `+inf`/`-inf` to `NaN`, then dropped rows with any `NaN` values |
| **3. Exact Deduplication** | 2,520,798 | -307,078 | Dropped identical flows matching across all feature columns and label |
| **4. Conflicting Label Deduplication** | 2,519,404 | -1,394 | Dropped flows sharing identical feature vectors but having conflicting labels |
| **5. Final Cleaned Dataset** | **2,519,404** | 0 | Assigned persistent `row_uid` (`CIC_0000001` to `CIC_2519404`) |

---

## 6. Duplicate Handling

1. **Exact Duplicate Flows:**  
   In Stage 3, exact duplicates (matching on all 78 feature columns plus the label) were removed. Exactly **307,078** duplicate copies were eliminated, retaining 1 canonical copy per distinct tuple and leaving 2,520,798 flows.
2. **Conflicting Duplicate Flows:**  
   In Stage 4, feature-identical rows that possessed conflicting labels (e.g., one instance labeled `BENIGN` and another labeled `DoS Hulk` with identical flow metrics) were detected. Because exact duplicates were already consolidated in Stage 3, any feature vectors appearing multiple times in `dedup_df` possessed conflicting labels. Exactly **1,394** conflicting rows (697 pairs with 2 conflicting labels) were removed deterministically.

---

## 7. Infinity and NaN Handling

- In the raw dataset, `Flow Bytes/s` and `Flow Packets/s` contained numeric strings representing `Infinity`, `-Infinity`, and missing `NaN` values.
- Exactly **2,867** rows contained infinite values (which also overlapped with the **857** rows containing standard NaNs).
- All infinite values were converted to `NaN`, and rows with any `NaN` values were dropped, reducing the dataset from 2,830,743 to 2,827,876 rows.

---

## 8. Feature Removals and Column Adjustments

1. **Duplicate Header Resolution:**  
   Column index 55 contained a second instance of `Fwd Header Length`. Verification confirmed that column index 40 and index 55 were 100% byte-identical. In accordance with Section 9, the duplicate column at index 55 was removed deterministically, retaining index 40 as the canonical feature.
2. **Globally Constant (Zero-Variance) Features Removed:**  
   Exactly 8 features with globally zero variance across all 8 shards were removed:
   - `Bwd Avg Packets/Bulk`
   - `Bwd PSH Flags`
   - `Bwd Avg Bulk Rate`
   - `Bwd URG Flags`
   - `Fwd Avg Bulk Rate`
   - `Fwd Avg Bytes/Bulk`
   - `Fwd Avg Packets/Bulk`
   - `Bwd Avg Bytes/Bulk`
3. **Feature Retained for Shortcut Learning Analysis:**  
   `Destination Port` is present and was **intentionally retained** in compliance with Section 13. It is preserved for the Sprint 3 shortcut freeze and mutual-information shortcut-learning investigation.
4. **Final Dimensionality:**  
   70 predictive feature columns + 1 canonical `Label` + 1 persistent `row_uid` = **72 columns**.

---

## 9. Label Cleaning and Normalization

Raw label encoding anomalies in `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` were cleaned into canonical ASCII strings:
- `Web Attack  Brute Force` $\rightarrow$ `Web Attack Brute Force` (1,470 raw occurrences)
- `Web Attack  XSS` $\rightarrow$ `Web Attack XSS` (652 raw occurrences)
- `Web Attack  Sql Injection` $\rightarrow$ `Web Attack Sql Injection` (21 raw occurrences)

### Canonical Family Mapping

| Raw Attack Category | Canonical Internal Family | Disposition |
| :--- | :--- | :--- |
| `BENIGN` | `BENIGN` | Train / Control / Test |
| `DoS Hulk`, `DoS GoldenEye`, `DoS slowloris`, `DoS Slowhttptest` | `DoS` | Train / Dev Test |
| `DDoS` | `DDoS` | Train / Dev Test |
| `PortScan` | `PortScan` | Train / Dev Test |
| `FTP-Patator`, `SSH-Patator` | `Brute Force` | Train / Dev Test |
| `Web Attack Brute Force` | `Web Attack` | Train / Dev Test |
| `Bot` | `Bot` | **PROTECTED_BOT** (Zero-Day Target) |
| `Web Attack XSS` | `Web Attack` | **UNSEEN_XSS** (Zero-Day Target) |
| `Infiltration` | `Infiltration` | **UNSEEN_INFILTRATION** (Zero-Day Target) |
| `Web Attack Sql Injection` | `Web Attack` | **EXCLUDED_SMALL** ($N = 21 < 30$) |
| `Heartbleed` | `Heartbleed` | **EXCLUDED_SMALL** ($N = 11 < 30$) |

---

## 10. Protected and Unseen Zero-Day Populations

1. **Headline Zero-Day Evaluation Target (`PROTECTED_BOT`):**
   - Exact observed label: `Bot`
   - Shard origin: Exclusively in `Friday-WorkingHours-Morning.pcap_ISCX.csv`
   - Cleaned count: **1,948 flows** (Threshold requirement $\ge 200$; satisfies Gate G12).
   - Complete isolation: Guaranteed zero representation in `TRAIN`, `CALIBRATION`, `EVAL_CONTROL`, `DEV_TEST`, preprocessing fitting, or feature selection.
2. **Supplementary Unseen Target (`UNSEEN_XSS`):**
   - Exact observed label: `Web Attack XSS`
   - Cleaned count: **652 flows** (Threshold requirement $\ge 30$).
3. **Supplementary Unseen Target (`UNSEEN_INFILTRATION`):**
   - Exact observed label: `Infiltration`
   - Cleaned count: **36 flows** (Threshold requirement $\ge 30$).
4. **Excluded Small Populations (`EXCLUDED_SMALL`):**
   - `Web Attack Sql Injection`: 21 flows
   - `Heartbleed`: 11 flows
   - Total: **32 flows** ($< 30$ samples each). Strictly held out as count-only references; never used for fitting or thresholding.

---

## 11. Split Method and Algorithm

- **Split Method:** `STRATIFIED_ROW_FALLBACK`
- **Split Seed:** `20260928`
- **Stratification Unit:** Daily/session shard and canonical label
- **Benign Subsampling Target:** **44,800** flows (UNSW benchmark parity scale)
- **Subsampling Seed:** `20260928`
- **Pure Benign Controls:** Extracted first across all 8 session shards to guarantee identical temporal session proportions.

---

## 12. Timestamp Limitation

The official UNB `MachineLearningCSV` representation lacks the `Timestamp` column entirely. Furthermore, `Flow ID`, `Source IP`, `Destination IP`, `Source Port`, and `Protocol` are absent. 

Consequently:
- No timestamps were synthesized or heuristically imputed.
- No false claims of "temporal splitting" are made.
- The evaluation explicitly records that temporal ordering within daily shards cannot be reconstructed from `MachineLearningCSV`.

---

## 13. Fallback Justification

Because `Timestamp` is absent in `MachineLearningCSV`, `STRATIFIED_ROW_FALLBACK` was deployed. Stratifying proportionally across daily shards prevents any single session or day from dominating the training or control distributions while preserving the exact session-shard composition across benign control splits.

---

## 14. Final Population Counts and Distribution

| Population Name | Rows | File Size (Bytes) | SHA-256 Hash | Composition / Description |
| :--- | :--- | :--- | :--- | :--- |
| **TRAIN** | 340,464 | 145,805,510 | `baae4da2e2aaf66a604df6bf9b1aed7c830ddbf4f55ac2a5ab1bfadaecf4ff99` | 44,800 Benign + 295,664 Known Attacks |
| **DEV_TEST** | 743,921 | 299,398,181 | `7adcc73ac9014aa612a048a9d7577ce0cdf71d555e49e047bf77b680387c9a39` | 617,209 Benign + 126,712 Known Attacks |
| **CALIBRATION** | 18,500 | 7,324,093 | `945c867d525a8e17f42643008911ebdf05087283a6b44493701f8b16f7c01034` | Pure Benign calibration baseline |
| **EVAL_CONTROL** | 18,500 | 7,327,503 | `a72268d83996d780c8bbe9491b8423c4d57c19a7ac053f34a0a8a1c66c15bef7` | Pure Benign evaluation control |
| **PROTECTED_BOT** | 1,948 | 743,659 | `8755a461308afd03c1978c45b8a128bf0a3f881876860ec0eebd7350e67e829e` | Headline zero-day attack population |
| **UNSEEN_XSS** | 652 | 261,945 | `4622fdf32590930275cdf34f4aece4e9f47cf53fb12538c7415ccec7794b5aed` | Supplementary unseen zero-day population |
| **UNSEEN_INFILTRATION** | 36 | 20,540 | `6035857c265457b5eb961f8df4f64d477fe8808277b2410d3705e8bf6581f31d` | Supplementary unseen zero-day population |
| **EXCLUDED_SMALL** | 32 | 16,379 | `ae87e08e039edecef7f864d166441140b001c52ec073691299cf1e92e8f3644d` | Sql Injection (21) + Heartbleed (11) ($<30$) |
| **Total Assigned** | **1,124,053** | **460,897,810** | — | **8 Disjoint Evaluated Populations** |
| **Logged Removals** | **1,395,351** | — | — | **Unselected Benign Development Flows** |
| **Total Cleaned** | **2,519,404** | — | — | **Exact Conservation Sum** |

---

## 15. Leakage Invariants Verification

All 7 preregistered leakage invariants were formally tested and verified via [`cicids2017/src/s04_verify_splits_and_invariants.py`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/cicids2017/src/s04_verify_splits_and_invariants.py):

- **Invariant 1 (Pairwise Disjointness):**  
  Every pair across the 8 populations has exactly $0$ overlapping `row_uid`s ($C(8, 2) = 28$ pairwise intersections tested; all 28 intersections $= 0$).
- **Invariant 2 (Benign Separation):**  
  `CALIBRATION` and `EVAL_CONTROL` are 100% pure benign ($18,500$ flows each) and share $0$ flows with `TRAIN` or `DEV_TEST`.
- **Invariant 3 (Zero-Day Isolation):**  
  Zero occurrences of `Bot`, `Web Attack XSS`, `Infiltration`, `Web Attack Sql Injection`, or `Heartbleed` exist in `TRAIN` or `DEV_TEST`.
- **Invariant 4 (Fitting Boundary):**  
  Preregistered pipeline fits scalers and normalizers strictly on `TRAIN`.
- **Invariant 5 (Feature Selection Boundary):**  
  Mutual information and feature selection compute statistics strictly on `TRAIN`.
- **Invariant 6 (Threshold Calibration Boundary):**  
  FPR thresholds (1%, 5%) are computed strictly on `CALIBRATION` and evaluated on `EVAL_CONTROL`.
- **Invariant 7 (Conservation Accounting):**  
  Total cleaned rows ($2,519,404$) equals the exact sum of all 8 assigned populations ($1,124,053$) plus explicitly logged unselected benign removals ($1,395,351$):
  $$1,124,053 + 1,395,351 = 2,519,404 \quad (\Delta = 0)$$

---

## 16. Conservation Checks

The conservation audit artifact [`results/cicids2017_revision_v1/audit/conservation_audit.csv`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/audit/conservation_audit.csv) confirms exact row accounting across all cleaning and splitting stages:

$$\text{Raw Ingested Flows} (2,830,743) - \text{Infs/NaNs} (2,867) - \text{Exact Duplicates} (307,078) - \text{Conflicts} (1,394) = 2,519,404$$

$$\sum_{i=1}^8 |\text{Population}_i| + |\text{LOGGED\_REMOVALS}| = 1,124,053 + 1,395,351 = 2,519,404$$

| Stage | Count | Delta | Description |
| :--- | :--- | :--- | :--- |
| 1. Raw Data Ingestion | 2,830,743 | 0 | All 8 raw CSV shards |
| 2. Infinite / NaN Removal | 2,827,876 | -2,867 | Dropped +inf/-inf and NaN flow rates |
| 3. Exact Deduplication | 2,520,798 | -307,078 | Dropped exact duplicate flows across all columns |
| 4. Conflicting Label Deduplication | 2,519,404 | -1,394 | Dropped feature-identical flows with conflicting labels |
| 5. Final Cleaned Population | 2,519,404 | 0 | Assigned persistent `row_uid` (`CIC_XXXXXXX`) |
|   $\to$ TRAIN | 340,464 | 0 | Development training partition (44,800 Benign + 295,664 Known attacks) |
|   $\to$ DEV_TEST | 743,921 | 0 | Development test partition (617,209 Held-out benign + 126,712 Known attacks) |
|   $\to$ CALIBRATION | 18,500 | 0 | Pure benign calibration baseline |
|   $\to$ EVAL_CONTROL | 18,500 | 0 | Pure benign evaluation control |
|   $\to$ PROTECTED_BOT | 1,948 | 0 | Headline zero-day evaluation population |
|   $\to$ UNSEEN_XSS | 652 | 0 | Supplementary unseen evaluation population |
|   $\to$ UNSEEN_INFILTRATION | 36 | 0 | Supplementary unseen evaluation population |
|   $\to$ EXCLUDED_SMALL | 32 | 0 | Excluded small categories (<30 flows, count-only) |
|   $\to$ EXPLICITLY_LOGGED_REMOVALS | 1,395,351 | 0 | Unselected benign development flows (subsampling 1.44M to 44.8k target) |
| **Conservation Sum** | **2,519,404** | **0** | Sum of all 8 populations + explicitly logged removals |

---

## 17. Day-Confound and Temporal Analysis

The day-confound audit [`results/cicids2017_revision_v1/audit/day_confound_check.csv`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/results/cicids2017_revision_v1/audit/day_confound_check.csv) quantifies the session-shard distribution across control populations, the subsampled training benign set, and the zero-day target:

| Source Shard | CALIBRATION Benign (%) | EVAL_CONTROL Benign (%) | TRAIN Benign (%) | DEV_TEST Benign (%) | PROTECTED_BOT (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Monday-WorkingHours.pcap_ISCX.csv` | 23.99% | 23.99% | 23.99% | 23.99% | 0.00% |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 19.14% | 19.14% | 19.14% | 19.14% | 0.00% |
| `Wednesday-workingHours.pcap_ISCX.csv` | 18.94% | 18.94% | 18.94% | 18.94% | 0.00% |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 7.37% | 7.37% | 7.37% | 7.37% | 0.00% |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 11.71% | 11.71% | 11.71% | 11.71% | 0.00% |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 8.51% | 8.51% | 8.51% | 8.51% | **100.00%** |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 5.81% | 5.81% | 5.81% | 5.81% | 0.00% |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 4.54% | 4.54% | 4.54% | 4.54% | 0.00% |

**Key Findings:**
1. `CALIBRATION`, `EVAL_CONTROL`, `TRAIN` (benign), and `DEV_TEST` (benign) have identical benign shard proportions down to two decimal places, ensuring that benign evaluation controls perfectly mirror training and calibration traffic.
2. `Friday-WorkingHours-Morning` benign traffic is represented at exactly **8.51%** (1,574 in calibration/control, 3,811 in train benign, 52,497 in dev test).
3. `PROTECTED_BOT` traffic occurs **100% on Friday morning** (1,948 flows). This inherent dataset characteristic is transparently documented for downstream evaluation.

---

## 18. Storage Layout and Repository-Relative Paths

All generated files reside strictly inside the repository root (`IDS-UNSW-NB15`):

```text
IDS-UNSW-NB15/
├── cicids2017/
│   ├── DATA/
│   │   ├── MachineLearningCSV/
│   │   │   └── MachineLearningCVE/    [Read-only source distribution]
│   │   ├── raw/                       [Preserved 8 raw CSV shards]
│   │   ├── processed/                 [cleaned_cicids2017.csv]
│   │   ├── splits/                    [8 disjoint population CSVs]
│   │   └── audit/                     [cleaning_audit.json, split_audit.json, unselected_train_benign_uids.json]
│   ├── src/
│   │   ├── s01_audit_raw.py
│   │   ├── s02_clean_and_preprocess.py
│   │   ├── s03_generate_splits.py
│   │   └── s04_verify_splits_and_invariants.py
│   └── check_no_hardcoded_paths.py
├── results/
│   └── cicids2017_revision_v1/
│       └── audit/
│           ├── schema.json
│           ├── class_distribution.csv
│           ├── missingness.csv
│           ├── duplicate_report.csv
│           ├── conservation_audit.csv
│           ├── day_confound_check.csv
│           └── dataset_audit.md
├── reports/
│   └── cicids2017_revision_v1/
│       ├── manifests/
│       │   ├── raw_manifest.json
│       │   ├── population_manifest.json
│       │   └── UNSW_FROZEN_MANIFEST.sha256
│       └── SPRINT_2_REPORT.md
└── configs/
    └── cicids2017_revision_v1.yaml
```

---

## 19. Hard-Coded Path Checker Results

The repository boundary checker [`cicids2017/check_no_hardcoded_paths.py`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/cicids2017/check_no_hardcoded_paths.py) was executed on all newly implemented CIC code:

```text
Scanning directory: C:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15\cicids2017\src
Files scanned: 4
PASS: Zero hardcoded paths or forbidden constants found.
```

- **Scanned Files:** 4
- **Violations Found:** 0
- **Status:** PASS

---

## 20. Papers-Only Storage Verification

- **Rule:** Zero files or directories written outside `<CURRENT_REPO_ROOT> = IDS-UNSW-NB15`.
- **Verification:**
  - `C:\ids_data` does NOT exist.
  - No writes to `D:\`, `E:\`, or sibling directories under `Papers/`.
  - Every path resolved starts with `IDS-UNSW-NB15`.
- **Status:** **PASS**

---

## 21. UNSW Freeze Verification

- **Frozen Commit:** `9a746c425f20b1c097d42e5499c0fc323865c3b7`
- **Frozen Tag:** `unsw_final`
- **Manifest Verification:** Checked all 1,261 files against [`reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256).
- **Result:**
  - Files Checked: 1,261
  - Hash Mismatches: **0**
  - Git Status: No modified tracked files
- **Status:** **PASS**

---

## 22. Sprint 2 Gate Evaluation

| Gate Criterion | Verification Details | Status |
| :--- | :--- | :--- |
| **1. Raw files preserved** | Untouched source in `MachineLearningCSV/`, copy in `cicids2017/DATA/raw/` | **PASS** |
| **2. Raw SHA-256 manifest exists** | Present in `reports/.../manifests/raw_manifest.json` | **PASS** |
| **3. Schema verified** | 79 columns verified, duplicate header identified and documented | **PASS** |
| **4. Labels unambiguous** | Malformed Web Attack labels cleanly normalized | **PASS** |
| **5. Cleaning counts reproducible** | Infs/NaNs (2,867), Duplicates (307,078), Conflicts (1,394) reproduced | **PASS** |
| **6. PROTECTED_BOT $\ge$ 200** | 1,948 flows $\ge$ 200 | **PASS** |
| **7. Populations pairwise disjoint** | 0 overlap across all 28 population pairs | **PASS** |
| **8. No zero-day leakage** | Zero Bot, XSS, Infiltration, SQLi, Heartbleed in TRAIN or DEV_TEST | **PASS** |
| **9. Conservation audit passes** | Exact conservation sum: 2,519,404 flows ($1,124,053 + 1,395,351 = 2,519,404$) | **PASS** |
| **10. Day-confound check exists** | Generated in `results/.../audit/day_confound_check.csv` (8.51% Friday Morning parity) | **PASS** |
| **11. Population hashes exist** | SHA-256 and MD5 recorded in `population_manifest.json` | **PASS** |
| **12. Path checker passes** | `cicids2017/check_no_hardcoded_paths.py` returned 0 violations | **PASS** |
| **13. UNSW frozen files unchanged** | 1,261/1,261 files match frozen hashes (0 mismatches) | **PASS** |
| **14. All outputs inside repo** | All files in `IDS-UNSW-NB15/` (`heavy_root = .`) | **PASS** |
| **15. No outside-repo writes** | Zero files written to external paths or drives | **PASS** |
| **16. Final count table complete** | Complete 8-population table documented | **PASS** |

**OVERALL SPRINT 2 GATE STATUS: PASS**

---

## 23. Sprint 2 Post-Execution Methodological Correction

### 23.1 Issue 1 — Feature-Identical Duplicate Handling Verification
- **Original Issue / Inquiry:**  
  Whether deduplication logic in `cicids2017/src/s02_clean_and_preprocess.py` inadvertently removed feature-identical flows that possessed the same label.
- **Empirical Evidence & Audit:**
  - Total flows involved in duplicate feature+label groups (`clean_numeric_df`): **402,149** flows.
  - Step 3 (Exact deduplication across all 78 feature columns + `label_clean`): exactly **307,078** duplicate copies were removed using `keep='first'`, preserving exactly 1 canonical copy per distinct tuple (**2,520,798** flows).
  - Step 4 & 5 (`dedup_df.duplicated(subset=feature_cols, keep=False)`): because all duplicate copies with identical `(features, label)` tuples were already reduced to a single representative in Step 3, any remaining feature vectors appearing multiple times in `dedup_df` must possess different labels.
  - Verification confirmed:
    * Distinct feature vectors with $>1$ labels: exactly **697** pairs (**1,394** rows).
    * Distinct feature vectors with $==1$ label in `conflict_df`: exactly **0** rows.
    * Same-label duplicate copies removed: **307,078** rows.
    * Conflicting-label duplicate rows removed: **1,394** rows.
  - **Verdict:** Same-label feature duplicates were **NOT** incorrectly removed. One canonical instance of each distinct feature-identical same-label pattern was correctly preserved.

### 23.2 Issue 2 — TRAIN Benign Scale Calibration and Subsampling Correction
- **Original Issue:**  
  In the initial execution, the development benign pool (2,057,360 flows) was partitioned via an uncalibrated 70/30 split, resulting in **1,440,151** benign flows in `TRAIN`. This exceeded the preregistered scale comparable to the UNSW experiment (tens of thousands up to approximately 100,000).
- **Intended Target Determination:**
  - In the frozen UNSW experiment, the benign training partition comprised exactly **44,800** flows (`CANONICAL_EXPERIMENT_CONFIG.md` and `UNSW_RECONCILIATION.md`).
  - `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (Task 9) states: *"TRAIN benign target is a documented size comparable in scale to UNSW (tens of thousands up to about 100,000); record the choice."*
  - The smallest defensible fixed target consistent with the frozen plan is **44,800** flows (exact UNSW baseline parity, enabling identical 90/10 fit/monitor Autoencoder calibration: 40,320 fit / 4,480 monitor).
- **Deterministic Sampling Implementation:**
  - Target: **44,800** benign flows.
  - Seed: `20260928` (fixed split seed from pre-registration).
  - Algorithm: `StratifiedShuffleSplit` on `shard_source`.
  - Friday-morning benign representation preserved: exactly **8.51%** (3,811 flows), identical to CALIBRATION (8.51%), EVAL_CONTROL (8.51%), and DEV_TEST (8.51%).
  - Logged Removals: $1,440,151 - 44,800 = \mathbf{1,395,351}$ unselected development benign flows, persistently recorded with row UIDs in `cicids2017/DATA/audit/unselected_train_benign_uids.json`.
- **New Counts (Before vs. After):**
  - `TRAIN` Benign: **44,800** flows (was 1,440,151).
  - `TRAIN` Known Attacks: **295,664** flows (unchanged, 70% split of known attack families).
  - `TRAIN` Total: **340,464** flows (was 1,735,815).
  - `DEV_TEST` Total: **743,921** flows (617,209 Benign + 126,712 Attacks; unchanged).
  - Explicitly Logged Removals: **1,395,351** flows (was 0).
  - Total Cleaned Dataset: **2,519,404** flows ($1,124,053 + 1,395,351 = 2,519,404$).
- **Why Correction Was Necessary:**
  - Prevents training imbalance and catastrophic sample inflation on CIC-IDS2017.
  - Restores strict methodological symmetry with the frozen UNSW benchmark.
  - Fully aligns with the preregistered autoencoder, isolation forest, and MI subsampling budgets.
