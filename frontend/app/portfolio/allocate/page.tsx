"use client";

import { useState, useMemo } from "react";
import { useAuth } from "@/components/AuthProvider";
import ProGate from "@/components/ProGate";
import { PieChartIcon, TrendingUp, Info } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

type RiskProfile = "Conservative" | "Income" | "Moderate" | "Growth" | "Aggressive";

const PROFILES: RiskProfile[] = ["Conservative", "Income", "Moderate", "Growth", "Aggressive"];

const ALLOCATION_MODELS: Record<RiskProfile, { equities: number; bonds: number; cash: number; alternatives: number; description: string }> = {
  Conservative: { equities: 20, bonds: 60, cash: 20, alternatives: 0,  description: "Prioritises capital preservation. Suited for short horizons and low volatility tolerance." },
  Income:       { equities: 35, bonds: 50, cash: 10, alternatives: 5,  description: "Aims for steady yield with modest capital appreciation." },
  Moderate:     { equities: 50, bonds: 40, cash: 5,  alternatives: 5,  description: "Balanced approach seeking a mix of growth and stability." },
  Growth:       { equities: 75, bonds: 20, cash: 5,  alternatives: 0,  description: "Focuses on long-term capital appreciation, accepting higher volatility." },
  Aggressive:   { equities: 90, bonds: 5,  cash: 5,  alternatives: 0,  description: "Maximises long-term growth potential. Suited for long horizons and high volatility tolerance." }
};

const SLICE_COLORS = ["#3b82f6", "#10b981", "#64748b", "#f59e0b"];

function defaultProfileForAge(age: number): RiskProfile {
  if (age < 30) return "Aggressive";
  if (age < 45) return "Growth";
  if (age < 55) return "Moderate";
  if (age < 65) return "Income";
  return "Conservative";
}

