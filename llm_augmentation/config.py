import os
from pathlib import Path
from typing import Any, Dict
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

def load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "model": "gpt-oss-120b",
                "timeout_per_task": 300,
                "max_tool_iterations": 10,
                "token_budget": 16000,
            },
            "paths": {
                "sootup_engine_dir": "sootup_engine",
                "datasets_dir": "datasets",
                "results_dir": "results",
            }
        }
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
