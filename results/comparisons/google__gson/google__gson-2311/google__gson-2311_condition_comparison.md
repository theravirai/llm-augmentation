# Three-Condition Comparative Evaluation: `google__gson-2311`

**Verified Target Commit:** `9f26679e7a96f0bb9952c326b2d9f79ef03ea9f5` (Adds Error Prone to the `maven-compiler-plugin` (#2308))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 9 (7 Source, 2 SootUp MCP) |
| **Total Tokens** | 7895 | 8299 | 90398 |
| **Latency** | 12.6s | 9.6s | 29.5s |