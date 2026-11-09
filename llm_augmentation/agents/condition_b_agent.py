import json
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from llm_augmentation.benchmark.task import Task
from llm_augmentation.benchmark.repo_manager import RepoContext
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

You have access to repository source code inspection and navigation tools:
- find_files: Finds files matching a glob pattern (e.g. '*TypeAdapter*.java', '*Gson*.java').
- list_directory: Lists directory layout and packages (e.g. 'gson/src/main/java' or empty for repository root).
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
Use the repository navigation and inspection tools (find_files, list_directory, search_source_code, read_source_file) to inspect the relevant classes, methods, and line ranges.
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
        Loads precomputed Ahead-of-Time (AOT) static analysis facts for Condition B.
        Checks for cached static facts in datasets/precomputed_facts/{task_id}.txt.
        If not yet generated, extracts them via direct standalone Java SootUpAnalyzer CLI
        (pure bytecode analysis, zero MCP / zero JSON-RPC) and caches them on disk.
        """
        precomputed_file = Path("datasets/precomputed_facts") / f"{task.instance_id}.txt"
        if precomputed_file.exists():
            try:
                return precomputed_file.read_text(encoding="utf-8")
            except Exception:
                pass

        if not repo_context.target_classes_dirs:
            return "[No compiled bytecode target/classes available for static fact extraction.]"

        facts = self._run_offline_sootup_extractor(task, repo_context)
        if facts:
            try:
                precomputed_file.parent.mkdir(parents=True, exist_ok=True)
                precomputed_file.write_text(facts, encoding="utf-8")
            except Exception:
                pass

        return facts if facts else "[No matching static facts extracted for identified types.]"

    def _run_offline_sootup_extractor(self, task: Task, repo_context: RepoContext) -> str:
        """
        Invokes the standalone Java SootUpAnalyzer CLI directly to extract static facts.
        Completely decoupled from the Model Context Protocol (zero MCP / zero JSON-RPC).
        """
        engine_dir = self.sootup_engine_dir.resolve()
        classes_dir = engine_dir / "target" / "classes"
        cp_file = engine_dir / "classpath.txt"

        if not cp_file.exists():
            return "[Offline SootUp extractor unavailable: classpath.txt not generated.]"

        try:
            with open(cp_file, "r", encoding="utf-8") as f:
                deps_cp = f.read().strip()
            full_cp = f"{classes_dir}:{deps_cp}"
            target_dir = repo_context.target_classes_arg

            classes_to_query = self._identify_target_classes(task, repo_context)
            facts = []

            for cls in classes_to_query:
                # 1. Hierarchy (Direct Java CLI invocation)
                cmd_h = ["java", "-cp", full_cp, "org.sootup.analyzer.SootUpAnalyzer", target_dir, "hierarchy", cls]
                res_h = subprocess.run(cmd_h, capture_output=True, text=True, cwd=engine_dir, timeout=60)
                clean_h = "\n".join([line for line in res_h.stdout.splitlines() if not line.startswith("SLF4J")]).strip()
                if "Subclasses:" in clean_h or "Hierarchy Analysis" in clean_h:
                    facts.append(clean_h)

                # 2. Allocations (Direct Java CLI invocation)
                cmd_a = ["java", "-cp", full_cp, "org.sootup.analyzer.SootUpAnalyzer", target_dir, "find-allocations", cls]
                res_a = subprocess.run(cmd_a, capture_output=True, text=True, cwd=engine_dir, timeout=60)
                clean_a = "\n".join([line for line in res_a.stdout.splitlines() if not line.startswith("SLF4J")]).strip()
                if "Match Found:" in clean_a or "Allocations" in clean_a:
                    facts.append(clean_a)

            return "\n\n".join(facts)
        except Exception as e:
            return f"[Error extracting static facts via offline SootUp: {e}]"

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
