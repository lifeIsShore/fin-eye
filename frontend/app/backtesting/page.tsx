"use client";

import { useState, useEffect, useCallback } from "react";
import {
  runBacktest,
  BacktestRequest,
  BacktestResponse,
  TradeRecord,
  saveStrategy,
  fetchMyStrategies,
  fetchPublicStrategies,
  deleteStrategy,
  updateStrategy,
  StrategyDto,
  runWalkForward,
  WalkForwardResponse,
  WalkForwardFold,
} from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from "recharts";
import {
  BarChart,
  Bar,
  Cell,
  XAxis as RechartXAxis,
  YAxis as RechartYAxis,
  CartesianGrid as RechartGrid,
  Tooltip as RechartTooltip,
  ResponsiveContainer as RechartContainer,
  ReferenceLine,
} from "recharts";
import {
  AlertTriangle,
  Info,
  TrendingUp,
  Activity,
  BookOpen,
  Save,
  Trash2,
  Globe,
  Lock,
  ChevronDown,
  ChevronUp,
  FlaskConical,
  ShieldAlert,
  SlidersHorizontal,
  Loader2,
} from "lucide-react";
import { PageBanner } from "@/components/ui/PageBanner";
import { useSymbol } from "@/lib/symbolContext";

// ─── Inline risk disclaimer bar (todos-v3.md UX-LEGAL-01) ────────────────────

