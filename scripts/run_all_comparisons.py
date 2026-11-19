import subprocess
import sys
import time
from pathlib import Path

def main():
    tasks = [
        "google__gson-1014",
        "google__gson-1093",
        "google__gson-1100",
        "google__gson-2024",
        "google__gson-2061",
        "google__gson-2134",
        "google__gson-2158",
        "google__gson-2311",
        "google__gson-2479"
    ]

    total_start = time.time()
    print(f"\n{'='*75}")
    print(f"[*] Starting Comprehensive 3-Condition Benchmark Across All {len(tasks)} Tasks")
    print(f"[*] Conditions: Condition A (Source), Condition B (AOT Facts), Condition C (MCP)")
    print(f"{'='*75}\n", flush=True)

    for i, task_id in enumerate(tasks, 1):
        t_start = time.time()
        print(f"\n{'#'*75}")
        print(f"[{i}/{len(tasks)}] Evaluating: {task_id}")
        print(f"{'#'*75}\n", flush=True)
        
        cmd = [sys.executable, "-m", "llm_augmentation.cli", "compare", "-t", task_id]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"[Warning] Task {task_id} exited with code {res.returncode}", flush=True)
        else:
            print(f"[+] Task {task_id} completed successfully in {time.time() - t_start:.1f}s", flush=True)

    # Regenerate the combined benchmark report
    print(f"\n{'='*75}")
    print(f"[*] All {len(tasks)} tasks finished in {time.time() - total_start:.1f}s. Synchronizing combined report...")
    print(f"{'='*75}\n", flush=True)

    from generate_combined_report import main as generate_report
    generate_report()
    print("\n[+] Full benchmark suite execution and combined report generation complete!")

if __name__ == "__main__":
    main()
