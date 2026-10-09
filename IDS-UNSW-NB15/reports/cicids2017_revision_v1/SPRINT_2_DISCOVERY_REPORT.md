# Sprint 2 Discovery Report — CIC-IDS-2017 Benchmark Evaluation
**Sprint:** Sprint 2 — Read-Only Dataset Reconnaissance  
**Document:** `reports/cicids2017_revision_v1/SPRINT_2_DISCOVERY_REPORT.md`  
**Governing Rule:** Rule G1 (UNSW Frozen), Rule G2 (Reuse-First), Rule G4 (Decoupling), Rule G7 (Pre-Registration)  
**Status:** PASS WITH WARNINGS  

---

## 1. Executive Summary

A comprehensive, strictly read-only forensic discovery was executed on the downloaded CIC-IDS-2017 dataset available to the workspace. All 8 raw CSV shards were inspected without modifying, moving, deleting, extracting, or preprocessing any data.

### Key Headline Findings:
1. **Dataset Package & Variant:** The available dataset is the **original, uncorrected official Canadian Institute for Cybersecurity (CIC) `MachineLearningCSV` distribution** (internally extracted from `MachineLearningCVE.zip`).
2. **Total Scale:** Exactly **2,830,743 rows** and **79 columns** across 8 daily CSV shards (884.65 MB uncompressed).
3. **Labels & Families:** Exactly 15 distinct labels across 8 attack families plus Benign. Benign constitutes 80.30% (2,273,097 flows).
4. **Headline Zero-Day Feasibility:** The planned `PROTECTED_BOT` zero-day evaluation is **HIGHLY FEASIBLE**. The `Bot` attack family consists of exactly **1,966 flows** located exclusively in `Friday-WorkingHours-Morning.pcap_ISCX.csv`. No other attack family exists in that shard, ensuring zero cross-family leakage into training.
5. **Temporal & Timestamp Discovery:** There is **NO `Timestamp` column** in the `MachineLearningCSV` feature representation. Contiguous 10-minute block splitting by timestamp is therefore infeasible without falling back to the pre-registered `STRATIFIED_ROW_FALLBACK` protocol.
6. **Data Quality & Anomalies:**
   - 256,479 duplicate rows (9.06% of the dataset).
   - 2,867 rows affected by infinite values (`+inf`) in `Flow Packets/s` and `Flow Bytes/s`.
   - 857 rows with `NaN` in `Flow Bytes/s`.
   - 8 columns with zero variance (strictly constant `0`) across all 2.83M rows.
   - 1 duplicate column name (`Fwd Header Length` at indices 34 and 55, with identical values).
   - Encoding anomaly in `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` where non-ASCII en-dash was replaced with `\xef\xbf\xbd` (`\ufffd`).
