# Project Architecture & End-to-End Execution Flow

This document details the system architecture and runtime execution lifecycle of the **LLM-Augmented Java Program Analysis** framework.

---

## 1. Architectural Overview

The framework decouples cognitive reasoning from formal program analysis:
- **LLM Agent Subsystem (Python):** Handles natural-language comprehension of bug reports, hypothesis generation, multi-turn tool interaction, and diagnostic synthesis.
- **SootUp Static Analysis Subsystem (Java 17+):** Reads compiled bytecode (`.class` files), lifts bytecode into Jimple 3-address Intermediate Representation (IR), and executes deterministic structural queries.
- **Model Context Protocol (MCP) Bridge:** Standardized JSON-RPC 2.0 communication over standard I/O (`stdio`), enabling the Python agent to invoke Java SootUp tools on-demand with minimal overhead.

```mermaid
graph TB
    subgraph Benchmark_Harness["1. Benchmark Harness & Evaluator"]
        CLI["CLI Entrypoint<br/>(python -m llm_augmentation.cli)"]
        DatasetLoader["TaskLoader<br/>(Ingests datasets/*.json)"]
        RepoManager["RepoManager<br/>(Checkouts & Classpath Discovery)"]
        Evaluator["Evaluator & MetricsCalculator<br/>(Gold Patch Ground Truth Comparison)"]
        Reporter["MarkdownReporter & JsonLogger<br/>(RQ1 & RQ2 Academic Tables)"]
    end

    subgraph Condition_Router["2. Three Experimental Conditions Router"]
        CondA["Condition A (Source Only Baseline)<br/>Issue + Multi-Turn Source Navigation Tools"]
        CondB["Condition B (Precomputed Static Facts)<br/>Issue + AOT Static Bytecode Facts + Source Tools"]
        CondC["Condition C (On-Demand MCP Tools)<br/>Multi-Turn ReAct Loop (Source Tools + Live SootUp MCP)"]
    end

    subgraph LLM_Agent_Subsystem["3. LLM Agent & Reasoning Subsystem"]
        Gateway["LLMGateway<br/>(Uni Paderborn Gateway / OpenAI / Local OSS)"]
        DiagnosisParser["Structured JSON Diagnostic Parser<br/>(BaseAgent.extract_json_diagnosis)"]
        SourceTools["SourceToolsExecutor<br/>(find_files, list_directory, search_source_code, read_source_file)"]
    end

    subgraph MCP_Bridge["4. Model Context Protocol (MCP) Bridge (Condition C)"]
        McpClient["Python McpClient<br/>(Subprocess JSON-RPC 2.0 Client)"]
        McpServer["Java SootUpMcpServer<br/>(STDIN/STDOUT JSON-RPC 2.0 Server)"]
    end

    subgraph Static_Fact_Extraction["5. SootUp Static Analysis & Facts (Condition B & C)"]
        AOT_Cache["Offline Facts Cache<br/>(datasets/precomputed_facts/*.txt)"]
        StandaloneCLI["Standalone SootUpAnalyzer CLI<br/>(Zero MCP / Pure Bytecode Extraction)"]
        JavaView["JavaView & TypeHierarchy<br/>(Reads target/classes bytecode)"]
        JimpleIR["Jimple 3-Address IR Transformer"]
        
        subgraph Primitives["The 5 Deterministic Bytecode Primitives"]
            P1["sootup_hierarchy"]
            P2["sootup_inspect_method"]
            P3["sootup_find_allocations"]
            P4["sootup_find_invocations"]
            P5["sootup_callgraph"]
        end
    end

    %% Execution Connections
    CLI --> DatasetLoader
    DatasetLoader --> RepoManager
    RepoManager --> Condition_Router

    Condition_Router --> CondA
    Condition_Router --> CondB
    Condition_Router --> CondC

    CondA <-->|Multi-turn source exploration| SourceTools
    CondA --> Gateway

    CondB --> AOT_Cache
    AOT_Cache -.->|Fallback extract| StandaloneCLI
    StandaloneCLI --> Primitives
    CondB -->|AOT facts in prompt| Gateway
    CondB <-->|Multi-turn source verification| SourceTools

    CondC <-->|Source navigation tools| SourceTools
    CondC <-->|ReAct MCP Tool Calls| McpClient
    McpClient <-->|stdio JSON-RPC| McpServer
    McpServer --> Primitives
    Primitives --> JimpleIR
    JimpleIR --> JavaView

    Gateway --> DiagnosisParser
    DiagnosisParser --> Evaluator
    DatasetLoader -.->|Developer Gold Patch| Evaluator
    Evaluator --> Reporter
```

