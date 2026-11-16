# Three-Condition Comparative Evaluation: `google__gson-2061`

**Verified Target Commit:** `be0a1f4ff74bcd01580887cc9f3ec592d773f24c` (Remove Gradle build support (#2063))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 7 (7 Source, 0 SootUp MCP) | 3 (3 Source, 0 SootUp MCP) | 26 (20 Source, 6 SootUp MCP) |
| **Total Tokens** | 51433 | 11688 | 345152 |
| **Latency** | 21.7s | 16.8s | 87.2s |