function RiskDisclaimerBar() {
  return (
    <div className="rounded-xl border border-amber-700/30 bg-amber-950/15 px-4 py-3 flex items-start gap-3">
      <ShieldAlert className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-amber-300/80 leading-relaxed">
        <span className="font-semibold text-amber-300">Educational use only.</span>{" "}
        Backtests use historical data and do not account for slippage, market
        impact, or regime changes. Past performance does not predict future
        results. This tool is not investment advice — always consult a qualified
        financial professional before making trading decisions.
      </p>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function OverfittingWarning({ triggered }: { triggered: boolean }) {
  return (
    <div
      className={`rounded-xl border p-4 ${triggered
          ? "border-red-500/40 bg-red-950/30"
          : "border-amber-500/30 bg-amber-950/20"
        }`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={`mt-0.5 h-5 w-5 flex-shrink-0 ${triggered ? "text-red-400" : "text-amber-400"
            }`}
        />
        <div>
          <p
            className={`text-sm font-semibold ${triggered ? "text-red-300" : "text-amber-300"
              }`}
          >
            {triggered
              ? "⚠ High Overfitting Risk Detected (Sharpe > 1.2)"
              : "Backtest Disclaimer"}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            Backtests use historical data. Strategies tuned to past performance
            often{" "}
            <strong className="text-slate-300">fail in live trading</strong>.
            {triggered &&
              " A Sharpe ratio above 1.2 in-sample is a strong indicator of curve-fitting. "}
            Expect real-world performance to be roughly 30–50% of backtest
            results. This is for{" "}
            <strong className="text-slate-300">educational purposes only</strong>{" "}
            — not investment advice.
          </p>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color = "text-slate-100",
  sub,
}: {
  label: string;
  value: string;
  color?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tracking-tight ${color}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

// ─── Monthly Returns Heatmap (todos-v3.md UX-BACKTEST-02) ────────────────────

function buildMonthlyReturns(
  equityCurve: { date: string; equity: number }[],
): { year: number; month: number; return_pct: number }[] {
  if (equityCurve.length < 2) return [];

  // Group by year-month, take first and last equity value of each month
  const byMonth: Record<string, { first: number; last: number }> = {};
  for (const point of equityCurve) {
    const d = new Date(point.date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    if (!byMonth[key]) byMonth[key] = { first: point.equity, last: point.equity };
    byMonth[key].last = point.equity;
  }

  return Object.entries(byMonth)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, { first, last }]) => {
      const [y, m] = key.split("-").map(Number);
      return {
        year: y,
        month: m,
        return_pct: first > 0 ? ((last - first) / first) * 100 : 0,
      };
    });
}

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function MonthlyHeatmap({
  equityCurve,
}: {
  equityCurve: { date: string; equity: number }[];
}) {
  const monthly = buildMonthlyReturns(equityCurve);
  if (monthly.length === 0) return null;

  // Group by year
  const years = [...new Set(monthly.map((m) => m.year))].sort();
  const byYear: Record<number, Record<number, number>> = {};
  for (const y of years) byYear[y] = {};
  for (const m of monthly) byYear[m.year][m.month] = m.return_pct;

  const maxAbs = Math.max(
    ...monthly.map((m) => Math.abs(m.return_pct)),
    1,
  );

  function cellColor(ret: number | undefined): string {
    if (ret === undefined) return "bg-slate-800/40";
    const intensity = Math.min(Math.abs(ret) / maxAbs, 1);
    if (ret > 0.5) return `bg-emerald-${intensity > 0.6 ? "600" : intensity > 0.3 ? "800" : "900"}/60`;
    if (ret < -0.5) return `bg-rose-${intensity > 0.6 ? "600" : intensity > 0.3 ? "800" : "900"}/60`;
    return "bg-slate-700/40";
  }

  function textColor(ret: number | undefined): string {
    if (ret === undefined) return "text-slate-700";
    if (ret > 0.5) return "text-emerald-300";
    if (ret < -0.5) return "text-rose-300";
    return "text-slate-400";
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-200">
          Monthly Returns Heatmap
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Green = positive month · Red = negative · Intensity = magnitude
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs border-separate border-spacing-0.5">
          <thead>
            <tr>
              <th className="text-left text-slate-500 font-medium pb-1 w-12">Year</th>
              {MONTH_LABELS.map((m) => (
                <th key={m} className="text-slate-500 font-medium pb-1 text-center w-10">{m}</th>
              ))}
              <th className="text-slate-500 font-medium pb-1 text-right">Ann.</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const monthData = byYear[year];
              const yearMonths = Object.values(monthData);
              // Approximate annual return by compounding monthly returns
              const annualRet = yearMonths.reduce(
                (acc, m) => acc * (1 + m / 100),
                1,
              ) - 1;

              return (
                <tr key={year}>
                  <td className="text-slate-400 font-mono pr-2">{year}</td>
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                    const ret = monthData[month];
                    return (
                      <td key={month} className="p-0">
                        <div
                          className={`rounded px-1 py-1.5 text-center tabular-nums ${cellColor(ret)} ${textColor(ret)}`}
                          title={ret !== undefined ? `${ret >= 0 ? "+" : ""}${ret.toFixed(1)}%` : "No data"}
                        >
                          {ret !== undefined
                            ? `${ret >= 0 ? "+" : ""}${ret.toFixed(0)}%`
                            : ""}
                        </div>
                      </td>
                    );
                  })}
                  <td
                    className={`text-right font-mono tabular-nums pl-2 font-semibold ${annualRet >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}
                  >
                    {annualRet >= 0 ? "+" : ""}
                    {(annualRet * 100).toFixed(1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Drawdown Chart (todos-v3.md UX-BACKTEST-03) ─────────────────────────────

function buildDrawdownSeries(
  equityCurve: { date: string; equity: number }[],
): { date: string; drawdown_pct: number }[] {
  if (equityCurve.length === 0) return [];
  let peak = equityCurve[0].equity;
  return equityCurve.map((point) => {
    if (point.equity > peak) peak = point.equity;
    const dd = peak > 0 ? ((point.equity - peak) / peak) * 100 : 0;
    return { date: point.date, drawdown_pct: dd };
  });
}

function DrawdownChart({
  equityCurve,
  maxDrawdownPct,
}: {
  equityCurve: { date: string; equity: number }[];
  maxDrawdownPct: number;
}) {
  const series = buildDrawdownSeries(equityCurve);
  if (series.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-200">Drawdown</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Peak-to-trough decline from equity highs ·{" "}
          <span className="text-rose-400 font-medium">
            Max drawdown: {maxDrawdownPct.toFixed(2)}%
          </span>
        </p>
      </div>

      <div className="h-[180px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={series}
            margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
          >
            <defs>
              <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="date"
              stroke="#475569"
              fontSize={11}
              tickFormatter={(v) =>
                new Date(v).toLocaleDateString(undefined, {
                  month: "short",
                  year: "2-digit",
                })
              }
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="#475569"
              fontSize={11}
              tickFormatter={(v) => `${v.toFixed(0)}%`}
              domain={["auto", 0]}
              width={44}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: "0.5rem",
                color: "#f8fafc",
                fontSize: 12,
              }}
              labelFormatter={(l) =>
                new Date(l).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })
              }
              formatter={(value: number) => [
                `${value.toFixed(2)}%`,
                "Drawdown",
              ]}
            />
            <Area
              type="monotone"
              dataKey="drawdown_pct"
              stroke="#f87171"
              strokeWidth={1.5}
              fill="url(#ddGradient)"
              dot={false}
              activeDot={{ r: 3, fill: "#f87171" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Strategy Library Panel ───────────────────────────────────────────────────

function StrategyCard({
  s,
  onLoad,
  onDelete,
  onTogglePublic,
  showActions,
}: {
  s: StrategyDto;
  onLoad: (s: StrategyDto) => void;
  onDelete: (id: number) => void;
  onTogglePublic: (s: StrategyDto) => void;
  showActions: boolean;
}) {
  const sharpeColor =
    s.sharpe_ratio == null
      ? "text-slate-400"
      : s.sharpe_ratio >= 1
        ? "text-emerald-400"
        : s.sharpe_ratio >= 0.5
          ? "text-amber-400"
          : "text-rose-400";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-slate-100 text-sm">{s.name}</span>
          <span className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
            {s.symbol}
          </span>
          {s.is_public ? (
            <span className="text-xs flex items-center gap-1 text-sky-400">
              <Globe className="h-3 w-3" />
              Public
            </span>
          ) : (
            <span className="text-xs flex items-center gap-1 text-slate-500">
              <Lock className="h-3 w-3" />
              Private
            </span>
          )}
        </div>
        <div className="mt-1.5 flex items-center gap-4 text-xs text-slate-500 flex-wrap">
          {s.sharpe_ratio != null && (
            <span>
              Sharpe{" "}
              <span className={`font-mono font-semibold ${sharpeColor}`}>
                {s.sharpe_ratio.toFixed(2)}
              </span>
            </span>
          )}
          {s.total_return_pct != null && (
            <span>
              Return{" "}
              <span
                className={`font-mono font-semibold ${s.total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}
              >
                {s.total_return_pct >= 0 ? "+" : ""}
                {s.total_return_pct.toFixed(1)}%
              </span>
            </span>
          )}
          {s.max_drawdown_pct != null && (
            <span>
              DD{" "}
              <span className="font-mono text-rose-400">
                {s.max_drawdown_pct.toFixed(1)}%
              </span>
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={() => onLoad(s)}
          className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-3 py-1.5 rounded transition"
        >
          Load
        </button>
        {showActions && s.is_mine && (
          <>
            <button
              onClick={() => onTogglePublic(s)}
              title={s.is_public ? "Make private" : "Make public"}
              className="p-1.5 text-slate-500 hover:text-sky-400 transition"
            >
              {s.is_public ? (
                <Lock className="h-4 w-4" />
              ) : (
                <Globe className="h-4 w-4" />
              )}
            </button>
            <button
              onClick={() => onDelete(s.id)}
              className="p-1.5 text-slate-500 hover:text-rose-400 transition"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Strategy Description Cards (Sprint 12) ────────────────────────────────────

const STRATEGY_DOCS: Record<string, {
  title: string;
  tagline: string;
  howItWorks: string;
  entryRule: string;
  exitRule: string;
  bestFor: string;
  watchOut: string;
  params: { name: string; default: string; meaning: string }[];
}> = {
  momentum: {
    title: "Momentum (SMA Crossover + RSI Filter)",
    tagline: "Ride trending markets by following moving average crossovers.",
    howItWorks:
      "Two Simple Moving Averages (a fast and a slow one) are computed on the closing price. When the fast SMA rises above the slow SMA, the market is considered to be in an uptrend — the strategy enters a long position. An RSI filter prevents buying into already-overbought conditions.",
    entryRule: "Fast SMA > Slow SMA AND RSI > threshold",
    exitRule: "Either condition fails (fast SMA drops below slow SMA, or RSI falls below threshold)",
    bestFor: "Strong, sustained directional trends (bull markets, growth stocks).",
    watchOut:
      "Whipsaws in sideways markets — the SMA crossover generates many false signals when price oscillates without trend. Lagging by nature: you will always enter after the move has started.",
    params: [
      { name: "SMA Fast",           default: "10",  meaning: "Short-term trend lookback. Smaller = more reactive, more signals." },
      { name: "SMA Slow",           default: "50",  meaning: "Long-term trend anchor. Larger = smoother, fewer signals." },
      { name: "RSI Period",         default: "14",  meaning: "RSI momentum lookback in days." },
      { name: "RSI Threshold",      default: "40",  meaning: "Minimum RSI to allow entry — filters near-oversold conditions." },
    ],
  },
  mean_reversion: {
    title: "Mean Reversion (Bollinger Band + RSI)",
    tagline: "Buy oversold dips expecting price to snap back to the mean.",
    howItWorks:
      "Bollinger Bands define a statistical price envelope (mean ± N standard deviations). When price touches or breaks below the lower band AND the RSI is also oversold, the model assumes the move is exhausted and bets on a snap-back to the middle band. Each trade is time-limited to prevent being stuck in a prolonged downtrend.",
    entryRule: "Close ≤ Lower Bollinger Band AND RSI ≤ oversold threshold",
    exitRule: "Close returns to middle band OR RSI ≥ upper threshold OR max hold days reached",
    bestFor: "Range-bound, mean-reverting assets with moderate volatility. Works well during consolidation phases.",
    watchOut:
      "Catastrophic in trending bear markets — you repeatedly buy dips that keep falling. Always check the GAS Regime indicator before using this strategy; avoid it in Risk-Off regimes.",
    params: [
      { name: "BB Period",          default: "20",  meaning: "Bollinger Band rolling window (standard = 20 days)." },
      { name: "RSI Period",         default: "14",  meaning: "RSI lookback for oversold detection." },
      { name: "RSI Oversold Entry", default: "30",  meaning: "Entry threshold — lower means more extreme oversold required." },
      { name: "Hold Days",          default: "5",   meaning: "Maximum days to stay in a trade before forced exit." },
    ],
  },
  macro_responsive: {
    title: "Macro-Responsive (Volatility-Targeted)",
    tagline: "Scale position size by inverse volatility — hold less when markets are stressed.",
    howItWorks:
      "Rather than a binary in/out signal, this strategy continuously adjusts position size based on the asset's recent realised volatility relative to a target annual volatility level. When markets are calm (low vol), sizing is increased up to 100%. When volatility spikes, position shrinks proportionally. A trend filter (price above a long SMA) prevents trading into confirmed downtrends.",
    entryRule: "Price > Trend SMA (uptrend confirmed) → position size = vol_target / realised_vol (capped at 100%)",
    exitRule: "Price drops below Trend SMA → position goes to 0%",
    bestFor: "Risk-managed exposure to trending assets. Approximates a 'macro-aware' positioning strategy that shrinks during stressed regimes.",
    watchOut:
      "Realised volatility is a backward-looking proxy — vol can spike faster than position reduces. Fractional sizing means returns are more muted than a full-size momentum strategy in bull markets.",
    params: [
      { name: "Vol Period",         default: "20",  meaning: "Lookback for computing realised volatility." },
      { name: "Trend MA Period",    default: "50",  meaning: "Only trade above this SMA — trend filter." },
      { name: "Vol Target (%)",     default: "15",  meaning: "Annualised volatility target (e.g. 15 = 15% p.a.). Higher = more aggressive sizing." },
    ],
  },
};

function StrategyDocPanel({ strategy }: { strategy: string }) {
  const [open, setOpen] = useState(false);
  const doc = STRATEGY_DOCS[strategy];
  if (!doc) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <BookOpen className="h-4 w-4 text-violet-400 flex-shrink-0" />
          <span className="text-sm font-semibold text-slate-200">How this strategy works</span>
        </div>
        {open
          ? <ChevronUp className="h-4 w-4 text-slate-500 flex-shrink-0" />
          : <ChevronDown className="h-4 w-4 text-slate-500 flex-shrink-0" />}
      </button>

      {open && (
        <div className="border-t border-slate-800 px-4 pb-4 pt-3 space-y-4 text-xs leading-relaxed">
          {/* Title + tagline */}
          <div>
            <p className="text-sm font-bold text-slate-100">{doc.title}</p>
            <p className="text-slate-400 mt-0.5 italic">{doc.tagline}</p>
          </div>

          {/* How it works */}
          <div className="space-y-1">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">How it works</p>
            <p className="text-slate-300">{doc.howItWorks}</p>
          </div>

          {/* Entry / Exit */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-lg bg-emerald-950/30 border border-emerald-900/40 px-3 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-500 mb-1">Entry Rule</p>
              <p className="text-emerald-300 font-mono text-[11px]">{doc.entryRule}</p>
            </div>
            <div className="rounded-lg bg-rose-950/30 border border-rose-900/40 px-3 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-rose-500 mb-1">Exit Rule</p>
              <p className="text-rose-300 font-mono text-[11px]">{doc.exitRule}</p>
            </div>
          </div>

          {/* Best for / Watch out */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-lg bg-sky-950/20 border border-sky-900/30 px-3 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-sky-500 mb-1">✓ Best for</p>
              <p className="text-slate-300">{doc.bestFor}</p>
            </div>
            <div className="rounded-lg bg-amber-950/20 border border-amber-900/30 px-3 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-500 mb-1">⚠ Watch out for</p>
              <p className="text-slate-300">{doc.watchOut}</p>
            </div>
          </div>

          {/* Parameter table */}
          <div className="space-y-1">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Parameters</p>
            <div className="rounded-lg border border-slate-800 overflow-hidden">
              <table className="w-full text-[11px]">
                <thead className="bg-slate-800/60">
                  <tr>
                    <th className="px-3 py-1.5 text-left text-slate-400 font-medium">Parameter</th>
                    <th className="px-3 py-1.5 text-center text-slate-400 font-medium">Default</th>
                    <th className="px-3 py-1.5 text-left text-slate-400 font-medium">Meaning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {doc.params.map((p) => (
                    <tr key={p.name}>
                      <td className="px-3 py-1.5 font-mono text-sky-300 whitespace-nowrap">{p.name}</td>
                      <td className="px-3 py-1.5 text-center font-mono text-slate-300">{p.default}</td>
                      <td className="px-3 py-1.5 text-slate-400">{p.meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Parameter Sweep Panel (Sprint 14 UX-BACKTEST-04) ─────────────────────────────

// ─── Walk-Forward Validation Panel (Sprint 18) ─────────────────────────────────────

function WalkForwardPanel({
  symbol,
  strategy,
  baseParams,
  initialCapital,
}: {
  symbol: string;
  strategy: string;
  baseParams: Record<string, number>;
  initialCapital: number;
}) {
  const [open, setOpen]         = useState(false);
  const [nSplits, setNSplits]   = useState(5);
  const [running, setRunning]   = useState(false);
  const [wfResult, setWfResult] = useState<WalkForwardResponse | null>(null);
  const [wfError, setWfError]   = useState<string | null>(null);

  const runWF = useCallback(async () => {
    setRunning(true);
    setWfError(null);
    setWfResult(null);
    try {
      const res = await runWalkForward({
        symbol: symbol.trim().toUpperCase(),
        strategy,
        parameters: baseParams,
        initial_capital: initialCapital,
        n_splits: nSplits,
      });
      setWfResult(res);
    } catch (e: unknown) {
      setWfError(e instanceof Error ? e.message : "Walk-forward failed");
    } finally {
      setRunning(false);
    }
  }, [symbol, strategy, baseParams, initialCapital, nSplits]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <Activity className="h-4 w-4 text-teal-400" />
          Walk-Forward Validation
          <span className="text-xs font-normal text-slate-500 ml-1">Out-of-sample reality check</span>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
      </button>

      {open && (
        <div className="border-t border-slate-800 px-5 pb-5 pt-4 space-y-4">
          <p className="text-xs text-slate-500 leading-relaxed">
            Splits the full 10-year history into N anchored IS/OOS windows. Each fold uses everything
            before the test window as in-sample training. The stitched out-of-sample equity curve
            is the closest thing to a true live-trading simulation. High Sharpe degradation (IS−OOS) signals overfitting.
          </p>

          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Number of folds</p>
              <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                {[3, 4, 5, 6, 8].map(n => (
                  <button
                    key={n}
                    onClick={() => { setNSplits(n); setWfResult(null); }}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      nSplits === n ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={runWF}
              disabled={running}
              className="flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
            >
              {running
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</>
                : <><Activity className="h-4 w-4" /> Run Walk-Forward</>}
            </button>
          </div>

          {running && (
            <p className="text-xs text-slate-400 flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-400" />
              Running {nSplits} IS/OOS folds on 10 years of data… this may take 15–30s.
            </p>
          )}
          {wfError && <p className="text-xs text-rose-400">{wfError}</p>}

          {wfResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "OOS Total Return", value: `${wfResult.oos_total_return_pct >= 0 ? "+" : ""}${wfResult.oos_total_return_pct.toFixed(1)}%`, color: wfResult.oos_total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400" },
                  { label: "Avg OOS Sharpe",   value: wfResult.oos_avg_sharpe.toFixed(2), color: wfResult.oos_avg_sharpe >= 0.5 ? "text-emerald-400" : wfResult.oos_avg_sharpe >= 0.2 ? "text-amber-400" : "text-rose-400" },
                  { label: "Sharpe Degradation", value: wfResult.avg_sharpe_degradation.toFixed(2), color: wfResult.avg_sharpe_degradation < 0.2 ? "text-emerald-400" : wfResult.avg_sharpe_degradation < 0.5 ? "text-amber-400" : "text-rose-400" },
                  { label: "Worst OOS DD",     value: `${wfResult.oos_max_drawdown_pct.toFixed(1)}%`, color: "text-rose-400" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-[10px] text-slate-500">{label}</p>
                    <p className={`text-xl font-bold mt-0.5 ${color}`}>{value}</p>
                  </div>
                ))}
              </div>

              {wfResult.overfitting_warning && (
                <div className="flex items-start gap-3 rounded-xl border border-rose-700/40 bg-rose-950/20 px-4 py-3">
                  <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                  <div className="text-xs">
                    <p className="font-semibold text-rose-300">Overfitting signal detected</p>
                    <p className="text-slate-400 mt-0.5">
                      {wfResult.avg_sharpe_degradation > 0.4
                        ? `IS→OOS Sharpe drops by ${wfResult.avg_sharpe_degradation.toFixed(2)} on average — strategy is likely curve-fitted.`
                        : `OOS Sharpe of ${wfResult.oos_avg_sharpe.toFixed(2)} is too low to be reliable in live trading.`}
                    </p>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
                <p className="text-xs font-semibold text-slate-300">IS vs OOS Sharpe per fold</p>
                <p className="text-[10px] text-slate-600">Blue = in-sample. Teal = out-of-sample. Similar heights = strategy generalises well.</p>
                <div className="space-y-2">
                  {wfResult.folds.map(fold => {
                    const maxS = Math.max(...wfResult.folds.flatMap(f => [f.in_sample_stats.sharpe_ratio, f.out_of_sample_stats.sharpe_ratio]), 0.01);
                    const isW  = Math.max(0, (fold.in_sample_stats.sharpe_ratio / maxS) * 100);
                    const oosW = Math.max(0, (fold.out_of_sample_stats.sharpe_ratio / maxS) * 100);
                    const degraded = (fold.in_sample_stats.sharpe_ratio - fold.out_of_sample_stats.sharpe_ratio) > 0.5;
                    return (
                      <div key={fold.fold} className="space-y-0.5">
                        <div className="flex justify-between text-[10px] text-slate-500">
                          <span>Fold {fold.fold} · OOS: {fold.test_start} → {fold.test_end}</span>
                          <span className={degraded ? "text-rose-400" : "text-slate-400"}>
                            IS {fold.in_sample_stats.sharpe_ratio.toFixed(2)} → OOS {fold.out_of_sample_stats.sharpe_ratio.toFixed(2)}{degraded && " ⚠"}
                          </span>
                        </div>
                        <div className="flex gap-0.5 h-4">
                          <div className="rounded-sm bg-blue-500/70" style={{ width: `${isW}%`, minWidth: 2 }} />
                          <div className={`rounded-sm ${oosW < isW * 0.5 ? "bg-rose-400/70" : "bg-teal-400/70"}`} style={{ width: `${oosW}%`, minWidth: oosW > 0 ? 2 : 0 }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-4 text-[10px] text-slate-500 pt-1">
                  <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 rounded-sm bg-blue-500/70" /> In-sample</span>
                  <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 rounded-sm bg-teal-400/70" /> Out-of-sample</span>
                  <span className="flex items-center gap-1"><span className="inline-block w-3 h-2 rounded-sm bg-rose-400/70" /> OOS &lt; 50% IS</span>
                </div>
              </div>

              {wfResult.combined_oos_equity.length > 1 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
                  <p className="text-xs font-semibold text-slate-300">Stitched OOS Equity Curve</p>
                  <p className="text-[10px] text-slate-500">Compounded out-of-sample equity across all folds — the closest approximation to live trading.</p>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={wfResult.combined_oos_equity} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="date" stroke="#475569" fontSize={10}
                          tickFormatter={v => new Date(v).toLocaleDateString(undefined, { month: "short", year: "2-digit" })}
                          interval="preserveStartEnd" />
                        <YAxis stroke="#475569" fontSize={10} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} width={44} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", fontSize: 12 }}
                          formatter={(v: number) => [`${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, "OOS Equity"]}
                          labelFormatter={l => new Date(l).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                        />
                        <Line type="monotone" dataKey="equity" stroke="#2dd4bf" strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SweepPoint {
  paramValue: number;
  sharpe: number;
  totalReturn: number;
  maxDrawdown: number;
  trades: number;
}

const SWEEP_PARAMS_BY_STRATEGY: Record<string, { key: string; label: string; min: number; max: number; step: number }[]> = {
  momentum: [
    { key: "sma_fast",      label: "SMA Fast",        min: 5,  max: 50,  step: 5  },
    { key: "sma_slow",      label: "SMA Slow",        min: 20, max: 200, step: 10 },
    { key: "rsi_threshold", label: "RSI Threshold",   min: 20, max: 60,  step: 5  },
  ],
  mean_reversion: [
    { key: "sma_fast",      label: "BB Period",       min: 10, max: 40,  step: 5  },
    { key: "rsi_threshold", label: "RSI Oversold",    min: 20, max: 40,  step: 2  },
    { key: "rsi_period",    label: "RSI Period",      min: 7,  max: 21,  step: 2  },
  ],
  macro_responsive: [
    { key: "sma_fast",      label: "Vol Period",      min: 5,  max: 40,  step: 5  },
    { key: "sma_slow",      label: "Trend MA",        min: 20, max: 100, step: 10 },
    { key: "rsi_threshold", label: "Vol Target (%)",  min: 5,  max: 30,  step: 5  },
  ],
};

function ParameterSweepPanel({
  symbol,
  strategy,
  baseParams,
  initialCapital,
  startDate,
  endDate,
}: {
  symbol: string;
  strategy: string;
  baseParams: Record<string, number>;
  initialCapital: number;
  startDate?: string;
  endDate?: string;
}) {
  const [open, setOpen] = useState(false);
  const [selectedParam, setSelectedParam] = useState(0);
  const [metric, setMetric] = useState<"sharpe" | "totalReturn" | "maxDrawdown">("sharpe");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<SweepPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  const params = SWEEP_PARAMS_BY_STRATEGY[strategy] ?? [];
  const param  = params[selectedParam];

  const runSweep = useCallback(async () => {
    if (!param) return;
    setRunning(true);
    setError(null);
    setResults([]);

    const values: number[] = [];
    for (let v = param.min; v <= param.max; v += param.step) values.push(v);

    const points: SweepPoint[] = [];
    for (const val of values) {
      try {
        const req: BacktestRequest = {
          symbol: symbol.trim().toUpperCase(),
          strategy,
          initial_capital: initialCapital,
          start_date: startDate || undefined,
          end_date:   endDate   || undefined,
          parameters: { ...baseParams, [param.key]: val },
        };
        const res = await runBacktest(req);
        points.push({
          paramValue:  val,
          sharpe:      res.stats.sharpe_ratio,
          totalReturn: res.stats.total_return_pct,
          maxDrawdown: Math.abs(res.stats.max_drawdown_pct),
          trades:      res.stats.total_trades,
        });
      } catch {
        points.push({ paramValue: val, sharpe: 0, totalReturn: 0, maxDrawdown: 0, trades: 0 });
      }
    }
    setResults(points);
    setRunning(false);
  }, [param, symbol, strategy, initialCapital, startDate, endDate, baseParams]);

  if (!params.length) return null;

  const bestPoint = results.length > 0
    ? [...results].sort((a, b) => {
        if (metric === "sharpe")      return b.sharpe - a.sharpe;
        if (metric === "totalReturn") return b.totalReturn - a.totalReturn;
        return a.maxDrawdown - b.maxDrawdown;  // lower is better
      })[0]
    : null;

  const METRIC_CONFIG = {
    sharpe:      { label: "Sharpe Ratio",  color: "#3b82f6", fmt: (v: number) => v.toFixed(2) },
    totalReturn: { label: "Total Return %", color: "#10b981", fmt: (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` },
    maxDrawdown: { label: "Max Drawdown %", color: "#f87171", fmt: (v: number) => `${v.toFixed(1)}%` },
  };
  const mc = METRIC_CONFIG[metric];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <SlidersHorizontal className="h-4 w-4 text-violet-400" />
          Parameter Sweep
          <span className="text-xs font-normal text-slate-500 ml-1">Find optimal parameter values</span>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
      </button>

      {open && (
        <div className="border-t border-slate-800 px-5 pb-5 pt-4 space-y-4">
          <p className="text-xs text-slate-500">
            Runs the backtest across a range of values for one parameter, holding all others constant.
            Helps identify which value maximises your chosen metric. ⚠ In-sample only — results will overfit.
          </p>

          {/* Controls row */}
          <div className="flex flex-wrap gap-3 items-end">
            {/* Parameter selector */}
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Sweep parameter</p>
              <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                {params.map((p, i) => (
                  <button
                    key={p.key}
                    onClick={() => { setSelectedParam(i); setResults([]); }}
                    className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      selectedParam === i ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Metric selector */}
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Optimise for</p>
              <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                {(["sharpe", "totalReturn", "maxDrawdown"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMetric(m)}
                    className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      metric === m ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {METRIC_CONFIG[m].label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={runSweep}
              disabled={running}
              className="flex items-center gap-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
            >
              {running ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</> : <><SlidersHorizontal className="h-4 w-4" /> Run Sweep</>}
            </button>
          </div>

          {/* Range info */}
          {param && (
            <p className="text-[10px] text-slate-600">
              Testing {param.label}: {param.min} → {param.max} (step {param.step}) — {Math.floor((param.max - param.min) / param.step) + 1} backtests
            </p>
          )}

          {error && <p className="text-xs text-rose-400">{error}</p>}

          {/* Progress during run */}
          {running && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
              Running {Math.floor((param?.max ?? 0 - param?.min ?? 0) / (param?.step ?? 1)) + 1} backtests…
            </div>
          )}

          {/* Results chart */}
          {results.length > 0 && (
            <div className="space-y-3">
              {/* Best value callout */}
              {bestPoint && (
                <div className="flex items-center gap-3 rounded-xl border border-violet-800/40 bg-violet-950/20 px-4 py-2.5">
                  <SlidersHorizontal className="h-4 w-4 text-violet-400 flex-shrink-0" />
                  <div className="text-xs">
                    <span className="text-slate-400">Best {mc.label}: </span>
                    <span className="font-bold text-violet-300">{param?.label} = {bestPoint.paramValue}</span>
                    <span className="ml-2 text-slate-500">({mc.fmt(bestPoint[metric])})</span>
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                <p className="text-xs font-semibold text-slate-300 mb-1">{mc.label} vs {param?.label}</p>
                <p className="text-[10px] text-slate-600 mb-3">Each bar = one full backtest. Taller bar = better {mc.label}.</p>
                <div className="h-48">
                  <RechartContainer width="100%" height="100%">
                    <BarChart data={results} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                      <RechartGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <RechartXAxis
                        dataKey="paramValue"
                        stroke="#475569" fontSize={11}
                        tickFormatter={(v) => String(v)}
                      />
                      <RechartYAxis
                        stroke="#475569" fontSize={11}
                        tickFormatter={(v) => mc.fmt(v)}
                        width={52}
                      />
                      <RechartTooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", fontSize: 12 }}
                        formatter={(v: number) => [mc.fmt(v), mc.label]}
                        labelFormatter={(l) => `${param?.label} = ${l}`}
                      />
                      {metric === "sharpe" && <ReferenceLine y={1.0} stroke="#f59e0b" strokeDasharray="4 2" strokeWidth={1} />}
                      {metric === "sharpe" && <ReferenceLine y={1.2} stroke="#ef4444" strokeDasharray="4 2" strokeWidth={1} />}
                      <Bar dataKey={metric} radius={[3, 3, 0, 0]} maxBarSize={40}>
                        {results.map((r, i) => {
                          const isBest = r.paramValue === bestPoint?.paramValue;
                          return (
                            <Cell
                              key={i}
                              fill={isBest ? "#a78bfa" : mc.color}
                              fillOpacity={isBest ? 1 : 0.65}
                            />
                          );
                        })}
                      </Bar>
                    </BarChart>
                  </RechartContainer>
                </div>
                {metric === "sharpe" && (
                  <p className="text-[10px] text-slate-600 mt-2">
                    <span className="text-amber-400">——</span> Sharpe 1.0 (good) &nbsp;
                    <span className="text-rose-400">——</span> Sharpe 1.2 (overfit risk)
                  </p>
                )}
              </div>

              {/* Results table */}
              <div className="rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900/60">
                    <tr className="border-b border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      <th className="px-3 py-2 text-left">{param?.label}</th>
                      <th className="px-3 py-2 text-right">Sharpe</th>
                      <th className="px-3 py-2 text-right">Return</th>
                      <th className="px-3 py-2 text-right">Max DD</th>
                      <th className="px-3 py-2 text-right">Trades</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {results.map((r) => {
                      const isBest = r.paramValue === bestPoint?.paramValue;
                      return (
                        <tr key={r.paramValue} className={`hover:bg-slate-800/20 transition-colors ${
                          isBest ? "bg-violet-950/20 border-l-2 border-violet-500" : ""
                        }`}>
                          <td className={`px-3 py-2 font-mono font-bold ${isBest ? "text-violet-300" : "text-slate-200"}`}>
                            {r.paramValue}
                            {isBest && <span className="ml-1.5 text-[9px] text-violet-400">★ best</span>}
                          </td>
                          <td className={`px-3 py-2 text-right font-mono ${
                            r.sharpe >= 1 ? "text-emerald-400" : r.sharpe >= 0.5 ? "text-amber-400" : "text-rose-400"
                          }`}>{r.sharpe.toFixed(2)}</td>
                          <td className={`px-3 py-2 text-right font-mono ${
                            r.totalReturn >= 0 ? "text-emerald-400" : "text-rose-400"
                          }`}>{r.totalReturn >= 0 ? "+" : ""}{r.totalReturn.toFixed(1)}%</td>
                          <td className="px-3 py-2 text-right font-mono text-rose-400">{r.maxDrawdown.toFixed(1)}%</td>
                          <td className="px-3 py-2 text-right font-mono text-slate-400">{r.trades}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Walk-Forward Validation Panel (Sprint 18) ──────────────────────────────

function WalkForwardPanel({
  symbol,
  strategy,
  baseParams,
  initialCapital,
}: {
  symbol: string;
  strategy: string;
  baseParams: Record<string, number>;
  initialCapital: number;
}) {
  const [open, setOpen]       = useState(false);
  const [nSplits, setNSplits] = useState(5);
  const [running, setRunning] = useState(false);
  const [result, setResult]   = useState<WalkForwardResponse | null>(null);
  const [error, setError]     = useState<string | null>(null);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runWalkForward({
        symbol: symbol.trim().toUpperCase(),
        strategy,
        parameters: baseParams,
        initial_capital: initialCapital,
        n_splits: nSplits,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Walk-forward failed");
    } finally {
      setRunning(false);
    }
  }, [symbol, strategy, baseParams, initialCapital, nSplits]);

  const degradationColor = (d: number) =>
    d > 0.8 ? "text-rose-400" : d > 0.4 ? "text-amber-400" : "text-emerald-400";
  const sharpeColor = (s: number) =>
    s >= 0.8 ? "text-emerald-400" : s >= 0.3 ? "text-amber-400" : "text-rose-400";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <Activity className="h-4 w-4 text-teal-400" />
          Walk-Forward Validation
          <span className="text-xs font-normal text-slate-500 ml-1">Out-of-sample reality check</span>
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
      </button>

      {open && (
        <div className="border-t border-slate-800 px-5 pb-5 pt-4 space-y-4">
          <p className="text-xs text-slate-500 leading-relaxed">
            Anchored walk-forward splits the full price history into <strong className="text-slate-400">N folds</strong>.
            Each fold trains on all prior data (in-sample) and tests on the next period (out-of-sample).
            A large gap between IS and OOS Sharpe signals curve-fitting.
          </p>

          {/* Controls */}
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Number of folds</p>
              <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-0.5">
                {[3, 4, 5, 6, 8].map(n => (
                  <button
                    key={n}
                    onClick={() => { setNSplits(n); setResult(null); }}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      nSplits === n ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 text-sm font-semibold text-white transition-colors"
            >
              {running ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</> : <><Activity className="h-4 w-4" /> Run Walk-Forward</>}
            </button>
          </div>

          {error && <p className="text-xs text-rose-400">{error}</p>}

          {result && (
            <div className="space-y-4">
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "OOS Total Return",  value: `${result.oos_total_return_pct >= 0 ? "+" : ""}${result.oos_total_return_pct.toFixed(1)}%`, color: result.oos_total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400" },
                  { label: "OOS Avg Sharpe",    value: result.oos_avg_sharpe.toFixed(2),   color: sharpeColor(result.oos_avg_sharpe) },
                  { label: "OOS Max Drawdown",  value: `${result.oos_max_drawdown_pct.toFixed(1)}%`, color: "text-rose-400" },
                  { label: "OOS Win Rate",      value: `${result.oos_avg_win_rate.toFixed(1)}%`, color: result.oos_avg_win_rate >= 50 ? "text-emerald-400" : "text-slate-300" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                    <p className={`text-xl font-bold mt-0.5 ${color}`}>{value}</p>
                  </div>
                ))}
              </div>

              {/* Overfitting / degradation banner */}
              <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
                result.overfitting_warning
                  ? "border-rose-800/50 bg-rose-950/20"
                  : "border-emerald-800/30 bg-emerald-950/10"
              }`}>
                <AlertTriangle className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                  result.overfitting_warning ? "text-rose-400" : "text-emerald-400"
                }`} />
                <div className="text-xs space-y-0.5">
                  <p className={`font-semibold ${
                    result.overfitting_warning ? "text-rose-300" : "text-emerald-300"
                  }`}>
                    {result.overfitting_warning
                      ? "⚠ Overfitting signal detected"
                      : "✓ Strategy shows reasonable OOS robustness"}
                  </p>
                  <p className="text-slate-400">
                    Avg IS→OOS Sharpe degradation:{" "}
                    <span className={`font-bold font-mono ${degradationColor(result.avg_sharpe_degradation)}`}>
                      {result.avg_sharpe_degradation >= 0 ? "+" : ""}{result.avg_sharpe_degradation.toFixed(2)}
                    </span>
                    {" "}&nbsp;(threshold: &gt;0.4 = concern, &gt;0.8 = high risk)
                  </p>
                </div>
              </div>

              {/* OOS equity curve */}
              {result.combined_oos_equity.length > 1 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <p className="text-xs font-semibold text-slate-300 mb-0.5">Stitched OOS Equity Curve</p>
                  <p className="text-[10px] text-slate-600 mb-3">All out-of-sample folds chained end-to-end — this is the closest proxy to live trading performance.</p>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={result.combined_oos_equity} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="date" stroke="#475569" fontSize={10}
                          tickFormatter={v => new Date(v).toLocaleDateString(undefined, { month: "short", year: "2-digit" })}
                          interval="preserveStartEnd" />
                        <YAxis stroke="#475569" fontSize={10}
                          tickFormatter={v => `${(v / 1000).toFixed(0)}k`}
                          domain={["auto", "auto"]} width={44} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", fontSize: 11 }}
                          labelFormatter={l => new Date(l).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                          formatter={(v: number) => [`${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, "OOS Equity"]}
                        />
                        <Line type="monotone" dataKey="equity" stroke="#2dd4bf" strokeWidth={2} dot={false} activeDot={{ r: 3, fill: "#2dd4bf" }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Per-fold IS vs OOS Sharpe comparison */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
                <p className="text-xs font-semibold text-slate-300">IS vs OOS Sharpe per Fold</p>
                <p className="text-[10px] text-slate-600">Blue = in-sample (training). Teal = out-of-sample (test). Large gap = possible overfit.</p>
                <div className="space-y-2">
                  {result.folds.map(fold => {
                    const maxSharpe = Math.max(
                      ...result.folds.flatMap(f => [Math.abs(f.in_sample_stats.sharpe_ratio), Math.abs(f.out_of_sample_stats.sharpe_ratio)]),
                      1,
                    );
                    const isBarPct  = Math.min(Math.abs(fold.in_sample_stats.sharpe_ratio)  / maxSharpe * 100, 100);
                    const oosBarPct = Math.min(Math.abs(fold.out_of_sample_stats.sharpe_ratio) / maxSharpe * 100, 100);
                    return (
                      <div key={fold.fold} className="space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-slate-500">
                          <span>Fold {fold.fold} &nbsp;<span className="text-slate-700">{fold.test_start} → {fold.test_end}</span></span>
                          <span>
                            IS {fold.in_sample_stats.sharpe_ratio.toFixed(2)}{" "}
                            <span className="text-slate-700">vs</span>{" "}
                            <span className={sharpeColor(fold.out_of_sample_stats.sharpe_ratio)}>
                              OOS {fold.out_of_sample_stats.sharpe_ratio.toFixed(2)}
                            </span>
                          </span>
                        </div>
                        <div className="space-y-0.5">
                          <div className="h-2 bg-slate-800 rounded overflow-hidden">
                            <div className="h-full bg-blue-500 rounded" style={{ width: `${isBarPct}%` }} />
                          </div>
                          <div className="h-2 bg-slate-800 rounded overflow-hidden">
                            <div className={`h-full rounded ${
                              fold.out_of_sample_stats.sharpe_ratio >= 0.5 ? "bg-teal-500" :
                              fold.out_of_sample_stats.sharpe_ratio >= 0 ? "bg-amber-500" : "bg-rose-500"
                            }`} style={{ width: `${oosBarPct}%` }} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-4 text-[10px] text-slate-600 pt-1">
                  <span><span className="inline-block w-2 h-2 rounded-sm bg-blue-500 mr-1" />In-sample</span>
                  <span><span className="inline-block w-2 h-2 rounded-sm bg-teal-500 mr-1" />Out-of-sample</span>
                </div>
              </div>

              {/* Fold details table */}
              <div className="rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-900/60">
                    <tr className="border-b border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      <th className="px-3 py-2 text-left">Fold</th>
                      <th className="px-3 py-2 text-left">OOS Window</th>
                      <th className="px-3 py-2 text-right">IS Sharpe</th>
                      <th className="px-3 py-2 text-right">OOS Sharpe</th>
                      <th className="px-3 py-2 text-right">OOS Return</th>
                      <th className="px-3 py-2 text-right">OOS DD</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {result.folds.map(fold => (
                      <tr key={fold.fold} className="hover:bg-slate-800/20">
                        <td className="px-3 py-2 font-mono font-bold text-slate-300">{fold.fold}</td>
                        <td className="px-3 py-2 text-slate-500 text-[10px]">
                          {fold.test_start.slice(0, 7)} → {fold.test_end.slice(0, 7)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-slate-400">{fold.in_sample_stats.sharpe_ratio.toFixed(2)}</td>
                        <td className={`px-3 py-2 text-right font-mono font-semibold ${sharpeColor(fold.out_of_sample_stats.sharpe_ratio)}`}>
                          {fold.out_of_sample_stats.sharpe_ratio.toFixed(2)}
                        </td>
                        <td className={`px-3 py-2 text-right font-mono ${
                          fold.out_of_sample_stats.total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"
                        }`}>
                          {fold.out_of_sample_stats.total_return_pct >= 0 ? "+" : ""}{fold.out_of_sample_stats.total_return_pct.toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-rose-400">{fold.out_of_sample_stats.max_drawdown_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Sprint 25: Benchmark Comparison Pill Strip ─────────────────────────────

const BENCHMARK_OPTIONS = [
  { value: "",        label: "Same Symbol" },
  { value: "SPY",     label: "SPY" },
  { value: "QQQ",     label: "QQQ" },
  { value: "BTC-USD", label: "BTC" },
  { value: "GLD",     label: "GLD" },
] as const;

function BenchmarkStrip({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-xs font-medium text-slate-400">
        Benchmark
      </label>
      <div className="flex flex-wrap gap-1 rounded-lg border border-slate-700 bg-slate-950 p-1">
        {BENCHMARK_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`flex-1 min-w-0 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
              value === opt.value
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Sprint 25: Trade Log Table ───────────────────────────────────────────────

const TRADE_LOG_PAGE_SIZE = 10;

function TradeLogTable({ trades }: { trades: TradeRecord[] }) {
  const [page, setPage]     = useState(0);
  const [open, setOpen]     = useState(false);

  if (!trades || trades.length === 0) return null;

  const totalPages = Math.ceil(trades.length / TRADE_LOG_PAGE_SIZE);
  const slice = trades.slice(
    page * TRADE_LOG_PAGE_SIZE,
    (page + 1) * TRADE_LOG_PAGE_SIZE,
  );

  const wins   = trades.filter((t) => t.return_pct > 0).length;
  const losses = trades.filter((t) => t.return_pct < 0).length;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <TrendingUp className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-semibold text-slate-200">Trade Log</span>
          <span className="text-xs text-slate-500">
            {trades.length} trades &middot;
            <span className="text-emerald-400 ml-1">{wins}W</span>
            {" / "}
            <span className="text-rose-400">{losses}L</span>
          </span>
        </div>
        {open
          ? <ChevronUp className="h-4 w-4 text-slate-500" />
          : <ChevronDown className="h-4 w-4 text-slate-500" />}
      </button>

      {open && (
        <div className="border-t border-slate-800">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-900/60">
                <tr className="border-b border-slate-800 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-2 text-left">#</th>
                  <th className="px-4 py-2 text-left">Entry Date</th>
                  <th className="px-4 py-2 text-left">Exit Date</th>
                  <th className="px-4 py-2 text-right">Entry $</th>
                  <th className="px-4 py-2 text-right">Exit $</th>
                  <th className="px-4 py-2 text-right">Return %</th>
                  <th className="px-4 py-2 text-right">Days</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {slice.map((t, i) => {
                  const idx = page * TRADE_LOG_PAGE_SIZE + i + 1;
                  const positive = t.return_pct >= 0;
                  return (
                    <tr
                      key={idx}
                      className="hover:bg-slate-800/20 transition-colors"
                    >
                      <td className="px-4 py-2 text-slate-600 font-mono">{idx}</td>
                      <td className="px-4 py-2 text-slate-400 font-mono">{t.entry_date}</td>
                      <td className="px-4 py-2 text-slate-400 font-mono">{t.exit_date}</td>
                      <td className="px-4 py-2 text-right font-mono text-slate-300">
                        ${t.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-300">
                        ${t.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td
                        className={`px-4 py-2 text-right font-mono font-semibold ${
                          positive ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {positive ? "+" : ""}{t.return_pct.toFixed(2)}%
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-slate-500">
                        {t.holding_days}d
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800">
              <p className="text-[10px] text-slate-600">
                Page {page + 1} of {totalPages} &middot; {trades.length} trades
              </p>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 border border-slate-800 hover:border-slate-700 transition"
                >
                  ←
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 border border-slate-800 hover:border-slate-700 transition"
                >
                  →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BacktestingPage() {
  const { symbol: globalSymbol } = useSymbol();
  const [symbol, setSymbol] = useState(globalSymbol || "TSLA");
  const [strategy, setStrategy] = useState("momentum");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [smaFast, setSmaFast] = useState("10");
  const [smaSlow, setSmaSlow] = useState("50");
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [rsiThreshold, setRsiThreshold] = useState("40");

  const [benchmark, setBenchmark] = useState(""); // Sprint 25

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResponse | null>(null);

  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [savePublic, setSavePublic] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [libTab, setLibTab] = useState<"mine" | "public">("mine");
  const [libOpen, setLibOpen] = useState(true);
  const [myStrategies, setMyStrategies] = useState<StrategyDto[]>([]);
  const [publicStrategies, setPublicStrategies] = useState<StrategyDto[]>([]);
  const [libLoading, setLibLoading] = useState(true);

  const loadLibrary = useCallback(async () => {
    setLibLoading(true);
    try {
      const [mine, pub] = await Promise.all([
        fetchMyStrategies(),
        fetchPublicStrategies(),
      ]);
      setMyStrategies(mine.strategies);
      setPublicStrategies(pub.strategies);
    } catch {
      /* unauthenticated or API down — silently degrade */
    } finally {
      setLibLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    const req: BacktestRequest = {
      symbol: symbol.trim().toUpperCase(),
      strategy: strategy,
      initial_capital: Number(initialCapital),
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      parameters: {
        sma_fast: Number(smaFast),
        sma_slow: Number(smaSlow),
        rsi_period: Number(rsiPeriod),
        rsi_threshold: Number(rsiThreshold),
      },
      benchmark: benchmark || undefined, // Sprint 25
    };
    try {
      const data = await runBacktest(req);
      setResult(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to run backtest",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLoad = (s: StrategyDto) => {
    setSymbol(s.symbol);
    setInitialCapital(String(s.initial_capital));
    setStartDate(s.start_date ?? "");
    setEndDate(s.end_date ?? "");
    setSmaFast(String(s.parameters.sma_fast ?? 10));
    setSmaSlow(String(s.parameters.sma_slow ?? 50));
    setRsiPeriod(String(s.parameters.rsi_period ?? 14));
    setRsiThreshold(String(s.parameters.rsi_threshold ?? 40));
    setResult(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSave = async () => {
    if (!saveName.trim()) return setSaveError("Name is required.");
    setSaving(true);
    setSaveError(null);
    try {
      const st = result?.stats;
      await saveStrategy({
        name: saveName.trim(),
        symbol: symbol.trim().toUpperCase(),
        strategy: "momentum",
        parameters: {
          sma_fast: Number(smaFast),
          sma_slow: Number(smaSlow),
          rsi_period: Number(rsiPeriod),
          rsi_threshold: Number(rsiThreshold),
        },
        initial_capital: Number(initialCapital),
        slippage_pct: 0.001,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        total_return_pct: st?.total_return_pct,
        annualized_return_pct: st?.annualized_return_pct,
        sharpe_ratio: st?.sharpe_ratio,
        max_drawdown_pct: st?.max_drawdown_pct,
        win_rate_pct: st?.win_rate_pct,
        total_trades: st?.total_trades,
        is_public: savePublic,
      });
      setShowSaveModal(false);
      setSaveName("");
      setSavePublic(false);
      await loadLibrary();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteStrategy(id);
    setMyStrategies((prev) => prev.filter((s) => s.id !== id));
  };

  const handleTogglePublic = async (s: StrategyDto) => {
    const updated = await updateStrategy(s.id, { is_public: !s.is_public });
    setMyStrategies((prev) =>
      prev.map((x) => (x.id === s.id ? updated : x)),
    );
  };

  const s = result?.stats;
  const triggered = result?.overfitting_warning ?? false;
  const displayedStrategies =
    libTab === "mine" ? myStrategies : publicStrategies;

  return (
    <div className="space-y-6">
      <PageBanner
        icon={<FlaskConical className="h-5 w-5" />}
        title="Strategy Backtester"
        description="Simulate momentum strategies on historical OHLCV data and measure risk-adjusted returns."
        badge="Educational"
        badgeColor="violet"
      />

      {/* Inline risk disclaimer bar — UX-LEGAL-01 */}
      <RiskDisclaimerBar />

      <OverfittingWarning triggered={triggered} />

      <div className="grid gap-6 lg:grid-cols-4">
        {/* ── Sidebar ── */}
        <div className="lg:col-span-1 space-y-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <h3 className="mb-4 text-sm font-semibold text-slate-300">
              Configuration
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">
                  Symbol
                </label>
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="AAPL"
                  required
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">
                  Strategy
                </label>
                <select
                  value={strategy}
                  onChange={(e) => { setStrategy(e.target.value); setResult(null); }}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="momentum">Momentum (SMA + RSI)</option>
                  <option value="mean_reversion">Mean Reversion (Bollinger + RSI)</option>
                  <option value="macro_responsive">Macro-Responsive (Vol-Targeted)</option>
                </select>
              </div>

              {/* Strategy description card */}
              <StrategyDocPanel strategy={strategy} />

              {/* Sprint 25 — benchmark toggle */}
              <BenchmarkStrip value={benchmark} onChange={setBenchmark} />

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">
                  Initial Capital ($)
                </label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                  min={100}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    Start
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    End
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="border-t border-slate-800 pt-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Parameters
                </h4>
                <div className="space-y-3">
                  {strategy === "momentum" && [
                    { label: "SMA Fast", val: smaFast, set: setSmaFast, tip: "Short-term MA period" },
                    { label: "SMA Slow", val: smaSlow, set: setSmaSlow, tip: "Long-term MA period" },
                    { label: "RSI Period", val: rsiPeriod, set: setRsiPeriod, tip: "RSI lookback" },
                    { label: "RSI Threshold (Buy >)", val: rsiThreshold, set: setRsiThreshold, tip: "Min RSI to enter" },
                  ].map(({ label, val, set, tip }) => (
                    <div key={label}>
                      <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                        {label}<span title={tip}><Info className="h-3 w-3 text-slate-600" /></span>
                      </label>
                      <input type="number" value={val} min={2} onChange={(e) => set(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100" />
                    </div>
                  ))}
                  {strategy === "mean_reversion" && [
                    { label: "BB Period", val: smaFast, set: setSmaFast, tip: "Bollinger Band lookback (default 20)" },
                    { label: "BB Std Dev", val: "2", set: () => { }, tip: "Standard deviations for bands" },
                    { label: "RSI Period", val: rsiPeriod, set: setRsiPeriod, tip: "RSI lookback" },
                    { label: "RSI Oversold (entry <)", val: rsiThreshold, set: setRsiThreshold, tip: "Entry when RSI below this" },
                  ].map(({ label, val, set, tip }) => (
                    <div key={label}>
                      <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                        {label}<span title={tip}><Info className="h-3 w-3 text-slate-600" /></span>
                      </label>
                      <input type="number" value={val} min={2} onChange={(e) => (set as (v: string) => void)(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100" />
                    </div>
                  ))}
                  {strategy === "macro_responsive" && [
                    { label: "Vol Period", val: smaFast, set: setSmaFast, tip: "Realised vol lookback (default 20)" },
                    { label: "Trend MA Period", val: smaSlow, set: setSmaSlow, tip: "Only trade above this SMA" },
                    { label: "Vol Target (%)", val: rsiThreshold, set: setRsiThreshold, tip: "Annual vol target (e.g. 15)" },
                  ].map(({ label, val, set, tip }) => (
                    <div key={label}>
                      <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                        {label}<span title={tip}><Info className="h-3 w-3 text-slate-600" /></span>
                      </label>
                      <input type="number" value={val} min={2} onChange={(e) => (set as (v: string) => void)(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100" />
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Simulating…
                  </span>
                ) : (
                  "Run Backtest"
                )}
              </button>
            </form>

            {error && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-950/30 p-3 text-sm text-red-300">
                {error}
              </div>
            )}
          </div>

          <a
            href="/learn/backtesting-pitfalls"
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/30 p-4 text-sm text-slate-400 hover:border-slate-700 hover:text-slate-200 transition-colors"
          >
            <Activity className="h-4 w-4 text-blue-400" />
            Learn: Common Backtesting Pitfalls →
          </a>
        </div>

        {/* ── Results ── */}
        <div className="lg:col-span-3 space-y-5">
          {!result && !loading && (
            <div className="flex h-[420px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-700 bg-slate-900/30">
              <TrendingUp className="h-10 w-10 text-slate-600" />
              <p className="text-sm text-slate-500">
                Configure the strategy and click Run Backtest
              </p>
            </div>
          )}

          {loading && (
            <div className="flex h-[420px] flex-col items-center justify-center gap-3 rounded-xl border border-slate-800 bg-slate-900/50">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500/30 border-t-blue-500" />
              <p className="text-sm text-slate-400 animate-pulse">
                Simulating {symbol} trading history…
              </p>
            </div>
          )}

          {result && s && !loading && (
            <div className="space-y-5">
              {/* Save button */}
              <div className="flex justify-end">
                <button
                  onClick={() => setShowSaveModal(true)}
                  className="flex items-center gap-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium px-4 py-2 transition"
                >
                  <Save className="h-4 w-4" />
                  Save Strategy
                </button>
              </div>

              {/* Stat grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatCard
                  label="Total Return"
                  value={`${s.total_return_pct >= 0 ? "+" : ""}${s.total_return_pct.toFixed(2)}%`}
                  color={s.total_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}
                  sub={`Ann. ${s.annualized_return_pct >= 0 ? "+" : ""}${s.annualized_return_pct.toFixed(1)}%`}
                />
                <StatCard
                  label="Max Drawdown"
                  value={`${s.max_drawdown_pct.toFixed(2)}%`}
                  color="text-red-400"
                  sub={`Recovery: ${s.recovery_factor.toFixed(2)}×`}
                />
                <StatCard
                  label="Sharpe Ratio"
                  value={s.sharpe_ratio.toFixed(2)}
                  color={s.sharpe_ratio > 1.2 ? "text-amber-400" : "text-slate-100"}
                  sub={s.sharpe_ratio > 1.2 ? "⚠ Possible overfit" : undefined}
                />
                <StatCard
                  label="Win Rate"
                  value={`${s.win_rate_pct.toFixed(1)}%`}
                  color={s.win_rate_pct >= 50 ? "text-emerald-400" : "text-slate-100"}
                  sub={`${s.total_trades} trades`}
                />
              </div>

              {/* Equity curve */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                <h3 className="mb-1 text-sm font-semibold text-slate-200">
                  Equity Curve
                </h3>
                <p className="mb-4 text-xs text-slate-500">
                  Strategy (blue) vs{" "}
                  <span className="text-slate-400 font-medium">
                    {result.benchmark_label ?? "Buy & Hold"}
                  </span>{" "}
                  benchmark (slate)
                </p>
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={result.equity_curve}
                      margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#1e293b"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="date"
                        stroke="#475569"
                        fontSize={11}
                        tickFormatter={(v) =>
                          new Date(v).toLocaleDateString(undefined, {
                            month: "short",
                            year: "2-digit",
                          })
                        }
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        stroke="#475569"
                        fontSize={11}
                        tickFormatter={(v) =>
                          `$${(v / 1000).toFixed(0)}k`
                        }
                        domain={["auto", "auto"]}
                        width={48}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          border: "1px solid #1e293b",
                          borderRadius: "0.5rem",
                          color: "#f8fafc",
                          fontSize: 12,
                        }}
                        labelFormatter={(l) =>
                          new Date(l).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })
                        }
                        formatter={(value: number, name: string) => [
                          `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                          name === "equity" ? "Strategy" : "Buy & Hold",
                        ]}
                      />
                      <Legend
                        formatter={(v) =>
                          v === "equity" ? "Strategy" : "Buy & Hold"
                        }
                        wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="equity"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: "#3b82f6" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="benchmark_equity"
                        stroke="#475569"
                        strokeWidth={1.5}
                        strokeDasharray="4 2"
                        dot={false}
                        activeDot={{ r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Drawdown chart — UX-BACKTEST-03 */}
              <DrawdownChart
                equityCurve={result.equity_curve}
                maxDrawdownPct={s.max_drawdown_pct}
              />

              {/* Monthly returns heatmap — UX-BACKTEST-02 */}
              <MonthlyHeatmap equityCurve={result.equity_curve} />

              {/* Secondary stats */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
                {[
                  { label: "Sortino Ratio", value: s.sortino_ratio.toFixed(2) },
                  {
                    label: "Profit Factor",
                    value: isFinite(s.profit_factor)
                      ? s.profit_factor.toFixed(2)
                      : "∞",
                  },
                  {
                    label: "Recovery Factor",
                    value: `${s.recovery_factor.toFixed(2)}×`,
                  },
                  { label: "Total Trades", value: String(s.total_trades) },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="rounded-xl border border-slate-800 bg-slate-900/40 p-3"
                  >
                    <div className="text-xs text-slate-500">{label}</div>
                    <div className="mt-1 font-semibold text-slate-200">
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {result.assumptions_applied && (
                <p className="text-xs text-slate-500 border-t border-slate-800 pt-3">
                  <span className="font-medium text-slate-400">
                    Assumptions:{" "}
                  </span>
                  {result.assumptions_applied}
                </p>
              )}

              {/* Sprint 25 — Trade Log */}
              {result.trade_log && result.trade_log.length > 0 && (
                <TradeLogTable trades={result.trade_log} />
              )}

              {/* Parameter Sweep — Sprint 14 UX-BACKTEST-04 */}
              <ParameterSweepPanel
                symbol={symbol}
                strategy={strategy}
                baseParams={{
                  sma_fast:      Number(smaFast),
                  sma_slow:      Number(smaSlow),
                  rsi_period:    Number(rsiPeriod),
                  rsi_threshold: Number(rsiThreshold),
                }}
                initialCapital={Number(initialCapital)}
                startDate={startDate || undefined}
                endDate={endDate || undefined}
              />

              {/* Walk-Forward Validation — Sprint 18 */}
              <WalkForwardPanel
                symbol={symbol}
                strategy={strategy}
                baseParams={{
                  sma_fast:      Number(smaFast),
                  sma_slow:      Number(smaSlow),
                  rsi_period:    Number(rsiPeriod),
                  rsi_threshold: Number(rsiThreshold),
                }}
                initialCapital={Number(initialCapital)}
              />
              {/* end Sprint 18 walk-forward */}
            </div>
          )}
        </div>
      </div>

      {/* ── Strategy Library ── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/30">
        <button
          onClick={() => setLibOpen(!libOpen)}
          className="w-full flex items-center justify-between px-5 py-4 text-left"
        >
          <div className="flex items-center gap-2 text-slate-200 font-semibold">
            <BookOpen className="h-4 w-4 text-blue-400" />
            Strategy Library
            <span className="text-xs font-normal text-slate-500 ml-1">
              ({myStrategies.length} saved)
            </span>
          </div>
          {libOpen ? (
            <ChevronUp className="h-4 w-4 text-slate-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-500" />
          )}
        </button>

        {libOpen && (
          <div className="px-5 pb-5 space-y-4">
            <div className="flex gap-1 bg-slate-900 rounded-lg p-1 w-fit">
              {(["mine", "public"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setLibTab(tab)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${libTab === tab
                      ? "bg-slate-700 text-slate-100"
                      : "text-slate-500 hover:text-slate-300"
                    }`}
                >
                  {tab === "mine" ? "My Strategies" : "Community"}
                </button>
              ))}
            </div>

            {libLoading && (
              <p className="text-sm text-slate-500 py-4">Loading…</p>
            )}

            {!libLoading && displayedStrategies.length === 0 && (
              <div className="text-center py-10 text-slate-600 text-sm">
                {libTab === "mine"
                  ? "No saved strategies yet. Run a backtest and click Save Strategy."
                  : "No public strategies yet. Run a backtest and share it with the community!"}
              </div>
            )}

            <div className="space-y-2">
              {displayedStrategies.map((s) => (
                <StrategyCard
                  key={s.id}
                  s={s}
                  onLoad={handleLoad}
                  onDelete={handleDelete}
                  onTogglePublic={handleTogglePublic}
                  showActions={libTab === "mine"}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Save Modal ── */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl space-y-4">
            <h3 className="text-lg font-semibold text-white">Save Strategy</h3>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Name</label>
              <input
                autoFocus
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="e.g. TSLA Momentum 10/50"
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="pub"
                checked={savePublic}
                onChange={(e) => setSavePublic(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-blue-500"
              />
              <label
                htmlFor="pub"
                className="text-sm text-slate-300 flex items-center gap-1.5"
              >
                <Globe className="h-4 w-4 text-sky-400" />
                Share publicly in Community
              </label>
            </div>

            {savePublic && (
              <p className="text-xs text-slate-500 bg-slate-800 rounded-lg p-3">
                Public strategies are visible to all logged-in users in the
                Community tab. Your username is not shown — only the strategy
                metrics and ticker.
              </p>
            )}

            {saveError && (
              <p className="text-xs text-rose-400">{saveError}</p>
            )}

            <div className="flex gap-3 pt-1">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-lg transition"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => {
                  setShowSaveModal(false);
                  setSaveError(null);
                }}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium py-2 rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}