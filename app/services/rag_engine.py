"""
Module C: SOTA RAG (Memory) - Hybrid Retrieval Engine.

This module implements state-of-the-art Retrieval-Augmented Generation with:
1. Dense Search: ChromaDB for semantic similarity
2. Sparse Search: BM25 for exact keyword matches
3. Ensemble: Reciprocal Rank Fusion (RRF) to combine results
4. Re-ranking: FlashRank (MiniLM-L-6-v2) for final scoring

Security Boundaries:
- Documents are stored in ChromaDB (local persistent storage)
- No document content is sent externally without privacy filtering
- Embeddings are generated locally via Ollama
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
import httpx
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.exceptions import DocumentIngestionError, RerankingError, RetrievalError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Optional FlashRank import
try:
    from flashrank import Ranker, RerankRequest

    FLASHRANK_AVAILABLE = True
except ImportError:
    FLASHRANK_AVAILABLE = False
    logger.warning("flashrank_not_available", message="Reranking will be disabled")


@dataclass
class Document:
    """A document with content and metadata.

    Security Boundary: Document content may contain sensitive information.
    Always filter through privacy guard before sending to cloud LLM.
    """

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class RetrievalResult:
    """Result from hybrid retrieval.

    Contains ranked documents with fusion and reranking scores.
    """

    documents: list[Document]
    query: str
    retrieval_method: str = "hybrid"


class OllamaEmbeddings:
    """Local embeddings using Ollama.

    Security Boundary: Embeddings are generated entirely locally.
    No data leaves the device.
    """

    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Security Boundary: Text is sent only to local inference server.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        client = await self._get_client()
        # Use OpenAI-compatible endpoint provided by Llamafile
        try:
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                json={"input": text, "model": "test"}, # Model name often ignored by llamafile, or use self.model
                headers={"Authorization": "Bearer no-key"}
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            # Fallback for standard Ollama if Llamafile fails?
            # For now, assume Llamafile /v1/embeddings
            logger.error("embedding_failed", error=str(e))
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        # Process in parallel with concurrency limit
        semaphore = asyncio.Semaphore(5)

        async def embed_with_limit(text: str) -> list[float]:
            async with semaphore:
                return await self.embed_text(text)

        embeddings = await asyncio.gather(*[embed_with_limit(text) for text in texts])
        return list(embeddings)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class DocumentChunker:
    """Split documents into chunks for indexing.

    Uses sliding window approach with configurable size and overlap.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, doc_id: str, metadata: dict[str, Any] | None = None) -> list[Document]:
        """Split text into overlapping chunks.

        Args:
            text: Full document text.
            doc_id: Document identifier.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            List of Document chunks.
        """
        if not text.strip():
            return []

        chunks: list[Document] = []
        words = text.split()

        if len(words) <= self.chunk_size:
            # Document is small enough, return as single chunk
            chunk_id = f"{doc_id}_chunk_0"
            return [
                Document(
                    id=chunk_id,
                    content=text,
                    metadata={**(metadata or {}), "doc_id": doc_id, "chunk_index": 0},
                )
            ]

        # Sliding window chunking
        step = self.chunk_size - self.chunk_overlap
        for i, start in enumerate(range(0, len(words), step)):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunk_id = f"{doc_id}_chunk_{i}"
            chunks.append(
                Document(
                    id=chunk_id,
                    content=chunk_text,
                    metadata={**(metadata or {}), "doc_id": doc_id, "chunk_index": i},
                )
            )

            if end >= len(words):
                break

        return chunks


