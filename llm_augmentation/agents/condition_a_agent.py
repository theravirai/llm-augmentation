import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionAAgent(BaseAgent):
    """
    Condition A: Source Only Baseline.
    Evaluates the bug using issue description and source files without any static analysis facts.
    """

    SYSTEM_PROMPT = """You are an expert Java program analysis and defect localization system.
You are tasked with identifying the exact root-cause files, classes, methods, and line ranges for the bug described below.

You MUST rely strictly on the provided problem statement and source code.
Do not hallucinate files or classes not present in the project.

Your final response MUST conclude with a JSON block in the following exact format:
```json
{
  "localized_files": ["path/to/FaultyFile.java"],
  "localized_classes": ["fully.qualified.ClassName"],
  "localized_methods": ["fully.qualified.ClassName.methodName"],
  "localized_lines": {
    "path/to/FaultyFile.java": [123, 124]
  },
  "root_cause_explanation": "Detailed explanation of the technical failure mechanism"
}
```
"""

    def __init__(self, model: str = "gpt-oss-120b", gateway: Optional[LLMGateway] = None):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}

### Problem Statement:
{task.problem_statement}

### Task Instructions:
Analyze the Java source code for the reported issue above.
Determine the exact root-cause bug locations across the repository.
Remember that bugs in object-oriented Java may span multiple files and classes.
Produce your localization diagnosis in the required JSON format.
"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        resp = self.gateway.chat_completion(messages=messages, model=self.model)
        duration = time.time() - start_time

        parsed_json = self.extract_json_diagnosis(resp.content or "")

        return LocalizationResult(
            task_id=task.instance_id,
            condition="A",
            model=self.model,
            predicted_files=parsed_json.get("localized_files", []),
            predicted_classes=parsed_json.get("localized_classes", []),
            predicted_methods=parsed_json.get("localized_methods", []),
            predicted_lines=parsed_json.get("localized_lines", {}),
            root_cause_explanation=parsed_json.get("root_cause_explanation", ""),
            raw_output=resp.content or "",
            tool_calls_count=0,
            tool_calls_trace=[],
            token_usage=resp.usage,
            latency_seconds=duration
        )
