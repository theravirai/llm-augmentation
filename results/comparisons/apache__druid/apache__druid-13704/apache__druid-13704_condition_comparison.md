# Three-Condition Comparative Evaluation: `apache__druid-13704`

**Verified Target Commit:** `51dfde02840017092486fb75be2b16566aff6a19` (Add maxInputBytesPerWorker as query context parameter (#13707))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 100% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Method Hit** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Min Line Distance** | 0.0 lines | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 2 (2 Source, 0 SootUp MCP) | 2 (2 Source, 0 SootUp MCP) | 15 (12 Source, 3 SootUp MCP) |
| **Total Tokens** | 8749 | 9549 | 160481 |
| **Latency** | 11.1s | 38.4s | 44.6s |