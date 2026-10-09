# Sprint 6 Deployment Latency and Throughput Benchmark Report

**Date:** 2026-10-07  
**Sprint:** Sprint 6 (Matched-FPR, Deployment Analysis, Cross-Dataset Comparison & Figures)  
**Status:** PASS — ALL 8 MODELS BENCHMARKED  
**Authoritative Artifact:** `results/cicids2017_revision_v1/deployment/s24_deployment_benchmark.csv`  

---

> [!IMPORTANT]
> **MANDATORY DEPLOYMENT DISCLAIMER:**  
> **"Local host inference benchmarks, not production gateway throughput."**  
> These measurements quantify purely local compute, kernel scheduling, and memory access overheads on static pre-extracted feature vectors. They do NOT include raw packet capture (PCAP), NIC ring buffer transfer, kernel-to-userspace copying, protocol parsing, flow reconstruction, sliding-window feature aggregation, or network serialization.

---

## 1. Executive Summary

This report establishes the local inference latency, throughput, CPU memory, and GPU VRAM footprint for eight intrusion detection architectures trained on CIC-IDS-2017 ($K^*=69$ features).

Benchmarks were conducted across three batch volumes:
$$N \in \{1,000, \; 10,000, \; 100,000\} \text{ flows}$$

### Headline Findings:
1. **Ultra-Low-Latency Category ($> 1\text{M flows/sec}$):**
   - **IDSNet / MLP (GPU):** Fastest overall architecture at high batch volumes. Achieved **$5.27\text{ ms}$** for $100,000$ flows (**$18,975,332\text{ flows/s}$**), with minimal GPU allocation ($205.8\text{ MB}$).
   - **Autoencoder (GPU):** Achieved **$15.12\text{ ms}$** for $100,000$ flows (**$6,612,226\text{ flows/s}$**), requiring only $73.7\text{ MB}$ GPU VRAM.
   - **Decision Tree (CPU):** Single-tree inference executes in **$17.68\text{ ms}$** for $100,000$ flows (**$5,656,557\text{ flows/s}$**).
   - **Linear SVC (CPU):** Matrix multiplication yields **$70.32\text{ ms}$** for $100,000$ flows (**$1,422,056\text{ flows/s}$**).
2. **Moderate-Latency Ensemble Category ($30\text{k} - 55\text{k flows/sec}$):**
   - **Random Forest (CPU, 100 trees):** **$1,995.11\text{ ms}$** for $100,000$ flows (**$50,123\text{ flows/s}$**).
   - **Isolation Forest (CPU, 100 trees):** **$1,807.06\text{ ms}$** for $100,000$ flows (**$55,338\text{ flows/s}$**).
   - **Stacking Ensemble (Hybrid CPU+GPU):** Executes DT, RF, SVM, and IDSNet sequentially before feeding meta-learner logistic regression. Incurs **$3,122.35\text{ ms}$** for $100,000$ flows (**$32,027\text{ flows/s}$**).
3. **Heavy Tabular Transformer Category:**
   - **FT-Transformer (GPU, Chunked 4096):** Incurs self-attention complexity across $70$ tokens ($K^*=69$ numeric features $+ 1$ [CLS] token) across 3 transformer blocks with 4 attention heads.
   - For $100,000$ flows, chunked execution requires **$7,049.74\text{ ms}$** (**$14,185\text{ flows/s}$**).
   - **Memory Safety Guard:** Chunking into mini-batches of $4,096$ flows prevented CUDA OOM on the 4.29 GB VRAM GPU, capping peak allocated VRAM at $528.0\text{ MB}$.

---

## 2. Experimental Environment & Protocol

### 2.1 Hardware and Platform Specifications
- **CPU:** Intel Core i5-11400H @ 2.70GHz (6 Cores, 12 Threads)
- **Host RAM:** 16.0 GB DDR4
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (4.29 GB Dedicated VRAM)
- **Host Operating System:** Windows 11 Enterprise (64-bit)
- **Python Runtime:** Python 3.11.9
- **Deep Learning Framework:** PyTorch 2.7.1+cu118 (CUDA 11.8)
- **Machine Learning Library:** Scikit-Learn 1.6.1

