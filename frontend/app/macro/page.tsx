"use client";

import useSWR from "swr";
import { fetchMacroLatest } from "../../lib/api";

const fetcher = () => fetchMacroLatest();

export default function MacroPage() {
  const { data, error, isLoading } = useSWR("macro-latest", fetcher);

  const macroScore = data?.macro_score ?? null;
  const indicators = data?.data ?? {};

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-lg font-semibold tracking-tight">Macro dashboard</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          High-level economic backdrop combining rates, inflation, labour
          market, yield curve and volatility into a simple Macro Score and
          interpretations. Educational view only, not a trading signal.
        </p>
      </section>

      <div className="grid gap-6 md:grid-cols-5">
        <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 md:col-span-2">
          <h3 className="text-sm font-semibold text-slate-100">Macro Score</h3>
          {isLoading && !data && !error && (
            <p className="text-sm text-slate-400">Loading macro data…</p>
          )}
          {error && (
            <p className="text-sm text-rose-400">
              Could not load macro data. Ensure the backend is running and has
              refreshed indicators.
            </p>
          )}
          {macroScore && (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Macro Score (0–100)
              </p>
              <p className="text-4xl font-semibold text-sky-400">
                {macroScore.score.toFixed(1)}
              </p>
              <p className="text-sm text-slate-200">{macroScore.label}</p>
              <p className="text-[11px] text-slate-500">
                Higher scores indicate a more supportive macro environment,
                while lower scores indicate stress. This is a simplified
                synthesis of several indicators as described in the PRD.
              </p>
            </div>
          )}
          {!macroScore && !isLoading && !error && (
            <p className="text-sm text-slate-400">
              Macro score is not available yet. Run the macro refresh job to
              populate indicators.
            </p>
          )}
        </section>

        <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 md:col-span-3">
          <h3 className="text-sm font-semibold text-slate-100">
            Key indicators (latest values)
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-xs">
            {Object.entries(indicators).map(([key, value]) => {
              const v = value as {
                value: number | null;
                date: string | null;
                interpretation: string;
              };
              const labelMap: Record<string, string> = {
                fed_funds_rate: "Fed Funds Rate",
                unemployment_rate: "Unemployment",
                yield_spread_10y_2y: "2–10yr Spread",
                cpi_yoy: "CPI YoY",
                vix: "VIX",
              };
              const title = labelMap[key] ?? key;

              return (
                <div
                  key={key}
                  className="rounded-lg border border-slate-800 bg-slate-950/60 p-3"
                >
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">
                    {title}
                  </p>
                  <p className="mt-1 text-base font-semibold text-slate-50">
                    {v.value !== null ? v.value : "n/a"}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {v.date ?? "No date"}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {v.interpretation}
                  </p>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}

