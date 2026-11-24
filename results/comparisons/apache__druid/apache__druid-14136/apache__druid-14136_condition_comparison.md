# Three-Condition Comparative Evaluation: `apache__druid-14136`

**Verified Target Commit:** `a7d4162195a630c380d75516c24229cc23e25271` (Compaction: Block input specs not aligned with segmentGranularity. (#14127))

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 33% | 33% | 33% |
| **File Precision** | 100% | 100% | 50% |
| **Exact Match** | ❌ No | ❌ No | ❌ No |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Min Line Distance** | 12.0 lines | 12.0 lines | 12.0 lines |
| **Fault Window Localized (≤25 lines)** | ❌ No | ❌ No | ❌ No |
| **Tool Calls Breakdown** | 8 (8 Source, 0 SootUp MCP) | 8 (8 Source, 0 SootUp MCP) | 12 (9 Source, 3 SootUp MCP) |
| **Total Tokens** | 59817 | 69291 | 143012 |
| **Latency** | 27.6s | 32.0s | 35.9s |