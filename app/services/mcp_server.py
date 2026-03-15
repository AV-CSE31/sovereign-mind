"""
Sovereign-Mind MCP Server via FastMCP.

This module exposes Sovereign-Mind capabilities as standardized MCP resources and tools.
"""

from fastapi import FastAPI
from fastmcp import Context, FastMCP

from app.core.security import get_vault
from app.services.audit_log import AuditLogger
from app.services.rag_engine import get_retriever

# Initialize FastMCP
mcp = FastMCP("Sovereign-Mind")


@mcp.tool()
async def query_vault(ctx: Context, session_id: str, query: str, limit: int = 5) -> str:
    """Search for encrypted messages within a specific vault session.

    Args:
        session_id: The ID of the session to search.
        query: The semantic search query.
        limit: Max number of messages to return.
    """
    vault = get_vault()
    if vault.is_locked:
        return "Error: Vault is locked. Please unlock via the main API first."

    try:
        # Note: This is an exact content match for now as the simple Vault
        # doesn't support semantic search yet.
        messages = vault.get_messages(session_id)
        results = [
            f"{m['role']}: {m['content']}"
            for m in messages
            if query.lower() in m["content"].lower()
        ]
        return "\n".join(results[:limit]) if results else "No matching messages found."
    except Exception as e:
        return f"Error accessing vault: {e!s}"


@mcp.tool()
async def search_knowledge_base(query: str, limit: int = 3) -> str:
    """Search the RAG knowledge base for relevant documents.

    Args:
        query: The semantic search query.
        limit: Max number of documents to return.
    """
    retriever = get_retriever()
    try:
        docs = await retriever.retrieve(query, limit=limit)
        return "\n\n".join(
            [
                f"--- Document: {d.metadata.get('original_filename', 'Unknown')} ---\n{d.page_content}"
                for d in docs
            ]
        )
    except Exception as e:
        return f"Error querying knowledge base: {e!s}"


@mcp.resource("audit://logs/recent")
async def get_recent_audit_logs() -> str:
    """Get the most recent 10 audit log entries."""
    actions = await AuditLogger.get_recent_actions(limit=10)
    return "\n".join(
        [f"[{a.timestamp}] {a.node}: {a.thought} (Risk: {a.risk_score})" for a in actions]
    )


@mcp.tool()
async def verify_compliance(ctx: Context) -> str:
    """Verify the cryptographic integrity of the Sovereign-Mind audit log."""
    is_valid = await AuditLogger.verify_integrity()
    return f"Integrity Check: {'PASSED' if is_valid else 'FAILED (TAMPERING DETECTED)'}"


# Mount to FastAPI if needed, or run standalone
def create_mcp_app() -> FastAPI:
    # fastmcp provides a way to mount to existing FastAPI
    # but here we might run it as a sub-app
    return mcp._app
