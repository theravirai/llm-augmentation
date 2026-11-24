# Three-Condition Comparative Evaluation: `apache__druid-16875`

**Verified Target Commit:** `483a03f26c7221f10493d86715985a58e61af967` (Web console: Server context defaults (#16868))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 0% | 100% | 100% |
| **File Precision** | 0% | 50% | 50% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | N/A | 0.0 lines | 0.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ✅ Yes |
| **Tool Calls Breakdown** | 27 (27 Source, 0 SootUp MCP) | 26 (26 Source, 0 SootUp MCP) | 24 (21 Source, 3 SootUp MCP) |
| **Total Tokens** | 354995 | 309943 | 337669 |
| **Latency** | 79.5s | 87.2s | 59.5s |