"""
Module C (Graph Extension): Local Knowledge Graph via NetworkX.

This module implements a lightweight, file-backed Knowledge Graph to support
GraphRAG (Retrieval Augmented Generation with Graph Traversal).

Features:
1. Entity Extraction: Uses LLM to identify Entities and Relations.
2. Graph Storage: NetworkX + Pickle for local persistence.
3. Multi-hop Retrieval: Finds neighbors of query entities.
"""

import os
import pickle

import networkx as nx
from langchain_core.prompts import ChatPromptTemplate

# We need to import create_llm, but it is in agent_graph.py which might cause circular import
# simpler to instantiate ChatOllama directly here or move create_llm to a shared utility.
# For now, we will duplicate the LLM creation logic slightly to avoid circular dependency loop with agent_graph
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# --- Schemas ---


class Entity(BaseModel):
    name: str = Field(..., description="Name of the entity (e.g., 'Alice', 'Project X').")
    type: str = Field(
        ..., description="Type of the entity (e.g., 'Person', 'Project', 'Location')."
    )


class Relation(BaseModel):
    source: str = Field(..., description="Source entity name.")
    target: str = Field(..., description="Target entity name.")
    relation: str = Field(..., description="Relationship type (e.g., 'works_on', 'located_in').")


class GraphExtraction(BaseModel):
    """Structured output for graph extraction."""

    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


# --- Service ---


class LocalGraphStore:
    """A NetworkX-backed knowledge graph that persists to disk."""

    def __init__(self, persist_path: str = "data/knowledge_graph.pkl"):
        self.persist_path = persist_path
        self._graph = nx.MultiDiGraph()
        self._load()

    def _load(self):
        """Load graph from disk."""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "rb") as f:
                    self._graph = pickle.load(f)
                logger.info(
                    "graph_loaded",
                    nodes=self._graph.number_of_nodes(),
                    edges=self._graph.number_of_edges(),
                )
            except Exception as e:
                logger.error("graph_load_failed", error=str(e))
                self._graph = nx.MultiDiGraph()
        else:
            self._graph = nx.MultiDiGraph()
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)

    def _save(self):
        """Save graph to disk."""
        try:
            with open(self.persist_path, "wb") as f:
                pickle.dump(self._graph, f)
            logger.debug("graph_saved", path=self.persist_path)
        except Exception as e:
            logger.error("graph_save_failed", error=str(e))

    def add_triplets(self, extract: GraphExtraction, source_doc_id: str):
        """Add entities and relations to the graph."""
        # Add nodes
        for entity in extract.entities:
            self._graph.add_node(entity.name.lower(), type=entity.type, original_name=entity.name)

        # Add edges
        for rel in extract.relations:
            self._graph.add_edge(
                rel.source.lower(),
                rel.target.lower(),
                relation=rel.relation,
                source_doc=source_doc_id,
            )

        self._save()

    def get_context(self, entities: list[str], depth: int = 1) -> list[str]:
        """Retrieve context (triplets) related to the given entities."""
        found_triplets = []

        for entity in entities:
            entity_key = entity.lower()
            if not self._graph.has_node(entity_key):
                continue

            # BFS traversal for context
            # For depth 1, just get neighbors
            edges = list(self._graph.edges(entity_key, data=True))
            for u, v, data in edges:
                rel = data.get("relation", "related_to")
                # Format: "Alice works_on Project X"
                # Retrieve original casing if possible
                u_name = self._graph.nodes[u].get("original_name", u)
                v_name = self._graph.nodes[v].get("original_name", v)

                triplet_str = f"{u_name} --[{rel}]--> {v_name}"
                found_triplets.append(triplet_str)

        return list(set(found_triplets))  # Deduplicate

    def get_stats(self):
        return {"nodes": self._graph.number_of_nodes(), "edges": self._graph.number_of_edges()}


# --- Extractor ---


class GraphExtractor:
    """Helper to extract graph data from text using LLM."""

    def __init__(self):
        settings = get_settings()
        self.llm = ChatOllama(
            model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0.0
        ).with_structured_output(GraphExtraction)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a knowledge graph builder. Extract entities and relationships from the text.

Nodes: Identifying Objects, People, Locations, Concepts.
Edges: Identifying relationships between them.

Return JSON.""",
                ),
                ("human", "{text}"),
            ]
        )

    async def extract(self, text: str) -> GraphExtraction:
        try:
            chain = self.prompt | self.llm
            result = await chain.ainvoke({"text": text})
            return result
        except Exception as e:
            logger.error("graph_extraction_failed", error=str(e))
            return GraphExtraction()


# Singleton
_graph_store = None


def get_graph_store() -> LocalGraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = LocalGraphStore()
    return _graph_store
