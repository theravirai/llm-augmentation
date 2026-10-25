from typing import Any, Dict, List, Optional

from .patch_parser import PatchParser
from .metrics import EvaluationReport, MetricsCalculator
from llm_augmentation.agents.base_agent import LocalizationResult
from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext

class Evaluator:
    """
    Automated evaluation engine comparing LLM localization diagnostics to ground-truth Gold Patches.
    """

    @classmethod
    def evaluate_task(
        cls,
        result: LocalizationResult,
        task: Task,
        repo_context: Optional[RepoContext] = None
    ) -> EvaluationReport:
        parsed_gold = PatchParser.parse(task.patch)
        comp_status = "OK"
        if repo_context and not repo_context.is_compilable:
            comp_status = "FAILED"

        return MetricsCalculator.compute(
            result=result,
            gold=parsed_gold,
            compilation_status=comp_status
        )

    @classmethod
    def aggregate_reports(cls, reports: List[EvaluationReport]) -> Dict[str, Any]:
        """
        Aggregates multiple EvaluationReports into a statistical benchmark summary.
        """
        if not reports:
            return {}

        n = len(reports)
        compilable = sum(1 for r in reports if r.compilation_status == "OK")

        mean_recall = sum(r.file_recall for r in reports) / n
        mean_precision = sum(r.file_precision for r in reports) / n
        mean_f1 = sum(r.file_f1 for r in reports) / n
        exact_matches = sum(1 for r in reports if r.exact_file_match)
        method_hits = sum(1 for r in reports if r.method_hit)
        resolved_count = sum(1 for r in reports if r.patch_resolved)

        total_tokens = sum(r.total_tokens for r in reports)
        total_tool_calls = sum(r.tool_calls_count for r in reports)
        total_latency = sum(r.latency_seconds for r in reports)

        return {
            "total_tasks": n,
            "compilable_tasks": compilable,
            "compilation_rate": round(compilable / n * 100, 1),
            "mean_file_recall": round(mean_recall * 100, 1),
            "mean_file_precision": round(mean_precision * 100, 1),
            "mean_file_f1": round(mean_f1 * 100, 1),
            "exact_file_match_rate": round(exact_matches / n * 100, 1),
            "method_hit_rate": round(method_hits / n * 100, 1),
            "patch_resolution_rate": round(resolved_count / n * 100, 1),
            "avg_tokens_per_task": round(total_tokens / n, 1),
            "avg_tool_calls_per_task": round(total_tool_calls / n, 2),
            "avg_latency_seconds": round(total_latency / n, 2),
        }
