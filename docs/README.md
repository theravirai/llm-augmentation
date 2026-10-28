# LLM-Augmented Java Program Analysis & Fault Localization Documentation

Welcome to the technical documentation for the **LLM-Augmented Java Program Analysis via SootUp Integration** research framework.

This project investigates whether augmenting Large Language Models (LLMs) with whole-program static analysis facts (extracted directly from compiled Java bytecode via **SootUp 3.x** and bridged via the **Model Context Protocol (MCP)**) overcomes non-local semantic reasoning blindspots (polymorphic dispatch, anonymous classes, factory decoupling) in multi-file Java defect localization.


---

## Documentation Index

The documentation is organized into eight specialized guides:

| Guide | Description | Key Topics |
| :--- | :--- | :--- |
| [**01. Architecture & Execution Flow**](01_architecture_and_flow.md) | High-level system design and end-to-end component interaction. | System components, sequence diagrams, cognitive agent vs. static analysis engine, Condition A/B/C routing. |
| [**02. Installation & Troubleshooting**](02_installation_and_troubleshooting.md) | Environment setup, dependencies, configuration, and recovery. | Java 17+, Maven 3.9+, Python 3.10+, Uni Paderborn AI Gateway setup, `config.yaml`, common failure modes. |
| [**03. CLI Reference**](03_cli_reference.md) | Exhaustive command-line interface manual. | Subcommands (`run`, `benchmark`, `compare`, `tools`), all flags, argument types, defaults, copyable commands. |
| [**04. Benchmark Datasets**](04_benchmark_datasets.md) | Benchmark schema, task ingestion, and extension guide. | 43 SWE-Bench Java tasks, dataset JSON schema, repository layout, step-by-step guide to add new projects. |
| [**05. Running Experiments**](05_running_experiments.md) | Operational manual for executing single tasks and batch runs. | Executing Condition A (Baseline), Condition B (Precomputed), and Condition C (On-Demand MCP), comparison matrices. |
| [**06. Evaluation & Metrics**](06_evaluation_and_metrics.md) | Mathematical formulation and ground-truth evaluation. | RQ1 accuracy (Recall, Precision, F1, Line proximity, Patch resolution), RQ2 cost metrics, diff parsing logic. |
| [**07. SootUp Engine & MCP Bridge**](07_sootup_and_mcp_bridge.md) | Bytecode analysis internals and JSON-RPC protocol. | The 5 primitives (`hierarchy`, `inspect-method`, `find-allocations`, `find-invocations`, `callgraph`), MCP stdio protocol. |
| [**08. Output Reports & Result Interpretation**](08_output_reports_and_interpretation.md) | Artifacts, schemas, and scientific evaluation reporting. | JSON trace schemas, Markdown report tables, batch aggregation, interpreting results for thesis defense. |

---

## Quick Navigation by Role

- **Getting Started as a Developer / Evaluator:**
  Start with [Installation & Setup](02_installation_and_troubleshooting.md), then run your first test task using the [CLI Reference](03_cli_reference.md).
- **Understanding the Scientific Framework:**
  Read [Architecture & Flow](01_architecture_and_flow.md), [Running Experiments](05_running_experiments.md), and [Evaluation & Metrics](06_evaluation_and_metrics.md).
- **Working with Static Analysis & MCP:**
  Refer to [SootUp Engine & MCP Bridge](07_sootup_and_mcp_bridge.md).
- **Adding New Tasks or Benchmarks:**
  Follow the instructions in [Benchmark Datasets](04_benchmark_datasets.md).

---

## Current Implementation State Summary

| Feature Area | Status | Implementation Details |
| :--- | :--- | :--- |
| **Java SootUp Engine** | ✅ Implemented | 5 primitives in `SootUpAnalyzer.java`, fast application-class scanning, Java 17+ bytecode to Jimple IR. |
| **MCP Server** | ✅ Implemented | JSON-RPC 2.0 stdio server in `SootUpMcpServer.java` with per-directory JavaView caching. |
| **MCP Client** | ✅ Implemented | Python subprocess manager in `llm_augmentation/mcp/client.py` using cached `classpath.txt`. |
| **Benchmark Loader** | ✅ Implemented | `TaskLoader` ingesting 43 SWE-Bench Java tasks across 6 repositories. |
| **Ground-Truth Diff Parser** | ✅ Implemented | `PatchParser` parsing unified diffs to extract files, classes, methods, and line ranges. |
| **Condition A Agent** | ✅ Implemented | `ConditionAAgent` for source-only baseline evaluation. |
| **Condition B Agent** | ✅ Implemented | `ConditionBAgent` with ahead-of-time (AOT) static fact injection into prompt. |
| **Condition C Agent** | ✅ Implemented | `ConditionCAgent` autonomous ReAct loop calling live SootUp tools over MCP. |
| **LLM Gateway** | ✅ Implemented | `LLMGateway` supporting Uni Paderborn AI Gateway, OpenAI, Anthropic, or local endpoints. |
| **Evaluation Suite** | ✅ Implemented | `Evaluator` and `MetricsCalculator` computing RQ1 and RQ2 metrics against developer Gold Patches. |
| **CLI** | ✅ Implemented | `run`, `benchmark`, `compare`, and `tools` commands in `llm_augmentation/cli.py`. |
| **Batch Concurrency** | ⏳ Planned | Tasks currently execute sequentially in `benchmark` command (`--limit` supported; multi-threading planned). |
