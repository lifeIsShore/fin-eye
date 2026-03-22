"use client";

/**
 * RegimeWidget.tsx
 *
 * Sprint 9 (UX-EDU-01): Added ScoreTooltip on both regime tiles.
 */

import { InfoButton } from "./ScoreExplainPanel";
import { ScoreTooltip } from "./Tooltip";

interface RegimeWidgetProps {
    technicalScore: number;
    vixLevel: number | null;
    /**
     * When provided, overrides the client-derived regime label with the
     * server-computed value from the GAS snapshot (EXP-PERF-01).
     */
    regime?: string;
    regimeOverride?: string;
    macroScore?: number;
    onExplainTechnical?: () => void;
    onExplainVolatility?: () => void;
}

export default function RegimeWidget({
    technicalScore,
    vixLevel,
    regime,
    regimeOverride,
    onExplainTechnical,
    onExplainVolatility,
}: RegimeWidgetProps) {
    // Derive regime locally as fallback; prefer the server value when present.
    let derivedRegime = "Range-Bound";
    if (technicalScore >= 60) derivedRegime = "Risk-On";
    else if (technicalScore <= 40) derivedRegime = "Risk-Off";

    const technicalRegime = regime ?? regimeOverride ?? derivedRegime;

    let techColor = "text-amber-400 bg-amber-950/40 border-amber-900/50";
    if (technicalRegime === "Risk-On")
        techColor = "text-emerald-400 bg-emerald-950/40 border-emerald-900/50";
    else if (technicalRegime === "Risk-Off")
        techColor = "text-rose-400 bg-rose-950/40 border-rose-900/50";

    let volatilityRegime = "Unknown";
    let volColor = "text-slate-400 bg-slate-900 border-slate-800";

    if (vixLevel !== null) {
        if (vixLevel < 15) {
            volatilityRegime = "Low Volatility";
            volColor = "text-sky-400 bg-sky-950/40 border-sky-900/50";
        } else if (vixLevel <= 25) {
            volatilityRegime = "Medium Volatility";
            volColor = "text-amber-400 bg-amber-950/40 border-amber-900/50";
        } else {
            volatilityRegime = "High Volatility";
            volColor = "text-rose-400 bg-rose-950/40 border-rose-900/50";
        }
    }

    return (
        <div className="flex flex-col sm:flex-row gap-3 mt-4">
            {/* ── Technical Regime ── */}
            <div className={`flex-1 p-4 rounded-xl border ${techColor} flex flex-col justify-center`}>
                <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold uppercase tracking-wider opacity-70">
                            Technical Regime
                        </span>
                        <ScoreTooltip
                            label="Technical Regime"
                            description="Derived from the Sharpe-weighted average of ML model signals across all timeframes. Risk-On means the majority of timeframes are bullish; Risk-Off means bearish; Transitional means mixed."
                            range="Risk-On · Transitional · Risk-Off"
                            side="bottom"
                            size="xs"
                        />
                    </div>
                    {onExplainTechnical && (
                        <InfoButton onClick={onExplainTechnical} label="Technical Regime" />
                    )}
                </div>
                <span className="text-xl font-bold">{technicalRegime}</span>
            </div>

            {/* ── Volatility Regime ── */}
            <div className={`flex-1 p-4 rounded-xl border ${volColor} flex flex-col justify-center`}>
                <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold uppercase tracking-wider opacity-70">
                            Volatility Regime
                        </span>
                        <ScoreTooltip
                            label="Volatility Regime"
                            description="Derived from the CBOE VIX index — the market's implied 30-day volatility expectation. Low VIX (<15) = calm markets. High VIX (>25) = elevated fear and wider swings."
                            range="Low (<15) · Medium (15–25) · High (>25)"
                            source="CBOE VIX via FRED"
                            side="bottom"
                            size="xs"
                        />
                    </div>
                    {onExplainVolatility && (
                        <InfoButton onClick={onExplainVolatility} label="Volatility Regime" />
                    )}
                </div>
                <span className="text-xl font-bold">{volatilityRegime}</span>
                {vixLevel !== null && (
                    <span className="text-xs opacity-60 mt-1">VIX: {vixLevel.toFixed(2)}</span>
                )}
            </div>
        </div>
    );
}
