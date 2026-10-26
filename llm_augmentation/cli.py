import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from llm_augmentation.config import load_config
from llm_augmentation.benchmark.task_loader import TaskLoader
from llm_augmentation.benchmark.repo_manager import RepoManager, RepoContext
from llm_augmentation.mcp.client import McpClient
from llm_augmentation.agents import (
    ConditionAAgent,
    ConditionBAgent,
    ConditionCAgent,
    LLMGateway
)
from llm_augmentation.evaluation.evaluator import Evaluator
from llm_augmentation.evaluation.metrics import EvaluationReport
from llm_augmentation.reporting import JsonLogger, MarkdownReporter

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-augmentation",
        description="LLM-Augmented Java Program Analysis and Fault Localization Framework (Conditions A, B, C)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Run fault localization on a single benchmark task")
    run_parser.add_argument(
        "-c", "--condition",
        choices=["A", "B", "C", "a", "b", "c"],
        required=True,
        help="Experimental Condition: A (Source Only), B (Precomputed Static Facts), C (On-Demand MCP)"
    )
    run_parser.add_argument(
        "-t", "--task",
        required=True,
        help="Task ID to analyze (e.g. 'google__gson-2158' or 'apache__druid-14136')"
    )
    run_parser.add_argument(
        "-m", "--model",
        default=None,
        help="LLM Model to use (defaults to config: gpt-oss-120b)"
    )
    run_parser.add_argument(
        "-d", "--dataset",
        default=None,
        help="Path to SWE-Bench Java dataset JSON file"
    )
    run_parser.add_argument(
        "-o", "--output-dir",
        default="results",
        help="Directory to save execution traces and evaluation results"
    )
    run_parser.add_argument(
        "--target-dir",
        default=None,
        help="Path to compiled target classes directory (overrides auto-detection)"
    )

    # Subcommand: benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Run automated benchmark batch without human intervention")
    bench_parser.add_argument(
        "-d", "--dataset",
        required=True,
        help="Path to SWE-Bench Java dataset JSON file (e.g. datasets/gson_tasks.json)"
    )
    bench_parser.add_argument(
        "-c", "--condition",
        choices=["A", "B", "C", "a", "b", "c"],
        required=True,
        help="Experimental Condition: A, B, or C"
    )
    bench_parser.add_argument(
        "-m", "--model",
        default=None,
        help="LLM Model to use"
    )
    bench_parser.add_argument(
        "-o", "--output-dir",
        default="results/benchmark",
        help="Directory to store evaluation metrics and reports"
    )
    bench_parser.add_argument(
        "--timeout-per-task",
        type=int,
        default=300,
        help="Max timeout per task in seconds (default: 300)"
    )
    bench_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tasks to run (useful for quick dry runs)"
    )

    # Subcommand: compare
    comp_parser = subparsers.add_parser("compare", help="Compare Conditions A, B, and C on a task")
    comp_parser.add_argument(
        "-t", "--task",
        required=True,
        help="Task ID to compare across conditions"
    )
    comp_parser.add_argument(
        "-m", "--model",
        default=None,
        help="LLM Model to use"
    )
    comp_parser.add_argument(
        "-o", "--output-dir",
        default="results/comparison",
        help="Directory to store comparative report"
    )

    # Subcommand: tools (Direct MCP tool execution utility)
    tool_parser = subparsers.add_parser("tools", help="Directly query SootUp MCP static analysis tools")
    tool_parser.add_argument(
        "tool_name",
        choices=["hierarchy", "inspect-method", "find-allocations", "find-invocations", "callgraph"],
        help="Primitive tool name to execute"
    )
    tool_parser.add_argument("--target-class", help="Target Java class name")
    tool_parser.add_argument("--target-method", help="Target Java method name")
    tool_parser.add_argument("--scope-class", help="Optional enclosing scope class")
    tool_parser.add_argument("--algorithm", default="cha", help="Callgraph algorithm: cha, rta, or spark")
    tool_parser.add_argument("--entry-class", help="Entry point class for callgraph")
    tool_parser.add_argument("--entry-method", help="Entry point method for callgraph")
    tool_parser.add_argument("--return-type", default="void", help="Return type for callgraph entry point")
    tool_parser.add_argument("--target-dir", required=True, help="Path to compiled target classes directory")

    return parser

def get_agent(condition: str, model: str, config: Dict):
    cond = condition.upper()
    engine_dir = Path(__file__).resolve().parent.parent / config["paths"]["sootup_engine_dir"]
    gateway = LLMGateway(default_model=model)

    if cond == "A":
        return ConditionAAgent(model=model, gateway=gateway)
    elif cond == "B":
        return ConditionBAgent(model=model, gateway=gateway, sootup_engine_dir=engine_dir)
    elif cond == "C":
        return ConditionCAgent(model=model, gateway=gateway, sootup_engine_dir=engine_dir)
    else:
        raise ValueError(f"Unknown condition: {condition}")

