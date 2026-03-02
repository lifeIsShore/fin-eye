"use client";

import { TechnicalSignalDto } from "../lib/api";

interface TimeframeGridProps {
    signals: TechnicalSignalDto[];
}

const TILE_ORDER = ["1m", "1h", "4h", "1d", "1w"];

export default function TimeframeGrid({ signals }: TimeframeGridProps) {
    // Sort signals to match the standard defined order
    const sortedSignals = [...signals].sort((a, b) => {
        return TILE_ORDER.indexOf(a.timeframe) - TILE_ORDER.indexOf(b.timeframe);
    });

    return (
        <div className="grid grid-cols-5 gap-2 w-full mt-4">
            {sortedSignals.map((signal) => {
                let bgColor = "bg-slate-800 border-slate-700";
                let textColor = "text-slate-300";

                if (signal.direction === "Bullish") {
                    bgColor = "bg-emerald-950/40 border-emerald-900/50";
                    textColor = "text-emerald-400";
                } else if (signal.direction === "Bearish") {
                    bgColor = "bg-rose-950/40 border-rose-900/50";
                    textColor = "text-rose-400";
                } else if (signal.direction === "Neutral") {
                    bgColor = "bg-amber-950/40 border-amber-900/50";
                    textColor = "text-amber-400";
                }

                return (
                    <div
                        key={signal.timeframe}
                        className={`flex flex-col items-center justify-center p-3 rounded-xl border ${bgColor} transition-colors`}
                    >
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                            {signal.timeframe}
                        </span>
                        <span className={`text-sm font-bold ${textColor}`}>
                            {signal.direction}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-1">
                            {signal.confidence.toFixed(1)}% Conf
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
