"""
Module B: The Brain - Agentic Reasoning with LangGraph.

This module implements System 2 thinking with a Plan-Execute-Grade-Refine loop:
1. Supervisor: Classifies intent (Simple Chat, Complex Reasoning, RAG Search)
2. Planner: Breaks complex queries into steps
3. Retriever: Fetches context from RAG engine
4. Grader: Evaluates retrieved documents for relevance (loops back if < 0.7)
5. Generator: Synthesizes the final answer

Security Boundaries:
- Local LLM (Ollama) is preferred for all reasoning
- Cloud LLM requires privacy filtering (see Module D)
- All prompts/responses are hashed for audit, never stored in plaintext
"""

import json
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_ollama import ChatOllama
from app.core.schemas import Intent, IntentType, Plan, Grade, RewriteQuery
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.core.config import get_settings
from app.core.exceptions import (
    IntentClassificationError,
    MaxRetriesExceeded,
    PlanningError,
)

from app.core.logging import audit_log, get_logger, hash_for_audit
from app.core.tracing import trace_node
from app.services.rag_engine import Document, get_retriever
from app.core.memory import get_memory_service, MemoryExtractor

logger = get_logger(__name__)


class IntentEnum(str, Enum):
    """User intent classification."""

    SIMPLE_CHAT = "simple_chat"
    COMPLEX_REASONING = "complex_reasoning"
    RAG_SEARCH = "rag_search"


