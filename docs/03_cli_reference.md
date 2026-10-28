# CLI Reference Manual

The framework provides a unified Command-Line Interface (CLI) accessible via:
```bash
python3 -m llm_augmentation.cli <subcommand> [options]
```
Or via the entrypoint script if installed with `pip install -e .`:
```bash
llm-aug <subcommand> [options]
```

---

## 1. Overview of Subcommands

| Subcommand | Purpose | Key Flags | Primary Output |
| :--- | :--- | :--- | :--- |
| **`run`** | Executes fault localization on a single benchmark task under a specific condition. | `-c [A\|B\|C]`, `-t <task_id>` | Task Markdown report (`*_report.md`) & JSON log (`*_eval.json`). |
| **`benchmark`** | Runs unattended batch evaluation across an entire dataset file. | `-d <dataset.json>`, `-c [A\|B\|C]` | Aggregated summary report (`*_summary.md`) & batch JSON (`*_summary.json`). |
| **`compare`** | Executes Conditions A, B, and C sequentially on the same task. | `-t <task_id>` | Side-by-side comparative table (`*_condition_comparison.md`). |
| **`tools`** | Directly executes SootUp static analysis primitives via MCP for debugging. | `<tool_name>`, `--target-dir <dir>` | Formatted Jimple IR / hierarchy facts printed to stdout. |

---

## 2. Subcommand: `run`

Executes fault localization on an individual task instance.

### Syntax
```bash
python3 -m llm_augmentation.cli run -c <CONDITION> -t <TASK_ID> [options]
```

### Options & Arguments
| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--condition` | `-c` | Choice (`A`, `B`, `C`) | *Required* | Experimental condition to evaluate. |
| `--task` | `-t` | String | *Required* | SWE-Bench instance ID (e.g. `google__gson-2158`). |
| `--model` | `-m` | String | `gpt-oss-120b` | LLM model identifier. |
| `--dataset` | `-d` | Path | `None` | Optional specific dataset JSON to load from. |
| `--output-dir` | `-o` | Path | `results` | Directory where evaluation logs are saved. |
| `--target-dir` | | Path | `None` | Path to compiled bytecode (`target/classes`). Overrides auto-detection. |

### Concrete Examples

#### 1. Baseline Run (Condition A - Source Only)
```bash
python3 -m llm_augmentation.cli run \
  -c A \
  -t google__gson-2158 \
  --output-dir results/gson_2158_baseline/
```

#### 2. Passive Static Injection Run (Condition B)
```bash
python3 -m llm_augmentation.cli run \
  -c B \
  -t google__gson-2158 \
  --output-dir results/gson_2158_precomputed/
```

#### 3. Active On-Demand MCP Run (Condition C)
```bash
python3 -m llm_augmentation.cli run \
  -c C \
  -t google__gson-2158 \
  --model gpt-oss-120b \
  --output-dir results/gson_2158_mcp/
```

#### 4. Explicit Bytecode Directory Override
```bash
python3 -m llm_augmentation.cli run \
  -c C \
  -t google__gson-2158 \
  --target-dir /Volumes/BrainStorm/Github/SootUp-Store/thesis-experiments/google-gson/gson/gson/target/classes \
  --output-dir results/manual_classes_run/
```

---

## 3. Subcommand: `benchmark`

Runs unattended, automated evaluation over a dataset file containing multiple task instances without human intervention.

### Syntax
```bash
python3 -m llm_augmentation.cli benchmark -d <DATASET_FILE> -c <CONDITION> [options]
```

### Options & Arguments
| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--dataset` | `-d` | Path | *Required* | Path to task dataset JSON (e.g. `datasets/gson_tasks.json`). |
| `--condition` | `-c` | Choice (`A`, `B`, `C`) | *Required* | Experimental condition to evaluate across all tasks. |
| `--model` | `-m` | String | `gpt-oss-120b` | LLM model identifier. |
| `--output-dir` | `-o` | Path | `results/benchmark` | Directory to store summary tables and task logs. |
| `--timeout-per-task` | | Integer | `300` | Per-task execution budget in seconds. |
| `--limit` | | Integer | `None` | Max number of tasks to execute (useful for dry runs). |

> [!NOTE]
> Tasks are currently executed sequentially per dataset run. Multi-threaded batch workers are planned for future distributed test harnesses.

