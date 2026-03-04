"use client";

import { useState } from "react";
import { runBacktest, BacktestRequest, BacktestResponse } from "@/lib/api";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import { AlertTriangle, Info, TrendingUp, TrendingDown, Activity } from "lucide-react";

// ─── Overfitting Warning ────────────────────────────────────────────────────

function OverfittingWarning({ triggered }: { triggered: boolean }) {
    return (
        <div className={`rounded-xl border p-4 ${triggered
            ? "border-red-500/40 bg-red-950/30"
            : "border-amber-500/30 bg-amber-950/20"
            }`}>
            <div className="flex items-start gap-3">
                <AlertTriangle className={`mt-0.5 h-5 w-5 flex-shrink-0 ${triggered ? "text-red-400" : "text-amber-400"}`} />
                <div>
                    <p className={`text-sm font-semibold ${triggered ? "text-red-300" : "text-amber-300"}`}>
                        {triggered
                            ? "⚠ High Overfitting Risk Detected (Sharpe > 1.2)"
                            : "Backtest Disclaimer"}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">
                        Backtests use historical data. Strategies tuned to past performance often <strong className="text-slate-300">fail in live trading</strong>.
                        {triggered && " A Sharpe ratio above 1.2 in-sample is a strong indicator of curve-fitting. "}
                        Expect real-world performance to be roughly 30–50% of backtest results. Always validate with out-of-sample and forward testing.
                        This is for <strong className="text-slate-300">educational purposes only</strong> — not investment advice.
                    </p>
                </div>
            </div>
        </div>
    );
}

// ─── Stat Card ──────────────────────────────────────────────────────────────