class AgentState(TypedDict):
    """State for the agent graph.

    Security Boundary: Messages may contain sensitive user data.
    Handle with care and ensure proper anonymization before cloud calls.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    intent: str | None
    plan: list[str] | None
    current_step: int
    query: str
    retrieved_docs: list[dict[str, Any]]
    grader_score: float
    retrieval_attempts: int
    final_answer: str | None
    mode: str
    depth: str
    session_id: str | None
    user_id: str
    pii_session_id: str | None
    user_profile: str  # SOTA: Episodic memory context
    reflexion_score: float
    reflexion_feedback: str | None
    reflexion_attempts: int


def load_policy():
    """Load policy.json."""
    try:
        with open("app/core/policy.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"compliance_rules": [], "reflexion_threshold": 0.8}


# reflexions logic below
@trace_node
async def reflexion_node(state: AgentState) -> dict[str, Any]:
    """Review the final answer for compliance with policy.

    Security Boundary: This node is the 'Self-Healing' governance layer.
    """
    settings = get_settings()
    llm = create_llm(local=True)
    policy = load_policy()
    
    answer = state.get("final_answer", "")
    if not answer:
        return {"reflexion_score": 1.0}

    rules_text = "\n".join([f"- {r['description']}" for r in policy.get("compliance_rules", [])])

    reflexion_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a Compliance Officer. Review the agent's response against the following rules:

{rules}

If the response violates ANY rule, score it below {threshold} and provide specific feedback to fix it.
If it is compliant, score it 1.0.

Response Format:
Score: <0.0-1.0>
Feedback: <Actionable advice>""",
            ),
            ("human", "Agent Response: {answer}"),
        ]
    )

    try:
        chain = reflexion_prompt | llm
        response = await chain.ainvoke({
            "rules": rules_text, 
            "threshold": policy.get("reflexion_threshold", 0.8),
            "answer": answer
        })
        
        content = response.content.strip()
        lines = content.split('\n')
        score = 0.0
        feedback = "Compliance check failed format."
        
        for line in lines:
            if line.startswith("Score:"):
                try:
                    score = float(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("Feedback:"):
                feedback = line.split(":", 1)[1].strip()

        logger.info("reflexion_complete", score=score, feedback=feedback[:50])
        
        return {
            "reflexion_score": score, 
            "reflexion_feedback": feedback,
            "reflexion_attempts": state.get("reflexion_attempts", 0) + 1
        }

    except Exception as e:
        logger.error("reflexion_failed", error=str(e))
        return {"reflexion_score": 1.0}  # Fail open if checker breaks, or strictly fail closed? Using fail open for now to avoid UX block.


        return {"reflexion_score": 1.0}  # Fail open if checker breaks, or strictly fail closed? Using fail open for now to avoid UX block.


@trace_node
async def load_memory_node(state: AgentState) -> dict[str, Any]:
    """Load user profile from persistent memory (Mem0)."""
    user_id = state.get("user_id", "default_user")
    service = get_memory_service()
    # Get all memories for generic profile, could also search based on query if available
    profile = service.get_all(user_id)
    
    if profile:
        logger.info("memory_loaded", user_id=user_id, length=len(profile))
        
    return {"user_profile": profile}


@trace_node
async def memorize_node(state: AgentState) -> dict[str, Any]:
    """Extract and save new facts about the user using Mem0."""
    user_id = state.get("user_id", "default_user")
    messages = state["messages"]
    
    # Run in background (don't block response) - for now sync in graph
    extractor = MemoryExtractor()
    service = get_memory_service()
    
    try:
        # Extract raw text interactions
        interactions = await extractor.extract_from_messages(messages)
        for interaction in interactions:
            # Add to Mem0 (it handles vectorization and storage)
            service.add(user_id, interaction)
            logger.info("memory_saved_mem0")
            
    except Exception as e:
        logger.error("memory_extraction_failed", error=str(e))
        
    return {}
    """Route based on reflexion score."""
    policy = load_policy()
    threshold = policy.get("reflexion_threshold", 0.8)
    score = state.get("reflexion_score", 1.0)
    attempts = state.get("reflexion_attempts", 0)
    
    if score >= threshold:
        return END
    elif attempts >= 3:
        # Max retries reached, append warning and end
        return "append_warning"
    else:
        # Retry generation with feedback
        return "generator"


async def append_warning_node(state: AgentState) -> dict[str, Any]:
    """Append a compliance warning if self-healing failed."""
    current_answer = state.get("final_answer", "")
    feedback = state.get("reflexion_feedback", "Compliance check failed.")
    warning = f"\n\n[SYSTEM WARNING: This response may violate compliance policy. Feedback: {feedback}]"
    
    return {
        "final_answer": current_answer + warning,
        "messages": [AIMessage(content=current_answer + warning)]
    }


# ... [Rest of routing functions] ...


def build_agent_graph() -> StateGraph:
    """Build the LangGraph agent with Plan-Execute-Grade-Refine loop.

    Returns:
        Compiled StateGraph.
    """
    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("grader", grader_node)
    graph.add_node("query_rewriter", query_rewriter_node)
    graph.add_node("generator", generator_node)
    graph.add_node("reflexion", reflexion_node)
    graph.add_node("append_warning", append_warning_node)

    # Set entry point
    graph.set_entry_point("supervisor")

    # Add conditional edges
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "generator": "generator",
            "planner": "planner",
            "retriever": "retriever",
        },
    )

    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "grader")

    graph.add_conditional_edges(
        "grader",
        route_after_grader,
        {
            "generator": "generator",
            "query_rewriter": "query_rewriter",
        },
    )

    graph.add_edge("query_rewriter", "retriever")
    graph.add_edge("generator", "reflexion")
    
    graph.add_conditional_edges(
        "reflexion",
        route_after_reflexion,
        {
            END: END,
            "generator": "generator",
            "append_warning": "append_warning"
        }
    )
    
    graph.add_edge("append_warning", END)

    logger.info("agent_graph_built")

    return graph.compile()


def create_llm(local: bool = True):
    """Create an LLM instance.

    Security Boundary: Local LLM sees all data. Cloud LLM must only see
    anonymized data (handled by the agent flow).

    Args:
        local: Whether to use local Ollama or cloud LLM.

    Returns:
        LLM instance.
    """
    settings = get_settings()

    if local:
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )
    else:
        # Cloud LLM (OpenAI) - requires API key
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )


# ============================================================================
# Node Implementations
# ============================================================================


# Node Implementations
# ============================================================================


