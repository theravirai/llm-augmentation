# Three-Condition Comparative Evaluation: `google__gson-2158`

**Verified Target Commit:** `796193d0326a2f44bc314bf24262732ea3e64014` (Improve versioning support documentation and validate version (#2214))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | N/A | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 6 (6 Source, 0 SootUp MCP) | 26 (26 Source, 0 SootUp MCP) | 17 (16 Source, 1 SootUp MCP) |
| **Total Tokens** | 20568 | 366080 | 196973 |
| **Latency** | 19.7s | 72.0s | 81.0s |