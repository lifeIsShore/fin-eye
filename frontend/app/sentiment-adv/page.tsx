"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchAdvancedSentiment,
  type AdvancedSentimentDto,
  type GoogleTrendsDto,
  type StockTwitsSnapshotDto,
  type StockTwitsMessageDto,
} from "@/lib/api";
import ProGate from "@/components/ProGate";
import { BrainCircuit, Info } from "lucide-react";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 58) return "text-teal-400";
  if (score >= 42) return "text-slate-300";
  if (score >= 30) return "text-orange-400";
  return "text-rose-400";
}

function scoreFill(score: number): string {
  if (score >= 70) return "#10b981";
  if (score >= 58) return "#14b8a6";
  if (score >= 42) return "#64748b";
  if (score >= 30) return "#f97316";
  return "#f87171";
}

function labelBadge(label: string | undefined | null): string {
  if (!label) return "bg-slate-800/60 border-slate-700/50 text-slate-400";
  if (label.includes("Strong Bullish")) return "bg-emerald-900/40 border-emerald-700/50 text-emerald-300";
  if (label.includes("Bullish"))        return "bg-teal-900/40 border-teal-700/50 text-teal-300";
  if (label.includes("Neutral"))        return "bg-slate-800/60 border-slate-700/50 text-slate-400";
  if (label.includes("Bearish Lean"))   return "bg-orange-900/40 border-orange-700/50 text-orange-300";
  return "bg-rose-900/40 border-rose-700/50 text-rose-300";
}

function trendColor(d: string): string {
  if (d === "Rising")  return "text-emerald-400";
  if (d === "Falling") return "text-rose-400";
  return "text-slate-400";
}

function trendArrow(d: string): string {
  if (d === "Rising")  return "↑";
  if (d === "Falling") return "↓";
  return "→";
}

function stBadge(sentiment: string): JSX.Element {
  if (sentiment === "Bullish")
    return <span className="rounded-full bg-emerald-900/40 border border-emerald-700/40 px-2 py-0.5 text-[10px] font-bold text-emerald-300">Bullish</span>;
  if (sentiment === "Bearish")
    return <span className="rounded-full bg-rose-900/40 border border-rose-700/40 px-2 py-0.5 text-[10px] font-bold text-rose-300">Bearish</span>;
  return <span className="rounded-full bg-slate-800/60 border border-slate-700/40 px-2 py-0.5 text-[10px] text-slate-500">Neutral</span>;
}

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ─── Composite Arc Gauge ──────────────────────────────────────────────────────

function CompositeGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score);
  const fill = scoreFill(score);
  const angle = Math.PI - (pct / 100) * Math.PI;
  const arcX  = 80 + 66 * Math.cos(angle);
  const arcY  = 88 - 66 * Math.sin(angle);
  const large = pct > 50 ? 1 : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <svg width="160" height="92" viewBox="0 0 160 92" fill="none">
          <path d="M 14 88 A 66 66 0 0 1 146 88" stroke="#1e293b" strokeWidth="13" strokeLinecap="round" fill="none" />
          {pct > 0 && (
            <path
              d={`M 14 88 A 66 66 0 ${large} 1 ${arcX.toFixed(2)} ${arcY.toFixed(2)}`}
              stroke={fill} strokeWidth="13" strokeLinecap="round" fill="none"
            />
          )}
          <line x1="80" y1="22" x2="80" y2="36" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div className="absolute bottom-1 left-0 right-0 flex flex-col items-center leading-none">
          <span className={`text-4xl font-black tabular-nums ${scoreColor(score)}`}>{pct}</span>
          <span className="text-[10px] text-slate-600 mt-0.5">out of 100</span>
        </div>
      </div>
      <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${labelBadge(label)}`}>{label}</span>
      <div className="w-full px-1 space-y-1">
        <div className="flex justify-between text-[9px] text-slate-600">
          <span>Bearish</span><span>Neutral</span><span>Bullish</span>
        </div>
        <div className="relative h-1.5 w-full rounded-full overflow-hidden">
          <div className="absolute inset-0" style={{ background: "linear-gradient(to right,#f87171,#f97316,#64748b,#14b8a6,#10b981)" }} />
          <div className="absolute top-1/2 h-3.5 w-1.5 -translate-y-1/2 -translate-x-1/2 rounded-sm bg-white shadow"
               style={{ left: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}

// ─── Google Trends Panel ──────────────────────────────────────────────────────

function TrendsPanel({ trends }: { trends: GoogleTrendsDto }) {
  const chartData = trends.interest_over_time.map(p => ({
    date: fmtDate(p.date),
    interest: p.interest,
  }));

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Avg Interest</p>
          <p className="text-2xl font-black text-slate-100">{trends.avg_interest.toFixed(0)}</p>
          <p className="text-[10px] text-slate-600">out of 100</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Peak Interest</p>
          <p className="text-2xl font-black text-slate-100">{trends.peak_interest}</p>
          <p className="text-[10px] text-slate-600">period maximum</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Recent Momentum</p>
          <p className={`text-2xl font-black tabular-nums ${trendColor(trends.trend_direction)}`}>
            {trendArrow(trends.trend_direction)} {trends.trend_direction}
          </p>
          <p className="text-[10px] text-slate-600">
            last 4wk vs avg: {trends.recent_vs_avg >= 0 ? "+" : ""}{trends.recent_vs_avg.toFixed(1)}
          </p>
        </div>
      </div>

      {/* Interest over time chart */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Search Interest Over Time — <span className="normal-case text-slate-600">{trends.keyword} · 90 days</span>
        </p>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
              <defs>
                <linearGradient id="trendsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 10 }} axisLine={{ stroke: "#334155" }} tickLine={false} />
              <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                labelStyle={{ color: "#94a3b8", fontSize: 11 }}
                formatter={(v: number) => [`${v}`, "Interest"]}
              />
              <ReferenceLine y={trends.avg_interest} stroke="#475569" strokeDasharray="3 2"
                label={{ value: `avg ${trends.avg_interest.toFixed(0)}`, position: "insideTopRight", fill: "#475569", fontSize: 10 }} />
              <Area type="monotone" dataKey="interest" stroke="#3b82f6" strokeWidth={2}
                fill="url(#trendsGrad)" dot={false} activeDot={{ r: 4, fill: "#3b82f6" }} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-8 text-center text-sm text-slate-600">No Google Trends data available</p>
        )}
      </div>

      {/* Rising queries */}
      {trends.rising_queries.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
            Rising Related Searches
          </p>
          <div className="space-y-2">
            {trends.rising_queries.map((q, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-slate-800/40 px-3 py-2">
                <span className="text-sm text-slate-200">{q.query}</span>
                <span className={`text-xs font-semibold ${q.value === "Breakout" ? "text-amber-300" : "text-blue-300"}`}>
                  {q.value === "Breakout" ? "🔥 Breakout" : `+${q.value}%`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── StockTwits Panel ─────────────────────────────────────────────────────────

function StockTwitsPanel({ data }: { data: StockTwitsSnapshotDto }) {
  const [activeTab, setActiveTab] = useState<"feed" | "bulls" | "bears">("feed");

  const barData = [
    { name: "Bullish", count: data.bullish_count, fill: "#10b981" },
    { name: "Neutral", count: data.neutral_count, fill: "#64748b" },
    { name: "Bearish", count: data.bearish_count, fill: "#f87171" },
  ];

  // Sentiment label styling
  const labelStyle: Record<string, string> = {
    "Very Bullish":  "bg-emerald-900/40 border-emerald-700/40 text-emerald-300",
    "Bullish":       "bg-teal-900/40 border-teal-700/40 text-teal-300",
    "Neutral":       "bg-slate-800/60 border-slate-700/40 text-slate-400",
    "Bearish":       "bg-orange-900/40 border-orange-700/40 text-orange-300",
    "Very Bearish":  "bg-rose-900/40 border-rose-700/40 text-rose-300",
  };

  const msgs = activeTab === "feed"  ? data.recent_messages
             : activeTab === "bulls" ? data.top_bullish
             :                         data.top_bearish;

  return (
    <div className="space-y-4">
      {/* Stats + bar chart */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Sentiment Label</p>
            <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${labelStyle[data.sentiment_label] ?? labelStyle["Neutral"]}`}>
              {data.sentiment_label}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-lg font-black text-emerald-300">{data.bullish_count}</p>
              <p className="text-[10px] text-slate-600">Bullish</p>
              <p className="text-xs font-semibold text-emerald-400">{data.bullish_pct.toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-lg font-black text-slate-400">{data.neutral_count}</p>
              <p className="text-[10px] text-slate-600">Neutral</p>
            </div>
            <div>
              <p className="text-lg font-black text-rose-300">{data.bearish_count}</p>
              <p className="text-[10px] text-slate-600">Bearish</p>
              <p className="text-xs font-semibold text-rose-400">{data.bearish_pct.toFixed(0)}%</p>
            </div>
          </div>
          {data.bull_bear_ratio != null && (
            <div className="rounded-lg bg-slate-800/40 px-3 py-1.5 text-xs flex justify-between">
              <span className="text-slate-500">Bull/Bear ratio</span>
              <span className={`font-bold ${data.bull_bear_ratio >= 1.5 ? "text-emerald-400" : data.bull_bear_ratio < 0.7 ? "text-rose-400" : "text-slate-300"}`}>
                {data.bull_bear_ratio.toFixed(2)}x
              </span>
            </div>
          )}
          <p className="text-[10px] text-slate-600">{data.total_messages} messages analysed</p>
        </div>

        {/* Bar chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Message Breakdown</p>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={barData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" tick={{ fill: "#475569", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#475569", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                formatter={(v: number) => [v, "Messages"]}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
                {barData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Message feed tabs */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        <div className="flex border-b border-slate-800">
          {(["feed", "bulls", "bears"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2.5 text-xs font-semibold transition-colors ${
                activeTab === tab
                  ? "bg-slate-800 text-slate-100"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {tab === "feed"  ? `Recent (${data.recent_messages.length})`
               : tab === "bulls" ? `Top Bullish (${data.top_bullish.length})`
               :                   `Top Bearish (${data.top_bearish.length})`}
            </button>
          ))}
        </div>
        <div className="divide-y divide-slate-800/50 max-h-72 overflow-y-auto">
          {msgs.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-600">No messages</p>
          ) : (
            msgs.map((m, i) => <MessageRow key={i} msg={m} />)
          )}
        </div>
      </div>
    </div>
  );
}

