# Three-Condition Comparative Benchmark Evaluation: `google/gson`

> **Thesis Research Report:** Quantitative comparative evaluation of Fault Localization (FL) performance across all 9 SWE-Bench Java benchmark instances for `google/gson` using the `gpt-oss-120b` large language model.

- **Subject Model:** `gpt-oss-120b` (Hosted on University of Paderborn AI Gateway)
- **Target Repository:** [`google/gson`](https://github.com/google/gson)
- **Benchmark Suite:** SWE-Bench Java (`google/gson`) — 9 Defect Tasks
- **Evaluation Date:** November 2026
- **Core Objective:** Investigate whether augmenting LLM reasoning with deterministic whole-program static analysis facts (extracted via **SootUp 3.x** and the **Model Context Protocol**) overcomes syntactic search-space tunnel vision and improves multi-file fault localization over source-code-only baselines.

---

## 1. Executive Guide: Experimental Setup & Metric Definitions

This section defines the experimental conditions and quantitative evaluation metrics used throughout this report. It is designed to provide immediate context without requiring external documentation.

### 1.1. Scope Boundary: Fault Localization (FL) vs. Automated Program Repair (APR)
This empirical study focuses strictly on **Fault Localization (FL)**—the task of accurately diagnosing *which files, methods, and exact line ranges contain the root-cause defect* given a developer bug report. It does **not** perform code synthesis, automated program repair (APR), or patch generation. Metrics measure how closely the model's diagnosed fault window matches the actual developer ground-truth fix.

### 1.2. The Three Experimental Conditions

| Condition | Setup & Context Provided | Interaction Mode | MCP Server Required? | Purpose & Research Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Condition A**<br>*(Baseline - Source Only)* | Natural-language bug statement + Local repository source navigation tools (`find_files`, `list_directory`, `search_source_code`, `read_source_file`). | Autonomous Multi-turn ReAct Loop (Source tools only) | **No** | Quantify baseline LLM localization performance when relying purely on syntactic pattern matching and grep-like source exploration without static analysis. |
| **Condition B**<br>*(Precomputed Static Injection)* | Bug statement + Source navigation tools + **Ahead-of-Time (AOT) precomputed SootUp static bytecode facts** (class hierarchies, object allocation sites) injected into the initial user prompt. | Autonomous Multi-turn ReAct Loop (Offline facts + Source tools) | **No** (Decoupled offline cache) | Test traditional passive RAG/injection architectures to determine if static facts in prompt context mitigate or trigger **LLM Confirmation Bias** (ignoring conflicting facts). |
| **Condition C**<br>*(On-Demand MCP Tools)* | Bug statement + Source navigation tools + **Live SootUp static analysis tools exposed dynamically via the Model Context Protocol (MCP)** over `stdio` JSON-RPC. | Autonomous Multi-turn Joint Source & Static Tool Calling | **Yes** (Java `SootUpMcpServer` subprocess) | Evaluate whether interactive, on-demand bytecode queries (`sootup_inspect_method`, `sootup_hierarchy`, `sootup_find_allocations`) enable the agent to uncover hidden classes and multi-file dependencies. |

### 1.3. Evaluation Metrics & Dimensions

#### Research Question 1 (RQ1): Localization Accuracy
- **File Recall ($\text{Recall}_{\text{file}}$):** The percentage of ground-truth modified Java files ($F_{\text{gold}}$) that were correctly identified in the model's diagnosis ($F_{\text{pred}}$). A recall of $100\%$ indicates that all defect files were successfully located.
- **File Precision ($\text{Precision}_{\text{file}}$):** The proportion of model-predicted files that actually contained the defect ($|F_{\text{pred}} \cap F_{\text{gold}}| / |F_{\text{pred}}|$). A precision of $100\%$ indicates zero false-positive or irrelevant files were flagged.
- **File F1-Score ($\text{F1}_{\text{file}}$):** The harmonic mean of File Recall and File Precision ($2 \times \frac{\text{Recall} \times \text{Precision}}{\text{Recall} + \text{Precision}}$).
- **Exact File Match:** A strict binary indicator (✅ Yes / ❌ No). True if and only if the model predicted the exact set of modified files with zero omissions and zero extraneous files ($\text{Recall} = 100\%$ and $\text{Precision} = 100\%$).
- **Method Hit:** A binary indicator (✅ Yes / ❌ No). Evaluates whether at least one of the model's localized method signatures matches the enclosing method modified in the developer's gold patch hunk headers (`@@ ... @@ methodSignature`).
- **Min Line Proximity (Line Distance):** The minimum absolute distance (in lines) between the model's localized lines and the ground-truth patch edit hunks ($L_{\text{gold}}$). A distance of `0.0 lines` represents an exact hit inside or on the boundary of the defect edit hunk.
- **Fault Window Localized ($\le 25$ lines):** A binary indicator (✅ Yes / ❌ No) confirming that the model achieved an Exact File Match and localized the root-cause within a standard 25-line inspection window ($d_{\text{min}} \le 25$). Replaces misleading 'Patch Resolved' terminology.

#### Research Question 2 (RQ2): Cost, Efficiency & Tool Overhead
- **Tool Calls Breakdown:** Total count of tool invocations executed during the ReAct loop, explicitly separated into **Source Navigation Calls** (`find_files`, `read_source_file`, `search_source_code`) vs. **SootUp MCP Static Analysis Calls** (`sootup_inspect_method`, `sootup_hierarchy`, `sootup_find_allocations`).
- **Total Tokens:** Cumulative token consumption across all conversational turns (Prompt Tokens + Completion Tokens).
- **Execution Latency:** Total wall-clock time in seconds ($S_{\text{latency}}$) required to complete the multi-turn diagnosis.
- **Verified Target Commit:** The exact unpatched Git commit hash (`base_commit`) checked out before evaluation began, verified directly via `git rev-parse HEAD` to guarantee experimental provenance.

---

## 2. Overall Aggregated Benchmark Summary (N = 9 Tasks)

| Evaluation Dimension / Metric | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **Mean File Recall** | **83.3%** | **94.4%** | **94.4%** |
| **Mean File Precision** | **100.0%** | **100.0%** | **100.0%** |
| **Mean File F1-Score** | **90.9%** | **97.1%** | **97.1%** |
| **Exact File Match Rate** | **66.7%** (6/9) | **88.9%** (8/9) | **88.9%** (8/9) |
| **Method Hit Rate** | **55.6%** (5/9) | **55.6%** (5/9) | **55.6%** (5/9) |
| **Fault Window Localized Rate (≤25 lines)** | **66.7%** (6/9) | **88.9%** (8/9) | **88.9%** (8/9) |
| **Average Total Tokens / Task** | 22,886 tokens | 38,998 tokens | 85,134 tokens |
| **Average Tool Calls / Task** | 4.2 (4.2 Source, 0 SootUp) | 4.7 (4.7 Source, 0 SootUp) | 7.6 (5.2 Source, 2.3 SootUp) |
| **Average Execution Latency / Task** | 12.6s | 38.4s | 28.1s |

---

## 3. Multi-Task Comparative Matrix

| Task ID | Verified Base Commit | GitHub Commit | GitHub Issue | Scope | Recall (A / B / C) | Exact Match | Min Line Proximity (A / B / C) | SootUp Calls (C) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`google__gson-1014`](#googlegson-1014) | `7719e73a` | [`7719e73a` ↗](https://github.com/google/gson/commit/7719e73a108c450666613c279bedaed724cd9cc9) | [#1014 ↗](https://github.com/google/gson/issues/1014) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-1093`](#googlegson-1093) | `0aaef0fd` | [`0aaef0fd` ↗](https://github.com/google/gson/commit/0aaef0fd1bb1b9729543dc40168adfb829eb75a4) | [#1093 ↗](https://github.com/google/gson/issues/1093) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-1100`](#googlegson-1100) | `f0aa1118` | [`f0aa1118` ↗](https://github.com/google/gson/commit/f0aa1118e9ef66ed324f9a63cdfb551cb4e9eca5) | [#1100 ↗](https://github.com/google/gson/issues/1100) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 2 |
| [`google__gson-2024`](#googlegson-2024) | `16b42ff5` | [`16b42ff5` ↗](https://github.com/google/gson/commit/16b42ff5805074126c2e5484450c182773e408a2) | [#2024 ↗](https://github.com/google/gson/issues/2024) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 2.0 / 3.0 / 3.0 | 3 |
| [`google__gson-2061`](#googlegson-2061) | `be0a1f4f` | [`be0a1f4f` ↗](https://github.com/google/gson/commit/be0a1f4ff74bcd01580887cc9f3ec592d773f24c) | [#2061 ↗](https://github.com/google/gson/issues/2061) | Multi-file (2) | 50% / 100% / 100% | ❌ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 7 |
| [`google__gson-2134`](#googlegson-2134) | `96ab171e` | [`96ab171e` ↗](https://github.com/google/gson/commit/96ab171eb48dcea94fd9b8f425f65c531e6c3aad) | [#2134 ↗](https://github.com/google/gson/issues/2134) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 95.0 | 1 |
| [`google__gson-2158`](#googlegson-2158) | `796193d0` | [`796193d0` ↗](https://github.com/google/gson/commit/796193d0326a2f44bc314bf24262732ea3e64014) | [#2158 ↗](https://github.com/google/gson/issues/2158) | Multi-file (2) | 50% / 100% / 100% | ❌ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 3 |
| [`google__gson-2311`](#googlegson-2311) | `9f26679e` | [`9f26679e` ↗](https://github.com/google/gson/commit/9f26679e7a96f0bb9952c326b2d9f79ef03ea9f5) | [#2311 ↗](https://github.com/google/gson/issues/2311) | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-2479`](#googlegson-2479) | `4dfae77a` | [`4dfae77a` ↗](https://github.com/google/gson/commit/4dfae77af3d543bea2782f85a154cc070290f086) | [#2479 ↗](https://github.com/google/gson/issues/2479) | Multi-file (2) | 50% / 50% / 50% | ❌ / ❌ / ❌ | 0.0 / 0.0 / 0.0 | 2 |

---

## 4. Individual Task Benchmark Reports

### 4.1. Three-Condition Comparative Evaluation: `google__gson-1014` <a id="googlegson-1014"></a>


**Verified Target Commit:** [`7719e73a108c450666613c279bedaed724cd9cc9` ↗](https://github.com/google/gson/commit/7719e73a108c450666613c279bedaed724cd9cc9) (Merge pull request #1012 from BloodShura/master) | **GitHub Issue:** [#1014 ↗](https://github.com/google/gson/issues/1014)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 5 (5 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 3 (2 Source, 1 SootUp MCP) |
| **Total Tokens** | 27003 | 13935 | 24237 |
| **Latency** | 9.9s | 5.5s | 12.5s |


---

### 4.2. Three-Condition Comparative Evaluation: `google__gson-1093` <a id="googlegson-1093"></a>


**Verified Target Commit:** [`0aaef0fd1bb1b9729543dc40168adfb829eb75a4` ↗](https://github.com/google/gson/commit/0aaef0fd1bb1b9729543dc40168adfb829eb75a4) ([maven-release-plugin] prepare for next development iteration) | **GitHub Issue:** [#1093 ↗](https://github.com/google/gson/issues/1093)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 3 (3 Source, 0 SootUp MCP) | 5 (5 Source, 0 SootUp MCP) | 6 (5 Source, 1 SootUp MCP) |
| **Total Tokens** | 16122 | 43202 | 57516 |
| **Latency** | 5.1s | 31.9s | 14.3s |


---

### 4.3. Three-Condition Comparative Evaluation: `google__gson-1100` <a id="googlegson-1100"></a>


**Verified Target Commit:** [`f0aa1118e9ef66ed324f9a63cdfb551cb4e9eca5` ↗](https://github.com/google/gson/commit/f0aa1118e9ef66ed324f9a63cdfb551cb4e9eca5) (Java protobuf uses lower camel for all field names. When using reflection to find the generic type of repeated fields, can't use the user specified formats for field name conversion. (#1119)) | **GitHub Issue:** [#1100 ↗](https://github.com/google/gson/issues/1100)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 5 (5 Source, 0 SootUp MCP) | 4 (4 Source, 0 SootUp MCP) | 7 (5 Source, 2 SootUp MCP) |
| **Total Tokens** | 17702 | 22831 | 47056 |
| **Latency** | 8.4s | 46.3s | 16.7s |


---

### 4.4. Three-Condition Comparative Evaluation: `google__gson-2024` <a id="googlegson-2024"></a>


**Verified Target Commit:** [`16b42ff5805074126c2e5484450c182773e408a2` ↗](https://github.com/google/gson/commit/16b42ff5805074126c2e5484450c182773e408a2) (Update Caliper dependency; disable automatic result upload (#2019)) | **GitHub Issue:** [#2024 ↗](https://github.com/google/gson/issues/2024)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 2.0 lines | 3.0 lines | 3.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 5 (2 Source, 3 SootUp MCP) |
| **Total Tokens** | 6758 | 12170 | 32387 |
| **Latency** | 4.9s | 36.7s | 15.8s |


---

### 4.5. Three-Condition Comparative Evaluation: `google__gson-2061` <a id="googlegson-2061"></a>


**Verified Target Commit:** [`be0a1f4ff74bcd01580887cc9f3ec592d773f24c` ↗](https://github.com/google/gson/commit/be0a1f4ff74bcd01580887cc9f3ec592d773f24c) (Remove Gradle build support (#2063)) | **GitHub Issue:** [#2061 ↗](https://github.com/google/gson/issues/2061)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 8 (8 Source, 0 SootUp MCP) | 4 (4 Source, 0 SootUp MCP) | 15 (8 Source, 7 SootUp MCP) |
| **Total Tokens** | 54661 | 13370 | 178872 |
| **Latency** | 31.5s | 20.2s | 40.5s |


---

### 4.6. Three-Condition Comparative Evaluation: `google__gson-2134` <a id="googlegson-2134"></a>


**Verified Target Commit:** [`96ab171eb48dcea94fd9b8f425f65c531e6c3aad` ↗](https://github.com/google/gson/commit/96ab171eb48dcea94fd9b8f425f65c531e6c3aad) (Add explicit support for floats in JsonWriter. (#2130)) | **GitHub Issue:** [#2134 ↗](https://github.com/google/gson/issues/2134)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 95.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 3 (3 Source, 0 SootUp MCP) | 3 (3 Source, 0 SootUp MCP) | 5 (4 Source, 1 SootUp MCP) |
| **Total Tokens** | 16471 | 24206 | 57811 |
| **Latency** | 11.7s | 49.2s | 31.6s |


---

### 4.7. Three-Condition Comparative Evaluation: `google__gson-2158` <a id="googlegson-2158"></a>


**Verified Target Commit:** [`796193d0326a2f44bc314bf24262732ea3e64014` ↗](https://github.com/google/gson/commit/796193d0326a2f44bc314bf24262732ea3e64014) (Improve versioning support documentation and validate version (#2214)) | **GitHub Issue:** [#2158 ↗](https://github.com/google/gson/issues/2158)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 3 (3 Source, 0 SootUp MCP) | 18 (18 Source, 0 SootUp MCP) | 15 (12 Source, 3 SootUp MCP) |
| **Total Tokens** | 8207 | 181042 | 189818 |
| **Latency** | 15.4s | 77.0s | 85.7s |


---

### 4.8. Three-Condition Comparative Evaluation: `google__gson-2311` <a id="googlegson-2311"></a>


**Verified Target Commit:** [`9f26679e7a96f0bb9952c326b2d9f79ef03ea9f5` ↗](https://github.com/google/gson/commit/9f26679e7a96f0bb9952c326b2d9f79ef03ea9f5) (Adds Error Prone to the `maven-compiler-plugin` (#2308)) | **GitHub Issue:** [#2311 ↗](https://github.com/google/gson/issues/2311)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 3 (2 Source, 1 SootUp MCP) |
| **Total Tokens** | 7825 | 18307 | 24282 |
| **Latency** | 10.1s | 36.6s | 13.6s |


---

### 4.9. Three-Condition Comparative Evaluation: `google__gson-2479` <a id="googlegson-2479"></a>


**Verified Target Commit:** [`4dfae77af3d543bea2782f85a154cc070290f086` ↗](https://github.com/google/gson/commit/4dfae77af3d543bea2782f85a154cc070290f086) (Bump com.github.siom79.japicmp:japicmp-maven-plugin (#2504)) | **GitHub Issue:** [#2479 ↗](https://github.com/google/gson/issues/2479)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 50% | 50% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ❌ No | ❌ No |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ❌ No | ❌ No |
| **Tool Calls Breakdown** | 7 (7 Source, 0 SootUp MCP) | 6 (6 Source, 0 SootUp MCP) | 16 (14 Source, 2 SootUp MCP) |
| **Total Tokens** | 53547 | 48432 | 215731 |
| **Latency** | 11.5s | 44.0s | 25.5s |


---
