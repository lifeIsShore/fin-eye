"use client";

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import { fetchHedgeAnalysis, HedgeAnalysisDto } from "../../lib/api";

// ─── Helpers ────────────────────────────────────────────────────────────────

function corrColor(v: number): string {
    if (v >= 0.7) return "text-emerald-400";
    if (v >= 0.3) return "text-sky-400";
    if (v >= -0.3) return "text-slate-400";
    if (v >= -0.7) return "text-amber-400";
    return "text-rose-400";
}

function payoffBar(value: number, max: number): string {
    const pct = Math.min(Math.max((value / max) * 100, 5), 100);
    return `${pct.toFixed(0)}%`;
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function CorrelationPanel({ data }: { data: HedgeAnalysisDto }) {
    const corr = data.correlation.correlations;
    const beta = data.beta;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">
                📊 Beta &amp; Correlation
            </h3>
            <p className="text-xs text-slate-500 mb-4">
                {data.correlation.period} daily returns vs benchmarks
            </p>

            <table className="w-full text-sm">
                <thead>
                    <tr className="text-slate-500 border-b border-slate-800">
                        <th className="text-left py-2 pr-4">Benchmark</th>
                        <th className="text-right py-2">Correlation</th>
                    </tr>
                </thead>
                <tbody>
                    {Object.entries(corr).map(([bm, val]) => (
                        <tr key={bm} className="border-b border-slate-800/50">
                            <td className="py-2 pr-4 font-medium text-slate-300">{bm}</td>
                            <td className={`py-2 text-right font-mono font-semibold ${corrColor(val)}`}>
                                {val >= 0 ? "+" : ""}
                                {val.toFixed(3)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-2 gap-4">
                <div>
                    <p className="text-xs text-slate-500">Beta vs {beta.benchmark}</p>
                    <p className="text-2xl font-black text-sky-400">{beta.beta.toFixed(2)}</p>
                </div>
                <div>
                    <p className="text-xs text-slate-500">R²</p>
                    <p className="text-2xl font-black text-slate-300">
                        {(beta.r_squared * 100).toFixed(1)}%
                    </p>
                </div>
            </div>
        </div>
    );
}

function PayoffPanel({ data }: { data: HedgeAnalysisDto }) {
    const scenarios = data.payoff.scenarios;
    const maxVal = Math.max(...scenarios.map((s) => Math.max(s.unhedged, s.hedged)));

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">📈 Payoff Diagram</h3>
            <p className="text-xs text-slate-500 mb-4">
                Projected portfolio value across market return scenarios
            </p>

            <div className="space-y-2">
                {scenarios.map((s) => (
                    <div key={s.return_pct} className="flex items-center gap-3 text-xs">
                        <span
                            className={`w-12 text-right font-mono font-semibold ${s.return_pct >= 0 ? "text-emerald-400" : "text-rose-400"
                                }`}
                        >
                            {s.return_pct >= 0 ? "+" : ""}
                            {s.return_pct}%
                        </span>

                        {/* Unhedged bar */}
                        <div className="flex-1 flex items-center gap-1">
                            <div
                                className="h-3 rounded-full bg-rose-500/40"
                                style={{ width: payoffBar(s.unhedged, maxVal) }}
                            />
                        </div>

                        {/* Hedged bar */}
                        <div className="flex-1 flex items-center gap-1">
                            <div
                                className="h-3 rounded-full bg-emerald-500/50"
                                style={{ width: payoffBar(s.hedged, maxVal) }}
                            />
                        </div>

                        <span className="w-20 text-right text-slate-500 font-mono">
                            ${s.hedged.toLocaleString()}
                        </span>
                    </div>
                ))}
            </div>

            <div className="flex gap-6 mt-4 pt-3 border-t border-slate-800 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-rose-500/40 inline-block" /> Unhedged
                </span>
                <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-emerald-500/50 inline-block" /> Hedged
                </span>
            </div>
        </div>
    );
}

function HedgeRatioPanel({ data }: { data: HedgeAnalysisDto }) {
    const ratio = data.hedge_ratio;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">⚖️ Hedge Ratio</h3>
            <p className="text-xs text-slate-500 mb-4">
                Beta-adjusted position to neutralise market exposure
            </p>

            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Hedge Units</p>
                    <p className="text-3xl font-black text-sky-400">{ratio.hedge_units}</p>
                    <p className="text-xs text-slate-500 mt-1">shares / contracts</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Notional Value</p>
                    <p className="text-3xl font-black text-slate-200">
                        ${ratio.notional.toLocaleString()}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">hedge exposure</p>
                </div>
            </div>
        </div>
    );
}

function CostPanel({ data }: { data: HedgeAnalysisDto }) {
    const cost = data.cost;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">💲 Hedge Cost Estimate</h3>
            <p className="text-xs text-slate-500 mb-4">{cost.description}</p>

            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Annual Cost %</p>
                    <p className="text-3xl font-black text-amber-400">{cost.annual_cost_pct}%</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Annual Cost USD</p>
                    <p className="text-3xl font-black text-slate-200">
                        ${cost.annual_cost_usd.toLocaleString()}
                    </p>
                </div>
            </div>
        </div>
    );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function HedgePage() {
    const [tickerInput, setTickerInput] = useState("AAPL");
    const [activeSymbol, setActiveSymbol] = useState("AAPL");
    const [hedgeType, setHedgeType] = useState("protective_put");
    const [portfolioValue, setPortfolioValue] = useState(10000);
    const [period, setPeriod] = useState("1y");

    const swrKey = `hedge-${activeSymbol}-${hedgeType}-${portfolioValue}-${period}`;

    const { data, error, isLoading } = useSWR<HedgeAnalysisDto>(
        swrKey,
        () => fetchHedgeAnalysis(activeSymbol, hedgeType, portfolioValue, period),
        { shouldRetryOnError: false, revalidateOnFocus: false },
    );

    const handleAnalyze = useCallback(
        (e: React.FormEvent) => {
            e.preventDefault();
            if (tickerInput.trim()) {
                setActiveSymbol(tickerInput.trim().toUpperCase());
            }
        },
        [tickerInput],
    );

    return (
        <div className="space-y-6">
            {/* ── Header ───────────────────────────────────────────────────────── */}
            <header className="border-b border-slate-800 pb-5">
                <h1 className="text-3xl font-black tracking-tight text-slate-100">
                    Hedging Simulator
                </h1>
                <p className="mt-1 text-sm text-slate-400">
                    Compute beta-adjusted hedges, view payoff diagrams, and estimate costs.
                </p>
            </header>

            {/* ── Configurator ─────────────────────────────────────────────────── */}
            <form
                onSubmit={handleAnalyze}
                className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6"
            >
                <h3 className="text-lg font-bold text-slate-100 mb-4">🛠️ Hedge Configurator</h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Ticker */}
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Ticker</label>
                        <input
                            type="text"
                            value={tickerInput}
                            onChange={(e) => setTickerInput(e.target.value)}
                            placeholder="e.g. AAPL"
                            className="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                        />
                    </div>

                    {/* Hedge Type */}
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Hedge Type</label>
                        <select
                            value={hedgeType}
                            onChange={(e) => setHedgeType(e.target.value)}
                            className="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                        >
                            <option value="protective_put">Protective Put</option>
                            <option value="inverse_etf">Inverse ETF (SH)</option>
                        </select>
                    </div>

                    {/* Portfolio Value */}
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Portfolio Value ($)</label>
                        <input
                            type="number"
                            value={portfolioValue}
                            onChange={(e) => setPortfolioValue(Number(e.target.value))}
                            min={100}
                            max={10000000}
                            className="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                        />
                    </div>

                    {/* Period */}
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Lookback Period</label>
                        <select
                            value={period}
                            onChange={(e) => setPeriod(e.target.value)}
                            className="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                        >
                            <option value="6mo">6 Months</option>
                            <option value="1y">1 Year</option>
                            <option value="2y">2 Years</option>
                            <option value="5y">5 Years</option>
                        </select>
                    </div>
                </div>

                <button
                    type="submit"
                    className="mt-4 rounded-md bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-sky-500 transition-colors"
                >
                    Run Analysis
                </button>
            </form>

            {/* ── Results ──────────────────────────────────────────────────────── */}
            {isLoading && (
                <div className="py-16 text-center animate-pulse text-slate-500">
                    Computing hedge analysis for {activeSymbol}…
                </div>
            )}

            {error && (
                <div className="p-4 rounded-xl border border-rose-800 bg-rose-950/20 text-rose-400 text-sm">
                    ⚠️ {error.message}
                </div>
            )}

            {data && !isLoading && (
                <div className="space-y-6">
                    {/* Row 1 – Correlation + Hedge Ratio */}
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <CorrelationPanel data={data} />
                        <HedgeRatioPanel data={data} />
                    </section>

                    {/* Row 2 – Payoff Diagram + Cost */}
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <PayoffPanel data={data} />
                        <CostPanel data={data} />
                    </section>

                    {/* Disclaimer */}
                    <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-5 py-3 text-xs text-slate-500 italic">
                        {data.disclaimer}
                    </div>
                </div>
            )}
        </div>
    );
}
