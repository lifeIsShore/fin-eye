"use client";

import { useState, useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Line, Legend,
} from "recharts";
import {
  FlaskConical,
  Plus,
  Trash2,
  TrendingUp,
  AlertTriangle,
  Info,
  ShieldCheck,
  Zap,
} from "lucide-react";
import ProGate from "@/components/ProGate";
import { 
  runPortfolioMonteCarlo, 
  MCPortfolioAsset, 
  MCPortfolioResult,
  MCPercentileResult
} from "@/lib/api";
import { PageBanner } from "@/components/ui/PageBanner";

interface FormData {
  starting_capital: number;
  years: number;
  monthly_contribution: number;
  model_type: "GBM" | "JUMP_DIFFUSION";
  jump_intensity: number;
  jump_mean: number;
  jump_std: number;
}

export default function MonteCarloDashboard() {
  const [assets, setAssets] = useState<MCPortfolioAsset[]>([
    { symbol: "Stocks", starting_value: 6000, mu: 0.10, sigma: 0.18 },
    { symbol: "Bonds", starting_value: 4000, mu: 0.04, sigma: 0.08 }
  ]);

  const [form, setForm] = useState<FormData>({
    starting_capital: 10000,
    years: 10,
    monthly_contribution: 500,
    model_type: "GBM",
    jump_intensity: 0.1,
    jump_mean: -0.2,
    jump_std: 0.1,
  });

  const [result, setResult] = useState<MCPortfolioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addAsset = () => {
    setAssets([...assets, { symbol: "New Asset", starting_value: 0, mu: 0.07, sigma: 0.15 }]);
  };

  const removeAsset = (index: number) => {
    setAssets(assets.filter((_, i) => i !== index));
  };

  const updateAsset = (index: number, field: keyof MCPortfolioAsset, value: any) => {
    const newAssets = [...assets];
    newAssets[index] = { ...newAssets[index], [field]: value };
    setAssets(newAssets);
  };

  const handleRunSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await runPortfolioMonteCarlo({
        starting_capital: form.starting_capital,
        assets: assets,
        years: form.years,
        paths: 5000,
        steps_per_year: 12, // Monthly steps
        monthly_contribution: form.monthly_contribution,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (v: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);

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

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Controls */}
          <div className="lg:col-span-1 space-y-6">
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-5">
              <h3 className="text-sm font-semibold text-slate-200">Simulation Settings</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Starting Capital ($)</label>
                  <input
                    type="number"
                    value={form.starting_capital}
                    onChange={(e) => setForm({ ...form, starting_capital: Number(e.target.value) })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Plan Horizon (Years)</label>
                  <div className="flex items-center gap-3">
                    <input
                      type="range" min={1} max={50}
                      value={form.years}
                      onChange={(e) => setForm({ ...form, years: Number(e.target.value) })}
                      className="flex-1 accent-indigo-500"
                    />
                    <span className="text-sm font-mono text-slate-200 w-8">{form.years}</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1.5">Monthly Contribution ($)</label>
                  <input
                    type="number"
                    value={form.monthly_contribution}
                    onChange={(e) => setForm({ ...form, monthly_contribution: Number(e.target.value) })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Assets</h4>
                  <button onClick={addAsset} className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 transition">
                    <Plus className="h-3 w-3" />
                  </button>
                </div>
                
                <div className="space-y-3">
                  {assets.map((asset, i) => (
                    <div key={i} className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-3 space-y-2">
                       <div className="flex items-center justify-between">
                          <input
                            type="text"
                            value={asset.symbol}
                            onChange={(e) => updateAsset(i, "symbol", e.target.value)}
                            className="bg-transparent text-xs font-bold text-slate-200 focus:outline-none w-20"
                          />
                          <button onClick={() => removeAsset(i)} className="text-slate-600 hover:text-rose-500 transition">
                            <Trash2 className="h-3 w-3" />
                          </button>
                       </div>
                       <div className="grid grid-cols-2 gap-2">
                          <div>
                            <span className="text-[10px] text-slate-500 block">Ret % (mu)</span>
                            <input
                              type="number" step={0.01}
                              value={asset.mu}
                              onChange={(e) => updateAsset(i, "mu", Number(e.target.value))}
                              className="w-full bg-transparent text-xs text-slate-300 border-b border-slate-800 focus:border-indigo-500 focus:outline-none"
                            />
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-500 block">Vol % (σ)</span>
                            <input
                              type="number" step={0.01}
                              value={asset.sigma}
                              onChange={(e) => updateAsset(i, "sigma", Number(e.target.value))}
                              className="w-full bg-transparent text-xs text-slate-300 border-b border-slate-800 focus:border-indigo-500 focus:outline-none"
                            />
                          </div>
                       </div>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleRunSimulation}
                disabled={loading}
                className="w-full rounded-xl bg-indigo-600 py-3 text-sm font-bold text-white hover:bg-indigo-500 disabled:opacity-50 transition drop-shadow-lg"
              >
                {loading ? <Zap className="h-4 w-4 animate-pulse mx-auto" /> : "Run 5,000 Paths"}
              </button>
            </div>

            {error && (
              <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 flex items-start gap-3">
                <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-rose-300">{error}</p>
              </div>
            )}
          </div>

          {/* Main Panel - Results */}
          <div className="lg:col-span-3 space-y-6">
            {!result && !loading && (
              <div className="flex h-[500px] flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-slate-800 bg-slate-900/20">
                <TrendingUp className="h-12 w-12 text-slate-700" />
                <div className="text-center">
                  <p className="text-slate-400 font-medium">No active simulation</p>
                  <p className="text-sm text-slate-600">Configure your portfolio parameters and run the Monte Carlo engine.</p>
                </div>
              </div>
            )}

            {loading && (
              <div className="flex h-[500px] flex-col items-center justify-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 animate-pulse">
                <div className="h-12 w-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <p className="text-slate-400 font-medium tracking-wide">GENERATING 5,000 FUTURES...</p>
              </div>
            )}

            {result && !loading && (
              <div className="space-y-6 animate-in fade-in duration-500">
                {/* KPI Blocks */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                    <span className="text-xs text-slate-500 block mb-1">Success Rate</span>
                    <span className={`text-2xl font-black ${result.success_rate > 80 ? 'text-emerald-400' : result.success_rate > 50 ? 'text-amber-400' : 'text-rose-400'}`}>
                      {result.success_rate.toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-slate-600 block mt-1">Prob. of Ending Value &gt; 0</span>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                    <span className="text-xs text-slate-500 block mb-1">Median Expectation</span>
                    <span className="text-2xl font-black text-slate-100">
                      {fmt(result.final_median)}
                    </span>
                    <span className="text-[10px] text-slate-600 block mt-1">P50 Outcome after {form.years}y</span>
                  </div>
                  <div className="rounded-xl border border-indigo-900/40 bg-indigo-950/20 p-5">
                    <span className="text-xs text-indigo-400/70 block mb-1">Downside Risk (P5)</span>
                    <span className="text-2xl font-black text-indigo-400">
                      {fmt(result.final_p5)}
                    </span>
                    <span className="text-[10px] text-indigo-500/60 block mt-1">95% of paths stay above this</span>
                  </div>
                </div>

                {/* Primary Chart: The Probability Cone */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-lg font-bold text-slate-100">Probability Trajectory</h3>
                      <p className="text-xs text-slate-500">Visualization of 5,000 potential futures based on selected variance.</p>
                    </div>
                    <div className="flex gap-4">
                       <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-emerald-500" />
                          <span className="text-[10px] text-slate-400">Best (P95)</span>
                       </div>
                       <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-indigo-500" />
                          <span className="text-[10px] text-slate-400">Median (P50)</span>
                       </div>
                       <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full bg-rose-500" />
                          <span className="text-[10px] text-slate-400">Worst (P5)</span>
                       </div>
                    </div>
                  </div>
                  
                  <div className="h-[400px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={result.trajectory}>
                        <defs>
                          <linearGradient id="p95p75" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="p50" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15}/>
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05}/>
                          </linearGradient>
                          <linearGradient id="p25p5" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.1}/>
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis 
                          dataKey="day" 
                          stroke="#475569" 
                          fontSize={11} 
                          tickFormatter={v => `Y${Math.floor(v/365)}`}
                          interval={Math.floor(result.trajectory.length / 5)} 
                        />
                        <YAxis 
                          stroke="#475569" 
                          fontSize={11}
                          tickFormatter={v => v >= 1000000 ? `$${(v/1000000).toFixed(1)}M` : `$${Math.round(v/1000)}k`}
                          width={60}
                        />
                        <Tooltip 
                          contentStyle={{ backgroundColor: "#020617", border: "1px solid #1e293b", borderRadius: "12px", fontSize: "12px" }}
                          formatter={(v: any) => [fmt(v), ""]}
                          labelFormatter={(l, items) => {
                             const day = items[0]?.payload?.day;
                             return `Elapsed: ${Math.floor(day/365)}y ${Math.floor((day%365)/30)}m`;
                          }}
                        />
                        <Area type="monotone" dataKey="p95" stroke="none" fill="url(#p95p75)" fillOpacity={1} />
                        <Area type="monotone" dataKey="p75" stroke="#10b981" strokeWidth={1} fill="url(#p50)" fillOpacity={1} />
                        <Area type="monotone" dataKey="p25" stroke="#ef4444" strokeWidth={1} fill="url(#p25p5)" fillOpacity={1} />
                        <Area type="monotone" dataKey="p5" stroke="none" fill="#ef4444" fillOpacity={0.05} />
                        <Line type="monotone" dataKey="p50" stroke="#818cf8" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 flex items-start gap-4">
                   <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                      <ShieldCheck className="h-5 w-5" />
                   </div>
                   <div>
                      <h4 className="text-sm font-semibold text-slate-200">Statistical Significance</h4>
                      <p className="text-xs text-slate-500 leading-relaxed mt-1">
                        These results are based on <strong>5,000 independent trials</strong> using Geometric Brownian Motion. 
                        While GBM models random walks effectively, it does not account for regime shifts, tax events, or 
                        unpredictable correlation spikes during market distress. 
                      </p>
                   </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </ProGate>
  );
}
