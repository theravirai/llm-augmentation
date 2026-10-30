import pytest
from pathlib import Path
from llm_augmentation.tools.source_tools import SOURCE_TOOLS, SourceToolsExecutor
from llm_augmentation.agents import ConditionAAgent, ConditionBAgent, ConditionCAgent

def test_source_tools_schema():
    assert len(SOURCE_TOOLS) == 2
    tool_names = [t["name"] for t in SOURCE_TOOLS]
    assert "search_source_code" in tool_names
    assert "read_source_file" in tool_names

def test_search_source_code_execution():
    repo_path = Path("/Volumes/BrainStorm/Github/SootUp-Store/swebench-java-evaluation/workspace/gson")
    if not repo_path.exists():
        pytest.skip("Gson repository not available on host")

    result = SourceToolsExecutor.execute(
        "search_source_code",
        {"query": "class TypeAdapter", "max_results": 5},
        repo_path
    )
    assert "=== Search Results for 'class TypeAdapter'" in result
    assert "TypeAdapter.java" in result

def test_read_source_file_execution():
    repo_path = Path("/Volumes/BrainStorm/Github/SootUp-Store/swebench-java-evaluation/workspace/gson")
    if not repo_path.exists():
        pytest.skip("Gson repository not available on host")

    result = SourceToolsExecutor.execute(
        "read_source_file",
        {"file_path": "TypeAdapter.java", "start_line": 1, "end_line": 20},
        repo_path
    )
    assert "=== File: " in result
    assert "TypeAdapter.java" in result
    assert "   1 | " in result

def test_agent_tool_configurations():
    agent_a = ConditionAAgent()
    assert agent_a.max_iterations == 5

    agent_b = ConditionBAgent()
    assert agent_b.max_iterations == 5

    agent_c = ConditionCAgent()
    assert agent_c.max_iterations == 8
    # Condition C has 5 SootUp MCP tools + read_source_file
    assert len(agent_c.tools) == 6
