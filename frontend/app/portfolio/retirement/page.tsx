"use client";

import { useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { AlertTriangle, Info, TrendingDown } from "lucide-react";
import ProGate from "@/components/ProGate";

// ─── Historical S&P 500 annual returns (approximate, nominal) ─────────────────
const SP500_ANNUAL: Record<number, number> = {
  1990: -3.1, 1991: 30.5, 1992: 7.6, 1993: 10.1, 1994: 1.3,
  1995: 37.6, 1996: 23.0, 1997: 33.4, 1998: 28.6, 1999: 21.0,
  2000: -9.1, 2001: -11.9, 2002: -22.1, 2003: 28.7, 2004: 10.9,
  2005: 4.9, 2006: 15.8, 2007: 5.5, 2008: -37.0, 2009: 26.5,
  2010: 15.1, 2011: 2.1, 2012: 16.0, 2013: 32.4, 2014: 13.7,
  2015: 1.4, 2016: 12.0, 2017: 21.8, 2018: -4.4, 2019: 31.5,
  2020: 18.4, 2021: 28.7, 2022: -18.1, 2023: 26.3, 2024: 23.3,
};

const SCENARIOS = [
  { label: "2000 Dot-com Crash",  startYear: 2000, color: "#f87171", dashed: false },
  { label: "2008 Financial Crisis", startYear: 2008, color: "#fb923c", dashed: false },
  { label: "2020 COVID Crash",    startYear: 2020, color: "#facc15", dashed: false },
  { label: "1990 Baseline",       startYear: 1990, color: "#34d399", dashed: true  },
];

// ─── Simulate portfolio ───────────────────────────────────────────────────────

interface SimYear {
  year: number; // sequential starting from 1
  [scenario: string]: number;
}

function simulateAll(
  portfolio: number,
  withdrawal: number,
  years: number,
): SimYear[] {
  const rows: SimYear[] = [];

  for (let y = 0; y < years; y++) {
    const row: SimYear = { year: y };
    for (const s of SCENARIOS) {
      const calYear = s.startYear + y;
      const ret = (SP500_ANNUAL[calYear] ?? 7.0) / 100; // fallback to 7% estimate

      // Carry over or use portfolio as starting point
      const prev = y === 0 ? portfolio : (rows[y - 1][s.label] ?? 0);
      const afterWithdrawal = Math.max(0, prev - withdrawal);
      const next = afterWithdrawal <= 0 ? 0 : afterWithdrawal * (1 + ret);
      row[s.label] = Math.round(next);
    }
    rows.push(row);
  }
  return rows;
}

function findDepletionYear(data: SimYear[], label: string): number | null {
  for (const d of data) {
    if ((d[label] ?? 1) <= 0) return d.year + 1;
  }
  return null;
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function fmt(v: number, currency: string): string {
  return new Intl.NumberFormat("en-DE", { style: "currency", currency, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v);
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RetirementRiskPage() {
  const [portfolio, setPortfolio] = useState(500_000);
  const [withdrawal, setWithdrawal] = useState(20_000);
  const [years, setYears] = useState(30);
  const [currency, setCurrency] = useState("EUR");

  const data = useMemo(() => simulateAll(portfolio, withdrawal, years), [portfolio, withdrawal, years]);

  const withdrawalRate = portfolio > 0 ? ((withdrawal / portfolio) * 100).toFixed(1) : "0";
  const isHighRate = parseFloat(withdrawalRate) > 4;

  return (
    <ProGate feature="Sequence of Returns Visualiser">
      <div className="min-h-screen bg-slate-950 text-slate-200">
        <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">

          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
              <TrendingDown className="h-6 w-6 text-rose-400" />
              Sequence of Returns Risk Visualiser
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              See how retiring into different market environments affects portfolio longevity.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* ── Inputs ────────────────────────────────────────────────────── */}
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Simulation Inputs</p>

                {/* Portfolio size */}
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-slate-400">Portfolio Size</label>
                    <span className="text-sm font-bold text-slate-200">{fmt(portfolio, currency)}</span>
                  </div>
                  <input
                    type="range" min={50_000} max={5_000_000} step={10_000}
                    value={portfolio}
                    onChange={e => setPortfolio(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
                    <span>50K</span><span>5M</span>
                  </div>
                </div>

                {/* Annual withdrawal */}
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-slate-400">Annual Withdrawal</label>
                    <span className="text-sm font-bold text-slate-200">{fmt(withdrawal, currency)}</span>
                  </div>
                  <input
                    type="range" min={5_000} max={200_000} step={1_000}
                    value={withdrawal}
                    onChange={e => setWithdrawal(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-600 mt-0.5">
                    <span>5K/yr</span><span>200K/yr</span>
                  </div>
                </div>

                {/* Time horizon */}
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-slate-400">Years in Retirement</label>
                    <span className="text-sm font-bold text-slate-200">{years} yrs</span>
                  </div>
                  <input
                    type="range" min={5} max={45} value={years}
                    onChange={e => setYears(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>

                {/* Currency */}
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Currency</label>
                  <select
                    value={currency}
                    onChange={e => setCurrency(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:outline-none"
                  >
                    {["EUR", "USD", "GBP", "CHF"].map(c => <option key={c}>{c}</option>)}
                  </select>
                </div>
              </div>

              {/* Withdrawal rate badge */}
              <div className={`rounded-xl border p-4 space-y-1 ${isHighRate ? "border-rose-800/40 bg-rose-950/20" : "border-emerald-800/40 bg-emerald-950/20"}`}>
                <p className="text-xs text-slate-500">Withdrawal Rate</p>
                <p className={`text-2xl font-black ${isHighRate ? "text-rose-400" : "text-emerald-400"}`}>
                  {withdrawalRate}%
                </p>
                <p className="text-[10px] text-slate-500">
                  {isHighRate
                    ? "Above the 4% rule — higher depletion risk"
                    : "Within the 4% safe withdrawal guideline"}
                </p>
              </div>

              {/* Scenario outcomes */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Outcomes</p>
                {SCENARIOS.map(s => {
                  const dep = findDepletionYear(data, s.label);
                  const final = data[data.length - 1]?.[s.label] ?? 0;
                  return (
                    <div key={s.label} className="flex items-center justify-between">
                      <span className="text-xs text-slate-400 flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
                        {s.label.split(" ")[0]}
                      </span>
                      {dep ? (
                        <span className="text-xs font-bold text-rose-400">Depleted yr {dep}</span>
                      ) : (
                        <span className="text-xs font-bold text-emerald-400">{fmt(final, currency)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── Chart ─────────────────────────────────────────────────────── */}
            <div className="lg:col-span-2 space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
                  Portfolio Value Over Time
                </p>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis
                        dataKey="year"
                        stroke="#475569"
                        tick={{ fontSize: 11, fill: "#64748b" }}
                        tickFormatter={v => `Yr ${v + 1}`}
                      />
                      <YAxis
                        stroke="#475569"
                        tick={{ fontSize: 11, fill: "#64748b" }}
                        tickFormatter={v => v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1000 ? `${Math.round(v / 1000)}K` : `${v}`}
                      />
                      <Tooltip
                        contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                        formatter={(value: number, name: string) => [fmt(value, currency), name]}
                        labelFormatter={v => `Year ${Number(v) + 1}`}
                      />
                      <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
                      <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} />
                      {SCENARIOS.map(s => (
                        <Line
                          key={s.label}
                          type="monotone"
                          dataKey={s.label}
                          stroke={s.color}
                          strokeWidth={s.dashed ? 1.5 : 2}
                          strokeDasharray={s.dashed ? "6 3" : undefined}
                          dot={false}
                          activeDot={{ r: 4 }}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Explainer */}
              <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-5 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">What is Sequence of Returns Risk?</p>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Even if the average long-run return is the same, <em>when</em> market crashes occur matters enormously in retirement.
                  A major crash in year 1 (like 2000 or 2008) forces you to sell depreciated assets to fund withdrawals,
                  permanently reducing your capital base &mdash; even if markets fully recover later.
                </p>
                <p className="text-sm text-slate-400 leading-relaxed">
                  The <strong className="text-slate-300">4% Rule</strong> suggests withdrawing no more than 4% of your initial
                  portfolio per year, historically surviving 30 years across most market environments.
                  This visualiser shows how three real crash scenarios compare.
                </p>
              </div>

              {isHighRate && (
                <div className="rounded-xl border border-amber-800/40 bg-amber-950/20 p-4 flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-300 leading-relaxed">
                    Your withdrawal rate of <strong>{withdrawalRate}%</strong> exceeds the traditional 4% safe withdrawal guideline.
                    Consider reducing annual withdrawals, increasing your portfolio size, or building a cash buffer for the early years.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 p-4 flex items-start gap-3">
            <Info className="h-4 w-4 text-slate-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-600 leading-relaxed">
              This tool uses historical S&amp;P 500 nominal annual returns for illustrative purposes only.
              It does not account for inflation, taxes, fees, dividends, or individual asset allocation.
              Past performance does not guarantee future results. Not investment or retirement advice.
              Consult a qualified financial planner for personalised guidance.
            </p>
          </div>
        </div>
      </div>
    </ProGate>
  );
}
