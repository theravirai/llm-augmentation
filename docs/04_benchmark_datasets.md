# Benchmark Datasets: Schema, Ingestion & Extension Guide

This guide details the benchmark dataset architecture, the SWE-Bench Multilingual (Java) dataset schema, directory structures, and step-by-step instructions for adding tasks from new Java codebases.

---

## 1. Curated Benchmark Corpus

The framework includes **43 enterprise-grade defect tasks** from the **SWE-Bench Multilingual (Java)** dataset, selected because they require multi-file, non-local semantic reasoning:

| Repository | Tasks | Primary Architectural Patterns | Dataset File |
| :--- | :---: | :--- | :--- |
| **`google/gson`** | 9 | Reflection, custom type adapters, factory registration, anonymous subclasses (`Gson$1`). | [`datasets/gson_tasks.json`](../datasets/gson_tasks.json) |
| **`apache/druid`** | 5 | Distributed time-series engine, multi-file query normalization, iterator decoupling (`JodaUtils`). | [`datasets/druid_tasks.json`](../datasets/druid_tasks.json) |
| **`apache/lucene`** | 9 | High-concurrency inverted index, multi-segment boundary conditions, decoupled codecs. | [`datasets/lucene_tasks.json`](../datasets/lucene_tasks.json) |
| **`projectlombok/lombok`** | 17 | AST mutations, annotation processors, compiler-time synthetic bytecode generation. | [`datasets/lombok_tasks.json`](../datasets/lombok_tasks.json) |
| **`javaparser/javaparser`** | 2 | Java grammar parser, symbol solver, AST attribution and type resolution. | [`datasets/javaparser_tasks.json`](../datasets/javaparser_tasks.json) |
| **`reactivex/rxjava`** | 1 | Reactive streams, concurrent scheduling, backpressure operators. | [`datasets/rxjava_tasks.json`](../datasets/rxjava_tasks.json) |
| **Total** | **43** | | |

---

## 2. Directory Structure & Layout

```text
llm-augmentation/
├── datasets/                            # Ingested dataset task definitions
│   ├── gson_tasks.json
│   ├── druid_tasks.json
│   ├── lucene_tasks.json
│   ├── lombok_tasks.json
│   ├── javaparser_tasks.json
│   └── rxjava_tasks.json
│
└── workspace/ (or external workspace)   # Local clones of target Java repositories
    ├── gson/
    │   ├── .git/
    │   ├── pom.xml
    │   └── gson/target/classes/         # Compiled bytecode (.class files)
    └── druid/
        ├── .git/
        └── processing/target/classes/
```

> [!NOTE]
> The [`RepoManager`](../llm_augmentation/benchmark/repo_manager.py) searches for cloned target repositories in:
> 1. `./workspace/`
> 2. `/Volumes/BrainStorm/Github/SootUp-Store/thesis-experiments/`
> 3. `/Volumes/BrainStorm/Github/SootUp-Store/swebench-java-evaluation/workspace/`

---

## 3. Dataset JSON Schema

Each dataset file is a JSON array of task objects matching the SWE-bench format:

```json
[
  {
    "instance_id": "google__gson-2158",
    "repo": "google/gson",
    "base_commit": "666e5f8bd36d93b1aa0a581e66c6b453a2916b9b",
    "problem_statement": "Numeric types are not properly converted when written...\n",
    "patch": "diff --git a/gson/src/main/java/com/google/gson/Gson.java b/gson/src/main/java/com/google/gson/Gson.java\n...",
    "test_patch": "diff --git a/gson/src/test/java/com/google/gson/functional/DefaultTypeAdaptersTest.java ...",
    "hints_text": "Optional hints or discussion from the issue thread",
    "created_at": "2022-04-10T12:00:00Z",
    "version": "2.9.0",
    "FAIL_TO_PASS": [
      "com.google.gson.functional.DefaultTypeAdaptersTest#testNumberConversions"
    ],
    "PASS_TO_PASS": []
  }
]
```

### Field Definitions

