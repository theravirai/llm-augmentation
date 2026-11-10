import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext

@dataclass
class LocalizationResult:
    """
    Structured outcome of a fault localization experiment.
    """
    task_id: str
    condition: str  # 'A', 'B', or 'C'
    model: str
    predicted_files: List[str] = field(default_factory=list)
    predicted_classes: List[str] = field(default_factory=list)
    predicted_methods: List[str] = field(default_factory=list)
    predicted_lines: Dict[str, List[int]] = field(default_factory=dict)
    root_cause_explanation: str = ""
    raw_output: str = ""
    system_prompt: str = ""
    initial_user_prompt: str = ""
    tool_calls_count: int = 0
    tool_calls_trace: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    latency_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "condition": self.condition,
            "model": self.model,
            "predicted_files": self.predicted_files,
            "predicted_classes": self.predicted_classes,
            "predicted_methods": self.predicted_methods,
            "predicted_lines": self.predicted_lines,
            "root_cause_explanation": self.root_cause_explanation,
            "system_prompt": self.system_prompt,
            "initial_user_prompt": self.initial_user_prompt,
            "tool_calls_count": self.tool_calls_count,
            "tool_calls_trace": self.tool_calls_trace,
            "token_usage": self.token_usage,
            "latency_seconds": round(self.latency_seconds, 2),
            "raw_output": self.raw_output,
        }

class BaseAgent(ABC):
    """
    Abstract Base Class for Condition Agents.
    """

    def __init__(self, model: str = "gpt-oss-120b"):
        self.model = model

    @abstractmethod
    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        """Executes the localization process for the given task and codebase."""
        pass

    @staticmethod
    def extract_json_diagnosis(text: str) -> Dict[str, Any]:
        """
        Extracts structured diagnosis JSON from markdown code blocks or plain text
        with multi-stage resilient parsing (comments, trailing commas, regex fallbacks).
        """
        if not text:
            return {}

        # 1. Clean comments and trailing commas
        cleaned = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

        # 2. Look for ```json ... ``` block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except Exception:
                pass

        # 3. Look for outermost { ... }
        brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except Exception:
                pass

        # 4. Resilient regex extraction fallback
        diagnosis: Dict[str, Any] = {
            "localized_files": [],
            "localized_classes": [],
            "localized_methods": [],
            "localized_lines": {},
            "root_cause_explanation": text.strip()
        }

        files_m = re.search(r'"(?:localized_files|files)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if files_m:
            diagnosis["localized_files"] = [f.strip().strip("'\"") for f in re.findall(r'["\']([^"\']+)["\']', files_m.group(1))]

        classes_m = re.search(r'"(?:localized_classes|classes)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if classes_m:
            diagnosis["localized_classes"] = [c.strip().strip("'\"") for c in re.findall(r'["\']([^"\']+)["\']', classes_m.group(1))]

        methods_m = re.search(r'"(?:localized_methods|methods)"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if methods_m:
            diagnosis["localized_methods"] = [m.strip().strip("'\"") for m in re.findall(r'["\']([^"\']+)["\']', methods_m.group(1))]

        lines_m = re.search(r'"(?:localized_lines|lines)"\s*:\s*\{([^}]+)\}', text, re.DOTALL)
        if lines_m:
            file_lines = re.findall(r'["\']([^"\']+)["\']\s*:\s*\[([0-9,\s\-]+)\]', lines_m.group(1))
            for fpath, lnums in file_lines:
                nums = [int(n.strip()) for n in re.findall(r'\b\d+\b', lnums)]
                if nums:
                    diagnosis["localized_lines"][fpath] = nums

        expl_m = re.search(r'"root_cause_explanation"\s*:\s*"([^"]+)"', text, re.DOTALL)
        if expl_m:
            diagnosis["root_cause_explanation"] = expl_m.group(1)

        return diagnosis
