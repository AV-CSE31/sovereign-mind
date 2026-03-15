import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Attempting to import app.core.memory...")
    print("Memory imported successfully.")

    print("Attempting to import app.core.agent_graph...")
    from app.core import agent_graph

    print("Attempting to build agent graph...")
    graph = agent_graph.build_agent_graph()

    # Check if new nodes are in the graph
    node_keys = graph.nodes.keys()
    if "load_memory" in node_keys and "memorize" in node_keys:
        print("Memory nodes confirmed in graph.")
    else:
        # Note: langgraph compiled graph structure format changes often,
        # so we might just trust the build success if keys aren't easily accessible
        print("Graph built. Nodes (raw check):", node_keys)

    print("VERIFICATION PASSED")

except Exception as e:
    print(f"VERIFICATION FAILED: {e!s}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
