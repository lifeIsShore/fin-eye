import Link from "next/link";
import { fetchMacroLatest } from "../lib/api";

export default async function HomePage() {
  let macroScore: { score: number; label: string } | null = null;

  try {
    const latest = await fetchMacroLatest();
    macroScore = latest.macro_score;
  } catch {
    macroScore = null;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-lg font-semibold tracking-tight">Dashboard</h2>
        <p className="mt-1 text-sm text-slate-400">
          This early dashboard shows a high-level Macro Score and links to the
          dedicated Macro and News &amp; Sentiment tabs. GAS and technical
          layers will be added in later stories.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/macro"
            className="inline-flex items-center rounded-md bg-sky-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-sky-400"
          >
            Open Macro tab
          </Link>
          <Link
            href="/news-sentiment"
            className="inline-flex items-center rounded-md border border-sky-500/40 px-4 py-2 text-sm font-medium text-sky-300 transition hover:bg-slate-900"
          >
            Open News &amp; Sentiment tab
          </Link>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h3 className="text-sm font-semibold text-slate-100">
          Macro Score summary
        </h3>
        {macroScore ? (
          <div className="mt-2 flex items-baseline gap-4">
            <p className="text-4xl font-semibold text-sky-400">
              {macroScore.score.toFixed(1)}
            </p>
            <div className="space-y-1 text-sm">
              <p className="text-slate-200">{macroScore.label}</p>
              <p className="text-xs text-slate-500 max-w-xl">
                Macro Score condenses rates, inflation, labour market, yield
                curve, and volatility into a 0–100 summary of how supportive or
                stressed the environment is. It is educational context, not a
                trading signal.
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-400">
            Macro Score is not available yet. Once the macro refresh job has
            populated indicators in the backend, it will appear here.
          </p>
        )}
      </section>
    </div>
  );
}

