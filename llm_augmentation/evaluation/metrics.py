import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .patch_parser import ParsedPatch
from llm_augmentation.agents.base_agent import LocalizationResult

@dataclass
class EvaluationReport:
    """
    Comprehensive quantitative evaluation metrics for a single fault localization run.
    Answers RQ1 (Effectiveness) and RQ2 (Cost-Benefit).
    """
    task_id: str
    condition: str
    model: str

    # RQ1: Localization Accuracy Metrics
    gold_files: List[str] = field(default_factory=list)
    predicted_files: List[str] = field(default_factory=list)
    matched_files: List[str] = field(default_factory=list)
    missed_files: List[str] = field(default_factory=list)
    spurious_files: List[str] = field(default_factory=list)

    file_recall: float = 0.0
    file_precision: float = 0.0
    file_f1: float = 0.0
    exact_file_match: bool = False

    method_hit: bool = False
    matched_methods: List[str] = field(default_factory=list)
    gold_methods: List[str] = field(default_factory=list)

    min_line_distance: Optional[float] = None
    exact_line_hit: bool = False

    # Downstream Patch Resolution measure (Slide 31)
    patch_resolved: bool = False

    # RQ2: Efficiency & Cost Metrics
    tool_calls_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    compilation_status: str = "OK"  # "OK", "SKIPPED", "FAILED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "condition": self.condition,
            "model": self.model,
            "rq1_accuracy": {
                "file_recall": round(self.file_recall, 4),
                "file_precision": round(self.file_precision, 4),
                "file_f1": round(self.file_f1, 4),
                "exact_file_match": self.exact_file_match,
                "method_hit": self.method_hit,
                "min_line_distance": round(self.min_line_distance, 1) if self.min_line_distance is not None else None,
                "exact_line_hit": self.exact_line_hit,
                "patch_resolved": self.patch_resolved,
                "matched_files": self.matched_files,
                "missed_files": self.missed_files,
                "spurious_files": self.spurious_files,
                "matched_methods": self.matched_methods,
            },
            "rq2_cost": {
                "tool_calls_count": self.tool_calls_count,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "latency_seconds": round(self.latency_seconds, 2),
                "compilation_status": self.compilation_status,
            }
        }

class MetricsCalculator:
    """
    Calculates scientific metrics comparing localization predictions to parsed Gold Patches.
    """

    @classmethod
    def compute(
        cls,
        result: LocalizationResult,
        gold: ParsedPatch,
        compilation_status: str = "OK"
    ) -> EvaluationReport:
        # Normalize files: check both full path and basename match
        gold_basenames = {Path(p).name: p for p in gold.file_paths}
        pred_basenames = {Path(p).name: p for p in result.predicted_files}

        matched_base = set(gold_basenames.keys()).intersection(set(pred_basenames.keys()))
        matched_files = [gold_basenames[b] for b in matched_base]

        missed_base = set(gold_basenames.keys()) - set(pred_basenames.keys())
        missed_files = [gold_basenames[b] for b in missed_base]

        spurious_base = set(pred_basenames.keys()) - set(gold_basenames.keys())
        spurious_files = [pred_basenames[b] for b in spurious_base]

        # File Recall & Precision
        total_gold = len(gold_basenames)
        total_pred = len(pred_basenames)

        recall = len(matched_base) / total_gold if total_gold > 0 else 0.0
        precision = len(matched_base) / total_pred if total_pred > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        exact_file_match = (len(missed_base) == 0 and len(matched_base) == total_gold)

        # Method Hit
        matched_methods = []
        method_hit = False
        gold_meth_lower = {m.lower(): m for m in gold.method_names}
        for pred_m in result.predicted_methods:
            # Extract method name if qualified e.g. "com.google.gson.Gson.doubleAdapter"
            short_m = pred_m.split(".")[-1].lower()
            if short_m in gold_meth_lower:
                method_hit = True
                matched_methods.append(gold_meth_lower[short_m])

        # Line Proximity
        min_line_dist: Optional[float] = None
        exact_line_hit = False
        all_distances = []

        for pred_file_str, pred_lines in result.predicted_lines.items():
            base = Path(pred_file_str).name
            if base in gold.lines_by_file:
                gold_lines = gold.lines_by_file[base]
                for p_line in pred_lines:
                    if p_line in gold_lines:
                        exact_line_hit = True
                        all_distances.append(0.0)
                    else:
                        dists = [abs(p_line - g_line) for g_line in gold_lines]
                        if dists:
                            all_distances.append(float(min(dists)))

        if all_distances:
            min_line_dist = min(all_distances)

        # Downstream patch resolution heuristic:
        # Patch is resolved if all gold files are localized and at least one key method/line is localized
        patch_resolved = exact_file_match and (method_hit or exact_line_hit or (min_line_dist is not None and min_line_dist <= 25))

        return EvaluationReport(
            task_id=result.task_id,
            condition=result.condition,
            model=result.model,
            gold_files=list(gold.file_paths),
            predicted_files=result.predicted_files,
            matched_files=matched_files,
            missed_files=missed_files,
            spurious_files=spurious_files,
            file_recall=recall,
            file_precision=precision,
            file_f1=f1,
            exact_file_match=exact_file_match,
            method_hit=method_hit,
            matched_methods=matched_methods,
            gold_methods=list(gold.method_names),
            min_line_distance=min_line_dist,
            exact_line_hit=exact_line_hit,
            patch_resolved=patch_resolved,
            tool_calls_count=result.tool_calls_count,
            prompt_tokens=result.token_usage.get("prompt_tokens", 0),
            completion_tokens=result.token_usage.get("completion_tokens", 0),
            total_tokens=result.token_usage.get("total_tokens", 0),
            latency_seconds=result.latency_seconds,
            compilation_status=compilation_status
        )