7. **Storage:** Local drive `C:\` has **88.93 GB free**. Storage candidate `C:\ids_data\cicids2017_revision_v1\` is recommended to keep heavy artifacts outside OneDrive. Drive `D:\` is unmounted/not ready.

---

## 2. Dataset Location & Package Inventory

| Attribute | Value / Status |
|---|---|
| **Local Path** | `c:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15\cicids2017\DATA\` |
| **Filesystem Volume** | `C:\` (NTFS Fixed Drive, 88.93 GB free of 525.73 GB) |
| **OneDrive Status** | **INSIDE OneDrive** (`...\OneDrive\Desktop\Papers\...`) |
| **Checksum Reference File** | `MachineLearningCSV (1).md5` (57 bytes) |
| **Official MD5 String** | `4f83860afbf29cac8163854095bf6cf7  MachineLearningCVE.zip` |
| **Local Archive Status** | ZIP file absent; uncompressed directory `MachineLearningCSV/MachineLearningCVE/` present |
| **Alternative Package** | `GeneratedLabelledFlows.zip` is **NOT PRESENT** |

### Complete Shard Inventory

| Shard Filename | Size (Bytes) | Size (MB) | MD5 Hash | SHA-256 Hash |
|---|---:|---:|---|---|
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 77,123,859 | 73.55 | `b2b2764e4c8a4c390506de7ee81c32ee` | `6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee` |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 76,906,168 | 73.34 | `4892380364f9c7ef297d3094d19f26bf` | `ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b` |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 58,316,725 | 55.62 | `134224ec64782709ae1078379f72c4fa` | `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000` |
| `Monday-WorkingHours.pcap_ISCX.csv` | 176,927,918 | 168.73 | `12ca72e319041856f6410e9a14d40581` | `852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34` |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 83,102,436 | 79.25 | `29ab45bfe378d983552a801d0a90cac8` | `6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5` |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 52,023,263 | 49.61 | `13e1c70d2b380bf5d90f82e60e7befb1` | `d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d` |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 135,078,995 | 128.82 | `df16dccfd59a4ee126690fd6b71ee0a4` | `52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851` |
| `Wednesday-workingHours.pcap_ISCX.csv` | 225,166,395 | 214.74 | `bf0dd7e9d991987df4e13ea58a1b409c` | `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a` |
| **TOTAL** | **884,645,759** | **843.66** | — | — |

---

## 3. Schema & Column Discovery

- **Consistency Status:** `COLUMN_SCHEMA_CONSISTENCY: PASS` (All 8 files contain identical 79 column names in identical sequence).
- **Column Count:** 79 total columns (78 feature columns + 1 label column).
- **Header Whitespace:** Raw column headers contain leading whitespace across almost all fields (e.g. `' Destination Port'`, `' Flow Duration'`, `' Label'`).
- **Duplicate Column:** Column index 34 and column index 55 are both named `' Fwd Header Length'`. Numerical comparison across rows confirms they have **100% identical values**.
- **Excluded Metadata:** Network identifiers (`Flow ID`, `Source IP`, `Source Port`, `Destination IP`, `Protocol`) and temporal metadata (`Timestamp`) are **ABSENT** in this release.

---

## 4. Label Inventory & Vocabulary

A full census across all 2,830,743 rows yielded exactly 15 labels:

| Label in Raw CSV | Exact Count | Proportion | Planned Family | Preregistration Category |
|---|---:|---:|---|---|
| `BENIGN` | 2,273,097 | 80.3004% | Benign | Training & Evaluation Baseline |
| `DoS Hulk` | 231,073 | 8.1630% | DoS | Known Attack (Train / Val / Test) |
| `PortScan` | 158,930 | 5.6144% | PortScan | Known Attack (Train / Val / Test) |
| `DDoS` | 128,027 | 4.5227% | DDoS | Known Attack (Train / Val / Test) |
| `DoS GoldenEye` | 10,293 | 0.3636% | DoS | Known Attack (Train / Val / Test) |
| `FTP-Patator` | 7,938 | 0.2804% | Brute Force | Known Attack (Train / Val / Test) |
| `SSH-Patator` | 5,897 | 0.2083% | Brute Force | Known Attack (Train / Val / Test) |
| `DoS slowloris` | 5,796 | 0.2048% | DoS | Known Attack (Train / Val / Test) |
| `DoS Slowhttptest` | 5,499 | 0.1943% | DoS | Known Attack (Train / Val / Test) |
| `Bot` | 1,966 | 0.0695% | Bot | **PROTECTED_BOT (Zero-Day Target)** |
| `Web Attack \ufffd Brute Force` | 1,507 | 0.0532% | Web Attack | Known Attack (Train / Val / Test) |
| `Web Attack \ufffd XSS` | 652 | 0.0230% | Web Attack | **UNSEEN_XSS (Supplementary)** |
| `Infiltration` | 36 | 0.0013% | Infiltration | **UNSEEN_INFILTRATION (Supplementary)** |
| `Web Attack \ufffd Sql Injection` | 21 | 0.0007% | Web Attack | **EXCLUDED_SMALL (< 30)** |
| `Heartbleed` | 11 | 0.0004% | Heartbleed | **EXCLUDED_SMALL (< 30)** |

---

## 5. Temporal Structure & Shard Distribution

| Shard | Available Day & Session | Attack Classes Present | Benign Flows | Attack Flows |
|---|---|---|---:|---:|
| `Monday-WorkingHours` | Monday Full Day | Pure Benign baseline | 529,918 | 0 |
| `Tuesday-WorkingHours` | Tuesday Full Day | `FTP-Patator`, `SSH-Patator` | 432,074 | 13,835 |
| `Wednesday-workingHours` | Wednesday Full Day | `DoS Hulk`, `GoldenEye`, `slowloris`, `Slowhttptest`, `Heartbleed` | 440,031 | 252,672 |
| `Thursday-Morning` | Thursday Morning | `Web Attack (Brute Force, XSS, SQLi)` | 168,186 | 2,180 |
| `Thursday-Afternoon` | Thursday Afternoon | `Infiltration` | 288,566 | 36 |
| `Friday-Morning` | Friday Morning | `Bot` | 189,067 | 1,966 |
| `Friday-Afternoon-PortScan` | Friday Afternoon Session 1 | `PortScan` | 127,537 | 158,930 |
| `Friday-Afternoon-DDos` | Friday Afternoon Session 2 | `DDoS` | 97,718 | 128,027 |

---

## 6. Zero-Day Feasibility Assessment (Bot Protection)

- **Target Candidate:** `Bot` (N = 1,966).
- **Preregistration Criterion:** Headline zero-day family must have $N \ge 200$. Here $N = 1,966 \gg 200$, passing comfortably.
- **Isolation Feasibility:** `Bot` appears **exclusively** on Friday Morning (`Friday-WorkingHours-Morning.pcap_ISCX.csv`). It does not appear in any other shard or day.
- **Leakage Prevention:** By completely isolating Friday Morning from training, zero Bot samples or related Friday-morning activity can contaminate training.
- **Supplementary Unseen Feasibility:**
  - `UNSEEN_XSS`: $N = 652 \ge 30$ (Passes supplementary threshold).
  - `UNSEEN_INFILTRATION`: $N = 36 \ge 30$ (Passes supplementary threshold).
  - `EXCLUDED_SMALL`: `Sql Injection` ($N = 21 < 30$) and `Heartbleed` ($N = 11 < 30$) are excluded from training and headline scoring, evaluated as count-only as preregistered.

---

## 7. Data Quality Audit & Artifacts

1. **Missing Values (`NaN`):**
   - Strictly confined to `Flow Bytes/s`: 138 rows on Tuesday, 719 rows on Wednesday (Total: 857 rows).
   - Zero NaNs across all other 78 columns.
2. **Infinite Values (`+inf`):**
   - Strictly confined to flow rate calculations (`Flow Bytes/s`: 1,509 rows; `Flow Packets/s`: 2,867 rows).
   - Caused by zero flow duration (`Flow Duration == 0`) with non-zero bytes/packets.
3. **Duplicate Rows:**
   - 256,479 exact duplicate rows across all 79 columns (9.06% of the dataset).
   - Highest concentration in `PortScan` (72,353 duplicates, 25.26%) and `Wednesday` (81,909 duplicates, 11.82%).
4. **Constant (Zero Variance) Columns:**
   - 8 columns are strictly 0 across all 2,830,743 rows:
     `Bwd Avg Packets/Bulk`, `Bwd PSH Flags`, `Bwd Avg Bulk Rate`, `Bwd URG Flags`, `Fwd Avg Bulk Rate`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Bwd Avg Bytes/Bulk`.
   - 2 additional columns (`CWE Flag Count`, `Fwd URG Flags`) are constant 0 across 7 files, but contain 315 positive values in Thursday Afternoon.

