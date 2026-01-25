"""
FastAPI routes for Sovereign-Mind API.

Endpoints:
- POST /v1/chat/completions: Chat with the AI assistant
- POST /v1/system/ingest: Ingest documents into RAG
- GET /v1/system/health: Health check
- Vault management endpoints
"""

import hashlib
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.agent_graph import run_agent
from app.core.config import get_settings
from app.core.exceptions import (
    PrivacyThresholdExceeded,
    VaultLockedError,
)
from app.core.logging import get_logger
from app.core.security import get_vault
from app.models.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatMode,
    CollectionStats,
    ErrorResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    MessageRole,
    SessionInfo,
    SessionListResponse,
)
from app.services.privacy_guard import get_anonymization_service
from app.services.rag_engine import get_retriever

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        423: {"model": ErrorResponse, "description": "Vault is locked"},
        451: {"model": ErrorResponse, "description": "Privacy threshold exceeded"},
    },
)
async def chat_completions(request: ChatCompletionRequest):
    """Process a chat completion request.

    Security Boundaries:
    - Local mode: All processing stays on device
    - Cloud mode: PII is anonymized before external calls, rehydrated in response

    Args:
        request: Chat completion request with messages and config.

    Returns:
        ChatCompletionResponse with the assistant's reply.
    """
    settings = get_settings()
    vault = get_vault()
    privacy_service = get_anonymization_service()

    # Extract the user's query (last user message)
    user_messages = [m for m in request.messages if m.role == MessageRole.USER]
    if not user_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message provided",
        )

    query = user_messages[-1].content

    # Handle vault session for encrypted history
    session_id = request.session_id
    if session_id:
        try:
            vault._require_unlocked()
        except VaultLockedError:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Vault is locked. Unlock with passphrase first.",
            )

    # Handle privacy for cloud mode
    pii_session_id = None
    original_query = query

    if request.config.mode == ChatMode.CLOUD_SECURE:
        if settings.block_pii_on_cloud:
            try:
                # Anonymize query before sending to cloud
                query, pii_session_id = privacy_service.anonymize(query)
                logger.info(
                    "query_anonymized_for_cloud",
                    pii_session_id=pii_session_id,
                )
            except PrivacyThresholdExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
                    detail=str(e),
                )

    # Convert request messages to LangChain format
    messages = []
    for msg in request.messages:
        if msg.role == MessageRole.SYSTEM:
            messages.append(SystemMessage(content=msg.content))
        elif msg.role == MessageRole.USER:
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            messages.append(AIMessage(content=msg.content))

    # Run the agent
    try:
        result = await run_agent(
            query=query,
            mode=request.config.mode.value,
            depth=request.config.depth.value,
            session_id=session_id,
            messages=messages,
        )
    except Exception as e:
        logger.error("agent_execution_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )

    # Get the response
    answer = result.get("answer", "")

    # Rehydrate PII if we anonymized for cloud
    if pii_session_id and request.config.mode == ChatMode.CLOUD_SECURE:
        answer = privacy_service.rehydrate(answer, pii_session_id)
        # Clean up PII session
        privacy_service.delete_session(pii_session_id)

    # Store in vault if session is active
    if session_id and not vault.is_locked:
        vault.add_message(session_id, "user", original_query)
        vault.add_message(session_id, "assistant", answer)

    # Build response
    response = ChatCompletionResponse(
        id=f"chatcmpl-{secrets.token_hex(12)}",
        created=int(time.time()),
        model=settings.ollama_model if request.config.mode == ChatMode.LOCAL else settings.openai_model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role=MessageRole.ASSISTANT, content=answer),
            )
        ],
        session_id=session_id,
        intent=result.get("intent"),
    )

    return response


# ============================================================================
# Document Ingestion Endpoints
# ============================================================================


