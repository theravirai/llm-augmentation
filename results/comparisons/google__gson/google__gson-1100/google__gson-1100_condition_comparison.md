# Three-Condition Comparative Evaluation: `google__gson-1100`

**Verified Target Commit:** `f0aa1118e9ef66ed324f9a63cdfb551cb4e9eca5` (Java protobuf uses lower camel for all field names. When using reflection to find the generic type of repeated fields, can't use the user specified formats for field name conversion. (#1119))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 23 (15 Source, 8 SootUp MCP) |
| **Total Tokens** | 6347 | 9806 | 309570 |
| **Latency** | 16.7s | 11.9s | 67.6s |