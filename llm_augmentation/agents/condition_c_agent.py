import json
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from llm_augmentation.mcp.client import McpClient
from llm_augmentation.mcp.tool_schemas import SOOTUP_TOOLS
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionCAgent(BaseAgent):
    """
    Condition C: Active On-Demand Tool Calling via MCP.
    The LLM operates as an autonomous agent in a ReAct loop, dynamically querying
    SootUp static analysis tools to validate hypotheses and uncover non-local defects.
    """

    SYSTEM_PROMPT = """You are an autonomous Java program analysis agent equipped with the SootUp static analysis tool suite.
Your goal is to pinpoint the exact root-cause bug locations across the Java repository for the issue described below.

You have access to live bytecode static analysis tools via the Model Context Protocol:
- sootup_hierarchy: Discover superclasses, subclasses, and anonymous inner classes (e.g. Gson$1).
- sootup_inspect_method: Disassemble method bodies into Jimple IR with line numbers.
- sootup_find_allocations: Find where objects of a class are instantiated (JNewExpr) to pinpoint factory methods.
- sootup_find_invocations: Find caller sites for a specific method across classes.
- sootup_callgraph: Construct CHA, RTA, or SPARK interprocedural call graphs.

Investigate systematically:
1. Examine the problem description and form an initial hypothesis.
2. Call SootUp tools on the compiled bytecode to resolve polymorphic dispatch, trace callers, and find hidden anonymous classes.
3. Once you have verified the root cause, conclude with the final JSON diagnosis block:

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
        max_iterations: int = 10
    ):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)
        self.sootup_engine_dir = Path(sootup_engine_dir) if sootup_engine_dir else Path(__file__).resolve().parent.parent.parent / "sootup_engine"
        self.max_iterations = max_iterations

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()
        target_dir = repo_context.target_classes_arg
        tool_traces: List[Dict[str, Any]] = []
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}
### Compiled Bytecode Directory: {target_dir or 'None'}

### Problem Statement:
{task.problem_statement}

### Instructions:
Begin your investigation. If you need static bytecode facts (such as subclasses of an interface, method bodies, allocation sites, or caller locations), invoke the relevant SootUp tool.
When ready, produce your final structured diagnosis JSON.
"""

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        final_content = ""

        # Open live MCP client connection to Java engine
        with McpClient(sootup_engine_dir=self.sootup_engine_dir, default_target_dir=target_dir) as mcp_client:
            iteration = 0
            while iteration < self.max_iterations:
                iteration += 1

                resp = self.gateway.chat_completion(
                    messages=messages,
                    tools=SOOTUP_TOOLS,
                    model=self.model
                )

                # Track token usage
                for k, v in resp.usage.items():
                    total_tokens[k] = total_tokens.get(k, 0) + v

                # Check if model wants to call tools
                if resp.tool_calls:
                    # Append assistant's tool-call message
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

                    # Execute each tool call against SootUp MCP Server
                    for tc in resp.tool_calls:
                        t_call_start = time.time()
                        call_args = dict(tc.arguments)
                        if "target_dir" not in call_args and target_dir:
                            call_args["target_dir"] = target_dir

                        try:
                            tool_result = mcp_client.call_tool(tc.name, call_args)
                        except Exception as e:
                            tool_result = f"Error executing tool {tc.name}: {e}"

                        t_duration = time.time() - t_call_start

                        tool_traces.append({
                            "iteration": iteration,
                            "tool": tc.name,
                            "arguments": call_args,
                            "result_snippet": tool_result[:500] if tool_result else "",
                            "duration_seconds": round(t_duration, 3)
                        })

                        # Append tool response
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": tool_result
                        })
                else:
                    # Model provided final text
                    final_content = resp.content or ""
                    break

        duration = time.time() - start_time
        parsed_json = self.extract_json_diagnosis(final_content)

        return LocalizationResult(
            task_id=task.instance_id,
            condition="C",
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