### 2.2 Timing Protocol
To eliminate cold-start transients, JIT overhead, and memory allocation jitter:
1. **Model Loading:** The model is restored from disk prior to timing.
2. **Input Preparation:** Slices of $N$ rows ($N \in \{1\text{k}, 10\text{k}, 100\text{k}\}$) are extracted from `DEV_TEST` once into memory.
3. **Warm-up Run:** Exactly 1 full inference pass is executed and discarded.
4. **Timed Repetitions:** Exactly 5 consecutive runs are measured using high-precision monotonic timers (`time.perf_counter()`). When CUDA is active, `torch.cuda.synchronize()` is enforced before timer start and stop.
5. **Reported Central Tendency:** The **median** wall-clock time across the 5 timed repetitions is reported as the authoritative latency metric. Min and max latencies are tracked for dispersion analysis.
6. **Memory Profiling:**
   - CPU Memory: Process Resident Set Size (RSS) via `psutil`.
   - GPU Memory: Peak CUDA memory allocated via `torch.cuda.max_memory_allocated()`.

---

## 3. Comprehensive Benchmark Results

### 3.1 Summary Across Batch Sizes

The table below provides full results across all 8 models and all 3 volume tiers.

| Model Architecture | Batch Flows ($N$) | Target Device | Median Latency (ms) | Min Latency (ms) | Max Latency (ms) | Throughput (flows/s) | Peak CPU RSS (MB) | Peak GPU VRAM (MB) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Decision Tree** | 1,000 | CPU | 0.59 | 0.51 | 0.99 | 1,698,370 | 1,066.2 | 0.5 |
| Decision Tree | 10,000 | CPU | 1.86 | 1.68 | 5.41 | 5,372,589 | 1,175.9 | 8.9 |
| Decision Tree | 100,000 | CPU | 17.68 | 16.49 | 18.22 | 5,656,557 | 1,235.7 | 11.2 |
| **Random Forest** | 1,000 | CPU | 172.82 | 154.85 | 185.34 | 5,786 | 1,077.0 | 0.5 |
| Random Forest | 10,000 | CPU | 388.95 | 341.12 | 556.22 | 25,710 | 1,188.2 | 8.9 |
| Random Forest | 100,000 | CPU | 1,995.11 | 1,317.00 | 2,191.66 | 50,123 | 1,332.1 | 11.2 |
| **Linear SVC** | 1,000 | CPU | 0.76 | 0.56 | 1.37 | 1,319,435 | 1,075.3 | 0.5 |
| Linear SVC | 10,000 | CPU | 6.48 | 5.92 | 7.62 | 1,542,377 | 1,187.8 | 8.9 |
| Linear SVC | 100,000 | CPU | 70.32 | 62.63 | 108.16 | 1,422,056 | 1,333.8 | 11.2 |
| **IDSNet (MLP)** | 1,000 | GPU | 1.89 | 1.49 | 2.32 | 530,251 | 1,136.3 | 11.1 |
| IDSNet (MLP) | 10,000 | GPU | 1.22 | 1.03 | 1.98 | 8,181,967 | 1,187.8 | 28.3 |
| IDSNet (MLP) | 100,000 | GPU | 5.27 | 5.17 | 54.62 | 18,975,332 | 1,335.7 | 205.8 |
| **Stacking Ensemble** | 1,000 | Hybrid | 172.99 | 163.49 | 207.47 | 5,781 | 1,153.8 | 10.6 |
| Stacking Ensemble | 10,000 | Hybrid | 214.08 | 210.43 | 224.25 | 46,712 | 1,188.3 | 21.0 |
| Stacking Ensemble | 100,000 | Hybrid | 3,122.35 | 2,668.07 | 3,927.02 | 32,027 | 1,311.2 | 132.6 |
| **Autoencoder (Std)** | 1,000 | GPU | 1.33 | 0.99 | 1.50 | 749,906 | 1,153.8 | 10.3 |
| Autoencoder (Std) | 10,000 | GPU | 0.80 | 0.76 | 0.87 | 12,520,346 | 1,188.4 | 16.0 |
| Autoencoder (Std) | 100,000 | GPU | 15.12 | 13.00 | 19.94 | 6,612,226 | 1,311.2 | 73.7 |
| **Isolation Forest** | 1,000 | CPU | 55.12 | 43.28 | 107.41 | 18,143 | 1,153.8 | 8.9 |
| Isolation Forest | 10,000 | CPU | 197.46 | 181.53 | 213.50 | 50,644 | 1,188.4 | 11.2 |
| Isolation Forest | 100,000 | CPU | 1,807.06 | 1,548.36 | 1,962.19 | 55,338 | 1,297.4 | 34.9 |
| **FT-Transformer** | 1,000 | GPU (Chunk 4k) | 70.29 | 69.53 | 89.86 | 14,226 | 1,170.6 | 134.1 |
| FT-Transformer | 10,000 | GPU (Chunk 4k) | 695.02 | 694.51 | 695.15 | 14,388 | 1,188.4 | 1,211.2 |
| FT-Transformer | 100,000 | GPU (Chunk 4k) | 7,049.74 | 7,044.05 | 7,059.39 | 14,185 | 1,246.3 | 528.0 |

