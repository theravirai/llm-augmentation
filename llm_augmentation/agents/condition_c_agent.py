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

    SYSTEM_PROMPT = """You are an autonomous Java program analysis agent equipped with repository navigation tools and the SootUp static analysis tool suite.
Your goal is to pinpoint the exact root-cause bug locations across the Java repository for the issue described below.

You have access to two complementary tool suites:

1. Repository Source Navigation Tools:
- find_files: Finds files matching a glob pattern (e.g. '*TypeAdapter*.java', '*Gson*.java').
- list_directory: Lists directory layout and packages (e.g. 'gson/src/main/java' or empty for repository root).
- search_source_code: Searches the codebase for keywords, classes, method names, or regex patterns.
- read_source_file: Reads exact line ranges from Java source files.

2. SootUp Static Analysis Tools (Bytecode Analysis):
- sootup_hierarchy: Discovers superclasses, direct/indirect subclasses, and anonymous inner classes (e.g. TypeAdapter implementations like Gson$1, Gson$2, or JsonReader subclasses like JsonTreeReader) grouped by declaring containers/files.
- sootup_inspect_method: Disassembles method bodies into Jimple IR with line numbers.
- sootup_find_allocations: Scans Jimple bodies for JNewExpr to pinpoint factory creation and instantiation sites across the repository (e.g. where TypeAdapter or anonymous classes like Gson$1, Gson$2 are instantiated).
- sootup_find_invocations: Traces cross-module call sites for a method across classes.
- sootup_callgraph: Builds interprocedural call graphs using CHA, RTA, or SPARK.

Systematic Multi-File Investigation Protocol:
1. Initial Discovery: Use search_source_code or find_files to locate candidate classes or methods matching the failure symptoms.
2. Cross-File Exploration via Static Analysis: Real-world Java bugs frequently span multiple non-local files across inheritance trees, polymorphic wrappers, and factories. Whenever you locate candidate faulty logic, methods, or classes:
   - Run sootup_hierarchy on the enclosing or base class (e.g. TypeAdapter, JsonReader) to discover all companion subclasses across all declaring files.
   - CRITICAL CROSS-FILE CHECK: Check subclasses declared across ALL files (for instance, if subclasses are declared in TypeAdapters.java AND in Gson.java, you MUST inspect both files!). Do NOT stop after finding defects in just one file.
   - Run sootup_find_allocations on the base class or adapter classes (e.g. TypeAdapter) to find all factory methods creating custom or anonymous adapters across the project (e.g. doubleAdapter, floatAdapter).
   - Use search_source_code or sootup_find_invocations to find matching buggy call patterns (e.g. calls to out.value(value) without numeric conversion) across the codebase.
   - Use sootup_inspect_method to verify bytecode logic and source line mappings.
3. Source Inspection: Use read_source_file to confirm the exact line numbers and logic in each identified file.
4. Conclude with your structured diagnosis JSON block containing ALL localized files:

```json
{
  "localized_files": ["path/to/FaultyFile1.java", "path/to/FaultyFile2.java"],
  "localized_classes": ["fully.qualified.ClassName1", "fully.qualified.ClassName2"],
  "localized_methods": ["fully.qualified.ClassName1.methodName1", "fully.qualified.ClassName2.methodName2"],
  "localized_lines": {
    "path/to/FaultyFile1.java": [123, 124],
    "path/to/FaultyFile2.java": [200, 205]
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
        self.tools = SOOTUP_TOOLS + SOURCE_TOOLS

    def run(self, task: Task, repo_context: RepoContext) -> LocalizationResult:
        start_time = time.time()
        self._reflection_asked = False
        target_dir = repo_context.target_classes_arg
        tool_traces: List[Dict[str, Any]] = []
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        user_content = f"""### Target Repository: {task.repo}
### Base Commit: {task.base_commit}
### Compiled Bytecode Directory: {target_dir or 'None'}

### Problem Statement:
{task.problem_statement}

### Task Instructions:
To localize the defect across the codebase, you MUST follow the Systematic Multi-File Investigation Protocol using SootUp MCP static analysis tools:
1. Locate initial candidate classes/methods using search or file tools.
2. When you find candidate classes/methods, invoke SootUp static analysis to discover cross-file dependencies:
   - sootup_hierarchy: Explore class hierarchy, superclasses, and all direct/indirect subclasses. Be sure to check subclasses in ALL declaring files (e.g., both TypeAdapters and Gson).
   - sootup_find_allocations: Find where candidate classes or adapters are instantiated across factory methods and classes.
   - sootup_inspect_method: Disassemble method bodies into Jimple IR with line numbers.
   - sootup_find_invocations / sootup_callgraph: Trace caller chains across classes.
3. Verify whether parallel implementations or factory-instantiated adapters in other files (such as Gson.java or TypeAdapters.java) share the same bug. All affected files MUST be included in localized_files.
4. Use read_source_file to confirm exact code lines across all affected files.
5. Output your diagnosis in the required JSON format.
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

                        if tool_name in SourceToolsExecutor.TOOL_NAMES:
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
                                "MANDATORY: To accurately find defect locations across this codebase, you MUST follow the Systematic Multi-File Investigation Protocol using SootUp MCP static analysis tools:\n"
                                "1. sootup_hierarchy: Explore class hierarchy (superclasses, subclasses, anonymous inner classes) to check whether companion subclasses in other files override or implement this behavior.\n"
                                "2. sootup_find_allocations: Find where candidate objects, type adapters, or anonymous classes are instantiated across factory classes in other files.\n"
                                "3. sootup_find_invocations: Find caller sites for a method across classes.\n"
                                "4. sootup_inspect_method: Disassemble method bodies into Jimple IR with line numbers.\n"
                                "5. sootup_callgraph: Construct interprocedural call graphs.\n"
                                "Please invoke the appropriate SootUp tool now based on your investigation."
                            )
                        })
                        continue
                    else:
                        parsed_diagnosis = self.extract_json_diagnosis(resp.content or "")
                        single_file = len(parsed_diagnosis.get("localized_files", [])) <= 1
                        if single_file and not self._reflection_asked and iteration < self.max_iterations - 2:
                            self._reflection_asked = True
                            print(f"  -> [Condition C] Single-file diagnosis detected. Prompting cross-file verification...", flush=True)
                            messages.append({"role": "assistant", "content": resp.content or ""})
                            messages.append({
                                "role": "user",
                                "content": (
                                    "CROSS-FILE VERIFICATION STEP: You have currently identified 1 file. "
                                    "In Java repositories, defects frequently span multiple non-local files across inheritance trees, companion adapters, and factory classes (for example, companion adapters or subclasses declared in Gson.java or other classes). "
                                    "Did you verify whether subclasses, factory methods, or parallel adapters in companion files (e.g. Gson.java doubleAdapter/floatAdapter if dealing with numeric adapters, or companion classes revealed in sootup_hierarchy) also exhibit or share this bug? "
                                    "If other files also contain affected methods, please inspect them and include them in localized_files. If you have verified that NO other files in the repository are affected, you may output your final diagnosis."
                                )
                            })
                            continue

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
            system_prompt=self.SYSTEM_PROMPT,
            initial_user_prompt=user_content,
            tool_calls_count=len(tool_traces),
            tool_calls_trace=tool_traces,
            token_usage=total_tokens,
            latency_seconds=duration
        )
