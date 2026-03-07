"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  fetchInsiderAnalysis,
  type InsiderAnalysisDto,
  type InsiderTransactionDto,
  type InsiderSentimentDto,
} from "../../lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtShares(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function fmtValue(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000)     return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000)         return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toLocaleString()}`;
}

function fmtPrice(n: number | null): string {
  if (n == null) return "—";
  return `$${n.toFixed(2)}`;
}

function fmtDate(d: string): string {
  if (!d) return "—";
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 58) return "text-teal-400";
  if (score >= 42) return "text-slate-300";
  if (score >= 30) return "text-orange-400";
  return "text-rose-400";
}

function scoreBadge(label: string): string {
  const map: Record<string, string> = {
    "Bullish":        "bg-emerald-900/40 text-emerald-300 border-emerald-700/50",
    "Mildly Bullish": "bg-teal-900/40 text-teal-300 border-teal-700/50",
    "Neutral":        "bg-slate-800/60 text-slate-300 border-slate-700/50",
    "Mildly Bearish": "bg-orange-900/40 text-orange-300 border-orange-700/50",
    "Bearish":        "bg-rose-900/40 text-rose-300 border-rose-700/50",
  };
  return map[label] ?? "bg-slate-800/60 text-slate-300 border-slate-700/50";
}

function txnRowColor(t: InsiderTransactionDto): string {
  if (t.is_buy)  return "border-l-2 border-emerald-500/50";
  if (t.is_sell) return "border-l-2 border-rose-500/50";
  return "border-l-2 border-slate-700/50";
}

function txnTypeBadge(t: InsiderTransactionDto): string {
  if (t.is_buy)  return "bg-emerald-900/40 text-emerald-300 border-emerald-700/40";
  if (t.is_sell) return "bg-rose-900/40 text-rose-300 border-rose-700/40";
  return "bg-slate-800/50 text-slate-400 border-slate-700/40";
}

function txnTypeShortLabel(t: InsiderTransactionDto): string {
  if (t.transaction_type === "P") return "Buy";
  if (t.transaction_type === "S") return "Sell";
  if (t.transaction_type === "A") return "Award";
  if (t.transaction_type === "M" || t.transaction_type === "X") return "Option Ex.";
  if (t.transaction_type === "F") return "Tax W/H";
  if (t.transaction_type === "D") return "Dispose";
  return t.transaction_type;
}

// ─── Sentiment Arc Gauge ──────────────────────────────────────────────────────

