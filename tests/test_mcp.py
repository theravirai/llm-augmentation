import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from llm_augmentation.mcp.client import McpClient

def test_mcp_handshake_and_tools():
    engine_dir = PROJECT_ROOT / "sootup_engine"
    target_classes = engine_dir / "target" / "classes"

    with McpClient(sootup_engine_dir=engine_dir, default_target_dir=target_classes) as client:
        # Test 1: list_tools
        tools = client.list_tools()
        assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
        tool_names = {t["name"] for t in tools}
        expected = {
            "sootup_hierarchy",
            "sootup_inspect_method",
            "sootup_find_allocations",
            "sootup_find_invocations",
            "sootup_callgraph"
        }
        assert tool_names == expected, f"Unexpected tools: {tool_names}"

        # Test 2: sootup_hierarchy on SootUpAnalyzer itself
        res = client.call_tool("sootup_hierarchy", {
            "target_class": "org.sootup.analyzer.SootUpAnalyzer"
        })
        assert "=== CLASS HIERARCHY FACT ===" in res
        assert "java.lang.Object" in res

        # Test 3: sootup_inspect_method
        res_m = client.call_tool("sootup_inspect_method", {
            "target_class": "org.sootup.analyzer.SootUpAnalyzer",
            "target_method": "getHierarchy"
        })
        assert "=== METHOD INSPECTION FACT ===" in res_m
        assert "Jimple Body:" in res_m

    print("All MCP unit tests passed successfully!")

if __name__ == "__main__":
    test_mcp_handshake_and_tools()