@trace_node
async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """Classify user intent (String Version)."""
    llm = create_llm(local=True)
    query = state["query"]

    # Simple prompt asking for specific keywords
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Classify the user query into exactly one of these labels:
- simple_chat (for greetings, casual talk)
- complex_reasoning (for math, analysis)
- rag_search (for facts, lookups)

Reply ONLY with the label name. do not add punctuation."""),
        ("human", "{query}")
    ])

    try:
        chain = prompt | llm
        response = await chain.ainvoke({"query": query})
        
        # Clean output
        # If response is AIMessage, get content. If str, use it.
        raw_intent = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()
        
        # Validate
        valid_intents = ["simple_chat", "complex_reasoning", "rag_search"]
        intent_val = raw_intent if raw_intent in valid_intents else "rag_search"
        
        logger.info("intent_classified_str", intent=intent_val)
        return {"intent": intent_val}

    except Exception as e:
        logger.error("intent_classification_failed_str", error=str(e))
        return {"intent": "rag_search"}


@trace_node
async def planner_node(state: AgentState) -> dict[str, Any]:
    """Break complex queries into executable steps.

    Security Boundary: This node sees the raw user query.
    Planning is done locally.
    """
    settings = get_settings()
    llm = create_llm(local=True)

    query = state["query"]

    # SOTA: Use structured output for planning
    structured_llm = llm.with_structured_output(Plan)

    planning_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a query planner. Break down the user's complex question into a sequence of simpler steps.
Rules:
1. Steps should be clear and actionable.
2. Steps should logically build on each other.
3. Keep it under {max_steps} steps.""",
            ),
            ("human", "{query}"),
        ]
    )

    try:
        chain = planning_prompt | structured_llm
        result: Plan = await chain.ainvoke(
            {"query": query, "max_steps": settings.max_planning_steps}
        )

        logger.info("plan_created", step_count=len(result.steps))

        return {"plan": result.steps, "current_step": 0}

    except Exception as e:
        logger.error("planning_failed", error=str(e))
        # Fallback: treat the query as a single step
        return {"plan": [query], "current_step": 0}


        # Fallback: treat the query as a single step
        return {"plan": [query], "current_step": 0}


@trace_node
async def retriever_node(state: AgentState) -> dict[str, Any]:
    """Retrieve relevant documents from the RAG engine.

    Security Boundary: Retrieval is entirely local (ChromaDB + BM25).
    """
    retriever = get_retriever()

    # Determine which query to use
    if state.get("plan") and state["current_step"] < len(state["plan"]):
        query = state["plan"][state["current_step"]]
    else:
        query = state["query"]

    try:
        result = await retriever.retrieve(query)

        # Convert to serializable format
        docs = [
            {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "score": doc.score,
            }
            for doc in result.documents
        ]

        logger.info(
            "retrieval_complete",
            query_length=len(query),
            doc_count=len(docs),
        )

        return {
            "retrieved_docs": docs,
            "retrieval_attempts": state.get("retrieval_attempts", 0) + 1,
        }

    except Exception as e:
        logger.error("retrieval_failed", error=str(e))
        return {"retrieved_docs": [], "retrieval_attempts": state.get("retrieval_attempts", 0) + 1}


    except Exception as e:
        logger.error("retrieval_failed", error=str(e))
        return {"retrieved_docs": [], "retrieval_attempts": state.get("retrieval_attempts", 0) + 1}


@trace_node
async def grader_node(state: AgentState) -> dict[str, Any]:
    """Evaluate retrieved documents for relevance.

    Security Boundary: This node evaluates local documents.
    If score < threshold, triggers re-query.
    """
    settings = get_settings()
    llm = create_llm(local=True)

    docs = state.get("retrieved_docs", [])
    query = state["query"]

    if not docs:
        logger.warning("no_documents_to_grade")
        return {"grader_score": 0.0}

    grading_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a relevance grader. Evaluate how well the retrieved documents answer the user's question.
