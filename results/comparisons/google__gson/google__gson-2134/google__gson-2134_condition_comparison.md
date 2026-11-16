# Three-Condition Comparative Evaluation: `google__gson-2134`

**Verified Target Commit:** `96ab171eb48dcea94fd9b8f425f65c531e6c3aad` (Add explicit support for floats in JsonWriter. (#2130))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 3 (3 Source, 0 SootUp MCP) | 8 (5 Source, 3 SootUp MCP) |
| **Total Tokens** | 9474 | 20564 | 98552 |
| **Latency** | 11.6s | 23.1s | 43.5s |