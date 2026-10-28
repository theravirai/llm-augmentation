# Evaluation Metrics: Mathematical Specification & Implementation

This document defines the quantitative metrics used to evaluate LLM fault localization against ground-truth developer Gold Patches, answering **RQ1 (Effectiveness)** and **RQ2 (Cost-Benefit & Feasibility)**.

---

## 1. Ground Truth Extraction (`PatchParser`)

Ground-truth fault targets are extracted directly from the developer's Gold Patch (`.patch` unified diff) by [`PatchParser`](../llm_augmentation/evaluation/patch_parser.py):

1. **Gold Files ($F_{\text{gold}}$):** The set of Java files modified in the diff (normalized by basename and relative path).
2. **Gold Methods ($M_{\text{gold}}$):** Method signatures and function names extracted from diff hunk headers (`@@ -old,len +new,len @@ method_signature(...)`).
3. **Gold Lines ($L_{\text{gold}}$):** Exact line numbers modified or deleted in the original unpatched file:
   $$L_{\text{gold}} = \bigcup_{h \in \text{hunks}} \{\text{old\_start}_h, \dots, \text{old\_start}_h + \text{old\_length}_h - 1\}$$

---

## 2. Model Diagnostic Extraction

From the model's raw completion, [`BaseAgent.extract_json_diagnosis`](../llm_augmentation/agents/base_agent.py) extracts:
* **Predicted Files ($F_{\text{pred}}$):** Array of file paths (e.g. `["com/google/gson/Gson.java"]`).
* **Predicted Classes ($C_{\text{pred}}$):** Array of class names (e.g. `["com.google.gson.Gson"]`).
* **Predicted Methods ($M_{\text{pred}}$):** Array of method identifiers (e.g. `["Gson.doubleAdapter"]`).
* **Predicted Lines ($L_{\text{pred}}$):** Dictionary mapping file names to line numbers (e.g. `{"Gson.java": [398]}`).

---

## 3. RQ1: Fault Localization Accuracy Metrics

Implemented in [`MetricsCalculator.compute`](../llm_augmentation/evaluation/metrics.py):

### 3.1 File Recall ($\text{Recall}_{\text{file}}$)
Measures the proportion of gold patch files correctly identified by the model:
$$\text{Recall}_{\text{file}} = \frac{|F_{\text{pred}} \cap F_{\text{gold}}|}{|F_{\text{gold}}|}$$

### 3.2 File Precision ($\text{Precision}_{\text{file}}$)
Measures the proportion of predicted files that were actually modified in the gold patch:
$$\text{Precision}_{\text{file}} = \begin{cases} \frac{|F_{\text{pred}} \cap F_{\text{gold}}|}{|F_{\text{pred}}|}, & \text{if } |F_{\text{pred}}| > 0 \\ 0.0, & \text{otherwise} \end{cases}$$

### 3.3 File F1-Score ($\text{F1}_{\text{file}}$)
Harmonic mean of File Precision and File Recall:
$$\text{F1}_{\text{file}} = \begin{cases} \frac{2 \times \text{Precision}_{\text{file}} \times \text{Recall}_{\text{file}}}{\text{Precision}_{\text{file}} + \text{Recall}_{\text{file}}}, & \text{if } (\text{Precision} + \text{Recall}) > 0 \\ 0.0, & \text{otherwise} \end{cases}$$

### 3.4 Exact File Match
Binary indicator of complete file-level parity without missing any modified file:
$$\text{Exact File Match} = (|F_{\text{gold}} \setminus F_{\text{pred}}| = 0) \land (|F_{\text{pred}} \cap F_{\text{gold}}| = |F_{\text{gold}}|)$$

### 3.5 Method Hit Rate
Binary indicator of whether at least one predicted method matches a method altered in the developer fix:
$$\text{Method Hit} = \begin{cases} \text{True}, & \text{if } \exists m \in M_{\text{pred}} \text{ s.t. } \text{simple\_name}(m) \in M_{\text{gold}} \\ \text{False}, & \text{otherwise} \end{cases}$$

