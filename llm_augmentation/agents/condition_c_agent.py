import json
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
from llm_augmentation.mcp.client import McpClient
from llm_augmentation.mcp.tool_schemas import SOOTUP_TOOLS
from llm_augmentation.tools.source_tools import SOURCE_TOOLS, SourceToolsExecutor
from .base_agent import BaseAgent, LocalizationResult
from .llm_gateway import LLMGateway

class ConditionCAgent(BaseAgent):
    """
    Condition C: Active On-Demand Tool Calling via MCP.
    The LLM operates as an autonomous agent in a ReAct loop, dynamically querying
    both repository source inspection tools and SootUp static analysis tools to
    validate hypotheses and uncover non-local defects.
    """

    SYSTEM_PROMPT = """You are an autonomous Java program analysis agent equipped with the SootUp static analysis tool suite.
Your goal is to pinpoint the exact root-cause bug locations across the Java repository for the issue described below.

When analyzing the bug, you MUST use the SootUp MCP static analysis tools. You are free to choose any of the available SootUp tools based on the issue/task:
- sootup_hierarchy: Discover superclasses, subclasses, and anonymous inner classes (e.g. TypeAdapter implementations like Gson$1).
- sootup_inspect_method: Disassemble method bodies into Jimple IR with line numbers.
- sootup_find_allocations: Find where objects or adapters are instantiated (JNewExpr) to pinpoint factory methods across the repository.
- sootup_find_invocations: Find caller sites for a specific method across classes.
- sootup_callgraph: Construct CHA, RTA, or SPARK interprocedural call graphs.
- read_source_file: Reads line ranges from Java source files in the repository.

Investigate systematically:
1. Examine the problem description and identify key candidate types, classes, or interfaces.
2. In Java object-oriented defect localization, bugs frequently span multiple non-local files across inheritance, polymorphic wrappers, and factories. You MUST invoke the relevant SootUp MCP tools (such as sootup_hierarchy to explore subclasses or sootup_find_allocations to locate instantiation sites) to uncover all affected locations.
3. Use read_source_file to inspect the source lines for the classes discovered by SootUp.
4. Conclude with your structured diagnosis JSON block:

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
        max_iterations: int = 8
    ):
        super().__init__(model=model)
        self.gateway = gateway or LLMGateway(default_model=model)
        self.sootup_engine_dir = Path(sootup_engine_dir) if sootup_engine_dir else Path(__file__).resolve().parent.parent.parent / "sootup_engine"
        self.max_iterations = max_iterations
        read_tool = [t for t in SOURCE_TOOLS if t["name"] == "read_source_file"]
        self.tools = SOOTUP_TOOLS + read_tool

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

### Task Instructions:
To localize the defect across the codebase, you MUST use the SootUp MCP static analysis tools.
You are free to choose whichever of the available SootUp tools best fit the issue/task:
- sootup_hierarchy: To explore class hierarchies, interfaces, and anonymous inner classes.
- sootup_find_allocations: To find where objects, type adapters, or anonymous classes are instantiated across the codebase.
- sootup_find_invocations: To find caller sites for methods across classes.
- sootup_inspect_method: To disassemble method bodies into Jimple IR with line numbers.
- sootup_callgraph: To construct call graphs.
Use read_source_file to read code files once located.
Produce your localization diagnosis in the required JSON format.
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
                print(f"  -> [Condition C] Turn {iteration}/{self.max_iterations}: Consulting model...", flush=True)

                resp = self.gateway.chat_completion(
                    messages=messages,
                    tools=self.tools,
                    model=self.model
                )

                # Track token usage
                for k, v in resp.usage.items():
                    total_tokens[k] = total_tokens.get(k, 0) + v

                # Check if model wants to call tools
                if resp.tool_calls:
                    tool_names = [tc.name for tc in resp.tool_calls]
                    print(f"  -> [Condition C] Model requested {len(resp.tool_calls)} tool call(s): {tool_names}", flush=True)

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

                    # Execute each tool call
                    for tc in resp.tool_calls:
                        t_call_start = time.time()
                        call_args = dict(tc.arguments)
                        tool_name = tc.name.replace("soothup_", "sootup_").strip()

                        if tool_name in ["search_source_code", "read_source_file"]:
                            print(f"  -> [Condition C] Executing source tool '{tool_name}' with args {call_args}...", flush=True)
                            try:
                                tool_result = SourceToolsExecutor.execute(tool_name, call_args, repo_context.repo_path)
                            except Exception as e:
                                tool_result = f"Error executing source tool {tool_name}: {e}"
                        else:
                            if target_dir and "target_dir" not in call_args:
                                call_args["target_dir"] = target_dir
                            print(f"  -> [Condition C] Executing SootUp MCP tool '{tool_name}' with args {call_args}...", flush=True)
                            try:
                                tool_result = mcp_client.call_tool(tool_name, call_args)
                            except Exception as e:
                                tool_result = f"Error executing SootUp tool {tool_name}: {e}"

                        t_duration = time.time() - t_call_start

                        tool_traces.append({
                            "iteration": iteration,
                            "tool": tool_name,
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
                    # Model provided text without tool calls
                    sootup_called = any(t["tool"].startswith("sootup_") for t in tool_traces)
                    if not sootup_called and iteration < self.max_iterations:
                        print(f"  -> [Condition C] Model attempted to conclude without calling SootUp MCP tools. Enforcing SootUp query...", flush=True)
                        messages.append({"role": "assistant", "content": resp.content or ""})
                        messages.append({
                            "role": "user",
                            "content": (
                                "MANDATORY: To accurately find the defect locations across this codebase, you MUST use the SootUp MCP static analysis tools. "
                                "You are free to choose any of the available SootUp tools based on the issue/task:\n"
                                "- sootup_hierarchy: Explore class hierarchy, superclasses, interfaces, and anonymous inner classes.\n"
                                "- sootup_find_allocations: Find where objects, type adapters, or anonymous classes are instantiated across the codebase.\n"
                                "- sootup_find_invocations: Find caller sites for a method across classes.\n"
                                "- sootup_inspect_method: Disassemble method bodies into Jimple IR with line numbers.\n"
                                "- sootup_callgraph: Construct interprocedural call graphs.\n"
                                "Please invoke the appropriate SootUp tool now based on your investigation."
                            )
                        })
                        continue
                    else:
                        final_content = resp.content or ""
                        print(f"  -> [Condition C] Model produced final diagnosis.", flush=True)
                        break

            # If iterations exhausted without final text, prompt for final synthesis
            if not final_content:
                print(f"  -> [Condition C] Synthesizing final diagnosis JSON...", flush=True)
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
