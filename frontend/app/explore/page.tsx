"use client";

/**
 * /explore — Market Explore page (Sprint 13)
 *
 * A top-level discovery hub surfacing the most useful cross-market signals
 * in one place:
 *   1. Sector Rotation Heatmap (reuses /sectors data — no new API needed)
 *   2. Relative Rotation Graph (RRG)
 *   3. Quick-links to all deep-signal pages
 *
 * The heatmap and RRG are embedded inline so users don't have to navigate
 * to /sectors. A "Full Analysis →" link takes them there for the full page.
 */

import { useState, useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchSectorRotation,
  fetchMacroLatest,
  fetchWatchlist,
  type SectorRotationDto,
  type SectorDto,
  type MacroLatestDto,
} from "../../lib/api";
import {
  PieChart as PieIcon, TrendingUp, Eye, TrendingDown,
  Calendar, Activity, Landmark, Globe, Zap, BarChart2,
  ArrowRight, RefreshCw, TrendingDown as ChevronDown2,
  Trophy,
} from "lucide-react";
import GradeBadge from "../../components/GradeBadge";
import { useSymbol } from "../../lib/symbolContext";
import { useRouter } from "next/navigation";

const API_BASE_EXPLORE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface LeaderEntry {
  symbol: string;
  gas_score: number;
  signal_grade: string | null;
  signal_grade_score: number | null;
  signal_tradeable: boolean | null;
  weather_label: string;
  regime: string;
  component_scores: { technical?: number; sentiment?: number; macro?: number };
}

