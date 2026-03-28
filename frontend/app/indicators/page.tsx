"use client";

import { useState, useCallback, useEffect } from "react";
import {
  AreaChart, Area, LineChart, Line,
  BarChart, Bar, ReferenceLine,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchIndicatorCatalog,
  evaluateIndicator,
  fetchSavedIndicators,
  saveIndicator,
  deleteIndicator,
  evaluateSavedIndicator,
  type CatalogEntry,
  type EvaluateResponseDto,
  type CustomIndicatorDto,
  type FormulaNode,
} from "../../lib/api";
import ProGate from "@/components/ProGate";

// ─── Starter presets ──────────────────────────────────────────────────────────

const PRESETS: Record<string, { label: string; formula: FormulaNode }> = {
  rsi14: {
    label: "RSI (14)",
    formula: { type: "indicator", fn: "RSI", params: { period: 14 } },
  },
  sma_cross: {
    label: "SMA 10 / 50 Cross",
    formula: {
      type: "cross",
      direction: "above",
      fast: { type: "indicator", fn: "SMA", params: { period: 10 } },
      slow: { type: "indicator", fn: "SMA", params: { period: 50 } },
    },
  },
  macd_hist: {
    label: "MACD Histogram",
    formula: { type: "indicator", fn: "MACD", params: { fast: 12, slow: 26, signal: 9 }, output: "hist" },
  },
  bb_pb: {
    label: "Bollinger %B",
    formula: { type: "indicator", fn: "BB", params: { period: 20, std: 2.0 }, output: "pb" },
  },
  rsi_minus_50: {
    label: "RSI − 50 (centred)",
    formula: {
      type: "binop", op: "-",
      left:  { type: "indicator", fn: "RSI", params: { period: 14 } },
      right: { type: "number", value: 50 },
    },
  },
  ema_diff: {
    label: "EMA 12 − EMA 26",
    formula: {
      type: "binop", op: "-",
      left:  { type: "indicator", fn: "EMA", params: { period: 12 } },
      right: { type: "indicator", fn: "EMA", params: { period: 26 } },
    },
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function thinArray<T>(arr: T[], max = 120): T[] {
  if (arr.length <= max) return arr;
  const step = Math.ceil(arr.length / max);
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1);
}

function categoryColor(cat: string): string {
  return (
    { Trend: "text-blue-300 bg-blue-900/30 border-blue-700/40",
      Momentum: "text-amber-300 bg-amber-900/30 border-amber-700/40",
      Volatility: "text-violet-300 bg-violet-900/30 border-violet-700/40",
      Volume: "text-teal-300 bg-teal-900/30 border-teal-700/40",
      Price: "text-slate-300 bg-slate-800/60 border-slate-700/40",
    }[cat] ?? "text-slate-300 bg-slate-800 border-slate-700"
  );
}

function formulaToText(node: FormulaNode): string {
  if (!node) return "";
  const t = node.type as string;
  if (t === "number") return String(node.value);
  if (t === "indicator") {
    const fn = node.fn as string;
    const params = node.params as Record<string, number> | undefined;
    const out    = node.output as string | undefined;
    const pStr   = params && Object.keys(params).length
      ? "(" + Object.entries(params).map(([k, v]) => `${k}=${v}`).join(", ") + ")"
      : "";
    return `${fn}${pStr}${out ? `.${out}` : ""}`;
  }
  if (t === "binop") {
    return `(${formulaToText(node.left as FormulaNode)} ${node.op} ${formulaToText(node.right as FormulaNode)})`;
  }
  if (t === "cross") {
    return `CROSS_${String(node.direction).toUpperCase()}(${formulaToText(node.fast as FormulaNode)}, ${formulaToText(node.slow as FormulaNode)})`;
  }
  return JSON.stringify(node);
}

// ─── Result chart ─────────────────────────────────────────────────────────────

function ResultChart({ result }: { result: EvaluateResponseDto }) {
  const raw = thinArray(result.dates.map((d, i) => ({
    date: fmtDate(d),
    value: result.values[i],
  })));

  const allVals = raw.map(r => r.value).filter((v): v is number => v !== null);
  const isSignal = result.type === "signal";

  if (isSignal) {
    const signals = raw.filter(r => r.value === 1);
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-emerald-900/40 border border-emerald-700/40 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
            Signal
          </span>
          <span className="text-xs text-slate-500">{signals.length} events in the last {result.dates.length} bars</span>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Signal Events</p>
          {signals.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-600">No signal events in the selected period</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {signals.map((s, i) => (
                <span key={i} className="rounded-lg bg-emerald-900/30 border border-emerald-700/30 px-2 py-1 text-xs text-emerald-300">
                  {s.date}
                </span>
              ))}
            </div>
          )}
        </div>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={raw} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false}
              interval={Math.floor(raw.length / 8)} />
            <YAxis domain={[0, 1]} ticks={[0, 1]} tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false} />
            <Bar dataKey="value" maxBarSize={6} radius={[2, 2, 0, 0]}>
              {raw.map((entry, i) => (
                <Cell key={i} fill={entry.value === 1 ? "#10b981" : "#1e293b"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Detect whether values cross zero (MACD hist, centred oscillators)
  const hasBothSigns = allVals.some(v => v > 0) && allVals.some(v => v < 0);
  const color = hasBothSigns ? "#60a5fa" : "#60a5fa";
  const gradId = "indGrad";

  return (
    <div className="space-y-3">
      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: "Current", val: result.summary.current },
          { label: "Mean",    val: result.summary.mean },
          { label: "Min",     val: result.summary.min },
          { label: "Max",     val: result.summary.max },
        ].map(({ label, val }) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-center">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider">{label}</p>
            <p className="text-sm font-black tabular-nums text-slate-200">
              {val != null ? val.toFixed(2) : "—"}
            </p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <ResponsiveContainer width="100%" height={200}>
          {hasBothSigns ? (
            <AreaChart data={raw} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false}
                interval={Math.floor(raw.length / 8)} />
              <YAxis tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false}
                tickFormatter={(v: number) => v.toFixed(1)} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                labelStyle={{ color: "#94a3b8", fontSize: 10 }}
                formatter={(v: number) => [v != null ? v.toFixed(4) : "—", "Value"]}
              />
              <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 2" />
              <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1.5}
                fill={`url(#${gradId})`} dot={false} connectNulls />
            </AreaChart>
          ) : (
            <LineChart data={raw} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false}
                interval={Math.floor(raw.length / 8)} />
              <YAxis tick={{ fill: "#475569", fontSize: 9 }} axisLine={false} tickLine={false}
                tickFormatter={(v: number) => v.toFixed(1)} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                labelStyle={{ color: "#94a3b8", fontSize: 10 }}
                formatter={(v: number) => [v != null ? v.toFixed(4) : "—", "Value"]}
              />
              {result.summary.mean != null && (
                <ReferenceLine y={result.summary.mean} stroke="#475569" strokeDasharray="3 2"
                  label={{ value: `avg ${result.summary.mean.toFixed(2)}`, position: "insideTopRight", fill: "#475569", fontSize: 9 }} />
              )}
              <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Saved indicator card ─────────────────────────────────────────────────────

function SavedCard({
  ind, onDelete, onLoad, onEvaluate,
}: {
  ind: CustomIndicatorDto;
  onDelete: (id: number) => void;
  onLoad: (formula: FormulaNode) => void;
  onEvaluate: (id: number) => void;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-100">{ind.name}</p>
          {ind.description && <p className="text-xs text-slate-500">{ind.description}</p>}
        </div>
        <div className="flex gap-1 shrink-0">
          <button onClick={() => onLoad(ind.formula)}
            className="rounded-lg bg-slate-800 hover:bg-slate-700 px-2 py-1 text-xs text-slate-300 transition">
            Load
          </button>
          <button onClick={() => onEvaluate(ind.id)}
            className="rounded-lg bg-blue-700/50 hover:bg-blue-600/60 px-2 py-1 text-xs text-blue-300 transition">
            Run
          </button>
          <button onClick={() => onDelete(ind.id)}
            className="rounded-lg hover:bg-rose-950/40 px-1.5 py-1 text-slate-600 hover:text-rose-400 transition text-base leading-none">
            ×
          </button>
        </div>
      </div>
      <code className="block text-[10px] text-slate-500 bg-slate-950/50 rounded p-2 overflow-x-auto">
        {formulaToText(ind.formula)}
      </code>
    </div>
  );
}

// ─── Function palette button ──────────────────────────────────────────────────

function FnButton({ entry, onInsert }: { entry: CatalogEntry; onInsert: (e: CatalogEntry) => void }) {
  const [hover, setHover] = useState(false);
  return (
    <div className="relative">
      <button
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={() => onInsert(entry)}
        className={`w-full text-left rounded-lg border px-3 py-2 text-xs font-semibold transition hover:brightness-110 ${categoryColor(entry.category)}`}
      >
        {entry.fn}
        <span className="ml-1.5 font-normal opacity-60">{entry.category}</span>
      </button>
      {hover && (
        <div className="absolute left-full top-0 z-50 ml-2 w-64 rounded-xl border border-slate-700 bg-slate-900 p-3 shadow-2xl space-y-1.5">
          <p className="text-xs font-bold text-slate-200">{entry.label}</p>
          <p className="text-[11px] text-slate-400 leading-relaxed">{entry.description}</p>
          {entry.outputs.length > 0 && (
            <p className="text-[10px] text-slate-500">Outputs: {entry.outputs.join(", ")}</p>
          )}
          {entry.params.length > 0 && (
            <div className="text-[10px] text-slate-500 space-y-0.5">
              {entry.params.map(p => (
                <div key={p.name}>
                  <span className="text-slate-400">{p.name}</span>: default {p.default} ({p.min}–{p.max})
                </div>
              ))}
            </div>
          )}
          <code className="block text-[9px] text-slate-500 bg-slate-950/60 rounded p-1.5 overflow-x-auto">
            {JSON.stringify(entry.example, null, 2)}
          </code>
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function IndicatorsPage() {
  const [catalog, setCatalog]       = useState<CatalogEntry[]>([]);
  const [saved, setSaved]           = useState<CustomIndicatorDto[]>([]);
  const [formulaText, setFormulaText] = useState(
    JSON.stringify(PRESETS.rsi14.formula, null, 2)
  );
  const [formulaError, setFormulaError] = useState<string | null>(null);
  const [symbol, setSymbol]         = useState("AAPL");
  const [timeframe, setTimeframe]   = useState("1d");
  const [periods, setPeriods]       = useState(300);
  const [result, setResult]         = useState<EvaluateResponseDto | null>(null);
  const [running, setRunning]       = useState(false);
  const [runError, setRunError]     = useState<string | null>(null);
  const [saveModal, setSaveModal]   = useState(false);
  const [saveName, setSaveName]     = useState("");
  const [saveDesc, setSaveDesc]     = useState("");
  const [saving, setSaving]         = useState(false);
  const [activeTab, setActiveTab]   = useState<"builder" | "saved">("builder");
  const [catFilter, setCatFilter]   = useState<string>("All");

  useEffect(() => {
    fetchIndicatorCatalog().then(setCatalog).catch(() => {});
    fetchSavedIndicators().then(setSaved).catch(() => {});
  }, []);

  const categories = ["All", ...Array.from(new Set(catalog.map(e => e.category)))];

  const parsedFormula = useCallback((): FormulaNode | null => {
    try {
      return JSON.parse(formulaText) as FormulaNode;
    } catch {
      return null;
    }
  }, [formulaText]);

  const handleRun = async () => {
    const formula = parsedFormula();
    if (!formula) {
      setFormulaError("Invalid JSON — check formula syntax");
      return;
    }
    setFormulaError(null);
    setRunError(null);
    setRunning(true);
    try {
      const res = await evaluateIndicator({
        formula, symbol: symbol.trim().toUpperCase(), timeframe, periods,
      });
      setResult(res);
    } catch (e: any) {
      setRunError(e.message ?? "Evaluation failed");
    } finally {
      setRunning(false);
    }
  };

  const handleInsertFn = (entry: CatalogEntry) => {
    setFormulaText(JSON.stringify(entry.example, null, 2));
    setResult(null);
  };

  const handlePreset = (key: string) => {
    setFormulaText(JSON.stringify(PRESETS[key].formula, null, 2));
    setResult(null);
  };

  const handleSave = async () => {
    const formula = parsedFormula();
    if (!formula || !saveName.trim()) return;
    setSaving(true);
    try {
      const created = await saveIndicator({ name: saveName, description: saveDesc || undefined, formula });
      setSaved(prev => [created, ...prev]);
      setSaveModal(false);
      setSaveName("");
      setSaveDesc("");
    } catch (e: any) {
      setRunError(e.message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteIndicator(id);
    setSaved(prev => prev.filter(i => i.id !== id));
  };

  const handleLoadSaved = (formula: FormulaNode) => {
    setFormulaText(JSON.stringify(formula, null, 2));
    setActiveTab("builder");
    setResult(null);
  };

  const handleEvaluateSaved = async (id: number) => {
    setRunError(null);
    setRunning(true);
    setActiveTab("builder");
    try {
      const res = await evaluateSavedIndicator(id, symbol.toUpperCase(), timeframe, periods);
      setResult(res);
    } catch (e: any) {
      setRunError(e.message ?? "Evaluation failed");
    } finally {
      setRunning(false);
    }
  };

  const visibleCatalog = catFilter === "All"
    ? catalog
    : catalog.filter(e => e.category === catFilter);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <ProGate feature="Indicator Builder">
        <div className="mx-auto max-w-7xl px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Indicator Builder</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Compose custom indicators from RSI, MACD, SMA, Bollinger and more — no code required
            </p>
          </div>
          {/* Symbol / timeframe controls */}
          <div className="flex flex-wrap gap-2 items-center">
            <input
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              placeholder="AAPL"
              className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:border-slate-500 focus:outline-none"
            />
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
            >
              {["1h", "1d", "1wk", "1mo"].map(tf => <option key={tf} value={tf}>{tf}</option>)}
            </select>
            <select
              value={periods}
              onChange={e => setPeriods(Number(e.target.value))}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
            >
              {[100, 200, 300, 500].map(p => <option key={p} value={p}>{p} bars</option>)}
            </select>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-slate-800 pb-0">
          {(["builder", "saved"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition -mb-px border-b-2 ${
                activeTab === tab
                  ? "border-blue-500 text-slate-100 bg-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {tab === "builder" ? "Formula Builder" : `Saved Indicators (${saved.length})`}
            </button>
          ))}
        </div>

        {/* ── BUILDER TAB ─────────────────────────────────────────────────── */}
        {activeTab === "builder" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

            {/* Left: function palette */}
            <div className="space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Functions
                </p>
                {/* Category filter */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {categories.map(cat => (
                    <button
                      key={cat}
                      onClick={() => setCatFilter(cat)}
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold border transition ${
                        catFilter === cat
                          ? "bg-blue-700/50 border-blue-600/50 text-blue-200"
                          : "bg-slate-800/60 border-slate-700/40 text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
                <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                  {visibleCatalog.map(entry => (
                    <FnButton key={entry.fn} entry={entry} onInsert={handleInsertFn} />
                  ))}
                </div>
              </div>

              {/* Presets */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Quick Presets
                </p>
                <div className="space-y-1.5">
                  {Object.entries(PRESETS).map(([key, { label }]) => (
                    <button
                      key={key}
                      onClick={() => handlePreset(key)}
                      className="w-full text-left rounded-lg border border-slate-700/50 bg-slate-900/40 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Middle: formula editor + run */}
            <div className="space-y-4 lg:col-span-2">

              {/* JSON editor */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Formula (JSON)
                  </p>
                  <span className="text-[10px] text-slate-600">
                    Click a function to insert · Edit params manually
                  </span>
                </div>
                <textarea
                  value={formulaText}
                  onChange={e => { setFormulaText(e.target.value); setFormulaError(null); }}
                  rows={10}
                  spellCheck={false}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 font-mono text-xs text-slate-200 focus:border-slate-500 focus:outline-none resize-y"
                  placeholder='{"type": "indicator", "fn": "RSI", "params": {"period": 14}}'
                />
                {formulaError && (
                  <p className="text-xs text-rose-400 flex items-center gap-1.5">
                    <span>⚠</span> {formulaError}
                  </p>
                )}

                {/* Formula preview */}
                {parsedFormula() && !formulaError && (
                  <div className="rounded-lg bg-slate-900/60 border border-slate-800 px-3 py-2 text-xs text-slate-400">
                    <span className="text-slate-600 mr-2">Preview:</span>
                    <code className="text-blue-300">{formulaToText(parsedFormula()!)}</code>
                  </div>
                )}
              </div>

              {/* Action bar */}
              <div className="flex flex-wrap gap-2 items-center">
                <button
                  onClick={handleRun}
                  disabled={running || !parsedFormula()}
                  className="rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-5 py-2 text-sm font-semibold text-white transition flex items-center gap-2"
                >
                  {running && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                  {running ? "Running…" : "▶ Run"}
                </button>
                <button
                  onClick={() => { setSaveModal(true); }}
                  disabled={!parsedFormula()}
                  className="rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 px-4 py-2 text-sm text-slate-300 transition"
                >
                  Save Indicator
                </button>
                <button
                  onClick={() => { setFormulaText(""); setResult(null); }}
                  className="rounded-lg border border-slate-700/50 bg-transparent px-3 py-2 text-sm text-slate-500 hover:text-slate-300 transition"
                >
                  Clear
                </button>
              </div>

              {/* Run error */}
              {runError && (
                <div className="rounded-xl border border-rose-800/40 bg-rose-950/30 px-4 py-3">
                  <p className="text-sm font-semibold text-rose-400">Evaluation error</p>
                  <p className="text-xs text-rose-400/80 mt-0.5">{runError}</p>
                </div>
              )}

              {/* Result chart */}
              {result && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Result — {symbol} · {timeframe}
                    </h3>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                      result.type === "signal"
                        ? "bg-emerald-900/40 border-emerald-700/40 text-emerald-300"
                        : "bg-blue-900/40 border-blue-700/40 text-blue-300"
                    }`}>
                      {result.type}
                    </span>
                    <span className="ml-auto text-[10px] text-slate-600">{result.dates.length} bars</span>
                  </div>
                  <ResultChart result={result} />
                </div>
              )}

              {/* Node type reference */}
              <details className="rounded-xl border border-slate-800/50 bg-slate-900/30">
                <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-slate-500 select-none">
                  Formula JSON reference ▾
                </summary>
                <div className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-400">
                  {[
                    { t: "indicator", code: `{"type":"indicator","fn":"RSI","params":{"period":14}}`, note: "Any function from the palette. Add \"output\":\"...\" for MACD/BB/STOCH." },
                    { t: "number",    code: `{"type":"number","value":30}`,   note: "A constant value (e.g. 70 for RSI overbought level)." },
                    { t: "binop",     code: `{"type":"binop","op":"+","left":{...},"right":{...}}`, note: "Operators: + − * / > < >= <=. Comparison returns 0/1." },
                    { t: "cross",     code: `{"type":"cross","direction":"above","fast":{...},"slow":{...}}`, note: "Returns 1 on the bar where fast crosses above/below slow." },
                  ].map(({ t, code, note }) => (
                    <div key={t} className="rounded-lg bg-slate-900/60 border border-slate-800 p-3 space-y-1.5">
                      <p className="font-semibold text-slate-300">{t}</p>
                      <code className="block text-[10px] text-slate-500 bg-slate-950/50 rounded p-1.5 overflow-x-auto whitespace-pre-wrap">{code}</code>
                      <p className="text-[10px] text-slate-500 leading-relaxed">{note}</p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          </div>
        )}

        {/* ── SAVED TAB ───────────────────────────────────────────────────── */}
        {activeTab === "saved" && (
          <div className="space-y-3">
            {saved.length === 0 ? (
              <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 p-12 text-center space-y-2">
                <p className="text-sm font-semibold text-slate-500">No saved indicators yet</p>
                <p className="text-xs text-slate-600">Build one in the Formula Builder tab and click "Save Indicator".</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {saved.map(ind => (
                  <SavedCard
                    key={ind.id}
                    ind={ind}
                    onDelete={handleDelete}
                    onLoad={handleLoadSaved}
                    onEvaluate={handleEvaluateSaved}
                  />
                ))}
              </div>
            )}
            {result && activeTab === "saved" && (
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3 mt-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Result — {symbol} · {timeframe}
                </h3>
                <ResultChart result={result} />
              </div>
            )}
          </div>
        )}

        {/* Disclaimer */}
        <p className="text-[10px] text-slate-700 text-center">
          Custom indicators are mathematical expressions applied to historical price data.
          They do not incorporate forward-looking information, fees, or slippage.
          Results are for educational and research purposes only and do not constitute investment advice.
        </p>
      </div>

      {/* ── Save modal ──────────────────────────────────────────────────────── */}
      {saveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4 shadow-2xl mx-4">
            <h3 className="text-base font-bold text-slate-100">Save Indicator</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Name *</label>
                <input
                  value={saveName}
                  onChange={e => setSaveName(e.target.value)}
                  placeholder="My RSI Strategy"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-slate-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Description (optional)</label>
                <input
                  value={saveDesc}
                  onChange={e => setSaveDesc(e.target.value)}
                  placeholder="Oversold RSI bounce signal"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-slate-500 focus:outline-none"
                />
              </div>
              <div className="rounded-lg bg-slate-800/60 px-3 py-2">
                <p className="text-[10px] text-slate-500 mb-1">Formula</p>
                <code className="text-[10px] text-blue-300">{formulaToText(parsedFormula()!)}</code>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setSaveModal(false)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition">
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !saveName.trim()}
                className="rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-4 py-2 text-sm font-semibold text-white transition"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      </div>
      </ProGate>
    </div>
  );
}
