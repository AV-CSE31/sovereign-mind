# ADR-001: Hybrid RAG Pipeline with RRF Fusion

## Status
Accepted

## Context
We needed a retrieval system that handles both semantic similarity (dense) and exact keyword matching (sparse). Single-method retrieval consistently fails on either conceptual queries or specific term lookups.

## Decision
Implement a hybrid retrieval pipeline combining:
- **Dense search**: ChromaDB with local embeddings (mxbai-embed-large)
- **Sparse search**: BM25 (rank-bm25) for keyword matching
- **Fusion**: Reciprocal Rank Fusion (RRF) to merge results
- **Reranking**: FlashRank (MiniLM-L6-v2) cross-encoder for final ordering

All processing runs locally by default — no data leaves the device.

## Consequences

### Positive
- Handles both semantic and keyword queries well
- RRF is parameter-free and robust
- Reranking significantly improves precision
- Fully local — maintains privacy guarantees

### Negative
- Higher latency than single-method retrieval (~2-3x)
- BM25 index must be rebuilt on document changes
- FlashRank model adds ~100MB to deployment