### Concrete Examples

#### 1. Quick Verification Dry-Run (First 2 tasks)
```bash
python3 -m llm_augmentation.cli benchmark \
  -d datasets/gson_tasks.json \
  -c C \
  --limit 2 \
  -o results/quick_verification/
```

#### 2. Full Benchmark Evaluation (Gson - Condition C)
```bash
python3 -m llm_augmentation.cli benchmark \
  -d datasets/gson_tasks.json \
  -c C \
  -o results/gson_benchmark_c/ \
  --timeout-per-task 300
```

#### 3. Full Benchmark Evaluation (Druid - Condition A Baseline)
```bash
python3 -m llm_augmentation.cli benchmark \
  -d datasets/druid_tasks.json \
  -c A \
  -o results/druid_benchmark_a/
```

---

## 4. Subcommand: `compare`

Runs Conditions A, B, and C sequentially on the same task instance and produces a unified comparative Markdown table.

### Syntax
```bash
python3 -m llm_augmentation.cli compare -t <TASK_ID> [options]
```

### Options & Arguments
| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--task` | `-t` | String | *Required* | SWE-Bench instance ID to compare. |
| `--model` | `-m` | String | `gpt-oss-120b` | LLM model identifier. |
| `--output-dir` | `-o` | Path | `results/comparison` | Directory where comparison Markdown report is saved. |

### Concrete Examples

```bash
# Compare Conditions A, B, and C on Google Gson #2158
python3 -m llm_augmentation.cli compare \
  -t google__gson-2158 \
  -o results/comparison_gson_2158/

# Compare Conditions A, B, and C on Apache Druid #14136
python3 -m llm_augmentation.cli compare \
  -t apache__druid-14136 \
  -o results/comparison_druid_14136/
```

---

## 5. Subcommand: `tools`

Directly executes the 5 SootUp static analysis primitives via the MCP client from the terminal. Useful for interactive inspection, debugging, and prompt preparation.

### Syntax
```bash
python3 -m llm_augmentation.cli tools <PRIMITIVE> --target-dir <DIR> [primitive_options]
```

### Primitive 1: `hierarchy`
Retrieves superclasses, subclasses (including compiler-generated anonymous classes), and interfaces:
```bash
python3 -m llm_augmentation.cli tools hierarchy \
  --target-class com.google.gson.TypeAdapter \
  --target-dir sootup_engine/target/classes
```

### Primitive 2: `inspect-method`
Disassembles method bytecode into Jimple 3-address IR with source line numbers:
```bash
python3 -m llm_augmentation.cli tools inspect-method \
  --target-class org.sootup.analyzer.SootUpAnalyzer \
  --target-method getHierarchy \
  --target-dir sootup_engine/target/classes
```

### Primitive 3: `find-allocations`
Scans Jimple bodies for `JNewExpr` statements to find instantiation sites:
```bash
python3 -m llm_augmentation.cli tools find-allocations \
  --target-class com.google.gson.Gson\$1 \
  --scope-class com.google.gson.Gson \
  --target-dir /Volumes/BrainStorm/Github/SootUp-Store/thesis-experiments/google-gson/gson/gson/target/classes
```

### Primitive 4: `find-invocations`
Scans Jimple bodies for `InvokableStmt` to trace callers:
```bash
python3 -m llm_augmentation.cli tools find-invocations \
  --target-class org.apache.druid.java.util.common.JodaUtils \
  --target-method condenseIntervals \
  --target-dir /Volumes/BrainStorm/Github/SootUp-Store/thesis-experiments/apache/druid/processing/target/classes
```

### Primitive 5: `callgraph`
Constructs an interprocedural Call Graph using CHA, RTA, or SPARK:
```bash
python3 -m llm_augmentation.cli tools callgraph \
  --algorithm cha \
  --entry-class org.sootup.analyzer.SootUpAnalyzer \
  --entry-method getHierarchy \
  --return-type java.lang.String \
  --target-dir sootup_engine/target/classes
```

---

## Related Documents
- [Architecture & Execution Flow](01_architecture_and_flow.md)
- [Running Experiments Manual](05_running_experiments.md)
- [SootUp Engine & MCP Bridge Guide](07_sootup_and_mcp_bridge.md)
- [Output Reports & Interpretation](08_output_reports_and_interpretation.md)
