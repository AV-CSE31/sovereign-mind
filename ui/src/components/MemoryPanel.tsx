'use client';

import { useState, useEffect } from 'react';
import { Brain, RefreshCw, User } from 'lucide-react';
import { api } from '@/lib/api';

export function MemoryPanel() {
    const [memory, setMemory] = useState<string>('');
    const [isLoading, setIsLoading] = useState(false);
    const userId = "default_user"; // Configurable in future

    const fetchMemory = async () => {
        setIsLoading(true);
        try {
            const data = await api.getMemory(userId);
            setMemory(data.profile);
        } catch (error) {
            console.error('Failed to fetch memory:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchMemory();
    }, []);

    // Helper to format the raw text with bullets if not already
    const formattedMemory = memory.split('\n').filter(line => line.trim()).map((line, i) => (
        <div key={i} className="flex gap-2 items-start p-2 bg-zinc-800/50 rounded-lg border border-zinc-700/50">
            <div className="mt-1 w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
            <p className="text-sm text-zinc-300 leading-relaxed">{line.replace(/^-\s*/, '')}</p>
        </div>
    ));

    return (
        <div className="flex flex-col h-full bg-zinc-900 overflow-hidden">
            <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-900/30 rounded-lg">
                        <Brain className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-zinc-100">Episodic Memory</h2>
                        <p className="text-xs text-zinc-500">Long-term facts learned about you</p>
                    </div>
                </div>
                <button
                    onClick={fetchMemory}
                    disabled={isLoading}
                    className="p-2 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-400 hover:text-white"
                    title="Refresh Memory"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
                {memory ? (
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 mb-4">
                            <User className="w-4 h-4 text-zinc-500" />
                            <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">User Profile: {userId}</span>
                        </div>
                        {formattedMemory}
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-50">
                        <Brain className="w-12 h-12 text-zinc-600 mb-3" />
                        <p className="text-zinc-400">No memories formed yet.</p>
                        <p className="text-xs text-zinc-600 mt-1">Chat with the agent to build your profile.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
