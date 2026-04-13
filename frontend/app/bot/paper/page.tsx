"use client";
/**
 * app/bot/paper/page.tsx — Sprint 47
 * Paper Trading Bot dashboard: status banner, open positions, audit log, settings.
 */
import { useState, useEffect, useCallback } from "react";
import useSWR from "swr";
import {
    Bot, Power, PowerOff, Settings, AlertTriangle, ChevronDown, ChevronUp,
    TrendingUp, TrendingDown, Minus, RefreshCw, X, Loader2, CheckCircle2,
    Shield, Zap, BarChart2,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import {
    fetchBotConfig, fetchBotPositions, fetchBotAuditLog, fetchBotPerformance,
    enableBot, disableBot, haltBot, resumeBot, updateBotConfig,
    type BotConfigDto, type BotPositionDto, type BotAuditLogEntry, type BotPerformanceDto,
} from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined, decimals = 1): string {
    if (v == null) return "—";
    return `${v >= 0 ? "+" : ""}${v.toFixed(decimals)}%`;
}
function usd(v: number | null | undefined): string {
    if (v == null) return "—";
    return `${v >= 0 ? "+" : ""}$${Math.abs(v).toFixed(2)}`;
}
function relTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1) return "just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
}

const ACTION_STYLES: Record<string, string> = {
    BUY:     "bg-emerald-900/40 text-emerald-400 border border-emerald-700/30",
    SELL:    "bg-rose-900/40 text-rose-400 border border-rose-700/30",
    HOLD:    "bg-slate-800 text-slate-400",
    SKIP:    "bg-slate-900 text-slate-600",
    HALT:    "bg-amber-900/40 text-amber-400 border border-amber-700/30",
    RESUME:  "bg-sky-900/40 text-sky-400 border border-sky-700/30",
    EVALUATE:"bg-slate-800 text-slate-500",
};

const GRADE_COLOR: Record<string, string> = {
    "A+": "text-emerald-400", A: "text-emerald-400",
    B: "text-sky-400", C: "text-amber-400",
    D: "text-orange-400", F: "text-rose-400",
};

// ── Settings slide-over ────────────────────────────────────────────────────

