import type { SentimentSourceBreakdownEntryDto } from "../lib/api";

interface Props {
  rows: SentimentSourceBreakdownEntryDto[];
}

export function SourceBreakdownTable({ rows }: Props) {
  if (!rows.length) {
    return (
      <p className="text-sm text-slate-400">
        No per-source sentiment data available for this symbol yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="min-w-full border-collapse text-xs">
        <thead className="bg-slate-900/70">
          <tr>
            <th className="px-3 py-2 text-left font-semibold text-slate-300">
              Source
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-300">
              Bullish
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-300">
              Bearish
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-300">
              Neutral
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-300">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const total = row.positive + row.negative + row.neutral;
            return (
              <tr key={row.source} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-100">{row.source}</td>
                <td className="px-3 py-2 text-right text-emerald-400">
                  {row.positive}
                </td>
                <td className="px-3 py-2 text-right text-rose-400">
                  {row.negative}
                </td>
                <td className="px-3 py-2 text-right text-slate-400">
                  {row.neutral}
                </td>
                <td className="px-3 py-2 text-right text-slate-300">
                  {total}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

