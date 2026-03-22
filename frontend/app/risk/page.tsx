"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert, TrendingDown, TrendingUp, BarChart3, AlertTriangle,
  ChevronDown, ChevronUp, Loader2, RefreshCw, Info, Plus, Trash2, X,
  Briefcase,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
function riskAuthHeaders(): HeadersInit {
  const t = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}) };
}
import {
  fetchScenarios, stressTestSymbol, stressTestSymbolMulti,
  stressTestPortfolio, stressTestPortfolioMulti,
  type ScenarioDto, type StockStressDto, type MultiScenarioStockDto,
  type PortfolioStressDto, type PortfolioStressPositionInput,
} from "@/lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt$(v: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);
}
function fmtPct(v: number) {
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}
function pctColor(v: number) {
  if (v >= 5) return "text-emerald-400";
  if (v >= 0) return "text-emerald-300";
  if (v > -10) return "text-amber-400";
  return "text-red-400";
}
function categoryBadge(cat: string) {
  const styles: Record<string, string> = {
    historical: "bg-amber-950/40 border-amber-700/40 text-amber-400",
    hypothetical: "bg-blue-950/40 border-blue-700/40 text-blue-400",
    macro: "bg-purple-950/40 border-purple-700/40 text-purple-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${styles[cat] ?? "bg-slate-800 border-slate-700 text-slate-400"}`}>
      {cat}
    </span>
  );
}

// ─── Scenario pill selector ───────────────────────────────────────────────────

