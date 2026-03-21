"use client";

import { useState } from "react";
import { TechnicalSignalDto } from "../lib/api";
import ModelDetailsPanel from "./ModelDetailsPanel";
import {
    X, TrendingUp, TrendingDown, Minus,
    Info, ChevronRight,
} from "lucide-react";

interface TimeframeGridProps {
    signals:    TechnicalSignalDto[];
    symbol?:    string;   // needed for ModelDetailsPanel
}

// ── Timeframe metadata ────────────────────────────────────────────────────────

const TIMEFRAME_META: Record<string, {
    label: string;
    horizon: string;
    audience: string;
    description: string;
}> = {
    "1h": {
        label: "1 Hour",
        horizon: "Next 3–12 hours",
        audience: "Day traders & intraday",
        description:
            "Trained on 1-hour candles. Predicts the likely direction over the next 3 candles (≈3 hours). " +
            "Short-horizon signals are noisier by nature — use this as a timing tool, not a standalone signal.",
    },
    "4h": {
        label: "4 Hour",
        horizon: "Next 12–24 hours",
        audience: "Swing traders",
        description:
            "Trained on 4-hour candles resampled from 1h data. Predicts direction over the next 3 bars (≈12 hours). " +
            "Good balance between noise and signal. Preferred timeframe for swing trade entries.",
    },
    "1d": {
        label: "1 Day",
        horizon: "Next 3–5 days",
        audience: "Swing & position traders",
        description:
            "Trained on daily candles from full price history. Predicts direction 3 days forward. " +
            "Daily models typically achieve the most stable Sharpe Ratios — treat this as the anchor signal.",
    },
    "1wk": {
        label: "1 Week",
        horizon: "Next 2–3 weeks",
        audience: "Position & macro traders",
        description:
            "Trained on weekly candles. Predicts direction 2 weeks forward. " +
            "Ideal for understanding the medium-term trend. Low noise, but slow to react to sudden moves.",
    },
    "1mo": {
        label: "1 Month",
        horizon: "Next 1–2 months",
        audience: "Long-term investors",
        description:
            "Trained on monthly candles. Predicts direction 1 month forward. " +
            "The slowest-moving signal — reflects deep structural trends. " +
            "Only available for assets with long enough price history.",
    },
};

const TILE_ORDER = ["1h", "4h", "1d", "1wk", "1mo"];

// ── Confidence interpretation ─────────────────────────────────────────────────

function interpretConfidence(conf: number): {
    label: string;
    description: string;
    color: string;
} {
    if (conf >= 80) return {
        label: "Very High",
        description: "The model is strongly leaning in this direction. All key features are aligned.",
        color: "text-emerald-400",
    };
    if (conf >= 65) return {
        label: "High",
        description: "Most features agree on this direction. A reliable signal but not exceptional.",
        color: "text-sky-400",
    };
    if (conf >= 55) return {
        label: "Moderate",
        description: "Slight majority of features point this way. Treat with caution — confirm with other layers.",
        color: "text-amber-400",
    };
    return {
        label: "Low",
        description: "Features are mixed. The model has a slight lean but this is near-random. Wait for a clearer signal.",
        color: "text-slate-400",
    };
}

// ── Direction UI helpers ──────────────────────────────────────────────────────

function directionConfig(direction: string) {
    if (direction === "Bullish") return {
        icon: <TrendingUp className="h-4 w-4" />,
        tile: "bg-emerald-950/40 border-emerald-800/50 hover:border-emerald-600/60",
        text: "text-emerald-400",
        badge: "bg-emerald-900/50 text-emerald-300 border-emerald-700/40",
        bar: "bg-emerald-500",
        panelBg: "bg-emerald-950/20 border-emerald-800/40",
        label: "Bullish",
        plain: "The model predicts this asset will move UP over the forecast horizon.",
    };
    if (direction === "Bearish") return {
        icon: <TrendingDown className="h-4 w-4" />,
        tile: "bg-rose-950/40 border-rose-800/50 hover:border-rose-600/60",
        text: "text-rose-400",
        badge: "bg-rose-900/50 text-rose-300 border-rose-700/40",
        bar: "bg-rose-500",
        panelBg: "bg-rose-950/20 border-rose-800/40",
        label: "Bearish",
        plain: "The model predicts this asset will move DOWN over the forecast horizon.",
    };
    return {
        icon: <Minus className="h-4 w-4" />,
        tile: "bg-amber-950/30 border-amber-800/40 hover:border-amber-600/50",
        text: "text-amber-400",
        badge: "bg-amber-900/50 text-amber-300 border-amber-700/40",
        bar: "bg-amber-500",
        panelBg: "bg-amber-950/20 border-amber-800/40",
        label: "Neutral",
        plain: "The model sees roughly equal probability of up and down movement.",
    };
}

