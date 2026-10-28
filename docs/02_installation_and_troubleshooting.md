# Installation, Setup, Configuration & Troubleshooting

This guide provides instructions for setting up the environment, compiling the SootUp backend, configuring LLM gateways, and resolving common runtime issues.

---

## 1. System Requirements

Ensure the following runtimes and tools are installed:

| Requirement | Minimum Version | Tested Version | Verification Command |
| :--- | :--- | :--- | :--- |
| **Java Development Kit (JDK)** | OpenJDK 17+ | OpenJDK 26.0.1 (Homebrew) | `java -version` |
| **Apache Maven** | 3.9.0+ | Maven 3.9.16 | `mvn -version` |
| **Python** | 3.10+ | Python 3.14.6 | `python3 --version` |
| **Git** | 2.30+ | Git 2.39+ | `git --version` |

---

## 2. Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/theravirai/llm-augmentation.git
cd llm-augmentation
```

### Step 2: Set Up Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
```

*Note: For development and testing tools (`pytest`), install optional dependencies:*
```bash
pip install -e ".[dev]"
```

### Step 3: Build the SootUp Java Engine
The static analysis engine must be compiled with Maven:
```bash
cd sootup_engine
mvn clean compile
```

To enable sub-second JVM launch times, generate the cached dependency classpath:
```bash
mvn dependency:build-classpath -Dmdep.outputFile=classpath.txt -q
cd ..
```

> [!NOTE]
> The Python [`McpClient`](../llm_augmentation/mcp/client.py) automatically checks for `sootup_engine/target/classes` and `sootup_engine/classpath.txt`. If they are missing, it attempts to generate them on first run. Pre-building them as shown above ensures immediate responsiveness.

---

## 3. Configuration & Environment Variables

### 3.1 API Gateway Setup (`.env`)
The framework supports OpenAI-compatible API gateways, including the **University of Paderborn AI Gateway**, OpenAI, and local endpoints (vLLM / Ollama).

Create a `.env` file in the project root:
```bash
# University of Paderborn AI Gateway
OPENAI_API_BASE=https://ai-gateway.uni-paderborn.de
OPENAI_API_KEY=your_university_api_key_here

# Optional: Default open-weights model identifier
OPENAI_MODEL=gpt-oss-120b
```

Alternatively, to use OpenAI directly:
```bash
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=sk-proj-yourOpenAIKeyHere
```

> [!TIP]
> The [`LLMGateway`](../llm_augmentation/agents/llm_gateway.py) searches for credentials in the following priority order:
> 1. Active environment variables (`OPENAI_API_BASE`, `OPENAI_API_KEY`, `ANTHROPIC_AUTH_TOKEN`).
> 2. Local `./.env` file.
> 3. Parent directory `../.env`.
> 4. Existing thesis workspace: `/Volumes/BrainStorm/Github/SootUp-Store/swebench-thesis/.env`.

### 3.2 Global Framework Configuration (`config.yaml`)
Global execution parameters are managed in [`config.yaml`](../config.yaml):

```yaml
defaults:
  model: "gpt-oss-120b"       # Model identifier passed to LLMGateway
  timeout_per_task: 300       # Per-task execution budget in seconds
  max_tool_iterations: 10     # Max multi-turn ReAct loops in Condition C
  token_budget: 16000         # Token limit allocated per task

paths:
  sootup_engine_dir: "sootup_engine"  # Relative path to Maven module
  datasets_dir: "datasets"            # Directory with SWE-Bench JSONs
  results_dir: "results"              # Output directory for evaluations

conditions:
  A:
    name: "Condition A (Source Only Baseline)"
    description: "LLM evaluates bug report with source code context only, without static facts."
  B:
    name: "Condition B (Precomputed Static Injection)"
    description: "LLM receives ahead-of-time precomputed SootUp static analysis summaries in prompt."
  C:
    name: "Condition C (On-Demand MCP Tools)"
    description: "LLM agent dynamically invokes SootUp static analysis tools via MCP."

sootup:
  java_home: null                     # Auto-detected if null
  jvm_memory: "-Xmx4g"                # Maximum JVM memory allocation
  default_callgraph_algorithm: "cha"  # cha, rta, or spark
```

