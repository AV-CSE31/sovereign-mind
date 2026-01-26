import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Attempting to import app.core.schemas...")
    from app.core import schemas
    print("Schemas imported successfully.")
    
    print("Attempting to import app.core.agent_graph...")
    from app.core import agent_graph
    
    print("Attempting to build agent graph...")
    graph = agent_graph.build_agent_graph()
    print("Agent graph built successfully.")
    
    print("VERIFICATION PASSED")
    
except Exception as e:
    print(f"VERIFICATION FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
