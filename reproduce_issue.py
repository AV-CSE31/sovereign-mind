
import asyncio
from app.services.rag_engine import get_retriever, HybridRetriever
from app.core.config import get_settings

async def reproduce_ingestion():
    print("Reproducing ingestion issue...")
    
    settings = get_settings()
    print(f"Settings: Collection Name: {settings.chroma_collection_name}")
    print(f"Settings: Embedding Model: {settings.embedding_model}")
    print(f"Settings: Ollama Local URL: {settings.ollama_base_url}")

    # Ensure engine is running
    from app.core.inference_engine import get_inference_engine
    engine = get_inference_engine()
    if not engine.is_running():
        print("Starting inference engine...")
        engine.start()
    else:
        print("Inference engine already running.")

    retriever = get_retriever()
    
    try:
        # Test document ingestion
        content = "This is a test document for ingestion reproduction."
        doc_id = "repro_doc_id"
        
        print("\nAttempting to ingest document...")
        chunk_count = await retriever.ingest_document(content=content, doc_id=doc_id)
        
        print(f"\nIngestion successful! Ingested {chunk_count} chunks.")
        
        # Verify retrieval
        print("\nVerifying retrieval...")
        results = await retriever.retrieve("test document")
        print(f"Retrieval results: {results}")

    except Exception as e:
        print(f"\nError encountered: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await retriever.close()

if __name__ == "__main__":
    asyncio.run(reproduce_ingestion())
