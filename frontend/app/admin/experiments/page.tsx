"use client";

/**
 * /admin/experiments — A/B Experiment Management Dashboard (CORE-EXPERIMENT-01)
 *
 * Sections:
 *   1. Experiment list with status badges + quick-action buttons
 *   2. Create-experiment slide-in form (2-variant default, configurable)
 *   3. Results panel — per-variant conversion funnel read from analytics_events
 *   4. Status lifecycle controls (draft → running → paused / concluded)
 *
 * Access: admin-only. Integrates with useExperiment hook for live preview.
 *
 * How experiments work end-to-end:
 *   1. Admin creates experiment here (draft).
 *   2. Admin launches it (running).
 *   3. Frontend calls assignVariant() on app boot → user gets a variant.
 *   4. Every analytics event fired by that user includes
 *      { experiment_key, experiment_variant } in properties.
 *   5. Admin reads results here — conversion counts are read from analytics_events.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  fetchExperiments,
  createExperiment,
  transitionExperiment,
  deleteExperiment,
  fetchExperimentResults,
  type ExperimentDto,
  type ExperimentResultsDto,
  type ExperimentCreatePayload,
  type VariantDefinition,
} from "@/lib/api";
import { AnalyticsEvent as AE } from "@/lib/api";

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  draft:     { label: "Draft",     cls: "bg-gray-700 text-gray-300" },
  running:   { label: "Running",   cls: "bg-green-900/60 text-green-400 border border-green-700/50" },
  paused:    { label: "Paused",    cls: "bg-yellow-900/40 text-yellow-400 border border-yellow-700/40" },
  concluded: { label: "Concluded", cls: "bg-purple-900/40 text-purple-400 border border-purple-700/40" },
};

// Goal events the admin can select when reading results
const GOAL_EVENT_OPTIONS = [
  { value: "backtest_run",              label: "Backtest Run" },
  { value: "hedging_simulator_viewed",  label: "Hedging Simulator Viewed" },
  { value: "macro_dashboard_viewed",    label: "Macro Dashboard Viewed" },
  { value: "dashboard_viewed",          label: "Dashboard Viewed" },
  { value: "portfolio_created",         label: "Portfolio Created" },
  { value: "alert_created",             label: "Alert Created" },
  { value: "upgrade_cta_clicked",       label: "Upgrade CTA Clicked" },
  { value: "billing_page_viewed",       label: "Billing Page Viewed" },
  { value: "consent_accepted",          label: "Consent Accepted" },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] ?? { label: status, cls: "bg-gray-700 text-gray-400" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

function ActionButton({
  label,
  onClick,
  variant = "default",
  disabled = false,
}: {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger" | "green" | "yellow";
  disabled?: boolean;
}) {
  const cls = {
    default: "bg-gray-800 text-gray-300 hover:bg-gray-700",
    danger:  "bg-red-900/40 text-red-400 hover:bg-red-900/70 border border-red-800/50",
    green:   "bg-green-900/40 text-green-400 hover:bg-green-900/70 border border-green-800/50",
    yellow:  "bg-yellow-900/30 text-yellow-400 hover:bg-yellow-900/60 border border-yellow-800/40",
  }[variant];

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-2.5 py-1 rounded text-xs font-medium transition-colors disabled:opacity-40 ${cls}`}
    >
      {label}
    </button>
  );
}

// ─── Create Experiment Form ───────────────────────────────────────────────────

const DEFAULT_VARIANTS: VariantDefinition[] = [
  { key: "control",   name: "Control",   weight: 50 },
  { key: "treatment", name: "Treatment", weight: 50 },
];

function CreateExperimentPanel({
  onCreated,
  onClose,
}: {
  onCreated: (exp: ExperimentDto) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<ExperimentCreatePayload>({
    key: "",
    name: "",
    hypothesis: "",
    variants: DEFAULT_VARIANTS,
    traffic_pct: 100,
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const setVariant = (idx: number, field: keyof VariantDefinition, value: string | number) => {
    setForm((f) => {
      const variants = [...f.variants];
      variants[idx] = { ...variants[idx], [field]: value };
      return { ...f, variants };
    });
  };

  const weightTotal = form.variants.reduce((s, v) => s + (Number(v.weight) || 0), 0);
  const weightsValid = weightTotal === 100;
  const hasControl = form.variants.some((v) => v.key === "control");

  const handleSubmit = async () => {
    if (!form.key || !form.name) { setError("Key and name are required."); return; }
    if (!weightsValid) { setError("Variant weights must sum to exactly 100."); return; }
    if (!hasControl) { setError("At least one variant must have key 'control'."); return; }

    setSaving(true);
    setError(null);
    try {
      const exp = await createExperiment({
        ...form,
        key: form.key.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_"),
      });
      onCreated(exp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create experiment");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white">New Experiment</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">×</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {error && (
            <div className="bg-red-900/30 border border-red-700/50 rounded-lg p-3 text-red-400 text-sm">{error}</div>
          )}

          {/* Key */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Key <span className="text-gray-600">(url-safe, snake_case)</span></label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              placeholder="onboarding_flow_v2"
              value={form.key}
              onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Name</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              placeholder="Onboarding Flow V2"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>

          {/* Hypothesis */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Hypothesis <span className="text-gray-600">(optional)</span></label>
            <textarea
              rows={2}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none"
              placeholder="If we show the macro dashboard first, users will engage more deeply..."
              value={form.hypothesis}
              onChange={(e) => setForm((f) => ({ ...f, hypothesis: e.target.value }))}
            />
          </div>

          {/* Traffic */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Traffic Allocation: <span className="text-white font-semibold">{form.traffic_pct}%</span>
              <span className="text-gray-600 ml-2">of eligible users</span>
            </label>
            <input
              type="range" min={5} max={100} step={5}
              value={form.traffic_pct}
              onChange={(e) => setForm((f) => ({ ...f, traffic_pct: Number(e.target.value) }))}
              className="w-full accent-indigo-500"
            />
          </div>

          {/* Variants */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-400">
                Variants
                <span className={`ml-2 font-semibold ${weightsValid ? "text-green-400" : "text-red-400"}`}>
                  ({weightTotal}/100)
                </span>
              </label>
              <button
                onClick={() => setForm((f) => ({ ...f, variants: [...f.variants, { key: `variant_${f.variants.length}`, name: `Variant ${f.variants.length}`, weight: 0 }] }))}
                className="text-xs text-indigo-400 hover:text-indigo-300"
              >
                + Add variant
              </button>
            </div>
            <div className="space-y-2">
              {form.variants.map((v, i) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_80px_32px] gap-2 items-center">
                  <input
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                    placeholder="key"
                    value={v.key}
                    onChange={(e) => setVariant(i, "key", e.target.value)}
                  />
                  <input
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                    placeholder="Name"
                    value={v.name}
                    onChange={(e) => setVariant(i, "name", e.target.value)}
                  />
                  <div className="flex items-center gap-1">
                    <input
                      type="number" min={0} max={100}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white text-right focus:outline-none focus:border-indigo-500"
                      value={v.weight}
                      onChange={(e) => setVariant(i, "weight", Number(e.target.value))}
                    />
                    <span className="text-gray-500 text-xs">%</span>
                  </div>
                  {form.variants.length > 2 && (
                    <button
                      onClick={() => setForm((f) => ({ ...f, variants: f.variants.filter((_, j) => j !== i) }))}
                      className="text-red-500 hover:text-red-400 text-lg leading-none"
                    >×</button>
                  )}
                </div>
              ))}
            </div>
            {!hasControl && (
              <p className="text-red-400 text-xs mt-1">⚠ One variant must have key "control"</p>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Notes <span className="text-gray-600">(optional)</span></label>
            <textarea
              rows={2}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={saving || !weightsValid || !hasControl}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            {saving ? "Creating…" : "Create Experiment"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Results Panel ────────────────────────────────────────────────────────────

function ResultsPanel({
  experiment,
  onClose,
}: {
  experiment: ExperimentDto;
  onClose: () => void;
}) {
  const [goalEvent, setGoalEvent] = useState(GOAL_EVENT_OPTIONS[0].value);
  const [periodDays, setPeriodDays] = useState(30);
  const [results, setResults] = useState<ExperimentResultsDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetchExperimentResults(experiment.key, goalEvent, periodDays);
      setResults(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  }, [experiment.key, goalEvent, periodDays]);

  useEffect(() => { load(); }, [load]);

  const maxRate = results ? Math.max(...results.variants.map((v) => v.conversion_rate_pct), 0.001) : 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-white">{experiment.name}</h2>
            <p className="text-xs text-gray-500 font-mono mt-0.5">{experiment.key}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl">×</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Controls */}
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Goal Event</label>
              <select
                value={goalEvent}
                onChange={(e) => setGoalEvent(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                {GOAL_EVENT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Period</label>
              <select
                value={periodDays}
                onChange={(e) => setPeriodDays(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                {[7, 14, 30, 60, 90].map((d) => (
                  <option key={d} value={d}>{d} days</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={load}
                disabled={loading}
                className="px-3 py-1.5 bg-gray-800 text-gray-400 hover:text-white rounded-lg text-xs transition-colors disabled:opacity-40"
              >
                {loading ? "↺ Loading…" : "↺ Refresh"}
              </button>
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {results && (
            <>
              {/* Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-white">{results.total_assigned_users}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Assigned Users</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-indigo-400">{results.variants.length}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Variants</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className={`text-xl font-bold ${results.winner ? "text-green-400" : "text-gray-500"}`}>
                    {results.winner ?? "—"}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Leading Variant</p>
                </div>
              </div>

              {/* Note */}
              <div className="bg-indigo-900/20 border border-indigo-800/40 rounded-lg p-3 text-xs text-indigo-300">
                {results.note}
              </div>

              {/* Per-variant metrics */}
              <div className="space-y-3">
                {results.variants.map((v) => {
                  const isWinner = v.variant_key === results.winner;
                  const barPct = (v.conversion_rate_pct / maxRate) * 100;
                  return (
                    <div
                      key={v.variant_key}
                      className={`rounded-xl p-4 border ${
                        isWinner
                          ? "bg-green-900/20 border-green-800/40"
                          : "bg-gray-800/60 border-gray-700/50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-white">{v.variant_key}</span>
                          <span className="text-xs text-gray-500">{v.variant_name}</span>
                          {isWinner && (
                            <span className="bg-green-600/30 border border-green-600/50 text-green-400 text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider">
                              Leading
                            </span>
                          )}
                        </div>
                        <span className={`text-lg font-bold font-mono ${isWinner ? "text-green-400" : "text-white"}`}>
                          {v.conversion_rate_pct.toFixed(1)}%
                        </span>
                      </div>

                      {/* Conversion bar */}
                      <div className="h-2 bg-gray-700 rounded-full overflow-hidden mb-3">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${isWinner ? "bg-green-500" : "bg-indigo-500"}`}
                          style={{ width: `${barPct}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div>
                          <p className="text-sm font-bold text-white">{v.unique_users.toLocaleString()}</p>
                          <p className="text-[10px] text-gray-500">Unique Users</p>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white">{v.conversions.toLocaleString()}</p>
                          <p className="text-[10px] text-gray-500">Conversions</p>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white">{v.total_events.toLocaleString()}</p>
                          <p className="text-[10px] text-gray-500">Total Events</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <p className="text-xs text-gray-600 text-center">
                Results are observational. Statistical significance is not computed automatically.
                Run for at least 2 weeks before drawing conclusions.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
  const router = useRouter();
  const [experiments, setExperiments] = useState<ExperimentDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [viewingResults, setViewingResults] = useState<ExperimentDto | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [actionPending, setActionPending] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchExperiments(statusFilter === "all" ? undefined : statusFilter);
      setExperiments(list);
    } catch (err) {
      if (err instanceof Error && err.message.includes("403")) {
        router.push("/auth/login?next=/admin/experiments");
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load experiments");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, router]);

  useEffect(() => { load(); }, [load]);

  const handleTransition = async (key: string, action: "launch" | "pause" | "conclude") => {
    setActionPending(key + action);
    try {
      const updated = await transitionExperiment(key, action);
      setExperiments((prev) => prev.map((e) => (e.key === key ? updated : e)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionPending(null);
    }
  };

  const handleDelete = async (key: string) => {
    if (!confirm(`Delete experiment "${key}"? This also deletes all assignment records.`)) return;
    try {
      await deleteExperiment(key);
      setExperiments((prev) => prev.filter((e) => e.key !== key));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const filtered = experiments; // filtering done server-side

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Modals */}
      {showCreate && (
        <CreateExperimentPanel
          onCreated={(exp) => { setExperiments((prev) => [exp, ...prev]); setShowCreate(false); }}
          onClose={() => setShowCreate(false)}
        />
      )}
      {viewingResults && (
        <ResultsPanel experiment={viewingResults} onClose={() => setViewingResults(null)} />
      )}

      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">A/B Experiments</h1>
            <p className="text-xs text-gray-500 mt-0.5">CORE-EXPERIMENT-01 · Admin only</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Status filter */}
            <div className="flex gap-1">
              {["all", "running", "draft", "paused", "concluded"].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                    statusFilter === s
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              + New Experiment
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-24" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-600 text-lg mb-2">No experiments yet</p>
            <p className="text-gray-700 text-sm mb-6">Create your first A/B experiment to start optimising.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg"
            >
              Create First Experiment
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((exp) => {
              const isPending = actionPending?.startsWith(exp.key);
              return (
                <div
                  key={exp.key}
                  className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    {/* Left: info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <StatusBadge status={exp.status} />
                        <h3 className="text-white font-semibold truncate">{exp.name}</h3>
                      </div>
                      <p className="text-xs text-gray-500 font-mono mb-2">{exp.key}</p>
                      {exp.hypothesis && (
                        <p className="text-xs text-gray-400 line-clamp-2 mb-2 italic">"{exp.hypothesis}"</p>
                      )}

                      {/* Variant pills */}
                      <div className="flex flex-wrap gap-2 mb-2">
                        {exp.variants.map((v) => (
                          <span
                            key={v.key}
                            className="inline-flex items-center gap-1 bg-gray-800 rounded-full px-2.5 py-0.5 text-xs text-gray-300"
                          >
                            <span className="font-mono text-indigo-400">{v.key}</span>
                            <span className="text-gray-500">{v.weight}%</span>
                          </span>
                        ))}
                        <span className="text-xs text-gray-600">
                          {exp.traffic_pct < 100 ? `${exp.traffic_pct}% traffic` : "100% traffic"}
                        </span>
                      </div>
                    </div>

                    {/* Right: actions */}
                    <div className="flex flex-col gap-2 items-end shrink-0">
                      <div className="flex flex-wrap gap-1.5 justify-end">
                        {/* Results — available for running/concluded */}
                        {(exp.status === "running" || exp.status === "concluded" || exp.status === "paused") && (
                          <ActionButton
                            label="Results"
                            onClick={() => setViewingResults(exp)}
                            variant="default"
                          />
                        )}
                        {/* Lifecycle buttons */}
                        {(exp.status === "draft" || exp.status === "paused") && (
                          <ActionButton
                            label="Launch"
                            onClick={() => handleTransition(exp.key, "launch")}
                            variant="green"
                            disabled={!!isPending}
                          />
                        )}
                        {exp.status === "running" && (
                          <ActionButton
                            label="Pause"
                            onClick={() => handleTransition(exp.key, "pause")}
                            variant="yellow"
                            disabled={!!isPending}
                          />
                        )}
                        {(exp.status === "running" || exp.status === "paused") && (
                          <ActionButton
                            label="Conclude"
                            onClick={() => handleTransition(exp.key, "conclude")}
                            variant="default"
                            disabled={!!isPending}
                          />
                        )}
                        {exp.status !== "running" && (
                          <ActionButton
                            label="Delete"
                            onClick={() => handleDelete(exp.key)}
                            variant="danger"
                          />
                        )}
                      </div>
                      <p className="text-[10px] text-gray-600">
                        Created {new Date(exp.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* How it works */}
        <div className="mt-12 bg-gray-900/50 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-white mb-3">How experiments work</h3>
          <ol className="space-y-2 text-xs text-gray-400 list-decimal list-inside">
            <li>Create an experiment here (stays in <span className="text-gray-300 font-mono">draft</span>).</li>
            <li>Instrument the frontend: call <span className="font-mono text-indigo-400">useExperiment("your_key")</span> in the relevant component.</li>
            <li>Launch the experiment — users are now deterministically assigned to variants.</li>
            <li>Every analytics event fired by assigned users automatically includes <span className="font-mono text-indigo-400">experiment_key</span> + <span className="font-mono text-indigo-400">experiment_variant</span> in properties.</li>
            <li>Read results here — conversion rates are computed from <span className="font-mono text-indigo-400">analytics_events</span>.</li>
            <li>Conclude when you have enough data. Ship the winning variant.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
