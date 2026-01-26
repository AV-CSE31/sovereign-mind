import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Attempting to import app.core.tracing...")
    from app.core import tracing
    print("Tracing imported successfully.")
    
    print("Attempting to import app.core.agent_graph...")
    from app.core import agent_graph
    
    print("Checking if nodes are decorated...")
    # asyncio.iscoroutinefunction is true for decorated async functions
    if not asyncio.iscoroutinefunction(agent_graph.supervisor_node):
        raise Exception("supervisor_node is not an async function (maybe decoration failed?)")
        
    print("VERIFICATION PASSED")
    
except Exception as e:
    print(f"VERIFICATION FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
