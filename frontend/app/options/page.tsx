"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  fetchOptionsAnalysis,
  type OptionsAnalysisDto,
  type OptionsExpiryBreakdownDto,
} from "../../lib/api";

// ─── Helpers ────────────────────────────────────────────────────────────────

const DEFAULT_SYMBOL = "AAPL";

function fgColor(score: number): string {
  if (score >= 75) return "text-emerald-400";
  if (score >= 60) return "text-teal-400";
  if (score >= 40) return "text-amber-400";
  if (score >= 25) return "text-orange-400";
  return "text-rose-400";
}

function fgBg(score: number): string {
  if (score >= 75) return "bg-emerald-950/30 border-emerald-900/50";
  if (score >= 60) return "bg-teal-950/30 border-teal-900/50";
  if (score >= 40) return "bg-amber-950/30 border-amber-900/50";
  if (score >= 25) return "bg-orange-950/30 border-orange-900/50";
  return "bg-rose-950/30 border-rose-900/50";
}

function pcrColor(label: string): string {
  if (label.includes("Extreme Fear")) return "text-rose-400";
  if (label.includes("Fear"))         return "text-orange-400";
  if (label.includes("Neutral"))      return "text-amber-400";
  if (label.includes("Greed"))        return "text-emerald-400";
  return "text-slate-400";
}

