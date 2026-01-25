'use client';

import { Shield, Database, Settings, FileText, ChevronDown, Bot, ClipboardCheck } from 'lucide-react';
import { useApp } from '@/lib/context';
import { VaultPanel } from './VaultPanel';

interface SidebarProps {
    activeTab: 'chat' | 'agents' | 'compliance' | 'documents' | 'settings';
    onTabChange: (tab: 'chat' | 'agents' | 'compliance' | 'documents' | 'settings') => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
    const { health, isVaultUnlocked, models, selectedModel, setSelectedModel } = useApp();

    return (
        <div className="w-72 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full">
            {/* Logo */}
            <div className="p-4 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                    <Shield className="w-8 h-8 text-emerald-400" />
                    <div>
                        <h1 className="font-bold text-lg">Sovereign-Mind</h1>
                        <p className="text-xs text-zinc-500">v{health?.version || '2.0'}</p>
                    </div>
                </div>
            </div>

            {/* Model Selector */}
            <div className="p-4 border-b border-zinc-800">
                <label className="text-xs text-zinc-500 block mb-2">Model</label>
                <div className="relative">
                    <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full appearance-none px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm focus:outline-none focus:border-emerald-500"
                    >
                        {models.map((model) => (
                            <option key={model.id} value={model.id}>
                                {model.id}
                            </option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="p-2 border-b border-zinc-800">
                <button
                    onClick={() => onTabChange('chat')}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${activeTab === 'chat' ? 'bg-emerald-900/30 text-emerald-400' : 'hover:bg-zinc-800 text-zinc-300'
                        }`}
                >
                    <Shield className="w-4 h-4" />
                    <span>Chat</span>
                </button>
                <button
                    onClick={() => onTabChange('agents')}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${activeTab === 'agents' ? 'bg-purple-900/30 text-purple-400' : 'hover:bg-zinc-800 text-zinc-300'
                        }`}
                >
                    <Bot className="w-4 h-4" />
                    <span>Agents</span>
                    <span className="ml-auto text-xs px-1.5 py-0.5 bg-purple-900/50 text-purple-300 rounded">NEW</span>
                </button>
                <button
                    onClick={() => onTabChange('compliance')}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${activeTab === 'compliance' ? 'bg-emerald-900/30 text-emerald-400' : 'hover:bg-zinc-800 text-zinc-300'
                        }`}
                >
                    <ClipboardCheck className="w-4 h-4" />
                    <span>Compliance</span>
                </button>
                <button
                    onClick={() => onTabChange('documents')}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${activeTab === 'documents' ? 'bg-emerald-900/30 text-emerald-400' : 'hover:bg-zinc-800 text-zinc-300'
                        }`}
                >
                    <FileText className="w-4 h-4" />
                    <span>Documents</span>
                    {health && (
                        <span className="ml-auto text-xs text-zinc-500">{health.rag_document_count}</span>
                    )}
                </button>
                <button
                    onClick={() => onTabChange('settings')}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${activeTab === 'settings' ? 'bg-emerald-900/30 text-emerald-400' : 'hover:bg-zinc-800 text-zinc-300'
                        }`}
                >
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                </button>
            </div>

            {/* Vault Panel */}
            <div className="flex-1 overflow-y-auto border-b border-zinc-800">
                <VaultPanel />
            </div>

            {/* Status Bar */}
            <div className="p-3 border-t border-zinc-800">
                <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        <span className="text-zinc-500">
                            {health?.status === 'healthy' ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Database className="w-3 h-3 text-zinc-500" />
                        <span className="text-zinc-500">{health?.rag_document_count || 0} docs</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