// ── Consensus summary ─────────────────────────────────────────────────────────

function ConsensusSummary({ signals }: { signals: TechnicalSignalDto[] }) {
    const bullish = signals.filter(s => s.direction === "Bullish").length;
    const bearish = signals.filter(s => s.direction === "Bearish").length;
    const neutral = signals.length - bullish - bearish;
    const total   = signals.length;

    const dominant      = bullish > bearish ? "Bullish" : bearish > bullish ? "Bearish" : "Mixed";
    const dominantCount = Math.max(bullish, bearish);
    const agreement     = total > 0 ? Math.round((dominantCount / total) * 100) : 0;
    const avgConf       = total > 0 ? signals.reduce((s, x) => s + x.confidence, 0) / total : 0;

    let summaryText  = "";
    let summaryColor = "text-slate-400";

    if (dominant === "Mixed") {
        summaryText  = "Signals are split — no clear directional consensus across timeframes.";
        summaryColor = "text-amber-400";
    } else if (agreement >= 80) {
        summaryText  = `Strong ${dominant} consensus — ${dominantCount} of ${total} timeframes agree.`;
        summaryColor = dominant === "Bullish" ? "text-emerald-400" : "text-rose-400";
    } else if (agreement >= 60) {
        summaryText  = `Mild ${dominant} lean — ${dominantCount} of ${total} timeframes agree.`;
        summaryColor = dominant === "Bullish" ? "text-emerald-400" : "text-rose-400";
    } else {
        summaryText  = `Conflicted signals — only ${dominantCount} of ${total} timeframes lean ${dominant.toLowerCase()}.`;
        summaryColor = "text-amber-400";
    }

    return (
        <div className="mt-3 rounded-lg bg-slate-900/60 border border-slate-800 px-3 py-2.5 space-y-2">
            <div className="flex items-center gap-2">
                <div className="flex-1 flex h-2 rounded-full overflow-hidden gap-px bg-slate-800">
                    {signals.map((s, i) => {
                        const cfg = directionConfig(s.direction);
                        return <div key={i} className={`flex-1 ${cfg.bar} opacity-80`} title={`${s.timeframe}: ${s.direction}`} />;
                    })}
                </div>
                <span className="text-[10px] font-mono text-slate-500 flex-shrink-0">{agreement}% agree</span>
            </div>
            <p className={`text-xs ${summaryColor} leading-relaxed`}>{summaryText}</p>
            <div className="flex gap-4 text-[10px] text-slate-500">
                <span className="text-emerald-500">▲ {bullish} bullish</span>
                <span className="text-rose-500">▼ {bearish} bearish</span>
                {neutral > 0 && <span className="text-amber-500">— {neutral} neutral</span>}
                <span className="ml-auto">avg conf {avgConf.toFixed(0)}%</span>
            </div>
        </div>
    );
}

// ── Detail panel (signal slide-over) ─────────────────────────────────────────

