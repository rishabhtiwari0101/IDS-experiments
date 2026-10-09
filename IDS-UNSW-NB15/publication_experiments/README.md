# publication_experiments/README.md
# Publication Extension Experiments — Stage A

## Overview

This folder contains the **publication extension framework** for the UNSW-NB15
IDS research project, built after Sprint 13 freeze (`f694e19`).

The canonical Sprint-1-to-Sprint-13 pipeline is **READ-ONLY and untouched**.

---

## Folder Structure

```
publication_experiments/
├── configs/
│   ├── no_ttl.yaml              # EXP_NO_TTL_V1 configuration
│   └── ae_unseen_families.yaml  # EXP_AE_UNSEEN_FAMILY_V1 configuration
├── scripts/
│   └── run_dry_run.py           # Stage A: validation + audit (NO training)
├── utils/
│   ├── feature_adapter.py       # No-TTL feature subsetting (72 features)
│   └── ae_family_eval.py        # Per-family AE evaluation utilities
├── features/                    # (staging area, outputs go to results/)
└── README.md                    # This file

results/publication_experiments/
├── EXP_NO_TTL_V1/
│   └── features/
│       └── no_ttl_features.json # Authoritative 72-feature manifest (Stage A output)
├── EXP_AE_UNSEEN_FAMILY_V1/     # Created in Stage C
└── stage_a_audit_report.json    # Full Stage A validation report
```

---

## Experiments

### EXP_NO_TTL_V1 — Controlled No-TTL Feature Ablation (Stage B)

**Objective:** Measure how supervised IDS performance changes when exactly
`{sttl, ct_state_ttl, dttl}` are removed from the canonical 75-feature set.

**Important:** This is a *controlled feature-ablation experiment*, NOT proof of
causal shortcut learning.

**Feature transformation:**
```
75 canonical features
→ remove sttl (index 1)
→ remove ct_state_ttl (index 3)  
→ remove dttl (index 4)
→ 72 No-TTL features
```

**Models:** DT + RF + SVM + IDSNet (72→128→64→2) → 5-fold OOF → LR meta-learner  
**Seeds:** 42, 123, 2024 (canonical)  
**Evaluation:** DEV TEST + Protected Backdoor (583 flows)

### EXP_AE_UNSEEN_FAMILY_V1 — AE Unseen Attack-Family Evaluation (Stage C)

**Objective:** Determine whether a benign-only AE can detect different attack
families that were never seen during AE training.

**Design:** ONE AE (72→12→6→12→72), ONE scaler, ONE threshold → four families.

| Family   | Source                | N     | Note         |
|----------|-----------------------|-------|--------------|
| Backdoor | protected_unseen_attack.csv | 583 | Protected    |
| Worms    | dev_test (attack_cat) | 44    | Small-N ⚠️  |
| Shellcode| dev_test (attack_cat) | 378   |              |
| Analysis | dev_test (attack_cat) | 677   |              |

---

## Stage A Commands (Dry-Run Only — No Training)

```bash
# Run Stage A: validate all preconditions and generate audit report
python publication_experiments/scripts/run_dry_run.py

# With verbose logging
python publication_experiments/scripts/run_dry_run.py --verbose
```

## Stage B Commands (After Explicit Approval)

```bash
# Run No-TTL supervised ablation
python publication_experiments/scripts/run_no_ttl_experiment.py \
  --config publication_experiments/configs/no_ttl.yaml

# Evaluate only (skip training if checkpoint exists)
python publication_experiments/scripts/run_no_ttl_experiment.py \
  --config publication_experiments/configs/no_ttl.yaml \
  --only-evaluate

# Single seed
python publication_experiments/scripts/run_no_ttl_experiment.py \
  --config publication_experiments/configs/no_ttl.yaml \
  --seed 42
```

## Stage C Commands (After Explicit Approval of Stage B Results)

```bash
# Train new 72-feature AE and evaluate all four families
python publication_experiments/scripts/run_ae_unseen_family.py \
  --config publication_experiments/configs/ae_unseen_families.yaml

# Evaluate specific family only (after AE is frozen)
python publication_experiments/scripts/run_ae_unseen_family.py \
  --config publication_experiments/configs/ae_unseen_families.yaml \
  --target-family SHELLCODE \
  --skip-training
```

---

## Key Design Decisions

### Monitor Partition
> **CONFIRMED ABSENT as CSV.** Monitor is an internal 10% split of Normal TRAIN
> rows created at AE training time inside `AETrainer.create_monitor_split()`.
> It is NOT a persistent partition and NOT used in new experiments differently
> from canonical.

### Scaler Strategy
> Canonical scalers (SVM: 75-feature, NN: 75-feature, AE: 75-feature) are
> **incompatible** with the 72-feature input. New scalers are fitted at Stage B/C
> training time on TRAIN only.

### Row Alignment
> Canonical and No-TTL predictions are paired by the `id` column (stable across
> all split files). Positional alignment alone is FORBIDDEN.

### AE Training Policy
> AE is **benign-only** (`label == 0`). Attack families appearing in TRAIN
> (Worms, Shellcode, Analysis) are attack-labeled and never enter AE training.
> Backdoor is excluded from TRAIN entirely.

---

## Canonical Pipeline (READ-ONLY)

The following are frozen and must NOT be modified:
- `results/zero_day/EXP_ZERODAY_V1/`
- `results/stacking/EXP_OOF_STACK_V1/`
- `results/autoencoder/EXP_AE_V1/`
- `results/explainability/EXP_EXPLAIN_V1/`
- All canonical `src/` code

New code imports from `src/` — it does NOT copy or modify it.
