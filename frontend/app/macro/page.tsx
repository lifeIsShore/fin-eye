"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  fetchMacroLatest,
  fetchMacroAdvanced,
  fetchMacroHistory,
  MacroAdvancedDto,
  MacroLatestDto,
  YieldCurvePoint,
  StressComponentDto,
} from "../../lib/api";
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import EventTimeline from "../../components/macro/EventTimeline";
import { AlertTriangle, Info, ChevronDown, ChevronUp, Globe } from "lucide-react";
import { PageBanner } from "../../components/ui/PageBanner";

// ─── Shared primitives ────────────────────────────────────────────────────────

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-900/50 p-4 ${className}`}>
      {children}
    </div>
  );
}

function Pill({ label, color }: { label: string; color: "green" | "amber" | "red" | "sky" | "slate" }) {
  const map = {
    green: "bg-emerald-900/50 text-emerald-400 border-emerald-800",
    amber: "bg-amber-900/50 text-amber-400 border-amber-800",
    red:   "bg-red-900/50 text-red-400 border-red-800",
    sky:   "bg-sky-900/50 text-sky-400 border-sky-800",
    slate: "bg-slate-800 text-slate-400 border-slate-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${map[color]}`}>
      {label}
    </span>
  );
}

// ─── Score Gauge ──────────────────────────────────────────────────────────────

function ScoreGauge({
  score,
  label,
  size = "lg",
  invert = false,
}: {
  score: number;
  label: string;
  size?: "sm" | "lg";
  invert?: boolean; // for stress index — higher = worse
}) {
  // Colour: for normal score, green=high. For inverted (stress), red=high.
  const pct = score;
  const good = invert ? pct < 30 : pct > 60;
  const bad  = invert ? pct > 60 : pct < 30;
  const color = good ? "text-emerald-400" : bad ? "text-red-400" : "text-amber-400";
  const barColor = good ? "bg-emerald-500" : bad ? "bg-red-500" : "bg-amber-500";

  return (
    <div className="space-y-2">
      <div className="flex items-end gap-2">
        <span className={`font-bold leading-none ${size === "lg" ? "text-5xl" : "text-3xl"} ${color}`}>
          {score.toFixed(1)}
        </span>
        <span className="text-slate-500 text-sm mb-1">/ 100</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-800">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className={`text-sm font-medium ${color}`}>{label}</span>
    </div>
  );
}

// ─── Core indicator card ──────────────────────────────────────────────────────

function IndicatorCard({
  title,
  value,
  date,
  interpretation,
}: {
  title: string;
  value: number | null;
  date: string | null;
  interpretation: string;
}) {
  const isWarning = interpretation.toLowerCase().includes("inverted") ||
    interpretation.toLowerCase().includes("high") ||
    interpretation.toLowerCase().includes("fear") ||
    interpretation.toLowerCase().includes("risk");

  return (
    <Card>
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1.5 text-2xl font-semibold text-slate-50">
        {value !== null ? value.toFixed(2) : "—"}
      </p>
      {date && <p className="mt-0.5 text-[11px] text-slate-600">{date}</p>}
      <p className={`mt-1.5 text-xs ${isWarning ? "text-amber-400" : "text-slate-400"}`}>
        {interpretation}
      </p>
    </Card>
  );
}

// ─── Yield Curve Chart ────────────────────────────────────────────────────────

