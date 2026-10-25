import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llm_augmentation.benchmark import TaskLoader
from llm_augmentation.agents.base_agent import LocalizationResult
from llm_augmentation.evaluation.evaluator import Evaluator
from llm_augmentation.reporting import MarkdownReporter

def test_evaluation_condition_a_vs_c():
    loader = TaskLoader()
    task = loader.get_task("google__gson-2158")
    assert task is not None

    # Condition A: Model only found TypeAdapters.java, missed Gson.java
    res_A = LocalizationResult(
        task_id=task.instance_id,
        condition="A",
        model="gpt-oss-120b",
        predicted_files=["gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java"],
        predicted_classes=["com.google.gson.internal.bind.TypeAdapters"],
        predicted_methods=["TypeAdapters.write"],
        predicted_lines={"TypeAdapters.java": [195]},
        token_usage={"prompt_tokens": 1200, "completion_tokens": 300, "total_tokens": 1500},
        latency_seconds=3.2
    )

    report_A = Evaluator.evaluate_task(res_A, task)
    assert report_A.file_recall == 0.5, f"Expected 0.5 recall, got {report_A.file_recall}"
    assert not report_A.exact_file_match
    assert "Gson.java" in [Path(f).name for f in report_A.missed_files]

    # Condition C: Model with SootUp found both TypeAdapters.java and Gson.java
    res_C = LocalizationResult(
        task_id=task.instance_id,
        condition="C",
        model="gpt-oss-120b",
        predicted_files=[
            "gson/src/main/java/com/google/gson/Gson.java",
            "gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java"
        ],
        predicted_classes=["com.google.gson.Gson", "com.google.gson.internal.bind.TypeAdapters"],
        predicted_methods=["com.google.gson.Gson.doubleAdapter"],
        predicted_lines={"Gson.java": [398]},
        tool_calls_count=2,
        token_usage={"prompt_tokens": 2500, "completion_tokens": 400, "total_tokens": 2900},
        latency_seconds=6.8
    )

    report_C = Evaluator.evaluate_task(res_C, task)
    assert report_C.file_recall == 1.0, f"Expected 1.0 recall, got {report_C.file_recall}"
    assert report_C.exact_file_match
    assert report_C.method_hit
    assert report_C.patch_resolved
    assert report_C.exact_line_hit

    # Test Comparison Table Generation
    comp_table = MarkdownReporter.generate_comparison_table({"A": report_A, "C": report_C})
    assert "Condition A (Source Only)" in comp_table
    assert "Condition C (On-Demand MCP)" in comp_table
    assert "50%" in comp_table
    assert "100%" in comp_table

    # Test Aggregation
    summary = Evaluator.aggregate_reports([report_A, report_C])
    assert summary["total_tasks"] == 2
    assert summary["mean_file_recall"] == 75.0
    assert summary["exact_file_match_rate"] == 50.0

    print("All Evaluation Engine tests passed successfully!")

if __name__ == "__main__":
    test_evaluation_condition_a_vs_c()
