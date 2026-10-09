"""
cicids2017/generate_cic_manifest.py
-----------------------------------
Generates the deterministic master checksum manifest:
reports/cicids2017_revision_v1/manifests/CIC_REVISION_V1_MANIFEST.sha256

Includes:
  - cicids2017/DATA/splits/*.csv (all 8 split partitions)
  - cicids2017/models/** (all model checkpoints, scalers, weights)
  - results/cicids2017_revision_v1/** (all JSON, CSV, MD results)
  - figures/cicids2017_revision_v1/* (all publication PNGs and vector PDFs)
  - reports/cicids2017_revision_v1/*.md and manifests/*.json
  - cicids2017 orchestration and verification scripts

Excludes:
  - Python __pycache__ / *.pyc
  - Transient temp files / .tmp
  - OS metadata (.DS_Store, Thumbs.db)
  - Active log files undergoing writes
  - External / virtual environment files (.venv, .git)
"""

import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "CIC_REVISION_V1_MANIFEST.sha256"
MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

candidate_paths = []

# 1. CIC split partitions
splits_dir = ROOT / "cicids2017" / "DATA" / "splits"
if splits_dir.exists():
    for f in splits_dir.glob("*.csv"):
        candidate_paths.append(f)

# 2. Models and scalers
models_dir = ROOT / "cicids2017" / "models"
if models_dir.exists():
    for f in models_dir.rglob("*"):
        if f.is_file() and f.suffix in [".pkl", ".pt", ".joblib", ".json"]:
            candidate_paths.append(f)

# 3. Results artifacts
results_dir = ROOT / "results" / "cicids2017_revision_v1"
if results_dir.exists():
    for f in results_dir.rglob("*"):
        if f.is_file() and f.suffix in [".json", ".csv", ".md", ".npy", ".log"]:
            candidate_paths.append(f)

# 4. Figures
figures_dir = ROOT / "figures" / "cicids2017_revision_v1"
if figures_dir.exists():
    for f in figures_dir.glob("*"):
        if f.is_file() and f.suffix in [".png", ".pdf"]:
            candidate_paths.append(f)

# 5. Reports & manifests
reports_dir = ROOT / "reports" / "cicids2017_revision_v1"
if reports_dir.exists():
    for f in reports_dir.glob("*.md"):
        candidate_paths.append(f)
    manifests_dir = reports_dir / "manifests"
    if manifests_dir.exists():
        for f in manifests_dir.glob("*.json"):
            candidate_paths.append(f)

# 6. Pipeline orchestration and verification code
src_files = [
    ROOT / "cicids2017" / "run_all.py",
    ROOT / "cicids2017" / "verify_revision.py",
    ROOT / "cicids2017" / "check_no_hardcoded_paths.py",
    ROOT / "cicids2017" / "generate_numbers_pack.py",
    ROOT / "cicids2017" / "generate_final_summary.py",
]
for f in (ROOT / "cicids2017" / "src").glob("*.py"):
    src_files.append(f)
for f in src_files:
    if f.exists() and f.is_file():
        candidate_paths.append(f)

# Deduplicate and sort deterministically
unique_paths = sorted(set(candidate_paths), key=lambda p: str(p.relative_to(ROOT)).replace("\\", "/"))

manifest_lines = []
for p in unique_paths:
    rel_path = str(p.relative_to(ROOT)).replace("\\", "/")
    # Filter out transient files
    if "__pycache__" in rel_path or rel_path.endswith(".tmp") or "verify_revision.log" in rel_path:
        continue

    hasher = hashlib.sha256()
    with open(p, "rb") as bf:
        while chunk := bf.read(65536):
            hasher.update(chunk)
    sha = hasher.hexdigest()
    manifest_lines.append(f"{sha}  {rel_path}")

with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(manifest_lines) + "\n")

print(f"Successfully generated master manifest: {MANIFEST_FILE}")
print(f"Total files hashed: {len(manifest_lines)}")
