"use client";

import { useState } from "react";
import { runBacktest, BacktestRequest, BacktestResponse } from "@/lib/api";
import { OverfittingWarning } from "@/components/OverfittingWarning";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

export default function BacktestingPage() {
    const [symbol, setSymbol] = useState("TSLA");
    const [strategy, setStrategy] = useState("momentum");
    const [initialCapital, setInitialCapital] = useState("10000");
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

        const req: BacktestRequest = {
            symbol: symbol.trim().toUpperCase(),
            strategy,
            initial_capital: Number(initialCapital),
            parameters: {
                sma_fast: Number(smaFast),
                sma_slow: Number(smaSlow),
                rsi_period: Number(rsiPeriod),
                rsi_threshold: Number(rsiThreshold)
            }
        };

        try {
            const data = await runBacktest(req);
            setResult(data);
        } catch (err: any) {
            setError(err.message || "Failed to run backtest");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <OverfittingWarning />

            <h2 className="text-xl font-semibold tracking-tight">Strategy Backtester</h2>

            <div className="grid gap-6 md:grid-cols-4">

                {/* Configuration Sidebar */}
                <div className="md:col-span-1 border-r border-slate-800 pr-4">
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-400">
                                Symbol
                            </label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="w-full rounded bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                required
                            />
                        </div>

                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-400">
                                Strategy
                            </label>
                            <select
                                value={strategy}
                                onChange={(e) => setStrategy(e.target.value)}
                                className="w-full rounded bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                                <option value="momentum">Momentum (SMA Crossover + RSI)</option>
                            </select>
                        </div>

                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-400">
                                Initial Capital ($)
                            </label>
                            <input
                                type="number"
                                value={initialCapital}
                                onChange={(e) => setInitialCapital(e.target.value)}
                                className="w-full rounded bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                required
                            />
                        </div>

                        <div className="pt-4 border-t border-slate-800">
                            <h3 className="text-sm font-medium text-slate-300 mb-2">Parameters</h3>
                            <div className="space-y-3">
                                <div>
                                    <label className="mb-1 block text-xs text-slate-400">SMA Fast</label>
                                    <input
                                        type="number"
                                        value={smaFast}
                                        onChange={(e) => setSmaFast(e.target.value)}
                                        className="w-full rounded bg-slate-900 px-2 py-1 text-sm text-slate-100"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-xs text-slate-400">SMA Slow</label>
                                    <input
                                        type="number"
                                        value={smaSlow}
                                        onChange={(e) => setSmaSlow(e.target.value)}
                                        className="w-full rounded bg-slate-900 px-2 py-1 text-sm text-slate-100"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-xs text-slate-400">RSI Period</label>
                                    <input
                                        type="number"
                                        value={rsiPeriod}
                                        onChange={(e) => setRsiPeriod(e.target.value)}
                                        className="w-full rounded bg-slate-900 px-2 py-1 text-sm text-slate-100"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-xs text-slate-400">RSI Threshold (Buy &lt; X)</label>
                                    <input
                                        type="number"
                                        value={rsiThreshold}
                                        onChange={(e) => setRsiThreshold(e.target.value)}
                                        className="w-full rounded bg-slate-900 px-2 py-1 text-sm text-slate-100"
                                    />
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="mt-6 w-full rounded bg-blue-600 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                        >
                            {loading ? "Running..." : "Run Backtest"}
                        </button>
                    </form>

                    {error && (
                        <div className="mt-4 rounded bg-red-900/50 p-3 text-sm text-red-200">
                            {error}
                        </div>
                    )}
                </div>

                {/* Results Area */}
                <div className="col-span-1 md:col-span-3">
                    {!result && !loading && (
                        <div className="flex h-[400px] items-center justify-center rounded-xl bg-slate-900/50 border border-slate-800 border-dashed">
                            <p className="text-slate-500">Configure parameters and run a backtest to see results</p>
                        </div>
                    )}

                    {loading && (
                        <div className="flex h-[400px] items-center justify-center rounded-xl bg-slate-900/50 border border-slate-800">
                            <p className="animate-pulse text-slate-400">Simulating trading history...</p>
                        </div>
                    )}

                    {result && !loading && (
                        <div className="space-y-6">
                            {/* Metrics Grid */}
                            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                                    <div className="text-sm text-slate-400">Total Return</div>
                                    <div className={`text-2xl font-semibold ${result.stats.total_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                        {result.stats.total_return_pct >= 0 ? "+" : ""}{result.stats.total_return_pct.toFixed(2)}%
                                    </div>
                                </div>

                                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                                    <div className="text-sm text-slate-400">Max Drawdown</div>
                                    <div className="text-2xl font-semibold text-red-400">
                                        {result.stats.max_drawdown_pct.toFixed(2)}%
                                    </div>
                                </div>

                                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                                    <div className="text-sm text-slate-400">Sharpe Ratio</div>
                                    <div className="text-2xl font-semibold text-slate-100">
                                        {result.stats.sharpe_ratio.toFixed(2)}
                                    </div>
                                </div>

                                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                                    <div className="text-sm text-slate-400">Win Rate</div>
                                    <div className="text-2xl font-semibold text-slate-100">
                                        {result.stats.win_rate_pct.toFixed(1)}%
                                    </div>
                                </div>
                            </div>

                            {/* Equity Curve Chart */}
                            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                                <h3 className="mb-4 text-sm font-medium text-slate-300">Equity Curve</h3>
                                <div className="h-[400px] w-full">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={result.equity_curve}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#475569"
                                                fontSize={12}
                                                tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', year: '2-digit' })}
                                            />
                                            <YAxis
                                                stroke="#475569"
                                                fontSize={12}
                                                tickFormatter={(v) => `$${v.toLocaleString()}`}
                                                domain={['auto', 'auto']}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: "#0f172a",
                                                    border: "1px solid #1e293b",
                                                    borderRadius: "0.5rem",
                                                    color: "#f8fafc",
                                                }}
                                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                                formatter={(value: number) => [`$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, "Equity"]}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="equity"
                                                stroke="#3b82f6"
                                                strokeWidth={2}
                                                dot={false}
                                                activeDot={{ r: 6, fill: "#3b82f6" }}
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Extra Stats */}
                            <div className="grid grid-cols-2 gap-4 text-sm text-slate-400 md:grid-cols-4">
                                <div>Annualized Return: <span className="text-slate-100">{result.stats.annualized_return_pct.toFixed(2)}%</span></div>
                                <div>Sortino Ratio: <span className="text-slate-100">{result.stats.sortino_ratio.toFixed(2)}</span></div>
                                <div>Profit Factor: <span className="text-slate-100">{result.stats.profit_factor.toFixed(2)}</span></div>
                                <div>Total Trades: <span className="text-slate-100">{result.stats.total_trades}</span></div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
