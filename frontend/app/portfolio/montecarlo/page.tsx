"use client";

/**
 * /portfolio/montecarlo — Sprint 56 Phase 3
 * Full rewrite: presets, single-asset mode, correlation matrix, vol auto-fill,
 * retirement mode, scenario comparison, educational tooltips, disclaimer.
 */

import { useState, useCallback } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
} from "recharts";
import {
  FlaskConical, Plus, Trash2, TrendingUp, AlertTriangle,
  ShieldCheck, Zap, Search, Info,
} from "lucide-react";
import ProGate from "@/components/ProGate";
import {
  runPortfolioMonteCarlo, runAssetMonteCarlo, fetchVolEstimate,
  MCPortfolioAsset, MCPortfolioResult, MCSimulationResult,
} from "@/lib/api";
import { PageBanner } from "@/components/ui/PageBanner";

// ── Types ─────────────────────────────────────────────────────────────────────

type Mode = "portfolio" | "single";
type JDModel = "GBM" | "JUMP_DIFFUSION";

interface AssetRow extends MCPortfolioAsset {
  fetchingVol?: boolean;
  volError?: string;
}

interface ScenarioRun {
  label: string;
  color: string;
  result: MCPortfolioResult | MCSimulationResult;
  mode: Mode;
  years: number;
}

// ── Presets ───────────────────────────────────────────────────────────────────

const PRESETS: { label: string; assets: AssetRow[]; contribution: number; years: number }[] = [
  {
    label: "Balanced 60/40",
    assets: [
      { symbol: "US Stocks", starting_value: 6000, mu: 0.10, sigma: 0.18 },
      { symbol: "Bonds",     starting_value: 4000, mu: 0.04, sigma: 0.08 },
    ],
    contribution: 500,
    years: 20,
  },
  {
    label: "All-Equity",
    assets: [
      { symbol: "US Stocks",    starting_value: 7000, mu: 0.10, sigma: 0.18 },
      { symbol: "Intl Stocks",  starting_value: 3000, mu: 0.07, sigma: 0.16 },
    ],
    contribution: 500,
    years: 20,
  },
  {
    label: "Retirement Income",
    assets: [
      { symbol: "Bonds",         starting_value: 5000, mu: 0.04, sigma: 0.08 },
      { symbol: "Div. Equities", starting_value: 3000, mu: 0.07, sigma: 0.12 },
      { symbol: "Cash",          starting_value: 2000, mu: 0.05, sigma: 0.01 },
    ],
    contribution: -500,
    years: 30,
  },
];

const SCENARIO_COLORS = ["#818cf8", "#34d399", "#f59e0b", "#f87171"];

// ── Tooltip helper ────────────────────────────────────────────────────────────

function Tip({ text }: { text: string }) {
  return (
    <span className="group relative ml-1 cursor-help">
      <Info className="inline h-3 w-3 text-slate-600 group-hover:text-sky-400 transition-colors" />
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-[10px] text-slate-300 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity z-50 shadow-xl">
        {text}
      </span>
    </span>
  );
}

// ── Correlation Matrix ────────────────────────────────────────────────────────

