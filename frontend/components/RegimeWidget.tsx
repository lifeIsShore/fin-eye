"use client";

interface RegimeWidgetProps {
    technicalScore: number;
    vixLevel: number | null;
}

export default function RegimeWidget({
    technicalScore,
    vixLevel,
}: RegimeWidgetProps) {
    let technicalRegime = "Range-Bound";
    let techColor = "text-amber-400 bg-amber-950/40 border-amber-900/50";

    if (technicalScore >= 60) {
        technicalRegime = "Risk-On";
        techColor = "text-emerald-400 bg-emerald-950/40 border-emerald-900/50";
    } else if (technicalScore <= 40) {
        technicalRegime = "Risk-Off";
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
                <span className="text-xs font-semibold uppercase tracking-wider opacity-70 mb-1">
                    Technical Regime
                </span>
                <span className="text-xl font-bold">{technicalRegime}</span>
            </div>

            <div
                className={`flex-1 p-4 rounded-xl border ${volColor} flex flex-col justify-center`}
            >
                <span className="text-xs font-semibold uppercase tracking-wider opacity-70 mb-1">
                    Volatility Regime
                </span>
                <span className="text-xl font-bold">{volatilityRegime}</span>
                {vixLevel !== null && (
                    <span className="text-xs opacity-60 mt-1">VIX: {vixLevel.toFixed(2)}</span>
                )}
            </div>
        </div>
    );
}
