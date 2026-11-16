# Three-Condition Comparative Evaluation: `google__gson-1093`

**Verified Target Commit:** `0aaef0fd1bb1b9729543dc40168adfb829eb75a4` ([maven-release-plugin] prepare for next development iteration)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 5 (5 Source, 0 SootUp MCP) | 4 (4 Source, 0 SootUp MCP) | 20 (16 Source, 4 SootUp MCP) |
| **Total Tokens** | 32495 | 24953 | 250489 |
| **Latency** | 11.0s | 10.8s | 102.0s |