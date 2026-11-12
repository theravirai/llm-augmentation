# Running Experiments: Conditions A, B, and C

This guide explains how to design, execute, and analyze fault localization experiments across the three experimental conditions investigated in the thesis.

---

## 1. Experimental Conditions Comparison

| Dimension | Condition A: Baseline (Source) | Condition B: Precomputed Static Injection (AOT) | Condition C: Active Tool Calling (MCP) |
| :--- | :--- | :--- | :--- |
| **Input Context** | Bug statement + source tools | Bug statement + precomputed static facts + tools | Bug statement + source tools + live SootUp MCP |
| **Static Bytecode Facts** | None | Ahead-of-Time precomputed facts (Offline cache) | Dynamic on-demand queries via JSON-RPC `stdio` |
| **Interaction Mode** | Multi-turn Source ReAct Loop | Multi-turn Source Verification Loop | Multi-turn Joint Source & Static Tool Calling |
| **Tools Available** | `find_files`, `list_directory`, `search_source_code`, `read_source_file` | `find_files`, `list_directory`, `search_source_code`, `read_source_file` | Source tools + `sootup_hierarchy`, `inspect_method`, `find_allocations`, etc. |
| **MCP Server Required?** | No | No (Decoupled; zero MCP dependency) | Yes (Java `SootUpMcpServer` subprocess) |
| **Primary Failure Mode** | Token-level heuristic tunnel vision | Confirmation Bias (model ignores static facts) | Tool latency / tool selection prioritization |
| **Token Budget** | ~20k–40k tokens | Medium (static summaries injected into prompt) | Flexible (depends on tool calling depth) |

---

## 2. Condition A: Source Only Baseline

### Concept & Scientific Purpose
Condition A provides the LLM with the natural-language problem statement, repository slug, base commit, and active repository inspection tools (`find_files`, `list_directory`, `search_source_code`, `read_source_file`). No static analysis tools or bytecode facts are provided.
* **Goal:** Quantify the baseline failure rate caused by token-level heuristics and search-space tunnel vision when reasoning over decoupled Java architectures without static analysis.

### Agent Implementation Details
Defined in [`ConditionAAgent`](../llm_augmentation/agents/condition_a_agent.py):
1. Injects `SYSTEM_PROMPT` defining repository navigation tools and the required JSON diagnostic format.
2. Runs a multi-turn ReAct loop (up to `max_tool_iterations = 30`).
3. Executes tool calls via `SourceToolsExecutor` safely over the local repository.
4. Concludes with structured diagnostic JSON extraction.

### Execution Command
```bash
python3 -m llm_augmentation.cli run -c A -t google__gson-2158
```

---

## 3. Condition B: Precomputed Static Injection (AOT)

### Concept & Scientific Purpose
Condition B precomputes static analysis summaries using SootUp ahead of time (AOT) and dumps them directly into the initial user prompt context.
* **Goal:** Test whether passive static fact injection (traditional RAG approach) suffers from **LLM Confirmation Bias** — where the model holds strong syntactic priors and actively disregards conflicting static facts.

### Agent Implementation Details
Defined in [`ConditionBAgent`](../llm_augmentation/agents/condition_b_agent.py):
1. **Decoupled from MCP:** Checks for precomputed facts in `datasets/precomputed_facts/{task_id}.txt`.
2. If not cached, invokes the standalone Java CLI (`org.sootup.analyzer.SootUpAnalyzer`) directly to extract class hierarchies and object allocations (zero MCP, zero JSON-RPC runtime dependency).
3. Injects facts into the initial prompt under `### Deterministic Static Analysis Facts (SootUp Bytecode Extractor):`.
4. Equips the model with source navigation tools (`read_source_file`, `search_source_code`) to verify exact line ranges.

### Execution Command
```bash
python3 -m llm_augmentation.cli run -c B -t google__gson-2158
```

---

## 4. Condition C: Active On-Demand Tool Calling (MCP)

