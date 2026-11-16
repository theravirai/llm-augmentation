# Three-Condition Comparative Benchmark Evaluation: `google/gson`

> **Thesis Experiment Summary:** Evaluation of Fault Localization performance across all 9 SWE-Bench Java benchmark instances for `google/gson` under three experimental conditions using `gpt-oss-120b`.

- **Subject Model:** `gpt-oss-120b` (University of Paderborn AI Gateway)
- **Benchmark Suite:** SWE-Bench Java (`google/gson`) — 9 Defects
- **Evaluation Date:** November 2026
- **Conditions Compared:**
  - **Condition A (Baseline):** Repository Source Navigation Tools only (`find_files`, `list_directory`, `search_source_code`, `read_source_file`).
  - **Condition B (Precomputed Static Injection):** Ahead-of-Time (AOT) precomputed SootUp static bytecode facts injected into prompt + Source Navigation Tools.
  - **Condition C (On-Demand MCP):** Interactive multi-turn tool calling over Model Context Protocol (MCP) using live SootUp static analysis tools + Source Navigation Tools.

---

## 1. Overall Aggregated Benchmark Summary (N = 9 Tasks)

| Evaluation Dimension / Metric | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **Mean File Recall** | **83.3%** | **83.3%** | **83.3%** |
| **Mean File Precision** | **100.0%** | **100.0%** | **100.0%** |
| **Mean File F1-Score** | **88.9%** | **88.9%** | **88.9%** |
| **Exact File Match Rate** | **66.7%** (6/9) | **66.7%** (6/9) | **66.7%** (6/9) |
| **Method Hit Rate** | **55.6%** (5/9) | **55.6%** (5/9) | **55.6%** (5/9) |
| **Fault Window Localized Rate (≤25 lines)** | **66.7%** (6/9) | **66.7%** (6/9) | **66.7%** (6/9) |
| **Average Total Tokens / Task** | 23,469 tokens | 41,564 tokens | 81,660 tokens |
| **Average Tool Calls / Task** | 4.4 (4.4 Source, 0 SootUp) | 4.8 (4.8 Source, 0 SootUp) | 8.6 (6.6 Source, 2.0 SootUp) |
| **Average Execution Latency / Task** | 12.1s | 41.8s | 27.7s |

---

## 2. Multi-Task Comparative Matrix

| Task ID | Verified Base Commit | Scope | Recall (A / B / C) | Exact Match | Min Line Proximity (A / B / C) | SootUp Calls (C) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`google__gson-1014`](#googlegson-1014) | `7719e73a10` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-1093`](#googlegson-1093) | `0aaef0fd1b` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-1100`](#googlegson-1100) | `f0aa1118e9` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 2 |
| [`google__gson-2024`](#googlegson-2024) | `16b42ff580` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 2.0 / 3.0 / 3.0 | 3 |
| [`google__gson-2061`](#googlegson-2061) | `be0a1f4ff7` | Multi-file (2) | 50% / 50% / 50% | ❌ / ❌ / ❌ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-2134`](#googlegson-2134) | `96ab171eb4` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 95.0 | 1 |
| [`google__gson-2158`](#googlegson-2158) | `796193d032` | Multi-file (2) | 50% / 50% / 50% | ❌ / ❌ / ❌ | 0.0 / 0.0 / 0.0 | 6 |
| [`google__gson-2311`](#googlegson-2311) | `9f26679e7a` | Single-file (1) | 100% / 100% / 100% | ✅ / ✅ / ✅ | 0.0 / 0.0 / 0.0 | 1 |
| [`google__gson-2479`](#googlegson-2479) | `4dfae77af3` | Multi-file (2) | 50% / 50% / 50% | ❌ / ❌ / ❌ | 0.0 / 0.0 / 0.0 | 2 |

---

## 3. Individual Task Comparison Reports

### 3.1. Three-Condition Comparative Evaluation: `google__gson-1014` <a id="googlegson-1014"></a>


**Verified Target Commit:** `7719e73a108c450666613c279bedaed724cd9cc9` (Merge pull request #1012 from BloodShura/master)

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

### 3.2. Three-Condition Comparative Evaluation: `google__gson-1093` <a id="googlegson-1093"></a>


**Verified Target Commit:** `0aaef0fd1bb1b9729543dc40168adfb829eb75a4` ([maven-release-plugin] prepare for next development iteration)

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

### 3.3. Three-Condition Comparative Evaluation: `google__gson-1100` <a id="googlegson-1100"></a>


**Verified Target Commit:** `f0aa1118e9ef66ed324f9a63cdfb551cb4e9eca5` (Java protobuf uses lower camel for all field names. When using reflection to find the generic type of repeated fields, can't use the user specified formats for field name conversion. (#1119))

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

### 3.4. Three-Condition Comparative Evaluation: `google__gson-2024` <a id="googlegson-2024"></a>


**Verified Target Commit:** `16b42ff5805074126c2e5484450c182773e408a2` (Update Caliper dependency; disable automatic result upload (#2019))

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

### 3.5. Three-Condition Comparative Evaluation: `google__gson-2061` <a id="googlegson-2061"></a>


**Verified Target Commit:** `be0a1f4ff74bcd01580887cc9f3ec592d773f24c` (Remove Gradle build support (#2063))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 50% | 50% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ❌ No | ❌ No |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ❌ No | ❌ No |
| **Tool Calls Breakdown** | 7 (7 Source, 0 SootUp MCP) | 5 (5 Source, 0 SootUp MCP) | 5 (4 Source, 1 SootUp MCP) |
| **Total Tokens** | 45242 | 32768 | 46170 |
| **Latency** | 10.0s | 40.1s | 15.3s |


---

### 3.6. Three-Condition Comparative Evaluation: `google__gson-2134` <a id="googlegson-2134"></a>


**Verified Target Commit:** `96ab171eb48dcea94fd9b8f425f65c531e6c3aad` (Add explicit support for floats in JsonWriter. (#2130))

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

### 3.7. Three-Condition Comparative Evaluation: `google__gson-2158` <a id="googlegson-2158"></a>


**Verified Target Commit:** `796193d0326a2f44bc314bf24262732ea3e64014` (Improve versioning support documentation and validate version (#2214))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 50% | 50% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ❌ No | ❌ No |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ❌ No | ❌ No |
| **Tool Calls Breakdown** | 6 (6 Source, 0 SootUp MCP) | 14 (14 Source, 0 SootUp MCP) | 27 (21 Source, 6 SootUp MCP) |
| **Total Tokens** | 20552 | 158225 | 229749 |
| **Latency** | 36.9s | 85.5s | 103.8s |


---

### 3.8. Three-Condition Comparative Evaluation: `google__gson-2311` <a id="googlegson-2311"></a>


**Verified Target Commit:** `9f26679e7a96f0bb9952c326b2d9f79ef03ea9f5` (Adds Error Prone to the `maven-compiler-plugin` (#2308))

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

### 3.9. Three-Condition Comparative Evaluation: `google__gson-2479` <a id="googlegson-2479"></a>


**Verified Target Commit:** `4dfae77af3d543bea2782f85a154cc070290f086` (Bump com.github.siom79.japicmp:japicmp-maven-plugin (#2504))

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
