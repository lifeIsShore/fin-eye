"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchSectorRotation,
  type SectorRotationDto,
  type SectorDto,
} from "../../lib/api";

// ─── Constants ───────────────────────────────────────────────────────────────

const CYCLE_COLORS: Record<string, string> = {
  "Early Cycle": "#38bdf8",   // sky
  "Mid Cycle":   "#a78bfa",   // violet
  "Late Cycle":  "#fb923c",   // orange
  "Recession":   "#94a3b8",   // slate
};

const CYCLE_BG: Record<string, string> = {
  "Early Cycle": "bg-sky-950/40 border-sky-800/50 text-sky-400",
  "Mid Cycle":   "bg-violet-950/40 border-violet-800/50 text-violet-400",
  "Late Cycle":  "bg-orange-950/40 border-orange-800/50 text-orange-400",
  "Recession":   "bg-slate-800/60 border-slate-700/50 text-slate-400",
};

const RRG_COLORS: Record<string, string> = {
  Leading:   "#34d399",  // emerald
  Weakening: "#f59e0b",  // amber
  Lagging:   "#f87171",  // red
  Improving: "#60a5fa",  // blue
};

const PERIOD_LABELS = ["return_1w", "return_1m", "return_3m"] as const;
type Period = typeof PERIOD_LABELS[number];
const PERIOD_DISPLAY: Record<Period, string> = {
  return_1w: "1 Week",
  return_1m: "1 Month",
  return_3m: "3 Month",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(v: number | null, digits = 2): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

function retColor(v: number | null): string {
  if (v == null) return "text-slate-500";
  if (v > 3)  return "text-emerald-400 font-semibold";
  if (v > 0)  return "text-teal-400";
  if (v > -3) return "text-orange-400";
  return "text-rose-400 font-semibold";
}

function heatBg(rsScore: number): string {
  // rsScore 0–100; 50 = SPY. Generate a background colour.
  if (rsScore >= 75) return "#052e16";   // deep green
  if (rsScore >= 62) return "#14532d";
  if (rsScore >= 55) return "#166534";
  if (rsScore >= 50) return "#1a3a28";
  if (rsScore >= 45) return "#3b1a1a";
  if (rsScore >= 38) return "#5c1717";
  return "#450a0a";                      // deep red
}

function heatText(rsScore: number): string {
  if (rsScore >= 60) return "#86efac";
  if (rsScore >= 50) return "#d1fae5";
  if (rsScore >= 45) return "#fca5a5";
  return "#fca5a5";
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CyclePhaseBadge({ phase }: { phase: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${CYCLE_BG[phase] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
      {phase}
    </span>
  );
}

function RRGBadge({ quadrant }: { quadrant: string }) {
  const colors: Record<string, string> = {
    Leading:   "bg-emerald-950/40 border-emerald-800/50 text-emerald-400",
    Improving: "bg-blue-950/40 border-blue-800/50 text-blue-400",
    Weakening: "bg-amber-950/40 border-amber-800/50 text-amber-400",
    Lagging:   "bg-rose-950/40 border-rose-800/50 text-rose-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${colors[quadrant] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
      {quadrant}
    </span>
  );
}

// ─── Heatmap Grid ─────────────────────────────────────────────────────────────

function HeatmapGrid({
  sectors,
  period,
}: {
  sectors: SectorDto[];
  period: Period;
}) {
  const sorted = [...sectors].sort((a, b) => {
    const av = a[period] ?? -999;
    const bv = b[period] ?? -999;
    return bv - av;
  });

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {sorted.map((s) => {
        const ret = s[period];
        return (
          <div
            key={s.ticker}
            className="relative rounded-xl border border-slate-800 p-4 flex flex-col gap-2 transition-transform hover:scale-[1.02] cursor-default"
            style={{ background: heatBg(s.rs_score) }}
          >
            {/* Ticker + quadrant badge */}
            <div className="flex items-start justify-between gap-1">
              <span className="font-mono text-sm font-bold text-slate-100">{s.ticker}</span>
              <RRGBadge quadrant={s.rrg_quadrant} />
            </div>
            {/* Name */}
            <p className="text-[10px] text-slate-400 leading-tight">{s.name}</p>
            {/* Return */}
            <p
              className="text-2xl font-bold"
              style={{ color: ret != null && ret >= 0 ? "#86efac" : "#fca5a5" }}
            >
              {fmt(ret)}
            </p>
            {/* RS score bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[9px] text-slate-600">
                <span>vs SPY</span>
                <span>{s.rs_score.toFixed(0)}/100</span>
              </div>
              <div className="h-1 rounded-full bg-slate-800/60">
                <div
                  className="h-1 rounded-full"
                  style={{
                    width: `${s.rs_score}%`,
                    background: s.rs_score >= 50 ? "#34d399" : "#f87171",
                  }}
                />
              </div>
            </div>
            {/* Cycle badge */}
            <CyclePhaseBadge phase={s.cycle_phase} />
          </div>
        );
      })}
    </div>
  );
}

// ─── Table View ───────────────────────────────────────────────────────────────

function SectorTable({ sectors, spyRet1m }: { sectors: SectorDto[]; spyRet1m: number | null }) {
  const sorted = [...sectors].sort((a, b) => (b.rs_score ?? 50) - (a.rs_score ?? 50));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-800 text-slate-500 uppercase tracking-wider text-[10px]">
            <th className="pb-2 text-left">Sector</th>
            <th className="pb-2 text-right">1W</th>
            <th className="pb-2 text-right">1M</th>
            <th className="pb-2 text-right">3M</th>
            <th className="pb-2 text-right">RS vs SPY</th>
            <th className="pb-2 text-right">Momentum</th>
            <th className="pb-2 text-center">RRG</th>
            <th className="pb-2 text-left pl-3">Cycle Phase</th>
          </tr>
        </thead>
        <tbody>
          {spyRet1m != null && (
            <tr className="border-b border-slate-800/40 bg-slate-900/30">
              <td className="py-2 font-mono text-slate-400">SPY</td>
              <td className="py-2 text-right text-slate-400">—</td>
              <td className={`py-2 text-right ${retColor(spyRet1m)}`}>{fmt(spyRet1m)}</td>
              <td className="py-2 text-right text-slate-400">—</td>
              <td className="py-2 text-right text-slate-500 text-[10px]">Benchmark</td>
              <td className="py-2 text-right text-slate-500">—</td>
              <td className="py-2" />
              <td className="py-2 pl-3 text-slate-500">Benchmark</td>
            </tr>
          )}
          {sorted.map((s) => (
            <tr key={s.ticker} className="border-b border-slate-800/30 hover:bg-slate-900/30 transition-colors">
              <td className="py-2">
                <span className="font-mono text-slate-200 font-medium">{s.ticker}</span>
                <span className="ml-2 text-slate-500 text-[10px]">{s.name}</span>
              </td>
              <td className={`py-2 text-right ${retColor(s.return_1w)}`}>{fmt(s.return_1w)}</td>
              <td className={`py-2 text-right ${retColor(s.return_1m)}`}>{fmt(s.return_1m)}</td>
              <td className={`py-2 text-right ${retColor(s.return_3m)}`}>{fmt(s.return_3m)}</td>
              <td className="py-2 text-right">
                <span className={s.rs_1m != null && s.rs_1m >= 1 ? "text-emerald-400" : "text-rose-400"}>
                  {s.rs_1m != null ? (s.rs_1m >= 1 ? "+" : "") + ((s.rs_1m - 1) * 100).toFixed(1) + "%" : "—"}
                </span>
              </td>
              <td className="py-2 text-right">
                {s.momentum != null ? (
                  <span className={s.momentum >= 0 ? "text-teal-400" : "text-orange-400"}>
                    {s.momentum > 0 ? "↑" : "↓"} {Math.abs(s.momentum).toFixed(2)}
                  </span>
                ) : <span className="text-slate-600">—</span>}
              </td>
              <td className="py-2 text-center"><RRGBadge quadrant={s.rrg_quadrant} /></td>
              <td className="py-2 pl-3"><CyclePhaseBadge phase={s.cycle_phase} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── RRG Scatter Chart ────────────────────────────────────────────────────────

const RRG_TOOLTIP = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 shadow-xl text-xs space-y-1">
      <p className="font-semibold text-slate-100">{d.ticker} — {d.name}</p>
      <p className="text-slate-400">RS vs SPY: {d.rs_1m != null ? ((d.rs_1m - 1) * 100).toFixed(2) + "%" : "—"}</p>
      <p className="text-slate-400">Momentum: {d.momentum != null ? d.momentum.toFixed(3) : "—"}</p>
      <p className="text-slate-400">1M return: {fmt(d.return_1m)}</p>
      <p><RRGBadge quadrant={d.rrg_quadrant} /></p>
    </div>
  );
};

function RRGChart({ sectors }: { sectors: SectorDto[] }) {
  const data = sectors
    .filter((s) => s.rs_1m != null && s.momentum != null)
    .map((s) => ({
      ...s,
      x: parseFloat(((s.rs_1m! - 1) * 100).toFixed(3)),  // % deviation from 1.0
      y: parseFloat((s.momentum!).toFixed(3)),
    }));

  const quadrantLabels = [
    { x: 3, y: 0.5,   label: "LEADING",   color: "#34d399" },
    { x: -5, y: 0.5,  label: "IMPROVING", color: "#60a5fa" },
    { x: -5, y: -0.5, label: "LAGGING",   color: "#f87171" },
    { x: 3, y: -0.5,  label: "WEAKENING", color: "#f59e0b" },
  ];

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 24, bottom: 20, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          {/* Quadrant dividers */}
          <ReferenceLine x={0} stroke="#334155" strokeWidth={1.5} />
          <ReferenceLine y={0} stroke="#334155" strokeWidth={1.5} />

          <XAxis
            dataKey="x"
            type="number"
            domain={["auto", "auto"]}
            stroke="#475569"
            fontSize={10}
            tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            label={{ value: "RS vs SPY (%)", position: "insideBottom", offset: -10, fill: "#64748b", fontSize: 10 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            domain={["auto", "auto"]}
            stroke="#475569"
            fontSize={10}
            tickFormatter={(v) => v.toFixed(2)}
            label={{ value: "Momentum", angle: -90, position: "insideLeft", offset: 12, fill: "#64748b", fontSize: 10 }}
          />
          <ZAxis range={[200, 200]} />
          <Tooltip content={<RRG_TOOLTIP />} />

          <Scatter data={data} isAnimationActive={false}>
            {data.map((entry, i) => (
              <Cell key={i} fill={RRG_COLORS[entry.rrg_quadrant] ?? "#94a3b8"} fillOpacity={0.85} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Quadrant labels overlay (positioned outside chart) */}
      <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-center">
        {[
          { q: "Leading",   desc: "Strong RS + rising momentum", color: "text-emerald-400" },
          { q: "Improving", desc: "Weak RS but momentum turning", color: "text-blue-400" },
          { q: "Weakening", desc: "Strong RS but fading fast",    color: "text-amber-400" },
          { q: "Lagging",   desc: "Weak RS + falling momentum",   color: "text-rose-400" },
        ].map(({ q, desc, color }) => (
          <div key={q} className="rounded-lg border border-slate-800 bg-slate-900/40 px-2 py-1">
            <p className={`font-semibold ${color}`}>{q}</p>
            <p className="text-slate-600">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Cycle Phase Panel ────────────────────────────────────────────────────────

function CyclePhasePanel({
  scores,
  dominant,
  description,
}: {
  scores: Record<string, number>;
  dominant: string;
  description: string;
}) {
  const phases = ["Early Cycle", "Mid Cycle", "Late Cycle", "Recession"];
  const maxScore = Math.max(...Object.values(scores));

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Dominant Cycle Phase</h3>
          <p className="mt-0.5 text-xs text-slate-500">Based on leading sector performance</p>
        </div>
        <CyclePhaseBadge phase={dominant} />
      </div>

      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>

      <div className="space-y-3">
        {phases.map((phase) => {
          const score = scores[phase] ?? 50;
          const isActive = phase === dominant;
          const barColor = CYCLE_COLORS[phase] ?? "#94a3b8";
          const pct = maxScore > 0 ? (score / 100) * 100 : 0;
          return (
            <div key={phase} className={`space-y-1 rounded-lg p-3 transition-colors ${isActive ? "bg-slate-800/60 border border-slate-700/60" : ""}`}>
              <div className="flex items-center justify-between text-xs">
                <span className={`font-medium ${isActive ? "text-slate-100" : "text-slate-400"}`}>
                  {isActive && "▶ "}{phase}
                </span>
                <span className="font-mono text-slate-500">{score.toFixed(0)}/100</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-800">
                <div
                  className="h-1.5 rounded-full transition-all"
                  style={{ width: `${pct}%`, background: barColor }}
                />
              </div>
              <p className="text-[10px] text-slate-600">
                {phase === "Early Cycle"  && "XLF · XLRE · XLY"}
                {phase === "Mid Cycle"   && "XLK · XLI · XLC"}
                {phase === "Late Cycle"  && "XLE · XLB"}
                {phase === "Recession"   && "XLU · XLV · XLP"}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type View = "heatmap" | "table" | "rrg";

export default function SectorsPage() {
  const [view, setView] = useState<View>("heatmap");
  const [period, setPeriod] = useState<Period>("return_1m");

  const { data, error, isLoading } = useSWR<SectorRotationDto>(
    "sector-rotation",
    fetchSectorRotation,
    { refreshInterval: 900_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Sector Rotation</h2>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            11 SPDR sector ETF performance, relative strength vs SPY, and Relative Rotation
            Graph. Educational view — not investment advice.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Period selector */}
          <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-1">
            {PERIOD_LABELS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  period === p ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {PERIOD_DISPLAY[p]}
              </button>
            ))}
          </div>
          {/* View toggle */}
          <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-1">
            {(["heatmap", "table", "rrg"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors capitalize ${
                  view === v ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {v === "rrg" ? "RRG" : v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {isLoading && !data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 animate-pulse">
          {Array.from({ length: 11 }).map((_, i) => (
            <div key={i} className="h-36 rounded-xl bg-slate-800/50" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && !data && (
        <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 px-5 py-4 text-sm text-rose-400">
          <strong>Could not load sector data.</strong> {error.message}
        </div>
      )}

      {/* Content */}
      {data && (
        <div className="space-y-6">
          {/* SPY benchmark strip */}
          <div className="flex flex-wrap gap-4 rounded-xl border border-slate-800 bg-slate-900/40 px-5 py-3 text-xs">
            <span className="text-slate-500 font-medium">SPY Benchmark</span>
            {[
              { label: "1W",  v: data.spy_return_1w },
              { label: "1M",  v: data.spy_return_1m },
              { label: "3M",  v: data.spy_return_3m },
            ].map(({ label, v }) => (
              <span key={label} className="flex gap-1.5 items-center">
                <span className="text-slate-600">{label}</span>
                <span className={retColor(v ?? null)}>{fmt(v ?? null)}</span>
              </span>
            ))}
            <span className="ml-auto text-slate-600 text-[10px]">
              Data 15-min delayed · 15-min cache
            </span>
          </div>

          {/* Main layout: left = view, right = cycle panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">

              {view === "heatmap" && (
                <section>
                  <p className="mb-3 text-xs text-slate-500 uppercase tracking-wide font-medium">
                    Sorted by {PERIOD_DISPLAY[period]} performance — colour by RS vs SPY
                  </p>
                  <HeatmapGrid sectors={data.sectors} period={period} />
                </section>
              )}

              {view === "table" && (
                <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  <SectorTable sectors={data.sectors} spyRet1m={data.spy_return_1m} />
                </section>
              )}

              {view === "rrg" && (
                <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">
                      Relative Rotation Graph (RRG)
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      x-axis: relative strength vs SPY · y-axis: RS momentum.
                      Rotation typically moves clockwise through quadrants.
                    </p>
                  </div>
                  <RRGChart sectors={data.sectors} />
                </section>
              )}
            </div>

            {/* Cycle Phase Panel — always visible */}
            <div className="lg:col-span-1">
              <CyclePhasePanel
                scores={data.cycle_phase_scores}
                dominant={data.dominant_cycle_phase}
                description={data.dominant_cycle_description}
              />
            </div>
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-slate-600 border-t border-slate-800/50 pt-4 leading-relaxed">
            {data.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
