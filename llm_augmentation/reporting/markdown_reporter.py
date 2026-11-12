import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_augmentation.evaluation.metrics import EvaluationReport

class MarkdownReporter:
    """
    Generates academic Markdown benchmark reports and condition comparison tables.
    """

    @classmethod
    def generate_task_report(
        cls,
        report: EvaluationReport,
        traces: Optional[List[Dict[str, Any]]] = None,
        raw_output: Optional[str] = None
    ) -> str:
        md = []
        md.append(f"# Fault Localization Report: `{report.task_id}`\n")
        md.append(f"**Condition:** {report.condition}  ")
        md.append(f"**Model:** {report.model}  ")
        if report.target_commit:
            commit_info = f"`{report.target_commit}`"
            if report.target_commit_subject:
                commit_info += f" ({report.target_commit_subject})"
            md.append(f"**Target Commit:** {commit_info} [Verified Faulty Base Commit]  ")
        md.append(f"**Compilation Status:** {report.compilation_status}  ")
        md.append(f"**Exact File Match:** {'✅ Yes' if report.exact_file_match else '❌ No'}  ")
        md.append(f"**Fault Window Localized (≤25 lines):** {'✅ Yes' if report.fault_window_localized else '❌ No'}  \n")

        md.append("## RQ1: Localization Accuracy")
        md.append("| Metric | Value |")
        md.append("| :--- | :--- |")
        md.append(f"| File Recall | {report.file_recall * 100:.1f}% |")
        md.append(f"| File Precision | {report.file_precision * 100:.1f}% |")
        md.append(f"| File F1-Score | {report.file_f1 * 100:.1f}% |")
        md.append(f"| Method Hit | {'✅ Yes' if report.method_hit else '❌ No'} ({', '.join(report.matched_methods) or 'None'}) |")
        line_dist_str = f"{report.min_line_distance:.1f} lines" if report.min_line_distance is not None else "N/A"
        md.append(f"| Min Line Proximity | {line_dist_str} |")
        md.append(f"| Fault Window Localized | {'✅ Yes' if report.fault_window_localized else '❌ No'} |")
        md.append("")

        md.append("### File Identification Details")
        md.append(f"- **Gold Files ({len(report.gold_files)}):** `{', '.join(report.gold_files)}`")
        md.append(f"- **Predicted Files ({len(report.predicted_files)}):** `{', '.join(report.predicted_files) or 'None'}`")
        md.append(f"- **Matched Files ({len(report.matched_files)}):** `{', '.join(report.matched_files) or 'None'}`")
        if report.missed_files:
            md.append(f"- **Missed Files ({len(report.missed_files)}):** `{', '.join(report.missed_files)}`")
        if report.spurious_files:
            md.append(f"- **Spurious Files ({len(report.spurious_files)}):** `{', '.join(report.spurious_files)}`")
        md.append("")

        md.append("## RQ2: Efficiency & Cost")
        md.append("| Metric | Value |")
        md.append("| :--- | :--- |")
        md.append(f"| Tool Calls Count | {report.tool_calls_count} ({report.source_tool_calls} Source, {report.mcp_tool_calls} SootUp MCP) |")
        md.append(f"| Prompt Tokens | {report.prompt_tokens} |")
        md.append(f"| Completion Tokens | {report.completion_tokens} |")
        md.append(f"| Total Tokens | {report.total_tokens} |")
        md.append(f"| Execution Latency | {report.latency_seconds:.2f}s |")
        md.append("")

        if traces:
            md.append("## Step-by-Step Tool Execution Trace")
            md.append("| Step | Tool Type | Tool Name | Arguments | Output Preview |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for idx, tr in enumerate(traces, start=1):
                tool_name = tr.get("tool", "unknown")
                is_mcp = tool_name.startswith("sootup_")
                tool_type = "SootUp MCP" if is_mcp else "Source Tool"
                args_str = json.dumps(tr.get("arguments", {}))
                if len(args_str) > 80:
                    args_str = args_str[:77] + "..."
                args_cell = f"`{args_str}`"
                preview = tr.get("output_preview", "").replace("\n", " ").replace("|", "\\|").strip()
                if len(preview) > 100:
                    preview = preview[:97] + "..."
                md.append(f"| {idx} | {tool_type} | `{tool_name}` | {args_cell} | {preview} |")
            md.append("")

        if raw_output:
            md.append("## LLM Model Final Diagnosis")
            md.append("```json")
            md.append(raw_output.strip())
            md.append("```\n")

        if report.system_prompt or report.initial_user_prompt:
            md.append("## Turn 1: Initial Prompts Given to Subject LLM\n")
            if report.system_prompt:
                md.append("<details>")
                md.append("<summary><b>View System Prompt</b></summary>\n")
                md.append("```text")
                md.append(report.system_prompt.strip())
                md.append("```")
                md.append("</details>\n")
            if report.initial_user_prompt:
                md.append("<details>")
                md.append("<summary><b>View Initial User Prompt</b></summary>\n")
                md.append("```text")
                md.append(report.initial_user_prompt.strip())
                md.append("```")
                md.append("</details>\n")

        return "\n".join(md)

    @classmethod
    def generate_batch_report(
        cls,
        summary: Dict[str, Any],
        reports: List[EvaluationReport],
        title: str = "Benchmark Evaluation Report"
    ) -> str:
        md = []
        md.append(f"# {title}\n")
        md.append(f"**Total Tasks:** {summary.get('total_tasks', 0)}  ")
        md.append(f"**Compilable Tasks:** {summary.get('compilable_tasks', 0)} ({summary.get('compilation_rate', 0)}%)  \n")

        md.append("## Overall Benchmark Summary (RQ1 & RQ2)")
        md.append("| Metric | Result |")
        md.append("| :--- | :--- |")
        md.append(f"| Mean File Recall | **{summary.get('mean_file_recall', 0)}%** |")
        md.append(f"| Mean File Precision | **{summary.get('mean_file_precision', 0)}%** |")
        md.append(f"| Mean File F1 | **{summary.get('mean_file_f1', 0)}%** |")
        md.append(f"| Exact File Match Rate | **{summary.get('exact_file_match_rate', 0)}%** |")
        md.append(f"| Method Hit Rate | **{summary.get('method_hit_rate', 0)}%** |")
        md.append(f"| Downstream Patch Resolution Rate | **{summary.get('patch_resolution_rate', 0)}%** |")
        md.append(f"| Avg Tokens per Task | {summary.get('avg_tokens_per_task', 0)} |")
        md.append(f"| Avg Tool Calls per Task | {summary.get('avg_tool_calls_per_task', 0)} |")
        md.append(f"| Avg Latency per Task | {summary.get('avg_latency_seconds', 0)}s |")
        md.append("")

        md.append("## Per-Task Breakdown")
        md.append("| Task ID | Cond | Gold Files | Matched | Recall | Precision | Method Hit | Exact Match | Resolved | Latency |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in reports:
            exact_str = "✅" if r.exact_file_match else "❌"
            meth_str = "✅" if r.method_hit else "❌"
            res_str = "✅" if r.patch_resolved else "❌"
            md.append(
                f"| `{r.task_id}` | {r.condition} | {len(r.gold_files)} | {len(r.matched_files)} | "
                f"{r.file_recall*100:.0f}% | {r.file_precision*100:.0f}% | {meth_str} | {exact_str} | {res_str} | {r.latency_seconds:.1f}s |"
            )

        return "\n".join(md)

    @classmethod
    def generate_comparison_table(cls, reports_by_condition: Dict[str, EvaluationReport]) -> str:
        """
        Produces a side-by-side comparison table for Conditions A, B, and C.
        """
        md = []
        task_id = next(iter(reports_by_condition.values())).task_id if reports_by_condition else "Unknown"
        md.append(f"# Three-Condition Comparative Evaluation: `{task_id}`\n")

        conds = ["A", "B", "C"]
        rA = reports_by_condition.get("A")
        rB = reports_by_condition.get("B")
        rC = reports_by_condition.get("C")

        first_rep = rA or rB or rC
        if first_rep and first_rep.target_commit:
            commit_lbl = f"`{first_rep.target_commit}`"
            if first_rep.target_commit_subject:
                commit_lbl += f" ({first_rep.target_commit_subject})"
            md.append(f"**Verified Target Commit:** {commit_lbl}\n")

        md.append("| Dimension | Condition A (Source Only) | Condition B (Precomputed Facts) | Condition C (On-Demand MCP) |")
        md.append("| :--- | :--- | :--- | :--- |")

        def val(report, attr, fmt=lambda x: str(x)):
            return fmt(getattr(report, attr)) if report else "N/A"

        def tool_calls_fmt(report):
            if not report:
                return "N/A"
            return f"{report.tool_calls_count} ({report.source_tool_calls} Source, {report.mcp_tool_calls} SootUp MCP)"

        md.append(f"| **File Recall** | {val(rA, 'file_recall', lambda x: f'{x*100:.0f}%')} | {val(rB, 'file_recall', lambda x: f'{x*100:.0f}%')} | {val(rC, 'file_recall', lambda x: f'{x*100:.0f}%')} |")
        md.append(f"| **File Precision** | {val(rA, 'file_precision', lambda x: f'{x*100:.0f}%')} | {val(rB, 'file_precision', lambda x: f'{x*100:.0f}%')} | {val(rC, 'file_precision', lambda x: f'{x*100:.0f}%')} |")
        md.append(f"| **Exact Match** | {val(rA, 'exact_file_match', lambda x: '✅ Yes' if x else '❌ No')} | {val(rB, 'exact_file_match', lambda x: '✅ Yes' if x else '❌ No')} | {val(rC, 'exact_file_match', lambda x: '✅ Yes' if x else '❌ No')} |")
        md.append(f"| **Method Hit** | {val(rA, 'method_hit', lambda x: '✅ Yes' if x else '❌ No')} | {val(rB, 'method_hit', lambda x: '✅ Yes' if x else '❌ No')} | {val(rC, 'method_hit', lambda x: '✅ Yes' if x else '❌ No')} |")
        md.append(f"| **Min Line Distance** | {val(rA, 'min_line_distance', lambda x: f'{x:.1f} lines' if x is not None else 'N/A')} | {val(rB, 'min_line_distance', lambda x: f'{x:.1f} lines' if x is not None else 'N/A')} | {val(rC, 'min_line_distance', lambda x: f'{x:.1f} lines' if x is not None else 'N/A')} |")
        md.append(f"| **Fault Window Localized (≤25 lines)** | {val(rA, 'fault_window_localized', lambda x: '✅ Yes' if x else '❌ No')} | {val(rB, 'fault_window_localized', lambda x: '✅ Yes' if x else '❌ No')} | {val(rC, 'fault_window_localized', lambda x: '✅ Yes' if x else '❌ No')} |")
        md.append(f"| **Tool Calls Breakdown** | {tool_calls_fmt(rA)} | {tool_calls_fmt(rB)} | {tool_calls_fmt(rC)} |")
        md.append(f"| **Total Tokens** | {val(rA, 'total_tokens')} | {val(rB, 'total_tokens')} | {val(rC, 'total_tokens')} |")
        md.append(f"| **Latency** | {val(rA, 'latency_seconds', lambda x: f'{x:.1f}s')} | {val(rB, 'latency_seconds', lambda x: f'{x:.1f}s')} | {val(rC, 'latency_seconds', lambda x: f'{x:.1f}s')} |")

        return "\n".join(md)
