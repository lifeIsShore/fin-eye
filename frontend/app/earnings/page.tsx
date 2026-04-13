"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  fetchEarningsAnalysis,
  type EarningsAnalysisDto,
  type EarningsRecordDto,
  type SurpriseScoreDto,
  type UpcomingEarningsDto,
} from "../../lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ─── ML Signal types ──────────────────────────────────────────────────

interface MlFeatureDetail {
  value: number;
  raw_days_until?: number | null;
  raw_score?: number;
  raw_streak?: number;
  label?: string;
  interpretation: string;
  description: string;
}

interface EarningsMlSignals {
  symbol: string;
  ml_features: {
    earnings_days_until_norm: MlFeatureDetail;
    earnings_surprise_score_norm: MlFeatureDetail;
    earnings_beat_streak_norm: MlFeatureDetail;
  };
  summary: {
    quarters_beat: number;
    quarters_missed: number;
    quarters_inline: number;
    avg_eps_surprise_pct: number | null;
    upcoming_date: string | null;
  };
  methodology: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtEps(v: number | null): string {
  if (v == null) return "—";
  return (v >= 0 ? "$" : "-$") + Math.abs(v).toFixed(2);
}

function fmtRevenue(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function fmtSurprisePct(v: number | null): string {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
}

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function surprisePctColor(v: number | null): string {
  if (v == null) return "text-slate-500";
  if (v > 5)  return "text-emerald-400 font-semibold";
  if (v > 0)  return "text-teal-400";
  if (v > -5) return "text-orange-400";
  return "text-rose-400 font-semibold";
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 58) return "text-teal-400";
  if (score >= 42) return "text-slate-300";
  if (score >= 30) return "text-orange-400";
  return "text-rose-400";
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 58) return "bg-teal-500";
  if (score >= 42) return "bg-slate-500";
  if (score >= 30) return "bg-orange-500";
  return "bg-rose-500";
}

function scoreBadge(label: string): string {
  const map: Record<string, string> = {
    "Strong Beater":     "bg-emerald-900/40 text-emerald-300 border-emerald-700/50",
    "Consistent Beater": "bg-teal-900/40 text-teal-300 border-teal-700/50",
    "Mixed":             "bg-slate-800/60 text-slate-300 border-slate-700/50",
    "Miss Tendency":     "bg-orange-900/40 text-orange-300 border-orange-700/50",
    "Consistent Misser": "bg-rose-900/40 text-rose-300 border-rose-700/50",
  };
  return map[label] ?? "bg-slate-800/60 text-slate-300 border-slate-700/50";
}

function beatBadge(beat: boolean | null): JSX.Element {
  if (beat === null) return <span className="text-slate-600 text-[10px]">—</span>;
  return beat
    ? <span className="rounded-full bg-emerald-900/40 border border-emerald-700/40 px-2 py-0.5 text-[10px] font-bold text-emerald-300">BEAT</span>
    : <span className="rounded-full bg-rose-900/40 border border-rose-700/40 px-2 py-0.5 text-[10px] font-bold text-rose-300">MISS</span>;
}

// ─── Surprise Arc Gauge ───────────────────────────────────────────────────────

