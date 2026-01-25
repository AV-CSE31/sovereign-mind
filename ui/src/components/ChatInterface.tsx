'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import { Send, Loader2, Shield, Brain, Search, MessageCircle } from 'lucide-react';
import { useApp } from '@/lib/context';
import { api, Message, ChatResponse } from '@/lib/api';

interface ChatMessage extends Message {
    intent?: string;
    isLoading?: boolean;
}

const intentIcons: Record<string, { icon: typeof Brain; color: string; label: string }> = {
    simple_chat: { icon: MessageCircle, color: 'text-blue-400', label: 'Chat' },
    rag_search: { icon: Search, color: 'text-purple-400', label: 'RAG' },
    complex_reasoning: { icon: Brain, color: 'text-amber-400', label: 'Reasoning' },
};

export function ChatInterface() {
    const { activeSessionId, selectedModel, isVaultUnlocked } = useApp();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Load session messages if active session changes
    useEffect(() => {
        if (activeSessionId && isVaultUnlocked) {
            api.getSessionMessages(activeSessionId)
                .then(data => {
                    setMessages(data.messages.map(m => ({ ...m })));
                })
                .catch(console.error);
        } else {
            setMessages([]);
        }
    }, [activeSessionId, isVaultUnlocked]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: ChatMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        // Add loading placeholder
        setMessages(prev => [...prev, { role: 'assistant', content: '', isLoading: true }]);

        try {
            const response: ChatResponse = await api.chat({
                messages: [...messages, userMessage].filter(m => !m.isLoading),
                session_id: activeSessionId || undefined,
                model: selectedModel,
            });

            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response.choices[0]?.message.content || 'No response',
                intent: response.intent,
            };

            setMessages(prev => prev.slice(0, -1).concat(assistantMessage));
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => prev.slice(0, -1).concat({
                role: 'assistant',
                content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
            }));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-emerald-400" />
                    <span className="font-medium">Sovereign-Mind</span>
                    {activeSessionId && (
                        <span className="px-2 py-0.5 text-xs bg-emerald-900/50 text-emerald-300 rounded-full">
                            Encrypted Session
                        </span>
                    )}
                </div>
                <span className="text-sm text-zinc-500">{selectedModel}</span>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <Shield className="w-16 h-16 text-zinc-700 mb-4" />
                        <h2 className="text-xl font-medium text-zinc-300 mb-2">
                            Welcome to Sovereign-Mind
                        </h2>
                        <p className="text-zinc-500 max-w-md">
                            Your private AI assistant with zero-knowledge encryption.
                            {!isVaultUnlocked && ' Unlock the vault for encrypted sessions.'}
                        </p>
                    </div>
                ) : (
                    messages.map((message, index) => (
                        <div
                            key={index}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] rounded-2xl px-4 py-2 ${message.role === 'user'
                                        ? 'bg-emerald-600 text-white'
                                        : 'bg-zinc-800 text-zinc-100'
                                    }`}
                            >
                                {message.isLoading ? (
                                    <div className="flex items-center gap-2">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-zinc-400">Thinking...</span>
                                    </div>
                                ) : (
                                    <>
                                        <p className="whitespace-pre-wrap">{message.content}</p>
                                        {message.intent && message.role === 'assistant' && (
                                            <div className="mt-2 flex items-center gap-1">
                                                {(() => {
                                                    const intentConfig = intentIcons[message.intent] || intentIcons.simple_chat;
                                                    const Icon = intentConfig.icon;
                                                    return (
                                                        <>
                                                            <Icon className={`w-3 h-3 ${intentConfig.color}`} />
                                                            <span className={`text-xs ${intentConfig.color}`}>
                                                                {intentConfig.label}
                                                            </span>
                                                        </>
                                                    );
                                                })()}
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-zinc-800">
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your message..."
                        disabled={isLoading}
                        className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="p-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-xl transition-colors"
                    >
                        {isLoading ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Send className="w-5 h-5" />
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
}
