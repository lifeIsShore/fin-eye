"use client";

/**
 * components/CryptoFearGreedBadge.tsx
 * Sprint 41 — Crypto Fear & Greed index widget for the dashboard.
 *
 * Shown only when the active symbol is a crypto ticker.
 * Polls GET /api/v1/macro/fear-greed/crypto every 5 min.
 *
 * Design: glassmorphic card with an SVG gauge arc (semi-circle).
 * Colour scale: 0-25 Extreme Fear (rose) → 26-45 Fear (orange) →
 *               46-54 Neutral (amber) → 55-74 Greed (emerald) → 75-100 Extreme Greed (green)
 */

import React, { useMemo } from "react";
import useSWR from "swr";
import { fetchCryptoFearGreed, type FearGreedDto } from "@/lib/api";
import { TrendingDown, TrendingUp, Minus, RefreshCw } from "lucide-react";

// ── Colour helpers ─────────────────────────────────────────────────────────

function scoreColour(score: number): {
  text: string;
  bg: string;
  ring: string;
  arc: string;
} {
  if (score <= 25)
    return {
      text: "text-rose-400",
      bg: "bg-rose-500/15",
      ring: "ring-rose-500/25",
      arc: "#f43f5e",
    };
  if (score <= 45)
    return {
      text: "text-orange-400",
      bg: "bg-orange-500/15",
      ring: "ring-orange-500/25",
      arc: "#f97316",
    };
  if (score <= 54)
    return {
      text: "text-amber-400",
      bg: "bg-amber-500/15",
      ring: "ring-amber-500/25",
      arc: "#f59e0b",
    };
  if (score <= 74)
    return {
      text: "text-emerald-400",
      bg: "bg-emerald-500/15",
      ring: "ring-emerald-500/25",
      arc: "#10b981",
    };
  return {
    text: "text-green-400",
    bg: "bg-green-500/15",
    ring: "ring-green-500/25",
    arc: "#22c55e",
  };
}

function ScoreIcon({ score }: { score: number }) {
  if (score <= 45) return <TrendingDown className="h-3.5 w-3.5" />;
  if (score >= 55) return <TrendingUp className="h-3.5 w-3.5" />;
  return <Minus className="h-3.5 w-3.5" />;
}

// ── SVG gauge arc ─────────────────────────────────────────────────────────────

const GAUGE_R = 38;          // arc radius
const GAUGE_CX = 56;         // centre x (= half of 112px viewBox width)
const GAUGE_CY = 48;         // centre y (shifted up from 56 to crop bottom)

function describeArc(cx: number, cy: number, r: number, angle: number): string {
  // angle is 0–180 degrees (sweep from left to right across top of circle)
  const rad = ((angle - 180) * Math.PI) / 180;
  const x = cx + r * Math.cos(rad);
  const y = cy + r * Math.sin(rad);
  return `M ${cx - r} ${cy} A ${r} ${r} 0 ${angle > 180 ? 1 : 0} 1 ${x.toFixed(2)} ${y.toFixed(2)}`;
}

function GaugeArc({ score, colour }: { score: number; colour: string }) {
  const angle = useMemo(() => (score / 100) * 180, [score]);
  const trackPath = describeArc(GAUGE_CX, GAUGE_CY, GAUGE_R, 180);
  const fillPath  = describeArc(GAUGE_CX, GAUGE_CY, GAUGE_R, Math.max(1, angle));

  return (
    <svg viewBox="0 0 112 56" className="w-full" aria-hidden>
      {/* Track */}
      <path
        d={trackPath}
        fill="none"
        stroke="rgb(51 65 85 / 0.6)"
        strokeWidth={8}
        strokeLinecap="round"
      />
      {/* Filled arc */}
      <path
        d={fillPath}
        fill="none"
        stroke={colour}
        strokeWidth={8}
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 4px ${colour}80)` }}
      />
      {/* Score text */}
      <text
        x={GAUGE_CX}
        y={GAUGE_CY + 10}
        textAnchor="middle"
        className="font-bold"
        fill="white"
        fontSize={22}
        fontFamily="inherit"
      >
        {score}
      </text>
    </svg>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface CryptoFearGreedBadgeProps {
  /** Used only for the aria-label; the data is global (not per-symbol) */
  symbol?: string;
}

export function CryptoFearGreedBadge({ symbol }: CryptoFearGreedBadgeProps) {
  const { data, error, isValidating } = useSWR<FearGreedDto>(
    "crypto-fear-greed",
    () => fetchCryptoFearGreed(),
    { refreshInterval: 5 * 60 * 1000, dedupingInterval: 60_000 },
  );

  // ── Loading state
  if (!data && !error) {
    return (
      <div className="rounded-xl bg-slate-800/50 ring-1 ring-slate-700/40 p-3 animate-pulse">
        <div className="h-3 w-24 bg-slate-700 rounded mb-2" />
        <div className="h-8 w-full bg-slate-700 rounded" />
      </div>
    );
  }

  // ── Error state
  if (error || !data) {
    return (
      <div className="rounded-xl bg-slate-800/40 ring-1 ring-slate-700/30 p-3">
        <p className="text-xs text-slate-500">Crypto F&G unavailable</p>
      </div>
    );
  }

  const { score, label } = data;
  const col = scoreColour(score);

  return (
    <div
      className={`rounded-xl ${col.bg} ring-1 ${col.ring} p-3 min-w-[120px]`}
      aria-label={`Crypto Fear & Greed index: ${score} — ${label}${symbol ? ` for ${symbol}` : ""}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-semibold tracking-wider uppercase text-slate-400">
          Crypto F&G
        </span>
        {isValidating && (
          <RefreshCw className="h-2.5 w-2.5 text-slate-500 animate-spin" />
        )}
      </div>

      {/* Gauge */}
      <GaugeArc score={score} colour={col.arc} />

      {/* Label row */}
      <div className={`flex items-center justify-center gap-1 mt-0.5 ${col.text}`}>
        <ScoreIcon score={score} />
        <span className="text-[11px] font-semibold">{label}</span>
      </div>
    </div>
  );
}

export default CryptoFearGreedBadge;