function SurpriseGauge({ score }: { score: SurpriseScoreDto }) {
  const pct = Math.round(score.score);
  const fillColor =
    pct >= 70 ? "#10b981" :
    pct >= 58 ? "#14b8a6" :
    pct >= 42 ? "#64748b" :
    pct >= 30 ? "#f97316" :
               "#f87171";

  const angle    = Math.PI - (pct / 100) * Math.PI;
  const arcX     = 80 + 66 * Math.cos(angle);
  const arcY     = 88 - 66 * Math.sin(angle);
  const largeArc = pct > 50 ? 1 : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <svg width="160" height="92" viewBox="0 0 160 92" fill="none">
          <path d="M 14 88 A 66 66 0 0 1 146 88" stroke="#1e293b" strokeWidth="13" strokeLinecap="round" fill="none" />
          {pct > 0 && (
            <path
              d={`M 14 88 A 66 66 0 ${largeArc} 1 ${arcX.toFixed(2)} ${arcY.toFixed(2)}`}
              stroke={fillColor}
              strokeWidth="13"
              strokeLinecap="round"
              fill="none"
            />
          )}
          <line x1="80" y1="22" x2="80" y2="36" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div className="absolute bottom-1 left-0 right-0 flex flex-col items-center leading-none">
          <span className={`text-4xl font-black tabular-nums ${scoreColor(score.score)}`}>{pct}</span>
          <span className="text-[10px] text-slate-600 mt-0.5">out of 100</span>
        </div>
      </div>

      <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${scoreBadge(score.label)}`}>
        {score.label}
      </span>

      {/* Gradient bar */}
      <div className="w-full px-1 space-y-1">
        <div className="flex justify-between text-[9px] text-slate-600">
          <span>Miss</span><span>Neutral</span><span>Beat</span>
        </div>
        <div className="relative h-1.5 w-full rounded-full overflow-hidden">
          <div className="absolute inset-0" style={{ background: "linear-gradient(to right,#f87171,#f97316,#64748b,#14b8a6,#10b981)" }} />
          <div className="absolute top-1/2 h-3.5 w-1.5 -translate-y-1/2 -translate-x-1/2 rounded-sm bg-white shadow"
               style={{ left: `${pct}%` }} />
        </div>
      </div>

      {/* Stats grid */}
      <div className="w-full grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg bg-slate-800/50 py-2">
          <p className="text-emerald-300 font-black text-lg">{score.quarters_beat}</p>
          <p className="text-slate-500 text-[10px]">Beat</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 py-2">
          <p className="text-slate-300 font-black text-lg">{score.quarters_inline}</p>
          <p className="text-slate-500 text-[10px]">Inline</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 py-2">
          <p className="text-rose-300 font-black text-lg">{score.quarters_missed}</p>
          <p className="text-slate-500 text-[10px]">Miss</p>
        </div>
      </div>

      {score.avg_eps_surprise_pct != null && (
        <div className="w-full rounded-lg bg-slate-800/40 px-3 py-2 flex items-center justify-between text-xs">
          <span className="text-slate-500">Avg EPS surprise (4q)</span>
          <span className={surprisePctColor(score.avg_eps_surprise_pct)}>
            {fmtSurprisePct(score.avg_eps_surprise_pct)}
          </span>
        </div>
      )}
      {score.consecutive_beats > 0 && (
        <div className="w-full rounded-lg bg-emerald-950/30 border border-emerald-800/40 px-3 py-2 flex items-center justify-between text-xs">
          <span className="text-slate-400">Consecutive beat streak</span>
          <span className="font-bold text-emerald-300">{score.consecutive_beats}Q</span>
        </div>
      )}
    </div>
  );
}

// ─── Upcoming Card ────────────────────────────────────────────────────────────

function UpcomingCard({ upcoming }: { upcoming: UpcomingEarningsDto }) {
  const urgency =
    upcoming.days_until <= 3  ? "border-amber-600/60 bg-amber-950/20" :
    upcoming.days_until <= 14 ? "border-blue-700/50 bg-blue-950/20" :
                                "border-slate-700 bg-slate-900/40";

  const daysLabel =
    upcoming.days_until === 0 ? "Today" :
    upcoming.days_until === 1 ? "Tomorrow" :
    `In ${upcoming.days_until} days`;

  return (
    <div className={`rounded-xl border p-4 ${urgency} space-y-3`}>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Next Earnings</h3>

      <div className="flex items-start justify-between">
        <div>
          <p className="text-xl font-black text-slate-100">{fmtDate(upcoming.earnings_date)}</p>
          <p className={`text-sm font-semibold mt-0.5 ${upcoming.days_until <= 3 ? "text-amber-300" : "text-blue-300"}`}>
            {daysLabel}
          </p>
        </div>
        {/* Countdown ring */}
        <div className="flex h-14 w-14 flex-col items-center justify-center rounded-full border-2 border-slate-700 bg-slate-900">
          <span className={`text-xl font-black leading-none ${upcoming.days_until <= 3 ? "text-amber-300" : "text-slate-200"}`}>
            {upcoming.days_until}
          </span>
          <span className="text-[9px] text-slate-600">days</span>
        </div>
      </div>

      {upcoming.eps_estimate != null && (
        <div className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2 text-xs">
          <span className="text-slate-400">EPS Estimate (consensus)</span>
          <span className="font-semibold text-slate-200">{fmtEps(upcoming.eps_estimate)}</span>
        </div>
      )}
      {upcoming.revenue_estimate != null && (
        <div className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2 text-xs">
          <span className="text-slate-400">Revenue Estimate</span>
          <span className="font-semibold text-slate-200">{fmtRevenue(upcoming.revenue_estimate)}</span>
        </div>
      )}
    </div>
  );
}

// ─── Surprise Bar Chart ───────────────────────────────────────────────────────

interface ChartPoint {
  name: string;
  surprise: number;
  beat: boolean | null;
}

const CustomBarLabel = ({ x, y, width, value }: { x?: number; y?: number; width?: number; value?: number }) => {
  if (value == null || x == null || y == null || width == null) return null;
  const isPos = value >= 0;
  return (
    <text
      x={x + width / 2}
      y={isPos ? y - 4 : y + 14}
      fill={isPos ? "#34d399" : "#f87171"}
      fontSize={10}
      textAnchor="middle"
      fontWeight="600"
    >
      {(value >= 0 ? "+" : "") + value.toFixed(1) + "%"}
    </text>
  );
};

function SurpriseChart({ history }: { history: EarningsRecordDto[] }) {
  const chartData: ChartPoint[] = history
    .filter(r => r.eps_surprise_pct != null)
    .slice(0, 8)
    .reverse()   // oldest on left
    .map(r => ({
      name: r.period_label,
      surprise: r.eps_surprise_pct!,
      beat: r.beat_eps,
    }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-slate-600">
        No EPS surprise data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 24, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v > 0 ? "+" : ""}${v}%`}
        />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
          labelStyle={{ color: "#94a3b8", fontSize: 11 }}
          formatter={(value: number) => [`${value >= 0 ? "+" : ""}${value.toFixed(2)}%`, "EPS Surprise"]}
        />
        <ReferenceLine y={0} stroke="#334155" strokeWidth={1.5} />
        <Bar dataKey="surprise" radius={[4, 4, 0, 0]} label={<CustomBarLabel />} maxBarSize={48}>
          {chartData.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.surprise > 2 ? "#10b981" : entry.surprise > 0 ? "#14b8a6" : entry.surprise > -2 ? "#f97316" : "#f87171"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── History Table ────────────────────────────────────────────────────────────

function HistoryTable({ history }: { history: EarningsRecordDto[] }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      <div className="border-b border-slate-800 px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Quarterly EPS History
        </h3>
      </div>
      {history.length === 0 ? (
        <div className="py-10 text-center text-sm text-slate-600">No earnings history available</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                {["Period", "Report Date", "EPS Est.", "EPS Actual", "Surprise", "Revenue", "Result"].map(h => (
                  <th key={h} className={`px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600 ${
                    ["EPS Est.", "EPS Actual", "Surprise", "Revenue"].includes(h) ? "text-right" : "text-left"
                  }`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {history.map((r, i) => (
                <tr key={i} className={`hover:bg-slate-800/25 transition-colors ${
                  r.beat_eps === true  ? "border-l-2 border-emerald-500/40" :
                  r.beat_eps === false ? "border-l-2 border-rose-500/40" :
                  "border-l-2 border-transparent"
                }`}>
                  <td className="px-4 py-2.5 text-xs font-medium text-slate-200">{r.period_label}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-400 whitespace-nowrap">{fmtDate(r.earnings_date)}</td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono text-slate-400">{fmtEps(r.eps_estimate)}</td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono font-semibold text-slate-200">{fmtEps(r.eps_actual)}</td>
                  <td className={`px-4 py-2.5 text-right text-xs font-mono ${surprisePctColor(r.eps_surprise_pct)}`}>
                    {fmtSurprisePct(r.eps_surprise_pct)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono text-slate-400">
                    {fmtRevenue(r.revenue_actual)}
                  </td>
                  <td className="px-4 py-2.5">{beatBadge(r.beat_eps)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="border-t border-slate-800 px-4 py-2 text-[10px] text-slate-600">
        Source: Yahoo Finance · Up to 8 most recent quarters
      </div>
    </div>
  );
}

// ─── Methodology card ─────────────────────────────────────────────────────────

function MethodologyCard() {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Score Methodology</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Data Source</p>
          <p>Yahoo Finance via yfinance. EPS estimates are analyst consensus at the time of data fetch. No API key required. Cached 6 hours.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Beat / Miss</p>
          <p>Beat = EPS surprise &gt;+2%. Miss = surprise &lt;−2%. Inline = within ±2%. Open-market EPS only — excludes one-time items if reported as adjusted.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Surprise Score</p>
          <p>Weighted average of last 4 quarters (newest 4×). Beat magnitude boosts score. Normalised 0–100 via tanh. 50 = neutral / no history.</p>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

// ─── ML Signal Impact Panel ───────────────────────────────────────

function MlFeatureBar({ label, value, description, interpretation }: {
  label: string; value: number; description: string; interpretation: string;
}) {
  const pct = Math.round(value * 100);
  const barColor = pct >= 60 ? "bg-emerald-500" : pct >= 40 ? "bg-slate-500" : "bg-rose-500";
  const textColor = pct >= 60 ? "text-emerald-400" : pct >= 40 ? "text-slate-300" : "text-rose-400";
  const badgeColor = interpretation.toLowerCase().includes("bullish")
    ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/40"
    : interpretation.toLowerCase().includes("bearish")
    ? "text-rose-400 bg-rose-950/30 border-rose-800/40"
    : "text-slate-400 bg-slate-800/40 border-slate-700/40";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-mono font-semibold text-sky-400">{label}</span>
        <span className={`text-xs font-bold tabular-nums ${textColor}`}>{value.toFixed(3)}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] text-slate-500 leading-relaxed flex-1">{description}</p>
        <span className={`flex-shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badgeColor}`}>
          {interpretation}
        </span>
      </div>
    </div>
  );
}

function MlSignalPanel({ symbol }: { symbol: string }) {
  const [open, setOpen] = useState(true);
  const [data, setData] = useState<EarningsMlSignals | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true); setError(null);
    fetch(`${API_BASE}/api/v1/earnings/${encodeURIComponent(symbol.toUpperCase())}/ml-signals`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<EarningsMlSignals>; })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [symbol]);

  return (
    <div className="rounded-xl border border-violet-800/40 bg-violet-950/10 overflow-hidden">
      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-violet-900/10 transition-colors">
        <div className="flex items-center gap-2">
          <span className="text-base">🤖</span>
          <span className="text-sm font-semibold text-violet-300">ML Signal Impact</span>
          <span className="text-[10px] text-violet-500 bg-violet-950/50 border border-violet-800/40 rounded-full px-2 py-0.5">
            Live features • Fed into model daily
          </span>
        </div>
        <svg className={`h-4 w-4 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-violet-800/30 px-5 py-5 space-y-5">
          <p className="text-xs text-slate-400 leading-relaxed">
            These three normalised values are computed daily from earnings data and injected into
            every ML model as features via the <code className="text-sky-400">external_signals</code> table.
            They directly influence the <strong className="text-slate-200">Technical Consensus score</strong> on the dashboard.
          </p>

          {loading && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <div className="h-3 w-3 animate-spin rounded-full border border-violet-500 border-t-transparent" />
              Loading ML feature values…
            </div>
          )}
          {error && <p className="text-xs text-rose-400">Could not load features: {error}. Model will use zero-fill fallback.</p>}

          {data && (
            <div className="space-y-5">
              <MlFeatureBar
                label="earnings_days_until_norm"
                value={data.ml_features.earnings_days_until_norm.value}
                description={data.ml_features.earnings_days_until_norm.description}
                interpretation={data.ml_features.earnings_days_until_norm.interpretation}
              />
              <MlFeatureBar
                label="earnings_surprise_score_norm"
                value={data.ml_features.earnings_surprise_score_norm.value}
                description={data.ml_features.earnings_surprise_score_norm.description}
                interpretation={data.ml_features.earnings_surprise_score_norm.interpretation}
              />
              <MlFeatureBar
                label="earnings_beat_streak_norm"
                value={data.ml_features.earnings_beat_streak_norm.value}
                description={data.ml_features.earnings_beat_streak_norm.description}
                interpretation={data.ml_features.earnings_beat_streak_norm.interpretation}
              />

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60">
                {[
                  { label: "Beats",   value: data.summary.quarters_beat,   color: "text-emerald-300" },
                  { label: "Misses",  value: data.summary.quarters_missed, color: "text-rose-300" },
                  { label: "Inline",  value: data.summary.quarters_inline, color: "text-slate-300" },
                  { label: "Avg EPS", value: data.summary.avg_eps_surprise_pct != null
                    ? `${data.summary.avg_eps_surprise_pct > 0 ? "+" : ""}${data.summary.avg_eps_surprise_pct.toFixed(1)}%`
                    : "—",
                    color: (data.summary.avg_eps_surprise_pct ?? 0) > 0 ? "text-emerald-400" : "text-rose-400" },
                ].map(s => (
                  <div key={s.label} className="rounded-lg bg-slate-800/40 px-3 py-2 text-center">
                    <p className={`text-sm font-black ${s.color}`}>{s.value}</p>
                    <p className="text-[10px] text-slate-600">{s.label}</p>
                  </div>
                ))}
              </div>

              <p className="text-[10px] text-slate-600 leading-relaxed border-t border-slate-800/50 pt-3">{data.methodology}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EarningsPage() {
  const [inputValue, setInputValue] = useState("AAPL");
  const [symbol, setSymbol]         = useState("AAPL");

  const { data, error, isLoading } = useSWR<EarningsAnalysisDto>(
    symbol,
    fetchEarningsAnalysis,
    { refreshInterval: 21_600_000, keepPreviousData: true },
  );

  const handleSearch = () => {
    const t = inputValue.trim().toUpperCase();
    if (t) setSymbol(t);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Earnings Tracker</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              EPS surprise history · upcoming calendar · beat/miss score · Yahoo Finance
            </p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="Ticker"
              className="w-28 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:border-slate-500 focus:outline-none"
            />
            <button
              onClick={handleSearch}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
            >
              Search
            </button>
          </div>
        </div>

        {/* Loading */}
        {isLoading && !data && (
          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <p className="text-sm text-slate-400">
              Fetching earnings data for <span className="font-semibold text-slate-200">{symbol}</span>…
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-4 space-y-1">
            <p className="text-sm font-semibold text-rose-400">Unable to load earnings data</p>
            <p className="text-xs text-rose-400/80">{error.message}</p>
            <p className="text-xs text-slate-500 pt-1">
              Only US-listed securities with Yahoo Finance coverage are supported.
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Company strip */}
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
              <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm font-black text-slate-100">{data.symbol}</span>
              <span className="text-sm text-slate-300">{data.company_name}</span>
              <span className="ml-auto text-[10px] text-slate-600">{data.history.length} quarters of data</span>
            </div>

            {/* Top row: gauge + upcoming */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  EPS Surprise Score (last 4Q)
                </h2>
                <SurpriseGauge score={data.surprise_score} />
              </div>

              <div className="space-y-4">
                {data.upcoming ? (
                  <UpcomingCard upcoming={data.upcoming} />
                ) : (
                  <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 flex items-center justify-center">
                    <p className="text-sm text-slate-600">No upcoming earnings date found in Yahoo Finance's calendar window (~3 months).</p>
                  </div>
                )}
              </div>
            </div>

            {/* Surprise chart */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
                EPS Surprise History (%)
              </h2>
              <SurpriseChart history={data.history} />
            </div>

            {/* History table */}
            <HistoryTable history={data.history} />

            {/* Methodology */}
            <MethodologyCard />

            {/* Disclaimer */}
            <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 px-4 py-3">
              <p className="text-[10px] leading-relaxed text-slate-600">{data.disclaimer}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
