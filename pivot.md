# Sovereign-Mind 2.0: The Agentic Pivot (Super-Prompt)

> **Objective:** Transform Sovereign-Mind from a "Private RAG Chatbot" into the "Compliance-First Agentic Platform" for the 2026 Enterprise.

## 1. The Strategic Pivot
We are moving beyond simple chat. The market has shifted. Companies don't just want to *talk* to their data; they want **Agents** that can *act* on it—but they are terrified of "Shadow AI" and regulatory fines (EU AI Act).

**Our New Value Prop:** "The only local AI agent platform that guarantees compliance and zero-knowledge privacy."

---

## 2. Core Architecture (What We Keep)
We retain the rock-solid foundation built in v1:
*   **The Vault:** Argon2id hashing + AES-256-GCM encryption for all session data.
*   **Local Inference:** Ollama / vLLM integration (Air-gapped ready).
*   **Hybrid RAG:** ChromaDB (Dense) + BM25 (Sparse) + Cross-Encoder Reranking.
*   **Privacy Guard:** PII redaction before inference.

---

## 3. New "Agentic Core" (What We Build)

### A. The Agent Orchestrator (LangGraph)
Replace simple request/response with a stateful graph.
*   **Supervisor Agent:** Routes intent (Chat vs. Research vs. Audit).
*   **Research Agent:** Autonomous web search + RAG loop for deep reports.
*   **Compliance Agent:** The "Supervisor's Supervisor". Checks every step against policy.

### B. "Compliance Shield" (The Killer Feature)
Enterprises need to PROVE they are safe.
*   **Tamper-Proof Audit Logs:** Record every "thought" and "action" of the agent to SQLite/DuckDB.
*   **Report Generator:** One-click PDF export: "EU AI Act Transparency Report."
*   **Shadow AI Defense:** A dashboard tracking "unauthorized" model usage (conceptual/stub).

### C. Human-in-the-Loop (HITL) Execution
Agents cannot be trusted with write access blindly.
*   **The "Nuclear Key" UI:** If an agent wants to *delete* a file or *send* an email, the UI MUST pause and demand a human click "APPROVE".

---

## 4. Tech Stack (Latest & Greatest)

### Backend (Python)
*   **Framework:** FastAPI (High performance async).
*   **Orchestration:** `langgraph` (Stateful, cyclic multi-agent flows).
*   **Inference:** `ollama` (Dev) / `vLLM` (Prod - 10x throughput).
*   **Vector Store:** `chromadb` (Local, embedded).

### Frontend (Next.js 14+)
*   **Framework:** Next.js App Router (React Server Components).
*   **UI Library:** `shadcn/ui` + `Tailwind CSS` (clean, accessible, enterprise-grade).
*   **State:** `tstack/query` (formerly React Query) for robust async state.
*   **Agent UI:** Streaming steps sidebar (show the agent's "thought process").

---

## 5. Detailed Implementation Prompt
*(Copy/Paste this to an AI engineer to build the system)*

```markdown
You are an expert AI Engineer specializing in Local LLMs and Security.

**Task:** Build Sovereign-Mind v2 - The Agentic Compliance Platform.

**Constraints:**
1.  **Zero-Knowledge:** No data leaves the container.
2.  **Local-First:** Must run on a single NVIDIA GPU or Consumer Mac (M3).
3.  **Secure:** Integrating existing `Vault` module is mandatory.

**Step-by-Step Instructions:**

1.  **Agent Backend (`/services/agent_graph.py`):**
    *   Initialize a `langgraph` StateGraph.
    *   Define nodes: `retrieve_docs`, `grade_documents`, `generate_answer`, `compliance_check`.
    *   Implement "Reflexion": If the `compliance_check` fails (e.g., PII detected), the agent attacks itself and retries.

2.  **Compliance Database (`/services/audit_log.py`):**
    *   Create a schema for `AgentAction`: {timestamp, agent_id, thought, tool_call, risk_score}.
    *   Every LangGraph step MUST emit an event to this log.

3.  **Frontend "Mission Control" (`/ui/app/agents`):**
    *   Create a dashboard showing active agents.
    *   **Live Stream:** Show the agent's "thinking" in real-time (e.g., "Searching vault...", "Redacting PII...", "Generating...").
    *   **Approval Mode:** If an agent requests a `TOOL_CALL: WRITE_FILE`, show a big yellow "APPROVE / REJECT" button.

4.  **Shadow AI Scanner (Mock):**
    *   Create a scanner that looks for other running LLM processes (Ollama, LM Studio) on the host network and reports them as "Unmanaged Risks".

**Success Criteria:**
*   I can ask the agent: "Research the risks of GenAI in finance based on my vault docs."
*   It performs multiple RAG lookups autonomously.
*   It produces a citation-rich answer.
*   I can go to "Compliance" tab and see the exact audit trail of how it derived that answer.
```