function YieldCurveChart({ points }: { points: YieldCurvePoint[] }) {
  const data = points
    .filter(p => p.yield_pct !== null)
    .map(p => ({ tenor: p.tenor, yield: p.yield_pct as number }));

  if (data.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-slate-600">
        No yield data available yet — run a macro refresh.
      </div>
    );
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="yieldGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="tenor" stroke="#475569" fontSize={11} />
          <YAxis stroke="#475569" fontSize={11}
            tickFormatter={(v) => `${v.toFixed(1)}%`}
            domain={["auto", "auto"]} width={44}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px", fontSize: 12, color: "#f8fafc" }}
            formatter={(v: number) => [`${v.toFixed(2)}%`, "Yield"]}
          />
          <Area type="monotone" dataKey="yield" stroke="#38bdf8" strokeWidth={2}
            fill="url(#yieldGrad)" dot={{ fill: "#38bdf8", r: 4 }} activeDot={{ r: 5 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Recession Gauge ──────────────────────────────────────────────────────────

function RecessionGauge({
  probability,
  label,
  nber,
  drivers,
}: {
  probability: number;
  label: string;
  nber: boolean;
  drivers: string[];
}) {
  const color =
    label === "High"     ? "text-red-400" :
    label === "Elevated" ? "text-amber-400" : "text-emerald-400";
  const barColor =
    label === "High"     ? "bg-red-500" :
    label === "Elevated" ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="space-y-4">
      {nber && (
        <div className="flex items-center gap-2 rounded-lg bg-red-950/40 border border-red-700/40 px-3 py-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
          <span className="text-xs text-red-300 font-medium">NBER official recession is active</span>
        </div>
      )}

      <div className="space-y-1.5">
        <div className="flex items-end justify-between">
          <span className={`text-3xl font-bold ${color}`}>{probability.toFixed(1)}%</span>
          <Pill label={label} color={label === "High" ? "red" : label === "Elevated" ? "amber" : "green"} />
        </div>
        <div className="h-2 w-full rounded-full bg-slate-800">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${Math.min(100, probability)}%` }}
          />
        </div>
        <p className="text-[11px] text-slate-500">12-month estimated probability</p>
      </div>

      {drivers.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-slate-400">Signal drivers</p>
          {drivers.map((d, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-500">
              <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-slate-600 shrink-0" />
              {d}
            </div>
          ))}
        </div>
      )}

      <p className="text-[11px] text-slate-600 border-t border-slate-800 pt-2">
        Educational estimate only — not a professional economic forecast.
      </p>
    </div>
  );
}

// ─── Stress Index Breakdown ───────────────────────────────────────────────────

function StressBreakdown({ components }: { components: StressComponentDto[] }) {
  const visible = components.filter(c => c.contribution > 0);
  if (visible.length === 0) {
    return <p className="text-xs text-slate-600">No stress signals detected.</p>;
  }
  const max = Math.max(...visible.map(c => c.contribution));

  return (
    <div className="space-y-3">
      {visible.map((c) => {
        const pct = max > 0 ? (c.contribution / max) * 100 : 0;
        const high = c.contribution >= 15;
        return (
          <div key={c.name} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className={`font-medium ${high ? "text-red-400" : "text-slate-300"}`}>{c.name}</span>
              <span className={`font-mono ${high ? "text-red-400" : "text-slate-400"}`}>+{c.contribution.toFixed(1)}</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-800">
              <div
                className={`h-1.5 rounded-full ${high ? "bg-red-500" : "bg-amber-500"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-600">{c.description}</p>
          </div>
        );
      })}
    </div>
  );
}

// ─── History Sparkline ────────────────────────────────────────────────────────

