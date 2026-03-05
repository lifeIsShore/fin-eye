"use client";

/**
 * /admin/analytics — Product Analytics Dashboard (CORE-ANALYTICS-01)
 *
 * Sections:
 *   1. Summary KPI strip (total events, signed-up users, active users, activation rate)
 *   2. Period selector (7 / 14 / 30 / 90 days)
 *   3. DAU / New Users chart (bar + line combo)
 *   4. Activation Funnel (horizontal funnel bars with conversion rates)
 *   5. Feature Adoption table (sorted by unique users desc)
 *   6. Top Pages table
 *   7. Top Searched Symbols table
 *   8. Conversion Funnel
 *
 * Access: admin-only. Redirects to /auth/login if not authenticated.
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  fetchAnalyticsSummary,
  type AnalyticsSummaryDto,
  type AnalyticsFunnelStep,
  type AnalyticsFeatureAdoptionRow,
  type AnalyticsDauPoint,
} from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

type Period = 7 | 14 | 30 | 90;

// ─── Helper Components ────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  colour,
}: {
  label: string;
  value: string | number;
  sub?: string;
  colour?: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-3xl font-bold ${colour ?? "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

// ─── DAU Chart (pure SVG, no external deps) ───────────────────────────────────

function DauChart({ data }: { data: AnalyticsDauPoint[] }) {
  if (!data.length) return <p className="text-gray-600 text-sm">No data</p>;

  const W = 800;
  const H = 180;
  const PADDING = { top: 20, right: 20, bottom: 36, left: 40 };
  const chartW = W - PADDING.left - PADDING.right;
  const chartH = H - PADDING.top - PADDING.bottom;

  const maxDau = Math.max(...data.map((d) => d.dau), 1);
  const barW = Math.max(4, (chartW / data.length) - 2);

  const dauPoints = data.map((d, i) => {
    const x = PADDING.left + (i / (data.length - 1)) * chartW;
    const y = PADDING.top + chartH - (d.dau / maxDau) * chartH;
    return `${x},${y}`;
  });

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ minWidth: 400 }}
        aria-label="Daily active users chart"
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = PADDING.top + chartH * (1 - frac);
          return (
            <g key={frac}>
              <line
                x1={PADDING.left}
                x2={W - PADDING.right}
                y1={y}
                y2={y}
                stroke="#374151"
                strokeWidth={0.5}
                strokeDasharray="4 4"
              />
              <text x={PADDING.left - 6} y={y + 4} fill="#6b7280" fontSize={9} textAnchor="end">
                {Math.round(maxDau * frac)}
              </text>
            </g>
          );
        })}

        {/* New user bars */}
        {data.map((d, i) => {
          const barH = (d.new_users / maxDau) * chartH;
          const x = PADDING.left + (i / data.length) * chartW;
          return (
            <rect
              key={i}
              x={x + 1}
              y={PADDING.top + chartH - barH}
              width={barW}
              height={barH}
              fill="#6366f1"
              opacity={0.5}
              rx={1}
            />
          );
        })}

        {/* DAU polyline */}
        {data.length > 1 && (
          <polyline
            fill="none"
            stroke="#34d399"
            strokeWidth={2}
            points={dauPoints.join(" ")}
          />
        )}

        {/* DAU dots */}
        {data.map((d, i) => {
          const x = PADDING.left + (i / (data.length - 1)) * chartW;
          const y = PADDING.top + chartH - (d.dau / maxDau) * chartH;
          return <circle key={i} cx={x} cy={y} r={3} fill="#34d399" />;
        })}

        {/* X-axis labels — show every ~7th */}
        {data
          .filter((_, i) => i % Math.ceil(data.length / 10) === 0)
          .map((d, idx, arr) => {
            const origIdx = data.indexOf(d);
            const x = PADDING.left + (origIdx / (data.length - 1)) * chartW;
            return (
              <text key={idx} x={x} y={H - 6} fill="#6b7280" fontSize={8} textAnchor="middle">
                {d.date.slice(5)}
              </text>
            );
          })}
      </svg>
      <div className="flex items-center gap-6 mt-2 justify-center">
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className="inline-block w-3 h-0.5 bg-green-400 rounded" /> DAU
        </span>
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className="inline-block w-3 h-3 bg-indigo-400 rounded opacity-60" /> New Signups
        </span>
      </div>
    </div>
  );
}