Be strict. If the document doesn't contain the specific information needed, mark it irrelevant.""",
            ),
            ("human", "Question: {query}\n\nDocuments:\n{documents}"),
        ]
    )

    try:
        # Format documents for grading
        docs_text = "\n\n".join(
            [f"Document {i+1}:\n{doc['content']}" for i, doc in enumerate(docs[:5])]
        )

        structured_llm = llm.with_structured_output(Grade)
        chain = grading_prompt | structured_llm
        result: Grade = await chain.ainvoke({"documents": docs_text, "query": query})

        logger.info("grading_complete", score=result.score, relevant=result.is_relevant)

        return {"grader_score": result.score}

    except Exception as e:
        logger.error("grading_failed", error=str(e))
        # Conservative: return low score to trigger retry
        return {"grader_score": 0.5}


        return {"grader_score": 0.5}


@trace_node
async def query_rewriter_node(state: AgentState) -> dict[str, Any]:
    """Rewrite query for better retrieval.

    Security Boundary: Query rewriting is done locally.
    """
    llm = create_llm(local=True)

    query = state["query"]

    rewrite_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a query optimizer. The previous search didn't find relevant documents.
Rewrite the query to be more specific or use different keywords that might match better.
Also extract key terms.""",
            ),
            ("human", "Original Query: {query}\nRewrite this for better search results."),
        ]
    )

    try:
        structured_llm = llm.with_structured_output(RewriteQuery)
        chain = rewrite_prompt | structured_llm
        result: RewriteQuery = await chain.ainvoke({"query": query})

        logger.info("query_rewritten", original=query, new=result.rewritten_query)

        return {"query": result.rewritten_query}

    except Exception as e:
        logger.error("query_rewrite_failed", error=str(e))
        return {}


        return {}


@trace_node
async def generator_node(state: AgentState) -> dict[str, Any]:
    """Synthesize the final answer.

    Security Boundary: This node generates the response.
    Uses local LLM by default, cloud LLM only if mode=cloud_secure
    and data has been anonymized.
    """
    settings = get_settings()

    # Determine which LLM to use
    use_local = state.get("mode", "local") == "local"
    llm = create_llm(local=use_local)

    query = state["query"]
    docs = state.get("retrieved_docs", [])
    intent = state.get("intent", IntentEnum.SIMPLE_CHAT.value)

    # Build context from retrieved documents
    context = ""
    if docs:
        context = "\n\n".join(
            [f"Source {i+1}:\n{doc['content']}" for i, doc in enumerate(docs)]
        )

    # Select prompt based on intent and depth
    depth = state.get("depth", "fast")

    if intent == IntentEnum.SIMPLE_CHAT.value:
        system_prompt = """You are a helpful AI assistant. Respond naturally and conversationally."""
    elif depth == "deep_reasoning":
        system_prompt = """You are an expert analyst. You think step-by-step and provide thorough, well-reasoned answers.

User Profile:
{user_profile}

When generating your response:
1. First, analyze the key aspects of the question
2. Consider multiple perspectives if applicable
3. Draw on the provided context when available
4. Synthesize a comprehensive answer
5. Acknowledge any limitations or uncertainties

Context (if provided):
{context}"""
    else:
        system_prompt = """You are a helpful AI assistant. Use the provided context to answer questions accurately and concisely.

User Profile:
{user_profile}