function HistoryChart({
  indicatorName,
  color = "#38bdf8",
  unit = "",
}: {
  indicatorName: string;
  color?: string;
  unit?: string;
}) {
  const { data, isLoading } = useSWR(
    `macro-history-${indicatorName}`,
    () => fetchMacroHistory(indicatorName, 60),
  );

  if (isLoading) {
    return <div className="h-24 flex items-center justify-center text-xs text-slate-600">Loading…</div>;
  }
  if (!data || data.series.length === 0) {
    return <div className="h-24 flex items-center justify-center text-xs text-slate-600">No history yet</div>;
  }

  return (
    <div className="h-24 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data.series} margin={{ top: 2, right: 4, left: -24, bottom: 0 }}>
          <XAxis dataKey="date" hide />
          <YAxis domain={["auto", "auto"]} fontSize={10} stroke="#475569"
            tickFormatter={(v) => `${v.toFixed(1)}${unit}`} width={36}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px", fontSize: 11, color: "#f8fafc" }}
            formatter={(v: number) => [`${v.toFixed(2)}${unit}`, indicatorName]}
            labelFormatter={(l) => l}
          />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ─── Yield Curve Shape Badge ──────────────────────────────────────────────────

function YieldShapeBadge({ shape }: { shape: string }) {
  const map: Record<string, { color: "green" | "amber" | "red" | "sky" | "slate"; icon: string }> = {
    Normal:      { color: "green", icon: "↗" },
    Steep:       { color: "sky",   icon: "↑↑" },
    Flat:        { color: "amber", icon: "→" },
    Inverted:    { color: "red",   icon: "↘" },
    Humped:      { color: "amber", icon: "∩" },
    Unavailable: { color: "slate", icon: "—" },
  };
  const { color, icon } = map[shape] ?? { color: "slate", icon: "?" };
  return <Pill label={`${icon} ${shape}`} color={color} />;
}

// ─── Collapsible leading indicators ──────────────────────────────────────────

function LeadingPanel({ leading }: { leading: MacroAdvancedDto["leading_indicators"] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between">
        <SectionHeader title="Leading Indicators" subtitle="NFP & Industrial Production" />
        {open ? <ChevronUp className="h-4 w-4 text-slate-500" /> : <ChevronDown className="h-4 w-4 text-slate-500" />}
      </button>
      {open && (
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "NFP Level",      value: leading.nonfarm_payrolls_latest,     unit: "k",  decimals: 0 },
            { label: "NFP MoM Change", value: leading.nonfarm_payrolls_mom,        unit: "k",  decimals: 0 },
            { label: "Ind. Prod.",     value: leading.industrial_production_latest, unit: "",   decimals: 1 },
            { label: "IP YoY",         value: leading.industrial_production_yoy,   unit: "%",  decimals: 1 },
          ].map(({ label, value, unit, decimals }) => (
            <div key={label}>
              <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
              <p className={`mt-1 text-xl font-semibold ${
                value === null ? "text-slate-600"
                : value < 0 ? "text-red-400"
                : "text-slate-100"
              }`}>
                {value !== null ? `${value.toFixed(decimals)}${unit}` : "—"}
              </p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── FOMC Countdown ─────────────────────────────────────────────────────────

/** Published FOMC meeting dates (decision day = second day of meeting). */
const FOMC_DATES_2025_2026: string[] = [
  "2025-01-29",
  "2025-03-19",
  "2025-05-07",
  "2025-06-18",
  "2025-07-30",
  "2025-09-17",
  "2025-10-29",
  "2025-12-10",
  "2026-01-28",
  "2026-03-18",
  "2026-04-29",
  "2026-06-17",
  "2026-07-29",
  "2026-09-16",
  "2026-10-28",
  "2026-12-09",
];

function getNextFomcDate(): { date: Date; label: string; daysAway: number } | null {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  for (const ds of FOMC_DATES_2025_2026) {
    const d = new Date(ds + "T00:00:00");
    if (d >= today) {
      const daysAway = Math.round((d.getTime() - today.getTime()) / 86_400_000);
      const label = d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
      return { date: d, label, daysAway };
    }
  }
  return null;
}

function FomcCountdown() {
  const next = getNextFomcDate();
  if (!next) return null;

  const urgency =
    next.daysAway <= 3  ? { color: "text-rose-400",   bg: "bg-rose-950/30",   border: "border-rose-800/40",   dot: "bg-rose-400 animate-pulse" } :
    next.daysAway <= 14 ? { color: "text-amber-400",  bg: "bg-amber-950/30",  border: "border-amber-800/40",  dot: "bg-amber-400" } :
                          { color: "text-slate-300",   bg: "bg-slate-800/40",  border: "border-slate-700/40",  dot: "bg-slate-500" };

  return (
    <div className={`flex items-center gap-3 rounded-xl border ${urgency.bg} ${urgency.border} px-4 py-3`}>
      <div className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${urgency.dot}`} />
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Next FOMC Decision</p>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-sm font-bold ${urgency.color}`}>{next.label}</span>
          <span className="text-xs text-slate-500">
            {next.daysAway === 0
              ? "Today — decision expected"
              : next.daysAway === 1
              ? "Tomorrow"
              : `${next.daysAway} days away`}
          </span>
        </div>
      </div>
      <a
        href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        target="_blank"
        rel="noopener noreferrer"
        className="ml-auto flex-shrink-0 text-[10px] text-sky-500 hover:text-sky-400 transition-colors"
      >
        Fed calendar ↗
      </a>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const CORE_LABEL_MAP: Record<string, string> = {
  fed_funds_rate:      "Fed Funds Rate",
  unemployment_rate:   "Unemployment",
  yield_spread_10y_2y: "10Y–2Y Spread",
  cpi_yoy:             "CPI YoY",
  vix:                 "VIX",
};

const HISTORY_CARDS = [
  { name: "fed_funds_rate",      label: "Fed Funds Rate", color: "#f59e0b", unit: "%" },
  { name: "cpi_yoy",             label: "CPI YoY",        color: "#f87171", unit: "%" },
  { name: "yield_spread_10y_2y", label: "10Y–2Y Spread",  color: "#a78bfa", unit: "%" },
  { name: "vix",                 label: "VIX",            color: "#38bdf8", unit: "" },
];

export default function MacroPage() {
  const [view, setView] = useState<"basic" | "advanced">("basic");

  const { data: basicData, error: basicError, isLoading: basicLoading } =
    useSWR<MacroLatestDto>("macro-latest", fetchMacroLatest);

  const { data: advData, error: advError, isLoading: advLoading } =
    useSWR<MacroAdvancedDto>(view === "advanced" ? "macro-advanced" : null, fetchMacroAdvanced);

  const macroScore = basicData?.macro_score ?? null;
  const indicators = basicData?.data ?? {};
  const loading = view === "basic" ? basicLoading : advLoading;
  const error   = view === "basic" ? basicError   : advError;

  return (
    <div className="space-y-6">
      <PageBanner
        icon={<Globe className="h-5 w-5" />}
        title="Macro Intelligence"
        description="Real-time FRED indicators, yield curve shape, VIX regime, and recession probability."
        badge="Live"
        badgeColor="emerald"
      />

      {/* ── Page header ── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Macro Dashboard</h2>
          <p className="mt-1 text-sm text-slate-400 max-w-xl">
            Economic backdrop synthesis — rates, inflation, yield curve, labour market and volatility.
            Educational view only, not a trading signal.
          </p>
        </div>

        {/* View toggle */}
        <div className="flex gap-1 rounded-lg bg-slate-900 border border-slate-800 p-1 self-start">
          {(["basic", "advanced"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition capitalize ${
                view === v ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {v === "basic" ? "Overview" : "Advanced"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/30 p-4 text-sm text-red-300">
          Could not load macro data. Ensure the backend is running and indicators are refreshed
          (POST /api/v1/macro/refresh).
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && !basicData && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5 animate-pulse">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-slate-800/50" />
          ))}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* OVERVIEW VIEW                                                       */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {view === "basic" && basicData && (
        <div className="space-y-6">

          {/* FOMC countdown — Sprint 21 */}
          <FomcCountdown />

          {/* Yield curve inversion alert — Sprint 23 */}
          {(() => {
            const spread = basicData.data?.yield_spread_10y_2y?.value ?? null;
            if (spread === null || spread >= 0) return null;
            return (
              <div className="flex items-start gap-3 rounded-xl border border-amber-700/50 bg-amber-950/25 px-4 py-3">
                <span className="text-lg flex-shrink-0">⚠️</span>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-amber-300">
                    Yield Curve Inverted — 10Y–2Y Spread: {spread.toFixed(2)}%
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    An inverted yield curve (where short-term rates exceed long-term rates) has historically
                    preceded recessions by 6–18 months. This is an educational signal, not a guarantee of
                    economic contraction. Monitor closely alongside the recession probability gauge below.
                  </p>
                </div>
                <a
                  href="/macro"
                  onClick={(e) => { e.preventDefault(); }}
                  className="flex-shrink-0 text-[10px] text-amber-500 hover:text-amber-400 whitespace-nowrap transition-colors"
                >
                  See Advanced ↗
                </a>
              </div>
            );
          })()}

          {/* Macro score + core indicators */}
          <div className="grid gap-4 md:grid-cols-5">
            <Card className="md:col-span-2 flex flex-col justify-between">
              <SectionHeader title="Macro Score" subtitle="0 = max stress · 100 = ideal backdrop" />
              <div className="mt-4">
                {macroScore
                  ? <ScoreGauge score={macroScore.score} label={macroScore.label} />
                  : <p className="text-sm text-slate-500">No data — run a macro refresh.</p>
                }
              </div>
            </Card>

            <div className="md:col-span-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
              {Object.entries(indicators).slice(0, 6).map(([key, val]) => (
                <IndicatorCard
                  key={key}
                  title={CORE_LABEL_MAP[key] ?? key}
                  value={val.value}
                  date={val.date}
                  interpretation={val.interpretation}
                />
              ))}
            </div>
          </div>

          {/* History sparklines */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">60-Day History</p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {HISTORY_CARDS.map(({ name, label, color, unit }) => (
                <Card key={name}>
                  <p className="mb-2 text-xs font-medium text-slate-400">{label}</p>
                  <HistoryChart indicatorName={name} color={color} unit={unit} />
                </Card>
              ))}
            </div>
          </div>

          {/* Events */}
          <div className="border-t border-slate-800 pt-6">
            <Card>
              <EventTimeline />
            </Card>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* ADVANCED VIEW                                                       */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {view === "advanced" && advData && (
        <div className="space-y-6">

          {/* FOMC countdown */}
          <FomcCountdown />

          {/* Yield curve inversion alert — Sprint 23 */}
          {(() => {
            const spread = advData.yield_curve?.spread_10y_2y ?? null;
            if (spread === null || spread >= 0) return null;
            return (
              <div className="flex items-start gap-3 rounded-xl border border-amber-700/50 bg-amber-950/25 px-4 py-3">
                <span className="text-lg flex-shrink-0">⚠️</span>
                <div>
                  <p className="text-sm font-bold text-amber-300">
                    Yield Curve Inverted — 10Y–2Y Spread: {spread.toFixed(2)}%
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Historically preceded recessions by 6–18 months. Educational signal only.
                  </p>
                </div>
              </div>
            );
          })()}

          {/* Row 1: Macro score + Stress index */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <SectionHeader title="Macro Environment Score" subtitle="Higher = more supportive backdrop" />
              <div className="mt-4">
                {advData.core.macro_score
                  ? <ScoreGauge score={advData.core.macro_score.score} label={advData.core.macro_score.label} />
                  : <p className="text-sm text-slate-500">No data.</p>
                }
              </div>
            </Card>

            <Card>
              <SectionHeader title="Macro Stress Index" subtitle="Higher = more stress" />
              <div className="mt-4">
                <ScoreGauge
                  score={advData.stress_index.index}
                  label={advData.stress_index.label}
                  invert
                />
              </div>
            </Card>
          </div>

          {/* Row 2: Yield curve + Recession */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <div className="flex items-center justify-between mb-3">
                <SectionHeader title="Yield Curve" subtitle="Treasury CMT yields by tenor" />
                <YieldShapeBadge shape={advData.yield_curve.shape} />
              </div>
              <YieldCurveChart points={advData.yield_curve.points} />
              <p className="mt-3 text-xs text-slate-500">{advData.yield_curve.shape_description}</p>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                {advData.yield_curve.spread_10y_2y !== null && (
                  <span>
                    10Y–2Y spread:{" "}
                    <span className={advData.yield_curve.spread_10y_2y < 0 ? "text-red-400 font-mono" : "text-emerald-400 font-mono"}>
                      {advData.yield_curve.spread_10y_2y > 0 ? "+" : ""}{advData.yield_curve.spread_10y_2y.toFixed(3)}%
                    </span>
                  </span>
                )}
                {advData.yield_curve.spread_30y_2y !== null && (
                  <span>
                    30Y–2Y spread:{" "}
                    <span className="font-mono text-slate-300">
                      {advData.yield_curve.spread_30y_2y > 0 ? "+" : ""}{advData.yield_curve.spread_30y_2y.toFixed(3)}%
                    </span>
                  </span>
                )}
              </div>
            </Card>

            <Card>
              <SectionHeader
                title="Recession Probability"
                subtitle="Rule-based estimate — educational only"
              />
              <div className="mt-4">
                <RecessionGauge
                  probability={advData.recession.probability_pct}
                  label={advData.recession.label}
                  nber={advData.recession.nber_in_recession}
                  drivers={advData.recession.drivers}
                />
              </div>
            </Card>
          </div>

          {/* Row 3: Stress breakdown */}
          <Card>
            <SectionHeader
              title="Stress Index Breakdown"
              subtitle="How much each factor contributes to the current stress reading"
            />
            <div className="mt-4">
              <StressBreakdown components={advData.stress_index.components} />
            </div>
          </Card>

          {/* Row 4: Core indicators grid */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Core Indicators</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {Object.entries(advData.core.data).map(([key, val]) => (
                <IndicatorCard
                  key={key}
                  title={CORE_LABEL_MAP[key] ?? key}
                  value={val.value}
                  date={val.date}
                  interpretation={val.interpretation}
                />
              ))}
            </div>
          </div>

          {/* Row 5: Leading indicators */}
          <LeadingPanel leading={advData.leading_indicators} />

          {/* Row 6: History sparklines */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">60-Day History</p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {HISTORY_CARDS.map(({ name, label, color, unit }) => (
                <Card key={name}>
                  <p className="mb-2 text-xs font-medium text-slate-400">{label}</p>
                  <HistoryChart indicatorName={name} color={color} unit={unit} />
                </Card>
              ))}
            </div>
          </div>

          {/* Events */}
          <div className="border-t border-slate-800 pt-6">
            <Card>
              <EventTimeline />
            </Card>
          </div>
        </div>
      )}

      {/* Advanced loading state */}
      {view === "advanced" && advLoading && !advData && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-48 rounded-xl bg-slate-800/50" />
          ))}
        </div>
      )}

      {/* Disclaimer */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/20 px-4 py-3 flex gap-2">
        <Info className="h-4 w-4 shrink-0 mt-0.5 text-slate-600" />
        <p className="text-xs text-slate-600">
          All macro data is sourced from FRED (Federal Reserve Bank of St. Louis) and Yahoo Finance.
          Macro scores, recession probability, and the stress index are simplified educational models —
          not professional economic forecasts. Past macro regimes do not predict future outcomes.
        </p>
      </div>
    </div>
  );
}