function formatOI(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function FearGreedGauge({ score, label }: { score: number; label: string }) {
  const clr = fgColor(score);
  const bg  = fgBg(score);
  // Arc: 0 = leftmost (fear), 100 = rightmost (greed)
  const pct = score / 100;
  const needleAngle = -90 + pct * 180; // -90° (far left) to +90° (far right)

  return (
    <div className={`rounded-2xl border ${bg} p-6 flex flex-col items-center gap-3`}>
      {/* SVG half-gauge */}
      <svg viewBox="0 0 200 110" className="w-48 h-auto">
        {/* Background track */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="#1e293b"
          strokeWidth="18"
          strokeLinecap="round"
        />
        {/* Coloured fill — gradient via 5 segments */}
        {[
          { offset: 0.0, stroke: "#f43f5e" },  // fear
          { offset: 0.25, stroke: "#fb923c" }, // mild fear
          { offset: 0.5, stroke: "#f59e0b" },  // neutral
          { offset: 0.75, stroke: "#2dd4bf" }, // mild greed
          { offset: 1.0, stroke: "#34d399" },  // greed
        ].map((seg, i, arr) => {
          if (i === arr.length - 1) return null;
          const next = arr[i + 1];
          const a1 = Math.PI * seg.offset;
          const a2 = Math.PI * next.offset;
          const x1 = 100 - 80 * Math.cos(a1);
          const y1 = 100 - 80 * Math.sin(a1);
          const x2 = 100 - 80 * Math.cos(a2);
          const y2 = 100 - 80 * Math.sin(a2);
          return (
            <path
              key={i}
              d={`M ${x1} ${y1} A 80 80 0 0 1 ${x2} ${y2}`}
              fill="none"
              stroke={seg.stroke}
              strokeWidth="18"
              strokeLinecap="butt"
              opacity={score / 100 >= seg.offset ? 0.85 : 0.15}
            />
          );
        })}
        {/* Needle */}
        <g transform={`rotate(${needleAngle}, 100, 100)`}>
          <line x1="100" y1="100" x2="100" y2="30" stroke="#e2e8f0" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="100" cy="100" r="5" fill="#e2e8f0" />
        </g>
        {/* Score label */}
        <text x="100" y="96" textAnchor="middle" fontSize="22" fontWeight="bold" fill="#e2e8f0">
          {score.toFixed(0)}
        </text>
      </svg>

      <div className="text-center space-y-1">
        <p className={`text-xl font-bold ${clr}`}>{label}</p>
        <p className="text-xs text-slate-500">Options Fear &amp; Greed Score (0 = Fear, 100 = Greed)</p>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  valueClass = "text-slate-100",
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col gap-1">
      <p className="text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
      <p className={`text-xl font-bold ${valueClass}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function ExpiryTable({ rows }: { rows: OptionsExpiryBreakdownDto[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-800 text-slate-500 uppercase tracking-wider">
            <th className="py-2 text-left font-medium">Expiry</th>
            <th className="py-2 text-right font-medium">Call OI</th>
            <th className="py-2 text-right font-medium">Put OI</th>
            <th className="py-2 text-right font-medium">PCR</th>
            <th className="py-2 text-right font-medium">Put Vol</th>
            <th className="py-2 text-right font-medium">Max Pain</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const pcr = row.pcr;
            const pcrCls =
              pcr > 1.5 ? "text-rose-400 font-semibold" :
              pcr > 1.0 ? "text-orange-400" :
              pcr > 0.7 ? "text-amber-400" :
              pcr > 0.5 ? "text-teal-400" :
              "text-emerald-400 font-semibold";
            return (
              <tr key={row.expiry} className="border-b border-slate-800/50 hover:bg-slate-900/30 transition-colors">
                <td className="py-2 text-slate-300 font-mono">{row.expiry}</td>
                <td className="py-2 text-right text-slate-400">{formatOI(row.calls_oi)}</td>
                <td className="py-2 text-right text-slate-400">{formatOI(row.puts_oi)}</td>
                <td className={`py-2 text-right ${pcrCls}`}>{pcr.toFixed(2)}</td>
                <td className="py-2 text-right text-slate-500">{formatOI(row.total_put_volume)}</td>
                <td className="py-2 text-right text-slate-300">
                  {row.max_pain_strike != null ? `$${row.max_pain_strike.toFixed(0)}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PCRBar({ pcr }: { pcr: number }) {
  // Map PCR 0–2 to a 0–100 position; midpoint (neutral ~0.7) ≈ 35%
  const pct = Math.min(100, (pcr / 2) * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-slate-500">
        <span>Greed (low PCR)</span>
        <span>Fear (high PCR)</span>
      </div>
      <div className="relative h-3 rounded-full bg-gradient-to-r from-emerald-600 via-amber-500 to-rose-600">
        {/* Neutral band 0.7–1.0 */}
        <div
          className="absolute top-0 h-full w-px bg-slate-300/50"
          style={{ left: "35%" }}
        />
        {/* PCR needle */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-white border-2 border-slate-800 shadow"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-slate-600">
        <span>0.0</span>
        <span>0.7</span>
        <span>1.0</span>
        <span>2.0+</span>
      </div>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function OptionsPage() {
  const [tickerInput, setTickerInput] = useState(DEFAULT_SYMBOL);
  const [activeSymbol, setActiveSymbol] = useState(DEFAULT_SYMBOL);

  const { data, error, isLoading } = useSWR<OptionsAnalysisDto>(
    `options-${activeSymbol}`,
    () => fetchOptionsAnalysis(activeSymbol),
    { refreshInterval: 900_000, shouldRetryOnError: false, keepPreviousData: true },
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const sym = tickerInput.trim().toUpperCase();
    if (sym) setActiveSymbol(sym);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">
            Options Fear &amp; Greed
          </h2>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Put/Call Ratio, IV Skew, and Max Pain derived from yfinance options chains.
            Educational analysis only — not investment advice.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-400" htmlFor="opt-ticker">Ticker</label>
          <input
            id="opt-ticker"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            className="h-9 rounded-md border border-slate-700 bg-slate-900 px-2 text-sm text-slate-50 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
            placeholder="e.g. AAPL"
          />
          <button
            type="submit"
            className="inline-flex h-9 items-center rounded-md bg-sky-500 px-3 text-xs font-medium text-white hover:bg-sky-400 transition-colors"
          >
            Load
          </button>
        </form>
      </div>

      {/* Loading */}
      {isLoading && !data && (
        <div className="py-20 text-center animate-pulse text-slate-500">
          Fetching options data for {activeSymbol}…
        </div>
      )}

      {/* Error */}
      {error && !data && (
        <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 px-5 py-4 text-sm text-rose-400">
          <strong>Could not load options data for {activeSymbol}.</strong>{" "}
          {error.message}{" "}
          Some tickers (ETFs, small-caps) may have limited or no listed options.
        </div>
      )}

      {/* Data */}
      {data && (
        <div className="space-y-6">
          {/* Row 1 — Fear & Greed gauge + key stats */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Gauge */}
            <FearGreedGauge
              score={data.fear_greed_score}
              label={data.fear_greed_label}
            />

            {/* Key stats grid */}
            <div className="grid grid-cols-2 gap-3">
              <StatCard
                label="Spot Price"
                value={`$${data.spot_price.toFixed(2)}`}
                sub={activeSymbol}
              />
              <StatCard
                label="Agg. Put/Call Ratio"
                value={data.aggregate_pcr.toFixed(2)}
                sub={data.pcr_label}
                valueClass={pcrColor(data.pcr_label)}
              />
              <StatCard
                label="IV Skew (10% OTM)"
                value={
                  data.iv_skew != null
                    ? `${data.iv_skew > 0 ? "+" : ""}${data.iv_skew.toFixed(1)}%`
                    : "N/A"
                }
                sub={data.iv_skew_label}
                valueClass={
                  data.iv_skew == null ? "text-slate-500"
                  : data.iv_skew > 4    ? "text-rose-400"
                  : data.iv_skew < -4   ? "text-emerald-400"
                  : "text-amber-400"
                }
              />
              <StatCard
                label="Max Pain Strike"
                value={data.max_pain_strike != null ? `$${data.max_pain_strike.toFixed(0)}` : "N/A"}
                sub={
                  data.max_pain_distance_pct != null
                    ? `${data.max_pain_distance_pct > 0 ? "+" : ""}${data.max_pain_distance_pct.toFixed(1)}% from spot`
                    : undefined
                }
              />
              <StatCard
                label="Total Call OI"
                value={formatOI(data.total_calls_oi)}
                sub="all expiries"
                valueClass="text-emerald-400"
              />
              <StatCard
                label="Total Put OI"
                value={formatOI(data.total_puts_oi)}
                sub="all expiries"
                valueClass="text-rose-400"
              />
            </div>
          </section>

          {/* Row 2 — PCR bar + interpretation */}
          <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-100">
              Put/Call Ratio — {activeSymbol}
            </h3>
            <PCRBar pcr={data.aggregate_pcr} />
            <p className="text-sm text-slate-400 leading-relaxed">
              {data.pcr_interpretation}
            </p>
            {/* IV Skew detail */}
            {(data.near_put_iv != null || data.near_call_iv != null) && (
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-800/60">
                <div className="text-center">
                  <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">10% OTM Put IV</p>
                  <p className="text-base font-semibold text-rose-400">
                    {data.near_put_iv != null ? `${data.near_put_iv.toFixed(1)}%` : "—"}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">IV Skew</p>
                  <p className={`text-base font-semibold ${data.iv_skew != null && data.iv_skew > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    {data.iv_skew != null ? `${data.iv_skew > 0 ? "+" : ""}${data.iv_skew.toFixed(1)}%` : "—"}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-1">10% OTM Call IV</p>
                  <p className="text-base font-semibold text-emerald-400">
                    {data.near_call_iv != null ? `${data.near_call_iv.toFixed(1)}%` : "—"}
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* Row 3 — Per-expiry breakdown */}
          {data.expiry_breakdown.length > 0 && (
            <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-100">
                  Per-Expiry PCR Breakdown
                </h3>
                <span className="text-xs text-slate-500">
                  {data.expiry_breakdown.length} nearest expiries
                </span>
              </div>
              <ExpiryTable rows={data.expiry_breakdown} />
            </section>
          )}

          {/* Max Pain explainer */}
          {data.max_pain_strike != null && (
            <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-2">
              <h3 className="text-sm font-semibold text-slate-100">Max Pain — ${data.max_pain_strike.toFixed(0)}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Max Pain is the strike price at which the total intrinsic value owed to all
                option holders would be minimised at expiry — in other words, where option
                sellers face the least losses. The current max pain for the nearest expiry
                is <span className="font-medium text-slate-200">${data.max_pain_strike.toFixed(0)}</span>,
                which is{" "}
                {data.max_pain_distance_pct != null ? (
                  <>
                    <span className={data.max_pain_distance_pct >= 0 ? "text-emerald-400 font-medium" : "text-rose-400 font-medium"}>
                      {data.max_pain_distance_pct > 0 ? "+" : ""}{data.max_pain_distance_pct.toFixed(1)}%
                    </span>{" "}
                    {data.max_pain_distance_pct >= 0 ? "above" : "below"} current spot.
                  </>
                ) : (
                  "near the current spot price."
                )}
              </p>
              <p className="text-xs text-slate-500">
                ⚠ Max Pain has mixed empirical support. It is most relevant in the final
                days before expiry and should not be used as a standalone signal.
              </p>
            </section>
          )}

          {/* Disclaimer */}
          <p className="text-xs text-slate-600 leading-relaxed border-t border-slate-800/50 pt-4">
            {data.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