### 3.6 Line-Level Proximity Score
Calculates the minimum absolute distance (in lines) between predicted fault lines and actual modified hunks:
$$D_{\text{min}} = \min_{p \in L_{\text{pred}}, g \in L_{\text{gold}}} |p - g|$$
* **`exact_line_hit`:** $\text{True}$ if $D_{\text{min}} = 0$.

### 3.7 Downstream Patch Resolution Metric
Patch resolution is evaluated as a downstream measure of localization quality:
$$\text{Patch Resolved} = \text{Exact File Match} \land (\text{Method Hit} \lor \text{Exact Line Hit} \lor D_{\text{min}} \le 25)$$

---

## 4. RQ2: Efficiency & Cost-Benefit Metrics

Implemented in [`EvaluationReport`](../llm_augmentation/evaluation/metrics.py) to assess whether performance gains justify the cost of maintaining LLM agents and running a dedicated SootUp server:

1. **Total Token Overhead ($T_{\text{total}}$):**
   $$T_{\text{total}} = T_{\text{prompt}} + T_{\text{completion}}$$
2. **Tool Call Volume ($K_{\text{tools}}$):** Total number of SootUp MCP queries executed during the ReAct loop.
3. **Execution Latency ($S_{\text{latency}}$):** Total wall-clock time (seconds) to complete localization and evaluation.
4. **Compilation Feasibility:** Records whether target bytecode could be compiled (`OK`, `SKIPPED`, or `FAILED`).

---

## 5. Batch Aggregation Formulas

Calculated in [`Evaluator.aggregate_reports`](../llm_augmentation/evaluation/evaluator.py) across $N$ tasks:

| Aggregated Metric | Formula |
| :--- | :--- |
| **Mean File Recall** | $\frac{1}{N} \sum_{i=1}^N \text{Recall}_i \times 100\%$ |
| **Mean File Precision** | $\frac{1}{N} \sum_{i=1}^N \text{Precision}_i \times 100\%$ |
| **Mean File F1** | $\frac{1}{N} \sum_{i=1}^N \text{F1}_i \times 100\%$ |
| **Exact Match Rate** | $\frac{1}{N} \sum_{i=1}^N \mathbf{1}_{[\text{ExactMatch}_i]} \times 100\%$ |
| **Method Hit Rate** | $\frac{1}{N} \sum_{i=1}^N \mathbf{1}_{[\text{MethodHit}_i]} \times 100\%$ |
| **Patch Resolution Rate**| $\frac{1}{N} \sum_{i=1}^N \mathbf{1}_{[\text{PatchResolved}_i]} \times 100\%$ |
| **Avg Tokens per Task** | $\frac{1}{N} \sum_{i=1}^N T_{\text{total}, i}$ |
| **Avg Latency per Task** | $\frac{1}{N} \sum_{i=1}^N S_{\text{latency}, i}$ |

---

## 6. Known Limitations & Technical Boundaries

1. **Diff Header Method Extraction:** Git diff headers (`@@ ... @@`) rely on regex heuristics to extract the enclosing method signature. For complex inner lambdas, method names may default to the enclosing class or method.
2. **Line Number Drifts:** Line proximity measures distances in the unpatched file. Significant comment modifications or multi-statement formatting can create small line offsets.
3. **Bytecode Compilation Requirement:** Static analysis requires compiled `.class` files. Tasks with broken build files or unsupported JDK bytecode versions cannot be evaluated with SootUp and are logged as `compilation_status: FAILED` per thesis guidelines.

---

## Related Documents
- [Architecture & Execution Flow](01_architecture_and_flow.md)
- [Running Experiments Manual](05_running_experiments.md)
- [Output Reports & Interpretation](08_output_reports_and_interpretation.md)
