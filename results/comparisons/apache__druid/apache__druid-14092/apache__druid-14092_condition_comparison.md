# Three-Condition Comparative Evaluation: `apache__druid-14092`

**Verified Target Commit:** `4fffee17761286996a8c43154b72db4bcaafb16d` (Web console: better lookup 404 detection (#14108))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 17.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 12 (8 Source, 4 SootUp MCP) |
| **Total Tokens** | 7708 | 8561 | 127873 |
| **Latency** | 7.9s | 27.8s | 67.2s |