function TimeframeDetailPanel({
    signal,
    onClose,
    onOpenModelDetails,
}: {
    signal:               TechnicalSignalDto | null;
    onClose:              () => void;
    onOpenModelDetails:   () => void;
}) {
    const isOpen   = signal !== null;
    const meta     = signal ? (TIMEFRAME_META[signal.timeframe] ?? { label: signal.timeframe, horizon: "Unknown", audience: "All traders", description: "" }) : null;
    const cfg      = signal ? directionConfig(signal.direction) : null;
    const confInfo = signal ? interpretConfidence(signal.confidence) : null;
    const confBarWidth = signal ? Math.min(100, signal.confidence) : 0;

    return (
        <>
            <div
                className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
                    isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
                }`}
                onClick={onClose}
            />
            <div
                role="dialog"
                aria-modal="true"
                className={`fixed top-0 right-0 z-50 h-full w-full sm:max-w-lg lg:max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col transition-transform duration-300 ${
                    isOpen ? "translate-x-0" : "translate-x-full"
                }`}
            >
                {signal && cfg && confInfo && meta && (
                    <>
                        {/* Header */}
                        <div className={`flex items-start justify-between p-6 lg:p-8 border-b border-slate-800 ${cfg.panelBg}`}>
                            <div>
                                <div className="flex items-center gap-2 mb-2">
                                    <span className={cfg.text}>{cfg.icon}</span>
                                    <span className={`text-xs font-bold uppercase tracking-widest ${cfg.text}`}>
                                        {meta.label} Signal
                                    </span>
                                </div>
                                <h2 className="text-3xl lg:text-4xl font-black text-slate-100">{cfg.label}</h2>
                                <p className="text-sm text-slate-400 mt-1">
                                    Forecast horizon: <span className="text-slate-200 font-medium">{meta.horizon}</span>
                                </p>
                            </div>
                            <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-3 mt-1">
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6">

                            {/* Plain English direction */}
                            <div className={`rounded-xl border p-5 ${cfg.panelBg}`}>
                                <div className="flex items-center gap-2 mb-3">
                                    <span className={cfg.text}>{cfg.icon}</span>
                                    <span className={`text-lg font-bold ${cfg.text}`}>{cfg.label}</span>
                                </div>
                                <p className="text-sm lg:text-base text-slate-300 leading-relaxed">{cfg.plain}</p>
                            </div>

                            {/* Confidence */}
                            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Model Confidence</h3>
                                    <span className={`text-2xl font-black ${confInfo.color}`}>{signal.confidence.toFixed(1)}%</span>
                                </div>
                                <div className="space-y-1">
                                    <div className="relative h-3 rounded-full bg-slate-800 overflow-hidden">
                                        <div className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${cfg.bar}`} style={{ width: `${confBarWidth}%` }} />
                                        <div className="absolute inset-y-0 left-1/2 w-px bg-slate-600/80" />
                                    </div>
                                    <div className="flex justify-between text-[10px] text-slate-600">
                                        <span>Random (50%)</span>
                                        <span>Certain (100%)</span>
                                    </div>
                                </div>
                                <div className={`flex items-center gap-2 rounded-lg px-3 py-2 border ${
                                    confInfo.label === "Very High" ? "bg-emerald-950/30 border-emerald-800/40" :
                                    confInfo.label === "High"      ? "bg-sky-950/30 border-sky-800/40" :
                                    confInfo.label === "Moderate"  ? "bg-amber-950/30 border-amber-800/40" :
                                    "bg-slate-800/40 border-slate-700/40"
                                }`}>
                                    <span className={`text-xs font-bold ${confInfo.color}`}>{confInfo.label} Confidence</span>
                                </div>
                                <p className="text-sm text-slate-400 leading-relaxed">{confInfo.description}</p>
                                <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 px-4 py-3">
                                    <p className="text-[11px] font-semibold text-slate-400 mb-1">💡 What does Confidence mean?</p>
                                    <p className="text-[11px] text-slate-500 leading-relaxed">
                                        Confidence is the ML model's probability estimate for this direction.
                                        <strong className="text-slate-400"> 50% = coin flip</strong> (no edge),{" "}
                                        <strong className="text-slate-400">100% = maximum certainty</strong>.
                                        Even at 90%, the model is not always right — markets are inherently uncertain.
                                    </p>
                                </div>
                            </div>

                            {/* Sharpe */}
                            {signal.sharpe_weight != null && (
                                <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-3">
                                    <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Model Quality (Sharpe Ratio)</h3>
                                    <div className="flex items-baseline gap-2">
                                        <span className={`text-2xl font-black ${
                                            signal.sharpe_weight >= 1.5 ? "text-emerald-400" :
                                            signal.sharpe_weight >= 0.5 ? "text-sky-400"     :
                                            signal.sharpe_weight >= 0   ? "text-amber-400"   : "text-rose-400"
                                        }`}>{signal.sharpe_weight.toFixed(2)}</span>
                                        <span className="text-sm text-slate-500">Sharpe</span>
                                    </div>
                                    <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 px-3 py-2.5">
                                        <p className="text-[11px] font-semibold text-slate-400 mb-1">💡 What does Sharpe Ratio mean?</p>
                                        <p className="text-[11px] text-slate-500 leading-relaxed">
                                            Quality score for the model on held-out validation data:<br />
                                            <span className="text-emerald-400 font-medium">≥ 1.5 = Excellent</span> ·{" "}
                                            <span className="text-sky-400 font-medium">0.5–1.5 = Good</span> ·{" "}
                                            <span className="text-amber-400 font-medium">0–0.5 = Weak</span> ·{" "}
                                            <span className="text-rose-400 font-medium">&lt; 0 = Poor</span>
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Timeframe info */}
                            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-5 space-y-4">
                                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">About This Timeframe</h3>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                                        <p className="text-slate-500 mb-0.5">Forecast Window</p>
                                        <p className="text-slate-200 font-semibold">{meta.horizon}</p>
                                    </div>
                                    <div className="rounded-lg bg-slate-800/50 px-3 py-2">
                                        <p className="text-slate-500 mb-0.5">Best For</p>
                                        <p className="text-slate-200 font-semibold">{meta.audience}</p>
                                    </div>
                                </div>
                                <p className="text-sm text-slate-400 leading-relaxed">{meta.description}</p>
                            </div>

                            {/* How to use */}
                            <div className="rounded-xl bg-slate-900/40 border border-slate-700/50 p-5">
                                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">How To Use This Signal</h3>
                                <ul className="space-y-3 text-sm text-slate-400 leading-relaxed">
                                    <li className="flex gap-2">
                                        <ChevronRight className="h-3 w-3 text-sky-500 flex-shrink-0 mt-0.5" />
                                        <span>Don't rely on a single timeframe — check if multiple agree.</span>
                                    </li>
                                    <li className="flex gap-2">
                                        <ChevronRight className="h-3 w-3 text-sky-500 flex-shrink-0 mt-0.5" />
                                        <span>Higher confidence + higher Sharpe = more reliable signal.</span>
                                    </li>
                                    <li className="flex gap-2">
                                        <ChevronRight className="h-3 w-3 text-sky-500 flex-shrink-0 mt-0.5" />
                                        <span>Always confirm with the GAS score, macro environment, and sentiment before acting.</span>
                                    </li>
                                    <li className="flex gap-2">
                                        <ChevronRight className="h-3 w-3 text-amber-500 flex-shrink-0 mt-0.5" />
                                        <span>Educational signal only — not investment advice.</span>
                                    </li>
                                </ul>
                            </div>

                            {/* ⚙ Model Details link — Sprint 4 addition */}
                            <button
                                onClick={() => { onClose(); onOpenModelDetails(); }}
                                className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/60 px-4 py-3 transition-colors group"
                            >
                                <span className="text-sm">⚙</span>
                                <span className="text-xs font-semibold text-slate-400 group-hover:text-slate-200 transition-colors">
                                    View full model details — features, training info &amp; model competition
                                </span>
                                <ChevronRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-slate-300 ml-auto transition-colors" />
                            </button>
                        </div>
                    </>
                )}
            </div>
        </>
    );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function TimeframeGrid({ signals, symbol }: TimeframeGridProps) {
    const [selectedSignal,       setSelectedSignal]       = useState<TechnicalSignalDto | null>(null);
    const [modelDetailsPanelOpen, setModelDetailsPanelOpen] = useState(false);

    const sortedSignals = [...signals].sort((a, b) =>
        TILE_ORDER.indexOf(a.timeframe) - TILE_ORDER.indexOf(b.timeframe)
    );

    return (
        <>
            {/* Signal tiles */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 w-full mt-4">
                {sortedSignals.map((signal) => {
                    const cfg      = directionConfig(signal.direction);
                    const confInfo = interpretConfidence(signal.confidence);
                    const meta     = TIMEFRAME_META[signal.timeframe];

                    return (
                        <button
                            key={signal.timeframe}
                            onClick={() => setSelectedSignal(signal)}
                            className={`group flex flex-col p-4 rounded-2xl border text-left transition-all duration-150 cursor-pointer hover:scale-[1.02] active:scale-[0.98] ${cfg.tile}`}
                            title={`Click to learn more about the ${signal.timeframe} signal`}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                    {meta?.label ?? signal.timeframe}
                                </span>
                                <Info className="h-3.5 w-3.5 text-slate-600 group-hover:text-slate-300 transition-colors" />
                            </div>
                            <div className={`flex items-center gap-2 mb-1 ${cfg.text}`}>
                                {cfg.icon}
                                <span className="text-base font-black">{cfg.label}</span>
                            </div>
                            <p className="text-[11px] text-slate-500 mb-3 leading-tight">{meta?.horizon ?? ""}</p>
                            <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden mb-2">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${cfg.bar}`}
                                    style={{ width: `${Math.min(100, signal.confidence)}%` }}
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <span className={`text-[10px] font-semibold ${confInfo.color}`}>{confInfo.label}</span>
                                <span className="text-xs text-slate-400 font-mono font-bold">{signal.confidence.toFixed(0)}%</span>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Consensus summary */}
            {sortedSignals.length > 1 && <ConsensusSummary signals={sortedSignals} />}

            {/* ⚙ Model Details link (bottom of grid) — Sprint 4 */}
            {symbol && sortedSignals.length > 0 && (
                <button
                    onClick={() => setModelDetailsPanelOpen(true)}
                    className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-600 hover:text-slate-400 transition-colors group"
                >
                    <span>⚙</span>
                    <span className="group-hover:underline">Model details — features, training info &amp; model competition</span>
                </button>
            )}

            {/* Signal detail slide-over */}
            <TimeframeDetailPanel
                signal={selectedSignal}
                onClose={() => setSelectedSignal(null)}
                onOpenModelDetails={() => setModelDetailsPanelOpen(true)}
            />

            {/* Model details panel — Sprint 4 */}
            {symbol && (
                <ModelDetailsPanel
                    symbol={symbol}
                    isOpen={modelDetailsPanelOpen}
                    onClose={() => setModelDetailsPanelOpen(false)}
                />
            )}
        </>
    );
}
