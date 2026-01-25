/**
 * Sovereign-Mind API Client
 * Type-safe client for backend API calls
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export interface Message {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

export interface ChatConfig {
    mode: 'local' | 'cloud_secure';
    depth: 'fast' | 'deep_reasoning';
}

export interface ChatRequest {
    messages: Message[];
    config?: ChatConfig;
    session_id?: string;
    model?: string;
}

export interface ChatChoice {
    index: number;
    message: Message;
    finish_reason: string;
}

export interface ChatResponse {
    id: string;
    object: string;
    created: number;
    model: string;
    choices: ChatChoice[];
    session_id?: string;
    intent?: string;
}

export interface HealthResponse {
    status: string;
    version: string;
    vault_unlocked: boolean;
    rag_document_count: number;
}

export interface Model {
    id: string;
    object: string;
    created: number;
    owned_by: string;
}

export interface ModelsResponse {
    object: string;
    data: Model[];
}

export interface SessionInfo {
    session_id: string;
    message_count: number;
    created_at: string;
    updated_at: string;
}

export interface SessionListResponse {
    sessions: SessionInfo[];
    total: number;
}

export interface CollectionStats {
    collection_name: string;
    document_count: number;
    bm25_corpus_size: number;
    reranking_enabled: boolean;
}

export interface IngestResponse {
    success: boolean;
    document_id: string;
    chunk_count: number;
    message: string;
}

// ============================================================================
// API Client
// ============================================================================

class SovereignMindAPI {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    // Health & Status
    async getHealth(): Promise<HealthResponse> {
        const res = await fetch(`${this.baseUrl}/v1/system/health`);
        if (!res.ok) throw new Error('Failed to fetch health');
        return res.json();
    }

    async getModels(): Promise<ModelsResponse> {
        const res = await fetch(`${this.baseUrl}/v1/models`);
        if (!res.ok) throw new Error('Failed to fetch models');
        return res.json();
    }

    async getCollectionStats(): Promise<CollectionStats> {
        const res = await fetch(`${this.baseUrl}/v1/system/collection`);
        if (!res.ok) throw new Error('Failed to fetch collection stats');
        return res.json();
    }

    // Chat
    async chat(request: ChatRequest): Promise<ChatResponse> {
        const res = await fetch(`${this.baseUrl}/v1/chat/completions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: request.messages,
                config: request.config || { mode: 'local', depth: 'fast' },
                session_id: request.session_id,
                model: request.model,
            }),
        });
        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || 'Chat request failed');
        }
        return res.json();
    }

    // Vault
    async unlockVault(passphrase: string): Promise<{ message: string }> {
        const res = await fetch(`${this.baseUrl}/v1/vault/unlock`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `passphrase=${encodeURIComponent(passphrase)}`,
        });
        if (!res.ok) throw new Error('Failed to unlock vault');
        return res.json();
    }

    async lockVault(): Promise<{ message: string }> {
        const res = await fetch(`${this.baseUrl}/v1/vault/lock`, {
            method: 'POST',
        });
        if (!res.ok) throw new Error('Failed to lock vault');
        return res.json();
    }

    async listSessions(): Promise<SessionListResponse> {
        const res = await fetch(`${this.baseUrl}/v1/vault/sessions`);
        if (!res.ok) throw new Error('Failed to list sessions');
        return res.json();
    }

    async createSession(): Promise<SessionInfo> {
        const res = await fetch(`${this.baseUrl}/v1/vault/sessions`, {
            method: 'POST',
        });
        if (!res.ok) throw new Error('Failed to create session');
        return res.json();
    }

    async getSessionMessages(sessionId: string): Promise<{ messages: Message[] }> {
        const res = await fetch(`${this.baseUrl}/v1/vault/sessions/${sessionId}/messages`);
        if (!res.ok) throw new Error('Failed to get session messages');
        return res.json();
    }

    async deleteSession(sessionId: string): Promise<{ message: string }> {
        const res = await fetch(`${this.baseUrl}/v1/vault/sessions/${sessionId}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete session');
        return res.json();
    }

    // RAG
    async ingestDocument(content: string, metadata?: Record<string, string>): Promise<IngestResponse> {
        const formData = new FormData();
        formData.append('content', content);
        if (metadata) {
            formData.append('metadata', JSON.stringify(metadata));
        }

        const res = await fetch(`${this.baseUrl}/v1/system/ingest`, {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) throw new Error('Failed to ingest document');
        return res.json();
    }

    async ingestFile(file: File, metadata?: Record<string, string>): Promise<IngestResponse> {
        const formData = new FormData();
        formData.append('file', file);
        if (metadata) {
            formData.append('metadata', JSON.stringify(metadata));
        }

        const res = await fetch(`${this.baseUrl}/v1/system/ingest`, {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) throw new Error('Failed to ingest file');
        return res.json();
    }
}

export const api = new SovereignMindAPI();
export default api;
