"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import {
  fetchShortAnalysis,
  type ShortAnalysisDto,
  type ShortVolumeDayDto,
  type SqueezeScoreDto,
} from "../../lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtShares(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return v.toLocaleString();
}

function fmtPct(v: number | null, decimals = 1): string {
  if (v == null) return "—";
  return v.toFixed(decimals) + "%";
}

function fmtNum(v: number | null, decimals = 2): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function fmtPrice(v: number | null): string {
  if (v == null) return "—";
  return "$" + v.toFixed(2);
}

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric",
  });
}

// Squeeze score colour helpers
function scoreTextColor(score: number): string {
  if (score >= 75) return "text-rose-400";
  if (score >= 60) return "text-orange-400";
  if (score >= 40) return "text-amber-400";
  if (score >= 25) return "text-teal-400";
  return "text-emerald-400";
}

function scoreFillColor(score: number): string {
  if (score >= 75) return "#f87171";
  if (score >= 60) return "#fb923c";
  if (score >= 40) return "#fbbf24";
  if (score >= 25) return "#2dd4bf";
  return "#34d399";
}

function scoreBadgeClass(label: string): string {
  const map: Record<string, string> = {
    "Extreme Squeeze Risk": "bg-rose-900/40 border-rose-700/50 text-rose-300",
    "High Squeeze Risk":    "bg-orange-900/40 border-orange-700/50 text-orange-300",
    "Moderate":             "bg-amber-900/40 border-amber-700/50 text-amber-300",
    "Low":                  "bg-teal-900/40 border-teal-700/50 text-teal-300",
    "Minimal":              "bg-emerald-900/40 border-emerald-700/50 text-emerald-300",
  };
  return map[label] ?? "bg-slate-800 border-slate-700 text-slate-300";
}

function trendBadge(direction: string): JSX.Element {
  const styles: Record<string, string> = {
    "Rising":              "bg-rose-900/40 border-rose-700/40 text-rose-300",
    "Falling":             "bg-emerald-900/40 border-emerald-700/40 text-emerald-300",
    "Flat":                "bg-slate-800/60 border-slate-700/40 text-slate-400",
    "Insufficient data":   "bg-slate-800/60 border-slate-700/40 text-slate-600",
  };
  const arrows: Record<string, string> = {
    "Rising": "↑", "Falling": "↓", "Flat": "→", "Insufficient data": "—",
  };
  const cls = styles[direction] ?? styles["Flat"];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      {arrows[direction] ?? ""} {direction}
    </span>
  );
}

// ─── Squeeze Arc Gauge (same inline SVG pattern as Insiders / Earnings) ───────

