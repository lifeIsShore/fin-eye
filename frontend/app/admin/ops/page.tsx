"use client";

import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import useSWR from "swr";
import {
    fetchOpsHealth,
    fetchOpsMetrics,
    fetchOpsAlerts,
    fetchOpsJobs,
    type OpsHealthDto,
    type OpsMetricsDto,
    type OpsAlertsDto,
    type OpsJobDto,
    type OpsRouteStats,
    type OpsPipelineRow,
} from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function fetchBackupStatus() {
    const res = await fetch(`${API_BASE_URL}/api/v1/ops/backup-status`, { headers: authHeaders(), cache: "no-store" });
    if (!res.ok) throw new Error("Failed");
    return res.json();
}

async function triggerBackupNow() {
    const res = await fetch(`${API_BASE_URL}/api/v1/ops/backup-now`, { method: "POST", headers: authHeaders() });
    if (!res.ok) throw new Error("Failed to trigger backup");
    return res.json();
}
import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock,
    Database,
    Loader2,
    RefreshCw,
    Server,
    Zap,
    XCircle,
    CalendarClock,
    Cpu,
    HardDrive,
    Play,
} from "lucide-react";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, unit = "ms"): string {
    if (n == null) return "—";
    return `${n.toLocaleString()}${unit}`;
}

function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "—";
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit", second: "2-digit",
        });
    } catch { return iso; }
}