function CorrelationMatrix({
  assets,
  matrix,
  onChange,
}: {
  assets: AssetRow[];
  matrix: number[][];
  onChange: (r: number, c: number, v: number) => void;
}) {
  const n = assets.length;
  if (n < 2) return null;
  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="w-20" />
            {assets.map((a, i) => (
              <th key={i} className="px-2 py-1 text-[10px] text-slate-500 font-medium truncate max-w-[60px]">
                {a.symbol.slice(0, 6)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: n }).map((_, r) => (
            <tr key={r}>
              <td className="pr-2 text-[10px] text-slate-500 text-right truncate max-w-[80px]">
                {assets[r].symbol.slice(0, 8)}
              </td>
              {Array.from({ length: n }).map((_, c) => {
                const isDiag = r === c;
                const val = matrix[r]?.[c] ?? (isDiag ? 1 : 0);
                return (
                  <td key={c} className="px-1 py-0.5">
                    <input
                      type="number"
                      step={0.05}
                      min={-1}
                      max={1}
                      disabled={isDiag}
                      value={isDiag ? 1 : val}
                      onChange={(e) => onChange(r, c, Number(e.target.value))}
                      className={`w-14 rounded border px-1.5 py-1 text-center text-xs focus:outline-none focus:border-sky-500 ${
                        isDiag
                          ? "border-slate-700 bg-slate-700 text-slate-500 cursor-not-allowed"
                          : "border-slate-700 bg-slate-800 text-slate-200"
                      }`}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Asset row ─────────────────────────────────────────────────────────────────

function AssetRowCard({
  asset,
  index,
  mode,
  onUpdate,
  onRemove,
  onFetchVol,
}: {
  asset: AssetRow;
  index: number;
  mode: Mode;
  onUpdate: (i: number, field: keyof AssetRow, v: unknown) => void;
  onRemove: (i: number) => void;
  onFetchVol: (i: number) => void;
}) {
  const showJD = mode === "single" && asset.model_type === "JUMP_DIFFUSION";
  return (
    <div className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={asset.symbol}
          placeholder="Symbol / Name"
          onChange={(e) => onUpdate(index, "symbol", e.target.value)}
          className="flex-1 bg-transparent text-xs font-bold text-slate-200 focus:outline-none border-b border-slate-800 focus:border-sky-500 pb-0.5"
        />
        <button
          onClick={() => onFetchVol(index)}
          disabled={!asset.symbol.trim() || asset.fetchingVol}
          title="Auto-fill sigma/mu from OHLCV history"
          className="rounded p-1 text-[10px] text-sky-400 hover:bg-sky-900/30 disabled:opacity-30 transition-colors flex items-center gap-0.5"
        >
          <Search className="h-3 w-3" />
          {asset.fetchingVol ? "…" : "Fetch"}
        </button>
        <button onClick={() => onRemove(index)} className="text-slate-600 hover:text-rose-500 transition">
          <Trash2 className="h-3 w-3" />
        </button>
      </div>

      {asset.volError && (
        <p className="text-[10px] text-rose-400">{asset.volError}</p>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-[10px] text-slate-500 flex items-center">
            Return μ
            <Tip text="Expected annual return (e.g. 0.10 = 10%). Historical US equities average ~7–10%." />
          </span>
          <input
            type="number" step={0.01}
            value={asset.mu}
            onChange={(e) => onUpdate(index, "mu", Number(e.target.value))}
            className="w-full bg-transparent text-xs text-slate-300 border-b border-slate-800 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <div>
          <span className="text-[10px] text-slate-500 flex items-center">
            Volatility σ
            <Tip text="Annual volatility (e.g. 0.18 = 18% std dev). Higher = more uncertainty." />
          </span>
          <input
            type="number" step={0.01}
            value={asset.sigma}
            onChange={(e) => onUpdate(index, "sigma", Number(e.target.value))}
            className="w-full bg-transparent text-xs text-slate-300 border-b border-slate-800 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {mode === "single" && (
        <div>
          <span className="text-[10px] text-slate-500 block mb-1">Model</span>
          <div className="flex gap-1">
            {(["GBM", "JUMP_DIFFUSION"] as JDModel[]).map((m) => (
              <button
                key={m}
                onClick={() => onUpdate(index, "model_type", m)}
                className={`rounded px-2 py-0.5 text-[10px] font-semibold border transition-colors ${
                  (asset.model_type ?? "GBM") === m
                    ? "border-indigo-500 bg-indigo-900/40 text-indigo-300"
                    : "border-slate-700 bg-slate-800 text-slate-500"
                }`}
              >
                {m === "GBM" ? "GBM" : "Jump Diffusion"}
              </button>
            ))}
          </div>
        </div>
      )}

      {showJD && (
        <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800">
          {[
            { key: "jump_intensity" as keyof AssetRow, label: "λ jumps/yr", tip: "Expected crashes per year. US equities ~2–3 major drops annually." },
            { key: "jump_mean" as keyof AssetRow,      label: "Jump mean",   tip: "Average log-return of a jump (negative = crash)." },
            { key: "jump_std" as keyof AssetRow,       label: "Jump σ",      tip: "Volatility of jump size." },
          ].map(({ key, label, tip }) => (
            <div key={key}>
              <span className="text-[10px] text-slate-500 flex items-center">{label}<Tip text={tip} /></span>
              <input
                type="number" step={0.05}
                value={(asset[key] as number | undefined) ?? 0}
                onChange={(e) => onUpdate(index, key, Number(e.target.value))}
                className="w-full bg-transparent text-xs text-slate-300 border-b border-slate-800 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function MonteCarloDashboard() {
  const [mode, setMode] = useState<Mode>("portfolio");
  const [assets, setAssets] = useState<AssetRow[]>([
    { symbol: "US Stocks", starting_value: 6000, mu: 0.10, sigma: 0.18 },
    { symbol: "Bonds",     starting_value: 4000, mu: 0.04, sigma: 0.08 },
  ]);
  const [startingCapital, setStartingCapital] = useState(10000);
  const [years, setYears] = useState(20);
  const [monthlyContrib, setMonthlyContrib] = useState(500);
  const [corrMatrix, setCorrMatrix] = useState<number[][]>([]);
  const [showCorr, setShowCorr] = useState(false);
  const [scenarios, setScenarios] = useState<ScenarioRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRetirement = monthlyContrib < 0;
  const fmt = (v: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);

  // ── Correlation matrix helpers ──────────────────────────────────────────────

  const ensureMatrix = useCallback((n: number) => {
    const m: number[][] = Array.from({ length: n }, (_, r) =>
      Array.from({ length: n }, (_, c) => (r === c ? 1 : 0))
    );
    setCorrMatrix(m);
  }, []);

  const updateCorr = (r: number, c: number, v: number) => {
    setCorrMatrix((prev) => {
      const next = prev.map((row) => [...row]);
      next[r][c] = v;
      next[c][r] = v; // keep symmetric
      return next;
    });
  };

  const resetCorr = () => ensureMatrix(assets.length);

  // ── Asset helpers ───────────────────────────────────────────────────────────

  const addAsset = () => {
    const next = [...assets, { symbol: "", starting_value: 1000, mu: 0.07, sigma: 0.15 }];
    setAssets(next);
    ensureMatrix(next.length);
  };

  const removeAsset = (i: number) => {
    const next = assets.filter((_, idx) => idx !== i);
    setAssets(next);
    ensureMatrix(next.length);
  };

  const updateAsset = (i: number, field: keyof AssetRow, v: unknown) => {
    setAssets((prev) => {
      const next = [...prev];
      next[i] = { ...next[i], [field]: v };
      return next;
    });
  };

  const fetchVol = async (i: number) => {
    const sym = assets[i].symbol.trim().toUpperCase();
    if (!sym) return;
    updateAsset(i, "fetchingVol", true);
    updateAsset(i, "volError", undefined);
    try {
      const data = await fetchVolEstimate(sym, 252);
      setAssets((prev) => {
        const next = [...prev];
        next[i] = {
          ...next[i],
          mu: data.annualized_return_pct,
          sigma: data.annualized_vol_pct,
          fetchingVol: false,
          volError: undefined,
        };
        return next;
      });
    } catch (e) {
      updateAsset(i, "fetchingVol", false);
      updateAsset(i, "volError", (e as Error).message);
    }
  };

  // ── Presets ─────────────────────────────────────────────────────────────────

  const applyPreset = (p: typeof PRESETS[0]) => {
    setAssets(p.assets);
    setMonthlyContrib(p.contribution);
    setYears(p.years);
    ensureMatrix(p.assets.length);
    setScenarios([]);
  };

  // ── Run ─────────────────────────────────────────────────────────────────────

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      let result: MCPortfolioResult | MCSimulationResult;

      if (mode === "single") {
        const a = assets[0];
        result = await runAssetMonteCarlo({
          symbol: a.symbol || "Asset",
          starting_value: startingCapital,
          mu: a.mu,
          sigma: a.sigma,
          years,
          model_type: a.model_type ?? "GBM",
          jump_intensity: a.jump_intensity ?? 0,
          jump_mean: a.jump_mean ?? 0,
          jump_std: a.jump_std ?? 0,
        });
      } else {
        // Re-scale asset starting_value so total sums to startingCapital
        const total = assets.reduce((s, a) => s + a.starting_value, 0) || startingCapital;
        const scaled: MCPortfolioAsset[] = assets.map((a) => ({
          ...a,
          starting_value: (a.starting_value / total) * startingCapital,
        }));
        result = await runPortfolioMonteCarlo({
          assets: scaled,
          correlation_matrix: corrMatrix.length === assets.length ? corrMatrix : null,
          starting_capital: startingCapital,
          monthly_contribution: monthlyContrib,
          years,
        });
      }

      const color = SCENARIO_COLORS[scenarios.length % SCENARIO_COLORS.length];
      const label = `Scenario ${scenarios.length + 1}`;
      setScenarios((prev) => [
        ...prev.slice(-2), // keep max 3 total
        { label, color, result, mode, years },
      ]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const latestScenario = scenarios[scenarios.length - 1] ?? null;
  const portfolioResult = latestScenario?.result as MCPortfolioResult | null;

  // ── Retirement KPI colour ───────────────────────────────────────────────────
  const successColor = (r: number) =>
    r >= 90 ? "text-emerald-400" : r >= 70 ? "text-amber-400" : "text-rose-400";

  // ── Chart data: overlay P50 lines for scenario comparison ─────────────────

  const overlayData = (() => {
    if (scenarios.length === 0) return [];
    const maxLen = Math.max(...scenarios.map((s) => s.result.trajectory.length));
    return Array.from({ length: maxLen }, (_, i) => {
      const point: Record<string, number> = { step: i };
      scenarios.forEach((s) => {
        const t = s.result.trajectory[i];
        if (t) point[s.label] = t.p50;
      });
      return point;
    });
  })();

  return (
    <ProGate feature="Advanced Monte Carlo Simulation">
      <div className="space-y-6">
        <PageBanner
          icon={<FlaskConical className="h-5 w-5" />}
          title="Monte Carlo Simulator"
          description="Project long-term portfolio outcomes using probabilistic path generation and correlation matrices."
          badge="QUANT"
          badgeColor="violet"
        />

        {/* Mode toggle */}
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-800 bg-slate-900 p-1">
            {(["portfolio", "single"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setScenarios([]); }}
                className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors capitalize ${
                  mode === m ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {m === "portfolio" ? "Portfolio Mode" : "Single Asset"}
              </button>
            ))}
          </div>
          {scenarios.length > 0 && (
            <button
              onClick={() => setScenarios([])}
              className="text-xs text-slate-500 hover:text-rose-400 transition-colors"
            >
              Clear scenarios
            </button>
          )}
        </div>

        {/* Preset strip */}
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-[10px] text-slate-600 uppercase tracking-wider font-semibold">Load preset:</span>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => applyPreset(p)}
              className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs text-slate-300 hover:border-indigo-500 hover:text-indigo-300 transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200">Settings</h3>

              <div>
                <label className="text-xs text-slate-400">Starting Capital ($)</label>
                <input
                  type="number" min={100}
                  value={startingCapital}
                  onChange={(e) => setStartingCapital(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 flex items-center">
                  {isRetirement ? "Monthly Withdrawal ($)" : "Monthly Contribution ($)"}
                  <Tip text="Positive = regular savings. Negative = retirement withdrawal mode." />
                </label>
                <input
                  type="number"
                  value={monthlyContrib}
                  onChange={(e) => setMonthlyContrib(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                />
                {isRetirement && (
                  <p className="mt-1 text-[10px] text-amber-400">Retirement withdrawal mode active</p>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-400">Horizon: {years} years</label>
                <input
                  type="range" min={1} max={50}
                  value={years}
                  onChange={(e) => setYears(Number(e.target.value))}
                  className="mt-1 w-full accent-indigo-500"
                />
              </div>

              {/* Assets */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    {mode === "single" ? "Asset" : "Assets"}
                  </h4>
                  {mode === "portfolio" && (
                    <button onClick={addAsset} className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 transition">
                      <Plus className="h-3 w-3" />
                    </button>
                  )}
                </div>

                {(mode === "single" ? [assets[0]].filter(Boolean) : assets).map((asset, i) => (
                  <AssetRowCard
                    key={i}
                    asset={asset}
                    index={i}
                    mode={mode}
                    onUpdate={updateAsset}
                    onRemove={removeAsset}
                    onFetchVol={fetchVol}
                  />
                ))}
              </div>

              {/* Correlation matrix toggle (portfolio only, ≥2 assets) */}
              {mode === "portfolio" && assets.length >= 2 && (
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <button
                    onClick={() => {
                      if (!showCorr) ensureMatrix(assets.length);
                      setShowCorr((v) => !v);
                    }}
                    className="text-xs text-slate-500 hover:text-sky-400 transition-colors"
                  >
                    {showCorr ? "Hide" : "Show"} correlation matrix
                  </button>
                  {showCorr && (
                    <>
                      <CorrelationMatrix
                        assets={assets}
                        matrix={corrMatrix}
                        onChange={updateCorr}
                      />
                      <button onClick={resetCorr} className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors">
                        Reset to 0
                      </button>
                    </>
                  )}
                </div>
              )}

              {error && (
                <div className="rounded-lg border border-rose-900/40 bg-rose-950/20 p-3 flex items-start gap-2">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-rose-300">{error}</p>
                </div>
              )}

              <button
                onClick={handleRun}
                disabled={loading}
                className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all"
              >
                {loading
                  ? <Zap className="h-4 w-4 animate-pulse mx-auto" />
                  : scenarios.length > 0
                    ? `Add Scenario ${scenarios.length + 1}`
                    : "Run 5,000 Paths"
                }
              </button>
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-3 space-y-6">
            {scenarios.length === 0 && !loading && (
              <div className="flex h-[500px] flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-slate-800 bg-slate-900/20">
                <TrendingUp className="h-12 w-12 text-slate-700" />
                <div className="text-center">
                  <p className="text-slate-400 font-medium">No active simulation</p>
                  <p className="text-sm text-slate-600 mt-1">Configure parameters and run the engine. Add up to 3 scenarios to compare.</p>
                </div>
              </div>
            )}

            {loading && (
              <div className="flex h-[400px] flex-col items-center justify-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 animate-pulse">
                <div className="h-10 w-10 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <p className="text-slate-400 font-medium tracking-wide text-sm">GENERATING 5,000 FUTURES…</p>
              </div>
            )}

            {latestScenario && !loading && (
              <>
                {/* KPI row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    {
                      label: isRetirement ? "Success Rate" : "Success Rate",
                      value: portfolioResult ? `${portfolioResult.success_rate.toFixed(1)}%` : "—",
                      sub: isRetirement
                        ? `Portfolio lasts ${years} years`
                        : "Paths ending above $0",
                      color: portfolioResult
                        ? successColor(portfolioResult.success_rate)
                        : "text-slate-300",
                      highlight: isRetirement,
                    },
                    {
                      label: "Median (P50)",
                      value: fmt(latestScenario.result.final_median),
                      sub: `After ${years} years`,
                      color: "text-slate-100",
                      highlight: false,
                    },
                    {
                      label: "Upside (P95)",
                      value: fmt(latestScenario.result.final_p95),
                      sub: "Best 5% of paths",
                      color: "text-emerald-400",
                      highlight: false,
                    },
                    {
                      label: "Downside (P5)",
                      value: fmt(latestScenario.result.final_p5),
                      sub: "Worst 5% of paths",
                      color: "text-indigo-400",
                      highlight: false,
                    },
                  ].map(({ label, value, sub, color, highlight }) => (
                    <div
                      key={label}
                      className={`rounded-xl border p-4 ${
                        highlight && isRetirement
                          ? portfolioResult && portfolioResult.success_rate >= 90
                            ? "border-emerald-800/50 bg-emerald-950/20"
                            : portfolioResult && portfolioResult.success_rate >= 70
                              ? "border-amber-800/50 bg-amber-950/20"
                              : "border-rose-800/50 bg-rose-950/20"
                          : "border-slate-800 bg-slate-900/60"
                      }`}
                    >
                      <span className="text-xs text-slate-500 block">{label}</span>
                      <span className={`text-2xl font-black ${color}`}>{value}</span>
                      <span className="text-[10px] text-slate-600 block mt-0.5">{sub}</span>
                    </div>
                  ))}
                </div>

                {/* Retirement plain-English */}
                {isRetirement && portfolioResult && (
                  <div className={`rounded-xl border px-5 py-4 text-sm font-semibold ${
                    portfolioResult.success_rate >= 90
                      ? "border-emerald-800/50 bg-emerald-950/10 text-emerald-300"
                      : portfolioResult.success_rate >= 70
                        ? "border-amber-800/50 bg-amber-950/10 text-amber-300"
                        : "border-rose-800/50 bg-rose-950/10 text-rose-300"
                  }`}>
                    Your portfolio has a <strong>{portfolioResult.success_rate.toFixed(1)}%</strong> chance of
                    lasting <strong>{years} years</strong> at this withdrawal rate.
                  </div>
                )}

                {/* Single-asset CVaR */}
                {mode === "single" && (latestScenario.result as MCSimulationResult).cvar_95 !== undefined && (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-xs text-slate-500 block">CVaR-95</span>
                      <span className="text-xl font-black text-rose-400">
                        {fmt((latestScenario.result as MCSimulationResult).cvar_95)}
                      </span>
                      <span className="text-[10px] text-slate-600 block mt-0.5">Expected loss in worst 5%</span>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-xs text-slate-500 block">Max Drawdown (P95)</span>
                      <span className="text-xl font-black text-amber-400">
                        {fmt((latestScenario.result as MCSimulationResult).max_drawdown_p95)}
                      </span>
                      <span className="text-[10px] text-slate-600 block mt-0.5">Worst-case drawdown</span>
                    </div>
                  </div>
                )}

                {/* Primary fan chart */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                  <h3 className="text-sm font-bold text-slate-100 mb-1">Probability Cone — Latest Scenario</h3>
                  <p className="text-xs text-slate-500 mb-4">Shaded bands show the distribution of 5,000 simulated paths.</p>
                  <div className="h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={latestScenario.result.trajectory}>
                        <defs>
                          <linearGradient id="gUp" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#10b981" stopOpacity={0.12} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="gDn" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.1} />
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                          dataKey="day"
                          stroke="#475569" fontSize={11}
                          tickFormatter={(v) => `Y${Math.floor(v / 365)}`}
                          interval={Math.max(1, Math.floor(latestScenario.result.trajectory.length / 5))}
                        />
                        <YAxis
                          stroke="#475569" fontSize={11} width={58}
                          tickFormatter={(v) => v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : `$${Math.round(v / 1000)}k`}
                        />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#020617", border: "1px solid #1e293b", borderRadius: "10px", fontSize: 11 }}
                          formatter={(v: number) => [fmt(v), ""]}
                          labelFormatter={(_, items) => {
                            const day = items[0]?.payload?.day as number | undefined;
                            return day !== undefined ? `Y${Math.floor(day / 365)}` : "";
                          }}
                        />
                        <Area type="monotone" dataKey="p95" stroke="none" fill="url(#gUp)" />
                        <Area type="monotone" dataKey="p75" stroke="#10b981" strokeWidth={1} fill="url(#gUp)" fillOpacity={0.5} />
                        <Area type="monotone" dataKey="p25" stroke="#ef4444" strokeWidth={1} fill="url(#gDn)" fillOpacity={0.5} />
                        <Area type="monotone" dataKey="p5"  stroke="none" fill="#ef4444" fillOpacity={0.04} />
                        <Area type="monotone" dataKey="p50" stroke={latestScenario.color} strokeWidth={2.5} fill="none" dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Scenario comparison chart */}
                {scenarios.length > 1 && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                    <h3 className="text-sm font-bold text-slate-100 mb-1">Scenario Comparison — Median (P50)</h3>
                    <p className="text-xs text-slate-500 mb-4">Each line is a scenario's median path.</p>
                    <div className="h-[240px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={overlayData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                          <XAxis dataKey="step" stroke="#475569" fontSize={11} tickFormatter={(v) => `Y${Math.floor(v / 12)}`} />
                          <YAxis stroke="#475569" fontSize={11} width={58}
                            tickFormatter={(v) => v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : `$${Math.round(v / 1000)}k`}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#020617", border: "1px solid #1e293b", borderRadius: "10px", fontSize: 11 }}
                            formatter={(v: number, name: string) => [fmt(v), name]}
                          />
                          <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
                          {scenarios.map((s) => (
                            <Line key={s.label} type="monotone" dataKey={s.label}
                              stroke={s.color} strokeWidth={2} dot={false} />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Disclaimer */}
                <div className="rounded-xl border border-amber-900/30 bg-amber-950/10 px-4 py-3 flex items-start gap-3">
                  <ShieldCheck className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    <span className="text-amber-400 font-semibold">Educational use only.</span>{" "}
                    Monte Carlo projections use historical parameters to generate hypothetical future scenarios.
                    They do not account for taxes, fees, inflation adjustments, or black swan events.
                    Past volatility does not guarantee future volatility. Not investment advice.
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </ProGate>
  );
}
