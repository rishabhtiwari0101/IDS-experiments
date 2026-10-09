"""
Section 12a: Scaler Application Verification
Trace which scaler was actually used for each model/seed in the No-TTL run.
"""
import hashlib
import json
import joblib
import inspect
import numpy as np
import pandas as pd
from pathlib import Path

REPO = Path(".")
EXP = REPO / "results/publication_experiments/EXP_NO_TTL_V1"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

# 1. Hash the two scalers in question
nottl_scaler_path  = EXP / "scalers/supervised_scaler_72.joblib"
canon_scaler_path  = REPO / "results/checkpoints/EXP_BASE_MODELS_V1/canonical_scaler.joblib"

nottl_hash = sha256_file(nottl_scaler_path)
print(f"NoTTL 72-feature scaler hash: {nottl_hash}")
print(f"NoTTL 72-feature scaler path: {nottl_scaler_path}")

# Check if canonical scaler exists
if canon_scaler_path.exists():
    canon_hash = sha256_file(canon_scaler_path)
    print(f"Canonical scaler hash: {canon_hash}")
else:
    # Find canonical scalers
    print("Searching for canonical scaler files...")
    for f in (REPO / "results/checkpoints").rglob("*.joblib"):
        if "scaler" in f.name.lower():
            h = sha256_file(f)
            scaler = joblib.load(f)
            print(f"  Found: {f} | n_features_in_={getattr(scaler, 'n_features_in_', 'N/A')} | hash={h[:16]}...")

# Also search preprocessing pipeline scaler
for f in REPO.glob("results/**/*.joblib"):
    if "scaler" in f.name.lower() or "pipeline" in f.name.lower() or "preprocess" in f.name.lower():
        try:
            s = joblib.load(f)
            n_feat = getattr(s, 'n_features_in_', None)
            if n_feat and n_feat > 72:
                h = sha256_file(f)
                print(f"  LARGE scaler found: {f} | n_features_in_={n_feat} | hash={h[:16]}...")
        except Exception:
            pass

# 2. Load the NoTTL scaler and inspect properties
nottl_scaler = joblib.load(nottl_scaler_path)
print(f"\nNoTTL scaler n_features_in_: {nottl_scaler.n_features_in_}")
print(f"NoTTL scaler mean range: [{nottl_scaler.mean_.min():.4f}, {nottl_scaler.mean_.max():.4f}]")
print(f"NoTTL scaler std range:  [{nottl_scaler.scale_.min():.4f}, {nottl_scaler.scale_.max():.4f}]")

# 3. Trace actual code — read the run_no_ttl_experiment.py script
script_path = REPO / "publication_experiments/scripts/run_no_ttl_experiment.py"
script_text = open(script_path).read()

# Find all references to scaler loading
scaler_lines = []
for i, line in enumerate(script_text.split("\n")):
    if "scaler" in line.lower() or "preprocessing_pipeline" in line.lower() or "fit(" in line or "transform(" in line:
        scaler_lines.append((i+1, line.strip()))

print("\n=== SCALER REFERENCES IN run_no_ttl_experiment.py ===")
for ln, text in scaler_lines:
    print(f"  L{ln}: {text}")

# 4. Verify the scaler fitting population
# The config says: fit_population: TRAIN_all_72_features
# Check what the no-ttl preprocessing pipeline actually fits on
print("\n=== PREPROCESSING PIPELINE REFERENCE ===")
pipeline_lines = [l for l in script_text.split("\n") if "PreprocessingPipeline" in l or "pipeline.fit" in l or "pipeline.transform" in l]
for l in pipeline_lines:
    print(f"  {l.strip()}")