function SentimentGauge({ sentiment }: { sentiment: InsiderSentimentDto }) {
  const pct = Math.round(sentiment.score);
  const fillColor =
    pct >= 70 ? "#10b981" :
    pct >= 58 ? "#14b8a6" :
    pct >= 42 ? "#64748b" :
    pct >= 30 ? "#f97316" :
               "#f87171";

  // Arc: from left (180°) to right (0°), progress = score/100
  const angle   = Math.PI - (pct / 100) * Math.PI;
  const arcX    = 80 + 66 * Math.cos(angle);
  const arcY    = 88 - 66 * Math.sin(angle);
  const largeArc = pct > 50 ? 1 : 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative flex items-center justify-center">
        <svg width="160" height="92" viewBox="0 0 160 92" fill="none">
          <path d="M 14 88 A 66 66 0 0 1 146 88" stroke="#1e293b" strokeWidth="13" strokeLinecap="round" fill="none" />
          {pct > 0 && (
            <path
              d={`M 14 88 A 66 66 0 ${largeArc} 1 ${arcX.toFixed(2)} ${arcY.toFixed(2)}`}
              stroke={fillColor}
              strokeWidth="13"
              strokeLinecap="round"
              fill="none"
            />
          )}
          <line x1="80" y1="22" x2="80" y2="36" stroke="#334155" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div className="absolute bottom-1 flex flex-col items-center leading-none">
          <span className={`text-4xl font-black tabular-nums ${scoreColor(sentiment.score)}`}>{pct}</span>
          <span className="text-[10px] text-slate-600 mt-0.5">out of 100</span>
        </div>
      </div>

      <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${scoreBadge(sentiment.label)}`}>
        {sentiment.label}
      </span>

      {/* Gradient bar */}
      <div className="w-full space-y-1 px-1">
        <div className="flex justify-between text-[9px] text-slate-600">
          <span>Bearish</span><span>Neutral</span><span>Bullish</span>
        </div>
        <div className="relative h-1.5 w-full rounded-full overflow-hidden">
          <div className="absolute inset-0" style={{ background: "linear-gradient(to right,#f87171,#f97316,#64748b,#14b8a6,#10b981)" }} />
          <div className="absolute top-1/2 h-3.5 w-1.5 -translate-y-1/2 -translate-x-1/2 rounded-sm bg-white shadow-md"
               style={{ left: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}

// ─── Buy / Sell Balance ───────────────────────────────────────────────────────

function BalanceCard({ sentiment }: { sentiment: InsiderSentimentDto }) {
  const total   = sentiment.buy_shares + sentiment.sell_shares;
  const buyPct  = total > 0 ? (sentiment.buy_shares / total) * 100 : 50;
  const sellPct = 100 - buyPct;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Buy / Sell Balance · {sentiment.lookback_days}d window
      </h3>

      <div className="flex h-3.5 w-full overflow-hidden rounded-full">
        <div className="bg-emerald-500" style={{ width: `${buyPct.toFixed(1)}%` }} />
        <div className="bg-rose-500"    style={{ width: `${sellPct.toFixed(1)}%` }} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-emerald-800/40 bg-emerald-950/30 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-[10px] font-bold uppercase text-emerald-400">Purchases</span>
          </div>
          <p className="text-xl font-black text-emerald-300">{fmtShares(sentiment.buy_shares)}</p>
          <p className="text-[10px] text-slate-500">{sentiment.buy_transactions} transactions</p>
          {sentiment.buy_value != null && (
            <p className="text-xs font-semibold text-emerald-400 mt-0.5">{fmtValue(sentiment.buy_value)}</p>
          )}
        </div>

        <div className="rounded-lg border border-rose-800/40 bg-rose-950/30 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="h-2 w-2 rounded-full bg-rose-500" />
            <span className="text-[10px] font-bold uppercase text-rose-400">Sales</span>
          </div>
          <p className="text-xl font-black text-rose-300">{fmtShares(sentiment.sell_shares)}</p>
          <p className="text-[10px] text-slate-500">{sentiment.sell_transactions} transactions</p>
          {sentiment.sell_value != null && (
            <p className="text-xs font-semibold text-rose-400 mt-0.5">{fmtValue(sentiment.sell_value)}</p>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-3 flex items-center justify-between">
        <div>
          <p className="text-[10px] text-slate-500 uppercase font-semibold tracking-wide">Net (180d)</p>
          <p className={`text-base font-bold ${sentiment.net_shares >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
            {sentiment.net_shares >= 0 ? "+" : ""}{fmtShares(Math.abs(sentiment.net_shares))} shares
          </p>
        </div>
        {sentiment.net_value != null && (
          <p className={`text-sm font-bold ${sentiment.net_value >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {sentiment.net_value >= 0 ? "+" : "−"}{fmtValue(Math.abs(sentiment.net_value))}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Transactions Table ───────────────────────────────────────────────────────

type FilterMode = "all" | "buy" | "sell";

function TransactionTable({ transactions }: { transactions: InsiderTransactionDto[] }) {
  const [filter, setFilter] = useState<FilterMode>("all");

  const visible = transactions.filter(t => {
    if (filter === "buy")  return t.is_buy;
    if (filter === "sell") return t.is_sell;
    return true;
  });

  const btn = (mode: FilterMode, label: string, count: number) => (
    <button
      onClick={() => setFilter(mode)}
      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
        filter === mode ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
      }`}
    >
      {label}
      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold ${
        filter === mode ? "bg-slate-600 text-slate-200" : "bg-slate-800 text-slate-500"
      }`}>{count}</span>
    </button>
  );

  const buyCount  = transactions.filter(t => t.is_buy).length;
  const sellCount = transactions.filter(t => t.is_sell).length;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Form 4 Transactions
        </h3>
        <div className="flex gap-1">
          {btn("all", "All", transactions.length)}
          {btn("buy", "Buys", buyCount)}
          {btn("sell", "Sells", sellCount)}
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-600">
          No {filter === "all" ? "" : filter} transactions in this filing set.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/80">
                {["Filed", "Insider", "Type", "Shares", "Price", "Value", "Held After"].map(h => (
                  <th key={h} className={`px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600 ${h === "Shares" || h === "Price" || h === "Value" || h === "Held After" ? "text-right" : "text-left"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {visible.map((t, i) => (
                <tr key={`${t.accession_number}-${i}`}
                    className={`${txnRowColor(t)} hover:bg-slate-800/25 transition-colors`}>
                  <td className="px-4 py-2.5 text-xs text-slate-400 whitespace-nowrap">
                    {fmtDate(t.transaction_date)}
                  </td>
                  <td className="px-4 py-2.5 max-w-[170px]">
                    <p className="text-xs font-medium text-slate-200 truncate">{t.insider_name}</p>
                    <p className="text-[10px] text-slate-500 truncate">{t.insider_title}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${txnTypeBadge(t)}`}>
                      {txnTypeShortLabel(t)}
                    </span>
                  </td>
                  <td className={`px-4 py-2.5 text-right text-xs font-mono font-semibold ${t.is_buy ? "text-emerald-300" : t.is_sell ? "text-rose-300" : "text-slate-400"}`}>
                    {t.is_sell ? "−" : ""}{fmtShares(t.shares)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono text-slate-400">
                    {fmtPrice(t.price_per_share)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono text-slate-300">
                    {fmtValue(t.total_value)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-xs font-mono text-slate-500">
                    {t.shares_after != null ? fmtShares(t.shares_after) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="border-t border-slate-800 px-4 py-2 text-[10px] text-slate-600">
        Showing {visible.length} transaction{visible.length !== 1 ? "s" : ""} · Source: SEC EDGAR Form 4
      </div>
    </div>
  );
}

// ─── Methodology ─────────────────────────────────────────────────────────────

function MethodologyCard() {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Score Methodology</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Data Source</p>
          <p>SEC EDGAR Form 4 — required within 2 business days of any transaction by directors, officers, and &gt;10% shareholders. No API key required.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">What Counts</p>
          <p>Only open-market purchases (P) and sales (S) are counted. Awards, option exercises, and tax withholding are excluded — they are not discretionary signals.</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3 space-y-1">
          <p className="font-semibold text-slate-200">Scoring</p>
          <p>Score = 100 × buy_value ÷ (buy + sell value), last 180 days. 0 = all selling, 100 = all buying, 50 = balanced. Cached for 1 hour.</p>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InsidersPage() {
  const [inputValue, setInputValue] = useState("AAPL");
  const [symbol, setSymbol]         = useState("AAPL");

  const { data, error, isLoading } = useSWR<InsiderAnalysisDto>(
    symbol,
    fetchInsiderAnalysis,
    { refreshInterval: 3_600_000, keepPreviousData: true },
  );

  const handleSearch = () => {
    const t = inputValue.trim().toUpperCase();
    if (t) setSymbol(t);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-end gap-4 justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Insider Activity</h1>
            <p className="text-sm text-slate-500 mt-0.5">SEC EDGAR Form 4 · Open-market buy/sell sentiment · 180-day window</p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="Ticker"
              className="w-28 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:border-slate-500 focus:outline-none"
            />
            <button
              onClick={handleSearch}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
            >
              Search
            </button>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && !data && (
          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <p className="text-sm text-slate-400">
              Fetching Form 4 filings from SEC EDGAR for <span className="font-semibold text-slate-200">{symbol}</span>…
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-rose-800/50 bg-rose-950/30 p-4 space-y-1">
            <p className="text-sm font-semibold text-rose-400">Unable to load insider data</p>
            <p className="text-xs text-rose-400/80">{error.message}</p>
            <p className="text-xs text-slate-500 pt-1">
              Only US-listed securities with SEC EDGAR filings are supported. ETFs and foreign listings may not have Form 4 data.
            </p>
          </div>
        )}

        {data && (
          <>
            {/* Company strip */}
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3">
              <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm font-black text-slate-100">{data.symbol}</span>
              <span className="text-sm text-slate-300">{data.company_name}</span>
              <a
                href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${data.cik}&type=4&dateb=&owner=include&count=40`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-blue-400 hover:text-blue-300 underline underline-offset-2"
              >
                View on EDGAR ↗
              </a>
              <span className="ml-auto text-[10px] text-slate-600">CIK {data.cik} · {data.total_filings_found} Form 4s found</span>
            </div>

            {/* Gauge + Balance */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Insider Sentiment Score</h2>
                <SentimentGauge sentiment={data.sentiment} />
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-lg bg-slate-800/50 py-2.5">
                    <p className="text-xl font-black text-emerald-300">{data.sentiment.buy_transactions}</p>
                    <p className="text-[10px] text-slate-500">Purchase txns</p>
                  </div>
                  <div className="rounded-lg bg-slate-800/50 py-2.5">
                    <p className="text-xl font-black text-rose-300">{data.sentiment.sell_transactions}</p>
                    <p className="text-[10px] text-slate-500">Sale txns</p>
                  </div>
                </div>
              </div>

              <BalanceCard sentiment={data.sentiment} />
            </div>

            {/* Transactions */}
            <TransactionTable transactions={data.transactions} />

            {/* Methodology */}
            <MethodologyCard />

            {/* Disclaimer */}
            <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 px-4 py-3">
              <p className="text-[10px] leading-relaxed text-slate-600">{data.disclaimer}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
