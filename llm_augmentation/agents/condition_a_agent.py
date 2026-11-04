import json
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from llm_augmentation.tools.source_tools import SOURCE_TOOLS, SourceToolsExecutor
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionAAgent(BaseAgent):
    """
    Condition A: Source Only Baseline (ReAct with Source Inspection Tools).
    Evaluates the bug using issue description and source navigation tools
    (search_source_code, read_source_file) without any static analysis facts.
    """

    SYSTEM_PROMPT = """You are an expert Java program analysis and defect localization system.
You are tasked with identifying the exact root-cause files, classes, methods, and line ranges for the bug described below.

You have access to repository source code inspection tools:
- search_source_code: Searches the codebase for keywords, classes, method names, or regex patterns.
- read_source_file: Reads line ranges from Java source files in the repository.

You MUST rely strictly on the provided problem statement and repository source code.
Do not guess or hallucinate files or classes not present in the project. Always inspect the relevant code first.

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
        max_iterations: int = 5
    ):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)
        self.max_iterations = max_iterations

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()
        tool_traces: List[Dict[str, Any]] = []
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}

### Problem Statement:
{task.problem_statement}

### Task Instructions:
Analyze the Java source code for the reported issue above.
Use the source code inspection tools (search_source_code, read_source_file) to explore and inspect the relevant classes and methods.
Determine the exact root-cause bug locations across the repository.
Remember that bugs in object-oriented Java may span multiple files and classes.
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
            print(f"  -> [Condition A] Turn {iteration}/{self.max_iterations}: Consulting model...", flush=True)

            resp = self.gateway.chat_completion(
                messages=messages,
                tools=SOURCE_TOOLS,
                model=self.model
            )

            for k, v in resp.usage.items():
                total_tokens[k] = total_tokens.get(k, 0) + v

            if resp.tool_calls:
                tool_names = [tc.name for tc in resp.tool_calls]
                print(f"  -> [Condition A] Model requested {len(resp.tool_calls)} tool call(s): {tool_names}", flush=True)

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
                    print(f"  -> [Condition A] Executing source tool '{tc.name}' with args {tc.arguments}...", flush=True)
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
                print(f"  -> [Condition A] Model produced final diagnosis.", flush=True)
                break

        if not final_content:
            print(f"  -> [Condition A] Synthesizing final diagnosis JSON...", flush=True)
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
            condition="A",
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