@router.post(
    "/v1/system/ingest",
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}},
)
async def ingest_document(
    file: Annotated[UploadFile | None, File()] = None,
    content: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form()] = None,
):
    """Ingest a document into the RAG system.

    Supports:
    - File upload (PDF, TXT)
    - Direct text content

    Security Boundary: Documents are stored locally in ChromaDB.
    No content is sent externally.

    Args:
        file: Optional file to upload.
        content: Optional direct text content.
        metadata: Optional JSON metadata string.

    Returns:
        IngestResponse with ingestion results.
    """
    retriever = get_retriever()

    # Parse metadata if provided
    meta_dict = {}
    if metadata:
        try:
            import json

            meta_dict = json.loads(metadata)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metadata JSON",
            )

    # Handle file upload
    if file:
        # Save to temp location
        temp_dir = Path("./data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "document.txt").suffix
        temp_path = temp_dir / f"{secrets.token_hex(8)}{suffix}"

        try:
            file_content = await file.read()
            temp_path.write_bytes(file_content)

            # Ingest the file
            chunk_count = await retriever.ingest_file(
                temp_path,
                metadata={**meta_dict, "original_filename": file.filename},
            )

            doc_id = temp_path.stem

            return IngestResponse(
                success=True,
                document_id=doc_id,
                chunk_count=chunk_count,
                message=f"Successfully ingested {file.filename}",
            )

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    # Handle direct content
    elif content:
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        chunk_count = await retriever.ingest_document(
            content=content,
            doc_id=doc_id,
            metadata=meta_dict,
        )

        return IngestResponse(
            success=True,
            document_id=doc_id,
            chunk_count=chunk_count,
            message="Successfully ingested text content",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file or content must be provided",
        )


@router.get("/v1/system/collection", response_model=CollectionStats)
async def get_collection_stats():
    """Get RAG collection statistics.

    Returns:
        CollectionStats with document counts and settings.
    """
    retriever = get_retriever()
    stats = retriever.get_collection_stats()

    return CollectionStats(**stats)


# ============================================================================
# Vault Management Endpoints
# ============================================================================


@router.post("/v1/vault/unlock")
async def unlock_vault(passphrase: str = Form(...)):
    """Unlock the vault with a passphrase.

    Security Boundary: Passphrase is used for key derivation only.
    Never stored or logged.

    Args:
        passphrase: User's secret passphrase.

    Returns:
        Success message.
    """
    vault = get_vault()

    try:
        vault.unlock(passphrase)
        return {"message": "Vault unlocked successfully"}
    except Exception as e:
        logger.error("vault_unlock_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to unlock vault",
        )


@router.post("/v1/vault/lock")
async def lock_vault():
    """Lock the vault and clear keys from memory.

    Returns:
        Success message.
    """
    vault = get_vault()
    vault.lock()
    return {"message": "Vault locked successfully"}


@router.post("/v1/vault/sessions", response_model=SessionInfo)
async def create_session():
    """Create a new encrypted chat session.

    Returns:
        SessionInfo for the new session.
    """
    vault = get_vault()

    try:
        vault._require_unlocked()
    except VaultLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked",
        )

    session_id = vault.create_session()

    return SessionInfo(
        session_id=session_id,
        message_count=0,
        created_at="",
        updated_at="",
    )


@router.get("/v1/vault/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all encrypted chat sessions.

    Returns:
        SessionListResponse with all sessions.
    """
    vault = get_vault()

    try:
        vault._require_unlocked()
    except VaultLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked",
        )

    sessions = vault.list_sessions()

    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions],
        total=len(sessions),
    )


@router.get("/v1/vault/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get decrypted messages from a session.

    Security Boundary: Returns plaintext messages.
    Only for authorized user viewing.

    Args:
        session_id: Session to retrieve messages from.

    Returns:
        List of decrypted messages.
    """
    vault = get_vault()

    try:
        vault._require_unlocked()
    except VaultLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked",
        )

    try:
        messages = vault.get_messages(session_id)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/v1/vault/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete an encrypted session.

    Args:
        session_id: Session to delete.

    Returns:
        Success message.
    """
    vault = get_vault()

    try:
        vault._require_unlocked()
    except VaultLockedError:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is locked",
        )

    vault.delete_session(session_id)
    return {"message": f"Session {session_id} deleted"}


# ============================================================================
# Health & Status Endpoints
# ============================================================================


@router.get("/v1/system/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        HealthResponse with system status.
    """
    settings = get_settings()
    vault = get_vault()
    retriever = get_retriever()

    stats = retriever.get_collection_stats()

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        vault_unlocked=not vault.is_locked,
        rag_document_count=stats["document_count"],
    )


# ============================================================================
# OpenAI-Compatible Endpoints (for Open WebUI)
# ============================================================================


@router.get("/v1/models")
async def list_models():
    """List available models for Open WebUI compatibility.

    Returns a list of models in OpenAI-compatible format.
    """
    settings = get_settings()

    return {
        "object": "list",
        "data": [
            {
                "id": settings.ollama_model,
                "object": "model",
                "created": 1700000000,
                "owned_by": "sovereign-mind",
                "permission": [],
                "root": settings.ollama_model,
                "parent": None,
            },
        ],
    }


# ============================================================================
# Agent Endpoints (v2 Agentic Platform)
# ============================================================================