function timeAgo(iso: string | null | undefined): string {
    if (!iso) return "—";
    try {
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return "just now";
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        return `${Math.floor(hrs / 24)}d ago`;
    } catch { return "—"; }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusDot({ ok }: { ok: boolean }) {
    return (
        <span className={`inline-block h-2 w-2 rounded-full flex-shrink-0 ${ok ? "bg-emerald-400" : "bg-rose-500 animate-pulse"}`} />
    );
}

function SectionHeader({ title, icon: Icon }: { title: string; icon: React.ElementType }) {
    return (
        <div className="flex items-center gap-2 mb-3">
            <Icon className="h-4 w-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">{title}</h2>
        </div>
    );
}

function HealthPanel({ data }: { data: OpsHealthDto }) {
    const ok = data.status === "ok";
    const components = [
        { label: "Database", value: data.components.database },
        { label: "Redis", value: data.components.redis },
        { label: "Pipelines", value: data.components.pipelines },
    ];
    return (
        <div className={`rounded-2xl border p-5 ${ok ? "border-emerald-700/30 bg-emerald-950/10" : "border-rose-700/30 bg-rose-950/10"}`}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    {ok
                        ? <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                        : <XCircle className="h-5 w-5 text-rose-400" />
                    }
                    <span className={`text-base font-bold ${ok ? "text-emerald-300" : "text-rose-300"}`}>
                        System {ok ? "Healthy" : "Degraded"}
                    </span>
                </div>
                <span className="text-xs text-slate-500">{fmtDate(data.checked_at)}</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
                {components.map((c) => (
                    <div key={c.label} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2">
                        <StatusDot ok={c.value === "ok"} />
                        <div>
                            <p className="text-xs text-slate-500">{c.label}</p>
                            <p className={`text-xs font-semibold capitalize ${c.value === "ok" ? "text-emerald-400" : "text-rose-400"}`}>{c.value}</p>
                        </div>
                    </div>
                ))}
            </div>
            {data.pipeline_issues.length > 0 && (
                <ul className="mt-3 space-y-1">
                    {data.pipeline_issues.map((issue, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-rose-300">
                            <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                            {issue}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

function AlertsPanel({ data }: { data: OpsAlertsDto }) {
    if (data.all_clear) {
        return (
            <div className="rounded-2xl border border-emerald-700/20 bg-emerald-950/10 p-4 flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                <div>
                    <p className="text-sm font-semibold text-emerald-300">All clear</p>
                    <p className="text-xs text-slate-500">No threshold breaches detected · {fmtDate(data.evaluated_at)}</p>
                </div>
            </div>
        );
    }
    return (
        <div className="space-y-2">
            {data.breaches.map((b, i) => (
                <div key={i} className={`rounded-xl border p-3.5 flex items-start gap-3 ${b.severity === "error" ? "border-rose-700/30 bg-rose-950/10" : "border-amber-700/30 bg-amber-950/10"}`}>
                    <AlertTriangle className={`h-4 w-4 flex-shrink-0 mt-0.5 ${b.severity === "error" ? "text-rose-400" : "text-amber-400"}`} />
                    <div className="min-w-0">
                        <p className={`text-xs font-semibold ${b.severity === "error" ? "text-rose-300" : "text-amber-300"}`}>
                            {b.type.replace(/_/g, " ").toUpperCase()}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">{b.message}</p>
                    </div>
                </div>
            ))}
        </div>
    );
}

function PipelinesTable({ rows }: { rows: OpsPipelineRow[] }) {
    if (!rows.length) return <p className="text-xs text-slate-500 py-4 text-center">No pipeline runs recorded yet — jobs will populate this after first run.</p>;
    return (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-xs">
                <thead>
                    <tr className="border-b border-slate-800 text-slate-500">
                        <th className="px-3 py-2.5 text-left font-medium">Job</th>
                        <th className="px-3 py-2.5 text-left font-medium">Last Run</th>
                        <th className="px-3 py-2.5 text-right font-medium">Duration</th>
                        <th className="px-3 py-2.5 text-right font-medium">Success Rate</th>
                        <th className="px-3 py-2.5 text-left font-medium">Status</th>
                        <th className="px-3 py-2.5 text-left font-medium">Detail</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((r) => (
                        <tr key={r.job_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                            <td className="px-3 py-2.5 font-mono text-slate-300">{r.job_id}</td>
                            <td className="px-3 py-2.5 text-slate-400">
                                {timeAgo(r.last_run_at)}
                                <span className="block text-[10px] text-slate-600">{fmtDate(r.last_run_at)}</span>
                            </td>
                            <td className="px-3 py-2.5 text-right text-slate-400">{fmt(r.last_duration_ms)}</td>
                            <td className="px-3 py-2.5 text-right">
                                <span className={`font-semibold ${r.success_rate_pct >= 80 ? "text-emerald-400" : r.success_rate_pct >= 50 ? "text-amber-400" : "text-rose-400"}`}>
                                    {r.success_rate_pct}%
                                </span>
                                <span className="text-slate-600 ml-1">({r.total_runs_recorded})</span>
                            </td>
                            <td className="px-3 py-2.5">
                                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${r.last_success ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}`}>
                                    <StatusDot ok={r.last_success} />
                                    {r.last_success ? "OK" : "FAILED"}
                                </span>
                            </td>
                            <td className="px-3 py-2.5 text-slate-500 max-w-xs truncate">{r.last_detail || "—"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function ApiRoutesTable({ routes }: { routes: OpsRouteStats[] }) {
    if (!routes.length) return <p className="text-xs text-slate-500 py-4 text-center">No API requests recorded yet.</p>;
    return (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-xs">
                <thead>
                    <tr className="border-b border-slate-800 text-slate-500">
                        <th className="px-3 py-2.5 text-left font-medium">Route</th>
                        <th className="px-3 py-2.5 text-right font-medium">Requests</th>
                        <th className="px-3 py-2.5 text-right font-medium">Err Rate</th>
                        <th className="px-3 py-2.5 text-right font-medium">P50</th>
                        <th className="px-3 py-2.5 text-right font-medium">P95</th>
                        <th className="px-3 py-2.5 text-right font-medium">P99</th>
                    </tr>
                </thead>
                <tbody>
                    {routes.map((r) => (
                        <tr key={r.route} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                            <td className="px-3 py-2 font-mono text-slate-300 max-w-xs truncate">{r.route}</td>
                            <td className="px-3 py-2 text-right text-slate-400">{r.total_requests.toLocaleString()}</td>
                            <td className="px-3 py-2 text-right">
                                <span className={r.error_rate_pct > 10 ? "text-rose-400 font-semibold" : r.error_rate_pct > 0 ? "text-amber-400" : "text-slate-500"}>
                                    {r.error_rate_pct}%
                                </span>
                            </td>
                            <td className="px-3 py-2 text-right text-slate-400">{fmt(r.latency_ms.p50)}</td>
                            <td className={`px-3 py-2 text-right font-semibold ${(r.latency_ms.p95 ?? 0) > 2000 ? "text-rose-400" : "text-slate-400"}`}>
                                {fmt(r.latency_ms.p95)}
                            </td>
                            <td className="px-3 py-2 text-right text-slate-400">{fmt(r.latency_ms.p99)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function JobsTable({ jobs }: { jobs: OpsJobDto[] }) {
    return (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-xs">
                <thead>
                    <tr className="border-b border-slate-800 text-slate-500">
                        <th className="px-3 py-2.5 text-left font-medium">Job ID</th>
                        <th className="px-3 py-2.5 text-left font-medium">Name</th>
                        <th className="px-3 py-2.5 text-left font-medium">Trigger</th>
                        <th className="px-3 py-2.5 text-left font-medium">Next Run</th>
                    </tr>
                </thead>
                <tbody>
                    {jobs.map((j) => (
                        <tr key={j.id} className="border-b border-slate-800/50">
                            <td className="px-3 py-2.5 font-mono text-slate-300">{j.id}</td>
                            <td className="px-3 py-2.5 text-slate-400">{j.name}</td>
                            <td className="px-3 py-2.5 font-mono text-slate-500 text-[10px]">{j.trigger}</td>
                            <td className="px-3 py-2.5 text-slate-400">
                                {j.next_run_at ? fmtDate(j.next_run_at) : <span className="text-slate-600">—</span>}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function BackupPanel({ data, onTrigger }: { data: any; onTrigger: () => void }) {
    const last = data?.last_run;
    return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-5 space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <HardDrive className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-semibold text-slate-300">
                        {data?.local_files_count ?? 0} local backup file(s)
                    </span>
                    <span className="text-xs text-slate-600">{data?.backup_dir}</span>
                </div>
                <button
                    onClick={onTrigger}
                    className="flex items-center gap-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors"
                >
                    <Play className="h-3 w-3" /> Backup Now
                </button>
            </div>

            {last ? (
                <div className="flex items-center gap-4 text-xs">
                    <span className={`flex items-center gap-1.5 font-semibold ${
                        last.last_success ? "text-emerald-400" : "text-rose-400"
                    }`}>
                        <StatusDot ok={last.last_success} />
                        {last.last_success ? "Last backup succeeded" : "Last backup FAILED"}
                    </span>
                    <span className="text-slate-500">{timeAgo(last.last_run_at)}</span>
                    <span className="text-slate-600">{fmt(last.last_duration_ms)}</span>
                    {last.last_detail && <span className="text-slate-600 truncate max-w-xs">{last.last_detail}</span>}
                </div>
            ) : (
                <p className="text-xs text-slate-600">No backup runs recorded yet — first run at 02:00 UTC.</p>
            )}

            {data?.recent_files?.length > 0 && (
                <div className="space-y-1.5">
                    {data.recent_files.slice(0, 5).map((f: any) => (
                        <div key={f.filename} className="flex items-center justify-between rounded-lg bg-slate-800/40 px-3 py-2 text-xs">
                            <span className="font-mono text-slate-400">{f.filename}</span>
                            <span className="text-slate-500">{f.size_mb} MB · {fmtDate(f.modified_at)}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const REFRESH_INTERVAL = 30_000; // 30 s

export default function OpsPage() {
    const { user, loading: authLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!authLoading && (!user || !(user as any).is_admin)) {
            router.replace("/");
        }
    }, [user, authLoading, router]);

    const { data: health, mutate: refetchHealth } = useSWR<OpsHealthDto>("ops-health", fetchOpsHealth, { refreshInterval: REFRESH_INTERVAL });
    const { data: metrics, mutate: refetchMetrics } = useSWR<OpsMetricsDto>("ops-metrics", fetchOpsMetrics, { refreshInterval: REFRESH_INTERVAL });
    const { data: alerts, mutate: refetchAlerts } = useSWR<OpsAlertsDto>("ops-alerts", fetchOpsAlerts, { refreshInterval: REFRESH_INTERVAL });
    const { data: jobs } = useSWR<OpsJobDto[]>("ops-jobs", fetchOpsJobs, { refreshInterval: 120_000 });
    const { data: backupStatus, mutate: refetchBackup } = useSWR("ops-backup", fetchBackupStatus, { refreshInterval: 60_000 });

    const handleTriggerBackup = useCallback(async () => {
        try {
            await triggerBackupNow();
            setTimeout(() => refetchBackup(), 3000);
        } catch { /* silent */ }
    }, [refetchBackup]);

    const refetchAll = useCallback(() => {
        refetchHealth(); refetchMetrics(); refetchAlerts(); refetchBackup();
    }, [refetchHealth, refetchMetrics, refetchAlerts, refetchBackup]);

    if (authLoading || !user) return (
        <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
    );

    return (
        <div className="space-y-8">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <header className="flex items-center justify-between border-b border-slate-800 pb-5">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800 border border-slate-700">
                        <Activity className="h-5 w-5 text-slate-300" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-slate-100">Ops Dashboard</h1>
                        <p className="text-xs text-slate-500">API latency · pipeline health · threshold alerts · auto-refreshes every 30s</p>
                    </div>
                </div>
                <button
                    onClick={refetchAll}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
                >
                    <RefreshCw className="h-3.5 w-3.5" /> Refresh
                </button>
            </header>

            {/* ── Health ─────────────────────────────────────────────────────── */}
            <section>
                <SectionHeader title="System Health" icon={Server} />
                {health ? <HealthPanel data={health} /> : <div className="text-xs text-slate-500 py-4">Loading…</div>}
            </section>

            {/* ── Threshold Alerts ───────────────────────────────────────────── */}
            <section>
                <SectionHeader title="Threshold Alerts" icon={AlertTriangle} />
                {alerts ? <AlertsPanel data={alerts} /> : <div className="text-xs text-slate-500 py-4">Loading…</div>}
            </section>

            {/* ── Pipelines ──────────────────────────────────────────────────── */}
            <section>
                <SectionHeader title="Data Pipeline Jobs" icon={Zap} />
                <PipelinesTable rows={metrics?.pipelines ?? []} />
            </section>

            {/* ── Inference stats ─────────────────────────────────────────────── */}
            {metrics && (
                <section>
                    <SectionHeader title="Model Inference" icon={Cpu} />
                    <div className="grid grid-cols-3 gap-3">
                        {[
                            { label: "Samples tracked", value: metrics.inference.count.toLocaleString(), unit: "" },
                            { label: "Avg latency", value: fmt(metrics.inference.avg_ms), unit: "" },
                            { label: "P95 latency", value: fmt(metrics.inference.p95_ms), unit: "", warn: (metrics.inference.p95_ms ?? 0) > 5000 },
                        ].map((s) => (
                            <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                                <p className="text-xs text-slate-500 mb-0.5">{s.label}</p>
                                <p className={`text-xl font-black ${(s as any).warn ? "text-rose-400" : "text-slate-100"}`}>{s.value}</p>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* ── API Routes ─────────────────────────────────────────────────── */}
            <section>
                <div className="flex items-center justify-between mb-3">
                    <SectionHeader title="API Route Metrics" icon={Activity} />
                    {metrics && <span className="text-xs text-slate-500">{metrics.api.total_routes_tracked} routes tracked · snapshot {fmtDate(metrics.snapshot_at)}</span>}
                </div>
                <ApiRoutesTable routes={metrics?.api.routes ?? []} />
            </section>

            {/* ── Scheduled Jobs ─────────────────────────────────────────────── */}
            <section>
                <SectionHeader title="Scheduled Jobs" icon={CalendarClock} />
                {jobs ? <JobsTable jobs={jobs} /> : <div className="text-xs text-slate-500 py-4">Loading…</div>}
            </section>

            {/* ── Server uptime ──────────────────────────────────────────────── */}
            <section>
                <SectionHeader title="Database Backups" icon={HardDrive} />
                <BackupPanel data={backupStatus} onTrigger={handleTriggerBackup} />
            </section>

            {metrics && (
                <p className="text-xs text-slate-600 border-t border-slate-800/50 pt-4">
                    Server started: {fmtDate(metrics.server_started_at)} · metrics are in-process (reset on restart)
                </p>
            )}
        </div>
    );
}
