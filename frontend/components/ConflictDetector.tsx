"use client";

import React from "react";

interface ConflictItem {
    layers: string;
    magnitude: string;
    message: string;
}

interface ConflictDetectorProps {
    hasConflict: boolean;
    conflicts: ConflictItem[];
    conflictSummary: string;
}

export default function ConflictDetector({
    hasConflict,
    conflicts,
    conflictSummary,
}: ConflictDetectorProps) {
    if (!hasConflict) {
        return (
            <div className="rounded-2xl border border-emerald-900/40 bg-emerald-950/20 p-5 flex items-center gap-3">
                <span className="text-emerald-400 text-xl">✅</span>
                <div>
                    <h3 className="text-sm font-semibold text-emerald-300">
                        No Major Conflicts
                    </h3>
                    <p className="text-xs text-emerald-600 mt-0.5">{conflictSummary}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-2xl border border-amber-800/50 bg-amber-950/20 p-5">
            <div className="flex items-center gap-2 mb-3">
                <span className="text-amber-400 text-lg">⚠️</span>
                <h3 className="text-sm font-semibold text-amber-300">
                    Signal Conflict Detected
                </h3>
            </div>

            <p className="text-xs text-amber-500/80 mb-3 leading-relaxed">
                {conflictSummary}
            </p>

            <div className="space-y-3">
                {conflicts.map((conflict, idx) => (
                    <div
                        key={idx}
                        className="rounded-lg bg-amber-900/20 border border-amber-800/30 p-3"
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold text-amber-300 uppercase tracking-wide">
                                {conflict.layers}
                            </span>
                            <span className="text-xs text-amber-500 font-mono">
                                {conflict.magnitude}
                            </span>
                        </div>
                        <p className="text-xs text-amber-200/70 leading-relaxed">
                            {conflict.message}
                        </p>
                    </div>
                ))}
            </div>

            <p className="mt-3 pt-3 border-t border-amber-900/30 text-xs text-amber-600 italic">
                Conflicts indicate uncertainty, not necessarily a bad trade setup. Use this information to size positions conservatively.
            </p>
        </div>
    );
}
