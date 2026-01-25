'use client';

import { useState, useRef } from 'react';
import { Upload, FileText, Loader2, Check, AlertCircle } from 'lucide-react';
import { api, IngestResponse } from '@/lib/api';
import { useApp } from '@/lib/context';

export function DocumentsPanel() {
    const { refreshHealth } = useApp();
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [textContent, setTextContent] = useState('');
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            await uploadFile(files[0]);
        }
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            await uploadFile(files[0]);
        }
    };

    const uploadFile = async (file: File) => {
        setIsUploading(true);
        setResult(null);

        try {
            const response: IngestResponse = await api.ingestFile(file, {
                source: file.name,
                type: 'uploaded',
            });

            setResult({
                success: true,
                message: `Ingested "${file.name}" (${response.chunk_count} chunks)`,
            });
            await refreshHealth();
        } catch (error) {
            setResult({
                success: false,
                message: `Failed to ingest: ${error instanceof Error ? error.message : 'Unknown error'}`,
            });
        } finally {
            setIsUploading(false);
        }
    };

    const handleTextIngest = async () => {
        if (!textContent.trim()) return;

        setIsUploading(true);
        setResult(null);

        try {
            const response: IngestResponse = await api.ingestDocument(textContent, {
                source: 'manual-input',
                type: 'text',
            });

            setResult({
                success: true,
                message: `Ingested text (${response.chunk_count} chunks)`,
            });
            setTextContent('');
            await refreshHealth();
        } catch (error) {
            setResult({
                success: false,
                message: `Failed to ingest: ${error instanceof Error ? error.message : 'Unknown error'}`,
            });
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="flex flex-col h-full p-6">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-400" />
                Document Ingestion
            </h2>

            {/* Drag & Drop Zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${isDragging
                        ? 'border-emerald-500 bg-emerald-900/20'
                        : 'border-zinc-700 hover:border-zinc-600'
                    }`}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    accept=".txt,.pdf,.md"
                    className="hidden"
                />
                <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? 'text-emerald-400' : 'text-zinc-500'}`} />
                <p className="text-zinc-300">
                    {isDragging ? 'Drop file here' : 'Drag & drop or click to upload'}
                </p>
                <p className="text-sm text-zinc-500 mt-1">Supports TXT, PDF, Markdown</p>
            </div>

            {/* Divider */}
            <div className="flex items-center my-6">
                <div className="flex-1 border-t border-zinc-800" />
                <span className="px-4 text-sm text-zinc-500">or paste text</span>
                <div className="flex-1 border-t border-zinc-800" />
            </div>

            {/* Text Input */}
            <div className="flex-1 flex flex-col">
                <textarea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Paste text content to ingest into RAG..."
                    className="flex-1 min-h-[200px] px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 resize-none"
                />

                <button
                    onClick={handleTextIngest}
                    disabled={isUploading || !textContent.trim()}
                    className="mt-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-xl font-medium transition-colors flex items-center justify-center gap-2"
                >
                    {isUploading ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Ingesting...
                        </>
                    ) : (
                        <>
                            <FileText className="w-4 h-4" />
                            Ingest Text
                        </>
                    )}
                </button>
            </div>

            {/* Result Message */}
            {result && (
                <div className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${result.success ? 'bg-emerald-900/30 text-emerald-300' : 'bg-red-900/30 text-red-300'
                    }`}>
                    {result.success ? <Check className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                    {result.message}
                </div>
            )}
        </div>
    );
}
