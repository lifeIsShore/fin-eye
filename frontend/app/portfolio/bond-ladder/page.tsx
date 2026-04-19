"use client";

/**
 * /portfolio/bond-ladder — Sprint 54
 * Bond Ladder Builder: Treasury yields from FRED, equal-split across maturities.
 */

import { useState, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import Link from "next/link";
import { fetchBondLadder, type BondLadderDto } from "@/lib/api";
import { TrendingUp, AlertTriangle, ArrowRight } from "lucide-react";

const CURRENCIES = ["EUR", "USD", "GBP"];

const CURVE_CONFIG: Record<string, { label: string; color: string }> = {
  Normal:   { label: "Normal curve ✓",    color: "text-emerald-400" },
  Inverted: { label: "Inverted curve ⚠️",  color: "text-rose-400"    },
  Flat:     { label: "Flat curve —",      color: "text-amber-400"   },
  Unknown:  { label: "Unknown",           color: "text-slate-400"   },
};

const BAR_COLORS = ["#34d399","#2dd4bf","#22d3ee","#38bdf8","#60a5fa","#818cf8","#a78bfa","#c084fc"];

export default function BondLadderPage() {
  const [investment, setInvestment] = useState(10000);
  const [currency, setCurrency]     = useState("EUR");
  const [data, setData]             = useState<BondLadderDto | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchBondLadder(investment, currency));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [investment, currency]);

  const sym   = currency === "USD" ? "$" : currency === "GBP" ? "£" : "€";
  const curve = data ? (CURVE_CONFIG[data.curve_shape] ?? CURVE_CONFIG.Unknown) : null;

  return (
    <div className="mx-auto max-w-3xl space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-sky-400" /> Bond Ladder Builder
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Visualise a Treasury bond ladder using live FRED yield data. Equal allocation across maturities.
        </p>
      </div>

      {/* Inputs */}
      <div className="flex flex-wrap gap-4 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Total investment</label>
          <input
            type="number"
            min={100}
            step={100}
            value={investment}
            onChange={(e) => setInvestment(Number(e.target.value))}
            className="w-36 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-500">Currency</label>
          <div className="flex gap-1">
            {CURRENCIES.map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                  currency === c
                    ? "border-sky-500 bg-sky-900/30 text-sky-300"
                    : "border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={run}
          disabled={loading || investment <= 0}
          className="rounded-xl bg-sky-600 px-5 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition-colors"
        >
          {loading ? "Loading…" : "Build Ladder"}
        </button>
      </div>

      {error && (
        <p className="text-sm text-rose-400 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" /> {error}
        </p>
      )}

      {data && (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Blended yield",      value: `${data.blended_yield.toFixed(2)}%`,                           color: "text-slate-100" },
              { label: "Total annual income", value: `${sym}${data.total_annual_income.toLocaleString()}`,          color: "text-emerald-400" },
              { label: "Yield curve",         value: curve!.label,                                                  color: curve!.color },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                <p className={`mt-1 text-lg font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Bar chart */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
            <p className="text-xs font-semibold text-slate-400 mb-4">Yield by maturity (%)</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.rungs} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                <XAxis dataKey="maturity" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <YAxis
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  formatter={(v: number) => [`${v.toFixed(3)}%`, "Yield"]}
                  contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="yield_pct" radius={[4, 4, 0, 0]}>
                  {data.rungs.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Allocation table */}
          <div className="rounded-2xl border border-slate-800 overflow-hidden">
            <div className="bg-slate-900/60 px-5 py-3 border-b border-slate-800">
              <p className="text-xs font-semibold text-slate-300">Ladder allocation ({currency})</p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40">
                  {["Maturity", "Yield", "Allocation", "Annual income"].map((h) => (
                    <th key={h} className="px-5 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {data.rungs.map((r, i) => (
                  <tr key={r.maturity} className="hover:bg-slate-900/20 transition-colors">
                    <td className="px-5 py-2.5 text-xs text-slate-300">{r.maturity}</td>
                    <td className="px-5 py-2.5 text-xs font-semibold" style={{ color: BAR_COLORS[i % BAR_COLORS.length] }}>
                      {r.yield_pct.toFixed(3)}%
                    </td>
                    <td className="px-5 py-2.5 text-xs text-slate-300">{sym}{r.allocation.toLocaleString()}</td>
                    <td className="px-5 py-2.5 text-xs text-emerald-400">{sym}{r.annual_income.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Macro link */}
          <div className="text-xs">
            <Link href="/macro" className="flex items-center gap-1 text-sky-400 hover:text-sky-300 transition-colors w-fit">
              View yield spreads in Macro <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {/* Disclaimer */}
          <p className="text-[11px] text-slate-600 leading-relaxed border-t border-slate-800 pt-4">
            ⚠ {data.disclaimer}
          </p>
        </>
      )}

      {!data && !loading && !error && (
        <p className="text-sm text-slate-500 text-center py-12">
          Enter your investment amount and click <span className="text-slate-300">Build Ladder</span> to see projections.
        </p>
      )}

    </div>
  );
}