Context:
{context}"""

    generation_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{query}"),
        ]
    )

    try:
        chain = generation_prompt | llm
        response = await chain.ainvoke({
            "query": query, 
            "context": context,
            "user_profile": state.get("user_profile", "")
        })
        answer = response.content
        
        # Audit log (hashes only)
        audit_log(
            "response_generated",
            prompt_hash=hash_for_audit(query),
            response_hash=hash_for_audit(answer),
            session_id=state.get("session_id"),
            mode=state.get("mode"),
            intent=intent,
        )

        logger.info(
            "generation_complete",
            intent=intent,
            response_length=len(answer),
            local=use_local,
        )

        # Add response to messages
        new_message = AIMessage(content=answer)

        return {"final_answer": answer, "messages": [new_message]}

    except Exception as e:
        logger.error("generation_failed", error=str(e))
        error_response = "I apologize, but I encountered an error generating a response. Please try again."
        return {"final_answer": error_response, "messages": [AIMessage(content=error_response)]}


# ============================================================================
# Routing Functions
# ============================================================================


def route_after_supervisor(state: AgentState) -> str:
    """Route based on classified intent."""
    intent = state.get("intent", IntentEnum.SIMPLE_CHAT.value)
    # Defensive casting
    if hasattr(intent, "value"):
        intent = intent.value
    intent = str(intent)

    if intent == IntentEnum.SIMPLE_CHAT.value:
        return "generator"
    elif intent == IntentEnum.COMPLEX_REASONING.value:
        return "planner"
    else:  # RAG_SEARCH
        return "retriever"


def route_after_planner(state: AgentState) -> str:
    """Route to retriever after planning."""
    return "retriever"


def route_after_grader(state: AgentState) -> str:
    """Route based on grading score."""
    settings = get_settings()
    score = state.get("grader_score", 0.0)
    attempts = state.get("retrieval_attempts", 0)

    if score >= settings.grader_relevance_threshold:
        # Good enough, proceed to generation
        return "generator"
    elif attempts >= settings.max_retrieval_retries:
        # Max retries reached, proceed anyway
        logger.warning(
            "max_retrieval_retries_reached",
            attempts=attempts,
            final_score=score,
        )
        return "generator"
    else:
        # Rewrite query and retry
        return "query_rewriter"


def route_after_rewriter(state: AgentState) -> str:
    """Route back to retriever after query rewrite."""
    return "retriever"


# ============================================================================
# Graph Construction
# ============================================================================


def build_agent_graph() -> StateGraph:
    """Build the LangGraph agent with Plan-Execute-Grade-Refine loop.

    Returns:
        Compiled StateGraph.
    """
    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    # Add nodes
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("grader", grader_node)
    graph.add_node("query_rewriter", query_rewriter_node)
    graph.add_node("generator", generator_node)
    graph.add_node("memorize", memorize_node)  # Parallel node

    # Set entry point
    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "supervisor")

    # Add conditional edges
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "generator": "generator",
            "planner": "planner",
            "retriever": "retriever",
        },
    )

    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "grader")

    graph.add_conditional_edges(
        "grader",
        route_after_grader,
        {
            "generator": "generator",
            "query_rewriter": "query_rewriter",
        },
    )

    graph.add_edge("query_rewriter", "retriever")

    # End after generator
    # Run memorize in parallel or sequence? For graph simplicity, sequence for now.
    graph.add_edge("generator", "memorize")
    graph.add_edge("memorize", END)

    logger.info("agent_graph_built")

    return graph.compile()


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    """Get the singleton compiled agent graph.

    Returns:
        Compiled StateGraph.
    """
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


async def run_agent(
    query: str,
    mode: str = "local",
    depth: str = "fast",
    session_id: str | None = None,
    messages: list[BaseMessage] | None = None,
) -> dict[str, Any]:
    """Run the agent on a query.

    Security Boundary: This function orchestrates the full agentic flow.
    Mode 'cloud_secure' requires prior anonymization.

    Args:
        query: User's question.
        mode: "local" or "cloud_secure".
        depth: "fast" or "deep_reasoning".
        session_id: Optional vault session ID for context.
        messages: Optional conversation history.

    Returns:
        Agent result including final_answer and state.
    """
    graph = get_agent_graph()

    # Build initial state
    initial_state: AgentState = {
        "messages": messages or [HumanMessage(content=query)],
        "intent": None,
        "plan": None,
        "current_step": 0,
        "query": query,
        "retrieved_docs": [],
        "grader_score": 0.0,
        "retrieval_attempts": 0,
        "final_answer": None,
        "mode": mode,
        "depth": depth,
        "session_id": session_id,
        "user_id": "default_user", # In real app, pass this in
        "pii_session_id": None,
        "user_profile": "",
    }

    # Run the graph
    result = await graph.ainvoke(initial_state)

    return {
        "answer": result.get("final_answer", ""),
        "intent": result.get("intent"),
        "retrieved_docs": result.get("retrieved_docs", []),
        "messages": result.get("messages", []),
    }
