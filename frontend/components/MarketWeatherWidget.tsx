"use client";

import { InfoButton } from "./ScoreExplainPanel";

interface MarketWeatherWidgetProps {
    gasScore: number;
    onExplain?: () => void;
}

export default function MarketWeatherWidget({
    gasScore,
    onExplain,
}: MarketWeatherWidgetProps) {
    let weatherLabel = "Unknown";
    let weatherColor = "text-slate-400";
    let weatherBg = "bg-slate-900 border-slate-800";
    let description = "Insufficient data to determine market weather.";

    if (gasScore >= 80) {
        weatherLabel = "Strong Tailwind";
        weatherColor = "text-emerald-400";
        weatherBg = "bg-emerald-950/30 border-emerald-900/50";
        description = "Conditions are highly supportive across technicals, sentiment, and macro.";
    } else if (gasScore >= 60) {
        weatherLabel = "Mild Support";
        weatherColor = "text-teal-400";
        weatherBg = "bg-teal-950/30 border-teal-900/50";
        description = "Broadly supportive environment, though some crosscurrents exist.";
    } else if (gasScore >= 40) {
        weatherLabel = "Mixed Signals";
        weatherColor = "text-amber-400";
        weatherBg = "bg-amber-950/30 border-amber-900/50";
        description = "No clear directional macro or technical consensus. Sideways trading likely.";
    } else if (gasScore >= 20) {
        weatherLabel = "Headwind";
        weatherColor = "text-orange-400";
        weatherBg = "bg-orange-950/30 border-orange-900/50";
        description = "Challenging environment. Caution warranted as momentum and macro turn negative.";
    } else {
        weatherLabel = "High Instability";
        weatherColor = "text-rose-500";
        weatherBg = "bg-rose-950/30 border-rose-900/50";
        description = "Extremely hostile conditions. Cash or aggressive hedging often preferred.";
    }

    return (
        <div className={`p-6 rounded-2xl border ${weatherBg} flex flex-col items-center justify-center text-center space-y-3`}>
            <div className="flex items-baseline space-x-3">
                <span className={`text-6xl font-black tracking-tighter ${weatherColor}`}>
                    {gasScore.toFixed(0)}
                </span>
                <span className="text-xl font-bold text-slate-500">GAS</span>
                {onExplain && (
                    <InfoButton onClick={onExplain} label="GAS Score" />
                )}
            </div>

            <div className="space-y-1">
                <h3 className={`text-2xl font-bold tracking-tight ${weatherColor}`}>
                    {weatherLabel}
                </h3>
                <p className="text-sm text-slate-400 max-w-sm mx-auto">
                    {description}
                </p>
            </div>
        </div>
    );
}
