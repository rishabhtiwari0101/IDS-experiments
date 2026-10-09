# DOC-08: Protocol Timing, Predeclaration Audit, and Preregistration Trace

**Date:** 2026-09-28  
**Scope:** Revision 5 (`revision_v5`) Publication Experiments  
**Governing Authority:** [`docs/IMPLEMENTATION_BLUEPRINT_v5.md`](IMPLEMENTATION_BLUEPRINT_v5.md) (§0 Rule 8, Rule 14, Rule 15; §16; §17)  

---

## 1. Governing Preregistration Principles

Per blueprint §0 Controlling Protocol Constraints:
1. **Evidence-Constrained Claims (§0 Rule 8):** *"Predeclared" may be used only where Git history or contemporaneous records show the criterion preceded the relevant result. Anything created after results were available is described as post-hoc, regardless of filename.*
2. **Protocol Configuration Freeze (§0 Rule 14):** *Protocol-defining configs are committed to Git before the script that reads them is executed. This applies to populations, calibration source, calibration rules and budgets, seeds, metric definitions, curve-aggregation rules, the equivalence margin, and MAD k values.*
3. **Headline Tier Decision Rule (§0 Rule 15):** *The identical text of the headline-tier decision rule is committed in `matched_fpr.yaml` before S3 runs. A cell is shift-affected if nominal budget lies outside the Clopper-Pearson 95% CI of the realized Tier-A held-out control FPR. S3 writes the outcome to `headline_tier_decision.json`.*
4. **Post-Hoc Equivalence Margin Disclosure (§0 Rule 7):** *Because the paired counts (582, 0, 0, 1) were already known from earlier sprint reports when the margin was chosen, the manuscript must describe the margin as specified after the paired data were observed (post-hoc), not as pre-registered.*

---

## 2. Chronological Git Commit Trace

The table below lists all Git commits in strict chronological order by commit timestamp (`%cI`), documenting the exact temporal ordering of protocol declarations, script drafts, and execution commits:

| Commit Hash | Commit Timestamp (ISO 8601) | Category | Description & Committed Artifacts |
|:---|:---|:---|:---|
| `03f60d7` | 2026-09-12T20:10:07+05:30 | Baseline Freeze | Prior repository state frozen (`all done paper close`); all upstream splits, checkpoints, and metrics locked. |
| `f8f97ab` | 2026-09-28T11:26:52+05:30 | Protocol Config | Phase 0a: Initial skeleton `populations.yaml` and `matched_fpr.yaml`. **First commit containing verbatim `headline_tier_rule` text** (stripped SHA-256: `f663657c...`); declares `split_seed: 20260928` and Tier B permutation method. |
| `4accd8c` | 2026-09-28T12:01:25+05:30 | Protocol Config | Phase 0b: Complete discovery audit (S0), resolve population manifests, commit configs (`populations.yaml`, `matched_fpr.yaml`, `stage_f.yaml`, `tost.yaml`, `mad.yaml`). Generates and commits UID-list files and hashes. |
| `e528528` | 2026-09-28T12:13:23+05:30 | Integrity Guard | `frozen_integrity_check.py` and `frozen_baseline_full.json` (342 files hashed). |
| `1818b81` | 2026-09-28T12:31:39+05:30 | Result Execution | Phase 1 (S1) probability inference outputs (`EXP_PROB_INFERENCE_V1`) and zero-training verification. |
| `f0bef8f` | 2026-09-28T12:38:07+05:30 | Script & Config | S2 draft script (`run_roc_pr_analysis.py`) and `roc_pr.yaml`, NOT run (committed after S1 ran; not predeclared). |
| `970f84c` | 2026-09-28T13:14:37+05:30 | Result Execution | S7 Isolation Forest baseline (`EXP_IF_V1`) and S3 Matched-FPR headline tier decision (`EXP_MATCHED_FPR_V1`). Headline Tier B decided in first S3 run; S3 re-run ingested `headline_tier_rule` text verbatim into `headline_tier_decision.json` (CSV SHA-256s identical). |
| `047581a` | 2026-09-28T13:27:09+05:30 | Script Fix | S2 draft column and tier lookups aligned to Tier B headline operating points, NOT run. |
| `ad2bd8d` | 2026-09-28T13:49:19+05:30 | Result Execution | S2 zero-day ROC/PR curves on Tier B eval half ($N=19,083$) (`EXP_ROC_PR_V1`). |
| `38434c0` | 2026-09-28T13:50:32+05:30 | Script Draft | S4 draft script (`run_tost_analysis.py`), NOT run. |
| `dfeb6f2` | 2026-09-28T13:54:05+05:30 | Result Execution | S4 conservative exact paired-equivalence test for RF ± TTL (`EXP_TOST_V1`). (Script: `run_tost_analysis.py`) |
| `c7cb840` | 2026-09-28T14:03:08+05:30 | Script Draft | S5 draft script (`run_mad_threshold.py`), NOT run. |
| `cd952fb` | 2026-09-28T14:09:32+05:30 | Script Draft | S5 draft update with threshold config assertion, NOT run. |
| `468e895` | 2026-09-28T14:14:54+05:30 | Result Execution | S5 AE threshold families and MAD analysis (`EXP_MAD_THRESHOLD_V1`). |
| `54b0ea6` | 2026-09-28T14:25:49+05:30 | Script Draft | S6 draft script (`run_ae_threshold_ablation.py`), NOT run. |
| `72d9fcd` | 2026-09-28T14:35:55+05:30 | Result Execution | S6 AE threshold ablation analysis (`EXP_AE_ABLATION_V1`). |
| `72a0bd0` | 2026-09-28T14:40:03+05:30 | Script Draft | S8 draft script (`run_alert_budget_analysis.py`), NOT run. |
| `19aa353` | 2026-09-28T14:50:15+05:30 | Script Draft | S8 draft update asserting calibration tier == 'B', NOT run. |
| `01f3702` | 2026-09-28T15:04:12+05:30 | Script Draft | S9 draft script (`run_cross_consistency_check.py`), NOT run. |
| `28fbfc5` | 2026-09-28T15:11:06+05:30 | Result Execution | S8 alert budget analysis (`EXP_ALERT_BUDGET_V1`). |
| `dcd76a6` | 2026-09-28T15:13:16+05:30 | Script Draft | S9 draft update (Check 4 S3 vs S6 reconciliation), NOT run. |
| `8ef616b` | 2026-09-28T15:17:25+05:30 | Script Draft | S9 draft update 2 (Check 1 baseline schema fix), NOT run. |
| `a6e1ca4` | 2026-09-28T15:22:08+05:30 | Script Draft | S9 draft update 3 (Check 8 population groupby & full dict equality), NOT run. |
| `7d3074c` | 2026-09-28T15:33:11+05:30 | Result Execution | S9 cross-stage consistency check (`EXP_CROSS_CHECK_V1`). All 9 checks PASS. |