function SqueezeGauge({ score }: { score: SqueezeScoreDto }) {
  const pct   = Math.round(score.score);
  const fill  = scoreFillColor(score.score);
  const angle = Math.PI - (pct / 100) * Math.PI;
  const arcX  = 80 + 66 * Math.cos(angle);
  const arcY  = 88 - 66 * Math.sin(angle);
  const largeArc = pct > 50 ? 1 : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <svg width="160" height="92" viewBox="0 0 160 92" fill="none">
          {/* Track */}
          <path d="M 14 88 A 66 66 0 0 1 146 88" stroke="#1e293b" strokeWidth="13" strokeLinecap="round" fill="none" />
          {/* Fill arc */}
          {pct > 0 && (
            <path
              d={`M 14 88 A 66 66 0 ${largeArc} 1 ${arcX.toFixed(2)} ${arcY.toFixed(2)}`}
              stroke={fill}
              strokeWidth="13"
              strokeLinecap="round"
              fill="none"
            />
          )}
          {/* Tick at centre */}
          <line x1="80" y1="22" x2="80" y2="36" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div className="absolute bottom-1 left-0 right-0 flex flex-col items-center leading-none">
          <span className={`text-4xl font-black tabular-nums ${scoreTextColor(score.score)}`}>{pct}</span>
          <span className="text-[10px] text-slate-600 mt-0.5">out of 100</span>
        </div>
      </div>

      {/* Label badge */}
      <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${scoreBadgeClass(score.label)}`}>
        {score.label}
      </span>

      {/* Gradient bar: green (low risk) → red (high risk) */}
      <div className="w-full px-1 space-y-1">
        <div className="flex justify-between text-[9px] text-slate-600">
          <span>Minimal</span><span>Moderate</span><span>Extreme</span>
        </div>
        <div className="relative h-1.5 w-full rounded-full overflow-hidden">
          <div className="absolute inset-0" style={{ background: "linear-gradient(to right,#34d399,#2dd4bf,#fbbf24,#fb923c,#f87171)" }} />
          <div
            className="absolute top-1/2 h-3.5 w-1.5 -translate-y-1/2 -translate-x-1/2 rounded-sm bg-white shadow"
            style={{ left: `${pct}%` }}
          />
        </div>
      </div>

      {/* Drivers list */}
      {score.drivers.length > 0 && (
        <div className="w-full space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Key squeeze drivers</p>
          {score.drivers.map((d, i) => (
            <div key={i} className="flex items-start gap-2 rounded-lg bg-rose-950/20 border border-rose-800/30 px-3 py-1.5 text-xs text-rose-300">
              <span className="text-rose-500 mt-0.5 flex-shrink-0">▲</span>
              {d}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Stats grid ───────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: "warn" | "good" | "neutral";
}) {
  const textColor =
    highlight === "warn"    ? "text-rose-300" :
    highlight === "good"    ? "text-emerald-300" :
    "text-slate-100";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 space-y-0.5">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">{label}</p>
      <p className={`text-xl font-black tabular-nums ${textColor}`}>{value}</p>
      {sub && <p className="text-[10px] text-slate-500">{sub}</p>}
    </div>
  );
}

// ─── 52-week price range bar ──────────────────────────────────────────────────

function PriceRangeBar({ data }: { data: ShortAnalysisDto }) {
  const { price_52w_low, price_52w_high, current_price } = data;
  if (!price_52w_low || !price_52w_high || !current_price) return null;

  const range = price_52w_high - price_52w_low;
  const position = range > 0 ? ((current_price - price_52w_low) / range) * 100 : 50;
  const clampedPos = Math.max(2, Math.min(98, position));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">52-Week Price Range</h3>
      <div className="space-y-2">
        <div className="relative h-3 rounded-full bg-slate-800">
          {/* Gradient range bar */}
          <div className="absolute inset-0 rounded-full overflow-hidden">
            <div className="h-full w-full" style={{ background: "linear-gradient(to right,#ef4444,#f97316,#84cc16,#22c55e)" }} />
          </div>
          {/* Current price marker */}
          <div
            className="absolute top-1/2 h-5 w-1.5 -translate-y-1/2 -translate-x-1/2 rounded-sm bg-white shadow-lg"
            style={{ left: `${clampedPos}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-500">
          <span>{fmtPrice(price_52w_low)} <span className="text-[10px] text-slate-700">52w low</span></span>
          <span className="font-semibold text-slate-200">{fmtPrice(current_price)} <span className="text-[10px] text-slate-500">current</span></span>
          <span>{fmtPrice(price_52w_high)} <span className="text-[10px] text-slate-700">52w high</span></span>
        </div>
      </div>
      {data.pct_from_52w_high != null && (
        <div className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-1.5 text-xs">
          <span className="text-slate-500">Distance from 52w high</span>
          <span className={data.pct_from_52w_high < -20 ? "text-rose-400 font-semibold" : "text-slate-300"}>
            {fmtPct(data.pct_from_52w_high)}
          </span>
        </div>
      )}
    </div>
  );
}

// ─── FINRA Short Volume Trend Chart ──────────────────────────────────────────

interface TrendPoint {
  date: string;
  ratio_pct: number;
}

const CustomTrendTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="font-semibold text-slate-100">{payload[0].value.toFixed(1)}% of volume was short</p>
    </div>
  );
};