---

## 2. Core Subsystems & Responsibilities

### 2.1 Benchmark Harness & Dataset Manager
- **[`TaskLoader`](../llm_augmentation/benchmark/task_loader.py):** Loads and indexes the 43 SWE-Bench Multilingual (Java) defect tasks stored in `datasets/`.
- **[`RepoManager`](../llm_augmentation/benchmark/repo_manager.py):** Manages local repository copies in `workspace/` (with automatic GitHub fallback cloning), automatically checks out the exact `base_commit`, records full 40-character commit hashes, discovers multi-module `target/classes` bytecode directories, and validates whether the target codebase compiles.
- **[`PatchParser`](../llm_augmentation/evaluation/patch_parser.py):** Analyzes the developer's Gold Patch (`.patch` unified diff) to establish ground-truth modified files, classes, methods, hunks, and exact lines touched.

### 2.2 Experimental Condition Router
The CLI routes execution to one of three experimental conditions defined by the thesis research design:
1. **Condition A (`ConditionAAgent`):** Baseline source-only evaluation equipped with repository inspection tools (`find_files`, `list_directory`, `search_source_code`, `read_source_file`). Evaluates the model's exploratory reasoning when limited strictly to textual source representations without static analysis assistance.
2. **Condition B (`ConditionBAgent`):** Passive static injection. Injects deterministic Ahead-of-Time (AOT) static analysis facts directly into the initial prompt context from `datasets/precomputed_facts/` (with standalone Java CLI fallback; completely decoupled from MCP). The model uses source navigation tools to verify exact line ranges, testing whether passive static injection suffers from **Confirmation Bias**.
3. **Condition C (`ConditionCAgent`):** Active on-demand tool calling. Equips the autonomous LLM agent with both source navigation tools and live SootUp static analysis tools via the Model Context Protocol (MCP) in a dynamic ReAct loop.

### 2.3 LLM Gateway & Provider Layer
- **[`LLMGateway`](../llm_augmentation/agents/llm_gateway.py):** Connects to OpenAI-compatible endpoints, auto-detecting environment credentials for the **University of Paderborn AI Gateway** (`https://ai-gateway.uni-paderborn.de`), OpenAI, Anthropic, or local inference engines (vLLM / Ollama).
- Formats tool schemas using the standard OpenAI function calling format.

### 2.4 Repository Source Navigation Tools
- **[`SourceToolsExecutor`](../llm_augmentation/tools/source_tools.py):** Provides sandboxed, non-destructive read operations against the target repository:
  - `find_files`: Locates files matching glob patterns (e.g. `*TypeAdapter*.java`).
  - `list_directory`: Recursively traverses package hierarchies and directory structures.
  - `search_source_code`: Executes fast regex/keyword grep across repository sources.
  - `read_source_file`: Reads specified line ranges with line numbering.

### 2.5 Model Context Protocol (MCP) Bridge (Condition C)
- **[`McpClient`](../llm_augmentation/mcp/client.py):** Spawns the Java MCP server as a subprocess using cached dependency classpaths (`classpath.txt`), executing the `initialize` handshake and relaying tool calls.
- **[`SootUpMcpServer`](../sootup_engine/src/main/java/org/sootup/analyzer/SootUpMcpServer.java):** Listens on standard input for JSON-RPC 2.0 messages, routes requests to `SootUpAnalyzer`, caches `JavaView` instances by target directory, and formats responses back to standard output.

### 2.5 SootUp 3.x Static Analysis Engine
- **[`SootUpAnalyzer`](../sootup_engine/src/main/java/org/sootup/analyzer/SootUpAnalyzer.java):** Interacts directly with `sootup.core`, `sootup.java.bytecode`, and `sootup.callgraph`.
- Translates `.class` files into Jimple 3-address statements with source line mapping.
- Prunes bytecode searches to application classes (`isApplicationClass()`), avoiding whole-JDK traversal and achieving sub-second query latency.

---

## 3. End-to-End Execution Sequence

