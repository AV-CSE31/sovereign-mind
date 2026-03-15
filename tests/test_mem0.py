import os
import sys
import unittest.mock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Attempting to import app.core.memory...")
    # Mocking mem0 to avoid actual DB initialization/download during quick test
    with unittest.mock.patch("mem0.Memory"):
        from app.core import memory

        print("Memory imported successfully.")

        service = memory.get_memory_service()
        if hasattr(service, "add") and hasattr(service, "get_all"):
            print("Mem0 Service interface verified.")
        else:
            raise Exception("Mem0 Service interface invalid.")

    print("Attempting to import app.core.agent_graph...")
    from app.core import agent_graph  # noqa: F401

    print("VERIFICATION PASSED")

except ImportError as e:
    if "mem0" in str(e):
        print("VERIFICATION SKIPPED: mem0ai package not installed in test env.")
    else:
        print(f"VERIFICATION FAILED: {e!s}")
        sys.exit(1)
except Exception as e:
    print(f"VERIFICATION FAILED: {e!s}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