function ShortVolumeTrendChart({ trend }: { trend: ShortVolumeDayDto[] }) {
  if (trend.length === 0) {
    return (
      <div className="flex h-36 items-center justify-center text-sm text-slate-600">
        No FINRA short volume data available
      </div>
    );
  }

  const chartData: TrendPoint[] = trend
    .slice()
    .reverse()   // oldest on left
    .map(d => ({
      date: fmtDate(d.date),
      ratio_pct: parseFloat((d.short_volume_ratio * 100).toFixed(1)),
    }));

  const avgRatio = chartData.reduce((s, d) => s + d.ratio_pct, 0) / chartData.length;

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={chartData} margin={{ top: 10, right: 8, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id="shortGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#f87171" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#f87171" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => `${v}%`}
          domain={["auto", "auto"]}
        />
        <Tooltip content={<CustomTrendTooltip />} />
        <ReferenceLine
          y={avgRatio}
          stroke="#475569"
          strokeDasharray="4 2"
          label={{ value: `avg ${avgRatio.toFixed(1)}%`, position: "insideTopRight", fill: "#64748b", fontSize: 10 }}
        />
        <Area
          type="monotone"
          dataKey="ratio_pct"
          stroke="#f87171"
          strokeWidth={2}
          fill="url(#shortGradient)"
          dot={{ fill: "#f87171", r: 3, strokeWidth: 0 }}
          activeDot={{ r: 5, fill: "#f87171" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── Methodology card ─────────────────────────────────────────────────────────

function MethodologyCard() {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Score Methodology</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Data Sources</p>
          <p>Short float % and days-to-cover from Yahoo Finance (yfinance). Daily short volume from FINRA REGSHO settlement files — free, no API key. Cached 4 hours.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Squeeze Score</p>
          <p>Composite of: short float % (45pts), days-to-cover (25pts), distance from 52w high (15pts), FINRA trend direction (10pts), borrow fee (5pts). Capped 5–95.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">FINRA Volume</p>
          <p>REGSHO daily files report short volume as a % of FINRA-visible volume. Excludes some dark pool and OTC prints — use as a directional trend signal, not absolute count.</p>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ShortsPage() {
  const [inputValue, setInputValue] = useState("GME");
  const [symbol, setSymbol]         = useState("GME");

  const { data, error, isLoading } = useSWR<ShortAnalysisDto>(
    symbol,
    fetchShortAnalysis,
    { refreshInterval: 14_400_000, keepPreviousData: true },
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
            <h1 className="text-2xl font-bold text-slate-100">Short Interest</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Short float · days-to-cover · squeeze risk score · FINRA daily trend
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
              Fetching short interest data for <span className="font-semibold text-slate-200">{symbol}</span>…
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-4 space-y-1">
            <p className="text-sm font-semibold text-rose-400">Unable to load short interest data</p>
            <p className="text-xs text-rose-400/80">{error.message}</p>
            <p className="text-xs text-slate-500 pt-1">
              Only US-listed securities with Yahoo Finance and FINRA REGSHO coverage are supported.
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Company strip */}
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
              <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm font-black text-slate-100">{data.symbol}</span>
              <span className="text-sm text-slate-300">{data.company_name}</span>
              <div className="ml-auto flex items-center gap-3">
                <span className="text-xs text-slate-600">Short trend:</span>
                {trendBadge(data.trend_direction)}
              </div>
            </div>

            {/* Top grid: gauge + key stats */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Squeeze gauge */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Short Squeeze Risk Score
                </h2>
                <SqueezeGauge score={data.squeeze_score} />
              </div>

              {/* Stats grid */}
              <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-3 gap-3 content-start">
                <StatCard
                  label="Short Float %"
                  value={fmtPct(data.short_float_pct)}
                  sub="% of float sold short"
                  highlight={
                    data.short_float_pct != null
                      ? data.short_float_pct >= 20 ? "warn"
                      : data.short_float_pct <= 5  ? "good"
                      : "neutral"
                      : "neutral"
                  }
                />
                <StatCard
                  label="Days-to-Cover"
                  value={fmtNum(data.short_ratio)}
                  sub="short interest / avg daily vol"
                  highlight={
                    data.short_ratio != null
                      ? data.short_ratio >= 5 ? "warn"
                      : data.short_ratio <= 1 ? "good"
                      : "neutral"
                      : "neutral"
                  }
                />
                <StatCard
                  label="Shares Short"
                  value={fmtShares(data.shares_short)}
                  sub="absolute shares shorted"
                />
                <StatCard
                  label="Float Shares"
                  value={fmtShares(data.float_shares)}
                  sub="tradeable float"
                />
                <StatCard
                  label="Avg Volume (10d)"
                  value={fmtShares(data.avg_volume_10d)}
                  sub="daily avg trading volume"
                />
                <StatCard
                  label="Borrow Fee"
                  value={data.borrow_fee_rate != null ? fmtPct(data.borrow_fee_rate) : "N/A"}
                  sub="annualised cost to borrow"
                  highlight={
                    data.borrow_fee_rate != null
                      ? data.borrow_fee_rate >= 10 ? "warn" : "neutral"
                      : "neutral"
                  }
                />
              </div>
            </div>

            {/* 52-week price range */}
            <PriceRangeBar data={data} />

            {/* FINRA short volume trend */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  FINRA Short Volume Trend (% of daily volume)
                </h2>
                <span className="text-[10px] text-slate-600">{data.short_volume_trend.length} trading day{data.short_volume_trend.length !== 1 ? "s" : ""}</span>
              </div>
              <ShortVolumeTrendChart trend={data.short_volume_trend} />

              {/* Trend table */}
              {data.short_volume_trend.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-600">
                        <th className="text-left px-3 py-2">Date</th>
                        <th className="text-right px-3 py-2">Short Volume</th>
                        <th className="text-right px-3 py-2">Total Volume</th>
                        <th className="text-right px-3 py-2">Short %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {data.short_volume_trend.map((d, i) => (
                        <tr key={i} className="hover:bg-slate-800/20">
                          <td className="px-3 py-2 text-slate-400">{fmtDate(d.date)}</td>
                          <td className="px-3 py-2 text-right text-slate-300 tabular-nums font-mono">{fmtShares(d.short_volume)}</td>
                          <td className="px-3 py-2 text-right text-slate-400 tabular-nums font-mono">{fmtShares(d.total_volume)}</td>
                          <td className={`px-3 py-2 text-right tabular-nums font-semibold ${d.short_volume_ratio > 0.5 ? "text-rose-400" : d.short_volume_ratio > 0.4 ? "text-orange-400" : "text-slate-300"}`}>
                            {(d.short_volume_ratio * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

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