---

## 8. Leakage & Shortcut Pre-Audit

### Investigation of Pre-Registered Shortcut Candidate Pool:
1. **`Destination Port` (HIGH RISK):**
   - `DDoS`: 99.998% targeting port 80.
   - `DoS (Hulk, GoldenEye, slowloris, Slowhttptest)`: 100% targeting port 80.
   - `Web Attacks (Brute Force, XSS, SQLi)`: 100% targeting port 80.
   - `FTP-Patator`: 99.99% targeting port 21.
   - `SSH-Patator`: 100% targeting port 22.
   - `Infiltration` & `Heartbleed`: 100% targeting port 444.
   - `Bot`: Distributed across 706 unique ports (port 8080 = 64.1%, mean port = 17,784).
   - *Implication:* Models trained with `Destination Port` can achieve near-perfect classification on training attacks via port memorization alone, but will fail to generalize to zero-day attacks running on arbitrary ports. This directly supports our hypothesis H1/H2 shortcut investigation.
2. **`Init_Win_bytes_forward` & `Init_Win_bytes_backward` (MEDIUM-HIGH RISK):**
   - Benign flows are dominated by `-1` (non-TCP or capture initialization artifact), whereas attacks exhibit distinct fixed TCP window sizes.
3. **`Flow Duration` (MEDIUM RISK):**
   - DoS/DDoS show characteristic multi-second durations, whereas benign flows concentrate at sub-millisecond durations.
