# Three-Condition Comparative Evaluation: `google__gson-2024`

**Verified Target Commit:** `16b42ff5805074126c2e5484450c182773e408a2` (Update Caliper dependency; disable automatic result upload (#2019))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 13.0 lines | 3.0 lines | 3.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 3 (3 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 13 (11 Source, 2 SootUp MCP) |
| **Total Tokens** | 11208 | 8776 | 111166 |
| **Latency** | 13.2s | 9.6s | 63.1s |