---

## 3. Aborted Execution Iterations & Re-Runs

The following aborted iterations and execution re-runs occurred during protocol execution, as documented in `PROGRESS_LOG.md`:

1. **Stage S3 Execution & Re-Run (committed in `970f84c`):**
   - First S3 run evaluated all 44 cells under Tier A, identified 43 of 44 cells (97.7%) as shift-affected, and decided Headline Tier B (per PROGRESS_LOG; the first run's JSON was not committed).
   - S3 was re-run once (prior to commit `970f84c`) solely to dynamically ingest `headline_tier_rule` verbatim from `matched_fpr.yaml` into `headline_tier_decision.json` alongside its SHA-256 (`f663657c...`), eliminating all hand-typed rule strings. The Tier B decision itself did not change.
   - All 6 output CSV SHA-256 hashes remained identical bit-for-bit; only `headline_tier_decision.json` and `metadata.json` were updated.
2. **Stage S8 Aborted Run (from draft `72a0bd0`):**
   - First execution aborted because the script compared `calibration_tier` to `'tier_b'` while S3 writes the value `'B'` into `headline_tier_decision.json`.
   - Fixed in draft update `19aa353` with strict `assert df["calibration_tier"].eq("B").all()` and `assert headline_tier_decision["headline_tier"] == "B"`.
   - Successful run executed from `19aa353` and committed in `28fbfc5`.
3. **Stage S9 Aborted Run 1 (from draft `01f3702`):**
   - First execution aborted at Check 1 (`AssertionError: Expected 342 files in baseline, found 5`) because `frozen_baseline_full.json` has schema `{"created_utc": ..., "git_commit": ..., "file_count": 342, "frozen_dirs": [...], "hashes": {...}}` and line 160 loaded the entire dictionary instead of `data["hashes"]`.
   - Fixed in draft update 2 `8ef616b`.
4. **Stage S9 Aborted Run 2 (from draft update 2 `8ef616b`):**
   - Second execution aborted at Check 8 with `KeyError: 'family'` because in `ae_ablation_results_unseen.csv` the column name is `population` (values: `unseen_worms`, `unseen_shellcode`, `unseen_analysis`), not `family`.
   - Fixed in draft update 3 `a6e1ca4` using `df_s6_unseen.groupby("population")["n_total"].first().to_dict()` and full dict equality `assert fam_counts == exp_fam`.
   - Successful run executed from `a6e1ca4` and committed in `7d3074c`.

---

## 4. Cryptographic Hashes of Predeclared Artifacts

The following protocol artifacts and manifests were committed prior to downstream zero-day evaluation:

1. **Headline Tier Decision Rule:**
   - **Stripped Text SHA-256:** `f663657c93046446d0753f56de95fe79f5bbf279b965056082b258801752751f`
   - **First Committed in Config:** `revision_v5/publication_experiments/configs/matched_fpr.yaml` (commit `f8f97ab`, reaffirmed in `4accd8c`)
   - **Ingested in Decision:** `revision_v5/results/publication_experiments/EXP_MATCHED_FPR_V1/headline_tier_decision.json` (commit `970f84c`)
   - **Cross-Checked:** Verified identical bit-for-bit by S9 Check 2 (commit `7d3074c`).

2. **Population Manifests & Real UID-List SHA-256 Values:**
   - **Declaration of Seed & Method:** Split seed `20260928` and the Tier B permutation method (`numpy.random.default_rng(split_seed) permutation of the sorted source-prefixed row IDs...`) were declared in `f8f97ab` (`populations.yaml` skeleton).
   - **Generation of UID Lists:** The row UID lists and their SHA-256 hashes were generated by S0 discovery and committed in `4accd8c`:
     * `cal_control` ($N=18,500$): SHA-256 `e95728c95299c21ad026b27434cc483d9b8fe7ddfb7563f0e0137decd76c7395`
     * `eval_control` ($N=18,500$): SHA-256 `25628d10faad090908ea4a149e1e5c3fa074c3df711b3a36bf0c865a0a0a0210`
     * `benign_control` ($N=37,000$): SHA-256 `9c87ab13a3f7f993d63aec68ab7f89b4390d11b934342952159bab791f4db7a1`
     * `calibration_benign` ($N=11,200$): SHA-256 `46f91f52c814a7038ede506e91b700656c99387b8cc7622a03f040721a6abe5f`
   - **Partition Verification:** Disjointness (`intersection == 0`) and exact union (`union == benign_control`) verified by S0 (commit `4accd8c`) and S9 Check 8 (commit `7d3074c`).

3. **Frozen Baseline Verification:**
   - **Committed in:** `revision_v5/frozen_baseline_full.json` (commit `e528528`)
   - 342 files across 7 frozen directories.
   - Verified 342/342 matching at every execution gate and re-verified by S9 Check 1.

---

## 5. Formal Preregistration Status Classification

| Protocol Item | Git File Path | First Commit | Predeclared Status | Justification / Citation |
|:---|:---|:---|:---|:---|
| Headline-tier decision rule | `matched_fpr.yaml` | `f8f97ab` | **PREDECLARED** | Rule text and hash committed in `f8f97ab` (and `4accd8c`) before S3 execution in `970f84c`. |
| Disjoint Tier B split seed & method | `populations.yaml` | `f8f97ab` | **PREDECLARED** | Seed `20260928` and permutation method declared in `f8f97ab` before S0 generation in `4accd8c`. |
| Disjoint Tier B UID lists & hashes | `populations.yaml` | `4accd8c` | **PREDECLARED** | UID lists generated by S0 and committed in `4accd8c` before S3 execution in `970f84c`. |
| Nominal FPR budgets (0.1%, 0.5%, 1%, 5%) | `matched_fpr.yaml` | `f8f97ab` | **PREDECLARED** | Rational-fraction form `["1/1000", "1/200", "1/100", "1/20"]` identical in `f8f97ab` and `4accd8c`; declared before S3 execution in `970f84c`. |
| Isolation Forest domain & seeds | `stage_f.yaml` | `4accd8c` | **PREDECLARED** | Parameters, seeds (`42, 123, 2024`), and AE scaler reference committed in `4accd8c` before S7 run in `970f84c`. |
| MAD k values $\{2, 3, 4\}$ and scale constant $1.4826$ | `mad.yaml` | `4accd8c` | **PREDECLARED** | Sensitivity values declared in `mad.yaml` before S5 run in `468e895`. |
| Equivalence Margin ($\delta = 0.01$, conservative exact paired test) | `tost.yaml` | `4accd8c` | **POST-HOC** | Committed in `4accd8c` prior to S4 script run, but paired counts $(582, 0, 0, 1)$ were known from prior sprint reports (§0 Rule 7). |
| ROC/PR curve configuration | `roc_pr.yaml` | `f0bef8f` | **NOT PREDECLARED** | Committed with the S2 script draft after S1 had already executed. |


---

## 6. Post-Publication Audit Corrections (2026-09-28)

### 6.1 Tier B Coverage -- 34/44 Verified (from matched_fpr_tier_b.csv)

The '34 of 44 cells' figure in Section 1 and DOC_SCOPE_DECISION refers to cells in
matched_fpr_tier_b.csv (commit 970f84c) where the nominal_budget lies INSIDE the Clopper-Pearson
95% CI of realized_control_fpr on eval_control (N=18,500, Tier B eval half). The shift_affected
column in matched_fpr_tier_b.csv is hardcoded False for all 44 Tier B rows (shift_affected is a
Tier A criterion only) and does not represent this coverage check.

Recomputed: nominal budget inside eval-half CI: 34/44; outside: 10/44.
All 10 outside cells have nominal budget lying ABOVE the CI upper bound (realized FPR below
nominal -- threshold is conservative but CI upper bound falls below the nominal budget).

  8 tie_unattainable=True cells (realized FPR below nominal; comparison ill-defined at discrete level):
    dt  (no seed)    1/1000  nom=0.001000  realized=0.000000  CI=[0.000000, 0.000199]
    dt  (no seed)    1/200   nom=0.005000  realized=0.000000  CI=[0.000000, 0.000199]
    dt  (no seed)    1/100   nom=0.010000  realized=0.000000  CI=[0.000000, 0.000199]
    dt  (no seed)    1/20    nom=0.050000  realized=0.000000  CI=[0.000000, 0.000199]
    rf  (no seed)    1/1000  nom=0.001000  realized=0.000432  CI=[0.000187, 0.000852]
    rf  (no seed)    1/20    nom=0.050000  realized=0.046270  CI=[0.043288, 0.049397]
    stacking seed123 1/20    nom=0.050000  realized=0.045784  CI=[0.042816, 0.048895]
    if  seed 42      1/1000  nom=0.001000  realized=0.000541  CI=[0.000259, 0.000994]

  2 tie_unattainable=False cells (genuine non-tie outside cells):
    stacking seed 42   1/20  nom=0.050000  realized=0.046216  CI=[0.043235, 0.049341]
    stacking seed 2024 1/20  nom=0.050000  realized=0.046324  CI=[0.043340, 0.049452]

### 6.2 Git History -- Complete Amend and Reset Record (verbatim reflog)

Verbatim excerpt from git reflog --oneline (relevant entries only; HEAD@{3}–HEAD@{18} omitted):

  978d893 HEAD@{0}:  commit: docs(revision_v5): Phase 8 documentation, scope decisions, and preregistration trace
  4195306 HEAD@{1}:  commit (amend): docs(revision_v5): preserve v5.0 execution blueprint in docs/
  af6ae0d HEAD@{2}:  commit: docs(revision_v5): preserve v5.0 execution blueprint in docs/
  047581a HEAD@{19}: commit: fix(revision_v5): S2 column and tier lookups for Tier B headline operating points
  970f84c HEAD@{20}: reset: moving to HEAD
  970f84c HEAD@{21}: reset: moving to HEAD~1
  64514f2 HEAD@{22}: commit (amend): fix(revision_v5): S2 column and tier lookups for Tier B headline operating points
  5e50951 HEAD@{23}: commit (amend): fix(revision_v5): S2 column and tier lookups for Tier B headline operating points
  7526d65 HEAD@{24}: commit (amend): fix(revision_v5): S2 column and tier lookups for Tier B headline operating points
  383dc26 HEAD@{25}: commit: fix(revision_v5): S2 column and tier lookups for Tier B headline operating points
  970f84c HEAD@{26}: commit: feat(revision_v5): S7 Isolation Forest baseline and S3 Matched-FPR headline tier decision (Tier B)
  457013c HEAD@{35}: reset: moving to HEAD~1

S2 amend chain (oldest to newest):
  383dc26  original commit       (HEAD@{25})
  7526d65  amend 1               (HEAD@{24})  -- not reachable from HEAD
  5e50951  amend 2               (HEAD@{23})  -- not reachable from HEAD
  64514f2  amend 3               (HEAD@{22})  -- not reachable from HEAD
  047581a  clean recommit        (HEAD@{19})  -- final history; script-only, NOT run

Blueprint amend: af6ae0d -> 4195306 (CRLF blob fix, documented BN-09).
All result-producing run commits are plain commits with no rewrites.
HEAD@{35} reset is pre-revision_v5 history.

**Verification Notes:**
1. The `(2fa630a discarded)` note on `HEAD@{35}` is UNVERIFIED, since that hash does not appear in the reflog output; the reflog shows `457013c`.
2. The reflog blocks are a verbatim excerpt of relevant entries only, `HEAD@{3}` to `HEAD@{18}` omitted.
3. The verified SHA-256 hash of `docs/IMPLEMENTATION_BLUEPRINT_v5.md` is `de7ed30fb9948683c0ce7ca5241d1b9b92cfff6cd64cd82f31c299ee9155b099` (64 chars); earlier prompts had a 63-char typo (omitted 'b').
