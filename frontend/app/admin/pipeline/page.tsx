"use client";
/**
 * app/admin/pipeline/page.tsx
 * Manual data pipeline trigger page — run every Monday (or whenever needed)
 * to refresh OHLCV data, retrain ML models, and refresh news sentiment.
 *
 * Sequence: Seed → Train → News (each waits for the previous to finish)
 */
import { useState, useEffect, useCallback } from "react";
import useSWR from "swr";
import {
    Database, Cpu, Newspaper, Play, RefreshCw,
    CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight, Zap,
} from "lucide-react";
import {
    triggerBulkSeed, triggerBulkTrain, triggerBulkNewsSeed,
    fetchBulkSeedStatus, fetchBulkTrainStatus, fetchBulkNewsStatus,
    fetchPipelineOverview,
    type BulkSeedStatusDto, type BulkTrainStatusDto,
    type BulkNewsStatusDto, type PipelineOverviewDto,
} from "@/lib/api_bulk";

// ── helpers ───────────────────────────────────────────────────────────────────

function ProgressBar({ pct, color }: { pct: number; color: "blue" | "emerald" | "amber" | "violet" }) {
    const cls = { blue: "bg-blue-500", emerald: "bg-emerald-500", amber: "bg-amber-500", violet: "bg-violet-500" }[color];
    return (
        <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-500 ${cls}`} style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
    );
}

function StatusBadge({ running, done, failed }: { running: boolean; done: number; failed: number }) {
    if (running) return <span className="flex items-center gap-1 text-[11px] text-sky-400"><Loader2 className="h-3 w-3 animate-spin" /> Running</span>;
    if (done > 0 && failed === 0) return <span className="flex items-center gap-1 text-[11px] text-emerald-400"><CheckCircle2 className="h-3 w-3" /> Done</span>;
    if (failed > 0) return <span className="flex items-center gap-1 text-[11px] text-amber-400"><XCircle className="h-3 w-3" /> Done ({failed} failed)</span>;
    return <span className="text-[11px] text-slate-500">Idle</span>;
}

type Phase = "idle" | "seeding" | "training" | "news" | "complete";

// ── main page ─────────────────────────────────────────────────────────────────

export default function PipelinePage() {
    const [phase, setPhase]         = useState<Phase>("idle");
    const [msg, setMsg]             = useState<string | null>(null);
    const [seedPoll, setSeedPoll]   = useState(false);
    const [trainPoll, setTrainPoll] = useState(false);
    const [newsPoll, setNewsPoll]   = useState(false);
    const [showRecent, setShowRecent] = useState<Record<string, boolean>>({});

    // Overview — refreshes every 15s
    const { data: overview, mutate: mutateOverview } =
        useSWR<PipelineOverviewDto>("pipeline-overview", fetchPipelineOverview, { refreshInterval: 15_000 });

    // Live status — only polls while running
    const { data: seedStatus } = useSWR<BulkSeedStatusDto>(
        seedPoll ? "seed-status-live" : null, fetchBulkSeedStatus, { refreshInterval: 3000 });
    const { data: trainStatus } = useSWR<BulkTrainStatusDto>(
        trainPoll ? "train-status-live" : null, fetchBulkTrainStatus, { refreshInterval: 3000 });
    const { data: newsStatus } = useSWR<BulkNewsStatusDto>(
        newsPoll ? "news-status-live" : null, fetchBulkNewsStatus, { refreshInterval: 3000 });

    // Stop polling when each job finishes; advance sequence
    useEffect(() => {
        if (seedStatus && !seedStatus.running && seedPoll) {
            setSeedPoll(false);
            mutateOverview();
            if (phase === "seeding") { setPhase("training"); setMsg("✅ Seed done — starting training…"); }
        }
    }, [seedStatus, seedPoll, phase, mutateOverview]);

    useEffect(() => {
        if (trainStatus && !trainStatus.running && trainPoll) {
            setTrainPoll(false);
            mutateOverview();
            if (phase === "training") { setPhase("news"); setMsg("✅ Training done — refreshing news…"); }
        }
    }, [trainStatus, trainPoll, phase, mutateOverview]);

    useEffect(() => {
        if (newsStatus && !newsStatus.running && newsPoll) {
            setNewsPoll(false);
            mutateOverview();
            if (phase === "news") { setPhase("complete"); setMsg("✅ All done — data is fresh!"); }
        }
    }, [newsStatus, newsPoll, phase, mutateOverview]);

    // Auto-advance: start each phase when previous finishes
    useEffect(() => {
        if (phase === "training") { startTrain(); }
        if (phase === "news")     { startNews(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [phase]);

    // ── individual starters ────────────────────────────────────────────────

    const startSeed = useCallback(async (scope: "missing_only" | "all" = "missing_only") => {
        try {
            const r = await triggerBulkSeed(scope);
            setSeedPoll(true);
            setMsg(`▶ Seeding ${r.total_tickers} tickers (${scope})…`);
        } catch (e: any) { setMsg(`❌ Seed failed: ${e.message}`); setPhase("idle"); }
    }, []);

    const startTrain = useCallback(async () => {
        try {
            const r = await triggerBulkTrain("untrained_only");
            setTrainPoll(true);
            setMsg(`▶ Training ${r.total_tickers} symbols…`);
        } catch (e: any) { setMsg(`❌ Train failed: ${e.message}`); setPhase("idle"); }
    }, []);

    const startNews = useCallback(async () => {
        try {
            await triggerBulkNewsSeed(7);
            setNewsPoll(true);
            setMsg("▶ Refreshing 7-day news…");
        } catch (e: any) { setMsg(`❌ News failed: ${e.message}`); setPhase("idle"); }
    }, []);

    // ── "Run Full Refresh" — the main Monday button ────────────────────────

    const runFullRefresh = async () => {
        setPhase("seeding");
        setMsg("▶ Starting full refresh: Seed → Train → News");
        await startSeed("missing_only");
    };

    const isRunning = phase !== "idle" && phase !== "complete";

    const ov = overview;
    const seedPct  = ov ? (ov.seeding.seeded / Math.max(1, ov.ticker_universe.yf_valid) * 100) : 0;
    const trainPct = ov ? (ov.training.trained / Math.max(1, ov.seeding.seeded) * 100) : 0;

    return (
        <div className="mx-auto max-w-2xl space-y-6">

            {/* Header */}
            <div>
                <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
                    <Zap className="h-5 w-5 text-sky-400" /> Data Pipeline
                </h1>
                <p className="text-sm text-slate-400 mt-1">
                    Run every Monday to keep data fresh. Full cycle: Seed → Train → News (~30–60 min).
                </p>
            </div>

            {/* Status message */}
            {msg && (
                <div className={`rounded-lg border px-4 py-3 text-sm font-medium ${
                    phase === "complete"
                        ? "border-emerald-700/40 bg-emerald-950/20 text-emerald-300"
                        : isRunning
                        ? "border-sky-700/40 bg-sky-950/20 text-sky-300"
                        : "border-slate-700 bg-slate-900/50 text-slate-300"
                }`}>
                    {msg}
                </div>
            )}

            {/* ── BIG RUN BUTTON ─────────────────────────────────────────── */}
            <button
                onClick={runFullRefresh}
                disabled={isRunning}
                className="w-full flex items-center justify-center gap-3 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed px-6 py-4 text-base font-bold text-white transition-colors shadow-lg shadow-sky-900/30"
            >
                {isRunning
                    ? <><Loader2 className="h-5 w-5 animate-spin" /> Running… ({phase})</>
                    : <><Play className="h-5 w-5" /> Run Full Refresh (Seed → Train → News)</>
                }
            </button>

            {/* ── Phase cards ───────────────────────────────────────────── */}
            <div className="space-y-3">

                {/* Seed */}
                <div className={`rounded-xl border p-4 space-y-3 transition-colors ${phase === "seeding" ? "border-sky-700/50 bg-sky-950/10" : "border-slate-800"}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Database className="h-4 w-4 text-blue-400" />
                            <span className="text-sm font-semibold text-slate-200">1 · OHLCV Seed</span>
                            {(phase === "seeding" || seedPoll) && <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" />}
                        </div>
                        <StatusBadge
                            running={seedPoll}
                            done={seedStatus?.done ?? ov?.seeding.seeded ?? 0}
                            failed={seedStatus?.failed ?? ov?.seeding.failed ?? 0}
                        />
                    </div>

                    {ov && (
                        <div className="space-y-1.5">
                            <div className="flex justify-between text-xs text-slate-500">
                                <span>{ov.seeding.seeded} / {ov.ticker_universe.yf_valid} tickers seeded</span>
                                <span>{seedPct.toFixed(0)}%</span>
                            </div>
                            <ProgressBar pct={seedPct} color={seedPct >= 100 ? "emerald" : "blue"} />
                            {ov.seeding.last_run_at && (
                                <p className="text-[11px] text-slate-600">Last run: {new Date(ov.seeding.last_run_at).toLocaleString()}</p>
                            )}
                        </div>
                    )}

                    {seedPoll && seedStatus && (
                        <p className="text-xs text-sky-400 tabular-nums">
                            {seedStatus.done}/{seedStatus.total} done ({seedStatus.pct_complete.toFixed(0)}%)
                        </p>
                    )}

                    {/* Individual seed buttons */}
                    <div className="flex gap-2 flex-wrap">
                        <button onClick={() => startSeed("missing_only")} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1.5 text-xs font-semibold text-white transition-colors">
                            <Play className="h-3 w-3" /> Seed Missing
                        </button>
                        <button onClick={() => startSeed("all")} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors">
                            <RefreshCw className="h-3 w-3" /> Re-seed All
                        </button>
                    </div>

                    {/* Recent results collapsible */}
                    {(seedStatus?.recent?.length ?? 0) > 0 && (
                        <RecentList
                            items={seedStatus!.recent.map((r) => ({ symbol: r.symbol, status: r.status, detail: r.reason ?? `+${r.rows_added} rows` }))}
                            open={showRecent.seed}
                            onToggle={() => setShowRecent((s) => ({ ...s, seed: !s.seed }))}
                        />
                    )}
                </div>

                {/* Train */}
                <div className={`rounded-xl border p-4 space-y-3 transition-colors ${phase === "training" ? "border-violet-700/50 bg-violet-950/10" : "border-slate-800"}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Cpu className="h-4 w-4 text-violet-400" />
                            <span className="text-sm font-semibold text-slate-200">2 · ML Training</span>
                            {(phase === "training" || trainPoll) && <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />}
                        </div>
                        <StatusBadge
                            running={trainPoll}
                            done={trainStatus?.done ?? ov?.training.trained ?? 0}
                            failed={trainStatus?.failed ?? ov?.training.failed ?? 0}
                        />
                    </div>

                    {ov && (
                        <div className="space-y-1.5">
                            <div className="flex justify-between text-xs text-slate-500">
                                <span>{ov.training.trained} / {ov.seeding.seeded} trained
                                    {ov.training.avg_sharpe != null && <> · Avg Sharpe {ov.training.avg_sharpe.toFixed(2)}</>}
                                </span>
                                <span>{trainPct.toFixed(0)}%</span>
                            </div>
                            <ProgressBar pct={trainPct} color={trainPct >= 100 ? "emerald" : "violet"} />
                            {ov.training.last_run_at && (
                                <p className="text-[11px] text-slate-600">Last run: {new Date(ov.training.last_run_at).toLocaleString()}</p>
                            )}
                        </div>
                    )}

                    {trainPoll && trainStatus && (
                        <p className="text-xs text-violet-400 tabular-nums">
                            {trainStatus.current_symbol ?? "—"} / {trainStatus.current_timeframe ?? "—"} &nbsp;·&nbsp;
                            {trainStatus.done}/{trainStatus.total} ({trainStatus.pct_complete.toFixed(0)}%)
                        </p>
                    )}

                    <div className="flex gap-2 flex-wrap">
                        <button onClick={startTrain} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 px-3 py-1.5 text-xs font-semibold text-white transition-colors">
                            <Play className="h-3 w-3" /> Train Untrained
                        </button>
                        <button onClick={async () => { setPhase("training"); await triggerBulkTrain("retrain_all"); setTrainPoll(true); }} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors">
                            <RefreshCw className="h-3 w-3" /> Retrain All
                        </button>
                    </div>

                    {(trainStatus?.recent?.length ?? 0) > 0 && (
                        <RecentList
                            items={trainStatus!.recent.map((r) => ({ symbol: r.symbol, status: r.status, detail: r.sharpe != null ? `Sharpe ${r.sharpe.toFixed(2)}` : (r.reason ?? "") }))}
                            open={showRecent.train}
                            onToggle={() => setShowRecent((s) => ({ ...s, train: !s.train }))}
                        />
                    )}
                </div>

                {/* News */}
                <div className={`rounded-xl border p-4 space-y-3 transition-colors ${phase === "news" ? "border-amber-700/50 bg-amber-950/10" : "border-slate-800"}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Newspaper className="h-4 w-4 text-amber-400" />
                            <span className="text-sm font-semibold text-slate-200">3 · News Sentiment</span>
                            {(phase === "news" || newsPoll) && <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />}
                        </div>
                        <StatusBadge
                            running={newsPoll}
                            done={newsStatus?.done ?? 0}
                            failed={newsStatus?.failed ?? 0}
                        />
                    </div>

                    {ov?.news && (
                        <div className="text-xs text-slate-500 space-y-0.5">
                            <p>{ov.news.total_articles.toLocaleString()} articles stored</p>
                            {ov.news.last_fetch_at && <p>Last fetch: {new Date(ov.news.last_fetch_at).toLocaleString()}</p>}
                        </div>
                    )}

                    {newsPoll && newsStatus && (
                        <p className="text-xs text-amber-400 tabular-nums">
                            {newsStatus.done}/{newsStatus.total} ({newsStatus.pct_complete.toFixed(0)}%)
                        </p>
                    )}

                    <div className="flex gap-2 flex-wrap">
                        <button onClick={startNews} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-40 px-3 py-1.5 text-xs font-semibold text-white transition-colors">
                            <Play className="h-3 w-3" /> Refresh News (7d)
                        </button>
                        <button onClick={async () => { await triggerBulkNewsSeed(365); setNewsPoll(true); }} disabled={isRunning}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors">
                            <RefreshCw className="h-3 w-3" /> Backfill 1yr
                        </button>
                    </div>
                </div>
            </div>

            {/* Weekly reminder */}
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 text-xs text-slate-500 space-y-1">
                <p className="font-semibold text-slate-400">📅 Recommended weekly schedule (Monday morning)</p>
                <p>1. Click <strong className="text-slate-300">Run Full Refresh</strong> — waits for each step automatically</p>
                <p>2. Seed missing fills any gaps since last run (fast, ~5 min)</p>
                <p>3. Train untrained adds models for newly-seeded symbols (~20–40 min)</p>
                <p>4. News refresh pulls last 7 days of headlines and scores sentiment (~5 min)</p>
                <p className="text-slate-600 pt-1">For a first-time full seed of all 1000 tickers, use Re-seed All + Retrain All (may take 2–4 hours).</p>
            </div>
        </div>
    );
}

// ── RecentList sub-component ──────────────────────────────────────────────────

function RecentList({
    items, open, onToggle,
}: { items: Array<{ symbol: string; status: string; detail: string }>; open: boolean; onToggle: () => void }) {
    return (
        <div>
            <button onClick={onToggle} className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors">
                {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                Recent results ({items.length})
            </button>
            {open && (
                <div className="mt-1.5 max-h-40 overflow-y-auto space-y-0.5">
                    {items.slice(0, 30).map((item, i) => (
                        <div key={i} className="flex items-center gap-2 text-[11px] px-2 py-0.5 rounded">
                            <span className={`font-mono font-semibold ${item.status === "done" ? "text-emerald-400" : item.status === "failed" ? "text-rose-400" : "text-amber-400"}`}>
                                {item.symbol}
                            </span>
                            <span className="text-slate-600">{item.detail}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
