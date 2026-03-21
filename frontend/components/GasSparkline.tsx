"use client";

/**
 * components/GasSparkline.tsx
 *
 * todos-v3.md UX-GROWTH-01 — 7-day GAS history sparkline.
 *
 * Renders as a mini SVG line chart below the GAS score showing the last
 * 7 daily snapshots. Each point is the GAS score at the time it was computed.
 *
 * Features:
 *   - Pure SVG — no chart library dependency
 *   - Colour-coded fill: emerald (high), amber (mid), rose (low)
 *   - Hover tooltip showing date + score
 *   - Trend arrow: ↑ (last > first), ↓ (last < first), → (flat)
 *   - Shows skeleton while loading, nothing if only 1 point (can't show trend)
 *   - Graceful empty state if no history
 */

import React, { useState } from "react";
import useSWR from "swr";
import { fetchGasHistory, type GasHistoryPoint } from "../lib/api";
import { SkeletonGasSparkline } from "./Skeletons";

// ── Colour helpers ────────────────────────────────────────────────────────────

function gasColor(score: number): string {
    if (score >= 65) return "#34d399"; // emerald-400
    if (score >= 40) return "#fbbf24"; // amber-400
    return "#f87171";                  // rose-400
}

function gasColorFill(score: number): string {
    if (score >= 65) return "rgba(52,211,153,0.15)";
    if (score >= 40) return "rgba(251,191,36,0.12)";
    return "rgba(248,113,113,0.12)";
}

// ── SVG sparkline ─────────────────────────────────────────────────────────────

interface SparklineProps {
    points: GasHistoryPoint[];
    width?: number;
    height?: number;
}

function Sparkline({ points, width = 260, height = 52 }: SparklineProps) {
    const [hovered, setHovered] = useState<number | null>(null);

    if (points.length < 2) return null;

    const scores = points.map((p) => p.gas_score);
    const minScore = Math.max(0,   Math.min(...scores) - 5);
    const maxScore = Math.min(100, Math.max(...scores) + 5);
    const range = maxScore - minScore || 10;

    const pad = { left: 4, right: 4, top: 6, bottom: 6 };
    const w = width  - pad.left - pad.right;
    const h = height - pad.top  - pad.bottom;

    const x = (i: number) => pad.left + (i / (points.length - 1)) * w;
    const y = (score: number) => pad.top + h - ((score - minScore) / range) * h;

    const pathD = points
        .map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.gas_score).toFixed(1)}`)
        .join(" ");

    const fillD = `${pathD} L ${x(points.length - 1).toFixed(1)} ${(pad.top + h).toFixed(1)} L ${pad.left.toFixed(1)} ${(pad.top + h).toFixed(1)} Z`;

    const lastScore = scores[scores.length - 1];
    const strokeColor = gasColor(lastScore);
    const fillColor   = gasColorFill(lastScore);

    return (
        <div className="relative select-none">
            <svg width={width} height={height} className="overflow-visible">
                {/* Area fill */}
                <path d={fillD} fill={fillColor} />
                {/* Line */}
                <path d={pathD} fill="none" stroke={strokeColor} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
                {/* Dots + hover targets */}
                {points.map((p, i) => (
                    <g key={i}>
                        <circle
                            cx={x(i)} cy={y(p.gas_score)} r={3}
                            fill={i === points.length - 1 ? strokeColor : "transparent"}
                            stroke={hovered === i ? strokeColor : "transparent"}
                            strokeWidth={1.5}
                        />
                        {/* Larger invisible hit target */}
                        <circle
                            cx={x(i)} cy={y(p.gas_score)} r={8}
                            fill="transparent"
                            onMouseEnter={() => setHovered(i)}
                            onMouseLeave={() => setHovered(null)}
                            style={{ cursor: "default" }}
                        />
                        {/* Tooltip */}
                        {hovered === i && (
                            <g>
                                <rect
                                    x={Math.min(x(i) - 26, width - 56)} y={y(p.gas_score) - 28}
                                    width={52} height={20} rx={4}
                                    fill="#1e293b" stroke="#334155" strokeWidth={0.5}
                                />
                                <text
                                    x={Math.min(x(i), width - 30)} y={y(p.gas_score) - 14}
                                    textAnchor="middle"
                                    fontSize={9} fill="#e2e8f0" fontFamily="monospace"
                                >
                                    {p.gas_score.toFixed(0)} · {new Date(p.computed_at).toLocaleDateString("en-DE", { month: "short", day: "2-digit" })}
                                </text>
                            </g>
                        )}
                    </g>
                ))}
            </svg>
        </div>
    );
}

// ── Trend badge ───────────────────────────────────────────────────────────────

function TrendBadge({ first, last }: { first: number; last: number }) {
    const delta = last - first;
    if (Math.abs(delta) < 1) {
        return <span className="text-[10px] text-slate-500">→ flat</span>;
    }
    if (delta > 0) {
        return <span className="text-[10px] text-emerald-400">↑ +{delta.toFixed(0)}</span>;
    }
    return <span className="text-[10px] text-rose-400">↓ {delta.toFixed(0)}</span>;
}

// ── Main component ────────────────────────────────────────────────────────────

interface GasSparklineProps {
    symbol: string;
    /** Number of history points to fetch — default 7 (1-week view) */
    limit?: number;
    /** Width of the SVG canvas in px — default fills container */
    width?: number;
}

export default function GasSparkline({ symbol, limit = 7, width = 260 }: GasSparklineProps) {
    const { data, isLoading } = useSWR(
        symbol ? `gas-history-${symbol}-${limit}` : null,
        () => fetchGasHistory(symbol, limit),
        { revalidateOnFocus: false, shouldRetryOnError: false },
    );

    if (isLoading) return <SkeletonGasSparkline />;
    if (!data || data.length < 2) return null;

    const first = data[0].gas_score;
    const last  = data[data.length - 1].gas_score;

    return (
        <div className="space-y-1.5">
            {/* Header row */}
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    7-day GAS trend
                </span>
                <TrendBadge first={first} last={last} />
            </div>

            {/* Sparkline */}
            <div className="rounded-lg bg-slate-800/20 border border-slate-700/30 px-2 py-1.5 overflow-hidden">
                <Sparkline points={data} width={width} height={52} />
            </div>

            {/* Min / max labels */}
            <div className="flex items-center justify-between px-1">
                <span className="text-[9px] text-slate-600 tabular-nums">
                    {new Date(data[0].computed_at).toLocaleDateString("en-DE", { month: "short", day: "2-digit" })}
                </span>
                <span className="text-[9px] text-slate-600 tabular-nums">
                    {new Date(data[data.length - 1].computed_at).toLocaleDateString("en-DE", { month: "short", day: "2-digit" })}
                </span>
            </div>
        </div>
    );
}
