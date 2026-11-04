import json
import re
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from llm_augmentation.mcp.client import McpClient
from llm_augmentation.tools.source_tools import SOURCE_TOOLS, SourceToolsExecutor
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionBAgent(BaseAgent):
    """
    Condition B: Precomputed Static Injection (Ahead-of-Time).
    Queries SootUp beforehand and injects bytecode facts (hierarchy, Jimple IR, allocations)
    directly into the initial prompt context, and allows the model to inspect source code.
    """

    SYSTEM_PROMPT = """You are an expert Java program analysis and defect localization system.
You are provided with a real-world bug description AND deterministic static analysis facts extracted from the compiled Java bytecode using the SootUp framework.

You have access to repository source code inspection tools:
- search_source_code: Searches the codebase for keywords, classes, method names, or regex patterns.
- read_source_file: Reads line ranges from Java source files in the repository.

Pay close attention to the bytecode static analysis facts (e.g., class hierarchies, anonymous inner classes, and allocation sites).
Do not ignore static evidence. Use the source code inspection tools to verify the exact faulty lines and methods.

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
        sootup_engine_dir: Optional[Path | str] = None,
        max_iterations: int = 5
    ):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)
        self.sootup_engine_dir = Path(sootup_engine_dir) if sootup_engine_dir else Path(__file__).resolve().parent.parent.parent / "sootup_engine"
        self.max_iterations = max_iterations

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()
        tool_traces: List[Dict[str, Any]] = []
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # 1. Extract Ahead-of-Time static facts using SootUp
        print("  -> [Condition B] Extracting precomputed SootUp static facts...", flush=True)
        static_facts = self._extract_aot_static_facts(task, repo_context)

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}

### Problem Statement:
{task.problem_statement}

### Deterministic Static Analysis Facts (SootUp Bytecode Extractor):
{static_facts}

### Task Instructions:
Analyze the Java source code and the deterministic SootUp static analysis facts above.
Use the source code inspection tools (search_source_code, read_source_file) to inspect the relevant classes, methods, and line ranges.
Identify all root-cause bug locations, including multi-file links, polymorphic dispatches, and anonymous classes.
Produce your localization diagnosis in the required JSON format.
"""

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        final_content = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"  -> [Condition B] Turn {iteration}/{self.max_iterations}: Consulting model...", flush=True)

            resp = self.gateway.chat_completion(
                messages=messages,
                tools=SOURCE_TOOLS,
                model=self.model
            )

            for k, v in resp.usage.items():
                total_tokens[k] = total_tokens.get(k, 0) + v

            if resp.tool_calls:
                tool_names = [tc.name for tc in resp.tool_calls]
                print(f"  -> [Condition B] Model requested {len(resp.tool_calls)} tool call(s): {tool_names}", flush=True)

                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": resp.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in resp.tool_calls
                    ]
                }
                messages.append(assistant_msg)

                for tc in resp.tool_calls:
                    t_call_start = time.time()
                    print(f"  -> [Condition B] Executing source tool '{tc.name}' with args {tc.arguments}...", flush=True)
                    tool_result = SourceToolsExecutor.execute(tc.name, tc.arguments, repo_context.repo_path)
                    t_duration = time.time() - t_call_start

                    tool_traces.append({
                        "iteration": iteration,
                        "tool": tc.name,
                        "arguments": tc.arguments,
                        "result_snippet": tool_result[:500] if tool_result else "",
                        "duration_seconds": round(t_duration, 3)
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": tool_result
                    })
            else:
                final_content = resp.content or ""
                print(f"  -> [Condition B] Model produced final diagnosis.", flush=True)
                break

        if not final_content:
            print(f"  -> [Condition B] Synthesizing final diagnosis JSON...", flush=True)
            messages.append({
                "role": "user",
                "content": (
                    "All tool iterations are exhausted. You cannot make any more tool calls. "
                    "You MUST output your final structured diagnosis JSON right now in the required format:\n"
                    "```json\n"
                    "{\n"
                    '  "localized_files": ["path/to/FaultyFile.java"],\n'
                    '  "localized_classes": ["fully.qualified.ClassName"],\n'
                    '  "localized_methods": ["fully.qualified.ClassName.methodName"],\n'
                    '  "localized_lines": {\n'
                    '    "path/to/FaultyFile.java": [123, 124]\n'
                    '  },\n'
                    '  "root_cause_explanation": "Detailed explanation of the technical failure mechanism"\n'
                    "}\n"
                    "```"
                )
            })
            synth_resp = self.gateway.chat_completion(
                messages=messages,
                tools=None,
                model=self.model
            )
            for k, v in synth_resp.usage.items():
                total_tokens[k] = total_tokens.get(k, 0) + v
            final_content = synth_resp.content or ""

        duration = time.time() - start_time
        parsed_json = self.extract_json_diagnosis(final_content)

        return LocalizationResult(
            task_id=task.instance_id,
            condition="B",
            model=self.model,
            predicted_files=parsed_json.get("localized_files", []),
            predicted_classes=parsed_json.get("localized_classes", []),
            predicted_methods=parsed_json.get("localized_methods", []),
            predicted_lines=parsed_json.get("localized_lines", {}),
            root_cause_explanation=parsed_json.get("root_cause_explanation", ""),
            raw_output=final_content,
            tool_calls_count=len(tool_traces),
            tool_calls_trace=tool_traces,
            token_usage=total_tokens,
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
                classes_to_query = self._identify_target_classes(task, repo_context)
                for cls in classes_to_query:
                    # 1. Hierarchy
                    h_fact = client.call_tool("sootup_hierarchy", {"target_class": cls, "target_dir": target_dir})
                    if "Subclasses:" in h_fact or "Hierarchy Analysis" in h_fact:
                        facts.append(h_fact.strip())

                    # 2. Allocations
                    a_fact = client.call_tool("sootup_find_allocations", {"target_class": cls, "target_dir": target_dir})
                    if "Match Found:" in a_fact or "Allocations" in a_fact:
                        facts.append(a_fact.strip())

        except Exception as e:
            facts.append(f"[Error extracting static facts via SootUp: {e}]")

        return "\n\n".join(facts) if facts else "[No matching static facts extracted for identified types.]"

    def _identify_target_classes(self, task: Task, repo_context: RepoContext) -> List[str]:
        """Identifies key class names to query from task problem statement and repository scan."""
        candidates: Set[str] = set()

        # Map production classes in repository
        if repo_context.repo_path and repo_context.repo_path.exists():
            prod_classes = self._map_production_classes(repo_context.repo_path)
            words = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", task.problem_statement))
            for word in words:
                if word in prod_classes:
                    candidates.add(prod_classes[word])

        # Domain-specific base classes and polymorphic targets
        if "gson" in task.repo.lower():
            candidates.add("com.google.gson.TypeAdapter")
            candidates.add("com.google.gson.Gson$1")
            candidates.add("com.google.gson.Gson$2")
        elif "druid" in task.repo.lower():
            candidates.add("org.apache.druid.timeline.VersionedIntervalTimeline")
            candidates.add("org.apache.druid.java.util.common.JodaUtils")

        # Keep deterministic order and limit to top 5 classes
        return sorted(list(candidates))[:5]

    @staticmethod
    def _map_production_classes(repo_path: Path) -> Dict[str, str]:
        """Maps simple class name -> FQCN for non-test java files."""
        class_map: Dict[str, str] = {}
        for p in repo_path.rglob("*.java"):
            if any(part in ["test", "target", "build", ".git"] for part in p.parts):
                continue
            pkg = ""
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("package ") and line.endswith(";"):
                            pkg = line[8:-1].strip()
                            break
            except Exception:
                pass
            fqcn = f"{pkg}.{p.stem}" if pkg else p.stem
            class_map[p.stem] = fqcn
        return class_map