class HybridRetriever:
    """SOTA Hybrid Retrieval with Dense + Sparse search and Reranking.

    Architecture:
    1. Dense Search (ChromaDB): Semantic similarity using embeddings
    2. Sparse Search (BM25): Lexical matching for exact terms
    3. Reciprocal Rank Fusion: Combine results from both methods
    4. Reranking (FlashRank): Cross-encoder reranking for precision

    Security Boundaries:
    - All storage and embedding generation is local
    - Document content is accessible only through this interface
    - No external API calls during retrieval
    """

    def __init__(self) -> None:
        """Initialize the hybrid retriever.

        Security Boundary: All data remains local.
        """
        self._settings = get_settings()

        # Initialize ChromaDB (dense retrieval)
        self._chroma_client = chromadb.PersistentClient(
            path=self._settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,  # Privacy: Disable telemetry
                allow_reset=True,
            ),
        )

        # Get or create collection
        self._collection = self._chroma_client.get_or_create_collection(
            name=self._settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Initialize embeddings (local)
        self._embedder = OllamaEmbeddings(
            model=self._settings.embedding_model,
            base_url=self._settings.ollama_base_url,
        )

        # BM25 index (sparse retrieval) - rebuilt as needed
        self._bm25_corpus: list[list[str]] = []
        self._bm25_doc_ids: list[str] = []
        self._bm25_index: BM25Okapi | None = None

        # Reranker (optional)
        self._reranker: Ranker | None = None
        if FLASHRANK_AVAILABLE:
            try:
                self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="./data/flashrank")
                logger.info("reranker_initialized", model="ms-marco-MiniLM-L-12-v2")
            except Exception as e:
                logger.warning("reranker_init_failed", error=str(e))

        # Document chunker
        self._chunker = DocumentChunker(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )

        logger.info(
            "hybrid_retriever_initialized",
            collection=self._settings.chroma_collection_name,
            reranking_enabled=self._reranker is not None,
        )

    def _generate_doc_id(self, content: str) -> str:
        """Generate a deterministic document ID from content hash."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def ingest_document(
        self,
        content: str,
        doc_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Ingest a document into the hybrid index.

        Security Boundary: Document content is stored locally.

        Args:
            content: Document text content.
            doc_id: Optional document identifier (generated if not provided).
            metadata: Optional metadata to store with the document.

        Returns:
            Number of chunks indexed.

        Raises:
            DocumentIngestionError: If ingestion fails.
        """
        try:
            # Generate ID if not provided
            if doc_id is None:
                doc_id = self._generate_doc_id(content)

            # Chunk the document
            chunks = self._chunker.chunk_text(content, doc_id, metadata)

            if not chunks:
                logger.warning("empty_document", doc_id=doc_id)
                return 0

            # Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self._embedder.embed_batch(chunk_texts)

            # Add to ChromaDB
            self._collection.add(
                ids=[chunk.id for chunk in chunks],
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=[chunk.metadata for chunk in chunks],
            )

            # Update BM25 index
            for chunk in chunks:
                tokenized = chunk.content.lower().split()
                self._bm25_corpus.append(tokenized)
                self._bm25_doc_ids.append(chunk.id)

            # Rebuild BM25 index
            self._bm25_index = BM25Okapi(self._bm25_corpus)

            logger.info(
                "document_ingested",
                doc_id=doc_id,
                chunk_count=len(chunks),
            )

            return len(chunks)

        except Exception as e:
            logger.error("ingestion_failed", doc_id=doc_id, error=str(e))
            raise DocumentIngestionError(str(e), doc_id) from e

    async def ingest_file(
        self,
        file_path: str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Ingest a file (PDF or TXT) into the index.

        Security Boundary: File content is read and stored locally.

        Args:
            file_path: Path to the file.
            metadata: Optional metadata.

        Returns:
            Number of chunks indexed.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise DocumentIngestionError(f"File not found: {file_path}", str(file_path))

        # Read file content
        content = ""
        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            content = file_path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(file_path))
                content = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise DocumentIngestionError("pypdf not installed for PDF support", str(file_path))
        else:
            raise DocumentIngestionError(f"Unsupported file type: {suffix}", str(file_path))

        # Add file metadata
        file_metadata = {
            **(metadata or {}),
            "source_file": str(file_path),
            "file_type": suffix,
        }

        return await self.ingest_document(
            content=content,
            doc_id=file_path.stem,
            metadata=file_metadata,
        )

    async def _dense_search(self, query: str, top_k: int) -> list[Document]:
        """Perform dense (semantic) search using ChromaDB.

        Args:
            query: Search query.
            top_k: Number of results to return.

        Returns:
            List of documents with similarity scores.
        """
        # Generate query embedding
        query_embedding = await self._embedder.embed_text(query)

        # Search ChromaDB
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc_text in enumerate(results["documents"][0]):
                doc_id = results["ids"][0][i] if results["ids"] else f"dense_{i}"
                distance = results["distances"][0][i] if results["distances"] else 0.0
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                # Convert distance to similarity (cosine distance to similarity)
                score = 1.0 - distance

                documents.append(
                    Document(
                        id=doc_id,
                        content=doc_text,
                        metadata=metadata,
                        score=score,
                    )
                )

        return documents

    def _sparse_search(self, query: str, top_k: int) -> list[Document]:
        """Perform sparse (BM25) search for lexical matching.

        Args:
            query: Search query.
            top_k: Number of results to return.

        Returns:
            List of documents with BM25 scores.
        """
        if self._bm25_index is None or not self._bm25_corpus:
            return []

        # Tokenize query
        tokenized_query = query.lower().split()

        # Get BM25 scores
        scores = self._bm25_index.get_scores(tokenized_query)

        # Get top-k results
        scored_indices = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]

        documents = []
        for idx, score in scored_indices:
            if score > 0:
                doc_id = self._bm25_doc_ids[idx]
                content = " ".join(self._bm25_corpus[idx])

                # Fetch metadata from ChromaDB
                try:
                    result = self._collection.get(ids=[doc_id], include=["metadatas"])
                    metadata = result["metadatas"][0] if result["metadatas"] else {}
                except Exception:
                    metadata = {}

                documents.append(
                    Document(
                        id=doc_id,
                        content=content,
                        metadata=metadata,
                        score=score,
                    )
                )

        return documents

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[Document],
        sparse_results: list[Document],
        k: int = 60,
    ) -> list[Document]:
        """Combine dense and sparse results using Reciprocal Rank Fusion.

        RRF Score = Σ 1 / (k + rank_i) for each ranking list

        Args:
            dense_results: Results from dense search.
            sparse_results: Results from sparse search.
            k: RRF constant (default 60).

        Returns:
            Fused and re-scored documents.
        """
        # Calculate RRF scores
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        # Process dense results
        for rank, doc in enumerate(dense_results):
            rrf_scores[doc.id] = rrf_scores.get(doc.id, 0) + 1 / (k + rank + 1)
            doc_map[doc.id] = doc

        # Process sparse results
        for rank, doc in enumerate(sparse_results):
            rrf_scores[doc.id] = rrf_scores.get(doc.id, 0) + 1 / (k + rank + 1)
            if doc.id not in doc_map:
                doc_map[doc.id] = doc

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build result list with RRF scores
        results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            doc.score = rrf_scores[doc_id]
            results.append(doc)

        return results

    def _rerank(self, query: str, documents: list[Document], top_n: int) -> list[Document]:
        """Rerank documents using FlashRank cross-encoder.

        Args:
            query: Search query.
            documents: Documents to rerank.
            top_n: Number of top results to return.

        Returns:
            Reranked documents.
        """
        if self._reranker is None or not documents:
            return documents[:top_n]

        try:
            # Prepare rerank request
            passages = [{"id": str(i), "text": doc.content} for i, doc in enumerate(documents)]

            rerank_request = RerankRequest(query=query, passages=passages)
            reranked = self._reranker.rerank(rerank_request)

            # Map back to documents with new scores
            reranked_docs = []
            for result in reranked[:top_n]:
                idx = int(result["id"])
                doc = documents[idx]
                doc.score = result["score"]
                reranked_docs.append(doc)

            return reranked_docs

        except Exception as e:
            logger.warning("reranking_failed", error=str(e))
            return documents[:top_n]

    async def retrieve(self, query: str) -> RetrievalResult:
        """Perform hybrid retrieval with RRF and reranking.

        Security Boundary: All retrieval is local.

        Args:
            query: Search query.

        Returns:
            RetrievalResult with ranked documents.

        Raises:
            RetrievalError: If retrieval fails.
        """
        try:
            # Step 1: Dense search (semantic)
            dense_results = await self._dense_search(query, self._settings.dense_top_k)

            # Step 2: Sparse search (BM25)
            sparse_results = self._sparse_search(query, self._settings.sparse_top_k)

            # Step 3: Reciprocal Rank Fusion
            fused_results = self._reciprocal_rank_fusion(dense_results, sparse_results)

            # Step 4: Rerank top candidates
            final_results = self._rerank(
                query,
                fused_results[: self._settings.rerank_top_n],
                self._settings.final_top_k,
            )

            logger.info(
                "retrieval_complete",
                query_length=len(query),
                dense_count=len(dense_results),
                sparse_count=len(sparse_results),
                fused_count=len(fused_results),
                final_count=len(final_results),
            )

            return RetrievalResult(
                documents=final_results,
                query=query,
                retrieval_method="hybrid_rrf_rerank" if self._reranker else "hybrid_rrf",
            )

        except Exception as e:
            logger.error("retrieval_failed", error=str(e))
            raise RetrievalError(str(e)) from e

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the document collection.

        Returns:
            Collection statistics.
        """
        return {
            "collection_name": self._settings.chroma_collection_name,
            "document_count": self._collection.count(),
            "bm25_corpus_size": len(self._bm25_corpus),
            "reranking_enabled": self._reranker is not None,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self._embedder.close()


# Singleton instance
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Get the singleton HybridRetriever instance.

    Returns:
        HybridRetriever instance.
    """
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
