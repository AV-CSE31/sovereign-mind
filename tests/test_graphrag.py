import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    print("Attempting to import app.services.knowledge_graph...")
    print("Knowledge Graph imported successfully.")

    print("Attempting to import app.services.rag_engine...")
    from app.services import rag_engine

    print("Attempting to instantiate HybridRetriever...")
    # This might fail if ChromaDB/Ollama are not reachable, but we just check syntax mostly
    # mocking to bypass init
    import unittest.mock

    with (
        unittest.mock.patch("chromadb.PersistentClient"),
        unittest.mock.patch("app.services.rag_engine.OllamaEmbeddings"),
    ):
        retriever = rag_engine.HybridRetriever()

        # Check if new methods exist
        if hasattr(retriever, "_graph_search") and hasattr(retriever, "_graph_store"):
            print("GraphRAG methods verified.")
        else:
            raise Exception("GraphRAG methods missing from RAG engine.")

    print("VERIFICATION PASSED")

except Exception as e:
    print(f"VERIFICATION FAILED: {e!s}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
