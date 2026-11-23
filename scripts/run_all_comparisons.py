import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_augmentation.benchmark.task_loader import TaskLoader

def main():
    parser = argparse.ArgumentParser(description="Run 3-condition comparative evaluations across all tasks in a dataset")
    parser.add_argument(
        "--dataset",
        default="datasets/gson_tasks.json",
        help="Path to dataset JSON file (e.g. datasets/druid_tasks.json)"
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Optional repo filter (e.g. 'gson', 'druid')"
    )
    parser.add_argument(
        "--target-dir",
        default=None,
        help="Optional explicit path to compiled target/classes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of tasks to evaluate"
    )
    args = parser.parse_args()

    loader = TaskLoader()
    if args.repo:
        tasks = loader.list_tasks(args.repo)
    else:
        dataset_path = Path(args.dataset).resolve()
        if not dataset_path.exists():
            print(f"[Error] Dataset file not found: {dataset_path}")
            sys.exit(1)
        tasks = loader.load_dataset_file(dataset_path)

    if args.limit:
        tasks = tasks[:args.limit]

    if not tasks:
        print("[Error] No tasks found to evaluate.")
        sys.exit(1)

    repo_slug = tasks[0].repo.replace("/", "__")
    total_start = time.time()
    print(f"\n{'='*75}")
    print(f"[*] Starting Comprehensive 3-Condition Benchmark Across {len(tasks)} Tasks ({repo_slug})")
    print(f"[*] Conditions: Condition A (Source), Condition B (AOT Facts), Condition C (MCP)")
    print(f"{'='*75}\n", flush=True)

    for i, task in enumerate(tasks, 1):
        t_start = time.time()
        print(f"\n{'#'*75}")
        print(f"[{i}/{len(tasks)}] Evaluating: {task.instance_id} ({task.repo})")
        print(f"{'#'*75}\n", flush=True)

        cmd = [sys.executable, "-m", "llm_augmentation.cli", "compare", "-t", task.instance_id]
        if args.target_dir:
            cmd.extend(["--target-dir", args.target_dir])

        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"[Warning] Task {task.instance_id} exited with code {res.returncode}", flush=True)
        else:
            print(f"[+] Task {task.instance_id} completed successfully in {time.time() - t_start:.1f}s", flush=True)

    # Regenerate the combined benchmark report for this repository
    print(f"\n{'='*75}")
    print(f"[*] All {len(tasks)} tasks finished in {time.time() - total_start:.1f}s. Synchronizing combined report...")
    print(f"{'='*75}\n", flush=True)

    from generate_combined_report import generate_report
    generate_report(repo_slug=repo_slug)
    print(f"\n[+] Full benchmark suite execution and combined report generation complete for {repo_slug}!")

if __name__ == "__main__":
    main()