function StatCard({
    label,
    value,
    color = "text-slate-100",
    sub,
}: {
    label: string;
    value: string;
    color?: string;
    sub?: string;
}) {
    return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="text-xs text-slate-400">{label}</div>
            <div className={`mt-1 text-2xl font-semibold tracking-tight ${color}`}>{value}</div>
            {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
        </div>
    );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function BacktestingPage() {
    const [symbol, setSymbol] = useState("TSLA");
    const [strategy] = useState("momentum");
    const [initialCapital, setInitialCapital] = useState("10000");
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [smaFast, setSmaFast] = useState("10");
    const [smaSlow, setSmaSlow] = useState("50");
    const [rsiPeriod, setRsiPeriod] = useState("14");
    const [rsiThreshold, setRsiThreshold] = useState("40");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<BacktestResponse | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        const req: BacktestRequest = {
            symbol: symbol.trim().toUpperCase(),
            strategy,
            initial_capital: Number(initialCapital),
            start_date: startDate || undefined,
            end_date: endDate || undefined,
            parameters: {
                sma_fast: Number(smaFast),
                sma_slow: Number(smaSlow),
                rsi_period: Number(rsiPeriod),
                rsi_threshold: Number(rsiThreshold),
            },
        };

        try {
            const data = await runBacktest(req);
            setResult(data);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to run backtest");
        } finally {
            setLoading(false);
        }
    };

    const s = result?.stats;
    const triggered = result?.overfitting_warning ?? false;

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-semibold tracking-tight">Strategy Backtester</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Simulate historical strategy performance — for learning only.
                </p>
            </div>

            {/* Always-visible educational disclaimer */}
            <OverfittingWarning triggered={triggered} />

            <div className="grid gap-6 lg:grid-cols-4">

                {/* ── Sidebar ── */}
                <div className="lg:col-span-1 space-y-5">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                        <h3 className="mb-4 text-sm font-semibold text-slate-300">Configuration</h3>
                        <form onSubmit={handleSubmit} className="space-y-4">

                            <div>
                                <label className="mb-1 block text-xs font-medium text-slate-400">Symbol</label>
                                <input
                                    type="text"
                                    value={symbol}
                                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    placeholder="AAPL"
                                    required
                                />
                            </div>

                            <div>
                                <label className="mb-1 block text-xs font-medium text-slate-400">Strategy</label>
                                <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300">
                                    Momentum (SMA Crossover + RSI)
                                </div>
                            </div>

                            <div>
                                <label className="mb-1 block text-xs font-medium text-slate-400">Initial Capital ($)</label>
                                <input
                                    type="number"
                                    value={initialCapital}
                                    onChange={(e) => setInitialCapital(e.target.value)}
                                    min={100}
                                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="mb-1 block text-xs font-medium text-slate-400">Start Date</label>
                                    <input
                                        type="date"
                                        value={startDate}
                                        onChange={(e) => setStartDate(e.target.value)}
                                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-xs font-medium text-slate-400">End Date</label>
                                    <input
                                        type="date"
                                        value={endDate}
                                        onChange={(e) => setEndDate(e.target.value)}
                                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="border-t border-slate-800 pt-4">
                                <h4 className="mb-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">Parameters</h4>
                                <div className="space-y-3">
                                    <div>
                                        <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                                            SMA Fast
                                            <span title="Short-term moving average period">
                                                <Info className="h-3 w-3 text-slate-600" />
                                            </span>
                                        </label>
                                        <input
                                            type="number"
                                            value={smaFast}
                                            min={2}
                                            onChange={(e) => setSmaFast(e.target.value)}
                                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100"
                                        />
                                    </div>
                                    <div>
                                        <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                                            SMA Slow
                                            <span title="Long-term moving average period">
                                                <Info className="h-3 w-3 text-slate-600" />
                                            </span>
                                        </label>
                                        <input
                                            type="number"
                                            value={smaSlow}
                                            min={3}
                                            onChange={(e) => setSmaSlow(e.target.value)}
                                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100"
                                        />
                                    </div>
                                    <div>
                                        <label className="mb-1 text-xs text-slate-400">RSI Period</label>
                                        <input
                                            type="number"
                                            value={rsiPeriod}
                                            min={2}
                                            onChange={(e) => setRsiPeriod(e.target.value)}
                                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100"
                                        />
                                    </div>
                                    <div>
                                        <label className="mb-1 text-xs text-slate-400">RSI Threshold (Buy when &gt;)</label>
                                        <input
                                            type="number"
                                            value={rsiThreshold}
                                            min={0}
                                            max={100}
                                            onChange={(e) => setRsiThreshold(e.target.value)}
                                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100"
                                        />
                                    </div>
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="mt-2 w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                                        Simulating…
                                    </span>
                                ) : (
                                    "Run Backtest"
                                )}
                            </button>
                        </form>

                        {error && (
                            <div className="mt-4 rounded-lg border border-red-500/30 bg-red-950/30 p-3 text-sm text-red-300">
                                {error}
                            </div>
                        )}
                    </div>

                    {/* Learn more link */}
                    <a
                        href="/learn/backtesting-pitfalls"
                        className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/30 p-4 text-sm text-slate-400 hover:border-slate-700 hover:text-slate-200 transition-colors"
                    >
                        <Activity className="h-4 w-4 text-blue-400" />
                        Learn: Common Backtesting Pitfalls →
                    </a>
                </div>

                {/* ── Results ── */}
                <div className="lg:col-span-3 space-y-5">

                    {/* Empty state */}
                    {!result && !loading && (
                        <div className="flex h-[420px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/30">
                            <TrendingUp className="h-10 w-10 text-slate-600" />
                            <p className="text-sm text-slate-500">Configure the strategy and click Run Backtest</p>
                        </div>
                    )}

                    {/* Loading state */}
                    {loading && (
                        <div className="flex h-[420px] flex-col items-center justify-center gap-3 rounded-xl border border-slate-800 bg-slate-900/50">
                            <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500/30 border-t-blue-500" />
                            <p className="text-sm text-slate-400 animate-pulse">Simulating {symbol} trading history…</p>
                        </div>
                    )}

                    {/* Results */}
                    {result && s && !loading && (
                        <div className="space-y-5">

                            {/* Key metrics grid */}
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                <StatCard
                                    label="Total Return"
                                    value={`${s.total_return_pct >= 0 ? "+" : ""}${s.total_return_pct.toFixed(2)}%`}
                                    color={s.total_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}
                                    sub={`Ann. ${s.annualized_return_pct >= 0 ? "+" : ""}${s.annualized_return_pct.toFixed(1)}%`}
                                />
                                <StatCard
                                    label="Max Drawdown"
                                    value={`${s.max_drawdown_pct.toFixed(2)}%`}
                                    color="text-red-400"
                                    sub={`Recovery: ${s.recovery_factor.toFixed(2)}×`}
                                />
                                <StatCard
                                    label="Sharpe Ratio"
                                    value={s.sharpe_ratio.toFixed(2)}
                                    color={s.sharpe_ratio > 1.2 ? "text-amber-400" : "text-slate-100"}
                                    sub={s.sharpe_ratio > 1.2 ? "⚠ Possible overfit" : undefined}
                                />
                                <StatCard
                                    label="Win Rate"
                                    value={`${s.win_rate_pct.toFixed(1)}%`}
                                    color={s.win_rate_pct >= 50 ? "text-emerald-400" : "text-slate-100"}
                                    sub={`${s.total_trades} trades`}
                                />
                            </div>

                            {/* Equity Curve — Strategy vs Buy & Hold */}
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                                <h3 className="mb-1 text-sm font-semibold text-slate-200">Equity Curve</h3>
                                <p className="mb-4 text-xs text-slate-500">
                                    Strategy (blue) vs Buy &amp; Hold benchmark (slate)
                                </p>
                                <div className="h-[360px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={result.equity_curve} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#475569"
                                                fontSize={11}
                                                tickFormatter={(v) =>
                                                    new Date(v).toLocaleDateString(undefined, {
                                                        month: "short",
                                                        year: "2-digit",
                                                    })
                                                }
                                                interval="preserveStartEnd"
                                            />
                                            <YAxis
                                                stroke="#475569"
                                                fontSize={11}
                                                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                                                domain={["auto", "auto"]}
                                                width={48}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: "#0f172a",
                                                    border: "1px solid #1e293b",
                                                    borderRadius: "0.5rem",
                                                    color: "#f8fafc",
                                                    fontSize: 12,
                                                }}
                                                labelFormatter={(label) =>
                                                    new Date(label).toLocaleDateString(undefined, {
                                                        year: "numeric",
                                                        month: "short",
                                                        day: "numeric",
                                                    })
                                                }
                                                formatter={(value: number, name: string) => [
                                                    `$${value.toLocaleString(undefined, {
                                                        minimumFractionDigits: 0,
                                                        maximumFractionDigits: 0,
                                                    })}`,
                                                    name === "equity" ? "Strategy" : "Buy & Hold",
                                                ]}
                                            />
                                            <Legend
                                                formatter={(value) =>
                                                    value === "equity" ? "Strategy" : "Buy & Hold"
                                                }
                                                wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="equity"
                                                stroke="#3b82f6"
                                                strokeWidth={2}
                                                dot={false}
                                                activeDot={{ r: 4, fill: "#3b82f6" }}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="benchmark_equity"
                                                stroke="#475569"
                                                strokeWidth={1.5}
                                                strokeDasharray="4 2"
                                                dot={false}
                                                activeDot={{ r: 3, fill: "#475569" }}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Secondary metrics row */}
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
                                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                                    <div className="text-xs text-slate-500">Sortino Ratio</div>
                                    <div className="mt-1 font-semibold text-slate-200">{s.sortino_ratio.toFixed(2)}</div>
                                </div>
                                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                                    <div className="text-xs text-slate-500">Profit Factor</div>
                                    <div className="mt-1 font-semibold text-slate-200">
                                        {isFinite(s.profit_factor) ? s.profit_factor.toFixed(2) : "∞"}
                                    </div>
                                </div>
                                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                                    <div className="text-xs text-slate-500">Recovery Factor</div>
                                    <div className="mt-1 font-semibold text-slate-200">{s.recovery_factor.toFixed(2)}×</div>
                                </div>
                                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                                    <div className="text-xs text-slate-500">Total Trades</div>
                                    <div className="mt-1 font-semibold text-slate-200">{s.total_trades}</div>
                                </div>
                            </div>

                            {/* Assumptions */}
                            {result.assumptions_applied && (
                                <p className="text-xs text-slate-500 border-t border-slate-800 pt-3">
                                    <span className="font-medium text-slate-400">Assumptions: </span>
                                    {result.assumptions_applied}
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
