import glob
import json
from pathlib import Path
from typing import Dict, List, Optional

from .task import Task

DEFAULT_DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets"

class TaskLoader:
    """
    Manages loading and querying of SWE-Bench Multilingual (Java) defect tasks.
    """

    def __init__(self, datasets_dir: str | Path = DEFAULT_DATASETS_DIR):
        self.datasets_dir = Path(datasets_dir).resolve()
        self._tasks_cache: Dict[str, Task] = {}
        self._load_all_tasks()

    def _load_all_tasks(self):
        for json_file in glob.glob(str(self.datasets_dir / "*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    for item in entries:
                        task = Task.from_dict(item)
                        self._tasks_cache[task.instance_id] = task
            except Exception as e:
                print(f"[Warning] Failed to load dataset file {json_file}: {e}")

    def get_task(self, instance_id: str) -> Optional[Task]:
        """Retrieves a task by its SWE-Bench instance ID."""
        return self._tasks_cache.get(instance_id)

    def list_tasks(self, repo_filter: Optional[str] = None) -> List[Task]:
        """Lists all tasks, optionally filtered by repo name (e.g. 'gson', 'druid')."""
        if not repo_filter:
            return list(self._tasks_cache.values())
        rf = repo_filter.lower()
        return [
            t for t in self._tasks_cache.values()
            if rf in t.repo.lower() or rf in t.instance_id.lower()
        ]

    def load_dataset_file(self, filepath: str | Path) -> List[Task]:
        """Loads tasks from a specific JSON dataset file."""
        path = Path(filepath).resolve()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Task.from_dict(item) for item in data]