| Field Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| **`instance_id`** | `string` | **Yes** | Unique task identifier formatted as `<owner>__<repo>-<issue_number>`. |
| **`repo`** | `string` | **Yes** | GitHub repository slug (e.g. `google/gson`, `apache/druid`). |
| **`base_commit`** | `string` | **Yes** | Git commit SHA representing the unpatched, buggy state of the repository. |
| **`problem_statement`** | `string` | **Yes** | The raw natural-language issue title, description, and reproduction code. |
| **`patch`** | `string` | **Yes** | Unified diff (`.patch`) of the developer's Gold Fix. Ground truth for evaluation. |
| **`test_patch`** | `string` | No | Unified diff adding or updating reproduction unit tests. |
| **`hints_text`** | `string` | No | Additional comments from the issue tracker. |
| **`FAIL_TO_PASS`** | `array[string]`| No | Test cases that fail on `base_commit` and pass after applying `patch`. |
| **`PASS_TO_PASS`** | `array[string]`| No | Regression test cases that must pass on both states. |

---

## 4. How the Patch Parser Extracts Ground Truth

The [`PatchParser`](../llm_augmentation/evaluation/patch_parser.py) reads the `patch` field:
1. **Target Files:** Extracted from `diff --git a/<old_path> b/<new_path>`.
2. **Target Classes:** Inferred from package paths (e.g. `gson/src/main/java/com/google/gson/Gson.java` $\rightarrow$ `com.google.gson.Gson`).
3. **Method Hints:** Parsed from the hunk header trailing signature (e.g. `@@ -398,7 +398,7 @@ private TypeAdapter<Number> doubleAdapter(...)` $\rightarrow$ `doubleAdapter`).
4. **Modified Lines:** Recorded as the exact line numbers touched in the unpatched file:
   $$\text{Lines} = [\text{old\_start}, \dots, \text{old\_start} + \text{old\_length} - 1]$$

---

## 5. Adding New Tasks from Other Java Projects

Follow these steps to add new tasks from any open-source or enterprise Java project (e.g., Apache Commons, Spring Framework, Jackson):

### Step 1: Ensure Target Codebase Compiles
Clone the repository into `workspace/<repo_name>` and verify that Maven can compile it to bytecode:
```bash
mkdir -p workspace/my-java-app
cd workspace/my-java-app
git checkout <buggy_commit>
mvn clean compile -DskipTests
```
Verify that `.class` files exist:
```bash
ls target/classes/
```

### Step 2: Extract Developer Gold Patch
Extract the exact commit that fixed the bug:
```bash
git diff <buggy_commit> <fixed_commit> > /tmp/gold_fix.patch
```

### Step 3: Create Task JSON Entry
Create `datasets/my_app_tasks.json` with the new task definition:

```json
[
  {
    "instance_id": "myorg__myapp-101",
    "repo": "myorg/myapp",
    "base_commit": "a1b2c3d4e5f678901234567890abcdef12345678",
    "problem_statement": "NullPointerException when deserializing nested polymorphic records.\n\nReproduction snippet:\nMyParser parser = new MyParser();\nparser.parse(\"{...}\");",
    "patch": "diff --git a/src/main/java/org/myorg/myapp/Parser.java b/src/main/java/org/myorg/myapp/Parser.java\nindex 1111111..2222222 100644\n--- a/src/main/java/org/myorg/myapp/Parser.java\n+++ b/src/main/java/org/myorg/myapp/Parser.java\n@@ -45,6 +45,9 @@ public Object parse(String input) {\n+        if (input == null) {\n+            return null;\n+        }\n         return parseInternal(input);\n     }\n",
    "FAIL_TO_PASS": ["org.myorg.myapp.ParserTest#testNullInput"]
  }
]
```

### Step 4: Verify with CLI
Run localization on your new task under Condition A, B, or C:
```bash
python3 -m llm_augmentation.cli run \
  -d datasets/my_app_tasks.json \
  -c C \
  -t myorg__myapp-101 \
  --output-dir results/my_app_test/
```

---

## Related Documents
- [Architecture & Execution Flow](01_architecture_and_flow.md)
- [CLI Reference Manual](03_cli_reference.md)
- [Evaluation & Metrics Specification](06_evaluation_and_metrics.md)