async function fetchLeaderboard(symbols: string[]): Promise<LeaderEntry[]> {
  if (symbols.length === 0) return [];
  try {
    const res = await fetch(`${API_BASE_EXPLORE}/api/v1/admin/gas/snapshots/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols }),
      cache: "no-store",
    });
    if (!res.ok) return [];
    const list: LeaderEntry[] = await res.json();
    return list;
  } catch { return []; }
}

// ── Constants ─────────────────────────────────────────────────────────────────

const RRG_COLORS: Record<string, string> = {
  Leading:   "#34d399",
  Weakening: "#f59e0b",
  Lagging:   "#f87171",
  Improving: "#60a5fa",
};

function heatBg(rs: number): string {
  if (rs >= 75) return "#052e16";
  if (rs >= 62) return "#14532d";
  if (rs >= 55) return "#166534";
  if (rs >= 50) return "#1a3a28";
  if (rs >= 45) return "#3b1a1a";
  if (rs >= 38) return "#5c1717";
  return "#450a0a";
}

function fmt(v: number | null, d = 1): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(d)}%`;
}

function retColor(v: number | null): string {
  if (v == null) return "text-slate-500";
  if (v > 3) return "text-emerald-400 font-semibold";
  if (v > 0) return "text-teal-400";
  if (v > -3) return "text-orange-400";
  return "text-rose-400 font-semibold";
}

const CYCLE_BG: Record<string, string> = {
  "Early Cycle": "bg-sky-950/40 border-sky-800/50 text-sky-400",
  "Mid Cycle":   "bg-violet-950/40 border-violet-800/50 text-violet-400",
  "Late Cycle":  "bg-orange-950/40 border-orange-800/50 text-orange-400",
  "Recession":   "bg-slate-800/60 border-slate-700/50 text-slate-400",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function CycleBadge({ phase }: { phase: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${CYCLE_BG[phase] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
      {phase}
    </span>
  );
}

function RRGBadge({ q }: { q: string }) {
  const cls: Record<string, string> = {
    Leading:   "bg-emerald-950/40 border-emerald-800/50 text-emerald-400",
    Improving: "bg-blue-950/40 border-blue-800/50 text-blue-400",
    Weakening: "bg-amber-950/40 border-amber-800/50 text-amber-400",
    Lagging:   "bg-rose-950/40 border-rose-800/50 text-rose-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${cls[q] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
      {q}
    </span>
  );
}

// ── Heatmap ───────────────────────────────────────────────────────────────────

function SectorHeatmap({ sectors }: { sectors: SectorDto[] }) {
  const sorted = [...sectors].sort((a, b) => (b.return_1m ?? -99) - (a.return_1m ?? -99));
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
      {sorted.map((s) => (
        <div
          key={s.ticker}
          className="relative rounded-xl border border-slate-800/60 p-3 flex flex-col gap-1.5 transition-transform hover:scale-[1.02] cursor-default"
          style={{ background: heatBg(s.rs_score) }}
        >
          <div className="flex items-start justify-between gap-1">
            <span className="font-mono text-xs font-bold text-slate-100">{s.ticker}</span>
            <RRGBadge q={s.rrg_quadrant} />
          </div>
          <p className="text-[9px] text-slate-400 leading-tight line-clamp-1">{s.name}</p>
          <p className={`text-lg font-bold leading-none ${s.return_1m != null && s.return_1m >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
            {fmt(s.return_1m)}
          </p>
          <div className="h-1 rounded-full bg-slate-800/60 overflow-hidden">
            <div className="h-full rounded-full" style={{
              width: `${s.rs_score}%`,
              background: s.rs_score >= 50 ? "#34d399" : "#f87171",
            }} />
          </div>
          <CycleBadge phase={s.cycle_phase} />
        </div>
      ))}
    </div>
  );
}

// ── Mini RRG Chart ─────────────────────────────────────────────────────────────

const RRGTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 shadow-xl text-xs space-y-0.5">
      <p className="font-bold text-slate-100">{d.ticker}</p>
      <p className="text-slate-400">{d.name}</p>
      <p className="text-slate-400">1M: <span className={retColor(d.return_1m)}>{fmt(d.return_1m)}</span></p>
      <RRGBadge q={d.rrg_quadrant} />
    </div>
  );
};

function MiniRRG({ sectors }: { sectors: SectorDto[] }) {
  const data = sectors
    .filter((s) => s.rs_1m != null && s.momentum != null)
    .map((s) => ({
      ...s,
      x: parseFloat(((s.rs_1m! - 1) * 100).toFixed(2)),
      y: parseFloat((s.momentum!).toFixed(3)),
    }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 16, bottom: 24, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <ReferenceLine x={0} stroke="#334155" strokeWidth={1.5} />
          <ReferenceLine y={0} stroke="#334155" strokeWidth={1.5} />
          <XAxis dataKey="x" type="number" domain={["auto", "auto"]} stroke="#475569" fontSize={10}
            tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            label={{ value: "RS vs SPY", position: "insideBottom", offset: -12, fill: "#64748b", fontSize: 10 }} />
          <YAxis dataKey="y" type="number" domain={["auto", "auto"]} stroke="#475569" fontSize={10}
            tickFormatter={(v) => v.toFixed(2)}
            label={{ value: "Momentum", angle: -90, position: "insideLeft", offset: 12, fill: "#64748b", fontSize: 10 }} />
          <ZAxis range={[180, 180]} />
          <Tooltip content={<RRGTooltip />} />
          <Scatter data={data} isAnimationActive={false}>
            {data.map((e, i) => (
              <Cell key={i} fill={RRG_COLORS[e.rrg_quadrant] ?? "#94a3b8"} fillOpacity={0.85} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Grade Leaderboard ──────────────────────────────────────────────────────────

const GRADE_ORDER_EXPLORE = ["A+", "A", "B", "C", "D", "F"];

function GradeLeaderboard() {
  const router = useRouter();
  const { setSymbol } = useSymbol();

  const { data: watchlist } = useSWR("watchlist-explore", fetchWatchlist, {
    revalidateOnFocus: false, shouldRetryOnError: false,
  });
  const symbols = (watchlist ?? []).map((w) => w.symbol);

  const { data: entries, isLoading, mutate } = useSWR(
    symbols.length > 0 ? ["leaderboard", ...symbols] : null,
    () => fetchLeaderboard(symbols),
    { refreshInterval: 5 * 60_000, revalidateOnFocus: false },
  );

  const ranked = (entries ?? [])
    .filter((e) => e.signal_grade)
    .sort((a, b) => {
      const ra = GRADE_ORDER_EXPLORE.indexOf(a.signal_grade ?? "F");
      const rb = GRADE_ORDER_EXPLORE.indexOf(b.signal_grade ?? "F");
      if (ra !== rb) return ra - rb;
      return b.gas_score - a.gas_score;
    });

  const handleClick = (symbol: string) => {
    setSymbol(symbol);
    router.push("/");
  };

  if (!watchlist || symbols.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-5 py-8 text-center">
        <Trophy className="h-6 w-6 text-slate-600 mx-auto mb-2" />
        <p className="text-sm text-slate-500">Add symbols to your watchlist to see them ranked here.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1,2,3,4].map((i) => (
          <div key={i} className="h-12 rounded-xl bg-slate-800/50" />
        ))}
      </div>
    );
  }

  if (ranked.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/30 px-5 py-6 text-center">
        <p className="text-sm text-slate-500">No grade data yet. Run GAS precompute for your watchlist symbols.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {ranked.map((entry, i) => {
        const gasColor = entry.gas_score >= 65 ? "text-emerald-400" : entry.gas_score >= 40 ? "text-amber-400" : "text-rose-400";
        const isTop3 = i < 3;
        const medals = ["🥇", "🥈", "🥉"];
        return (
          <button
            key={entry.symbol}
            onClick={() => handleClick(entry.symbol)}
            className={`w-full flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all hover:bg-slate-900/70 ${
              isTop3 ? "border-slate-700 bg-slate-900/50" : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
            }`}
          >
            {/* Rank */}
            <span className="w-6 text-center flex-shrink-0">
              {i < 3 ? (
                <span className="text-base">{medals[i]}</span>
              ) : (
                <span className="text-xs text-slate-600 font-mono tabular-nums">{i + 1}</span>
              )}
            </span>

            {/* Symbol */}
            <span className="font-mono font-bold text-sm text-slate-100 w-16 flex-shrink-0">{entry.symbol}</span>

            {/* Grade badge */}
            <GradeBadge grade={entry.signal_grade} score={entry.signal_grade_score} size="sm" />

            {/* Weather label */}
            <span className="text-xs text-slate-500 hidden sm:block truncate flex-1">{entry.weather_label}</span>

            {/* Component dots */}
            <div className="hidden md:flex items-center gap-1.5 flex-shrink-0">
              {["T", "S", "M"].map((lbl, ci) => {
                const val = ci === 0 ? entry.component_scores?.technical
                  : ci === 1 ? entry.component_scores?.sentiment
                  : entry.component_scores?.macro;
                const dotColor = val == null ? "bg-slate-700" : val >= 65 ? "bg-emerald-500" : val >= 40 ? "bg-amber-500" : "bg-rose-500";
                return (
                  <div key={lbl} className="flex items-center gap-0.5" title={`${lbl}: ${val?.toFixed(0) ?? "—"}`}>
                    <div className={`h-2 w-2 rounded-full ${dotColor}`} />
                    <span className="text-[9px] text-slate-600">{lbl}</span>
                  </div>
                );
              })}
            </div>

            {/* GAS score */}
            <span className={`font-mono font-black text-sm tabular-nums flex-shrink-0 w-8 text-right ${gasColor}`}>
              {entry.gas_score.toFixed(0)}
            </span>

            {/* Arrow */}
            <ArrowRight className="h-3.5 w-3.5 text-slate-700 flex-shrink-0" />
          </button>
        );
      })}
      <div className="flex justify-end pt-1">
        <button onClick={() => mutate()} className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors">
          ↻ Refresh rankings
        </button>
      </div>
    </div>
  );
}

// ── Quick-link cards ───────────────────────────────────────────────────────────

const SIGNAL_PAGES = [
  { href: "/sectors",      icon: PieIcon,    label: "Sector Rotation",   desc: "Heatmap, RRG, cycle phase",  color: "text-violet-400" },
  { href: "/macro",        icon: Globe,      label: "Macro Intel",       desc: "FRED composite, yield curve", color: "text-sky-400"    },
  { href: "/fed-policy",   icon: Landmark,   label: "Fed Policy",        desc: "Rate path, dot plot, QT",    color: "text-amber-400"  },
  { href: "/options",      icon: Activity,   label: "Options Flow",      desc: "PCR, skew, max pain",        color: "text-rose-400"   },
  { href: "/insiders",     icon: Eye,        label: "Insider Activity",  desc: "SEC Form 4 sentiment",       color: "text-emerald-400" },
  { href: "/shorts",       icon: TrendingDown, label: "Short Interest",  desc: "Float%, borrow rate, squeeze", color: "text-orange-400" },
  { href: "/earnings",     icon: Calendar,   label: "Earnings Calendar", desc: "Beat/miss history, EPS est.", color: "text-teal-400"   },
  { href: "/sentiment-adv", icon: Zap,       label: "Adv. Sentiment",   desc: "Google Trends, StockTwits",  color: "text-indigo-400" },
];

// ── Main Page ─────────────────────────────────────────────────────────────────

// -- Macro Heat Strip (Sprint 18) --

const MACRO_TILES: {
  key: keyof MacroLatestDto["data"];
  label: string;
  format: (v: number) => string;
}[] = [
  { key: "fed_funds_rate",      label: "Fed Funds Rate",  format: (v) => `${v.toFixed(2)}%`  },
  { key: "unemployment_rate",   label: "Unemployment",   format: (v) => `${v.toFixed(1)}%`  },
  { key: "yield_spread_10y_2y", label: "Yield Spread",   format: (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%` },
  { key: "cpi_yoy",             label: "CPI YoY",        format: (v) => `${v.toFixed(1)}%`  },
  { key: "vix",                 label: "VIX",            format: (v) => v.toFixed(1)         },
];

function macroTileColor(key: string, v: number | null): string {
  if (v === null) return "text-slate-500";
  switch (key) {
    case "fed_funds_rate":      return v > 4.5 ? "text-rose-400" : v < 2 ? "text-emerald-400" : "text-amber-400";
    case "unemployment_rate":   return v > 5.5 ? "text-rose-400" : v < 4 ? "text-emerald-400" : "text-amber-400";
    case "yield_spread_10y_2y": return v < 0 ? "text-rose-400" : v > 0.5 ? "text-emerald-400" : "text-amber-400";
    case "cpi_yoy":             return v > 3.5 ? "text-rose-400" : v < 2 ? "text-emerald-400" : "text-amber-400";
    case "vix":                 return v > 30 ? "text-rose-400" : v > 20 ? "text-amber-400" : "text-emerald-400";
    default:                   return "text-slate-300";
  }
}

function macroTileBorder(key: string, v: number | null): string {
  if (v === null) return "border-slate-800";
  switch (key) {
    case "fed_funds_rate":      return v > 4.5 ? "border-rose-900/50" : v < 2 ? "border-emerald-900/50" : "border-amber-900/50";
    case "unemployment_rate":   return v > 5.5 ? "border-rose-900/50" : v < 4 ? "border-emerald-900/50" : "border-amber-900/50";
    case "yield_spread_10y_2y": return v < 0 ? "border-rose-900/50" : v > 0.5 ? "border-emerald-900/50" : "border-amber-900/50";
    case "cpi_yoy":             return v > 3.5 ? "border-rose-900/50" : v < 2 ? "border-emerald-900/50" : "border-amber-900/50";
    case "vix":                 return v > 30 ? "border-rose-900/50" : v > 20 ? "border-amber-900/50" : "border-emerald-900/50";
    default:                   return "border-slate-800";
  }
}

function MacroHeatStrip() {
  const { data, isLoading, error } = useSWR<MacroLatestDto>(
    "macro-latest-explore",
    () => fetchMacroLatest(),
    { refreshInterval: 900_000, shouldRetryOnError: false },
  );

  const scoreLabel = data?.macro_score?.label ?? null;
  const scoreLabelColor =
    scoreLabel === "Supportive" ? "text-emerald-400"
    : scoreLabel === "Stressed"  ? "text-rose-400"
    : "text-amber-400";

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-100">Macro Pulse</h2>
          <p className="text-xs text-slate-500 mt-0.5">FRED indicators &middot; click any tile for full macro view</p>
        </div>
        {scoreLabel && (
          <div className="text-right">
            <p className="text-[10px] text-slate-600 uppercase tracking-wider">Macro Score</p>
            <p className={`text-sm font-bold ${scoreLabelColor}`}>{scoreLabel}</p>
          </div>
        )}
      </div>

      {isLoading && !data && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 animate-pulse">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-slate-800/50" />
          ))}
        </div>
      )}

      {error && !data && (
        <p className="text-xs text-slate-500 italic">Macro data unavailable — check backend.</p>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {MACRO_TILES.map(({ key, label, format }) => {
              const indicator = data.data[key];
              const v         = indicator?.value ?? null;
              const interp    = indicator?.interpretation ?? "";
              const valColor  = macroTileColor(key, v);
              const border    = macroTileBorder(key, v);

              return (
                <Link
                  key={key}
                  href="/macro"
                  className={`group rounded-xl border ${border} bg-slate-900/50 p-3 hover:bg-slate-900/80 hover:border-slate-600 transition-all`}
                >
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">{label}</p>
                  {v !== null ? (
                    <p className={`text-xl font-bold font-mono ${valColor}`}>{format(v)}</p>
                  ) : (
                    <p className="text-xl font-bold text-slate-600">&mdash;</p>
                  )}
                  <p className="text-[10px] text-slate-600 mt-1 leading-tight line-clamp-2">{interp}</p>
                  <div className="flex items-center gap-0.5 text-[9px] text-slate-600 group-hover:text-sky-400 mt-2 transition-colors">
                    Full macro <ArrowRight className="h-2.5 w-2.5" />
                  </div>
                </Link>
              );
            })}
          </div>

          {data.macro_score && (
            <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/30 px-4 py-2.5">
              <div className="flex-1">
                <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                  <span>Composite Macro Score</span>
                  <span className={`font-semibold ${scoreLabelColor}`}>
                    {data.macro_score.score.toFixed(0)}/100 &middot; {data.macro_score.label}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      data.macro_score.label === "Supportive" ? "bg-emerald-500"
                      : data.macro_score.label === "Stressed"  ? "bg-rose-500"
                      : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.min(data.macro_score.score, 100)}%` }}
                  />
                </div>
              </div>
              <Link href="/macro" className="text-[10px] text-sky-400 hover:text-sky-300 font-medium whitespace-nowrap flex items-center gap-0.5 transition-colors">
                Full Analysis <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default function ExplorePage() {
  const [tab, setTab] = useState<"heatmap" | "rrg">("heatmap");

  const { data, isLoading, error, mutate } = useSWR<SectorRotationDto>(
    "sector-rotation",
    fetchSectorRotation,
    { refreshInterval: 900_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const dominant = data?.dominant_cycle_phase ?? "Unknown";
  const cycleColor = CYCLE_BG[dominant]?.split(" ")[2] ?? "text-slate-400";

  return (
    <div className="space-y-8 max-w-6xl">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-100">
            Market Explorer
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Cross-market sector rotation, regime signals, and deep-signal quick links.
          </p>
        </div>
        {data && (
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right">
              <p className="text-[10px] text-slate-600 uppercase tracking-wider">Dominant Cycle</p>
              <p className={`text-sm font-bold ${cycleColor}`}>{dominant}</p>
            </div>
            <button onClick={() => mutate()} className="p-1.5 rounded-lg text-slate-600 hover:text-slate-400 hover:bg-slate-800 transition-colors">
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        )}
      </div>

      {/* ── SPY benchmark strip ─────────────────────────────────────────── */}
      {data && (
        <div className="flex flex-wrap gap-6 rounded-xl border border-slate-800 bg-slate-900/40 px-5 py-3 text-xs">
          <span className="text-slate-500 font-medium">SPY Benchmark</span>
          {[
            { label: "1W", v: data.spy_return_1w },
            { label: "1M", v: data.spy_return_1m },
            { label: "3M", v: data.spy_return_3m },
          ].map(({ label, v }) => (
            <span key={label} className="flex gap-1.5 items-center">
              <span className="text-slate-600">{label}</span>
              <span className={retColor(v ?? null)}>{fmt(v ?? null)}</span>
            </span>
          ))}
          <Link href="/sectors" className="ml-auto flex items-center gap-1 text-sky-400 hover:text-sky-300 font-medium text-[10px] transition-colors">
            Full Sector Analysis <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      )}

      {/* ── Sector view: Heatmap + RRG ────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-100">Sector Rotation</h2>
          <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900 p-1">
            {(["heatmap", "rrg"] as const).map((v) => (
              <button key={v} onClick={() => setTab(v)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  tab === v ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                }`}>
                {v === "rrg" ? "RRG" : "Heatmap"}
              </button>
            ))}
          </div>
        </div>

        {isLoading && !data && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 animate-pulse">
            {Array.from({ length: 11 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-slate-800/50" />
            ))}
          </div>
        )}

        {error && !data && (
          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 px-4 py-3 text-sm text-rose-400">
            Could not load sector data. {error.message}
          </div>
        )}

        {data && tab === "heatmap" && (
          <div className="space-y-2">
            <p className="text-xs text-slate-600">1-month return vs SPY — colour by relative strength</p>
            <SectorHeatmap sectors={data.sectors} />
          </div>
        )}

        {data && tab === "rrg" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
            <div>
              <p className="text-sm font-semibold text-slate-100">Relative Rotation Graph</p>
              <p className="text-xs text-slate-500 mt-0.5">
                x = RS vs SPY · y = momentum · rotation moves clockwise
              </p>
            </div>
            <MiniRRG sectors={data.sectors} />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
              {[
                { q: "Leading",   desc: "Strong RS + rising",   color: "text-emerald-400" },
                { q: "Improving", desc: "Weak RS, turning up",  color: "text-blue-400"    },
                { q: "Weakening", desc: "Strong RS, fading",    color: "text-amber-400"   },
                { q: "Lagging",   desc: "Weak RS + falling",    color: "text-rose-400"    },
              ].map(({ q, desc, color }) => (
                <div key={q} className="rounded-lg border border-slate-800 bg-slate-900/40 px-2 py-1.5">
                  <p className={`font-semibold ${color}`}>{q}</p>
                  <p className="text-slate-600">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Deep signal quick-links ──────────────────────────────────────── */}
      {/* Macro Heat Strip -- Sprint 18 */}
      <MacroHeatStrip />

      {/* Grade Leaderboard — Sprint 23 */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-400" />
              Signal Grade Leaderboard
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Your watchlist ranked by signal grade (A+ → F) then GAS score. Click to open on the dashboard.
            </p>
          </div>
        </div>
        <GradeLeaderboard />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-100">Deep Signal Pages</h2>
          <span className="text-xs text-slate-600">{SIGNAL_PAGES.length} modules</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SIGNAL_PAGES.map(({ href, icon: Icon, label, desc, color }) => (
            <Link
              key={href}
              href={href}
              className="group flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/70 p-4 transition-all"
            >
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800 border border-slate-700 group-hover:border-slate-600 transition-colors">
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <span className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors">
                  {label}
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
              <div className="flex items-center gap-1 text-[10px] text-slate-600 group-hover:text-sky-400 transition-colors mt-auto pt-1">
                Open <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      <p className="text-[10px] text-slate-700 border-t border-slate-800/50 pt-4">
        Data is for educational purposes only and does not constitute investment advice.
        Sector data refreshes every 15 minutes.
      </p>
    </div>
  );
}
