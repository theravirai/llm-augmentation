import json
from pathlib import Path
from typing import Any, Dict, List

from llm_augmentation.evaluation.metrics import EvaluationReport

class JsonLogger:
    """
    Persists evaluation results and execution traces to machine-readable JSON files.
    """

    @classmethod
    def save_task_report(cls, report: EvaluationReport, output_file: str | Path):
        path = Path(output_file).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

    @classmethod
    def save_batch_summary(
        cls,
        summary: Dict[str, Any],
        reports: List[EvaluationReport],
        output_file: str | Path
    ):
        path = Path(output_file).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": summary,
            "tasks": [r.to_dict() for r in reports]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
