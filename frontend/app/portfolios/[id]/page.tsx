"use client";

import { useState, useCallback } from "react";
import React from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../components/AuthProvider";
import {
    ChevronLeft, Plus, Trash2, Loader2, CheckCircle2,
    Pencil, Check, X, Info, Target, BarChart2, Globe,
    Clock, TrendingUp, FileText, Bookmark, Zap, RefreshCw,
} from "lucide-react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    Legend, ResponsiveContainer, ReferenceLine,
    PieChart, Pie, Cell, Tooltip as ReTooltip,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeaders() {
    const token = localStorage.getItem("access_token") || "";
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

const fetcher = async (url: string) => {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) throw new Error("Failed to load");
    return res.json();
};

async function patchPortfolio(id: string | string[], body: Record<string, any>) {
    const res = await fetch(`${API}/api/v1/portfolios/${id}`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save");
    }
    return res.json();
}

// ── Option lists ──────────────────────────────────────────────────────────────

const STRATEGY_TAGS = ["Growth", "Income", "Hedge", "Speculative", "Index", "Crypto", "Mixed", "Balanced", "Dividend"];
const RISK_LEVELS   = ["Conservative", "Moderate", "Aggressive"];
const HORIZONS      = ["Short-term (<1yr)", "Medium (1–3yr)", "Long-term (3yr+)"];
const CURRENCIES    = ["USD", "EUR", "GBP", "TRY", "JPY", "CAD", "AUD", "CHF", "SGD", "HKD"];

// ── Inline editable field ─────────────────────────────────────────────────────

