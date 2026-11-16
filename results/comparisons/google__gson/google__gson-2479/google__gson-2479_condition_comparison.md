# Three-Condition Comparative Evaluation: `google__gson-2479`

**Verified Target Commit:** `4dfae77af3d543bea2782f85a154cc070290f086` (Bump com.github.siom79.japicmp:japicmp-maven-plugin (#2504))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 13 (13 Source, 0 SootUp MCP) | 8 (8 Source, 0 SootUp MCP) | 27 (22 Source, 5 SootUp MCP) |
| **Total Tokens** | 91913 | 66307 | 430906 |
| **Latency** | 30.2s | 20.9s | 68.2s |