@router.post("/v1/agent/run")
async def run_agent_endpoint(
    query: str = Form(...),
    session_id: str | None = Form(None),
):
    """Execute the agentic research pipeline.
    
    This runs the LangGraph agent with:
    - Intent classification
    - Document retrieval  
    - Grading and query refinement
    - Answer generation
    
    Returns the answer and metadata.
    """
    from app.core.minion_orchestrator import get_minion_orchestrator, ContextSyncError
    from app.services.audit_log import AuditLogger, AgentAction
    from datetime import datetime
    import uuid
    
    # Use Minion Orchestrator for hybrid execution
    orchestrator = get_minion_orchestrator()
    
    try:
        # Phase 1: Orchestration & Execution
        result = await orchestrator.orchestrate(
            query=query,
            session_id=session_id
        )
        
        # Phase 2: Auditing
        run_id = str(uuid.uuid4())
        
        action = AgentAction(
            run_id=run_id,
            node="minion_orchestrator",
            thought=f"Hybrid execution completed. Plan steps: {len(result.get('plan', {}).get('steps', []))}",
            tool_call=None,
            risk_score=0.1,
            timestamp=datetime.utcnow()
        )
        await AuditLogger.log(action)
        
        return {
            "success": True,
            "answer": result["answer"],
            "intent": "hybrid_inference", 
            "documents_used": 0, # TODO: Aggregate from sub-tasks
            "compliance_passed": True, 
            "retries": 0,
            "run_id": run_id,
            "audit_trail": [{
                "run_id": run_id,
                "node": "minion_orchestrator",
                "thought": action.thought,
                "tool_call": None,
                "risk_score": 0.1,
                "timestamp": action.timestamp.isoformat(),
                "witness_signature": action.witness_signature # Include signature in response
            }]
        }
        
    except ContextSyncError as e:
        logger.error("minion_sync_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cloud/Local Context Mismatch: {str(e)}. Please perform full sync."
        )
    except Exception as e:
        logger.error("minion_execution_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/v1/agent/run/{run_id}")
async def get_agent_run(run_id: str):
    """Get the audit trail for a specific agent run."""
    from app.services.audit_log import AuditLogger
    
    actions = await AuditLogger.get_run_actions(run_id)
    
    if not actions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )
    
    return {
        "run_id": run_id,
        "actions": [a.model_dump() for a in actions],
    }


# ============================================================================
# Compliance Endpoints
# ============================================================================


@router.get("/v1/compliance/logs")
async def get_compliance_logs(limit: int = 100):
    """Get recent compliance audit logs.
    
    Returns the most recent agent actions across all runs.
    """
    from app.services.audit_log import AuditLogger
    
    actions = await AuditLogger.get_recent_actions(limit=limit)
    
    return {
        "total": len(actions),
        "actions": [a.model_dump() for a in actions],
    }



@router.get("/v1/compliance/verify")
async def verify_compliance_integrity():
    """Verify the cryptographic integrity of the audit logs.
    
    This performs an on-the-fly verification of the Merkle Chain.
    """
    from app.services.audit_log import AuditLogger
    
    is_valid = await AuditLogger.verify_integrity()
    
    return {
        "integrity_verified": is_valid,
        "verified_at": datetime.utcnow().isoformat(),
        "integrity_check": "passed" if is_valid else "failed"
    }

@router.get("/v1/compliance/report")
async def generate_compliance_report():
    """Generate a compliance report.
    
    Returns aggregate statistics and recent actions for
    EU AI Act / SOC 2 compliance reporting.
    """
    from app.services.audit_log import AuditLogger
    
    report = await AuditLogger.generate_report()
    
    return {
        "generated_at": report.generated_at.isoformat(),
        "summary": {
            "total_actions": report.total_actions,
            "high_risk_actions": report.high_risk_actions,
            "runs_with_pii": report.runs_with_pii,
            "runs_total": report.runs_total,
        },
        "recent_actions": [a.model_dump() for a in report.actions[:20]],
    }


# ============================================================================
# Shadow AI Scanner Endpoints
# ============================================================================


@router.get("/v1/system/shadow-scan")
async def scan_shadow_ai():
    """Scan for unauthorized AI processes on the local network.
    
    Returns a list of potential "shadow AI" risks - unauthorized
    LLM services that may pose compliance or security risks.
    """
    from app.services.shadow_scanner import get_shadow_scanner
    
    scanner = get_shadow_scanner()
    risks = scanner.scan_ports()
    
    return scanner.get_report()

