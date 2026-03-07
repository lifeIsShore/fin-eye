"use client";

import { InfoButton } from "./ScoreExplainPanel";

interface RegimeWidgetProps {
    technicalScore: number;
    vixLevel: number | null;
    /**
     * When provided, overrides the client-derived regime label with the
     * server-computed value from the GAS snapshot (EXP-PERF-01).
     */
    regimeOverride?: string;
    onExplainTechnical?: () => void;
    onExplainVolatility?: () => void;
}

export default function RegimeWidget({
    technicalScore,
    vixLevel,
    regimeOverride,
    onExplainTechnical,
    onExplainVolatility,
}: RegimeWidgetProps) {
    // Derive regime locally as fallback; prefer the server value when present.
    let derivedRegime = "Range-Bound";
    if (technicalScore >= 60)      derivedRegime = "Risk-On";
    else if (technicalScore <= 40) derivedRegime = "Risk-Off";

    const technicalRegime = regimeOverride ?? derivedRegime;

    let techColor = "text-amber-400 bg-amber-950/40 border-amber-900/50";
    if (technicalRegime === "Risk-On") {
        techColor = "text-emerald-400 bg-emerald-950/40 border-emerald-900/50";
    } else if (technicalRegime === "Risk-Off") {
        techColor = "text-rose-400 bg-rose-950/40 border-rose-900/50";
    }

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
            <div
                className={`flex-1 p-4 rounded-xl border ${techColor} flex flex-col justify-center`}
            >
                <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold uppercase tracking-wider opacity-70">
                        Technical Regime
                    </span>
                    {onExplainTechnical && (
                        <InfoButton onClick={onExplainTechnical} label="Technical Regime" />
                    )}
                </div>
                <span className="text-xl font-bold">{technicalRegime}</span>
            </div>

            <div
                className={`flex-1 p-4 rounded-xl border ${volColor} flex flex-col justify-center`}
            >
                <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold uppercase tracking-wider opacity-70">
                        Volatility Regime
                    </span>
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