---

## 4. Verification & Self-Test

Run the complete test suite to verify that the environment, SootUp engine, MCP JSON-RPC bridge, and evaluators are operational:

```bash
# 1. Test MCP JSON-RPC Server & Primitives
python3 tests/test_mcp.py

# 2. Test Benchmark Task Ingestion & Unified Diff Patch Parser
python3 tests/test_benchmark_and_patch.py

# 3. Test Agent Conditions (A, B, C with live MCP loop)
python3 tests/test_agents.py

# 4. Test Automated Evaluation Metrics & Comparison Tables
python3 tests/test_evaluation_engine.py
```

All 4 test suites should report:
```text
All MCP unit tests passed successfully!
All Benchmark & Patch Parser tests passed successfully!
All Agent tests passed successfully!
All Evaluation Engine tests passed successfully!
```

---

## 5. Troubleshooting & Common Issues

### Issue 1: SootUp SNAPSHOT Dependency Resolution Fails
- **Symptom:** Maven build fails with `Could not find artifact org.soot-oss:sootup.core:jar:3.0.2-SNAPSHOT`.
- **Cause:** `3.0.2-SNAPSHOT` is a local development snapshot built from the SootUp repository.
- **Resolution:** Verify your local Maven repository contains SootUp:
  ```bash
  ls ~/.m2/repository/org/soot-oss/sootup.core/3.0.2-SNAPSHOT/
  ```
  If missing, build SootUp locally from source (`git clone https://github.com/soot-oss/SootUp.git && mvn install -DskipTests`) or use existing local cache from `/Volumes/BrainStorm/Github/SootUp-Store/SootUp`.

### Issue 2: MCP Subprocess Hangs or Fails to Respond
- **Symptom:** Python raises `RuntimeError: SootUp MCP Server closed stream unexpectedly`.
- **Causes & Fixes:**
  1. **Classpath out of date:** If dependencies changed, regenerate `classpath.txt`:
     ```bash
     cd sootup_engine && mvn dependency:build-classpath -Dmdep.outputFile=classpath.txt -q
     ```
  2. **Invalid Target Classes Path:** The bytecode directory passed does not exist. Ensure the target project has been compiled (`mvn compile`) so that `target/classes` exists.
  3. **Check Stderr Output:** The `McpClient` captures JVM crash output and reports it directly in the exception message.

### Issue 3: Java Target Project Fails Compilation
- **Symptom:** `compilation_status: FAILED` in task report.
- **Academic Specification:** Per thesis proposal defense methodology (Slide 31), if a benchmark project or commit cannot compile with `mvn compile`, the framework leaves it out, logs `is_compilable = False`, and reports it without interrupting batch execution.
- **Resolution:** If manual compilation is needed:
  ```bash
  cd <repo_path>
  git checkout -f <base_commit>
  mvn compile -DskipTests
  ```

### Issue 4: AI Gateway SSL / Authentication Errors
- **Symptom:** HTTP 401 Unauthorized or HTTP 403 Forbidden when calling LLMs.
- **Resolution:**
  1. Check token validity:
     ```bash
     curl -i -H "Authorization: Bearer $OPENAI_API_KEY" "$OPENAI_API_BASE/models"
     ```
  2. If using the University of Paderborn AI Gateway, verify `OPENAI_API_BASE=https://ai-gateway.uni-paderborn.de` and confirm your token has active compute quota.

---

## Related Documents
- [Architecture & Execution Flow](01_architecture_and_flow.md)
- [CLI Reference Guide](03_cli_reference.md)
- [SootUp Engine & MCP Bridge Guide](07_sootup_and_mcp_bridge.md)
