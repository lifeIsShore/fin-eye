"use client";

import { useState, useEffect, useCallback } from "react";
import {
  runBacktest,
  BacktestRequest,
  BacktestResponse,
  saveStrategy,
  fetchMyStrategies,
  fetchPublicStrategies,
  deleteStrategy,
  updateStrategy,
  StrategyDto,
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
      className={`rounded-xl border p-4 ${
        triggered
          ? "border-red-500/40 bg-red-950/30"
          : "border-amber-500/30 bg-amber-950/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={`mt-0.5 h-5 w-5 flex-shrink-0 ${
            triggered ? "text-red-400" : "text-amber-400"
          }`}
        />
        <div>
          <p
            className={`text-sm font-semibold ${
              triggered ? "text-red-300" : "text-amber-300"
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

const MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

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
                    className={`text-right font-mono tabular-nums pl-2 font-semibold ${
                      annualRet >= 0 ? "text-emerald-400" : "text-rose-400"
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
                className={`font-mono font-semibold ${
                  s.total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"
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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BacktestingPage() {
  const { symbol: globalSymbol } = useSymbol();
  const [symbol, setSymbol] = useState(globalSymbol || "TSLA");
  const [initialCapital, setInitialCapital] = useState("10000");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [smaFast, setSmaFast] = useState("10");
  const [smaSlow, setSmaSlow] = useState("50");
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [rsiThreshold, setRsiThreshold] = useState("40");

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
      strategy: "momentum",
      initial_capital: Number(initialCapital),
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      parameters: {
        sma_fast: Number(smaFast),
        sma_slow: Number(smaSlow),
        rsi_period: Number(rsiPeriod),
        rsi_threshold: Number(rsiThreshold),
      },
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
                <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300">
                  Momentum (SMA Crossover + RSI)
                </div>
              </div>

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
                  {[
                    {
                      label: "SMA Fast",
                      val: smaFast,
                      set: setSmaFast,
                      tip: "Short-term MA period",
                    },
                    {
                      label: "SMA Slow",
                      val: smaSlow,
                      set: setSmaSlow,
                      tip: "Long-term MA period",
                    },
                    {
                      label: "RSI Period",
                      val: rsiPeriod,
                      set: setRsiPeriod,
                      tip: "RSI lookback",
                    },
                    {
                      label: "RSI Threshold (Buy >)",
                      val: rsiThreshold,
                      set: setRsiThreshold,
                      tip: "Minimum RSI to enter",
                    },
                  ].map(({ label, val, set, tip }) => (
                    <div key={label}>
                      <label className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                        {label}
                        <span title={tip}>
                          <Info className="h-3 w-3 text-slate-600" />
                        </span>
                      </label>
                      <input
                        type="number"
                        value={val}
                        min={2}
                        onChange={(e) => set(e.target.value)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100"
                      />
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
                  Strategy (blue) vs Buy &amp; Hold benchmark (slate)
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
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
                    libTab === tab
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
