'use client';

import { useApp } from '@/lib/context';
import { Shield, Database, Lock, Unlock, Server } from 'lucide-react';
import { ShadowAIPanel } from './ShadowAIPanel';

export function SettingsPanel() {
    const { health, isVaultUnlocked } = useApp();

    return (
        <div className="flex flex-col h-full p-6 overflow-y-auto">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Server className="w-5 h-5 text-emerald-400" />
                System Status
            </h2>

            <div className="space-y-4">
                {/* API Status */}
                <div className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-zinc-400">API Status</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${health?.status === 'healthy'
                            ? 'bg-emerald-900/50 text-emerald-300'
                            : 'bg-red-900/50 text-red-300'
                            }`}>
                            {health?.status || 'Unknown'}
                        </span>
                    </div>
                    <p className="text-sm text-zinc-500">Version: {health?.version || '2.0'}</p>
                </div>

                {/* Vault Status */}
                <div className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            {isVaultUnlocked ? (
                                <Unlock className="w-4 h-4 text-emerald-400" />
                            ) : (
                                <Lock className="w-4 h-4 text-amber-400" />
                            )}
                            <span className="text-zinc-400">Vault Status</span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${isVaultUnlocked
                            ? 'bg-emerald-900/50 text-emerald-300'
                            : 'bg-amber-900/50 text-amber-300'
                            }`}>
                            {isVaultUnlocked ? 'Unlocked' : 'Locked'}
                        </span>
                    </div>
                    <p className="text-sm text-zinc-500">
                        {isVaultUnlocked
                            ? 'Encrypted sessions are accessible'
                            : 'Enter passphrase to access encrypted sessions'}
                    </p>
                </div>

                {/* RAG Stats */}
                <div className="bg-zinc-800 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Database className="w-4 h-4 text-purple-400" />
                        <span className="text-zinc-400">RAG Knowledge Base</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-3">
                        <div>
                            <p className="text-2xl font-bold text-white">{health?.rag_document_count || 0}</p>
                            <p className="text-sm text-zinc-500">Documents</p>
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-white">
                                <Shield className="w-6 h-6 text-emerald-400 inline" />
                            </p>
                            <p className="text-sm text-zinc-500">Local Only</p>
                        </div>
                    </div>
                </div>

                {/* Shadow AI Scanner */}
                <ShadowAIPanel />

                {/* Security Features */}
                <div className="bg-zinc-800 rounded-xl p-4">
                    <h3 className="text-zinc-300 font-medium mb-3">Security Features</h3>
                    <ul className="space-y-2 text-sm">
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                            AES-256-GCM Encryption
                        </li>
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                            Argon2id Key Derivation
                        </li>
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                            Zero-Knowledge Architecture
                        </li>
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                            Local LLM Processing
                        </li>
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-purple-400 rounded-full" />
                            LangGraph Agent Orchestration
                        </li>
                        <li className="flex items-center gap-2 text-zinc-400">
                            <span className="w-2 h-2 bg-purple-400 rounded-full" />
                            Compliance Audit Trail
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