function SettingsPanel({
    config, onClose, onSaved,
}: { config: BotConfigDto; onClose: () => void; onSaved: () => void }) {
    const [strategy, setStrategy]     = useState(config.strategy);
    const [minGrade, setMinGrade]      = useState(config.min_grade);
    const [maxPos, setMaxPos]          = useState(config.max_position_pct * 100);
    const [maxTotal, setMaxTotal]      = useState(config.max_total_pct * 100);
    const [lossLimit, setLossLimit]    = useState(config.daily_loss_limit * 100);
    const [portfolio, setPortfolio]    = useState(config.portfolio_value);
    const [saving, setSaving]          = useState(false);
    const [err, setErr]                = useState<string | null>(null);

    const save = async () => {
        setSaving(true); setErr(null);
        try {
            await updateBotConfig({
                strategy, min_grade: minGrade,
                max_position_pct: maxPos / 100,
                max_total_pct: maxTotal / 100,
                daily_loss_limit: lossLimit / 100,
                portfolio_value: portfolio,
            });
            onSaved();
        } catch (e: any) { setErr(e.message); }
        finally { setSaving(false); }
    };

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-sm bg-slate-950 border-l border-slate-800 flex flex-col h-full overflow-y-auto">
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                        <Settings className="h-4 w-4 text-slate-400" />
                        <h2 className="text-sm font-semibold text-slate-200">Bot Settings</h2>
                    </div>
                    <button onClick={onClose} className="text-slate-500 hover:text-slate-300"><X className="h-4 w-4" /></button>
                </div>
                <div className="flex-1 p-5 space-y-6">
                    {/* Strategy */}
                    <div>
                        <label className="text-xs font-medium text-slate-400 block mb-2">Strategy</label>
                        <div className="flex gap-2">
                            {(["conservative","balanced","aggressive"] as const).map((s) => (
                                <button key={s} onClick={() => setStrategy(s)}
                                    className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium capitalize transition-colors ${strategy === s ? "border-sky-600 bg-sky-600/20 text-sky-300" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}>
                                    {s}
                                </button>
                            ))}
                        </div>
                        <p className="text-[11px] text-slate-600 mt-1.5">
                            {strategy === "conservative" ? "A+ only, small positions" : strategy === "balanced" ? "A/B signals, standard sizes" : "B+ signals, larger positions"}
                        </p>
                    </div>

                    {/* Min Grade */}
                    <div>
                        <label className="text-xs font-medium text-slate-400 block mb-2">Minimum Signal Grade</label>
                        <div className="flex gap-2">
                            {["A+","A","B"].map((g) => (
                                <button key={g} onClick={() => setMinGrade(g)}
                                    className={`flex-1 rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${minGrade === g ? "border-emerald-600 bg-emerald-600/20 text-emerald-300" : "border-slate-700 text-slate-400 hover:border-slate-500"}`}>
                                    {g}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Sliders */}
                    {[
                        { label: "Max position size", val: maxPos, set: setMaxPos, min: 5, max: 25, suffix: "%" },
                        { label: "Max total deployed", val: maxTotal, set: setMaxTotal, min: 40, max: 100, suffix: "%" },
                        { label: "Daily loss limit", val: lossLimit, set: setLossLimit, min: 1, max: 10, suffix: "%" },
                    ].map(({ label, val, set, min, max, suffix }) => (
                        <div key={label}>
                            <div className="flex justify-between text-xs mb-1.5">
                                <span className="text-slate-400 font-medium">{label}</span>
                                <span className="text-slate-200 font-bold tabular-nums">{val.toFixed(0)}{suffix}</span>
                            </div>
                            <input type="range" min={min} max={max} step={1} value={val}
                                onChange={(e) => set(parseFloat(e.target.value))}
                                className="w-full accent-sky-500" />
                        </div>
                    ))}

                    {/* Portfolio value */}
                    <div>
                        <label className="text-xs font-medium text-slate-400 block mb-1.5">Paper portfolio value ($)</label>
                        <input type="number" value={portfolio} onChange={(e) => setPortfolio(parseFloat(e.target.value) || 10000)}
                            min={100} step={100}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm tabular-nums text-slate-200 focus:border-sky-500 focus:outline-none" />
                    </div>

                    {err && <p className="text-xs text-rose-400">{err}</p>}
                </div>
                <div className="px-5 py-4 border-t border-slate-800">
                    <button onClick={save} disabled={saving}
                        className="w-full flex items-center justify-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 px-4 py-2.5 text-sm font-semibold text-white transition-colors">
                        {saving ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</> : "Save Settings"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function PaperBotPage() {
    const { user } = useAuth();
    const [showSettings, setShowSettings] = useState(false);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [logSymbol, setLogSymbol] = useState("");

    const { data: config, mutate: mutateConfig } = useSWR("bot-config", fetchBotConfig, { refreshInterval: 30_000 });
    const { data: positions, mutate: mutatePos } = useSWR("bot-positions", fetchBotPositions, { refreshInterval: 60_000 });
    const { data: perf } = useSWR("bot-perf", fetchBotPerformance, { refreshInterval: 60_000 });
    const { data: logs } = useSWR(
        ["bot-log", logSymbol],
        () => fetchBotAuditLog(100, logSymbol || undefined),
        { refreshInterval: 30_000 },
    );

    const refresh = useCallback(() => { mutateConfig(); mutatePos(); }, [mutateConfig, mutatePos]);

    const doAction = async (action: string, fn: () => Promise<any>) => {
        setActionLoading(action);
        try { await fn(); refresh(); }
        catch (e: any) { alert(e.message); }
        finally { setActionLoading(null); }
    };

    if (!config) return (
        <div className="flex items-center gap-2 text-sm text-slate-500 py-12 justify-center">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading bot…
        </div>
    );

    const isHalted   = config.halt_flag;
    const isEnabled  = config.is_enabled;
    const openPos    = (positions ?? []).filter((p) => p.is_open);
    const closedPos  = (positions ?? []).filter((p) => !p.is_open);
    const deployed   = openPos.reduce((s, p) => s + p.size_usd, 0);
    const deployedPct = config.portfolio_value > 0 ? (deployed / config.portfolio_value * 100).toFixed(1) : "0.0";

    return (
        <div className="mx-auto max-w-4xl space-y-6">
            {showSettings && (
                <SettingsPanel
                    config={config}
                    onClose={() => setShowSettings(false)}
                    onSaved={() => { setShowSettings(false); mutateConfig(); }}
                />
            )}

            {/* ── Status Banner ──────────────────────────────────────────── */}
            <div className={`rounded-xl border px-5 py-4 ${
                isHalted   ? "border-amber-700/40 bg-amber-950/20"
                : isEnabled ? "border-emerald-700/40 bg-emerald-950/10"
                :             "border-slate-700 bg-slate-900/40"
            }`}>
                <div className="flex flex-wrap items-center gap-3">
                    {/* Status */}
                    <div className="flex items-center gap-2.5 flex-1 min-w-0">
                        <Bot className={`h-5 w-5 flex-shrink-0 ${isHalted ? "text-amber-400" : isEnabled ? "text-emerald-400" : "text-slate-500"}`} />
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="text-sm font-semibold text-slate-100">Paper Trading Bot</span>
                                <span className={`text-[10px] font-bold rounded-full px-2 py-0.5 ${
                                    isHalted   ? "bg-amber-900/60 text-amber-300"
                                    : isEnabled ? "bg-emerald-900/60 text-emerald-300"
                                    :             "bg-slate-800 text-slate-500"
                                }`}>
                                    {isHalted ? "HALTED" : isEnabled ? "ACTIVE" : "INACTIVE"}
                                </span>
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">
                                Portfolio: ${config.portfolio_value.toLocaleString()}
                                {" · "}Deployed: ${deployed.toFixed(0)} ({deployedPct}%)
                                {perf && <> · PnL: <span className={perf.total_pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"}>{usd(perf.total_pnl_usd)} ({pct(perf.total_pnl_pct)})</span></>}
                                {perf?.win_rate != null && <> · Win rate: {(perf.win_rate * 100).toFixed(0)}%</>}
                            </p>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {isHalted ? (
                            <button onClick={() => doAction("resume", resumeBot)} disabled={!!actionLoading}
                                className="flex items-center gap-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40 transition-colors">
                                {actionLoading === "resume" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Power className="h-3.5 w-3.5" />}
                                Resume
                            </button>
                        ) : isEnabled ? (
                            <button onClick={() => doAction("halt", () => haltBot(false))} disabled={!!actionLoading}
                                className="flex items-center gap-1.5 rounded-lg bg-amber-700 hover:bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40 transition-colors">
                                {actionLoading === "halt" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                                Halt Bot
                            </button>
                        ) : (
                            <button onClick={() => doAction("enable", enableBot)} disabled={!!actionLoading}
                                className="flex items-center gap-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40 transition-colors">
                                {actionLoading === "enable" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Power className="h-3.5 w-3.5" />}
                                Enable Bot
                            </button>
                        )}
                        {isEnabled && !isHalted && (
                            <button onClick={() => doAction("disable", disableBot)} disabled={!!actionLoading}
                                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 disabled:opacity-40 transition-colors">
                                {actionLoading === "disable" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <PowerOff className="h-3.5 w-3.5" />}
                                Disable
                            </button>
                        )}
                        <button onClick={() => setShowSettings(true)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
                            <Settings className="h-4 w-4" />
                        </button>
                    </div>
                </div>

                {/* Config summary row */}
                <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-slate-500">
                    <span>Strategy: <span className="text-slate-300 capitalize">{config.strategy}</span></span>
                    <span>Min grade: <span className={`font-bold ${GRADE_COLOR[config.min_grade] ?? "text-slate-300"}`}>{config.min_grade}</span></span>
                    <span>Max position: <span className="text-slate-300">{(config.max_position_pct * 100).toFixed(0)}%</span></span>
                    <span>Daily loss limit: <span className="text-slate-300">{(config.daily_loss_limit * 100).toFixed(0)}%</span></span>
                </div>
            </div>

            {/* ── Performance stats ──────────────────────────────────────── */}
            {perf && perf.total_trades > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                        { label: "Total PnL", value: usd(perf.total_pnl_usd), sub: pct(perf.total_pnl_pct), color: perf.total_pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400" },
                        { label: "Win Rate", value: `${((perf.win_rate ?? 0) * 100).toFixed(0)}%`, sub: `${perf.total_trades} trades`, color: "text-sky-400" },
                        { label: "Best Trade", value: usd(perf.best_trade_usd), sub: pct(perf.best_trade_pct), color: "text-emerald-400" },
                        { label: "Worst Trade", value: usd(perf.worst_trade_usd), sub: pct(perf.worst_trade_pct), color: "text-rose-400" },
                    ].map(({ label, value, sub, color }) => (
                        <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                            <p className="text-[11px] text-slate-500 mb-1">{label}</p>
                            <p className={`text-sm font-bold tabular-nums ${color}`}>{value}</p>
                            <p className="text-[11px] text-slate-500 tabular-nums">{sub}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* ── Open Positions ─────────────────────────────────────────── */}
            <div className="rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                    <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                        <BarChart2 className="h-4 w-4 text-slate-400" />
                        Open Positions
                        {openPos.length > 0 && (
                            <span className="text-[11px] text-slate-500 bg-slate-800 rounded-full px-2 py-0.5">{openPos.length}</span>
                        )}
                    </h2>
                    <button onClick={() => mutatePos()} className="p-1.5 text-slate-500 hover:text-slate-300 rounded-lg hover:bg-slate-800 transition-colors">
                        <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                </div>

                {openPos.length === 0 ? (
                    <div className="px-4 py-8 text-center">
                        <Bot className="h-8 w-8 text-slate-700 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">No open positions</p>
                        <p className="text-xs text-slate-600 mt-1">
                            {isEnabled ? "Bot is watching watchlist symbols — positions open automatically on A/B signals" : "Enable the bot to start trading"}
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-800">
                                    <th className="text-left px-4 py-2.5">Symbol</th>
                                    <th className="text-left px-3 py-2.5">Grade</th>
                                    <th className="text-right px-3 py-2.5">Entry $</th>
                                    <th className="text-right px-3 py-2.5">Size</th>
                                    <th className="text-right px-3 py-2.5">Unrealised PnL</th>
                                    <th className="text-right px-3 py-2.5">Since</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {openPos.map((p) => (
                                    <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                                        <td className="px-4 py-3 font-mono font-semibold text-slate-100">{p.symbol}</td>
                                        <td className="px-3 py-3">
                                            <span className={`text-xs font-bold ${GRADE_COLOR[p.entry_grade] ?? "text-slate-400"}`}>{p.entry_grade}</span>
                                        </td>
                                        <td className="px-3 py-3 text-right tabular-nums text-slate-300">${p.entry_price.toFixed(2)}</td>
                                        <td className="px-3 py-3 text-right tabular-nums text-slate-400">${p.size_usd.toFixed(0)}</td>
                                        <td className="px-3 py-3 text-right tabular-nums">
                                            {p.unrealised_pnl_usd != null ? (
                                                <span className={p.unrealised_pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"}>
                                                    {usd(p.unrealised_pnl_usd)} ({pct(p.unrealised_pnl_pct)})
                                                </span>
                                            ) : <span className="text-slate-600">—</span>}
                                        </td>
                                        <td className="px-3 py-3 text-right text-slate-500 text-xs">{relTime(p.opened_at)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ── Audit Log ──────────────────────────────────────────────── */}
            <div className="rounded-xl border border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                    <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                        <Zap className="h-4 w-4 text-slate-400" />
                        Audit Log
                    </h2>
                    <div className="flex items-center gap-2">
                        <input
                            value={logSymbol}
                            onChange={(e) => setLogSymbol(e.target.value.toUpperCase())}
                            placeholder="Filter symbol…"
                            className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs font-mono text-slate-300 placeholder-slate-600 focus:border-sky-500 focus:outline-none w-28"
                        />
                    </div>
                </div>

                {!logs || logs.length === 0 ? (
                    <div className="px-4 py-8 text-center">
                        <p className="text-sm text-slate-500">No activity logged yet</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-800">
                                    <th className="text-left px-4 py-2.5">Time</th>
                                    <th className="text-left px-3 py-2.5">Symbol</th>
                                    <th className="text-left px-3 py-2.5">Action</th>
                                    <th className="text-left px-3 py-2.5">Grade</th>
                                    <th className="text-right px-3 py-2.5">Price</th>
                                    <th className="text-left px-3 py-2.5 hidden sm:table-cell">Reason</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-slate-800/20">
                                        <td className="px-4 py-2 text-slate-500 whitespace-nowrap">{relTime(log.logged_at)}</td>
                                        <td className="px-3 py-2 font-mono text-slate-300">{log.symbol ?? "—"}</td>
                                        <td className="px-3 py-2">
                                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${ACTION_STYLES[log.action] ?? "text-slate-400"}`}>
                                                {log.action}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2">
                                            <span className={`font-bold ${GRADE_COLOR[log.grade ?? ""] ?? "text-slate-500"}`}>{log.grade ?? "—"}</span>
                                        </td>
                                        <td className="px-3 py-2 text-right tabular-nums text-slate-400">
                                            {log.price != null ? `$${log.price.toFixed(2)}` : "—"}
                                        </td>
                                        <td className="px-3 py-2 text-slate-500 max-w-xs truncate hidden sm:table-cell">{log.reason}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ── Disclaimer ─────────────────────────────────────────────── */}
            <p className="text-xs text-slate-600 text-center">
                Paper trading mode only — no real money is deployed. All trades are simulated using live GAS signals and current prices.
                Past paper performance does not guarantee future results. Not financial advice.
            </p>
        </div>
    );
}
