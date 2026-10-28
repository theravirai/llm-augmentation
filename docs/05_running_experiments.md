# Running Experiments: Conditions A, B, and C

This guide explains how to design, execute, and analyze fault localization experiments across the three experimental conditions investigated in the thesis.

---

## 1. Experimental Conditions Comparison

```text
+-----------------------+----------------------------------+----------------------------------------------------+
| Dimension             | Condition A: Baseline (Source)   | Condition B: Passive Static Injection             | Condition C: Active Tool Calling (MCP)             |
+-----------------------+----------------------------------+----------------------------------------------------+
| Input Context         | Bug statement + source files     | Bug statement + source files + AOT static dump    | Bug statement + source files + live SootUp tools   |
| Static Bytecode Facts | None                             | Ahead-of-Time precomputed dump                    | Dynamic / Interactive on-demand queries            |
| Interaction Mode      | Single-turn prompt completion    | Single-turn prompt completion                     | Multi-turn Agentic Loop (ReAct via MCP)            |
| Primary Failure Mode  | Token-level heuristic tunnel     | Confirmation Bias (model ignores static facts)    | Tool latency / irrelevant query paths              |
| Token Cost            | Low                              | High (verbose static dumps in prompt)             | Proportional to number of tool iterations          |
+-----------------------+----------------------------------+----------------------------------------------------+
```

---

## 2. Condition A: Source Only Baseline

### Concept & Scientific Purpose
Condition A provides the LLM with only the natural-language problem statement, repository slug, and base commit. No static analysis tools or bytecode facts are provided.
* **Goal:** Quantify the baseline failure rate caused by token-level heuristics and search-space tunnel vision when reasoning over decoupled Java architectures.

### Agent Implementation Details
Defined in [`ConditionAAgent`](../llm_augmentation/agents/condition_a_agent.py):
1. Assembles prompt using `SYSTEM_PROMPT` instructing the model to analyze Java source files.
2. Demands a strict JSON diagnosis format (`localized_files`, `localized_classes`, `localized_methods`, `localized_lines`).
3. Executes a single-turn completion with `temperature=0.0`.

### Execution Command
```bash
python3 -m llm_augmentation.cli run \
  -c A \
  -t google__gson-2158 \
  --output-dir results/condition_a_gson_2158/
```

---

## 3. Condition B: Precomputed Static Injection (AOT)

### Concept & Scientific Purpose
Condition B precomputes static analysis summaries using SootUp ahead of time (AOT) and dumps them directly into the prompt context.
* **Goal:** Test whether passive static fact injection (traditional RAG approach) suffers from **LLM Confirmation Bias** — where the model holds strong syntactic priors and actively disregards conflicting static facts.

### Agent Implementation Details
Defined in [`ConditionBAgent`](../llm_augmentation/agents/condition_b_agent.py):
1. Connects to `SootUpMcpServer` to pre-query static facts for candidate types mentioned in the task description.
2. Gathers class hierarchies (`sootup_hierarchy`) and object allocation sites (`sootup_find_allocations`).
3. Injects facts into the prompt under `### Deterministic Static Analysis Facts (SootUp Bytecode Extractor)`.
4. Executes single-turn completion.

### Execution Command
```bash
python3 -m llm_augmentation.cli run \
  -c B \
  -t google__gson-2158 \
  --output-dir results/condition_b_gson_2158/
```

---

## 4. Condition C: Active On-Demand Tool Calling (MCP)

### Concept & Scientific Purpose
Condition C equips the model with live SootUp static analysis tools exposed via the Model Context Protocol (MCP) in a multi-turn ReAct loop.
* **Goal:** Test whether selective, on-demand querying allows the agent to validate hypotheses dynamically, pivot its search space upon discovering hidden anonymous classes, and achieve gold patch parity.

### Agent Implementation Details
Defined in [`ConditionCAgent`](../llm_augmentation/agents/condition_c_agent.py):
1. Spawns `SootUpMcpServer` over `stdio`.
2. Registers [`SOOTUP_TOOLS`](../llm_augmentation/mcp/tool_schemas.py) in the OpenAI function-calling format.
3. Loops up to `max_iterations = 10`:
   - If the model returns `tool_calls`, dispatches queries to SootUp via `McpClient.call_tool()`.
   - Records tool execution latency and captures facts into `tool_calls_trace`.
   - Feeds tool output back as a role `tool` message.
   - When the model produces final text, extracts the structured JSON diagnosis.

### Execution Command
```bash
python3 -m llm_augmentation.cli run \
  -c C \
  -t google__gson-2158 \
  --output-dir results/condition_c_gson_2158/
```

---

## 5. Automated Three-Condition Comparison

To run an apples-to-apples comparison of Conditions A, B, and C on a specific defect:

```bash
python3 -m llm_augmentation.cli compare \
  -t google__gson-2158 \
  --model gpt-oss-120b \
  --output-dir results/comparison_gson_2158/
```

This generates `results/comparison_gson_2158/google__gson-2158_condition_comparison.md`:

```markdown
# Three-Condition Comparative Evaluation: `google__gson-2158`

| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |
| :--- | :--- | :--- | :--- |
| **File Recall** | 50% | 100% | 100% |
| **File Precision** | 100% | 100% | 100% |
| **Exact Match** | ❌ No | ✅ Yes | ✅ Yes |
| **Method Hit** | ❌ No | ❌ No | ✅ Yes |
| **Patch Resolved** | ❌ No | ❌ No | ✅ Yes |
| **Tool Calls** | 0 | 0 | 2 |
| **Total Tokens** | 1,520 | 4,890 | 2,840 |
| **Latency** | 2.1s | 4.8s | 5.4s |
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