function InlineText({
    value, placeholder, onSave, multiline = false, className = "",
}: {
    value: string | null | undefined;
    placeholder: string;
    onSave: (val: string) => Promise<void>;
    multiline?: boolean;
    className?: string;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(value ?? "");
    const [saving, setSaving] = useState(false);

    const commit = async () => {
        if (draft === (value ?? "")) { setEditing(false); return; }
        setSaving(true);
        try { await onSave(draft); setEditing(false); }
        catch { /* keep editing open on error */ }
        finally { setSaving(false); }
    };

    const cancel = () => { setDraft(value ?? ""); setEditing(false); };

    if (!editing) return (
        <button
            onClick={() => { setDraft(value ?? ""); setEditing(true); }}
            className={`group flex items-start gap-1.5 text-left w-full hover:text-slate-100 transition-colors ${className}`}
        >
            <span className={value ? "text-slate-300" : "text-slate-600 italic"}>
                {value || placeholder}
            </span>
            <Pencil className="h-3 w-3 text-slate-600 opacity-0 group-hover:opacity-100 mt-0.5 flex-shrink-0 transition-opacity" />
        </button>
    );

    const inputClass = "w-full rounded-lg border border-sky-500/50 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 outline-none focus:ring-1 focus:ring-sky-500/30 resize-none";

    return (
        <div className="space-y-1.5">
            {multiline
                ? <textarea rows={3} value={draft} onChange={e => setDraft(e.target.value)} className={inputClass} autoFocus />
                : <input value={draft} onChange={e => setDraft(e.target.value)} className={inputClass}
                    autoFocus onKeyDown={e => { if (e.key === "Enter") commit(); if (e.key === "Escape") cancel(); }} />
            }
            <div className="flex gap-1.5">
                <button onClick={commit} disabled={saving}
                    className="flex items-center gap-1 rounded-md bg-sky-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition-colors">
                    {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                    Save
                </button>
                <button onClick={cancel}
                    className="flex items-center gap-1 rounded-md bg-slate-700 px-2.5 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-600 transition-colors">
                    <X className="h-3 w-3" /> Cancel
                </button>
            </div>
        </div>
    );
}

function InlineSelect({
    value, options, placeholder, onSave, colorMap = {},
}: {
    value: string | null | undefined;
    options: string[];
    placeholder: string;
    onSave: (val: string) => Promise<void>;
    colorMap?: Record<string, string>;
}) {
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);

    const pick = async (opt: string) => {
        if (opt === value) { setOpen(false); return; }
        setSaving(true);
        try { await onSave(opt); }
        finally { setSaving(false); setOpen(false); }
    };

    const color = value ? (colorMap[value] ?? "text-slate-300") : "text-slate-600";

    return (
        <div className="relative">
            <button onClick={() => setOpen(o => !o)}
                className="group flex items-center gap-1.5 text-sm hover:text-slate-100 transition-colors">
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" />
                    : <Pencil className="h-3 w-3 text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />}
                <span className={`font-medium ${color}`}>{value || <span className="text-slate-600 italic">{placeholder}</span>}</span>
            </button>
            {open && (
                <div className="absolute left-0 top-full mt-1 z-20 min-w-[180px] rounded-xl border border-slate-700 bg-slate-900 shadow-2xl py-1">
                    {options.map(opt => (
                        <button key={opt} onClick={() => pick(opt)}
                            className={`flex w-full items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-slate-800 ${
                                opt === value ? "text-sky-400" : "text-slate-300"
                            }`}>
                            {opt}
                            {opt === value && <Check className="h-3.5 w-3.5" />}
                        </button>
                    ))}
                    {value && (
                        <button onClick={() => pick("")}
                            className="flex w-full items-center gap-1.5 px-3 py-2 text-xs text-slate-500 hover:bg-slate-800 transition-colors border-t border-slate-800 mt-1">
                            <X className="h-3 w-3" /> Clear
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Performance Chart (Sprint 15 P3-PORT-02) ───────────────────────────────────────────────────────

interface PerfData {
    dates: string[];
    portfolio: number[];
    benchmark: (number | null)[];
    benchmark_symbol: string;
    period: string;
    portfolio_return_pct: number;
    benchmark_return_pct: number;
    alpha_pct: number;
    error: string | null;
}

const PERF_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"] as const;
type PerfPeriod = typeof PERF_PERIODS[number];

function PerformanceChart({
    portfolioId, benchmark, hasItems,
}: {
    portfolioId: string;
    benchmark: string | null | undefined;
    hasItems: boolean;
}) {
    const [period, setPeriod] = React.useState<PerfPeriod>("1y");

    const { data, isLoading, error } = useSWR<PerfData>(
        hasItems ? `${API}/api/v1/portfolios/${portfolioId}/performance?period=${period}` : null,
        fetcher,
        { revalidateOnFocus: false, shouldRetryOnError: false, keepPreviousData: true },
    );

    if (!hasItems) return null;

    const chartData = (data?.dates ?? []).map((d, i) => ({
        date: d,
        portfolio: data?.portfolio[i] ?? null,
        benchmark: data?.benchmark?.[i] ?? null,
    }));

    const benchSym = benchmark ?? data?.benchmark_symbol ?? "SPY";
    const portRet  = data?.portfolio_return_pct ?? 0;
    const benchRet = data?.benchmark_return_pct ?? 0;
    const alpha    = data?.alpha_pct ?? 0;

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-sky-400" />
                    <h2 className="text-sm font-bold text-slate-100">Portfolio vs Benchmark</h2>
                    <span className="text-[10px] text-slate-500">Normalised to 100</span>
                </div>
                <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                    {PERF_PERIODS.map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                                period === p ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                            }`}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {data && !data.error && (
                <div className="flex flex-wrap gap-4">
                    <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full bg-sky-400" />
                        <span className="text-xs text-slate-400">Portfolio</span>
                        <span className={`text-sm font-bold tabular-nums ${portRet >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {portRet >= 0 ? "+" : ""}{portRet.toFixed(1)}%
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full bg-slate-500" />
                        <span className="text-xs text-slate-400">{benchSym}</span>
                        <span className={`text-sm font-bold tabular-nums ${benchRet >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {benchRet >= 0 ? "+" : ""}{benchRet.toFixed(1)}%
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">Alpha</span>
                        <span className={`text-sm font-bold tabular-nums ${alpha >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {alpha >= 0 ? "+" : ""}{alpha.toFixed(1)}%
                        </span>
                    </div>
                </div>
            )}

            {isLoading && !data && <div className="h-56 rounded-xl bg-slate-800/40 animate-pulse" />}
            {(error || data?.error) && (
                <div className="rounded-xl border border-amber-800/30 bg-amber-950/15 px-4 py-3 text-xs text-amber-400">
                    {data?.error ?? "Could not load performance data. Ensure price data is available for the selected period."}
                </div>
            )}
            {chartData.length > 0 && (
                <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                            <XAxis dataKey="date" stroke="#475569" fontSize={10}
                                tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: "short", year: "2-digit" })}
                                interval="preserveStartEnd" />
                            <YAxis stroke="#475569" fontSize={10} tickFormatter={(v) => `${v.toFixed(0)}`} width={38} domain={["auto", "auto"]} />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", fontSize: 11 }}
                                labelFormatter={(l) => new Date(l).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                                formatter={(v: number, name: string) => [
                                    `${v?.toFixed(1)} (${(v - 100) >= 0 ? "+" : ""}${(v - 100)?.toFixed(1)}%)`,
                                    name === "portfolio" ? "Portfolio" : benchSym,
                                ]}
                            />
                            <Legend formatter={(v) => v === "portfolio" ? "Portfolio" : benchSym} wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
                            <ReferenceLine y={100} stroke="#334155" strokeDasharray="4 2" />
                            <Line type="monotone" dataKey="portfolio" stroke="#38bdf8" strokeWidth={2} dot={false} activeDot={{ r: 3, fill: "#38bdf8" }} />
                            <Line type="monotone" dataKey="benchmark" stroke="#475569" strokeWidth={1.5} strokeDasharray="4 2" dot={false} activeDot={{ r: 3 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
            <p className="text-[10px] text-slate-700">
                Daily close prices from Yahoo Finance. Portfolio = weighted sum of constituent returns. Educational only.
            </p>
        </div>
    );
}

// ── Portfolio GAS Banner ───────────────────────────────────────────────────────────────────────────

function PortfolioGasBanner({
    analysis, isLoading, onRefresh, symbolCount,
}: {
    analysis: any;
    isLoading: boolean;
    onRefresh: () => void;
    symbolCount: number;
}) {
    if (symbolCount === 0) return null;

    const gas: number | null = analysis?.weighted_gas ?? null;
    const breakdown: { symbol: string; gas_score: number; weight_pct: number }[] =
        analysis?.symbol_gas_breakdown ?? [];

    const scoreColor = (s: number) =>
        s >= 65 ? "text-emerald-400" : s >= 40 ? "text-amber-400" : "text-rose-400";
    const barColor = (s: number) =>
        s >= 65 ? "bg-emerald-500" : s >= 40 ? "bg-amber-500" : "bg-rose-500";
    const label = (s: number) =>
        s >= 75 ? "Strong Tailwind" : s >= 60 ? "Mild Support" : s >= 45 ? "Mixed Signals" : s >= 30 ? "Headwind" : "High Instability";

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap className="h-4 w-4 text-sky-400" />
                    <h2 className="text-sm font-bold text-slate-100">Portfolio GAS Aggregate</h2>
                    <span className="text-[10px] text-slate-500">Weighted across {symbolCount} asset{symbolCount !== 1 ? "s" : ""}</span>
                </div>
                <button onClick={onRefresh} disabled={isLoading}
                    className="p-1.5 rounded-lg text-slate-600 hover:text-slate-400 hover:bg-slate-800 transition-colors disabled:opacity-40">
                    <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
                </button>
            </div>

            {isLoading && !analysis && (
                <div className="flex items-center gap-3 animate-pulse">
                    <div className="h-14 w-14 rounded-xl bg-slate-800" />
                    <div className="space-y-2 flex-1">
                        <div className="h-4 w-32 rounded bg-slate-800" />
                        <div className="h-2 w-full rounded-full bg-slate-800" />
                    </div>
                </div>
            )}

            {gas != null && (
                <div className="flex items-start gap-5">
                    <div className="flex-shrink-0 text-center">
                        <div className={`text-5xl font-black tabular-nums ${scoreColor(gas)}`}>{gas.toFixed(0)}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">/ 100</div>
                        <div className={`text-xs font-semibold mt-1 ${scoreColor(gas)}`}>{label(gas)}</div>
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                        {breakdown.length > 0 ? breakdown.map((row) => (
                            <div key={row.symbol} className="space-y-0.5">
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono font-bold text-slate-200 w-14 truncate">{row.symbol}</span>
                                        <span className="text-slate-600 text-[10px]">{row.weight_pct.toFixed(0)}% weight</span>
                                    </div>
                                    <span className={`font-mono font-semibold tabular-nums ${scoreColor(row.gas_score)}`}>{row.gas_score.toFixed(0)}</span>
                                </div>
                                <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                                    <div className={`h-full rounded-full ${barColor(row.gas_score)}`} style={{ width: `${Math.min(100, row.gas_score)}%` }} />
                                </div>
                            </div>
                        )) : (
                            <div className="space-y-1.5">
                                <p className="text-xs text-slate-500">Weighted GAS across all positions.</p>
                                <div className="h-2.5 rounded-full bg-slate-800 overflow-hidden">
                                    <div className={`h-full rounded-full ${barColor(gas)}`} style={{ width: `${Math.min(100, gas)}%` }} />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
            <p className="text-[10px] text-slate-600 border-t border-slate-800/50 pt-3">
                GAS = (Technical × 40%) + (Sentiment × 30%) + (Macro × 30%). Weighted by portfolio allocation. Educational only.
            </p>
        </div>
    );
}

// ── Target Return Progress (Sprint 17) ──────────────────────────────────────────────────────────────

function TargetReturnProgress({
    portfolioId, targetReturnPct,
}: { portfolioId: string; targetReturnPct: number }) {
    const { data } = useSWR<PerfData>(
        `${API}/api/v1/portfolios/${portfolioId}/performance?period=1y`,
        fetcher,
        { revalidateOnFocus: false, shouldRetryOnError: false, keepPreviousData: true },
    );

    const ytdReturn = React.useMemo(() => {
        if (!data?.dates || !data.portfolio || data.portfolio.length < 2) return null;
        const yr = new Date().getFullYear();
        const idx = data.dates.findIndex(d => new Date(d).getFullYear() >= yr);
        const start = idx >= 0 ? data.portfolio[idx] : data.portfolio[0];
        const end   = data.portfolio[data.portfolio.length - 1];
        if (!start || !end) return null;
        return ((end / start) - 1) * 100;
    }, [data]);

    const now       = new Date();
    const dayOfYear = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86_400_000);
    const proRata   = (dayOfYear / 365) * targetReturnPct;
    const fillPct   = ytdReturn != null && targetReturnPct > 0
        ? Math.min(100, Math.max(0, (ytdReturn / targetReturnPct) * 100))
        : 0;
    const onTrack = ytdReturn != null && proRata > 0 && ytdReturn >= proRata * 0.8;
    const ahead   = ytdReturn != null && proRata > 0 && ytdReturn >= proRata * 1.2;

    return (
        <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 px-3 py-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 font-medium">Target Return</span>
                <span className="text-emerald-400 font-semibold tabular-nums">{targetReturnPct}% p.a.</span>
            </div>
            {ytdReturn != null ? (
                <>
                    <div className="space-y-1">
                        <div className="flex justify-between text-[10px] text-slate-500">
                            <span>YTD actual</span>
                            <span className={`font-semibold tabular-nums ${
                                ytdReturn >= 0 ? "text-emerald-400" : "text-rose-400"
                            }`}>{ytdReturn >= 0 ? "+" : ""}{ytdReturn.toFixed(1)}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-700 overflow-hidden relative">
                            {proRata > 0 && (
                                <div
                                    className="absolute top-0 bottom-0 w-0.5 bg-slate-300/40"
                                    style={{ left: `${Math.min((proRata / Math.max(targetReturnPct, 1)) * 100, 97)}%` }}
                                    title={`On-pace: ${proRata.toFixed(1)}%`}
                                />
                            )}
                            <div
                                className={`h-full rounded-full transition-all duration-700 ${
                                    ahead ? "bg-emerald-400" : onTrack ? "bg-emerald-600" : ytdReturn >= 0 ? "bg-amber-500" : "bg-rose-500"
                                }`}
                                style={{ width: `${fillPct}%` }}
                            />
                        </div>
                        <div className="flex justify-between text-[10px] text-slate-700">
                            <span>0%</span>
                            {proRata > 0 && <span className="text-slate-600">pace {proRata.toFixed(1)}%</span>}
                            <span>{targetReturnPct}%</span>
                        </div>
                    </div>
                    <p className={`text-[10px] font-medium ${
                        ahead ? "text-emerald-400" : onTrack ? "text-teal-400" : "text-amber-400"
                    }`}>
                        {ahead ? "✔ Ahead of pace" : onTrack ? "✔ On track" : "Behind pace — see chart above"}
                    </p>
                </>
            ) : (
                <p className="text-[10px] text-slate-600">Loading performance data…</p>
            )}
        </div>
    );
}

// ── Metric bar ─────────────────────────────────────────────────────────────────────────────────────

// -- Correlation Matrix Heatmap (Sprint 19) --

interface CorrelationData {
    symbols: string[];
    matrix: number[][];
    period: string;
    n_days?: number;
    error: string | null;
}

const CORR_PERIODS = ["1mo", "3mo", "6mo", "1y"] as const;
type CorrPeriod = typeof CORR_PERIODS[number];

function corrColor(v: number): string {
    if (v >= 0.8)  return "#064e3b";
    if (v >= 0.6)  return "#065f46";
    if (v >= 0.4)  return "#166534";
    if (v >= 0.2)  return "#14532d";
    if (v >= 0.05) return "#1a3a28";
    if (v > -0.05) return "#1e293b";
    if (v >= -0.2) return "#3b1a1a";
    if (v >= -0.4) return "#5c1717";
    if (v >= -0.6) return "#7f1d1d";
    return "#450a0a";
}

function corrTextColor(v: number): string {
    if (Math.abs(v) > 0.5) return "text-slate-100";
    if (Math.abs(v) > 0.2) return "text-slate-300";
    return "text-slate-500";
}

function CorrelationMatrix({ portfolioId, hasItems }: { portfolioId: string; hasItems: boolean }) {
    const [corrPeriod, setCorrPeriod] = React.useState<CorrPeriod>("6mo");

    const { data: corrData, isLoading: corrLoading, error: corrErr } = useSWR<CorrelationData>(
        hasItems ? `${API}/api/v1/portfolios/${portfolioId}/correlation?period=${corrPeriod}` : null,
        fetcher,
        { revalidateOnFocus: false, shouldRetryOnError: false, keepPreviousData: true },
    );

    if (!hasItems) return null;

    const symbols = corrData?.symbols ?? [];
    const matrix  = corrData?.matrix  ?? [];

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <BarChart2 className="h-4 w-4 text-violet-400" />
                    <h2 className="text-sm font-bold text-slate-100">Correlation Matrix</h2>
                    <span className="text-[10px] text-slate-500">Pairwise Pearson &middot; daily close prices</span>
                </div>
                <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                    {CORR_PERIODS.map((p) => (
                        <button
                            key={p}
                            onClick={() => setCorrPeriod(p)}
                            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                                corrPeriod === p ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                            }`}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {corrLoading && !corrData && (
                <div className="h-40 rounded-xl bg-slate-800/40 animate-pulse" />
            )}

            {(corrErr || corrData?.error) && (
                <div className="rounded-xl border border-amber-800/30 bg-amber-950/15 px-4 py-3 text-xs text-amber-400">
                    {corrData?.error ?? "Could not load correlation data."}
                </div>
            )}

            {symbols.length >= 2 && matrix.length > 0 && (
                <>
                    <div className="overflow-x-auto">
                        <table className="text-xs border-separate border-spacing-1">
                            <thead>
                                <tr>
                                    <th className="w-16" />
                                    {symbols.map((s) => (
                                        <th key={s} className="text-center font-mono text-[10px] text-slate-400 pb-1 px-1 min-w-[52px]">
                                            {s}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {symbols.map((row, ri) => (
                                    <tr key={row}>
                                        <td className="font-mono text-[10px] text-slate-400 pr-2 text-right whitespace-nowrap">{row}</td>
                                        {symbols.map((col, ci) => {
                                            const v = matrix[ri]?.[ci] ?? 0;
                                            const isDiag = ri === ci;
                                            return (
                                                <td
                                                    key={col}
                                                    className={`rounded text-center tabular-nums font-mono py-2 px-1 ${
                                                        isDiag ? "text-slate-600" : corrTextColor(v)
                                                    }`}
                                                    style={{ backgroundColor: isDiag ? "#0f172a" : corrColor(v), fontSize: "10px" }}
                                                    title={`${row} vs ${col}: ${v.toFixed(3)}`}
                                                >
                                                    {isDiag ? "1.00" : v.toFixed(2)}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="flex items-center gap-2 text-[10px] text-slate-500">
                        <span>Low (&minus;1)</span>
                        <div className="flex gap-0.5">
                            {[-1, -0.6, -0.2, 0.2, 0.6, 1].map((v) => (
                                <div key={v} className="h-3 w-5 rounded-sm" style={{ backgroundColor: corrColor(v) }} />
                            ))}
                        </div>
                        <span>High (+1)</span>
                        {corrData?.n_days && (
                            <span className="ml-auto text-slate-700">{corrData.n_days} trading days</span>
                        )}
                    </div>

                    <p className="text-[10px] text-slate-700">
                        Pearson correlation of daily returns. 1.0 = perfectly correlated, 0 = uncorrelated, &minus;1 = inverse. Lower average off-diagonal = better diversification.
                    </p>
                </>
            )}
        </div>
    );
}

// ── Sector Pie Chart — Sprint 24 ────────────────────────────────────────────────────────────────

const SECTOR_COLORS = [
    "#38bdf8", "#34d399", "#f59e0b", "#f87171", "#a78bfa",
    "#fb923c", "#2dd4bf", "#e879f9", "#94a3b8", "#86efac",
];

function SectorPieChart({ breakdown }: { breakdown: Record<string, number> }) {
    const data = Object.entries(breakdown)
        .filter(([, v]) => v > 0)
        .sort(([, a], [, b]) => b - a)
        .map(([name, value], i) => ({ name, value, color: SECTOR_COLORS[i % SECTOR_COLORS.length] }));

    if (data.length === 0) return null;

    return (
        <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Sector Exposure</h3>
            <div className="flex items-center gap-4">
                <div className="flex-shrink-0">
                    <PieChart width={120} height={120}>
                        <Pie
                            data={data}
                            dataKey="value"
                            nameKey="name"
                            cx={60}
                            cy={60}
                            innerRadius={34}
                            outerRadius={56}
                            strokeWidth={0}
                            isAnimationActive={false}
                        >
                            {data.map((entry, i) => (
                                <Cell key={i} fill={entry.color} />
                            ))}
                        </Pie>
                        <ReTooltip
                            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 11 }}
                            formatter={(v: number) => [`${v.toFixed(1)}%`, ""]}
                        />
                    </PieChart>
                </div>
                <div className="flex-1 min-w-0 space-y-1.5">
                    {data.slice(0, 6).map((entry) => (
                        <div key={entry.name} className="flex items-center gap-2">
                            <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ background: entry.color }} />
                            <span className="text-xs text-slate-400 truncate flex-1">{entry.name}</span>
                            <span className="text-xs font-mono text-slate-300 tabular-nums">{entry.value.toFixed(1)}%</span>
                        </div>
                    ))}
                    {data.length > 6 && (
                        <p className="text-[10px] text-slate-600">+{data.length - 6} more</p>
                    )}
                </div>
            </div>
        </div>
    );
}

// ── Rebalancing Calculator — Sprint 31 ───────────────────────────────────────────────────────────

function RebalancingCalculator({
    portfolio, totalCapital,
}: { portfolio: any; totalCapital: number }) {
    const items: any[] = portfolio?.items ?? [];
    const [capitals, setCapitals] = React.useState<Record<string, string>>({});
    const [open, setOpen] = React.useState(false);

    if (items.length === 0) return null;

    const totalWeight = items.reduce((s: number, i: any) => s + i.weight, 0) || 1;

    const rows = items.map((item: any) => {
        const targetPct  = (item.weight / totalWeight) * 100;
        const currentStr = capitals[item.symbol] ?? "";
        const currentUsd = parseFloat(currentStr) || 0;
        const currentPct = totalCapital > 0 ? (currentUsd / totalCapital) * 100 : targetPct;
        const diffPct    = targetPct - currentPct;
        const tradeUsd   = Math.abs(diffPct / 100 * totalCapital);
        const action     = Math.abs(diffPct) < 0.5 ? "HOLD" : diffPct > 0 ? "BUY" : "SELL";
        return { symbol: item.symbol, currentPct, targetPct, diffPct, action, tradeUsd };
    });

    const allFilled = items.every((i: any) => capitals[i.symbol] !== undefined && capitals[i.symbol] !== "");

    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <button type="button" onClick={() => setOpen((v) => !v)}
                className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/20 transition-colors">
                <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-violet-400" />
                    <h2 className="text-sm font-bold text-slate-100">Rebalancing Calculator</h2>
                    <span className="text-[10px] text-slate-500">Enter current holdings → get instructions</span>
                </div>
                <svg className={`h-4 w-4 text-slate-600 transition-transform ${open ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {open && (
                <div className="border-t border-slate-800 px-5 py-4 space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {items.map((item: any) => (
                            <div key={item.symbol} className="space-y-1">
                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                                    {item.symbol} — current value ($)
                                </label>
                                <input type="number" min={0}
                                    placeholder={`e.g. ${(totalCapital * (item.weight / totalWeight)).toFixed(0)}`}
                                    value={capitals[item.symbol] ?? ""}
                                    onChange={(e) => setCapitals((prev) => ({ ...prev, [item.symbol]: e.target.value }))}
                                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                                />
                            </div>
                        ))}
                    </div>

                    {allFilled && (
                        <div className="overflow-x-auto rounded-xl border border-slate-800">
                            <table className="w-full text-xs">
                                <thead className="bg-slate-900/60">
                                    <tr className="border-b border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                                        <th className="px-4 py-2.5 text-left">Symbol</th>
                                        <th className="px-4 py-2.5 text-right">Current %</th>
                                        <th className="px-4 py-2.5 text-right">Target %</th>
                                        <th className="px-4 py-2.5 text-right">Diff</th>
                                        <th className="px-4 py-2.5 text-center">Action</th>
                                        <th className="px-4 py-2.5 text-right">Trade ($)</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                    {rows.map((row: any) => (
                                        <tr key={row.symbol} className="hover:bg-slate-800/10">
                                            <td className="px-4 py-2.5 font-mono font-bold text-slate-100">{row.symbol}</td>
                                            <td className="px-4 py-2.5 text-right font-mono tabular-nums text-slate-400">{row.currentPct.toFixed(1)}%</td>
                                            <td className="px-4 py-2.5 text-right font-mono tabular-nums text-slate-300">{row.targetPct.toFixed(1)}%</td>
                                            <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold ${
                                                row.action === "HOLD" ? "text-slate-500" :
                                                row.action === "BUY"  ? "text-emerald-400" : "text-rose-400"
                                            }`}>{row.diffPct >= 0 ? "+" : ""}{row.diffPct.toFixed(1)}%</td>
                                            <td className="px-4 py-2.5 text-center">
                                                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                                                    row.action === "BUY"  ? "bg-emerald-950/40 border-emerald-800/50 text-emerald-300" :
                                                    row.action === "SELL" ? "bg-rose-950/40 border-rose-800/50 text-rose-300" :
                                                    "bg-slate-800/40 border-slate-700/50 text-slate-500"
                                                }`}>{row.action}</span>
                                            </td>
                                            <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold ${
                                                row.action === "HOLD" ? "text-slate-600" :
                                                row.action === "BUY"  ? "text-emerald-400" : "text-rose-400"
                                            }`}>
                                                {row.action === "HOLD" ? "—" : `${row.tradeUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {!allFilled && (
                        <p className="text-xs text-slate-600">Fill in all current values above to see rebalancing instructions.</p>
                    )}
                    <p className="text-[10px] text-slate-700">
                        Trade sizes = |target − current| × ${totalCapital.toLocaleString()}. Diff &lt; 0.5% = HOLD. Educational estimate only.
                    </p>
                </div>
            )}
        </div>
    );
}

function MetricBar({ label, value, max = 100, description }: {
    label: string; value: number; max?: number; description: string;
}) {
    const pct = Math.min((value / max) * 100, 100);
    const color = value > 60 ? "bg-emerald-500" : value < 40 ? "bg-rose-500" : "bg-amber-500";
    const textColor = value > 60 ? "text-emerald-400" : value < 40 ? "text-rose-400" : "text-amber-400";
    return (
        <div>
            <div className="flex justify-between items-baseline mb-1.5">
                <span className="text-sm font-medium text-slate-300">{label}</span>
                <span className={`text-lg font-black tabular-nums ${textColor}`}>
                    {value.toFixed(1)} <span className="text-xs font-normal text-slate-500">/ {max}</span>
                </span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2">
                <div className={`h-2 rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
            </div>
            <p className="mt-1.5 text-xs text-slate-500">{description}</p>
        </div>
    );
}

// ── Page ───────────────────────────────────────────────────────────────────────────────────────────

export default function PortfolioDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const id = params.id as string;

    const [symbol, setSymbol]     = useState("");
    const [weight, setWeight]     = useState<number | "">("");
    const [isAdding, setIsAdding] = useState(false);
    const [addError, setAddError] = useState<string | null>(null);

    const { data: portfolio, mutate: mutatePort } = useSWR(
        user && id ? `${API}/api/v1/portfolios/${id}` : null,
        fetcher,
    );

    const { data: analysis, error: analysisError, isLoading: analysisLoading, mutate: mutateAnalysis } = useSWR(
        user && id && portfolio?.items?.length > 0
            ? `${API}/api/v1/portfolios/${id}/analysis` : null,
        fetcher,
        { revalidateOnFocus: false },
    );

    const save = useCallback(async (body: Record<string, any>) => {
        const updated = await patchPortfolio(id, body);
        mutatePort(updated, false);
    }, [id, mutatePort]);

    const handleAddItem = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!symbol || weight === "") return;
        setIsAdding(true);
        setAddError(null);
        try {
            const res = await fetch(`${API}/api/v1/portfolios/${id}/items`, {
                method: "POST", headers: authHeaders(),
                body: JSON.stringify({ symbol: symbol.toUpperCase(), weight: Number(weight) }),
            });
            if (res.ok) { setSymbol(""); setWeight(""); mutatePort(); }
            else { const d = await res.json().catch(() => ({})); setAddError(d.detail ?? "Failed to add"); }
        } catch { setAddError("Network error"); }
        finally { setIsAdding(false); }
    };

    const removeItem = async (sym: string) => {
        await fetch(`${API}/api/v1/portfolios/${id}/items/${sym}`, {
            method: "DELETE", headers: authHeaders(),
        });
        mutatePort();
    };

    if (!portfolio) return (
        <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
    );

    const totalWeight = portfolio.items?.reduce((s: number, i: any) => s + i.weight, 0) ?? 0;
    const weightOk    = Math.abs(totalWeight - 1.0) < 0.001;

    const strategyColors: Record<string, string> = {
        Growth: "text-emerald-400", Income: "text-sky-400", Hedge: "text-violet-400",
        Speculative: "text-rose-400", Index: "text-blue-400", Crypto: "text-amber-400",
        Mixed: "text-slate-300", Balanced: "text-teal-400", Dividend: "text-green-400",
    };
    const riskColors: Record<string, string> = {
        Conservative: "text-sky-400", Moderate: "text-amber-400", Aggressive: "text-rose-400",
    };

    return (
        <div className="space-y-6 max-w-7xl">

            {/* Back + Header */}
            <div>
                <button onClick={() => router.push("/portfolios")}
                    className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors mb-3">
                    <ChevronLeft className="h-4 w-4" /> Back to Portfolios
                </button>
                <InlineText
                    value={portfolio.name}
                    placeholder="Portfolio name"
                    onSave={name => save({ name })}
                    className="text-3xl font-black text-slate-100"
                />
                <div className="mt-1">
                    <InlineText
                        value={portfolio.description}
                        placeholder="Add a description…"
                        onSave={description => save({ description })}
                        className="text-sm text-slate-400"
                    />
                </div>
            </div>

            {/* Performance vs Benchmark chart */}
            <PerformanceChart
                portfolioId={id}
                benchmark={portfolio.benchmark}
                hasItems={(portfolio.items?.length ?? 0) > 0}
            />

            {/* Correlation Matrix -- Sprint 19 */}
            <CorrelationMatrix
                portfolioId={id}
                hasItems={(portfolio.items?.length ?? 0) >= 2}
            />

            {/* GAS Aggregate Banner */}
            <PortfolioGasBanner
                analysis={analysis}
                isLoading={analysisLoading}
                onRefresh={() => mutateAnalysis()}
                symbolCount={portfolio.items?.length ?? 0}
            />

            {/* Profile card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">Portfolio Profile</h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-5">
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Bookmark className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Strategy</span>
                        </div>
                        <InlineSelect value={portfolio.strategy_tag} options={STRATEGY_TAGS}
                            placeholder="Set strategy" colorMap={strategyColors}
                            onSave={strategy_tag => save({ strategy_tag })} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <BarChart2 className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Risk Level</span>
                        </div>
                        <InlineSelect value={portfolio.risk_tolerance} options={RISK_LEVELS}
                            placeholder="Set risk" colorMap={riskColors}
                            onSave={risk_tolerance => save({ risk_tolerance })} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Clock className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Horizon</span>
                        </div>
                        <InlineSelect value={portfolio.horizon} options={HORIZONS}
                            placeholder="Set horizon"
                            onSave={horizon => save({ horizon })} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Globe className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Currency</span>
                        </div>
                        <InlineSelect value={portfolio.base_currency ?? "USD"} options={CURRENCIES}
                            placeholder="USD"
                            onSave={base_currency => save({ base_currency })} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Target className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Target Return</span>
                        </div>
                        <InlineText
                            value={portfolio.target_return != null ? `${portfolio.target_return}` : ""}
                            placeholder="e.g. 15"
                            onSave={v => save({ target_return: v === "" ? null : parseFloat(v) })}
                            className="text-sm"
                        />
                        {portfolio.target_return != null && (
                            <span className="text-[10px] text-slate-600">% per year</span>
                        )}
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <TrendingUp className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Benchmark</span>
                        </div>
                        <InlineText
                            value={portfolio.benchmark}
                            placeholder="e.g. SPY"
                            onSave={benchmark => save({ benchmark: benchmark.toUpperCase() || null })}
                            className="text-sm font-mono"
                        />
                    </div>
                </div>
                <div className="mt-5 pt-4 border-t border-slate-800">
                    <div className="flex items-center gap-1.5 mb-2">
                        <FileText className="h-3.5 w-3.5 text-slate-600" />
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Investment Thesis / Notes</span>
                    </div>
                    <InlineText
                        value={portfolio.notes}
                        placeholder="Write your investment thesis, reminders, or strategy notes here…"
                        onSave={notes => save({ notes })}
                        multiline
                        className="text-sm text-slate-400"
                    />
                </div>
            </div>

            {/* Rebalancing Calculator — Sprint 31 */}
            {(portfolio.items?.length ?? 0) >= 2 && (
                <RebalancingCalculator
                    portfolio={portfolio}
                    totalCapital={10000}
                />
            )}

            {/* Main grid: allocations + analytics */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* LEFT: Allocation table */}
                <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-5">
                    <h2 className="text-base font-bold text-slate-100">Allocation Mapping</h2>
                    <form onSubmit={handleAddItem} className="flex gap-2">
                        <input type="text" placeholder="Ticker (e.g. AAPL)" value={symbol}
                            onChange={e => setSymbol(e.target.value.toUpperCase())}
                            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/20"
                            required />
                        <input type="number" step="0.01" min="0.001" max="1" placeholder="Weight (0–1)" value={weight}
                            onChange={e => setWeight(e.target.valueAsNumber || "")}
                            className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/20"
                            required />
                        <button type="submit" disabled={isAdding}
                            className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition-colors">
                            {isAdding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                            Add
                        </button>
                    </form>
                    {addError && <p className="text-xs text-rose-400">{addError}</p>}
                    <div className="overflow-x-auto rounded-lg border border-slate-800">
                        <table className="min-w-full divide-y divide-slate-800">
                            <thead className="bg-slate-900/80">
                                <tr className="text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                                    <th className="px-4 py-2.5">Symbol</th>
                                    <th className="px-4 py-2.5">Raw Weight</th>
                                    <th className="px-4 py-2.5">Normalised</th>
                                    <th className="px-4 py-2.5 text-right">Remove</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {portfolio.items?.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-4 py-10 text-center text-sm text-slate-600 italic">
                                            No assets yet — add a ticker above.
                                        </td>
                                    </tr>
                                ) : portfolio.items?.map((item: any) => {
                                    const norm = totalWeight > 0 ? (item.weight / totalWeight) * 100 : 0;
                                    return (
                                        <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                                            <td className="px-4 py-3 text-sm font-bold text-slate-100 font-mono">{item.symbol}</td>
                                            <td className="px-4 py-3 text-sm text-slate-400">{(item.weight * 100).toFixed(1)}%</td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-20 bg-slate-800 rounded-full h-1.5">
                                                        <div className="bg-sky-500 h-1.5 rounded-full" style={{ width: `${Math.min(norm, 100)}%` }} />
                                                    </div>
                                                    <span className="text-xs text-slate-400 font-mono">{norm.toFixed(1)}%</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <button onClick={() => removeItem(item.symbol)}
                                                    className="rounded-lg p-1.5 text-slate-600 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
                                                    title={`Remove ${item.symbol}`}>
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                    {portfolio.items?.length > 0 && (
                        <div className={`flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-2 border ${
                            weightOk
                                ? "text-emerald-400 bg-emerald-950/20 border-emerald-800/40"
                                : "text-amber-400 bg-amber-950/20 border-amber-800/40"
                        }`}>
                            {weightOk
                                ? <><CheckCircle2 className="h-3.5 w-3.5" /> Weights sum to 100% — fully allocated</>
                                : <><Info className="h-3.5 w-3.5" /> Weights sum to {(totalWeight * 100).toFixed(1)}% — analytics will auto-normalise to 100%</>
                            }
                        </div>
                    )}
                </div>

                {/* RIGHT: Analytics */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-6">
                    <h2 className="text-base font-bold text-slate-100">Quantitative Analytics</h2>
                    {portfolio.items?.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
                            <BarChart2 className="h-8 w-8 text-slate-700" />
                            <p className="text-sm text-slate-500">Add assets to generate portfolio metrics.</p>
                        </div>
                    ) : analysisLoading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-3">
                            <Loader2 className="h-6 w-6 animate-spin text-sky-400" />
                            <p className="text-xs text-slate-500">Computing metrics…</p>
                        </div>
                    ) : analysisError ? (
                        <div className="rounded-lg bg-rose-950/20 border border-rose-800/40 p-4 text-sm text-rose-400">
                            Analytics unavailable — models may not be trained for all symbols.
                        </div>
                    ) : analysis ? (
                        <div className="space-y-6">
                            <MetricBar
                                label="Portfolio GAS"
                                value={analysis.weighted_gas}
                                description="Weighted average Global Alignment Score. Above 60 = broadly bullish signal environment."
                            />
                            <MetricBar
                                label="Diversification"
                                value={analysis.diversification_score}
                                description="Based on inter-asset price correlation (6mo). Higher = less concentrated risk."
                            />
                            {Object.keys(analysis.sector_breakdown ?? {}).length > 0 && (
                                <SectorPieChart breakdown={analysis.sector_breakdown} />
                            )}
                            {portfolio.target_return != null && (
                                <TargetReturnProgress
                                    portfolioId={id}
                                    targetReturnPct={portfolio.target_return}
                                />
                            )}
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    );
}
