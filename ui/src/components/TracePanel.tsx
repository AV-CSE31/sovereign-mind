'use client';

import { useState, useEffect } from 'react';
import { Activity, RefreshCw, Clock, ArrowRight, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/lib/api';

interface TraceLog {
    trace_id: string;
    span_id: string;
    name: string;
    status: string;
    duration_ms: number;
    inputs: any;
    outputs: any;
    error?: string;
}

export function TracePanel() {
    const [traces, setTraces] = useState<TraceLog[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedTrace, setSelectedTrace] = useState<TraceLog | null>(null);

    const fetchTraces = async () => {
        setIsLoading(true);
        try {
            const data = await api.getTraces(100);
            setTraces(data.traces);
        } catch (error) {
            console.error('Failed to fetch traces:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchTraces();
        const interval = setInterval(fetchTraces, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex h-full bg-zinc-900 text-zinc-300 font-mono text-sm overflow-hidden">
            {/* List */}
            <div className="w-1/3 border-r border-zinc-800 flex flex-col">
                <div className="px-4 py-3 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/80 backdrop-blur">
                    <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-purple-400" />
                        <span className="font-semibold text-zinc-100">Live Traces</span>
                    </div>
                    <button onClick={fetchTraces} className="hover:text-white">
                        <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                    {traces.map((trace, i) => (
                        <div
                            key={i}
                            onClick={() => setSelectedTrace(trace)}
                            className={`p-3 border-b border-zinc-800 cursor-pointer hover:bg-zinc-800/50 transition-colors ${selectedTrace === trace ? 'bg-zinc-800 border-l-2 border-l-purple-500' : ''}`}
                        >
                            <div className="flex justify-between items-start mb-1">
                                <span className="font-semibold text-purple-300 truncate">{trace.name}</span>
                                <span className={`text-xs px-1.5 py-0.5 rounded ${trace.status === 'success' ? 'bg-emerald-900/30 text-emerald-400' : 'bg-red-900/30 text-red-400'}`}>
                                    {trace.status}
                                </span>
                            </div>
                            <div className="flex justify-between text-xs text-zinc-500">
                                <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {(trace.duration_ms || 0).toFixed(0)}ms
                                </span>
                                <span className="truncate w-24 text-right text-zinc-600">{trace.trace_id.slice(0, 8)}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Details */}
            <div className="flex-1 flex flex-col bg-zinc-950/50">
                {selectedTrace ? (
                    <div className="flex flex-col h-full">
                        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center">
                            <div>
                                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                    {selectedTrace.name}
                                    {selectedTrace.status === 'success' ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                                </h3>
                                <p className="text-xs text-zinc-500 font-mono">ID: {selectedTrace.span_id}</p>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6 space-y-6">

                            {/* Inputs */}
                            <div className="space-y-2">
                                <span className="text-xs uppercase tracking-wider text-zinc-500 font-bold flex items-center gap-2">
                                    <ArrowRight className="w-3 h-3" /> Input
                                </span>
                                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 overflow-x-auto">
                                    <pre className="text-blue-300 whitespace-pre-wrap">{JSON.stringify(selectedTrace.inputs, null, 2)}</pre>
                                </div>
                            </div>

                            {/* Outputs */}
                            <div className="space-y-2">
                                <span className="text-xs uppercase tracking-wider text-zinc-500 font-bold flex items-center gap-2">
                                    <ArrowRight className="w-3 h-3 transform rotate-180" /> Output
                                </span>
                                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 overflow-x-auto">
                                    {selectedTrace.error ? (
                                        <pre className="text-red-400 whitespace-pre-wrap">{selectedTrace.error}</pre>
                                    ) : (
                                        <pre className="text-emerald-300 whitespace-pre-wrap">{JSON.stringify(selectedTrace.outputs, null, 2)}</pre>
                                    )}
                                </div>
                            </div>

                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full text-zinc-600">
                        <p>Select a trace to view details</p>
                    </div>
                )}
            </div>
        </div>
    );
}
