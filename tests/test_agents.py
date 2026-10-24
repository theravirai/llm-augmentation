import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llm_augmentation.benchmark import TaskLoader, RepoManager
from llm_augmentation.agents import (
    BaseAgent,
    LocalizationResult,
    LLMResponse,
    ToolCall,
    ConditionAAgent,
    ConditionBAgent,
    ConditionCAgent
)

def test_json_extraction():
    sample_text = """Here is my reasoning:
The bug is caused by TypeAdapters.

```json
{
  "localized_files": ["com/google/gson/Gson.java", "com/google/gson/TypeAdapters.java"],
  "localized_classes": ["com.google.gson.Gson"],
  "localized_methods": ["com.google.gson.Gson.doubleAdapter"],
  "localized_lines": {
    "com/google/gson/Gson.java": [398, 400]
  },
  "root_cause_explanation": "Numeric conversion omitted"
}
```
Done.
"""
    parsed = BaseAgent.extract_json_diagnosis(sample_text)
    assert len(parsed["localized_files"]) == 2
    assert "com.google.gson.Gson" in parsed["localized_classes"]
    assert "com.google.gson.Gson.doubleAdapter" in parsed["localized_methods"]
    assert parsed["localized_lines"]["com/google/gson/Gson.java"] == [398, 400]
    print("test_json_extraction passed!")

def test_condition_a_mock():
    loader = TaskLoader()
    task = loader.get_task("google__gson-2158")
    repo_manager = RepoManager()
    repo_context = repo_manager.prepare_repo_for_task(task, compile_if_needed=False)

    mock_gateway = MagicMock()
    mock_gateway.chat_completion.return_value = LLMResponse(
        content="""```json
{
  "localized_files": ["com/google/gson/internal/bind/TypeAdapters.java"],
  "localized_classes": ["com.google.gson.internal.bind.TypeAdapters"],
  "localized_methods": ["TypeAdapters.write"],
  "localized_lines": {"TypeAdapters.java": [195]},
  "root_cause_explanation": "Primitive adapter misses cast"
}
```""",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )

    agent = ConditionAAgent(model="gpt-oss-120b", gateway=mock_gateway)
    res = agent.run(task, repo_context)

    assert res.condition == "A"
    assert res.task_id == "google__gson-2158"
    assert "com/google/gson/internal/bind/TypeAdapters.java" in res.predicted_files
    print("test_condition_a_mock passed!")

def test_condition_c_tool_loop_mock():
    loader = TaskLoader()
    task = loader.get_task("google__gson-2158")
    repo_manager = RepoManager()
    repo_context = repo_manager.prepare_repo_for_task(task, compile_if_needed=False)

    # Mock gateway: Turn 1 requests tool call, Turn 2 gives final JSON
    mock_gateway = MagicMock()
    mock_gateway.chat_completion.side_effect = [
        LLMResponse(
            content="I will check the hierarchy of TypeAdapter.",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="sootup_hierarchy",
                    arguments={"target_class": "com.google.gson.TypeAdapter"}
                )
            ],
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}
        ),
        LLMResponse(
            content="""Based on the hierarchy showing Gson$1 and Gson$2, I have localized the bug.
```json
{
  "localized_files": ["com/google/gson/Gson.java", "com/google/gson/TypeAdapters.java"],
  "localized_classes": ["com.google.gson.Gson", "com.google.gson.internal.bind.TypeAdapters"],
  "localized_methods": ["com.google.gson.Gson.doubleAdapter"],
  "localized_lines": {"com/google/gson/Gson.java": [398]},
  "root_cause_explanation": "Overriding adapters in Gson.java miss narrowing conversion"
}
```""",
            usage={"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180}
        )
    ]

    agent = ConditionCAgent(model="gpt-oss-120b", gateway=mock_gateway)
    res = agent.run(task, repo_context)

    assert res.condition == "C"
    assert res.tool_calls_count == 1
    assert res.tool_calls_trace[0]["tool"] == "sootup_hierarchy"
    assert "com/google/gson/Gson.java" in res.predicted_files
    assert "com/google/gson/TypeAdapters.java" in res.predicted_files
    print("test_condition_c_tool_loop_mock passed!")

if __name__ == "__main__":
    test_json_extraction()
    test_condition_a_mock()
    test_condition_c_tool_loop_mock()
    print("\nAll Agent tests passed successfully!")
