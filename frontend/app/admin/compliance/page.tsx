"use client";

/**
 * /admin/compliance — Sprint 55
 * Compliance audit log viewer: date-range filter, tenant selector,
 * summary stats, log table, and CSV export.
 * Admin-only (redirects away for non-admins via useAuth guard).
 */

import { useState, useCallback, useEffect } from "react";
import {
  Download, Search, RefreshCw, Shield, Users, Activity, Filter,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface LogEntry {
  id: string;
  tenant_id: string | null;
  user_id: string | null;
  action: string;
  resource: string | null;
  ip_address: string | null;
  timestamp: string;
}

interface ComplianceSummary {
  total_calls: number;
  unique_users: number;
  unique_tenants: number;
  from_date: string | null;
  to_date: string | null;
  calls_by_action: Record<string, number>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function buildParams(
  tenantId: string,
  fromDate: string,
  toDate: string,
  extra: Record<string, string> = {}
): string {
  const p = new URLSearchParams();
  if (tenantId) p.set("tenant_id", tenantId);
  if (fromDate)  p.set("from_date", fromDate);
  if (toDate)    p.set("to_date", toDate);
  Object.entries(extra).forEach(([k, v]) => p.set(k, v));
  return p.toString();
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ── Action badge colours ──────────────────────────────────────────────────────

function ActionBadge({ action }: { action: string }) {
  const colour = action.startsWith("GET")
    ? "bg-sky-900/40 text-sky-300 border-sky-700/40"
    : action.startsWith("POST")
    ? "bg-emerald-900/40 text-emerald-300 border-emerald-700/40"
    : action.startsWith("DELETE")
    ? "bg-rose-900/40 text-rose-300 border-rose-700/40"
    : "bg-slate-800 text-slate-400 border-slate-700";

  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-bold leading-none ${colour}`}>
      {action}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const today = new Date().toISOString().slice(0, 10);
  const thirtyDaysAgo = new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10);

  const [tenantId, setTenantId] = useState("");
  const [fromDate, setFromDate] = useState(thirtyDaysAgo);
  const [toDate,   setToDate]   = useState(today);
  const [logs,     setLogs]     = useState<LogEntry[]>([]);
  const [summary,  setSummary]  = useState<ComplianceSummary | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = buildParams(tenantId, fromDate, toDate, { limit: "200" });
      const [newLogs, newSummary] = await Promise.all([
        apiFetch<LogEntry[]>(`/api/v1/admin/compliance/export?${qs}`),
        apiFetch<ComplianceSummary>(`/api/v1/admin/compliance/summary?${qs}`),
      ]);
      setLogs(newLogs);
      setSummary(newSummary);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [tenantId, fromDate, toDate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCsvDownload = async () => {
    const qs = buildParams(tenantId, fromDate, toDate, { format: "csv" });
    const url = `${API}/api/v1/admin/compliance/export?${qs}`;
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) { alert("Export failed"); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `compliance_${fromDate}_${toDate}.csv`;
    a.click();
  };

  const visibleLogs = actionFilter
    ? logs.filter(l => l.action.toLowerCase().includes(actionFilter.toLowerCase()))
    : logs;

  return (
    <div className="mx-auto max-w-6xl space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Shield className="h-5 w-5 text-violet-400" /> Compliance Audit Log
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Export and review tenant API call history for compliance and auditing.
          </p>
        </div>
        <button
          onClick={handleCsvDownload}
          className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition-colors"
        >
          <Download className="h-4 w-4" /> Download CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex flex-col gap-1 min-w-[180px]">
          <label className="text-[10px] text-slate-500 uppercase tracking-wider">Tenant ID (optional)</label>
          <input
            value={tenantId}
            onChange={e => setTenantId(e.target.value)}
            placeholder="UUID or leave blank for all"
            className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 uppercase tracking-wider">From</label>
          <input
            type="date"
            value={fromDate}
            onChange={e => setFromDate(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 uppercase tracking-wider">To</label>
          <input
            type="date"
            value={toDate}
            onChange={e => setToDate(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-violet-500"
          />
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && (
        <p className="rounded-xl border border-rose-800 bg-rose-900/20 px-4 py-3 text-sm text-rose-400">
          ⚠ {error}
        </p>
      )}

      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: "Total API calls",    value: summary.total_calls.toLocaleString(),    icon: <Activity className="h-4 w-4 text-violet-400" /> },
            { label: "Unique users",       value: summary.unique_users.toLocaleString(),   icon: <Users className="h-4 w-4 text-sky-400" /> },
            { label: "Unique tenants",     value: summary.unique_tenants.toLocaleString(), icon: <Shield className="h-4 w-4 text-emerald-400" /> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
              <div className="flex items-center gap-2 mb-2">{icon}<p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p></div>
              <p className="text-2xl font-bold text-slate-100">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Top actions breakdown */}
      {summary && Object.keys(summary.calls_by_action).length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
          <p className="text-xs font-semibold text-slate-400 mb-4">Calls by action type</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.calls_by_action)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 12)
              .map(([action, count]) => (
                <button
                  key={action}
                  onClick={() => setActionFilter(actionFilter === action ? "" : action)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                    actionFilter === action
                      ? "border-violet-500 bg-violet-900/30 text-violet-300"
                      : "border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {action}
                  <span className="rounded-full bg-slate-700 px-1.5 py-px text-[9px] font-bold text-slate-300">{count}</span>
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Log table */}
      <div className="rounded-2xl border border-slate-800 overflow-hidden">
        <div className="bg-slate-900/60 px-5 py-3 border-b border-slate-800 flex items-center justify-between">
          <p className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <Filter className="h-3.5 w-3.5 text-slate-500" />
            Audit Log
            <span className="text-slate-500">({visibleLogs.length} entries)</span>
          </p>
          {actionFilter && (
            <button
              onClick={() => setActionFilter("")}
              className="text-[10px] text-violet-400 hover:text-violet-300 transition-colors"
            >
              Clear filter ×
            </button>
          )}
        </div>

        {/* Action filter input */}
        <div className="border-b border-slate-800 bg-slate-900/30 px-5 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-600" />
            <input
              value={actionFilter}
              onChange={e => setActionFilter(e.target.value)}
              placeholder="Filter by action name…"
              className="w-full rounded-lg bg-slate-800/60 border border-slate-700 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-violet-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40">
                {["Timestamp", "Action", "Resource", "Tenant", "User", "IP"].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {visibleLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    {loading ? "Loading…" : "No log entries found for the selected filters."}
                  </td>
                </tr>
              )}
              {visibleLogs.map(entry => (
                <tr key={entry.id} className="hover:bg-slate-900/20 transition-colors">
                  <td className="px-4 py-2.5 text-slate-400 whitespace-nowrap">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <ActionBadge action={entry.action} />
                  </td>
                  <td className="px-4 py-2.5 text-slate-400 max-w-[200px] truncate">
                    {entry.resource ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 font-mono text-[10px]">
                    {entry.tenant_id ? entry.tenant_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 font-mono text-[10px]">
                    {entry.user_id ? entry.user_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500">
                    {entry.ip_address ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-[11px] text-slate-600 leading-relaxed border-t border-slate-800 pt-4">
        ⚠ Compliance audit logs are append-only. Exports are limited to 90 days per request.
        This data is for authorised compliance and auditing purposes only.
      </p>

    </div>
  );
}
