'use client';

import { useState } from 'react';
import { Lock, Unlock, Key, Plus, Trash2, MessageSquare } from 'lucide-react';
import { useApp } from '@/lib/context';

export function VaultPanel() {
    const {
        isVaultUnlocked,
        sessions,
        activeSessionId,
        unlockVault,
        lockVault,
        createSession,
        deleteSession,
        setActiveSession,
    } = useApp();

    const [passphrase, setPassphrase] = useState('');
    const [isUnlocking, setIsUnlocking] = useState(false);
    const [error, setError] = useState('');

    const handleUnlock = async () => {
        if (!passphrase.trim()) return;
        setIsUnlocking(true);
        setError('');

        const success = await unlockVault(passphrase);
        if (!success) {
            setError('Failed to unlock vault');
        } else {
            setPassphrase('');
        }
        setIsUnlocking(false);
    };

    const handleNewSession = async () => {
        const session = await createSession();
        if (session) {
            setActiveSession(session.session_id);
        }
    };

    if (!isVaultUnlocked) {
        return (
            <div className="p-4 space-y-4">
                <div className="flex items-center gap-2 text-amber-400">
                    <Lock className="w-5 h-5" />
                    <span className="font-medium">Vault Locked</span>
                </div>

                <p className="text-sm text-zinc-400">
                    Enter passphrase to unlock encrypted sessions
                </p>

                <div className="space-y-2">
                    <div className="relative">
                        <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                        <input
                            type="password"
                            value={passphrase}
                            onChange={(e) => setPassphrase(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleUnlock()}
                            placeholder="Enter passphrase..."
                            className="w-full pl-10 pr-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                        />
                    </div>

                    {error && (
                        <p className="text-sm text-red-400">{error}</p>
                    )}

                    <button
                        onClick={handleUnlock}
                        disabled={isUnlocking || !passphrase.trim()}
                        className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
                    >
                        {isUnlocking ? 'Unlocking...' : 'Unlock Vault'}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-400">
                    <Unlock className="w-5 h-5" />
                    <span className="font-medium">Vault Unlocked</span>
                </div>
                <button
                    onClick={lockVault}
                    className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
                    title="Lock Vault"
                >
                    <Lock className="w-4 h-4 text-zinc-400" />
                </button>
            </div>

            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">Encrypted Sessions</span>
                    <button
                        onClick={handleNewSession}
                        className="p-1 hover:bg-zinc-800 rounded transition-colors"
                        title="New Session"
                    >
                        <Plus className="w-4 h-4 text-zinc-400" />
                    </button>
                </div>

                <div className="space-y-1">
                    {sessions.length === 0 ? (
                        <p className="text-sm text-zinc-500 py-2">No encrypted sessions</p>
                    ) : (
                        sessions.map((session) => (
                            <div
                                key={session.session_id}
                                className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${activeSessionId === session.session_id
                                        ? 'bg-emerald-900/30 border border-emerald-700'
                                        : 'hover:bg-zinc-800'
                                    }`}
                                onClick={() => setActiveSession(session.session_id)}
                            >
                                <div className="flex items-center gap-2 min-w-0">
                                    <MessageSquare className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <span className="text-sm truncate">
                                        {session.session_id.slice(0, 12)}...
                                    </span>
                                    <span className="text-xs text-zinc-500">
                                        ({session.message_count})
                                    </span>
                                </div>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        deleteSession(session.session_id);
                                    }}
                                    className="p-1 hover:bg-zinc-700 rounded opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 className="w-3 h-3 text-zinc-500" />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