def handle_run(args, config):
    condition = args.condition.upper()
    model = args.model or config["defaults"]["model"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = TaskLoader()
    task = loader.get_task(args.task)
    if not task:
        print(f"[Error] Task '{args.task}' not found in ingested datasets.")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"[*] Starting Fault Localization: Task={task.instance_id} | Condition={condition} | Model={model}")
    print(f"{'='*70}")

    repo_manager = RepoManager()
    repo_context = repo_manager.prepare_repo_for_task(task, compile_if_needed=False)
    if args.target_dir:
        repo_context.target_classes_dirs = [Path(args.target_dir).resolve()]

    agent = get_agent(condition, model, config)
    res = agent.run(task, repo_context)

    # Evaluate against developer Gold Patch
    report = Evaluator.evaluate_task(res, task, repo_context)

    # Save reports
    md_report = MarkdownReporter.generate_task_report(report)
    md_file = output_dir / f"{task.instance_id}_cond_{condition}_report.md"
    json_file = output_dir / f"{task.instance_id}_cond_{condition}_eval.json"

    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_report)
    JsonLogger.save_task_report(report, json_file)

    print(md_report)
    print(f"\n[+] Results saved to: {md_file} and {json_file}")

def handle_benchmark(args, config):
    condition = args.condition.upper()
    model = args.model or config["defaults"]["model"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = TaskLoader()
    tasks = loader.load_dataset_file(args.dataset)
    if args.limit:
        tasks = tasks[:args.limit]

    print(f"\n{'='*70}")
    print(f"[*] Batch Benchmark Execution (Zero Human Intervention)")
    print(f"[*] Total Tasks: {len(tasks)} | Condition={condition} | Model={model}")
    print(f"{'='*70}\n")

    repo_manager = RepoManager()
    agent = get_agent(condition, model, config)
    reports: List[EvaluationReport] = []

    for i, task in enumerate(tasks, start=1):
        print(f"[{i}/{len(tasks)}] Evaluating {task.instance_id} ({task.repo})...", end="", flush=True)
        repo_context = repo_manager.prepare_repo_for_task(task, compile_if_needed=False)

        try:
            res = agent.run(task, repo_context)
            rep = Evaluator.evaluate_task(res, task, repo_context)
            reports.append(rep)
            status_str = "MATCH" if rep.exact_file_match else "PARTIAL" if rep.file_recall > 0 else "MISSED"
            print(f" -> {status_str} (Recall: {rep.file_recall*100:.0f}%, Latency: {rep.latency_seconds:.1f}s)")
        except Exception as e:
            print(f" -> ERROR: {e}")

    # Aggregate results
    summary = Evaluator.aggregate_reports(reports)
    dataset_name = Path(args.dataset).stem
    batch_title = f"SWE-Bench Java Benchmark: {dataset_name} (Condition {condition})"
    md_content = MarkdownReporter.generate_batch_report(summary, reports, title=batch_title)

    summary_md_file = output_dir / f"{dataset_name}_cond_{condition}_summary.md"
    summary_json_file = output_dir / f"{dataset_name}_cond_{condition}_summary.json"

    with open(summary_md_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    JsonLogger.save_batch_summary(summary, reports, summary_json_file)

    print("\n" + md_content)
    print(f"\n[+] Batch benchmark completed without human intervention.")
    print(f"[+] Summary written to: {summary_md_file} and {summary_json_file}")

def handle_compare(args, config):
    model = args.model or config["defaults"]["model"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = TaskLoader()
    task = loader.get_task(args.task)
    if not task:
        print(f"[Error] Task '{args.task}' not found.")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"[*] Three-Condition Comparative Evaluation: {task.instance_id} | Model={model}")
    print(f"{'='*70}\n")

    repo_manager = RepoManager()
    repo_context = repo_manager.prepare_repo_for_task(task, compile_if_needed=False)

    reports: Dict[str, EvaluationReport] = {}
    for cond in ["A", "B", "C"]:
        print(f"[*] Running Condition {cond}...", flush=True)
        agent = get_agent(cond, model, config)
        res = agent.run(task, repo_context)
        rep = Evaluator.evaluate_task(res, task, repo_context)
        reports[cond] = rep

    comp_table = MarkdownReporter.generate_comparison_table(reports)
    comp_file = output_dir / f"{task.instance_id}_condition_comparison.md"
    with open(comp_file, "w", encoding="utf-8") as f:
        f.write(comp_table)

    print(comp_table)
    print(f"\n[+] Comparison saved to: {comp_file}")

def handle_tools(args, config):
    engine_dir = Path(__file__).resolve().parent.parent / config["paths"]["sootup_engine_dir"]
    with McpClient(sootup_engine_dir=engine_dir, default_target_dir=args.target_dir) as client:
        tool_map = {
            "hierarchy": ("sootup_hierarchy", {"target_class": args.target_class}),
            "inspect-method": ("sootup_inspect_method", {"target_class": args.target_class, "target_method": args.target_method}),
            "find-allocations": ("sootup_find_allocations", {"target_class": args.target_class, "scope_class": args.scope_class}),
            "find-invocations": ("sootup_find_invocations", {"target_class": args.target_class, "target_method": args.target_method, "scope_class": args.scope_class}),
            "callgraph": ("sootup_callgraph", {
                "algorithm": args.algorithm,
                "entry_class": args.entry_class,
                "entry_method": args.entry_method,
                "return_type": args.return_type
            })
        }
        mcp_tool_name, params = tool_map[args.tool_name]
        params = {k: v for k, v in params.items() if v is not None}
        print(f"[*] Invoking {mcp_tool_name} with params: {params}")
        output = client.call_tool(mcp_tool_name, params)
        print(output)

def main(args=None):
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    config = load_config()

    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)

    if parsed_args.command == "tools":
        handle_tools(parsed_args, config)
    elif parsed_args.command == "run":
        handle_run(parsed_args, config)
    elif parsed_args.command == "benchmark":
        handle_benchmark(parsed_args, config)
    elif parsed_args.command == "compare":
        handle_compare(parsed_args, config)

if __name__ == "__main__":
    main()