The following sequence diagram illustrates an unattended benchmark run under **Condition C** (Active MCP Tool Calling):

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher / CLI
    participant CLI as llm_augmentation.cli
    participant Loader as TaskLoader
    participant Repo as RepoManager
    participant Agent as ConditionCAgent
    participant Gateway as LLMGateway
    participant MCP as McpClient (Python)
    participant Server as SootUpMcpServer (Java)
    participant Analyzer as SootUpAnalyzer
    participant Eval as Evaluator & PatchParser
    participant Rep as MarkdownReporter & JsonLogger

    User->>CLI: python -m llm_augmentation.cli run -c C -t google__gson-2158
    CLI->>Loader: get_task("google__gson-2158")
    Loader-->>CLI: Task object (problem_statement, patch, base_commit)
    CLI->>Repo: prepare_repo_for_task(task, checkout=True)
    Repo-->>CLI: RepoContext (target_commit="666e5f8b...", target_classes_dirs, is_compilable)

    CLI->>Agent: run(task, repo_context)
    Agent->>MCP: start_server(target_classes)
    MCP->>Server: spawn java org.sootup.analyzer.SootUpMcpServer
    MCP->>Server: {"method": "initialize", "params": {...}}
    Server-->>MCP: {"result": {"capabilities": {"tools": {}}}}

    Note over Agent,Gateway: Turn 1: Initial Investigation (Source Tools + MCP)
    Agent->>Gateway: chat_completion(messages=[ProblemStatement], tools=[SOURCE_TOOLS, SOOTUP_TOOLS])
    Gateway-->>Agent: tool_calls=[sootup_hierarchy(target_class="com.google.gson.TypeAdapter")]

    Note over Agent,Server: Live Bytecode Query Loop
    Agent->>MCP: call_tool("sootup_hierarchy", {"target_class": "..."})
    MCP->>Server: {"method": "tools/call", "params": {"name": "sootup_hierarchy", ...}}
    Server->>Analyzer: getHierarchy("com.google.gson.TypeAdapter")
    Analyzer-->>Server: Subclasses: Gson$1, Gson$2, TypeAdapters$*
    Server-->>MCP: JSON-RPC response with text content
    MCP-->>Agent: Formatted static hierarchy facts

    Note over Agent,Gateway: Turn 2: Allocation Site Pinpointing
    Agent->>Gateway: chat_completion(messages=[ToolResult], tools=[SOURCE_TOOLS, SOOTUP_TOOLS])
    Gateway-->>Agent: tool_calls=[sootup_find_allocations(target_class="com.google.gson.Gson$1")]
    Agent->>MCP: call_tool("sootup_find_allocations", ...)
    MCP->>Server: {"method": "tools/call", ...}
    Server->>Analyzer: findAllocations("com.google.gson.Gson$1", ...)
    Analyzer-->>Server: Match: Gson.doubleAdapter() line 394
    Server-->>MCP: JSON-RPC response
    MCP-->>Agent: Allocation facts

    Note over Agent,Gateway: Turn 3: Source Verification & Diagnosis
    Agent->>Gateway: chat_completion(messages=[ToolResult], tools=[SOURCE_TOOLS, SOOTUP_TOOLS])
    Gateway-->>Agent: Final JSON Diagnosis (files, classes, methods, lines)
    Agent->>MCP: close()
    Agent-->>CLI: LocalizationResult (predictions, traces, prompt snapshots)

    Note over CLI,Rep: Ground Truth Evaluation & Reporting
    CLI->>Eval: evaluate_task(result, task, repo_context)
    Eval-->>CLI: EvaluationReport (Recall: 100%, FaultWindowLocalized: true)
    CLI->>Rep: generate_task_report(report, traces)
    Rep-->>User: Console output + saved .md report, _eval.json, and _trace.json
```

---

## 4. Cognitive Agent vs. Deterministic Static Engine

A core contribution of this thesis is clearly separating what the LLM does from what SootUp does:

| Capability | LLM Agent | SootUp Static Analysis Engine |
| :--- | :--- | :--- |
| **Input** | Bug issue descriptions, stack traces, source text, tool outputs. | Compiled Java bytecode (`.class` files in `target/classes`). |
| **Strengths** | Natural-language comprehension, intent recognition, hypothesis generation, synthesizing root causes. | Deterministic, whole-program mathematical ground truth (subclasses, call graphs, Jimple 3-address IR, allocations). |
| **Failure Modes** | Heuristic tunnel vision, syntactic confirmation bias, hallucinated paths. | Lacks context about user requirements or natural-language bug descriptions. |
| **Combined Synergies** | Guides *what* structural questions to ask based on bug symptoms. | Authoritatively provides *answers*, preventing LLM hallucination and overcoming confirmation bias. |

---

## Related Documents
- [Installation & Troubleshooting Guide](02_installation_and_troubleshooting.md)
- [CLI Reference Guide](03_cli_reference.md)
- [SootUp Engine & MCP Bridge Guide](07_sootup_and_mcp_bridge.md)
- [Evaluation & Metrics Guide](06_evaluation_and_metrics.md)
