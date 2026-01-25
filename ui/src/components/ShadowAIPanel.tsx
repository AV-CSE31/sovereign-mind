'use client';

import { useState, useEffect } from 'react';
import { Radar, AlertTriangle, Shield, RefreshCw, Check } from 'lucide-react';

interface ShadowRisk {
    process_name: string;
    port: number;
    host: string;
    risk_level: string;
    detected_at: string;
    description: string;
}

interface ScanReport {
    last_scan: string | null;
    total_risks: number;
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
    risks: ShadowRisk[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function ShadowAIPanel() {
    const [report, setReport] = useState<ScanReport | null>(null);
    const [isScanning, setIsScanning] = useState(false);

    const runScan = async () => {
        setIsScanning(true);
        try {
            const response = await fetch(`${API_BASE}/v1/system/shadow-scan`);
            if (response.ok) {
                const data = await response.json();
                setReport(data);
            }
        } catch (err) {
            console.error('Failed to scan:', err);
        } finally {
            setIsScanning(false);
        }
    };

    useEffect(() => {
        runScan();
    }, []);

    const getRiskColor = (level: string) => {
        switch (level) {
            case 'high': return 'text-red-400 bg-red-900/30';
            case 'medium': return 'text-amber-400 bg-amber-900/30';
            default: return 'text-blue-400 bg-blue-900/30';
        }
    };

    return (
        <div className="bg-zinc-800 rounded-xl p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Radar className="w-5 h-5 text-purple-400" />
                    <h3 className="font-semibold">Shadow AI Scanner</h3>
                </div>
                <button
                    onClick={runScan}
                    disabled={isScanning}
                    className="px-3 py-1 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm flex items-center gap-2"
                >
                    <RefreshCw className={`w-3 h-3 ${isScanning ? 'animate-spin' : ''}`} />
                    {isScanning ? 'Scanning...' : 'Scan Now'}
                </button>
            </div>

            {/* Status */}
            {report && (
                <>
                    {report.total_risks === 0 ? (
                        <div className="flex items-center gap-3 p-4 bg-emerald-900/30 border border-emerald-700 rounded-lg">
                            <Check className="w-6 h-6 text-emerald-400" />
                            <div>
                                <p className="font-medium text-emerald-300">All Clear</p>
                                <p className="text-sm text-zinc-400">No unauthorized AI processes detected</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <div className="flex items-center gap-3 p-3 bg-amber-900/30 border border-amber-700 rounded-lg">
                                <AlertTriangle className="w-5 h-5 text-amber-400" />
                                <p className="text-amber-300">
                                    {report.total_risks} potential risk{report.total_risks !== 1 ? 's' : ''} detected
                                </p>
                            </div>

                            {/* Risk List */}
                            <div className="space-y-2">
                                {report.risks.map((risk, index) => (
                                    <div
                                        key={index}
                                        className="p-3 bg-zinc-900 border border-zinc-700 rounded-lg"
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-medium">{risk.process_name}</span>
                                            <span className={`px-2 py-0.5 rounded text-xs ${getRiskColor(risk.risk_level)}`}>
                                                {risk.risk_level.toUpperCase()}
                                            </span>
                                        </div>
                                        <p className="text-sm text-zinc-400">
                                            Port {risk.port} on {risk.host}
                                        </p>
                                        <p className="text-xs text-zinc-500 mt-1">{risk.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {report.last_scan && (
                        <p className="text-xs text-zinc-500 mt-3">
                            Last scan: {new Date(report.last_scan).toLocaleString()}
                        </p>
                    )}
                </>
            )}
        </div>
    );
}
