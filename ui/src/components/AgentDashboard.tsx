'use client';

import { useState } from 'react';
import { Bot, Loader2, CheckCircle, AlertTriangle, Search, FileText, Shield, User, Activity } from 'lucide-react';
import { MemoryPanel } from './MemoryPanel';
import { TracePanel } from './TracePanel';
import { CompliancePanel } from './CompliancePanel';

interface AuditAction {
    run_id: string;
    node: string;
    thought: string;
    tool_call: string | null;
    risk_score: number;
    timestamp: string;
}

interface AgentResult {
    success: boolean;
    answer: string;
    intent: string;
    documents_used: number;
    compliance_passed: boolean;
    retries: number;
    run_id: string;
    audit_trail: AuditAction[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function AgentDashboard() {
    const [query, setQuery] = useState('');
    const [isRunning, setIsRunning] = useState(false);
    const [result, setResult] = useState<AgentResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const runAgent = async () => {
        if (!query.trim()) return;

        setIsRunning(true);
        setError(null);
        setResult(null);

        try {
            const formData = new FormData();
            formData.append('query', query);

            const response = await fetch(`${API_BASE}/v1/agent/run`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Agent failed: ${response.statusText}`);
            }

            const data: AgentResult = await response.json();
            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setIsRunning(false);
        }
    };

    const [activeTab, setActiveTab] = useState<'agents' | 'memory' | 'traces' | 'compliance'>('agents');

    return (
        <div className="flex flex-col h-full bg-zinc-900">
            {/* Header Tabs */}
            <div className="flex border-b border-zinc-800 bg-zinc-950/50">
                <button
                    onClick={() => setActiveTab('agents')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'agents' ? 'border-purple-500 text-purple-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
                >
                    <div className="flex items-center justify-center gap-2">
                        <Bot className="w-4 h-4" />
                        Mission Control
                    </div>
                </button>
                <button
                    onClick={() => setActiveTab('memory')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'memory' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
                >
                    <div className="flex items-center justify-center gap-2">
                        <User className="w-4 h-4" />
                        Memory Store
                    </div>
                </button>
                <button
                    onClick={() => setActiveTab('traces')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'traces' ? 'border-amber-500 text-amber-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
                >
                    <div className="flex items-center justify-center gap-2">
                        <Activity className="w-4 h-4" />
                        Observability
                    </div>
                </button>
                <button
                    onClick={() => setActiveTab('compliance')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'compliance' ? 'border-red-500 text-red-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
                >
                    <div className="flex items-center justify-center gap-2">
                        <Shield className="w-4 h-4" />
                        Compliance PII
                    </div>
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-hidden relative">

                {/* AGENT VIEW */}
                <div className={`absolute inset-0 flex flex-col transition-opacity duration-300 ${activeTab === 'agents' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`}>
                    {/* Input Section */}
                    <div className="p-6 border-b border-zinc-800">
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && runAgent()}
                                placeholder="Ask the agent to research something..."
                                className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500"
                                disabled={isRunning}
                            />
                            <button
                                onClick={runAgent}
                                disabled={isRunning || !query.trim()}
                                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-xl font-medium transition-colors flex items-center gap-2"
                            >
                                {isRunning ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Running...
                                    </>
                                ) : (
                                    <>
                                        <Bot className="w-4 h-4" />
                                        Run Agent
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Results Section */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {error && (
                            <div className="p-4 bg-red-900/30 border border-red-700 rounded-xl mb-4">
                                <p className="text-red-300">{error}</p>
                            </div>
                        )}

                        {result && (
                            <div className="space-y-6">
                                {/* Answer Card */}
                                <div className="bg-zinc-800 rounded-xl p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="font-semibold text-lg">Agent Response</h3>
                                        <div className="flex items-center gap-2">
                                            {result.compliance_passed ? (
                                                <span className="flex items-center gap-1 px-2 py-1 bg-emerald-900/50 text-emerald-300 rounded text-sm">
                                                    <CheckCircle className="w-3 h-3" />
                                                    Compliant
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1 px-2 py-1 bg-amber-900/50 text-amber-300 rounded text-sm">
                                                    <AlertTriangle className="w-3 h-3" />
                                                    Reviewed
                                                </span>
                                            )}
                                            <span className="px-2 py-1 bg-purple-900/50 text-purple-300 rounded text-sm">
                                                {result.intent}
                                            </span>
                                        </div>
                                    </div>
                                    <p className="text-zinc-200 whitespace-pre-wrap">{result.answer}</p>
                                    <div className="mt-4 flex items-center gap-4 text-sm text-zinc-500">
                                        <span className="flex items-center gap-1">
                                            <FileText className="w-3 h-3" />
                                            {result.documents_used} docs used
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Shield className="w-3 h-3" />
                                            {result.retries} compliance retries
                                        </span>
                                    </div>
                                </div>

                                {/* Audit Trail */}
                                <div className="bg-zinc-800 rounded-xl p-6">
                                    <h3 className="font-semibold text-lg mb-4">Audit Trail</h3>
                                    <div className="space-y-3">
                                        {result.audit_trail.map((action, index) => (
                                            <div
                                                key={index}
                                                className={`p-3 rounded-lg border ${action.risk_score > 0.5
                                                    ? 'border-amber-700 bg-amber-900/20'
                                                    : 'border-zinc-700 bg-zinc-900'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-mono text-sm text-purple-400">{action.node}</span>
                                                    <span className={`text-xs px-2 py-0.5 rounded ${action.risk_score > 0.5
                                                        ? 'bg-amber-900/50 text-amber-300'
                                                        : 'bg-zinc-700 text-zinc-400'
                                                        }`}>
                                                        Risk: {(action.risk_score * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                                <p className="text-sm text-zinc-300">{action.thought}</p>
                                                {action.tool_call && (
                                                    <p className="text-xs text-zinc-500 font-mono mt-1">
                                                        → {action.tool_call}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {!result && !error && !isRunning && (
                            <div className="flex flex-col items-center justify-center h-full text-center">
                                <Bot className="w-16 h-16 text-zinc-700 mb-4" />
                                <h2 className="text-xl font-medium text-zinc-300 mb-2">
                                    Agentic Research
                                </h2>
                                <p className="text-zinc-500 max-w-md">
                                    Enter a research query. The agent will autonomously search your vault,
                                    grade documents, and generate a compliance-checked answer.
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                {/* MEMORY VIEW */}
                <div className={`absolute inset-0 bg-zinc-900 transition-opacity duration-300 ${activeTab === 'memory' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`}>
                    <MemoryPanel />
                </div>

                {/* TRACES VIEW */}
                <div className={`absolute inset-0 bg-zinc-900 transition-opacity duration-300 ${activeTab === 'traces' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`}>
                    <TracePanel />
                </div>

                {/* COMPLIANCE VIEW */}
                <div className={`absolute inset-0 bg-zinc-900 transition-opacity duration-300 ${activeTab === 'compliance' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'}`}>
                    <CompliancePanel />
                </div>

            </div>
        </div>
    );
}
