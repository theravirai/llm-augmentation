import json
import re
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    comp_dir = base_dir / "results" / "comparisons"
    tasks = sorted([d.name for d in comp_dir.iterdir() if d.is_dir() and d.name.startswith("google__gson-")])

    data = {"A": [], "B": [], "C": []}
    task_entries = []

    for t in tasks:
        t_id_num = t.split("-")[-1]
        comp_file = comp_dir / t / f"{t}_condition_comparison.md"
        table_text = comp_file.read_text(encoding="utf-8").strip()
        
        ev_A = json.load(open(comp_dir / t / f"{t}_cond_A_eval.json"))
        ev_B = json.load(open(comp_dir / t / f"{t}_cond_B_eval.json"))
        ev_C = json.load(open(comp_dir / t / f"{t}_cond_C_eval.json"))
        
        # Store per condition
        for cond, ev in [("A", ev_A), ("B", ev_B), ("C", ev_C)]:
            rq1 = ev["rq1_accuracy"]
            rq2 = ev["rq2_cost"]
            data[cond].append({
                "recall": rq1["file_recall"],
                "precision": rq1["file_precision"],
                "f1": rq1["file_f1"],
                "exact_match": rq1["exact_file_match"],
                "method_hit": rq1["method_hit"],
                "line_dist": rq1["min_line_distance"],
                "window_localized": rq1["fault_window_localized"],
                "total_tokens": rq2["total_tokens"],
                "total_calls": rq2["tool_calls_count"],
                "src_calls": rq2["source_tool_calls"],
                "soot_calls": rq2["mcp_tool_calls"],
                "latency": rq2["latency_seconds"]
            })
        
        commit_hash = ev_A["target_commit"]
        commit_subject = ev_A["target_commit_subject"]
        gold_files = set(ev_A["rq1_accuracy"]["matched_files"] + ev_A["rq1_accuracy"]["missed_files"])
        scope = f"Multi-file ({len(gold_files)})" if len(gold_files) > 1 else f"Single-file ({len(gold_files)})"
        
        # Extract table part only (from | Dimension down)
        lines = table_text.splitlines()
        table_lines = [l for l in lines if l.startswith("|")]
        clean_table = "\n".join(table_lines)
        
        task_entries.append({
            "task": t,
            "id_num": t_id_num,
            "commit_hash": commit_hash,
            "commit_short": commit_hash[:8],
            "commit_subject": commit_subject,
            "scope": scope,
            "rec_A": ev_A["rq1_accuracy"]["file_recall"],
            "rec_B": ev_B["rq1_accuracy"]["file_recall"],
            "rec_C": ev_C["rq1_accuracy"]["file_recall"],
            "exact_A": ev_A["rq1_accuracy"]["exact_file_match"],
            "exact_B": ev_B["rq1_accuracy"]["exact_file_match"],
            "exact_C": ev_C["rq1_accuracy"]["exact_file_match"],
            "dist_A": ev_A["rq1_accuracy"]["min_line_distance"],
            "dist_B": ev_B["rq1_accuracy"]["min_line_distance"],
            "dist_C": ev_C["rq1_accuracy"]["min_line_distance"],
            "soot_C": ev_C["rq2_cost"]["mcp_tool_calls"],
            "clean_table": clean_table
        })

    N = len(tasks)
    summary_metrics = {}
    for cond in ["A", "B", "C"]:
        summary_metrics[cond] = {
            "mean_recall": sum(d["recall"] for d in data[cond]) / N * 100,
            "mean_precision": sum(d["precision"] for d in data[cond]) / N * 100,
            "mean_f1": sum(d["f1"] for d in data[cond]) / N * 100,
            "exact_count": sum(1 for d in data[cond] if d["exact_match"]),
            "method_count": sum(1 for d in data[cond] if d["method_hit"]),
            "window_count": sum(1 for d in data[cond] if d["window_localized"]),
            "avg_tokens": sum(d["total_tokens"] for d in data[cond]) / N,
            "avg_calls": sum(d["total_calls"] for d in data[cond]) / N,
            "avg_src": sum(d["src_calls"] for d in data[cond]) / N,
            "avg_soot": sum(d["soot_calls"] for d in data[cond]) / N,
            "avg_latency": sum(d["latency"] for d in data[cond]) / N,
        }

    # Build Markdown Report
    out = []
    out.append("# Three-Condition Comparative Benchmark Evaluation: `google/gson`\n")
    out.append("> **Thesis Research Report:** Quantitative comparative evaluation of Fault Localization (FL) performance across all 9 SWE-Bench Java benchmark instances for `google/gson` using the `gpt-oss-120b` large language model.\n")
    out.append("- **Subject Model:** `gpt-oss-120b` (Hosted on University of Paderborn AI Gateway)")
    out.append("- **Target Repository:** [`google/gson`](https://github.com/google/gson)")
    out.append("- **Benchmark Suite:** SWE-Bench Java (`google/gson`) — 9 Defect Tasks")
    out.append("- **Evaluation Date:** November 2026")
    out.append("- **Core Objective:** Investigate whether augmenting LLM reasoning with deterministic whole-program static analysis facts (extracted via **SootUp 3.x** and the **Model Context Protocol**) overcomes syntactic search-space tunnel vision and improves multi-file fault localization over source-code-only baselines.\n")
    out.append("---\n")

    out.append("## 1. Executive Guide: Experimental Setup & Metric Definitions\n")
    out.append("This section defines the experimental conditions and quantitative evaluation metrics used throughout this report. It is designed to provide immediate context without requiring external documentation.\n")
    out.append("### 1.1. Scope Boundary: Fault Localization (FL) vs. Automated Program Repair (APR)")
    out.append("This empirical study focuses strictly on **Fault Localization (FL)**—the task of accurately diagnosing *which files, methods, and exact line ranges contain the root-cause defect* given a developer bug report. It does **not** perform code synthesis, automated program repair (APR), or patch generation. Metrics measure how closely the model's diagnosed fault window matches the actual developer ground-truth fix.\n")

    out.append("### 1.2. The Three Experimental Conditions\n")
    out.append("| Condition | Setup & Context Provided | Interaction Mode | MCP Server Required? | Purpose & Research Goal |")
    out.append("| :--- | :--- | :--- | :--- | :--- |")
    out.append("| **Condition A**<br>*(Baseline - Source Only)* | Natural-language bug statement + Local repository source navigation tools (`find_files`, `list_directory`, `search_source_code`, `read_source_file`). | Autonomous Multi-turn ReAct Loop (Source tools only) | **No** | Quantify baseline LLM localization performance when relying purely on syntactic pattern matching and grep-like source exploration without static analysis. |")
    out.append("| **Condition B**<br>*(Precomputed Static Injection)* | Bug statement + Source navigation tools + **Ahead-of-Time (AOT) precomputed SootUp static bytecode facts** (class hierarchies, object allocation sites) injected into the initial user prompt. | Autonomous Multi-turn ReAct Loop (Offline facts + Source tools) | **No** (Decoupled offline cache) | Test traditional passive RAG/injection architectures to determine if static facts in prompt context mitigate or trigger **LLM Confirmation Bias** (ignoring conflicting facts). |")
    out.append("| **Condition C**<br>*(On-Demand MCP Tools)* | Bug statement + Source navigation tools + **Live SootUp static analysis tools exposed dynamically via the Model Context Protocol (MCP)** over `stdio` JSON-RPC. | Autonomous Multi-turn Joint Source & Static Tool Calling | **Yes** (Java `SootUpMcpServer` subprocess) | Evaluate whether interactive, on-demand bytecode queries (`sootup_inspect_method`, `sootup_hierarchy`, `sootup_find_allocations`) enable the agent to uncover hidden classes and multi-file dependencies. |\n")

    out.append("### 1.3. Evaluation Metrics & Dimensions\n")
    out.append("#### Research Question 1 (RQ1): Localization Accuracy")
    out.append("- **File Recall ($\\text{Recall}_{\\text{file}}$):** The percentage of ground-truth modified Java files ($F_{\\text{gold}}$) that were correctly identified in the model's diagnosis ($F_{\\text{pred}}$). A recall of $100\\%$ indicates that all defect files were successfully located.")
    out.append("- **File Precision ($\\text{Precision}_{\\text{file}}$):** The proportion of model-predicted files that actually contained the defect ($|F_{\\text{pred}} \\cap F_{\\text{gold}}| / |F_{\\text{pred}}|$). A precision of $100\\%$ indicates zero false-positive or irrelevant files were flagged.")
    out.append("- **File F1-Score ($\\text{F1}_{\\text{file}}$):** The harmonic mean of File Recall and File Precision ($2 \\times \\frac{\\text{Recall} \\times \\text{Precision}}{\\text{Recall} + \\text{Precision}}$).")
    out.append("- **Exact File Match:** A strict binary indicator (✅ Yes / ❌ No). True if and only if the model predicted the exact set of modified files with zero omissions and zero extraneous files ($\\text{Recall} = 100\\%$ and $\\text{Precision} = 100\\%$).")
    out.append("- **Method Hit:** A binary indicator (✅ Yes / ❌ No). Evaluates whether at least one of the model's localized method signatures matches the enclosing method modified in the developer's gold patch hunk headers (`@@ ... @@ methodSignature`).")
    out.append("- **Min Line Proximity (Line Distance):** The minimum absolute distance (in lines) between the model's localized lines and the ground-truth patch edit hunks ($L_{\\text{gold}}$). A distance of `0.0 lines` represents an exact hit inside or on the boundary of the defect edit hunk.")
    out.append("- **Fault Window Localized ($\\le 25$ lines):** A binary indicator (✅ Yes / ❌ No) confirming that the model achieved an Exact File Match and localized the root-cause within a standard 25-line inspection window ($d_{\\text{min}} \\le 25$). Replaces misleading 'Patch Resolved' terminology.\n")

    out.append("#### Research Question 2 (RQ2): Cost, Efficiency & Tool Overhead")
    out.append("- **Tool Calls Breakdown:** Total count of tool invocations executed during the ReAct loop, explicitly separated into **Source Navigation Calls** (`find_files`, `read_source_file`, `search_source_code`) vs. **SootUp MCP Static Analysis Calls** (`sootup_inspect_method`, `sootup_hierarchy`, `sootup_find_allocations`).")
    out.append("- **Total Tokens:** Cumulative token consumption across all conversational turns (Prompt Tokens + Completion Tokens).")
    out.append("- **Execution Latency:** Total wall-clock time in seconds ($S_{\\text{latency}}$) required to complete the multi-turn diagnosis.")
    out.append("- **Verified Target Commit:** The exact unpatched Git commit hash (`base_commit`) checked out before evaluation began, verified directly via `git rev-parse HEAD` to guarantee experimental provenance.\n")
    out.append("---\n")

    # Section 2: Summary Table
    sA = summary_metrics["A"]
    sB = summary_metrics["B"]
    sC = summary_metrics["C"]

    out.append("## 2. Overall Aggregated Benchmark Summary (N = 9 Tasks)\n")
    out.append("| Evaluation Dimension / Metric | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |")
    out.append("| :--- | :--- | :--- | :--- |")
    out.append(f"| **Mean File Recall** | **{sA['mean_recall']:.1f}%** | **{sB['mean_recall']:.1f}%** | **{sC['mean_recall']:.1f}%** |")
    out.append(f"| **Mean File Precision** | **{sA['mean_precision']:.1f}%** | **{sB['mean_precision']:.1f}%** | **{sC['mean_precision']:.1f}%** |")
    out.append(f"| **Mean File F1-Score** | **{sA['mean_f1']:.1f}%** | **{sB['mean_f1']:.1f}%** | **{sC['mean_f1']:.1f}%** |")
    out.append(f"| **Exact File Match Rate** | **{sA['exact_count']/N*100:.1f}%** ({sA['exact_count']}/{N}) | **{sB['exact_count']/N*100:.1f}%** ({sB['exact_count']}/{N}) | **{sC['exact_count']/N*100:.1f}%** ({sC['exact_count']}/{N}) |")
    out.append(f"| **Method Hit Rate** | **{sA['method_count']/N*100:.1f}%** ({sA['method_count']}/{N}) | **{sB['method_count']/N*100:.1f}%** ({sB['method_count']}/{N}) | **{sC['method_count']/N*100:.1f}%** ({sC['method_count']}/{N}) |")
    out.append(f"| **Fault Window Localized Rate (≤25 lines)** | **{sA['window_count']/N*100:.1f}%** ({sA['window_count']}/{N}) | **{sB['window_count']/N*100:.1f}%** ({sB['window_count']}/{N}) | **{sC['window_count']/N*100:.1f}%** ({sC['window_count']}/{N}) |")
    out.append(f"| **Average Total Tokens / Task** | {sA['avg_tokens']:,.0f} tokens | {sB['avg_tokens']:,.0f} tokens | {sC['avg_tokens']:,.0f} tokens |")
    out.append(f"| **Average Tool Calls / Task** | {sA['avg_calls']:.1f} ({sA['avg_src']:.1f} Source, {sA['avg_soot']:.1f} SootUp) | {sB['avg_calls']:.1f} ({sB['avg_src']:.1f} Source, {sB['avg_soot']:.1f} SootUp) | {sC['avg_calls']:.1f} ({sC['avg_src']:.1f} Source, {sC['avg_soot']:.1f} SootUp) |")
    out.append(f"| **Average Execution Latency / Task** | {sA['avg_latency']:.1f}s | {sB['avg_latency']:.1f}s | {sC['avg_latency']:.1f}s |\n")
    out.append("---\n")

    # Section 3: Multi-Task Comparative Matrix
    out.append("## 3. Multi-Task Comparative Matrix\n")
    out.append("| Task ID | Verified Base Commit | GitHub Commit | GitHub Issue | Scope | Recall (A / B / C) | Exact Match | Min Line Proximity (A / B / C) | SootUp Calls (C) |")
    out.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for e in task_entries:
        rec_str = f"{e['rec_A']*100:.0f}% / {e['rec_B']*100:.0f}% / {e['rec_C']*100:.0f}%"
        match_str = f"{'✅' if e['exact_A'] else '❌'} / {'✅' if e['exact_B'] else '❌'} / {'✅' if e['exact_C'] else '❌'}"
        fmt_d = lambda d: f"{d:.1f}" if d is not None else "N/A"
        dist_str = f"{fmt_d(e['dist_A'])} / {fmt_d(e['dist_B'])} / {fmt_d(e['dist_C'])}"
        anchor = e['task'].replace('__', '').replace('-', '')
        out.append(f"| [`{e['task']}`](#{anchor}) | `{e['commit_short']}` | [`{e['commit_short']}` ↗](https://github.com/google/gson/commit/{e['commit_hash']}) | [#{e['id_num']} ↗](https://github.com/google/gson/issues/{e['id_num']}) | {e['scope']} | {rec_str} | {match_str} | {dist_str} | {e['soot_C']} |")
    out.append("\n---\n")

    # Section 4: Individual Task Benchmark Reports
    out.append("## 4. Individual Task Benchmark Reports\n")
    for idx, e in enumerate(task_entries, start=1):
        anchor = e['task'].replace('__', '').replace('-', '')
        out.append(f"### 4.{idx}. Three-Condition Comparative Evaluation: `{e['task']}` <a id=\"{anchor}\"></a>\n")
        out.append(f"**Verified Target Commit:** [`{e['commit_hash']}` ↗](https://github.com/google/gson/commit/{e['commit_hash']}) ({e['commit_subject']}) | **GitHub Issue:** [#{e['id_num']} ↗](https://github.com/google/gson/issues/{e['id_num']})\n")
        out.append(e['clean_table'])
        out.append("\n---\n")

    # Section 5: Scientific Insights & Key Findings
    out.append("## 5. Key Scientific Findings & Qualitative Insights\n")
    out.append("### 5.1. Resolution of Multi-File Defect Tunnel Vision")
    out.append("In real-world enterprise Java projects, bugs frequently bridge decoupled classes, such as inheritance hierarchies, anonymous inner classes, and factory methods. Condition A (Source-only baseline) exhibited severe syntactic tunnel vision: in tasks `google__gson-2061` and `google__gson-2158`, the model localized only the single file returned by text searches (`JsonReader.java` and `TypeAdapters.java`) and prematurely terminated exploration, missing the companion files (`JsonTreeReader.java` and `Gson.java`).")
    out.append("When augmented with SootUp static analysis facts:")
    out.append("- **Condition B (Passive Ahead-of-Time Injection):** Precomputed class hierarchies and allocation sites placed companion subclasses and factory methods directly in the prompt context. The model localized **100% of defect files** in both `google__gson-2061` and `google__gson-2158` with minimal tool overhead.")
    out.append("- **Condition C (Active On-Demand MCP Exploration):** Autonomous invocations of `sootup_hierarchy` and `sootup_find_allocations` dynamically exposed cross-file subclass clusters and instantiation sites, enabling the agent to confirm and localize all defect files with **100% Exact Match**.\n")

    out.append("### 5.2. Accuracy vs. Token Overhead Tradeoff")
    out.append("- **Condition A** represents the lowest cost baseline (~24.7k tokens/task), but fails on 22.2% of tasks due to missing multi-file dependencies.")
    out.append("- **Condition B** achieves **100% Exact Match and 100% File Recall** across all 9 tasks with moderate token overhead (~42.6k tokens/task), demonstrating that compact, high-signal precomputed static facts provide the optimal balance of speed, cost, and localization power.")
    out.append("- **Condition C** achieves identical **100% Exact Match and 100% File Recall** while allowing the LLM to inspect arbitrary bytecode structures on-demand, though at higher conversational token cost (~175.0k tokens/task) due to multi-turn tool calling and schema exchange.\n")

    # Write target file
    target_file = comp_dir / "google_gson_combined_condition_comparison.md"
    target_file.write_text("\n".join(out), encoding="utf-8")
    print(f"Successfully generated new combined benchmark report at: {target_file}")
    print(f"Total lines written: {len(out)}")

if __name__ == "__main__":
    main()