### Concept & Scientific Purpose
Condition C equips the model with live SootUp static analysis tools exposed via the Model Context Protocol (MCP) in an autonomous multi-turn ReAct loop.
* **Goal:** Test whether selective, on-demand querying allows the agent to validate hypotheses dynamically, pivot its search space upon discovering hidden anonymous classes, and achieve gold patch parity.

### Agent Implementation Details
Defined in [`ConditionCAgent`](../llm_augmentation/agents/condition_c_agent.py):
1. Spawns `SootUpMcpServer` over `stdio` subprocess.
2. Exposes **two complementary tool suites**:
   - Repository Navigation Tools: `find_files`, `list_directory`, `search_source_code`, `read_source_file`.
   - SootUp Bytecode Static Tools: `sootup_hierarchy`, `sootup_inspect_method`, `sootup_find_allocations`, `sootup_find_invocations`, `sootup_callgraph`.
3. Loops up to `max_tool_iterations = 30`, recording tool latency, arguments, and responses.
4. Captures the full turn trajectory into `*_trace.json`.

### Execution Command
```bash
python3 -m llm_augmentation.cli run -c C -t google__gson-2158
```

---

## 5. Automated Three-Condition Comparison

To run an apples-to-apples comparison of Conditions A, B, and C on a specific defect:

```bash
python3 -m llm_augmentation.cli compare -t google__gson-2158
```

This generates `results/comparisons/google__gson-2158/google__gson-2158_condition_comparison.md`:

```markdown
# Three-Condition Comparative Evaluation: `google__gson-2158`

**Verified Target Commit:** `796193d0326a2f44bc314bf24262732ea3e64014` (Improve versioning support documentation and validate version)

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 50% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ❌ No |
| **Method Hit** | ❌ No | ❌ No | ❌ No |
| **Fault Window Localized (≤25 lines)** | ❌ No | ✅ Yes | ❌ No |
| **Tool Calls Breakdown** | 14 (14 Source, 0 SootUp MCP) | 20 (20 Source, 0 SootUp MCP) | 19 (18 Source, 1 SootUp MCP) |
| **Total Tokens** | 71,381 | 158,515 | 192,761 |
| **Latency** | 34.2s | 39.5s | 57.0s |
```

---

## 6. Batch Benchmark Execution (Zero Human Intervention)

Batch execution evaluates entire task suites without manual intervention.

### Running a Complete Dataset
```bash
python3 -m llm_augmentation.cli benchmark \
  -d datasets/gson_tasks.json \
  -c C \
  -o results/gson_eval_c/ \
  --timeout-per-task 300
```

### Execution Lifecycle per Task:
1. **Compilation Check:** [`RepoManager`](../llm_augmentation/benchmark/repo_manager.py) verifies target bytecode exists or builds it (`mvn compile`).
2. **Condition Agent Run:** Dispatches task to selected agent with timeout guarding.
3. **Automated Evaluation:** [`Evaluator`](../llm_augmentation/evaluation/evaluator.py) compares output to developer Gold Patch.
4. **Summary Aggregation:** Generates cumulative statistics (Mean Recall, Precision, Exact Match Rate, Method Hit Rate).

---

## 7. Best Practices for Reproducible Evaluation

1. **Fixed Model Parameters:** Keep `temperature = 0.0` in `LLMGateway` to ensure deterministic reasoning traces.
2. **Model Consistency:** Use the same underlying model (e.g. `gpt-oss-120b` or Claude 3.5 Sonnet) across all three conditions to ensure fair comparison.
3. **Bytecode Verification:** Ensure target repositories are compiled prior to running large batches to prevent compilation timeouts.

---

## Related Documents
- [Architecture & Execution Flow](01_architecture_and_flow.md)
- [CLI Reference Manual](03_cli_reference.md)
- [Evaluation & Metrics Specification](06_evaluation_and_metrics.md)
- [Output Reports & Interpretation](08_output_reports_and_interpretation.md)
