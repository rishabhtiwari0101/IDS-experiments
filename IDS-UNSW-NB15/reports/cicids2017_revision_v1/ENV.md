# Environment Audit & Hardware Diagnostic Report
**Sprint:** Sprint 1 — Repository Freeze, Pre-Registration & Reuse Audit  
**Document:** `reports/cicids2017_revision_v1/ENV.md`  
**Governing Rule:** Rule G11 (Software and Hardware Environment Recording)  

---

## 1. Host Hardware Specifications

| Hardware Component | Detected System Specification |
|---|---|
| **Operating System** | Windows 11 Home (64-bit, Version 10.0.26100, AMD64 architecture) |
| **Processor (CPU)** | 13th Gen Intel(R) Core(TM) i7-13700H (14 cores: 6 Performance cores + 8 Efficient cores, 20 logical threads) |
| **System Memory (RAM)** | 16.0 GB Total Physical RAM (15.7 GB usable) |
| **Dedicated Graphics (GPU)**| NVIDIA GeForce RTX 3050 Laptop GPU |
| **GPU Dedicated VRAM** | 4.0 GB / 6.0 GB GDDR6 |
| **Storage Architecture** | NVMe SSD hosting Windows OS and local workspaces |

---

## 2. Python Runtimes & Virtual Environments

### 2.1 Host Python Runtime (Active for Sprint 1 Execution)
- **Interpreter Path:** System `python.exe` (on PATH)
- **Version:** `Python 3.13.1` (tags/v3.13.1:0671451, Dec 3 2024, 19:30:55) [MSC v.1942 64 bit (AMD64)]
- **Status:** Fully functional. Successfully executed SHA-256 manifest generation, verification, and AST checker self-test.

### 2.2 Workspace Virtual Environment Diagnostic
- **Path:** `c:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15\.venv`
- **Configuration:** `.venv/pyvenv.cfg` references `home = C:\Program Files\Python311` and `version = 3.11.9`.
- **Diagnostic Finding:** The underlying base installation `C:\Program Files\Python311\python.exe` is absent on the host filesystem, causing direct invocations of `.venv\Scripts\python.exe` to fail with "The system cannot find the path specified."
- **Policy Compliance Note:** In strict compliance with Sprint 1 instructions ("Do NOT reinstall or repair the Python environment in this sprint... A broken `.venv` is NOT by itself a reason to perform environment surgery now"), no environment repair was performed in Sprint 1. Host Python was used for all read/write/audit tasks. The `.venv` environment will be repaired or re-pointed prior to executing Sprint 2 data processing pipelines.

---

## 3. Dependency Specifications

The repository's dependencies are declared in [`requirements.txt`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/requirements.txt):

```text
torch>=2.0.0
torchvision
scikit-learn>=1.3.0
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
shap>=0.42.0
pyyaml>=6.0
tqdm>=4.65.0
joblib>=1.3.0
```

All required standard library modules (`hashlib`, `ast`, `pathlib`, `os`, `sys`, `json`) are natively provided by the active host Python 3.13 runtime.
