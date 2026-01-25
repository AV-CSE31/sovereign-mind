'use client';

import { useState, useEffect } from 'react';
import { Shield, FileText, AlertTriangle, Clock, Download } from 'lucide-react';

interface AuditAction {
    run_id: string;
    node: string;
    thought: string;
    tool_call: string | null;
    risk_score: number;
    timestamp: string;
    witness_signature: string | null;
    hash: string;
}

interface ComplianceReport {
    generated_at: string;
    summary: {
        total_actions: number;
        high_risk_actions: number;
        runs_with_pii: number;
        runs_total: number;
    };
    integrity_verified: boolean;
    recent_actions: AuditAction[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function CompliancePanel() {
    const [report, setReport] = useState<ComplianceReport | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isVerifying, setIsVerifying] = useState(false);
    const [verificationResult, setVerificationResult] = useState<boolean | null>(null);

    useEffect(() => {
        fetchReport();
    }, []);

    const fetchReport = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE}/v1/compliance/report`);
            if (response.ok) {
                const data = await response.json();
                setReport(data);
                setVerificationResult(data.integrity_verified);
            }
        } catch (err) {
            console.error('Failed to fetch compliance report:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const verifyIntegrity = async () => {
        setIsVerifying(true);
        try {
            const response = await fetch(`${API_BASE}/v1/compliance/verify`);
            if (response.ok) {
                const data = await response.json();
                setVerificationResult(data.integrity_verified);
                // Refresh full report to ensure sync
                fetchReport();
            }
        } catch (err) {
            console.error('Verification failed:', err);
        } finally {
            setIsVerifying(false);
        }
    };

    const downloadReport = () => {
        if (!report) return;

        const reportText = `
SOVEREIGN-MIND COMPLIANCE REPORT
Generated: ${new Date(report.generated_at).toLocaleString()}
Integrity Verified: ${verificationResult ? 'YES' : 'NO (TAMPERING DETECTED)'}

SUMMARY
=======
Total Agent Actions: ${report.summary.total_actions}
Total Agent Runs: ${report.summary.runs_total}
High-Risk Actions: ${report.summary.high_risk_actions}
Runs with PII Detected: ${report.summary.runs_with_pii}

RECENT ACTIONS
==============
${report.recent_actions.map(a =>
            `[${a.timestamp}] ${a.node}: ${a.thought} 
             Risk: ${(a.risk_score * 100).toFixed(0)}%
             Signed: ${a.witness_signature ? 'YES' : 'NO'}
             Hash: ${a.hash.substring(0, 8)}...`
        ).join('\n\n')}
    `.trim();

        const blob = new Blob([reportText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance-report-${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (isLoading && !report) {
        return (
            <div className="flex items-center justify-center h-full">
                <p className="text-zinc-500">Loading compliance data...</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Shield className={`w-8 h-8 ${verificationResult ? 'text-emerald-400' : 'text-red-500'}`} />
                        {verificationResult && (
                            <div className="absolute -bottom-1 -right-1 bg-zinc-900 rounded-full border border-black">
                                <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                        )}
                    </div>
                    <div>
                        <h1 className="text-xl font-bold">Compliance Shield</h1>
                        <div className="flex items-center gap-2">
                            <p className="text-sm text-zinc-500">EU AI Act & SOC 2 Reporting</p>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${verificationResult ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
                                {verificationResult ? 'Merkle Verified' : 'Integrity Failed'}
                            </span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={verifyIntegrity}
                        disabled={isVerifying}
                        className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 rounded-lg flex items-center gap-2 text-sm text-zinc-200"
                    >
                        {isVerifying ? <Clock className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                        Verify Now
                    </button>
                    <button
                        onClick={downloadReport}
                        disabled={!report}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 rounded-lg flex items-center gap-2 text-sm"
                    >
                        <Download className="w-4 h-4" />
                        Export
                    </button>
                </div>
            </div>

            {/* Stats Grid */}
            {report && (
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
                        <p className="text-2xl font-bold">{report.summary.total_actions}</p>
                        <p className="text-sm text-zinc-500">Total Actions</p>
                    </div>
                    <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
                        <p className="text-2xl font-bold">{report.summary.runs_total}</p>
                        <p className="text-sm text-zinc-500">Agent Runs</p>
                    </div>
                    <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
                        <p className="text-2xl font-bold text-amber-400">{report.summary.high_risk_actions}</p>
                        <p className="text-sm text-zinc-500">High-Risk Actions</p>
                    </div>
                    <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700/50">
                        <p className="text-2xl font-bold text-red-400">{report.summary.runs_with_pii}</p>
                        <p className="text-sm text-zinc-500">PII Detected</p>
                    </div>
                </div>
            )}

            {/* Recent Actions */}
            <div className="flex-1 overflow-y-auto">
                <h3 className="font-semibold mb-3 flex items-center gap-2 text-zinc-400 uppercase text-xs tracking-wider">
                    <Clock className="w-3 h-3" />
                    Immutable Audit Log
                </h3>

                {report && report.recent_actions.length > 0 ? (
                    <div className="space-y-2">
                        {report.recent_actions.map((action, index) => (
                            <div
                                key={index}
                                className={`p-3 rounded-lg border group relative transition-colors ${action.risk_score > 0.5
                                    ? 'border-amber-700/50 bg-amber-900/10 hover:bg-amber-900/20'
                                    : 'border-zinc-700/50 bg-zinc-800/50 hover:bg-zinc-800'
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-sm text-purple-400">{action.node}</span>
                                        <span className="text-xs text-zinc-500 font-mono">
                                            {new Date(action.timestamp).toLocaleTimeString()}
                                        </span>
                                        {action.witness_signature && (
                                            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-900/30 border border-blue-800/50 text-blue-400 text-[10px]" title="Cryptographically Signed by ZK-Witness">
                                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                                Witnessed
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] font-mono text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" title={`Hash: ${action.hash}`}>
                                            {action.hash?.substring(0, 8)}...
                                        </span>
                                        {action.risk_score > 0.5 && (
                                            <AlertTriangle className="w-4 h-4 text-amber-400" />
                                        )}
                                    </div>
                                </div>
                                <p className="text-sm text-zinc-300 font-medium">{action.thought}</p>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8 text-zinc-500">
                        <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>No actions logged yet. Run an agent query to see the audit trail.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
