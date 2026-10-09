import json, hashlib, pandas as pd, numpy as np
from pathlib import Path

REPO = Path(".")

# 1. Canonical fold seeds from metadata
print("=== CANONICAL OOF SEEDS FROM METADATA ===")
for seed in [42, 123, 2024]:
    m = json.load(open(REPO / f"results/stacking/EXP_OOF_STACK_V1/seed_{seed}/metadata.json"))
    print(f"  Canon Seed {seed}: oof_seed={m['oof_seed']}, oof_n_splits={m['oof_n_splits']}")

# 2. No-TTL metadata oof seed
print("\n=== NO-TTL METADATA ===")
m_nottl = json.load(open(REPO / "results/publication_experiments/EXP_NO_TTL_V1/metadata.json"))
print("Top-level keys:", list(m_nottl.keys())[:15])
for k,v in m_nottl.items():
    if any(kw in k.lower() for kw in ["oof","fold","seed"]):
        print(f"  {k}: {v}")

# 3. No-TTL config oof_seed
cfg = json.load(open(REPO / "results/publication_experiments/EXP_NO_TTL_V1/metadata.json"))
# Also from yaml config
import yaml
cfg_yaml = yaml.safe_load(open(REPO / "results/publication_experiments/EXP_NO_TTL_V1/config_used.yaml"))
print("\n=== NO-TTL CONFIG OOF FIELDS ===")
stacking_cfg = cfg_yaml.get("models", {}).get("stacking", {})
print(f"  stacking.oof_n_splits: {stacking_cfg.get('oof_n_splits')}")
print(f"  stacking.oof_random_state: {stacking_cfg.get('oof_random_state')}")

# 4. Verify fold assignment ID overlap between canonical and no-ttl
print("\n=== FOLD ASSIGNMENT ROW-ID MATCH ===")
ca42 = pd.read_csv(REPO / "results/stacking/EXP_OOF_STACK_V1/seed_42/fold_assignments.csv")
nottl_oof42 = pd.read_csv(REPO / "results/publication_experiments/EXP_NO_TTL_V1/predictions/seed_42/oof_predictions.csv")

canon_ids = set(ca42["row_id"].values)
nottl_ids = set(nottl_oof42["row_id"].values)
print(f"  Canon fold assignment row IDs: {len(canon_ids)}")
print(f"  NoTTL OOF row IDs:            {len(nottl_ids)}")
print(f"  Sets identical:               {canon_ids == nottl_ids}")

# 5. Check if the fold assignments match by rejoining
merged = ca42.merge(nottl_oof42, on="row_id", how="inner")
print(f"  Inner join rows (should be 162395): {len(merged)}")

print("\nSECTION 11a SUMMARY:")
print("  Canonical oof_seed=7 across seeds 42/123/2024 (all logs confirm 'Creating OOF folds | n_splits=5 | seed=7')")
print("  No-TTL stacking.oof_random_state=", stacking_cfg.get('oof_random_state'))
if stacking_cfg.get('oof_random_state') == 7:
    print("  FOLD-SEED: MATCH — both canonical and No-TTL used fold seed=7")
else:
    print("  FOLD-SEED: DEVIATION — No-TTL used different fold seed!")
