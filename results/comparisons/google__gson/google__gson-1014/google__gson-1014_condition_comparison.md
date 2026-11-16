# Three-Condition Comparative Evaluation: `google__gson-1014`

**Verified Target Commit:** `7719e73a108c450666613c279bedaed724cd9cc9` (Merge pull request #1012 from BloodShura/master)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 5 (5 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 29 (24 Source, 5 SootUp MCP) |
| **Total Tokens** | 26853 | 10377 | 350348 |
| **Latency** | 18.9s | 13.1s | 91.5s |