---

## 4. Architecture-by-Architecture Engineering Analysis

### 4.1 Decision Tree & Linear Models
- **Decision Tree:** Single tree traversal is trivially fast ($0.59\text{ ms}$ for 1k flows, $17.68\text{ ms}$ for 100k flows). However, single trees are brittle and lack regularization.
- **Linear SVC:** Matrix-vector multiplication scales linearly with batch size. Throughput exceeds $1.4\text{M flows/s}$ at 100k flows.

### 4.2 Neural Feedforward Models (IDSNet & Autoencoder)
- **Hardware Acceleration:** Highly optimized BLAS/GEMM kernels inside PyTorch CUDA allow IDSNet and Autoencoder to dominate high-throughput workloads.
- **Batch Scaling Efficiency:** For IDSNet, processing 10,000 flows takes *less* wall-clock time than 1,000 flows ($1.22\text{ ms}$ vs $1.89\text{ ms}$), reflecting GPU warp saturation where per-flow overhead decreases dramatically.
- **VRAM Footprint:** Both architectures require under $210\text{ MB}$ of VRAM even at 100k flows.

### 4.3 Tree Ensembles (Random Forest & Isolation Forest)
- **CPU Bottleneck:** Tree ensembles evaluate 100 trees per flow on CPU. While Scikit-Learn parallelizes tree evaluation across CPU threads, memory bandwidth and tree traversal branches limit throughput to $\approx 50,000\text{ flows/s}$.

### 4.4 Stacking Ensemble
- **Inference Pipeline:** Evaluates DT, RF, SVM, and IDSNet sequentially before feeding the meta-classifier.
- **Latency Driver:** Dominated by the RF base learner ($1.99\text{ s}$ out of $3.12\text{ s}$ total at 100k flows).

### 4.5 FT-Transformer
- **Computational Cost:** Evaluates multi-head self-attention ($O(L^2)$ where $L=70$ tokens) per flow across 3 layers.
- **Chunked Processing:** Chunking into mini-batches of 4,096 flows successfully prevented out-of-memory errors on a 4GB GPU, achieving steady throughput of $\approx 14,200\text{ flows/s}$.

---

## 5. Architectural Recommendations for Edge & Gateway Deployment

1. **Inline Edge Filtering ($10\text{ Gbps}$ / Line-Rate):**
   - High-throughput neural models (IDSNet MLP or compressed Linear models) are the only architectures capable of sustaining multi-million flows/sec inference.
2. **Secondary Deep Analysis Pipeline:**
   - Tree ensembles (Random Forest, Isolation Forest) and FT-Transformer should be relegated to asynchronous out-of-band analysis clusters where latencies on the order of hundreds of milliseconds are tolerable.