4. **Duplicate Column `Fwd Header Length` (LOW RISK):**
   - Perfect collinearity; should be deduplicated during cleaning.

---

## 9. Model Architecture & Dimensionality Compatibility

- **UNSW Legacy Assumption:** Existing UNSW pipeline produced 75 one-hot encoded features (`IDSNet` and `Autoencoder` had hardcoded input dimensions of 75).
- **CIC-IDS-2017 Dimensionality:** 78 numerical features (or 77 if duplicate `Fwd Header Length` is removed; 67 if 10 zero-variance columns are removed).
- **Adaptation Requirement:**
  - `IDSNet` MLP: Parameterize $D_{\text{in}} = X_{\text{train}}.\text{shape}[1]$ (Class B adaptation).
  - `DenseAutoencoder`: Parameterize $D_{\text{in}} \to 12 \to 6 \to 12 \to D_{\text{in}}$ (Class B adaptation).
  - Automated path & constant checker (`cicids2017/check_no_hardcoded_paths.py`) passed and will enforce clean decoupling.

---

## 10. Storage / Heavy Root Analysis

- **Drive `C:\`:** Ready, 88.93 GB available space.
- **Drive `D:\`:** Not ready (unmounted).
- **OneDrive Risk:** Writing multi-GB intermediate splits, OOF predictions, and model checkpoints to `c:\Users\Atul2\OneDrive\...` risks sync throttles and high disk churn.
- **Recommended Candidate:** `C:\ids_data\cicids2017_revision_v1\`
- **Status:** `HEAVY_ROOT STATUS: CANDIDATE` (Awaiting user confirmation before creation).

---

## 11. Pre-Registration Consistency Check

| Preregistered Item | Status | Finding / Action Required |
|---|:---:|---|
| Contiguous time blocks (10-min) | **PREREGISTRATION CONFLICT** | `Timestamp` column is absent in `MachineLearningCSV`. |
| Fallback `STRATIFIED_ROW_FALLBACK` | **COMPATIBLE** | Pre-registered fallback handles missing timestamps via daily stratification. |
| Leakage-controlled preprocessing | **COMPATIBLE** | Pipeline ready. Zero categorical columns; scaling strictly fit on TRAIN. |
| TRAIN-only Scaler / MI selection | **COMPATIBLE** | Standard z-score and $k$-NN MI evaluated on TRAIN only. |
| Model Suite ($M_1, M_2, M_3, M_4, M_5, C01, C02, \text{IF}$) | **COMPATIBLE** | Algorithms dataset-agnostic; PyTorch MLP & AE require $D_{\text{in}}$ parameterization. |
| Bot Zero-Day Evaluation | **COMPATIBLE** | $N = 1,966$ flows, isolated to Friday Morning. Clean zero-day testbed. |
| Matched-FPR Calibration ($\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$) | **COMPATIBLE** | Calibration on CALIBRATION benign partition, evaluation on EVAL_CONTROL. |
| Multi-Seed Robustness (42, 123, 2024) | **COMPATIBLE** | Full 3-seed evaluation feasible. |
