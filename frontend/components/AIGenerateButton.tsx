"use client";

import React, { useState } from "react";

// BUG-FIX-1: Use the same env-var base URL as every other API call.
// Previously hardcoded to http://localhost:8000 which breaks in any
// non-local deployment (staging, production, Docker, etc.).
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface AIGenerateButtonProps {
    symbol: string;
    techScore: number;
    sentScore?: number | null;
    macroScore: number;
    gasScore: number;
    mlOutput?: string | null;
    initialSummary?: string | null;
}

export default function AIGenerateButton({
    symbol,
    techScore,
    sentScore,
    macroScore,
    gasScore,
    mlOutput,
    initialSummary,
}: AIGenerateButtonProps) {
    const [summary, setSummary] = useState<string | null>(initialSummary || null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const generateSummary = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(
                `${API_BASE_URL}/api/v1/explanation/${symbol}/generate-ai`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        tech_score: techScore,
                        sent_30d: sentScore ?? null,
                        macro_score: macroScore,
                        gas_score: gasScore,
                        ml_output: mlOutput ?? null,
                    }),
                },
            );
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(
                    (data as any)?.detail ?? "Failed to generate AI summary.",
                );
            }
            const data = await res.json();
            setSummary(data.ai_summary);
        } catch (err: unknown) {
            setError(
                err instanceof Error ? err.message : "An unexpected error occurred.",
            );
        } finally {
            setLoading(false);
        }
    };

    if (summary) {
        return (
            <div className="mt-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-400 mb-2">
                    <span className="text-lg">✨</span> Fin-Eye AI Insight
                </h4>
                <p className="text-sm text-slate-300 leading-relaxed">{summary}</p>
            </div>
        );
    }

    return (
        <div className="mt-4 p-4 bg-slate-800/30 rounded-lg border border-slate-700/50 flex flex-col items-center justify-center text-center">
            <h4 className="text-sm font-medium text-slate-300 mb-3">
                Want a deeper dive? Let AI analyze {symbol}.
            </h4>
            <button
                onClick={generateSummary}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors border border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(37,99,235,0.2)]"
            >
                {loading ? (
                    <>
                        <svg
                            className="animate-spin h-4 w-4 text-white"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            />
                        </svg>
                        Generating Insight...
                    </>
                ) : (
                    <>
                        <span className="text-lg">✨</span> Generate AI Insight
                    </>
                )}
            </button>
            {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        </div>
    );
}
