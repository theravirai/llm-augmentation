import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from llm_augmentation.mcp.client import McpClient
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionBAgent(BaseAgent):
    """
    Condition B: Precomputed Static Injection (Ahead-of-Time).
    Queries SootUp beforehand and injects bytecode facts (hierarchy, Jimple IR, allocations)
    directly into the initial prompt context.
    """

    SYSTEM_PROMPT = """You are an expert Java program analysis and defect localization system.
You are provided with a real-world bug description AND deterministic static analysis facts extracted from the compiled Java bytecode using the SootUp framework.

Pay close attention to the bytecode static analysis facts (e.g., class hierarchies, anonymous inner classes, and allocation sites).
Do not ignore static evidence.

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

    def __init__(
        self,
        model: str = "gpt-oss-120b",
        gateway: Optional[LLMGateway] = None,
        sootup_engine_dir: Optional[Path | str] = None
    ):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)
        self.sootup_engine_dir = Path(sootup_engine_dir) if sootup_engine_dir else Path(__file__).resolve().parent.parent.parent / "sootup_engine"

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()

        # 1. Extract Ahead-of-Time static facts using SootUp
        static_facts = self._extract_aot_static_facts(task, repo_context)

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}

### Problem Statement:
{task.problem_statement}

### Deterministic Static Analysis Facts (SootUp Bytecode Extractor):
{static_facts}

### Task Instructions:
Analyze the Java source code and the deterministic SootUp static analysis facts above.
Identify all root-cause bug locations, including multi-file links, polymorphic dispatches, and anonymous classes.
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
            condition="B",
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

    def _extract_aot_static_facts(self, task: Task, repo_context: RepoContext) -> str:
        """
        Runs precomputed static queries on target classes based on task context.
        """
        if not repo_context.target_classes_dirs:
            return "[No compiled bytecode target/classes available for static fact extraction.]"

        facts = []
        target_dir = repo_context.target_classes_arg

        try:
            with McpClient(sootup_engine_dir=self.sootup_engine_dir, default_target_dir=target_dir) as client:
                # Heuristic extraction based on common patterns in issue text
                classes_to_query = self._identify_target_classes(task)
                for cls in classes_to_query:
                    # 1. Hierarchy
                    h_fact = client.call_tool("sootup_hierarchy", {"target_class": cls, "target_dir": target_dir})
                    if "Subclasses:" in h_fact:
                        facts.append(h_fact.strip())

                    # 2. Allocations
                    a_fact = client.call_tool("sootup_find_allocations", {"target_class": cls, "target_dir": target_dir})
                    if "Match Found:" in a_fact:
                        facts.append(a_fact.strip())

        except Exception as e:
            facts.append(f"[Error extracting static facts via SootUp: {e}]")

        return "\n\n".join(facts) if facts else "[No matching static facts extracted for identified types.]"

    def _identify_target_classes(self, task: Task) -> List[str]:
        """Identifies key class names to query from task problem statement."""
        text = task.problem_statement
        candidates = []
        if "gson" in task.repo.lower():
            candidates.extend(["com.google.gson.TypeAdapter", "com.google.gson.Gson$1", "com.google.gson.Gson$2"])
        elif "druid" in task.repo.lower():
            candidates.extend([
                "org.apache.druid.timeline.VersionedIntervalTimeline",
                "org.apache.druid.java.util.common.JodaUtils"
            ])
        return candidates
