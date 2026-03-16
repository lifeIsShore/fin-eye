"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../components/AuthProvider";
import {
    ChevronLeft, Plus, Trash2, Loader2, CheckCircle2,
    Pencil, Check, X, Info, Target, BarChart2, Globe,
    Clock, TrendingUp, FileText, Bookmark,
} from "lucide-react";

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

// ── Metric bar ────────────────────────────────────────────────────────────────

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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PortfolioDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const id = params.id as string;

    const [symbol, setSymbol]   = useState("");
    const [weight, setWeight]   = useState<number | "">("");
    const [isAdding, setIsAdding] = useState(false);
    const [addError, setAddError] = useState<string | null>(null);

    const { data: portfolio, mutate: mutatePort } = useSWR(
        user && id ? `${API}/api/v1/portfolios/${id}` : null,
        fetcher,
    );

    const { data: analysis, error: analysisError, isLoading: analysisLoading } = useSWR(
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
    const weightOk = Math.abs(totalWeight - 1.0) < 0.001;

    // ── Colour maps for selects ────────────────────────────────────────────
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

            {/* ── Back + Header ───────────────────────────────────────────── */}
            <div>
                <button onClick={() => router.push("/portfolios")}
                    className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors mb-3">
                    <ChevronLeft className="h-4 w-4" /> Back to Portfolios
                </button>

                {/* Editable name */}
                <InlineText
                    value={portfolio.name}
                    placeholder="Portfolio name"
                    onSave={name => save({ name })}
                    className="text-3xl font-black text-slate-100"
                />

                {/* Editable description */}
                <div className="mt-1">
                    <InlineText
                        value={portfolio.description}
                        placeholder="Add a description…"
                        onSave={description => save({ description })}
                        className="text-sm text-slate-400"
                    />
                </div>
            </div>

            {/* ── Profile card ────────────────────────────────────────────── */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">
                    Portfolio Profile
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-5">

                    {/* Strategy */}
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Bookmark className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Strategy</span>
                        </div>
                        <InlineSelect value={portfolio.strategy_tag} options={STRATEGY_TAGS}
                            placeholder="Set strategy" colorMap={strategyColors}
                            onSave={strategy_tag => save({ strategy_tag })} />
                    </div>

                    {/* Risk */}
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <BarChart2 className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Risk Level</span>
                        </div>
                        <InlineSelect value={portfolio.risk_tolerance} options={RISK_LEVELS}
                            placeholder="Set risk" colorMap={riskColors}
                            onSave={risk_tolerance => save({ risk_tolerance })} />
                    </div>

                    {/* Horizon */}
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Clock className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Horizon</span>
                        </div>
                        <InlineSelect value={portfolio.horizon} options={HORIZONS}
                            placeholder="Set horizon"
                            onSave={horizon => save({ horizon })} />
                    </div>

                    {/* Currency */}
                    <div>
                        <div className="flex items-center gap-1.5 mb-1.5">
                            <Globe className="h-3.5 w-3.5 text-slate-600" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Currency</span>
                        </div>
                        <InlineSelect value={portfolio.base_currency ?? "USD"} options={CURRENCIES}
                            placeholder="USD"
                            onSave={base_currency => save({ base_currency })} />
                    </div>

                    {/* Target return */}
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

                    {/* Benchmark */}
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

                {/* Notes — full width */}
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

            {/* ── Main grid: allocations + analytics ──────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* LEFT: Allocation table */}
                <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-5">
                    <h2 className="text-base font-bold text-slate-100">Allocation Mapping</h2>

                    {/* Add form */}
                    <form onSubmit={handleAddItem} className="flex gap-2">
                        <input
                            type="text" placeholder="Ticker (e.g. AAPL)" value={symbol}
                            onChange={e => setSymbol(e.target.value.toUpperCase())}
                            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/20"
                            required
                        />
                        <input
                            type="number" step="0.01" min="0.001" max="1" placeholder="Weight (0–1)" value={weight}
                            onChange={e => setWeight(e.target.valueAsNumber || "")}
                            className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/20"
                            required
                        />
                        <button type="submit" disabled={isAdding}
                            className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition-colors">
                            {isAdding ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                            Add
                        </button>
                    </form>
                    {addError && <p className="text-xs text-rose-400">{addError}</p>}

                    {/* Table */}
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

                    {/* Weight status */}
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
                                description="Weighted average Global Alignment Score across your constituents. Above 60 = broadly bullish signal environment."
                            />
                            <MetricBar
                                label="Diversification"
                                value={analysis.diversification_score}
                                description="Based on inter-asset price correlation (6mo). Higher = less concentrated risk. Below 40 suggests high overlap."
                            />

                            {/* Sector breakdown */}
                            {Object.keys(analysis.sector_breakdown ?? {}).length > 0 && (
                                <div>
                                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
                                        Sector Exposure
                                    </h3>
                                    <div className="space-y-2.5">
                                        {Object.entries(analysis.sector_breakdown)
                                            .sort(([, a]: any, [, b]: any) => b - a)
                                            .map(([sector, pct]: any) => (
                                                <div key={sector}>
                                                    <div className="flex justify-between text-xs mb-1">
                                                        <span className="text-slate-400 truncate max-w-[130px]">{sector}</span>
                                                        <span className="text-slate-200 font-mono">{pct.toFixed(1)}%</span>
                                                    </div>
                                                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                                                        <div className="bg-sky-500/70 h-1.5 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
                                                    </div>
                                                </div>
                                            ))
                                        }
                                    </div>
                                </div>
                            )}

                            {/* Benchmark hint */}
                            {portfolio.benchmark && (
                                <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 px-3 py-2.5">
                                    <p className="text-xs text-slate-500">
                                        Benchmark: <span className="text-slate-300 font-mono font-semibold">{portfolio.benchmark}</span>
                                        <span className="ml-1.5 text-slate-600">— comparison charts coming soon</span>
                                    </p>
                                </div>
                            )}

                            {/* Target return hint */}
                            {portfolio.target_return != null && (
                                <div className="rounded-lg bg-slate-800/50 border border-slate-700/50 px-3 py-2.5">
                                    <p className="text-xs text-slate-500">
                                        Target: <span className="text-emerald-400 font-semibold">{portfolio.target_return}% p.a.</span>
                                        <span className="ml-1.5 text-slate-600">— return tracking coming soon</span>
                                    </p>
                                </div>
                            )}
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    );
}
