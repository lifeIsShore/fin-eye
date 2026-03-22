"use client";

import useSWR from "swr";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from "recharts";
import {
  fetchFedPolicy,
  type FedPolicyDto,
  type RateRangeDto,
  type RatePointDto,
  type DotPlotProjectionDto,
  type ForwardExpectationDto,
} from "../../lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtRate(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toFixed(2) + "%";
}

function fmtBillions(v: number | null | undefined): string {
  if (v == null) return "—";
  return "$" + v.toFixed(1) + "T";
}

function fmtDate(d: string): string {
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function fmtDateFull(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// Thin down a series to at most N evenly-spaced points for charting
function thinSeries<T>(pts: T[], max = 120): T[] {
  if (pts.length <= max) return pts;
  const step = Math.ceil(pts.length / max);
  return pts.filter((_, i) => i % step === 0 || i === pts.length - 1);
}

function trendBadge(trend: string): JSX.Element {
  const styles: Record<string, string> = {
    "Hiking":  "bg-rose-900/40 border-rose-700/40 text-rose-300",
    "Cutting": "bg-emerald-900/40 border-emerald-700/40 text-emerald-300",
    "Holding": "bg-amber-900/40 border-amber-700/40 text-amber-300",
    "Unknown": "bg-slate-800/60 border-slate-700/40 text-slate-500",
  };
  const arrows: Record<string, string> = {
    "Hiking": "↑", "Cutting": "↓", "Holding": "→", "Unknown": "—",
  };
  const cls = styles[trend] ?? styles["Unknown"];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-bold ${cls}`}>
      {arrows[trend] ?? ""} {trend}
    </span>
  );
}

// ─── Current Rate Hero ────────────────────────────────────────────────────────

function RateHero({ data }: { data: FedPolicyDto }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 sm:col-span-2">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 mb-1">Fed Funds Target Range</p>
        <p className="text-4xl font-black tabular-nums text-slate-100">
          {data.current_target_lower.toFixed(2)}
          <span className="text-2xl text-slate-500 mx-1">–</span>
          {data.current_target_upper.toFixed(2)}
          <span className="text-base font-normal text-slate-500 ml-1">%</span>
        </p>
        <div className="mt-2 flex items-center gap-2">
          {trendBadge(data.hike_or_cut_trend)}
          {data.total_moves_ytd !== 0 && (
            <span className="text-xs text-slate-500">
              {data.total_moves_ytd > 0 ? "+" : ""}{data.total_moves_ytd}bps YTD
            </span>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Effective Rate (DFF)</p>
        <p className="text-2xl font-black tabular-nums text-slate-100">{fmtRate(data.current_effective_rate)}</p>
        <p className="text-[10px] text-slate-600 mt-1">latest daily print</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Balance Sheet</p>
        <p className="text-2xl font-black tabular-nums text-slate-100">
          {data.current_balance_sheet_b != null
            ? "$" + (data.current_balance_sheet_b / 1000).toFixed(1) + "T"
            : "—"}
        </p>
        <p className="text-[10px] text-slate-600 mt-1">Fed total assets</p>
      </div>
    </div>
  );
}

// ─── Rate History Chart ───────────────────────────────────────────────────────

function RateHistoryChart({ data }: { data: FedPolicyDto }) {
  // Merge target range + DFF into aligned chart series
  const dffMap = new Map(data.effective_rate_history.map(p => [p.date, p.value]));

  const thinned = thinSeries(data.target_range_history);
  const chartData = thinned.map(r => ({
    date: fmtDate(r.date),
    lower: r.lower,
    upper: r.upper,
    mid: r.midpoint,
    dff: dffMap.get(r.date) ?? null,
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Fed Funds Target Range & Effective Rate — 3 Years
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#475569", fontSize: 10 }}
            axisLine={{ stroke: "#334155" }}
            tickLine={false}
            interval={Math.floor(chartData.length / 8)}
          />
          <YAxis
            tick={{ fill: "#475569", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `${v}%`}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            formatter={(v: number, name: string) => [`${v?.toFixed(2)}%`, name]}
          />
          <Legend
            wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "8px" }}
            formatter={(value) => ({
              lower: "Target Lower", upper: "Target Upper", mid: "Midpoint", dff: "Effective (DFF)"
            }[String(value) as "lower" | "upper" | "mid" | "dff"] ?? value)}
          />
          {/* Shaded range band */}
          <Line type="stepAfter" dataKey="lower" stroke="#3b82f6" strokeWidth={1} dot={false} strokeDasharray="4 2" name="lower" />
          <Line type="stepAfter" dataKey="upper" stroke="#3b82f6" strokeWidth={1} dot={false} strokeDasharray="4 2" name="upper" />
          <Line type="stepAfter" dataKey="mid"   stroke="#60a5fa" strokeWidth={2} dot={false} name="mid" />
          <Line type="monotone"  dataKey="dff"   stroke="#34d399" strokeWidth={1.5} dot={false} name="dff" connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Balance Sheet Chart ──────────────────────────────────────────────────────

function BalanceSheetChart({ history }: { history: RatePointDto[] }) {
  if (history.length === 0) return null;
  const chartData = thinSeries(history, 100).map(p => ({
    date: fmtDate(p.date),
    assets: parseFloat((p.value / 1000).toFixed(2)),   // billions → trillions
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Fed Balance Sheet (Total Assets, $T) — 3 Years
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="bsGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 10 }} axisLine={{ stroke: "#334155" }} tickLine={false}
            interval={Math.floor(chartData.length / 6)} />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={v => `$${v}T`} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            formatter={(v: number) => [`$${v.toFixed(2)}T`, "Total Assets"]}
          />
          <Area type="monotone" dataKey="assets" stroke="#8b5cf6" strokeWidth={2}
            fill="url(#bsGrad)" dot={false} activeDot={{ r: 4, fill: "#8b5cf6" }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── SOFR vs DFF Chart ────────────────────────────────────────────────────────

function SofrChart({ sofr, dff }: { sofr: RatePointDto[]; dff: RatePointDto[] }) {
  if (sofr.length === 0) return null;
  const dffMap = new Map(dff.map(p => [p.date, p.value]));
  const chartData = thinSeries(sofr, 120).map(p => ({
    date: fmtDate(p.date),
    sofr: p.value,
    dff: dffMap.get(p.date) ?? null,
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
        SOFR vs Effective Fed Funds Rate — 3 Years
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 10 }} axisLine={{ stroke: "#334155" }} tickLine={false}
            interval={Math.floor(chartData.length / 8)} />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={v => `${v}%`} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            formatter={(v: any, name: string) => [typeof v === "number" ? `${v.toFixed(3)}%` : "—", name === "sofr" ? "SOFR" : "DFF"]}
          />
          <Legend wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "8px" }}
            formatter={(v) => v === "sofr" ? "SOFR" : "Effective FFR"} />
          <Line type="monotone" dataKey="sofr" stroke="#f59e0b" strokeWidth={2} dot={false} name="sofr" />
          <Line type="monotone" dataKey="dff"  stroke="#34d399" strokeWidth={1.5} dot={false} name="dff" connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Dot Plot ─────────────────────────────────────────────────────────────────

function DotPlotPanel({ dots, current }: { dots: DotPlotProjectionDto[]; current: number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
      <div className="flex items-start justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          FOMC Dot Plot — SEP Median Projections
        </h3>
        {dots[0] && (
          <span className="text-[10px] text-slate-600">{dots[0].as_of_label}</span>
        )}
      </div>

      <div className="space-y-3">
        {dots.map((d) => {
          const isLongerRun = d.year === "longer_run";
          const delta = d.median_rate - current;
          const impliedMoves = Math.round(delta / 0.25);   // 25bp increments

          return (
            <div key={d.year} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className={`font-semibold ${isLongerRun ? "text-slate-500" : "text-slate-200"}`}>
                  {isLongerRun ? "Longer Run" : d.year}
                </span>
                <div className="flex items-center gap-3">
                  {!isLongerRun && (
                    <span className={`text-[10px] ${delta < 0 ? "text-emerald-400" : delta > 0 ? "text-rose-400" : "text-slate-500"}`}>
                      {delta > 0 ? "+" : ""}{delta.toFixed(2)}% vs current
                      {impliedMoves !== 0 && ` (${impliedMoves > 0 ? "+" : ""}${impliedMoves} × 25bp)`}
                    </span>
                  )}
                  <span className={`font-black text-sm tabular-nums ${isLongerRun ? "text-slate-400" : "text-slate-100"}`}>
                    {d.median_rate.toFixed(3)}%
                  </span>
                </div>
              </div>
              {/* Visual bar */}
              <div className="relative h-1.5 w-full rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full ${isLongerRun ? "bg-slate-600" : delta < 0 ? "bg-emerald-500" : delta > 0 ? "bg-rose-500" : "bg-blue-500"}`}
                  style={{ width: `${Math.min(100, (d.median_rate / 6) * 100)}%` }}
                />
                {/* Current rate marker */}
                <div
                  className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-slate-400"
                  style={{ left: `${Math.min(100, (current / 6) * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-slate-600">
        Vertical bar = current target midpoint. Red = projected above current, green = below (cuts implied).
        Dot plot updated each FOMC meeting quarter (March, June, September, December).
      </p>
    </div>
  );
}

// ─── Forward Expectations ─────────────────────────────────────────────────────

function ForwardTable({ expectations, current }: { expectations: ForwardExpectationDto[]; current: number }) {
  if (expectations.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Market Rate Expectations (Treasury Yield Proxies)
      </h3>
      <div className="space-y-2">
        {expectations.map((e, i) => {
          const delta = e.implied_rate - current;
          return (
            <div key={i} className="flex items-center justify-between rounded-lg bg-slate-800/40 px-4 py-2.5">
              <div>
                <p className="text-sm font-medium text-slate-200">{e.label}</p>
                <p className="text-[10px] text-slate-600">{e.source}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-black tabular-nums text-slate-100">{e.implied_rate.toFixed(2)}%</p>
                <p className={`text-[10px] tabular-nums ${delta < 0 ? "text-emerald-400" : delta > 0 ? "text-rose-400" : "text-slate-500"}`}>
                  {delta >= 0 ? "+" : ""}{delta.toFixed(2)}% vs current
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[10px] text-slate-600">
        These are Treasury yield proxies, not actual fed funds futures — use as directional indicators only.
      </p>
    </div>
  );
}

// ─── Reverse Repo Chart ───────────────────────────────────────────────────────

function ReverseRepoChart({ history, current }: { history: RatePointDto[]; current: number | null }) {
  if (history.length === 0) return null;
  const chartData = thinSeries(history, 120).map(p => ({
    date: fmtDate(p.date),
    rrp: p.value,
  }));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Overnight Reverse Repo (RRP) — Billions
        </h3>
        {current != null && (
          <span className="text-xs font-semibold text-slate-300">${current.toFixed(1)}B current</span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="rrpGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 10 }} axisLine={{ stroke: "#334155" }} tickLine={false}
            interval={Math.floor(chartData.length / 6)} />
          <YAxis tick={{ fill: "#475569", fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={v => `$${v}B`} domain={[0, "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            formatter={(v: number) => [`$${v.toFixed(1)}B`, "Reverse Repo"]}
          />
          <Area type="monotone" dataKey="rrp" stroke="#f59e0b" strokeWidth={2}
            fill="url(#rrpGrad)" dot={false} activeDot={{ r: 4, fill: "#f59e0b" }} />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-slate-600 mt-2">
        RRP draining = liquidity leaving the facility = tighter financial conditions. Rising RRP = excess cash parked at Fed.
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FedPolicyPage() {
  const { data, error, isLoading } = useSWR<FedPolicyDto>(
    "fed-policy",
    fetchFedPolicy,
    { refreshInterval: 10_800_000, keepPreviousData: true },  // 3h
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Fed Policy</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Target rate · balance sheet · SOFR · dot plot · market expectations · FRED data
          </p>
        </div>

        {/* Loading */}
        {isLoading && !data && (
          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <p className="text-sm text-slate-400">Fetching Fed data from FRED…</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-4 space-y-1">
            <p className="text-sm font-semibold text-rose-400">Unable to load Fed policy data</p>
            <p className="text-xs text-rose-400/80">{error.message}</p>
            <p className="text-xs text-slate-500 pt-1">
              FRED requires a valid API key in backend settings (<code className="text-slate-400">FRED_API_KEY</code>).
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Current rate hero */}
            <RateHero data={data} />

            {/* Rate history */}
            <RateHistoryChart data={data} />

            {/* Dot plot + forward expectations side by side on wide screens */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <DotPlotPanel dots={data.dot_plot} current={data.current_midpoint} />
              <ForwardTable expectations={data.forward_expectations} current={data.current_midpoint} />
            </div>

            {/* Balance sheet */}
            <BalanceSheetChart history={data.balance_sheet_history} />

            {/* SOFR */}
            <SofrChart sofr={data.sofr_history} dff={data.effective_rate_history} />

            {/* Reverse repo */}
            <ReverseRepoChart history={data.reverse_repo_history} current={data.current_reverse_repo_b} />

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