// ─── Funnel Visualiser ────────────────────────────────────────────────────────

function FunnelChart({ steps }: { steps: AnalyticsFunnelStep[] }) {
  const maxUsers = Math.max(...steps.map((s) => s.unique_users), 1);

  return (
    <div className="space-y-2">
      {steps.map((step, i) => {
        const barPct = (step.unique_users / maxUsers) * 100;
        return (
          <div key={step.event_name} className="group">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span>{step.label}</span>
              <span className="font-mono">
                {step.unique_users.toLocaleString()} users
                {step.conversion_from_previous_pct !== null && (
                  <span
                    className={`ml-2 font-semibold ${
                      step.conversion_from_previous_pct > 50
                        ? "text-green-400"
                        : step.conversion_from_previous_pct > 20
                        ? "text-yellow-400"
                        : "text-red-400"
                    }`}
                  >
                    ↓ {step.conversion_from_previous_pct}%
                  </span>
                )}
              </span>
            </div>
            <div className="relative h-7 bg-gray-800 rounded overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-indigo-600 transition-all duration-500 rounded"
                style={{ width: `${barPct}%` }}
              />
              <span className="absolute inset-0 flex items-center px-3 text-xs text-white font-mono">
                {step.total_occurrences.toLocaleString()} events
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Feature Adoption Table ───────────────────────────────────────────────────

function FeatureAdoptionTable({ rows }: { rows: AnalyticsFeatureAdoptionRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 text-xs uppercase tracking-wider border-b border-gray-800">
            <th className="pb-2 pr-4">Feature</th>
            <th className="pb-2 pr-4 text-right">Unique Users</th>
            <th className="pb-2 pr-4 text-right">Total Events</th>
            <th className="pb-2 pr-4 text-right">Adoption</th>
            <th className="pb-2">Adoption Bar</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {rows.map((row) => (
            <tr key={row.event_name} className="hover:bg-gray-900/50 transition-colors">
              <td className="py-2.5 pr-4 text-white font-medium">{row.label}</td>
              <td className="py-2.5 pr-4 text-right font-mono text-gray-300">
                {row.unique_users.toLocaleString()}
              </td>
              <td className="py-2.5 pr-4 text-right font-mono text-gray-400">
                {row.total_occurrences.toLocaleString()}
              </td>
              <td
                className={`py-2.5 pr-4 text-right font-mono font-semibold ${
                  row.adoption_pct > 30
                    ? "text-green-400"
                    : row.adoption_pct > 10
                    ? "text-yellow-400"
                    : "text-red-400"
                }`}
              >
                {row.adoption_pct.toFixed(1)}%
              </td>
              <td className="py-2.5">
                <div className="h-2 bg-gray-800 rounded w-32 overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded"
                    style={{ width: `${Math.min(row.adoption_pct, 100)}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const router = useRouter();
  const [period, setPeriod] = useState<Period>(30);
  const [data, setData] = useState<AnalyticsSummaryDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await fetchAnalyticsSummary(period);
      setData(summary);
    } catch (err) {
      if (err instanceof Error && err.message.includes("403")) {
        router.push("/auth/login?next=/admin/analytics");
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [period, router]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Derived numbers ───────────────────────────────────────────────────────

  const activationRate =
    data && data.total_signed_up_users > 0
      ? ((data.total_active_users / data.total_signed_up_users) * 100).toFixed(1)
      : "—";

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Product Analytics</h1>
            <p className="text-xs text-gray-500 mt-0.5">CORE-ANALYTICS-01 · Admin only</p>
          </div>
          <div className="flex items-center gap-2">
            {(([7, 14, 30, 90] as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  period === p
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {p}d
              </button>
            )))}
            <button
              onClick={load}
              disabled={loading}
              className="ml-2 px-3 py-1.5 rounded-lg text-xs bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-40 transition-colors"
            >
              {loading ? "↺" : "Refresh"}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-10">
        {/* Error state */}
        {error && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && !data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-24" />
            ))}
          </div>
        )}

        {data && (
          <>
            {/* ── KPI Strip ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard
                label="Total Events"
                value={data.total_events.toLocaleString()}
                sub={`Last ${data.period_days} days`}
                colour="text-indigo-400"
              />
              <KpiCard
                label="Signed-Up Users"
                value={data.total_signed_up_users.toLocaleString()}
                sub="All time"
                colour="text-white"
              />
              <KpiCard
                label="Active Users"
                value={data.total_active_users.toLocaleString()}
                sub={`Last ${data.period_days} days`}
                colour="text-green-400"
              />
              <KpiCard
                label="Activation Rate"
                value={`${activationRate}%`}
                sub="Active / signed-up"
                colour={
                  parseFloat(activationRate as string) > 50
                    ? "text-green-400"
                    : parseFloat(activationRate as string) > 20
                    ? "text-yellow-400"
                    : "text-red-400"
                }
              />
            </div>

            {/* ── DAU Chart ─────────────────────────────────────────────── */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <SectionHeader
                title="Daily Active Users"
                sub="Unique users + new signups per day"
              />
              <DauChart data={data.daily_active_users} />
            </div>

            {/* ── Funnels ───────────────────────────────────────────────── */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <SectionHeader
                  title="Activation Funnel"
                  sub="Signed-up → first key actions"
                />
                <FunnelChart steps={data.activation_funnel.steps} />
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <SectionHeader
                  title="Conversion Funnel"
                  sub="Free → billing intent"
                />
                {data.conversion_funnel.steps.length === 0 ? (
                  <p className="text-gray-600 text-sm">No conversion data yet.</p>
                ) : (
                  <FunnelChart steps={data.conversion_funnel.steps} />
                )}
              </div>
            </div>

            {/* ── Feature Adoption ──────────────────────────────────────── */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <SectionHeader
                title="Feature Adoption"
                sub={`Unique users per feature · % of total ${data.total_signed_up_users.toLocaleString()} signed-up users`}
              />
              {data.feature_adoption.length === 0 ? (
                <p className="text-gray-600 text-sm">No feature events tracked yet.</p>
              ) : (
                <FeatureAdoptionTable rows={data.feature_adoption} />
              )}
            </div>

            {/* ── Top Pages + Top Symbols ───────────────────────────────── */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Top Pages */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <SectionHeader title="Top Pages" sub="By total views" />
                {data.top_pages.length === 0 ? (
                  <p className="text-gray-600 text-sm">No page view data yet.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                        <th className="pb-2 pr-4">Page</th>
                        <th className="pb-2 pr-4 text-right">Views</th>
                        <th className="pb-2 text-right">Unique Users</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {data.top_pages.map((row) => (
                        <tr key={row.page} className="hover:bg-gray-800/30">
                          <td className="py-2 pr-4 text-indigo-400 font-mono text-xs truncate max-w-[160px]">
                            {row.page}
                          </td>
                          <td className="py-2 pr-4 text-right font-mono text-gray-300">
                            {row.views.toLocaleString()}
                          </td>
                          <td className="py-2 text-right font-mono text-gray-400">
                            {row.unique_users.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Top Symbols */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <SectionHeader title="Top Searched Symbols" sub="By search frequency" />
                {data.top_symbols.length === 0 ? (
                  <p className="text-gray-600 text-sm">No symbol search data yet.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
                        <th className="pb-2 pr-4">Symbol</th>
                        <th className="pb-2 text-right">Searches</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {data.top_symbols.map((row) => (
                        <tr key={row.symbol} className="hover:bg-gray-800/30">
                          <td className="py-2 pr-4 text-green-400 font-mono font-semibold">
                            {row.symbol}
                          </td>
                          <td className="py-2 text-right font-mono text-gray-300">
                            {row.searches.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* ── Footer ───────────────────────────────────────────────── */}
            <p className="text-xs text-gray-600 text-center pb-8">
              Analytics data is self-hosted in PostgreSQL — no third-party tracking.
              User identification is by UUID only; no PII is stored in event properties.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
