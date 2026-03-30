"use client";

import { useState } from "react";
import Link from "next/link";
import { TechnicalSignalDto } from "../lib/api";
import ModelDetailsPanel from "./ModelDetailsPanel";
import {
    X, TrendingUp, TrendingDown, Minus,
    Info, ChevronRight, ExternalLink,
} from "lucide-react";
import {
    interpretConfidence as interpretConfidenceUtil,
    directionConfig as directionConfigUtil,
    buildAgreementSummary,
    type ConfidenceInfo,
    type DirectionConfig,
} from "../lib/signalUtils";

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

// ── Local wrappers — add JSX icon onto the shared util config ────────────────

function interpretConfidence(conf: number): ConfidenceInfo {
    return interpretConfidenceUtil(conf);
}

function directionConfig(direction: string): DirectionConfig & { icon: React.ReactNode } {
    const base = directionConfigUtil(direction);
    const icon =
        base.iconName === "TrendingUp"   ? <TrendingUp   className="h-4 w-4" /> :
        base.iconName === "TrendingDown" ? <TrendingDown className="h-4 w-4" /> :
                                           <Minus        className="h-4 w-4" />;
    return { ...base, icon };
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
    symbol,
    onClose,
    onOpenModelDetails,
}: {
    signal:               TechnicalSignalDto | null;
    symbol?:              string;
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
                                    confInfo.label === "Strong signal" ? "bg-emerald-950/30 border-emerald-800/40" :
                                    confInfo.label === "Moderate signal" ? "bg-sky-950/30 border-sky-800/40" :
                                    confInfo.label === "Weak signal" || confInfo.label === "Uncertain" ? "bg-amber-950/30 border-amber-800/40" :
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

                            {/* ⚙ Model Details — Sprint 4 + Sprint 33 (link to deep-dive page) */}
                            <div className="flex flex-col gap-2">
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
                                {symbol && (
                                    <Link
                                        href={`/model-info/${encodeURIComponent(symbol)}`}
                                        onClick={onClose}
                                        className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-700/40 bg-slate-900/40 hover:bg-slate-800/40 px-4 py-2.5 transition-colors group"
                                    >
                                        <ExternalLink className="h-3.5 w-3.5 text-slate-600 group-hover:text-slate-300 transition-colors" />
                                        <span className="text-xs text-slate-500 group-hover:text-slate-300 transition-colors">
                                            Open full model report for {symbol} →
                                        </span>
                                    </Link>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </>
    );
}

// ── Agreement banner (inside the grid component) — Sprint 33 ────────────────

function AgreementBanner({ signals }: { signals: TechnicalSignalDto[] }) {
    if (signals.length < 2) return null;

    const summary = buildAgreementSummary(signals);

    const schemeClasses: Record<typeof summary.scheme, { wrapper: string; text: string; icon: string }> = {
        "emerald-strong": { wrapper: "border-emerald-800/40 bg-emerald-950/15", text: "text-emerald-300",  icon: "🟢" },
        "emerald-mild":   { wrapper: "border-emerald-900/30 bg-emerald-950/10", text: "text-emerald-400",  icon: "🟢" },
        "rose-strong":    { wrapper: "border-rose-800/40 bg-rose-950/15",       text: "text-rose-300",    icon: "🔴" },
        "rose-mild":      { wrapper: "border-rose-900/30 bg-rose-950/10",       text: "text-rose-400",    icon: "🔴" },
        "amber":          { wrapper: "border-amber-800/40 bg-amber-950/15",     text: "text-amber-300",   icon: "🟡" },
    };

    const cls = schemeClasses[summary.scheme];

    return (
        <div className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 ${cls.wrapper}`}>
            <span className="text-base flex-shrink-0">{cls.icon}</span>
            <div className="min-w-0 flex-1">
                <p className={`text-sm font-semibold ${cls.text}`}>{summary.message}</p>
                <p className={`text-xs opacity-70 mt-0.5 ${cls.text}`}>{summary.subText}</p>
            </div>
            {/* Mini per-timeframe bar strip */}
            <div className="flex-shrink-0 hidden sm:flex flex-col items-end gap-0.5">
                <div className="flex gap-0.5 h-2">
                    {signals.map((s, i) => (
                        <div
                            key={i}
                            title={`${s.timeframe}: ${s.direction}`}
                            className={`w-4 rounded-sm ${
                                s.direction === "Bullish" ? "bg-emerald-500" :
                                s.direction === "Bearish" ? "bg-rose-500"    : "bg-amber-400/40"
                            }`}
                        />
                    ))}
                </div>
                <p className="text-[9px] text-slate-600">
                    {summary.bullish}B · {summary.bearish}Be · {summary.neutral}N
                </p>
            </div>
        </div>
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
            {/* Agreement banner — Sprint 33 (inside TimeframeGrid, above tiles) */}
            <AgreementBanner signals={sortedSignals} />

            {/* Signal tiles */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 w-full mt-2">
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
                symbol={symbol}
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