function MessageRow({ msg }: { msg: StockTwitsMessageDto }) {
  const borderColor =
    msg.sentiment === "Bullish" ? "border-l-emerald-500/50" :
    msg.sentiment === "Bearish" ? "border-l-rose-500/50"    :
    "border-l-slate-700/50";

  return (
    <div className={`px-4 py-3 border-l-2 ${borderColor} hover:bg-slate-800/20`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-semibold text-slate-300">@{msg.username}</span>
        {stBadge(msg.sentiment)}
        {msg.likes > 0 && (
          <span className="ml-auto text-[10px] text-slate-600">♥ {msg.likes}</span>
        )}
      </div>
      <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">{msg.body}</p>
      {msg.created_at && (
        <p className="text-[10px] text-slate-700 mt-1">{msg.created_at}</p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdvancedSentimentPage() {
  const [inputValue, setInputValue] = useState("AAPL");
  const [symbol, setSymbol]         = useState("AAPL");

  const { data, error, isLoading } = useSWR<AdvancedSentimentDto>(
    symbol,
    fetchAdvancedSentiment,
    { refreshInterval: 900_000, keepPreviousData: true },    // 15 min (StockTwits cache)
  );

  const handleSearch = () => {
    const t = inputValue.trim().toUpperCase();
    if (t) setSymbol(t);
  };

  return (
    <ProGate feature="Advanced Sentiment Analysis">
      <div className="min-h-screen bg-slate-950 text-slate-200">
        <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Advanced Sentiment</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Google Trends search interest · StockTwits bull/bear ratio · composite score
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
              Fetching sentiment for <span className="font-semibold text-slate-200">{symbol}</span>
              <span className="text-slate-600"> — Google Trends may take up to 15s…</span>
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-4">
            <p className="text-sm font-semibold text-rose-400">Unable to load sentiment data</p>
            <p className="text-xs text-rose-400/80 mt-1">{error.message}</p>
          </div>
        )}

        {data && (
          <>
            {/* Company + composite strip */}
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
              <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm font-black text-slate-100">{data.symbol}</span>
              <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${labelBadge(data.composite_label)}`}>
                {data.composite_label}
              </span>
              <span className="ml-auto text-[10px] text-slate-600">Refreshes every 15 min</span>
            </div>

            {/* Top row: composite gauge + source availability */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Composite Sentiment Score
                </h2>
                <CompositeGauge score={data.composite_score} label={data.composite_label} />
                <div className="space-y-1.5 text-xs">
                  <p className="text-slate-600 text-[10px] uppercase tracking-wider font-semibold">Sources</p>
                  <div className={`flex items-center gap-2 ${data.google_trends ? "text-emerald-400" : "text-slate-600"}`}>
                    <div className={`h-2 w-2 rounded-full ${data.google_trends ? "bg-emerald-500" : "bg-slate-700"}`} />
                    Google Trends {data.google_trends ? "✓" : "unavailable"}
                  </div>
                  <div className={`flex items-center gap-2 ${data.stocktwits ? "text-emerald-400" : "text-slate-600"}`}>
                    <div className={`h-2 w-2 rounded-full ${data.stocktwits ? "bg-emerald-500" : "bg-slate-700"}`} />
                    StockTwits {data.stocktwits ? "✓" : "unavailable"}
                  </div>
                </div>
              </div>

              {/* Quick stats from each source */}
              <div className="md:col-span-2 grid grid-cols-2 gap-3 content-start">
                {data.google_trends && (
                  <>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Search Trend</p>
                      <p className={`text-xl font-black ${trendColor(data.google_trends.trend_direction)}`}>
                        {trendArrow(data.google_trends.trend_direction)} {data.google_trends.trend_direction}
                      </p>
                      <p className="text-[10px] text-slate-600">last 4wk vs avg: {data.google_trends.recent_vs_avg >= 0 ? "+" : ""}{data.google_trends.recent_vs_avg.toFixed(1)}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Avg Search Interest</p>
                      <p className="text-xl font-black text-slate-100">{data.google_trends.avg_interest.toFixed(0)}<span className="text-sm font-normal text-slate-500">/100</span></p>
                      <p className="text-[10px] text-slate-600">peak: {data.google_trends.peak_interest} this period</p>
                    </div>
                  </>
                )}
                {data.stocktwits && (
                  <>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Bullish %</p>
                      <p className="text-xl font-black text-emerald-300">{data.stocktwits.bullish_pct.toFixed(0)}%</p>
                      <p className="text-[10px] text-slate-600">{data.stocktwits.bullish_count} / {data.stocktwits.total_messages} messages</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Bull/Bear Ratio</p>
                      <p className={`text-xl font-black ${data.stocktwits.bull_bear_ratio != null && data.stocktwits.bull_bear_ratio >= 1.5 ? "text-emerald-300" : data.stocktwits.bull_bear_ratio != null && data.stocktwits.bull_bear_ratio < 0.7 ? "text-rose-300" : "text-slate-100"}`}>
                        {data.stocktwits.bull_bear_ratio != null ? `${data.stocktwits.bull_bear_ratio.toFixed(2)}x` : "—"}
                      </p>
                      <p className="text-[10px] text-slate-600">{data.stocktwits.sentiment_label}</p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Google Trends section */}
            {data.google_trends && (
              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                  Google Trends
                </h2>
                <TrendsPanel trends={data.google_trends} />
              </div>
            )}

            {!data.google_trends && (
              <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-5 text-center space-y-1">
                <p className="text-sm font-semibold text-slate-500">Google Trends unavailable</p>
                <p className="text-xs text-slate-600">pytrends may be rate-limited. Data will refresh automatically in 4 hours.</p>
              </div>
            )}

            {/* StockTwits section */}
            {data.stocktwits && (
              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  StockTwits Feed
                </h2>
                <StockTwitsPanel data={data.stocktwits} />
              </div>
            )}

            {/* Methodology */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Methodology</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
                <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
                  <p className="font-semibold text-slate-200">Google Trends</p>
                  <p>Interest-over-time (0–100 normalised) for "{data.symbol} stock" keyword, 90-day window, weekly granularity. Rising queries surface narrative shifts. Cached 4h to avoid rate limits.</p>
                </div>
                <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
                  <p className="font-semibold text-slate-200">StockTwits</p>
                  <p>Self-reported Bullish/Bearish tags from the most recent ~30 public messages. No NLP — user-supplied labels only. Highly real-time retail signal. Cached 15 min.</p>
                </div>
                <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
                  <p className="font-semibold text-slate-200">Composite Score</p>
                  <p>Weighted: StockTwits bullish ratio 60%, Google Trends momentum shift 40%. 50 = neutral. Score is sentiment blend — does not incorporate price action.</p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 px-4 py-3">
              <p className="text-[10px] leading-relaxed text-slate-600">{data.disclaimer}</p>
            </div>
          </>
        )}
      </div>
      </div>
    </ProGate>
  );
}