const RADIAN = Math.PI / 180;
const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name }: any) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  if (percent < 0.05) return null;
  return (
    <text x={x} y={y} fill="white" textAnchor={x > cx ? "start" : "end"} dominantBaseline="central" fontSize={12} fontWeight="bold">
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};
export default function AssetAllocationPage() {
  const { user } = useAuth();

  const storedProfile = (user?.risk_profile as RiskProfile | undefined);
  const [age, setAge] = useState(35);
  const [horizon, setHorizon] = useState(20);
  const [currency, setCurrency] = useState("EUR");
  const [profile, setProfile] = useState<RiskProfile>(storedProfile ?? defaultProfileForAge(35));
  const [showInfo, setShowInfo] = useState(false);

  // Re-suggest profile when age changes
  function handleAgeChange(val: number) {
    setAge(val);
    if (!storedProfile) setProfile(defaultProfileForAge(val));
  }

  const model = ALLOCATION_MODELS[profile];

  const pieData = useMemo(() => [
    { name: "Equities",      value: model.equities,     color: SLICE_COLORS[0] },
    { name: "Bonds",         value: model.bonds,        color: SLICE_COLORS[1] },
    { name: "Cash",          value: model.cash,         color: SLICE_COLORS[2] },
    { name: "Alternatives",  value: model.alternatives, color: SLICE_COLORS[3] },
  ].filter(d => d.value > 0), [model]);

  const tableRows = [
    { label: "Equities",     pct: model.equities,     color: SLICE_COLORS[0], note: "Global stocks, ETFs, funds" },
    { label: "Bonds",        pct: model.bonds,        color: SLICE_COLORS[1], note: "Government & corporate bonds" },
    { label: "Cash",         pct: model.cash,         color: SLICE_COLORS[2], note: "Money market, savings" },
    { label: "Alternatives", pct: model.alternatives, color: SLICE_COLORS[3], note: "REITs, commodities, gold" },
  ];

  const profileIndex = PROFILES.indexOf(profile);

  return (
    <ProGate feature="portfolio_allocation">
      <div className="min-h-screen bg-slate-950 text-slate-200">
        <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">

          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
              <PieChartIcon className="h-6 w-6 text-blue-400" />
              Asset Allocation Suggester
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Get a suggested portfolio allocation based on your risk profile, age, and time horizon.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* ── Left: Inputs ──────────────────────────────────────────────── */}
            <div className="space-y-5">

              {/* Risk profile */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Risk Profile</p>
                {storedProfile && (
                  <p className="text-[10px] text-sky-400 bg-sky-900/20 border border-sky-800/30 rounded-md px-2 py-1">
                    Auto-filled from your Settings preference
                  </p>
                )}
                <div className="flex flex-col gap-1.5">
                  {PROFILES.map((p) => (
                    <button
                      key={p}
                      onClick={() => setProfile(p)}
                      className={`rounded-lg px-3 py-2 text-sm text-left transition-all ${
                        profile === p
                          ? "bg-blue-700/50 border border-blue-600/50 text-blue-200 font-semibold"
                          : "bg-slate-800/50 border border-slate-700/40 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Age + Horizon */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Parameters</p>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs text-slate-400">Age</label>
                    <span className="text-sm font-bold text-slate-200">{age}</span>
                  </div>
                  <input
                    type="range" min={18} max={80} value={age}
                    onChange={e => handleAgeChange(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs text-slate-400">Time Horizon</label>
                    <span className="text-sm font-bold text-slate-200">{horizon} yrs</span>
                  </div>
                  <input
                    type="range" min={1} max={40} value={horizon}
                    onChange={e => setHorizon(Number(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>

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

              {/* Risk meter */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-xs text-slate-500 mb-2">Risk Level</p>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${((profileIndex + 1) / PROFILES.length) * 100}%`,
                      background: `linear-gradient(90deg, #22d3ee, #3b82f6, #f59e0b, #ef4444)`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                  <span>Low</span><span>High</span>
                </div>
              </div>
            </div>

            {/* ── Right: Chart + Table ───────────────────────────────────────── */}
            <div className="lg:col-span-2 space-y-5">

              {/* Profile description */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-lg font-black text-slate-100">{profile}</span>
                  <span className="text-xs text-slate-500 bg-slate-800 rounded-full px-2 py-0.5">
                    {horizon}yr horizon · Age {age}
                  </span>
                </div>
                <p className="text-sm text-slate-400">{model.description}</p>
              </div>

              {/* Pie chart */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">
                  Suggested Allocation
                </p>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        dataKey="value"
                        labelLine={false}
                        label={CustomLabel as any}
                      >
                        {pieData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }}
                        formatter={(value: number) => [`${value}%`, ""]}
                      />
                      <Legend
                        formatter={(value) => <span style={{ color: "#94a3b8", fontSize: 12 }}>{value}</span>}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Breakdown table */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Asset Class</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Weight</th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">Examples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.filter(r => r.pct > 0).map((row) => (
                      <tr key={row.label} className="border-b border-slate-800/50 last:border-0">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ background: row.color }} />
                            <span className="font-medium text-slate-200">{row.label}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center gap-2 justify-end">
                            <div className="w-20 bg-slate-800 rounded-full h-1.5">
                              <div
                                className="h-1.5 rounded-full"
                                style={{ width: `${row.pct}%`, background: row.color }}
                              />
                            </div>
                            <span className="font-bold text-slate-100 w-10 text-right">{row.pct}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-xs hidden sm:table-cell">{row.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Key insight */}
              <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-4 flex items-start gap-3">
                <TrendingUp className="h-4 w-4 text-sky-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-slate-400 leading-relaxed">
                  With a <strong className="text-slate-300">{horizon}-year horizon</strong>, you can weather
                  {profile === "Conservative" || profile === "Income"
                    ? " short-term volatility with stability-focused assets."
                    : profile === "Moderate"
                    ? " market cycles. A balanced mix gives you growth without excessive drawdown."
                    : " significant drawdowns. Staying invested through downturns maximises long-run compounding."}
                </p>
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 p-4 flex items-start gap-3">
            <Info className="h-4 w-4 text-slate-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-600 leading-relaxed">
              This allocation is a mathematical model based on your inputs — not personalised financial advice.
              Asset class weights are illustrative. Actual returns, taxation, and suitability vary by individual
              circumstance. Consult a qualified financial adviser before making investment decisions.
            </p>
          </div>
        </div>
      </div>
    </ProGate>

  );
}
