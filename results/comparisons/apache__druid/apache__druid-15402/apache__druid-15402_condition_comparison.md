# Three-Condition Comparative Evaluation: `apache__druid-15402`

**Verified Target Commit:** `1df53d6eb30a019fff69a5ff7533ebbd998a438d` (fix physical memory detection on OSX (#15405))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 15 (15 Source, 0 SootUp MCP) | 11 (11 Source, 0 SootUp MCP) | 29 (24 Source, 5 SootUp MCP) |
| **Total Tokens** | 135636 | 100073 | 419935 |
| **Latency** | 31.0s | 35.8s | 80.8s |