function ScenarioPicker({
  scenarios,
  selected,
  onSelect,
}: {
  scenarios: ScenarioDto[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = scenarios.find((s) => s.id === selected);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 hover:border-slate-500 transition-colors w-full"
      >
        <span className="flex-1 text-left truncate">{current?.name ?? "Select scenario…"}</span>
        {current && categoryBadge(current.category)}
        {open ? <ChevronUp className="h-4 w-4 text-slate-500 flex-shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-500 flex-shrink-0" />}
      </button>

      {open && (
        <div className="absolute z-30 mt-1 w-full max-h-72 overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
          {scenarios.map((s) => (
            <button
              key={s.id}
              onClick={() => { onSelect(s.id); setOpen(false); }}
              className={`w-full flex items-start gap-2 px-4 py-3 text-left hover:bg-slate-800 transition-colors border-b border-slate-800 last:border-0 ${selected === s.id ? "bg-slate-800" : ""}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-slate-200 truncate">{s.name}</span>
                  {categoryBadge(s.category)}
                </div>
                <p className="text-xs text-slate-500 line-clamp-2">{s.description}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Single stock result card ─────────────────────────────────────────────────

function StockResultCard({ r }: { r: StockStressDto }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      {/* Summary row */}
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-slate-100">{r.scenario_name}</span>
            {categoryBadge(r.scenario_id.includes("2008") || r.scenario_id.includes("covid") || r.scenario_id.includes("2022") || r.scenario_id.includes("dot") || r.scenario_id.includes("black") ? "historical" : r.scenario_id.includes("inflation") ? "macro" : "hypothetical")}
          </div>
          <p className="text-xs text-slate-500 line-clamp-1">{r.macro_notes}</p>
        </div>

        {/* Impact */}
        <div className="text-right flex-shrink-0">
          <p className={`text-lg font-bold tabular-nums ${pctColor(r.estimated_pnl_pct)}`}>{fmtPct(r.estimated_pnl_pct)}</p>
          <p className={`text-xs tabular-nums ${pctColor(r.estimated_pnl_pct)}`}>{fmt$(r.estimated_pnl)}</p>
        </div>

        <button
          onClick={() => setExpanded((e) => !e)}
          className="rounded-lg p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-800 px-5 py-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
          <Stat label="Portfolio Value" value={fmt$(r.portfolio_value)} />
          <Stat label="Beta vs SPY" value={r.beta_vs_spy.toFixed(2)} />
          <Stat label="Annual Vol" value={`${r.annualised_vol.toFixed(1)}%`} />
          <Stat label="Max Drawdown (hist.)" value={`${r.max_drawdown_historical.toFixed(1)}%`} neutral />
          <Stat label="VaR 95 (1-day)" value={r.var_95 !== null ? fmt$(r.var_95) : "—"} neutral />
          <Stat label="CVaR 95" value={r.cvar_95 !== null ? fmt$(r.cvar_95) : "—"} neutral />
          <Stat label="VaR 99 (1-day)" value={r.var_99 !== null ? fmt$(r.var_99) : "—"} neutral />
          <Stat label="Recovery Est." value={r.recovery_estimate_days !== null ? `~${r.recovery_estimate_days} days` : "N/A"} neutral />
          {r.macro_notes && (
            <div className="col-span-2 sm:col-span-3 rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-2">
              <p className="text-slate-500 text-[11px] mb-1">Macro context</p>
              <p className="text-slate-300">{r.macro_notes}</p>
            </div>
          )}
          <div className="col-span-2 sm:col-span-3 text-slate-600 text-[10px] italic">{r.disclaimer}</div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, neutral }: { label: string; value: string; neutral?: boolean }) {
  return (
    <div>
      <p className="text-slate-500 mb-0.5">{label}</p>
      <p className={`font-medium ${neutral ? "text-slate-300" : "text-slate-100"}`}>{value}</p>
    </div>
  );
}

// ─── Multi-scenario comparison table ─────────────────────────────────────────

function MultiScenarioTable({ data }: { data: MultiScenarioStockDto }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-200">All Scenarios — {data.symbol}</p>
          <p className="text-xs text-slate-500">Position value: {fmt$(data.portfolio_value)}</p>
        </div>
        <div className="flex gap-4 text-xs">
          {data.worst_scenario && (
            <span className="flex items-center gap-1 text-red-400">
              <TrendingDown className="h-3.5 w-3.5" />
              Worst: {data.results.find(r => r.scenario_id === data.worst_scenario)?.scenario_name ?? data.worst_scenario}
            </span>
          )}
          {data.best_scenario && (
            <span className="flex items-center gap-1 text-emerald-400">
              <TrendingUp className="h-3.5 w-3.5" />
              Best: {data.results.find(r => r.scenario_id === data.best_scenario)?.scenario_name ?? data.best_scenario}
            </span>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-500">
              <th className="text-left px-5 py-2.5">Scenario</th>
              <th className="text-right px-4 py-2.5">Est. P&L</th>
              <th className="text-right px-4 py-2.5">% Change</th>
              <th className="text-right px-4 py-2.5">Beta</th>
              <th className="text-right px-4 py-2.5">VaR 95</th>
              <th className="text-right px-5 py-2.5">Recover</th>
            </tr>
          </thead>
          <tbody>
            {data.results
              .slice()
              .sort((a, b) => a.estimated_pnl_pct - b.estimated_pnl_pct)
              .map((r) => (
                <tr key={r.scenario_id} className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30">
                  <td className="px-5 py-2.5">
                    <span className="text-slate-200 font-medium">{r.scenario_name}</span>
                  </td>
                  <td className={`text-right px-4 py-2.5 font-mono tabular-nums ${pctColor(r.estimated_pnl_pct)}`}>
                    {fmt$(r.estimated_pnl)}
                  </td>
                  <td className={`text-right px-4 py-2.5 font-mono tabular-nums font-semibold ${pctColor(r.estimated_pnl_pct)}`}>
                    {fmtPct(r.estimated_pnl_pct)}
                  </td>
                  <td className="text-right px-4 py-2.5 text-slate-400 tabular-nums">{r.beta_vs_spy.toFixed(2)}</td>
                  <td className="text-right px-4 py-2.5 text-slate-400 tabular-nums">
                    {r.var_95 !== null ? fmt$(r.var_95) : "—"}
                  </td>
                  <td className="text-right px-5 py-2.5 text-slate-400">
                    {r.recovery_estimate_days !== null ? `~${r.recovery_estimate_days}d` : "—"}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Portfolio stress result ──────────────────────────────────────────────────

function PortfolioResultCard({ r }: { r: PortfolioStressDto }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      <div className="flex items-center gap-4 px-5 py-4">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-100 mb-0.5">{r.scenario_name}</p>
          <p className="text-xs text-slate-500">
            Total: {fmt$(r.total_portfolio_value)}
            {r.worst_position && <> · Worst: <span className="text-red-400">{r.worst_position}</span></>}
            {r.best_position && <> · Best: <span className="text-emerald-400">{r.best_position}</span></>}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className={`text-lg font-bold tabular-nums ${pctColor(r.total_estimated_pnl_pct)}`}>{fmtPct(r.total_estimated_pnl_pct)}</p>
          <p className={`text-xs tabular-nums ${pctColor(r.total_estimated_pnl_pct)}`}>{fmt$(r.total_estimated_pnl)}</p>
        </div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="rounded-lg p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-slate-800">
          {/* Per-position breakdown */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="text-left px-5 py-2">Symbol</th>
                  <th className="text-right px-4 py-2">Weight</th>
                  <th className="text-right px-4 py-2">Value</th>
                  <th className="text-right px-4 py-2">Est. P&L</th>
                  <th className="text-right px-5 py-2">% Impact</th>
                </tr>
              </thead>
              <tbody>
                {r.positions
                  .slice()
                  .sort((a, b) => a.estimated_pnl_pct - b.estimated_pnl_pct)
                  .map((p) => (
                    <tr key={p.symbol} className="border-b border-slate-800/50 last:border-0">
                      <td className="px-5 py-2 font-medium text-slate-200">{p.symbol}</td>
                      <td className="text-right px-4 py-2 text-slate-400">{p.weight_pct.toFixed(1)}%</td>
                      <td className="text-right px-4 py-2 text-slate-400 tabular-nums">{fmt$(p.value)}</td>
                      <td className={`text-right px-4 py-2 tabular-nums ${pctColor(p.estimated_pnl_pct)}`}>{fmt$(p.estimated_pnl)}</td>
                      <td className={`text-right px-5 py-2 tabular-nums font-semibold ${pctColor(p.estimated_pnl_pct)}`}>{fmtPct(p.estimated_pnl_pct)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {/* Aggregate risk */}
          <div className="px-5 py-4 grid grid-cols-3 gap-4 text-xs border-t border-slate-800">
            <Stat label="Portfolio VaR 95" value={r.portfolio_var_95 !== null ? fmt$(r.portfolio_var_95) : "—"} neutral />
            <Stat label="Portfolio VaR 99" value={r.portfolio_var_99 !== null ? fmt$(r.portfolio_var_99) : "—"} neutral />
            <Stat label="Portfolio CVaR 95" value={r.portfolio_cvar_95 !== null ? fmt$(r.portfolio_cvar_95) : "—"} neutral />
          </div>
          {r.macro_notes && (
            <div className="px-5 pb-4">
              <div className="rounded-lg bg-slate-800/50 border border-slate-700 px-3 py-2 text-xs text-slate-300">
                <span className="text-slate-500 mr-2">Macro:</span>{r.macro_notes}
              </div>
            </div>
          )}
          <p className="px-5 pb-4 text-[10px] text-slate-600 italic">{r.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

// ─── Portfolio builder ────────────────────────────────────────────────────────

function PortfolioBuilder({
  positions,
  onChange,
}: {
  positions: PortfolioStressPositionInput[];
  onChange: (p: PortfolioStressPositionInput[]) => void;
}) {
  const add = () => onChange([...positions, { symbol: "", weight: 0, value: 1000 }]);
  const remove = (i: number) => onChange(positions.filter((_, idx) => idx !== i));
  const update = (i: number, field: keyof PortfolioStressPositionInput, val: string) => {
    const updated = [...positions];
    if (field === "symbol") updated[i].symbol = val.toUpperCase();
    else if (field === "weight") updated[i].weight = parseFloat(val) / 100 || 0;
    else updated[i].value = parseFloat(val) || 0;
    onChange(updated);
  };

  const totalWeight = positions.reduce((s, p) => s + p.weight, 0);

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {positions.map((p, i) => (
          <div key={i} className="grid grid-cols-[1fr_80px_110px_auto] gap-2 items-center">
            <input
              type="text"
              value={p.symbol}
              onChange={(e) => update(i, "symbol", e.target.value)}
              placeholder="AAPL"
              maxLength={10}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 uppercase"
            />
            <div className="relative">
              <input
                type="number"
                value={(p.weight * 100).toFixed(0)}
                onChange={(e) => update(i, "weight", e.target.value)}
                placeholder="25"
                min={0}
                max={100}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 pr-6 text-sm tabular-nums text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-500">%</span>
            </div>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">$</span>
              <input
                type="number"
                value={p.value}
                onChange={(e) => update(i, "value", e.target.value)}
                placeholder="10000"
                min={1}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 pl-7 text-sm tabular-nums text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={() => remove(i)}
              className="p-2 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-950/20 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={add}
          disabled={positions.length >= 20}
          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 disabled:opacity-40 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          Add position
        </button>
        <span className={`text-xs tabular-nums ${Math.abs(totalWeight - 1) > 0.02 ? "text-amber-400" : "text-slate-500"}`}>
          Total weight: {(totalWeight * 100).toFixed(0)}%
          {Math.abs(totalWeight - 1) > 0.02 && " ⚠ should sum to 100%"}
        </span>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type Tab = "single" | "multi" | "portfolio";

export default function RiskPage() {
  const [scenarios, setScenarios] = useState<ScenarioDto[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("single");

  // Single stock
  const [sSymbol, setSSymbol] = useState("AAPL");
  const [sValue, setSValue] = useState(10000);
  const [sScenario, setSScenario] = useState("");
  const [sResult, setSResult] = useState<StockStressDto | null>(null);
  const [sLoading, setSLoading] = useState(false);
  const [sError, setSError] = useState<string | null>(null);

  // Multi scenario
  const [mSymbol, setMSymbol] = useState("AAPL");
  const [mValue, setMValue] = useState(10000);
  const [mResult, setMResult] = useState<MultiScenarioStockDto | null>(null);
  const [mLoading, setMLoading] = useState(false);
  const [mError, setMError] = useState<string | null>(null);

  // Portfolio
  const [pPositions, setPPositions] = useState<PortfolioStressPositionInput[]>([
    { symbol: "AAPL", weight: 0.4, value: 4000 },
    { symbol: "SPY", weight: 0.3, value: 3000 },
    { symbol: "TLT", weight: 0.3, value: 3000 },
  ]);
  const [savedPortfolios, setSavedPortfolios] = useState<{id: number; name: string; items: {symbol: string; weight: number}[]}[]>([]);
  const [portImportOpen, setPortImportOpen] = useState(false);
  const [pScenario, setPScenario] = useState("");
  const [pAllScenarios, setPAllScenarios] = useState(false);
  const [pResults, setPResults] = useState<PortfolioStressDto[]>([]);
  const [pLoading, setPLoading] = useState(false);
  const [pError, setPError] = useState<string | null>(null);

  useEffect(() => {
    fetchScenarios()
      .then((data) => {
        setScenarios(data);
        if (data.length > 0) {
          setSScenario(data[0].id);
          setPScenario(data[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setScenariosLoading(false));
  }, []);

  // Load saved portfolios for the import feature
  useEffect(() => {
    if (activeTab !== "portfolio") return;
    fetch(`${API_BASE}/api/v1/portfolios/`, { headers: riskAuthHeaders() })
      .then(r => r.ok ? r.json() : [])
      .then((data: any[]) => setSavedPortfolios(data.filter(p => p.items?.length > 0)))
      .catch(() => {});
  }, [activeTab]);

  const runSingle = async () => {
    if (!sSymbol || !sScenario) return;
    setSLoading(true);
    setSError(null);
    setSResult(null);
    try {
      const r = await stressTestSymbol(sSymbol.toUpperCase(), sScenario, sValue);
      setSResult(r);
    } catch (e) {
      setSError(e instanceof Error ? e.message : "Stress test failed");
    } finally {
      setSLoading(false);
    }
  };

  const runMulti = async () => {
    if (!mSymbol) return;
    setMLoading(true);
    setMError(null);
    setMResult(null);
    try {
      const r = await stressTestSymbolMulti(mSymbol.toUpperCase(), mValue);
      setMResult(r);
    } catch (e) {
      setMError(e instanceof Error ? e.message : "Multi stress test failed");
    } finally {
      setMLoading(false);
    }
  };

  const runPortfolio = async () => {
    const valid = pPositions.filter((p) => p.symbol && p.value > 0);
    if (!valid.length) return;
    setPLoading(true);
    setPError(null);
    setPResults([]);
    try {
      if (pAllScenarios) {
        const r = await stressTestPortfolioMulti(valid);
        setPResults(r);
      } else {
        if (!pScenario) return;
        const r = await stressTestPortfolio(valid, pScenario);
        setPResults([r]);
      }
    } catch (e) {
      setPError(e instanceof Error ? e.message : "Portfolio stress test failed");
    } finally {
      setPLoading(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "single", label: "Single Stock", icon: <ShieldAlert className="h-4 w-4" /> },
    { id: "multi", label: "All Scenarios", icon: <BarChart3 className="h-4 w-4" /> },
    { id: "portfolio", label: "Portfolio Stress", icon: <TrendingDown className="h-4 w-4" /> },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <ShieldAlert className="h-6 w-6 text-red-400" />
          <h2 className="text-xl font-semibold tracking-tight text-slate-100">Scenario & Stress Tests</h2>
        </div>
        <p className="text-sm text-slate-400">
          Apply historical crises and hypothetical market shocks to estimate portfolio impact, VaR, and recovery time.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="flex items-start gap-2.5 rounded-xl border border-amber-800/30 bg-amber-950/10 px-4 py-3">
        <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-amber-300/80">
          <span className="font-semibold text-amber-300">Educational tool only.</span>{" "}
          Stress test results are estimates based on historical beta and market data. They are not predictions and do not constitute investment advice.
          Actual results will differ. Past crises do not repeat identically.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex rounded-xl border border-slate-800 bg-slate-900/50 p-1 gap-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
              activeTab === t.id
                ? "bg-slate-800 text-slate-100 shadow"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Single Stock ──────────────────────────────────────────────── */}
      {activeTab === "single" && (
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-300">Configure Test</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Symbol</label>
                <input
                  type="text"
                  value={sSymbol}
                  onChange={(e) => setSSymbol(e.target.value.toUpperCase())}
                  placeholder="AAPL"
                  maxLength={10}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-slate-200 placeholder-slate-600 uppercase focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Position Value ($)</label>
                <input
                  type="number"
                  value={sValue}
                  onChange={(e) => setSValue(parseFloat(e.target.value) || 0)}
                  min={1}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm tabular-nums text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Scenario</label>
              {scenariosLoading ? (
                <div className="h-10 rounded-lg bg-slate-800 animate-pulse" />
              ) : (
                <ScenarioPicker scenarios={scenarios} selected={sScenario} onSelect={setSScenario} />
              )}
              {sScenario && (
                <p className="mt-1.5 text-xs text-slate-500 line-clamp-2">
                  {scenarios.find((s) => s.id === sScenario)?.description}
                </p>
              )}
            </div>

            <button
              onClick={runSingle}
              disabled={sLoading || !sSymbol || !sScenario}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {sLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</> : <><ShieldAlert className="h-4 w-4" /> Run Stress Test</>}
            </button>

            {sError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-800/40 bg-red-950/20 px-3 py-2 text-xs text-red-400">
                <X className="h-3.5 w-3.5" />{sError}
              </div>
            )}
          </div>

          {sResult && <StockResultCard r={sResult} />}
        </div>
      )}

      {/* ── Multi Scenario ──────────────────────────────────────────────── */}
      {activeTab === "multi" && (
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-300">Run All Scenarios</h3>
            <p className="text-xs text-slate-500">Compare a single position across every scenario in the library simultaneously.</p>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Symbol</label>
                <input
                  type="text"
                  value={mSymbol}
                  onChange={(e) => setMSymbol(e.target.value.toUpperCase())}
                  placeholder="TSLA"
                  maxLength={10}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-slate-200 placeholder-slate-600 uppercase focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Position Value ($)</label>
                <input
                  type="number"
                  value={mValue}
                  onChange={(e) => setMValue(parseFloat(e.target.value) || 0)}
                  min={1}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm tabular-nums text-slate-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <button
              onClick={runMulti}
              disabled={mLoading || !mSymbol}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {mLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Running all scenarios…</> : <><BarChart3 className="h-4 w-4" /> Run All Scenarios</>}
            </button>

            {mError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-800/40 bg-red-950/20 px-3 py-2 text-xs text-red-400">
                <X className="h-3.5 w-3.5" />{mError}
              </div>
            )}
          </div>

          {mResult && <MultiScenarioTable data={mResult} />}
        </div>
      )}

      {/* ── Portfolio ──────────────────────────────────────────────── */}
      {activeTab === "portfolio" && (
        <div className="space-y-5">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-300">Portfolio Positions</h3>
              {/* Import from saved portfolios */}
              {savedPortfolios.length > 0 && (
                <div className="relative">
                  <button
                    onClick={() => setPortImportOpen(o => !o)}
                    className="flex items-center gap-1.5 text-xs rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-slate-300 hover:bg-slate-800 transition-colors"
                  >
                    <Briefcase className="h-3.5 w-3.5 text-sky-400" />
                    Import from Portfolio
                    <ChevronDown className="h-3 w-3 text-slate-500" />
                  </button>
                  {portImportOpen && (
                    <div className="absolute right-0 top-full mt-1 z-30 min-w-[220px] rounded-xl border border-slate-700 bg-slate-900 shadow-2xl py-1">
                      <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Saved Portfolios</p>
                      {savedPortfolios.map(p => (
                        <button
                          key={p.id}
                          onClick={() => {
                            const totalW = p.items.reduce((s, i) => s + i.weight, 0) || 1;
                            const totalVal = 10000;
                            setPPositions(p.items.map(i => ({
                              symbol: i.symbol,
                              weight: i.weight / totalW,
                              value: Math.round((i.weight / totalW) * totalVal),
                            })));
                            setPortImportOpen(false);
                          }}
                          className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 transition-colors"
                        >
                          <span className="font-medium">{p.name}</span>
                          <span className="ml-1.5 text-slate-500 text-xs">{p.items.length} positions</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="grid grid-cols-[1fr_80px_110px_auto] gap-2">
              <span className="text-xs text-slate-500">Symbol</span>
              <span className="text-xs text-slate-500">Weight</span>
              <span className="text-xs text-slate-500">$ Value</span>
              <span />
            </div>
            <PortfolioBuilder positions={pPositions} onChange={setPPositions} />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-300">Scenario Selection</h3>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setPAllScenarios(false)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${!pAllScenarios ? "bg-blue-600 text-white" : "border border-slate-700 text-slate-400 hover:border-slate-500"}`}
              >
                Single Scenario
              </button>
              <button
                onClick={() => setPAllScenarios(true)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${pAllScenarios ? "bg-blue-600 text-white" : "border border-slate-700 text-slate-400 hover:border-slate-500"}`}
              >
                All Scenarios
              </button>
            </div>

            {!pAllScenarios && !scenariosLoading && (
              <ScenarioPicker scenarios={scenarios} selected={pScenario} onSelect={setPScenario} />
            )}

            <button
              onClick={runPortfolio}
              disabled={pLoading || pPositions.filter((p) => p.symbol && p.value > 0).length === 0}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {pLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Running…</> : <><TrendingDown className="h-4 w-4" /> Run Portfolio Stress Test</>}
            </button>

            {pError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-800/40 bg-red-950/20 px-3 py-2 text-xs text-red-400">
                <X className="h-3.5 w-3.5" />{pError}
              </div>
            )}
          </div>

          {pResults.length > 0 && (
            <div className="space-y-3">
              {pResults.map((r) => <PortfolioResultCard key={r.scenario_id} r={r} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
