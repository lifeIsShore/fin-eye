"use client";

/**
 * /admin/gas — GAS Pre-compute Control Panel (Sprint 13)
 *
 * Lets admins:
 *   - See the latest GAS snapshot for every default symbol (score + age)
 *   - Trigger a full batch precompute (all symbols) in one click
 *   - Trigger precompute for a single symbol inline
 *   - Add an arbitrary symbol to trigger individually
 *   - Watch per-symbol status update in real-time via polling
 */

"use client";

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useAuth } from "../../../components/AuthProvider";
import {
  RefreshCw, Play, Zap, Clock, CheckCircle2,
  AlertCircle, ChevronLeft, Plus, Loader2,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function ageLabel(computedAt: string | null | undefined): string {
  if (!computedAt) return "never";
  const ageMs = Date.now() - new Date(computedAt).getTime();
  const mins = Math.floor(ageMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function ageDot(computedAt: string | null | undefined): string {
  if (!computedAt) return "bg-slate-700";
  const mins = Math.floor((Date.now() - new Date(computedAt).getTime()) / 60_000);
  if (mins < 30) return "bg-emerald-400";
  if (mins < 120) return "bg-amber-400";
  return "bg-rose-400";
}

function scoreColor(s: number): string {
  return s >= 65 ? "text-emerald-400" : s >= 40 ? "text-amber-400" : "text-rose-400";
}

function scoreBarColor(s: number): string {
  return s >= 65 ? "bg-emerald-500" : s >= 40 ? "bg-amber-500" : "bg-rose-500";
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface SnapRow {
  symbol: string;
  gas_score: number;
  weather_label: string;
  regime: string;
  component_scores: { technical: number; sentiment: number; macro: number };
  computed_at: string;
  source: string;
}

// ── Snapshot fetcher ──────────────────────────────────────────────────────────

async function fetchSnapshots(): Promise<SnapRow[]> {
  const res = await fetch(`${API}/api/v1/admin/gas/snapshots`, {
    headers: authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load snapshots: ${res.status}`);
  return res.json();
}

// ── Per-symbol trigger row ────────────────────────────────────────────────────

function SymbolRow({ snap, onTriggered }: { snap: SnapRow; onTriggered: () => void }) {
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const trigger = useCallback(async () => {
    setStatus("running");
    setErrMsg(null);
    try {
      const res = await fetch(
        `${API}/api/v1/admin/gas/precompute/${encodeURIComponent(snap.symbol)}`,
        { method: "POST", headers: authHeaders() },
      );
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as any).detail ?? `HTTP ${res.status}`);
      }
      setStatus("done");
      setTimeout(() => { setStatus("idle"); onTriggered(); }, 1500);
    } catch (e) {
      setStatus("error");
      setErrMsg((e as Error).message);
    }
  }, [snap.symbol, onTriggered]);

  return (
    <tr className="border-b border-slate-800/50 hover:bg-slate-900/30 transition-colors group">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full flex-shrink-0 ${ageDot(snap.computed_at)}`} />
          <span className="font-mono font-bold text-slate-100 text-sm">{snap.symbol}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`text-xl font-black tabular-nums ${scoreColor(snap.gas_score)}`}>
            {snap.gas_score.toFixed(0)}
          </span>
          <div className="hidden sm:flex flex-col gap-0.5 w-20">
            <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div className={`h-full rounded-full ${scoreBarColor(snap.gas_score)}`}
                style={{ width: `${Math.min(100, snap.gas_score)}%` }} />
            </div>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-400 hidden md:table-cell">
        <div className="space-y-0.5">
          <p>T: <span className={scoreColor(snap.component_scores?.technical ?? 50)}>{(snap.component_scores?.technical ?? 0).toFixed(0)}</span></p>
          <p>S: <span className={scoreColor(snap.component_scores?.sentiment ?? 50)}>{(snap.component_scores?.sentiment ?? 0).toFixed(0)}</span></p>
          <p>M: <span className={scoreColor(snap.component_scores?.macro ?? 50)}>{(snap.component_scores?.macro ?? 0).toFixed(0)}</span></p>
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {ageLabel(snap.computed_at)}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500 hidden xl:table-cell">
        {snap.regime}
      </td>
      <td className="px-4 py-3 text-right">
        {status === "idle" && (
          <button
            onClick={trigger}
            className="invisible group-hover:visible inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800/50 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-slate-100 transition-colors"
          >
            <Play className="h-3 w-3" /> Run
          </button>
        )}
        {status === "running" && (
          <span className="inline-flex items-center gap-1 text-sky-400 text-xs">
            <Loader2 className="h-3 w-3 animate-spin" /> Running…
          </span>
        )}
        {status === "done" && (
          <span className="inline-flex items-center gap-1 text-emerald-400 text-xs">
            <CheckCircle2 className="h-3 w-3" /> Done
          </span>
        )}
        {status === "error" && (
          <span className="inline-flex items-center gap-1 text-rose-400 text-xs" title={errMsg ?? ""}>
            <AlertCircle className="h-3 w-3" /> Error
          </span>
        )}
      </td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminGasPage() {
  const { user } = useAuth();
  const [batchStatus, setBatchStatus] = useState<"idle" | "triggered" | "error">("idle");
  const [batchMsg, setBatchMsg] = useState<string | null>(null);
  const [customSymbol, setCustomSymbol] = useState("");
  const [customStatus, setCustomStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [customMsg, setCustomMsg] = useState<string | null>(null);

  const {
    data: snapshots,
    isLoading,
    error,
    mutate: refresh,
  } = useSWR("admin-gas-snapshots", fetchSnapshots, {
    refreshInterval: 30_000,
    shouldRetryOnError: false,
  });

  // Guard: admin only
  if (user && !user.is_admin) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-rose-400 text-sm">Admin access required.</p>
      </div>
    );
  }

  const triggerBatch = async () => {
    setBatchStatus("triggered");
    setBatchMsg(null);
    try {
      const res = await fetch(`${API}/api/v1/admin/gas/precompute`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as any).detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setBatchMsg(data.message ?? "Batch precompute started in background.");
      // Poll for updates
      setTimeout(() => refresh(), 10_000);
      setTimeout(() => refresh(), 25_000);
      setTimeout(() => refresh(), 60_000);
    } catch (e) {
      setBatchStatus("error");
      setBatchMsg((e as Error).message);
    }
  };

  const triggerCustom = async () => {
    const sym = customSymbol.trim().toUpperCase();
    if (!sym) return;
    setCustomStatus("running");
    setCustomMsg(null);
    try {
      const res = await fetch(
        `${API}/api/v1/admin/gas/precompute/${encodeURIComponent(sym)}`,
        { method: "POST", headers: authHeaders() },
      );
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as any).detail ?? `HTTP ${res.status}`);
      }
      setCustomStatus("done");
      setCustomMsg(`GAS computed for ${sym}.`);
      setCustomSymbol("");
      setTimeout(() => { setCustomStatus("idle"); refresh(); }, 2000);
    } catch (e) {
      setCustomStatus("error");
      setCustomMsg((e as Error).message);
    }
  };

  const sorted = [...(snapshots ?? [])].sort((a, b) => b.gas_score - a.gas_score);

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div>
        <Link
          href="/admin/ops"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Back to Ops
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-sky-400" />
              <h1 className="text-xl font-black tracking-tight text-slate-100">GAS Precompute</h1>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">
              Trigger and monitor Global Alignment Score computation per symbol.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => refresh()}
              className="p-2 rounded-lg border border-slate-700 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={triggerBatch}
              disabled={batchStatus === "triggered"}
              className="flex items-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
            >
              {batchStatus === "triggered" ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Running…</>
              ) : (
                <><Play className="h-4 w-4" /> Run All Symbols</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Batch status */}
      {batchMsg && (
        <div className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${
          batchStatus === "error"
            ? "border-rose-800/40 bg-rose-950/20 text-rose-400"
            : "border-emerald-800/40 bg-emerald-950/20 text-emerald-400"
        }`}>
          {batchStatus === "error"
            ? <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            : <CheckCircle2 className="h-4 w-4 flex-shrink-0 mt-0.5" />}
          <div>
            <p className="font-medium">{batchStatus === "error" ? "Batch failed" : "Batch triggered"}</p>
            <p className="text-xs opacity-75 mt-0.5">{batchMsg}</p>
            {batchStatus !== "error" && (
              <p className="text-xs opacity-60 mt-1">Scores will update in the table below as each symbol completes (~10–30s per symbol).</p>
            )}
          </div>
        </div>
      )}

      {/* Custom symbol trigger */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Trigger for a specific symbol
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={customSymbol}
            onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && triggerCustom()}
            placeholder="e.g. NVDA, BTC-USD…"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/20"
          />
          <button
            onClick={triggerCustom}
            disabled={!customSymbol.trim() || customStatus === "running"}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
          >
            {customStatus === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Compute
          </button>
        </div>
        {customMsg && (
          <p className={`mt-2 text-xs ${customStatus === "error" ? "text-rose-400" : "text-emerald-400"}`}>
            {customMsg}
          </p>
        )}
      </div>

      {/* Summary stats strip */}
      {snapshots && snapshots.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              label: "Total symbols",
              value: snapshots.length,
              color: "text-slate-100",
            },
            {
              label: "Bullish (GAS ≥ 60)",
              value: snapshots.filter((s) => s.gas_score >= 60).length,
              color: "text-emerald-400",
            },
            {
              label: "Bearish (GAS < 40)",
              value: snapshots.filter((s) => s.gas_score < 40).length,
              color: "text-rose-400",
            },
            {
              label: "Stale (> 2 hours)",
              value: snapshots.filter((s) => {
                if (!s.computed_at) return true;
                return Date.now() - new Date(s.computed_at).getTime() > 2 * 60 * 60_000;
              }).length,
              color: "text-amber-400",
            },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
              <p className={`text-2xl font-black tabular-nums mt-0.5 ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Snapshot table */}
      {isLoading && !snapshots && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center animate-pulse">
          <p className="text-sm text-slate-500">Loading snapshots…</p>
        </div>
      )}

      {error && !snapshots && (
        <div className="rounded-xl border border-rose-800/40 bg-rose-950/20 px-5 py-4 text-sm text-rose-400">
          Failed to load snapshots — ensure you are logged in as an admin and the backend is running.
        </div>
      )}

      {sorted.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/60 border-b border-slate-800">
              <tr className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">GAS Score</th>
                <th className="px-4 py-3 text-left hidden md:table-cell">Components</th>
                <th className="px-4 py-3 text-left hidden lg:table-cell">Age</th>
                <th className="px-4 py-3 text-left hidden xl:table-cell">Regime</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((snap) => (
                <SymbolRow key={snap.symbol} snap={snap} onTriggered={() => refresh()} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && sorted.length === 0 && !error && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/20 p-12 text-center">
          <Zap className="h-8 w-8 text-slate-700 mx-auto mb-3" />
          <p className="text-slate-400 font-medium">No GAS snapshots yet</p>
          <p className="text-sm text-slate-600 mt-1">
            Click <span className="font-semibold text-sky-400">Run All Symbols</span> to compute the first batch.
          </p>
        </div>
      )}

      <p className="text-[10px] text-slate-700 pb-4">
        GAS snapshots are also auto-computed nightly by the scheduler.
        This page lets you trigger on-demand for testing or after model retraining.
      </p>
    </div>
  );
}
