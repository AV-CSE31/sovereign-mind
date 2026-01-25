'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api, HealthResponse, SessionInfo, Model } from '@/lib/api';

interface AppState {
    // Health
    health: HealthResponse | null;
    isLoading: boolean;

    // Vault
    isVaultUnlocked: boolean;
    sessions: SessionInfo[];
    activeSessionId: string | null;

    // Models
    models: Model[];
    selectedModel: string;

    // Actions
    refreshHealth: () => Promise<void>;
    unlockVault: (passphrase: string) => Promise<boolean>;
    lockVault: () => Promise<void>;
    refreshSessions: () => Promise<void>;
    setActiveSession: (sessionId: string | null) => void;
    createSession: () => Promise<SessionInfo | null>;
    deleteSession: (sessionId: string) => Promise<void>;
    setSelectedModel: (modelId: string) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
    const [health, setHealth] = useState<HealthResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isVaultUnlocked, setIsVaultUnlocked] = useState(false);
    const [sessions, setSessions] = useState<SessionInfo[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [models, setModels] = useState<Model[]>([]);
    const [selectedModel, setSelectedModel] = useState('qwen2:0.5b');

    const refreshHealth = useCallback(async () => {
        try {
            const data = await api.getHealth();
            setHealth(data);
            setIsVaultUnlocked(data.vault_unlocked);
        } catch (error) {
            console.error('Failed to fetch health:', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const unlockVault = useCallback(async (passphrase: string): Promise<boolean> => {
        try {
            await api.unlockVault(passphrase);
            setIsVaultUnlocked(true);
            await refreshHealth();
            return true;
        } catch (error) {
            console.error('Failed to unlock vault:', error);
            return false;
        }
    }, [refreshHealth]);

    const lockVault = useCallback(async () => {
        try {
            await api.lockVault();
            setIsVaultUnlocked(false);
            setSessions([]);
            setActiveSessionId(null);
            await refreshHealth();
        } catch (error) {
            console.error('Failed to lock vault:', error);
        }
    }, [refreshHealth]);

    const refreshSessions = useCallback(async () => {
        if (!isVaultUnlocked) return;
        try {
            const data = await api.listSessions();
            setSessions(data.sessions);
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
        }
    }, [isVaultUnlocked]);

    const createSession = useCallback(async (): Promise<SessionInfo | null> => {
        try {
            const session = await api.createSession();
            await refreshSessions();
            return session;
        } catch (error) {
            console.error('Failed to create session:', error);
            return null;
        }
    }, [refreshSessions]);

    const deleteSession = useCallback(async (sessionId: string) => {
        try {
            await api.deleteSession(sessionId);
            if (activeSessionId === sessionId) {
                setActiveSessionId(null);
            }
            await refreshSessions();
        } catch (error) {
            console.error('Failed to delete session:', error);
        }
    }, [activeSessionId, refreshSessions]);

    // Initial load
    React.useEffect(() => {
        refreshHealth();
        api.getModels().then(data => setModels(data.data)).catch(console.error);
    }, [refreshHealth]);

    // Load sessions when vault is unlocked
    React.useEffect(() => {
        if (isVaultUnlocked) {
            refreshSessions();
        }
    }, [isVaultUnlocked, refreshSessions]);

    return (
        <AppContext.Provider
            value={{
                health,
                isLoading,
                isVaultUnlocked,
                sessions,
                activeSessionId,
                models,
                selectedModel,
                refreshHealth,
                unlockVault,
                lockVault,
                refreshSessions,
                setActiveSession: setActiveSessionId,
                createSession,
                deleteSession,
                setSelectedModel,
            }}
        >
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const context = useContext(AppContext);
    if (!context) {
        throw new Error('useApp must be used within AppProvider');
    }
    return context;
}
