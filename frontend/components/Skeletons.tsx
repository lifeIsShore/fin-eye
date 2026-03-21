/**
 * components/Skeletons.tsx
 *
 * todos-v3.md UX-UI-01 — Layout-accurate skeleton loaders for dashboard widgets.
 *
 * All skeletons mirror the real component shapes so the layout doesn't jump
 * when data loads. Uses `animate-pulse` on slate-800 blocks.
 *
 * Exported:
 *   SkeletonGasCard         — GAS score circle + weather + regime + component bars
 *   SkeletonTimeframeGrid   — 5 signal tiles in a row
 *   SkeletonWhyMoving       — 3 bullet-list rows + disclaimer
 *   SkeletonMacroWidget     — macro score bar + 4 indicator rows
 *   SkeletonSentimentCard   — sentiment score + 3 article rows
 *   SkeletonLLMInsight      — 6-section card placeholder
 *   SkeletonPriceTarget     — price range bar + Kelly grid
 *   SkeletonLine            — generic single-line pulse (for inline use)
 *   SkeletonBlock           — generic rect pulse
 */

import React from "react";

// ── Primitives ────────────────────────────────────────────────────────────────

function Pulse({ className }: { className: string }) {
    return <div className={`animate-pulse rounded bg-slate-800 ${className}`} />;
}

export function SkeletonLine({ className = "h-3 w-full" }: { className?: string }) {
    return <Pulse className={className} />;
}

export function SkeletonBlock({ className = "h-16 w-full" }: { className?: string }) {
    return <Pulse className={className} />;
}

// ── GAS Card ──────────────────────────────────────────────────────────────────

export function SkeletonGasCard() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-5">
            {/* Circle */}
            <div className="flex justify-center">
                <Pulse className="h-36 w-36 rounded-full" />
            </div>
            {/* Weather label + regime */}
            <div className="space-y-2">
                <Pulse className="h-5 w-40 mx-auto rounded" />
                <Pulse className="h-3 w-24 mx-auto rounded" />
            </div>
            {/* Component bars */}
            <div className="space-y-3 pt-1">
                {["Technical", "Sentiment", "Macro"].map((l) => (
                    <div key={l} className="space-y-1">
                        <div className="flex justify-between">
                            <Pulse className="h-3 w-20 rounded" />
                            <Pulse className="h-3 w-8 rounded" />
                        </div>
                        <Pulse className="h-2 w-full rounded-full" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Timeframe Grid ────────────────────────────────────────────────────────────

export function SkeletonTimeframeGrid() {
    return (
        <div className="space-y-3">
            {/* Header */}
            <Pulse className="h-5 w-48 rounded" />
            {/* 5 tiles */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
                        <Pulse className="h-3 w-12 rounded" />
                        <Pulse className="h-5 w-20 rounded" />
                        <Pulse className="h-3 w-16 rounded" />
                        <Pulse className="h-2 w-full rounded-full" />
                        <div className="flex justify-between">
                            <Pulse className="h-3 w-10 rounded" />
                            <Pulse className="h-3 w-8 rounded" />
                        </div>
                    </div>
                ))}
            </div>
            {/* Consensus summary */}
            <div className="rounded-lg bg-slate-900/60 border border-slate-800 px-3 py-2.5 space-y-2">
                <Pulse className="h-2 w-full rounded-full" />
                <Pulse className="h-3 w-3/4 rounded" />
            </div>
        </div>
    );
}

// ── Why Moving ────────────────────────────────────────────────────────────────

export function SkeletonWhyMoving() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            {/* Header */}
            <div className="flex items-center gap-2">
                <Pulse className="h-5 w-5 rounded" />
                <Pulse className="h-4 w-40 rounded" />
            </div>
            {/* Bullets */}
            <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="pl-3 border-l-2 border-slate-700 space-y-1">
                        <Pulse className="h-3 w-full rounded" />
                        <Pulse className="h-3 w-4/5 rounded" />
                    </div>
                ))}
            </div>
            {/* Disclaimer */}
            <Pulse className="h-3 w-full rounded mt-2" />
        </div>
    );
}

// ── Macro Widget ──────────────────────────────────────────────────────────────

export function SkeletonMacroWidget() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <Pulse className="h-5 w-32 rounded" />
                <Pulse className="h-6 w-16 rounded-full" />
            </div>
            <Pulse className="h-2 w-full rounded-full" />
            <div className="space-y-3 pt-1">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="flex items-center justify-between">
                        <Pulse className="h-3 w-28 rounded" />
                        <Pulse className="h-4 w-16 rounded" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Sentiment Card ────────────────────────────────────────────────────────────

export function SkeletonSentimentCard() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <Pulse className="h-5 w-40 rounded" />
                <Pulse className="h-6 w-20 rounded-full" />
            </div>
            <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="rounded-lg border border-slate-800 p-3 space-y-1">
                        <Pulse className="h-3 w-3/4 rounded" />
                        <Pulse className="h-3 w-1/2 rounded" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── LLM Insight ───────────────────────────────────────────────────────────────

export function SkeletonLLMInsight() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center gap-2">
                <Pulse className="h-5 w-5 rounded" />
                <Pulse className="h-5 w-48 rounded" />
                <Pulse className="h-5 w-20 rounded-full ml-auto" />
            </div>
            <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="rounded-xl border border-slate-800 p-4 space-y-2">
                        <Pulse className="h-3 w-32 rounded" />
                        <Pulse className="h-3 w-full rounded" />
                        <Pulse className="h-3 w-4/5 rounded" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Price Target Card ─────────────────────────────────────────────────────────

export function SkeletonPriceTarget() {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <Pulse className="h-5 w-36 rounded" />
                <Pulse className="h-5 w-20 rounded" />
            </div>
            {/* Price range bar */}
            <Pulse className="h-8 w-full rounded-xl" />
            {/* Stat grid */}
            <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="rounded-lg border border-slate-800 p-3 space-y-1">
                        <Pulse className="h-3 w-12 rounded" />
                        <Pulse className="h-4 w-16 rounded" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── GAS Sparkline (inline in GAS card) ────────────────────────────────────────

export function SkeletonGasSparkline() {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center">
                <Pulse className="h-3 w-24 rounded" />
                <Pulse className="h-3 w-16 rounded" />
            </div>
            <Pulse className="h-14 w-full rounded-lg" />
        </div>
    );
}
