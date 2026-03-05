"use client";

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import {
    fetchHedgeAnalysis,
    fetchAdvancedHedge,
    HedgeAnalysisDto,
    AdvancedHedgeDto,
    AdvHedgeSummaryRow,
} from "../../lib/api";

// ─── Constants ───────────────────────────────────────────────────────────────

const STRATEGY_COLORS: Record<string, string> = {
    unhedged: "#f43f5e",        // rose
    protective_put: "#38bdf8",  // sky
    collar: "#a78bfa",          // violet
    stock_put_etf: "#34d399",   // emerald
};

const STRATEGY_LABELS: Record<string, string> = {
    unhedged: "Unhedged",
    protective_put: "Protective Put",
    collar: "Collar",
    stock_put_etf: "Put + Inverse ETF",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

function fmtPct(v: number, showPlus = true): string {
    const s = v.toFixed(2) + "%";
    return showPlus && v > 0 ? `+${s}` : s;
}

function fmtUsd(v: number): string {
    return "$" + v.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

// ─── MVP sub-components (unchanged) ──────────────────────────────────────────

function CorrelationPanel({ data }: { data: HedgeAnalysisDto }) {
    const corr = data.correlation.correlations;
    const beta = data.beta;
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">📊 Beta &amp; Correlation</h3>
            <p className="text-xs text-slate-500 mb-4">{data.correlation.period} daily returns vs benchmarks</p>
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
                                {val >= 0 ? "+" : ""}{val.toFixed(3)}
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
                    <p className="text-2xl font-black text-slate-300">{(beta.r_squared * 100).toFixed(1)}%</p>
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
            <p className="text-xs text-slate-500 mb-4">Projected portfolio value across market return scenarios</p>
            <div className="space-y-2">
                {scenarios.map((s) => (
                    <div key={s.return_pct} className="flex items-center gap-3 text-xs">
                        <span className={`w-12 text-right font-mono font-semibold ${s.return_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {s.return_pct >= 0 ? "+" : ""}{s.return_pct}%
                        </span>
                        <div className="flex-1 flex items-center gap-1">
                            <div className="h-3 rounded-full bg-rose-500/40" style={{ width: payoffBar(s.unhedged, maxVal) }} />
                        </div>
                        <div className="flex-1 flex items-center gap-1">
                            <div className="h-3 rounded-full bg-emerald-500/50" style={{ width: payoffBar(s.hedged, maxVal) }} />
                        </div>
                        <span className="w-20 text-right text-slate-500 font-mono">${s.hedged.toLocaleString()}</span>
                    </div>
                ))}
            </div>
            <div className="flex gap-6 mt-4 pt-3 border-t border-slate-800 text-xs text-slate-500">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-rose-500/40 inline-block" /> Unhedged</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-emerald-500/50 inline-block" /> Hedged</span>
            </div>
        </div>
    );
}

function HedgeRatioPanel({ data }: { data: HedgeAnalysisDto }) {
    const ratio = data.hedge_ratio;
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">⚖️ Hedge Ratio</h3>
            <p className="text-xs text-slate-500 mb-4">Beta-adjusted position to neutralise market exposure</p>
            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Hedge Units</p>
                    <p className="text-3xl font-black text-sky-400">{ratio.hedge_units}</p>
                    <p className="text-xs text-slate-500 mt-1">shares / contracts</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Notional Value</p>
                    <p className="text-3xl font-black text-slate-200">${ratio.notional.toLocaleString()}</p>
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
                    <p className="text-3xl font-black text-slate-200">${cost.annual_cost_usd.toLocaleString()}</p>
                </div>
            </div>
        </div>
    );
}

// ─── Advanced sub-components ──────────────────────────────────────────────────

function EquityCurvePanel({ data }: { data: AdvancedHedgeDto }) {
    const { equity_curves, strategies, portfolio_value } = data;

    // Build a mini SVG chart — find common date range
    const firstStrategy = strategies[0];
    const baseCurve = equity_curves[firstStrategy] ?? [];
    if (baseCurve.length === 0) return null;

    const N = baseCurve.length;
    const W = 600;
    const H = 220;
    const PAD = { top: 10, right: 10, bottom: 30, left: 56 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;

    // Find global min/max across all strategies
    let globalMin = Infinity;
    let globalMax = -Infinity;
    strategies.forEach((sk) => {
        (equity_curves[sk] ?? []).forEach((pt) => {
            if (pt.value < globalMin) globalMin = pt.value;
            if (pt.value > globalMax) globalMax = pt.value;
        });
    });
    if (globalMin === globalMax) globalMax = globalMin + 1;
    const valueRange = globalMax - globalMin;

    const xScale = (i: number) => (i / (N - 1)) * chartW;
    const yScale = (v: number) => chartH - ((v - globalMin) / valueRange) * chartH;

    // X-axis labels: first, middle, last date
    const xLabels = [0, Math.floor(N / 2), N - 1].map((i) => ({
        x: xScale(i),
        label: baseCurve[i]?.date?.slice(0, 7) ?? "",
    }));

    // Y-axis labels
    const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => ({
        y: chartH - t * chartH,
        label: fmtUsd(globalMin + t * valueRange),
    }));

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">📈 Equity Curves (Backtest)</h3>
            <p className="text-xs text-slate-500 mb-4">
                Simulated portfolio value over {data.period} — {data.symbol}, starting {fmtUsd(portfolio_value)}
            </p>

            {/* SVG chart */}
            <div className="overflow-x-auto">
                <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 320 }}>
                    <g transform={`translate(${PAD.left},${PAD.top})`}>
                        {/* Grid lines */}
                        {yTicks.map((t) => (
                            <line key={t.label} x1={0} y1={t.y} x2={chartW} y2={t.y}
                                stroke="#1e293b" strokeWidth={1} />
                        ))}

                        {/* Curves */}
                        {strategies.map((sk) => {
                            const curve = equity_curves[sk] ?? [];
                            if (curve.length === 0) return null;
                            const pts = curve
                                .map((pt, i) => `${xScale(i)},${yScale(pt.value)}`)
                                .join(" ");
                            return (
                                <polyline
                                    key={sk}
                                    points={pts}
                                    fill="none"
                                    stroke={STRATEGY_COLORS[sk] ?? "#94a3b8"}
                                    strokeWidth={sk === "unhedged" ? 1.5 : 2}
                                    strokeOpacity={0.9}
                                />
                            );
                        })}

                        {/* Y-axis labels */}
                        {yTicks.map((t) => (
                            <text key={t.label} x={-6} y={t.y + 4} textAnchor="end"
                                fontSize={9} fill="#64748b">{t.label}</text>
                        ))}

                        {/* X-axis labels */}
                        {xLabels.map((l) => (
                            <text key={l.label} x={l.x} y={chartH + 18} textAnchor="middle"
                                fontSize={9} fill="#64748b">{l.label}</text>
                        ))}
                    </g>
                </svg>
            </div>

            {/* Legend */}
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
                {strategies.map((sk) => (
                    <span key={sk} className="flex items-center gap-1.5 text-xs text-slate-400">
                        <span className="inline-block w-6 h-0.5 rounded-full"
                            style={{ backgroundColor: STRATEGY_COLORS[sk] ?? "#94a3b8" }} />
                        {STRATEGY_LABELS[sk] ?? sk}
                    </span>
                ))}
            </div>
        </div>
    );
}

function SummaryComparisonTable({ data }: { data: AdvancedHedgeDto }) {
    const { summary } = data;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">⚖️ Strategy Comparison</h3>
            <p className="text-xs text-slate-500 mb-4">
                Performance and cost summary across all strategies over the backtest period
            </p>

            <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[520px]">
                    <thead>
                        <tr className="text-slate-500 text-xs border-b border-slate-800">
                            <th className="text-left py-2 pr-3 font-medium">Strategy</th>
                            <th className="text-right py-2 px-3 font-medium">Total Return</th>
                            <th className="text-right py-2 px-3 font-medium">Max Drawdown</th>
                            <th className="text-right py-2 px-3 font-medium">Annual Cost</th>
                            <th className="text-right py-2 pl-3 font-medium">Annual Cost $</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary.map((row: AdvHedgeSummaryRow) => (
                            <tr key={row.strategy} className="border-b border-slate-800/50">
                                <td className="py-2.5 pr-3">
                                    <div className="flex items-center gap-2">
                                        <span className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                                            style={{ backgroundColor: STRATEGY_COLORS[row.strategy] ?? "#94a3b8" }} />
                                        <span className="font-medium text-slate-200">{row.label}</span>
                                    </div>
                                </td>
                                <td className={`py-2.5 px-3 text-right font-mono font-semibold ${row.total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                    {fmtPct(row.total_return_pct)}
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono text-rose-400">
                                    -{row.max_drawdown_pct.toFixed(2)}%
                                </td>
                                <td className={`py-2.5 px-3 text-right font-mono ${row.annual_cost_pct > 0 ? "text-amber-400" : "text-slate-500"}`}>
                                    {row.annual_cost_pct > 0 ? `${row.annual_cost_pct}%` : "—"}
                                </td>
                                <td className={`py-2.5 pl-3 text-right font-mono ${row.annual_cost_usd > 0 ? "text-amber-400/80" : "text-slate-500"}`}>
                                    {row.annual_cost_usd > 0 ? fmtUsd(row.annual_cost_usd) : "—"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Strategy descriptions */}
            <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
                {data.strategy_definitions.map((def) => (
                    <div key={def.key} className="flex gap-2 text-xs text-slate-500">
                        <span className="inline-block w-2 h-2 rounded-full mt-1 flex-shrink-0"
                            style={{ backgroundColor: STRATEGY_COLORS[def.key] ?? "#94a3b8" }} />
                        <span><span className="text-slate-400 font-medium">{def.label}:</span> {def.description}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ScenarioPayoffGrid({ data }: { data: AdvancedHedgeDto }) {
    const { payoff_comparison, strategies, portfolio_value } = data;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">🎯 Scenario Payoff Comparison</h3>
            <p className="text-xs text-slate-500 mb-4">
                Final portfolio value by market return scenario (starting {fmtUsd(portfolio_value)})
            </p>

            <div className="overflow-x-auto">
                <table className="w-full text-xs min-w-[560px]">
                    <thead>
                        <tr className="text-slate-500 border-b border-slate-800">
                            <th className="text-left py-2 pr-4 font-medium">Market Return</th>
                            {strategies.map((sk) => (
                                <th key={sk} className="text-right py-2 px-2 font-medium">
                                    <span className="flex items-center justify-end gap-1">
                                        <span className="inline-block w-1.5 h-1.5 rounded-full"
                                            style={{ backgroundColor: STRATEGY_COLORS[sk] ?? "#94a3b8" }} />
                                        {STRATEGY_LABELS[sk] ?? sk}
                                    </span>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {payoff_comparison.map((row) => {
                            const isNeg = row.return_pct < 0;
                            return (
                                <tr key={row.return_pct}
                                    className={`border-b border-slate-800/40 ${isNeg ? "bg-rose-950/10" : row.return_pct > 0 ? "bg-emerald-950/10" : ""}`}>
                                    <td className={`py-1.5 pr-4 font-mono font-semibold ${isNeg ? "text-rose-400" : row.return_pct > 0 ? "text-emerald-400" : "text-slate-400"}`}>
                                        {row.return_pct > 0 ? "+" : ""}{row.return_pct}%
                                    </td>
                                    {strategies.map((sk) => {
                                        const val = row[sk];
                                        if (val === undefined) return <td key={sk} className="py-1.5 px-2 text-right text-slate-600">—</td>;
                                        const pnl = val - portfolio_value;
                                        return (
                                            <td key={sk} className={`py-1.5 px-2 text-right font-mono ${pnl >= 0 ? "text-slate-300" : "text-rose-300"}`}>
                                                {fmtUsd(val)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function BetaPanel({ data }: { data: AdvancedHedgeDto }) {
    const b = data.beta;
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-bold text-slate-100 mb-1">📐 Market Sensitivity</h3>
            <p className="text-xs text-slate-500 mb-4">
                {data.symbol} vs {b.benchmark} over {data.period} ({b.data_points} trading days)
            </p>
            <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">Beta</p>
                    <p className="text-3xl font-black text-sky-400">{b.beta.toFixed(2)}</p>
                    <p className="text-xs text-slate-500 mt-1">vs {b.benchmark}</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-800/50">
                    <p className="text-xs text-slate-500 mb-1">R²</p>
                    <p className="text-3xl font-black text-slate-300">{(b.r_squared * 100).toFixed(1)}%</p>
                    <p className="text-xs text-slate-500 mt-1">explained variance</p>
                </div>
            </div>
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

type Tab = "basic" | "advanced";

export default function HedgePage() {
    // ── Shared inputs ─────────────────────────────────────────────────────
    const [tickerInput, setTickerInput] = useState("AAPL");
    const [activeSymbol, setActiveSymbol] = useState("AAPL");
    const [portfolioValue, setPortfolioValue] = useState(10000);
    const [period, setPeriod] = useState("1y");
    const [activeTab, setActiveTab] = useState<Tab>("basic");

    // ── Basic-mode inputs ─────────────────────────────────────────────────
    const [hedgeType, setHedgeType] = useState("protective_put");

    const basicKey = `hedge-${activeSymbol}-${hedgeType}-${portfolioValue}-${period}`;
    const advKey = `hedge-adv-${activeSymbol}-${portfolioValue}-${period}`;

    const { data: basicData, error: basicError, isLoading: basicLoading } = useSWR<HedgeAnalysisDto>(
        activeTab === "basic" ? basicKey : null,
        () => fetchHedgeAnalysis(activeSymbol, hedgeType, portfolioValue, period),
        { shouldRetryOnError: false, revalidateOnFocus: false },
    );

    const { data: advData, error: advError, isLoading: advLoading } = useSWR<AdvancedHedgeDto>(
        activeTab === "advanced" ? advKey : null,
        () => fetchAdvancedHedge(activeSymbol, portfolioValue, period),
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

    const isLoading = activeTab === "basic" ? basicLoading : advLoading;
    const error = activeTab === "basic" ? basicError : advError;

    return (
        <div className="space-y-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <header className="border-b border-slate-800 pb-5">
                <h1 className="text-3xl font-black tracking-tight text-slate-100">Hedging Simulator</h1>
                <p className="mt-1 text-sm text-slate-400">
                    Compute beta-adjusted hedges, compare multi-leg strategies, and explore payoff scenarios.
                </p>
            </header>

            {/* ── Mode Tabs ──────────────────────────────────────────────────── */}
            <div className="flex gap-1 rounded-xl border border-slate-800 bg-slate-900/50 p-1 w-fit">
                {(["basic", "advanced"] as Tab[]).map((t) => (
                    <button
                        key={t}
                        onClick={() => setActiveTab(t)}
                        className={`px-5 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
                            activeTab === t
                                ? "bg-sky-600 text-white"
                                : "text-slate-400 hover:text-slate-200"
                        }`}
                    >
                        {t === "basic" ? "Basic" : "Advanced (Multi-leg)"}
                    </button>
                ))}
            </div>

            {/* ── Configurator ───────────────────────────────────────────────── */}
            <form onSubmit={handleAnalyze} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                <h3 className="text-lg font-bold text-slate-100 mb-4">🛠️ Hedge Configurator</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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

                    {activeTab === "basic" && (
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
                    )}

                    {activeTab === "advanced" && (
                        <div className="flex items-end pb-0.5">
                            <span className="text-xs text-slate-500">
                                All strategies run simultaneously:<br />
                                <span className="text-slate-400">Unhedged · Put · Collar · Put+ETF</span>
                            </span>
                        </div>
                    )}

                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Portfolio Value ($)</label>
                        <input
                            type="number"
                            value={portfolioValue}
                            onChange={(e) => setPortfolioValue(Number(e.target.value))}
                            min={100}
                            max={10000000}
                            className="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                        />
                    </div>

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

            {/* ── Loading / Error ─────────────────────────────────────────────── */}
            {isLoading && (
                <div className="py-16 text-center animate-pulse text-slate-500">
                    Computing hedge analysis for {activeSymbol}…
                </div>
            )}
            {error && (
                <div className="p-4 rounded-xl border border-rose-800 bg-rose-950/20 text-rose-400 text-sm">
                    ⚠️ {(error as Error).message}
                </div>
            )}

            {/* ── Basic Results ─────────────────────────────────────────────── */}
            {activeTab === "basic" && basicData && !basicLoading && (
                <div className="space-y-6">
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <CorrelationPanel data={basicData} />
                        <HedgeRatioPanel data={basicData} />
                    </section>
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <PayoffPanel data={basicData} />
                        <CostPanel data={basicData} />
                    </section>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-5 py-3 text-xs text-slate-500 italic">
                        {basicData.disclaimer}
                    </div>
                </div>
            )}

            {/* ── Advanced Results ──────────────────────────────────────────── */}
            {activeTab === "advanced" && advData && !advLoading && !advData.error && (
                <div className="space-y-6">
                    {/* Equity Curves — full width */}
                    <EquityCurvePanel data={advData} />

                    {/* Summary + Beta side by side */}
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <SummaryComparisonTable data={advData} />
                        <BetaPanel data={advData} />
                    </section>

                    {/* Scenario Payoff Grid — full width */}
                    <ScenarioPayoffGrid data={advData} />

                    <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-5 py-3 text-xs text-slate-500 italic">
                        {advData.disclaimer}
                    </div>
                </div>
            )}

            {activeTab === "advanced" && advData?.error && (
                <div className="p-4 rounded-xl border border-rose-800 bg-rose-950/20 text-rose-400 text-sm">
                    ⚠️ {advData.error}
                </div>
            )}
        </div>
    );
}
