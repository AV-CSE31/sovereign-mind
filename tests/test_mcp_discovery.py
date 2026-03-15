from app.services.mcp_server import mcp


def test_mcp_tool_discovery():
    """Verify that MCP server exposes the expected tools."""
    tools = mcp.list_tools()

    tool_names = [t.name for t in tools]
    print(f"\nDiscovered MCP Tools: {tool_names}")

    assert "query_vault" in tool_names
    assert "search_knowledge_base" in tool_names
    assert "verify_compliance" in tool_names


if __name__ == "__main__":
    test_mcp_tool_discovery()
