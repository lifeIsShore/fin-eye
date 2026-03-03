"use client";

import React from "react";

interface WhyMovingPanelProps {
    symbol: string;
    bullets: string[];
    disclaimer: string;
}

export default function WhyMovingPanel({
    symbol,
    bullets,
    disclaimer,
}: WhyMovingPanelProps) {
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
            <div className="flex items-center gap-2 mb-4">
                <span className="text-lg">🔍</span>
                <h3 className="text-sm font-semibold text-slate-100">
                    Why is {symbol} moving?
                </h3>
            </div>

            <ul className="space-y-3">
                {bullets.map((bullet, idx) => (
                    <li
                        key={idx}
                        className="text-sm text-slate-300 leading-relaxed pl-1 border-l-2 border-slate-700 pl-3"
                    >
                        {bullet}
                    </li>
                ))}
            </ul>

            <p className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-500 italic leading-relaxed">
                ⚠️ {disclaimer}
            </p>
        </div>
    );
}
