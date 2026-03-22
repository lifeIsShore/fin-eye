"use client";

/**
 * components/ErrorBoundary.tsx
 *
 * todos-v3.md UX-PERF-01 — Per-widget SWR error boundaries.
 *
 * Two exports:
 *
 * 1. ErrorBoundary (class component) — catches JS render errors in children,
 *    shows a contained fallback UI instead of crashing the whole page.
 *
 * 2. SectionError (functional) — shown when an SWR fetch returns an error.
 *    Use alongside the existing isLoading/error pattern for each widget.
 *    Shows the section name + a retry button that calls mutate().
 *
 * Usage (class boundary around a section):
 *   <ErrorBoundary section="Technical Consensus">
 *     <TimeframeGrid signals={signals} symbol={symbol} />
 *   </ErrorBoundary>
 *
 * Usage (SWR error inline):
 *   if (error) return <SectionError section="GAS Score" onRetry={() => mutate()} />;
 */

import React from "react";
import { RefreshCw } from "lucide-react";

// ── SectionError — inline SWR error state ────────────────────────────────────

interface SectionErrorProps {
    section:  string;
    onRetry?: () => void;
    message?: string;
}

export function SectionError({ section, onRetry, message }: SectionErrorProps) {
    return (
        <div className="rounded-2xl border border-rose-800/30 bg-rose-950/20 px-5 py-5 flex items-start gap-4">
            <span className="text-xl flex-shrink-0 mt-0.5">⚠️</span>
            <div className="flex-1 min-w-0 space-y-2">
                <p className="text-sm font-semibold text-rose-300">{section} is unavailable</p>
                <p className="text-xs text-slate-400 leading-relaxed">
                    {message ?? "Failed to load data. This could be a temporary network issue."}
                </p>
                {onRetry && (
                    <button
                        onClick={onRetry}
                        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                    >
                        <RefreshCw className="h-3 w-3" />
                        Try again
                    </button>
                )}
            </div>
        </div>
    );
}

// ── ErrorBoundary — class component for render errors ────────────────────────

interface ErrorBoundaryProps {
    children: React.ReactNode;
    section?: string;
    fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    errorMessage: string;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, errorMessage: "" };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, errorMessage: error.message };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        // In production, send to Sentry here
        console.error(`[ErrorBoundary] ${this.props.section ?? "Section"} crashed:`, error, info);
    }

    reset = () => this.setState({ hasError: false, errorMessage: "" });

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;
            return (
                <div className="rounded-2xl border border-rose-800/30 bg-rose-950/20 px-5 py-5 flex items-start gap-4">
                    <span className="text-xl flex-shrink-0 mt-0.5">💥</span>
                    <div className="flex-1 min-w-0 space-y-2">
                        <p className="text-sm font-semibold text-rose-300">
                            {this.props.section ?? "Section"} encountered an error
                        </p>
                        <p className="text-xs text-slate-500 font-mono leading-relaxed break-all">
                            {this.state.errorMessage}
                        </p>
                        <button
                            onClick={this.reset}
                            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                        >
                            <RefreshCw className="h-3 w-3" />
                            Reset section
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
