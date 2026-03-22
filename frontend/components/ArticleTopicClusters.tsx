"use client";

/**
 * components/ArticleTopicClusters.tsx — Sprint 19
 *
 * Groups article headlines into topic clusters using a lightweight
 * keyword-seed approach: each cluster is anchored by a seed keyword set,
 * and articles matching ≥1 seed word are assigned to that cluster.
 *
 * Multi-cluster membership is allowed — an article can appear in up to 2
 * clusters. An "Other" catch-all bucket holds everything that matches nothing.
 *
 * No extra API call needed — receives the already-fetched articles array.
 */

import { useMemo, useState } from "react";
import type { NewsArticleDto } from "../lib/api";

// ── Topic cluster definitions ─────────────────────────────────────────────────
// Each cluster has a label, an icon (emoji), a colour class, and seed keywords.
// Seeds are matched against lowercased headline words.

interface ClusterDef {
  id: string;
  label: string;
  icon: string;
  colorClass: string;   // Tailwind border + text colour
  bgClass: string;      // Tailwind background
  seeds: string[];
}

const CLUSTERS: ClusterDef[] = [
  {
    id: "earnings",
    label: "Earnings & Revenue",
    icon: "📊",
    colorClass: "border-emerald-700/50 text-emerald-400",
    bgClass: "bg-emerald-950/25",
    seeds: ["earnings", "revenue", "profit", "eps", "beats", "misses", "guidance",
            "quarterly", "results", "income", "margin", "ebitda", "q1", "q2", "q3", "q4"],
  },
  {
    id: "macro",
    label: "Macro & Fed",
    icon: "🏛️",
    colorClass: "border-sky-700/50 text-sky-400",
    bgClass: "bg-sky-950/25",
    seeds: ["fed", "federal", "inflation", "interest", "rates", "cpi", "gdp",
            "recession", "economy", "economic", "yields", "treasury", "macro",
            "powell", "fomc", "jobs", "unemployment", "tariff", "tariffs"],
  },
  {
    id: "analyst",
    label: "Analyst Moves",
    icon: "🔬",
    colorClass: "border-violet-700/50 text-violet-400",
    bgClass: "bg-violet-950/25",
    seeds: ["upgrade", "downgrade", "price", "target", "analyst", "rating",
            "overweight", "underweight", "neutral", "buy", "sell", "hold",
            "outperform", "underperform", "initiates", "raises", "lowers"],
  },
  {
    id: "product",
    label: "Products & Innovation",
    icon: "🚀",
    colorClass: "border-amber-700/50 text-amber-400",
    bgClass: "bg-amber-950/25",
    seeds: ["launch", "launches", "product", "announce", "announces",
            "release", "releases", "update", "unveil", "unveils",
            "partnership", "deal", "contract", "innovation", "technology",
            "ai", "model", "platform", "service", "software"],
  },
  {
    id: "legal",
    label: "Legal & Regulatory",
    icon: "⚖️",
    colorClass: "border-rose-700/50 text-rose-400",
    bgClass: "bg-rose-950/25",
    seeds: ["lawsuit", "sue", "sues", "settlement", "fine", "fined",
            "regulation", "regulatory", "sec", "ftc", "doj", "antitrust",
            "probe", "investigation", "court", "ruling", "penalty"],
  },
  {
    id: "market",
    label: "Market Moves",
    icon: "📈",
    colorClass: "border-teal-700/50 text-teal-400",
    bgClass: "bg-teal-950/25",
    seeds: ["stock", "shares", "rally", "surges", "drops", "falls",
            "rises", "gains", "loses", "trading", "market", "investors",
            "short", "squeeze", "volatility", "volume", "momentum"],
  },
];

// ── Clustering logic ──────────────────────────────────────────────────────────

interface ClusterResult {
  cluster: ClusterDef;
  articles: NewsArticleDto[];
  avgSentiment: number | null;
}

function clusterArticles(articles: NewsArticleDto[]): {
  clusters: ClusterResult[];
  other: NewsArticleDto[];
} {
  const clusterArticles: Map<string, NewsArticleDto[]> = new Map(
    CLUSTERS.map((c) => [c.id, []]),
  );
  const assignedSet = new Set<string>(); // track by title to allow ≤2 memberships
  const assignCount: Map<string, number> = new Map();

  for (const article of articles) {
    if (!article.title) continue;
    const words = new Set(
      article.title
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter(Boolean),
    );

    let matches = 0;
    for (const cluster of CLUSTERS) {
      if (matches >= 2) break; // max 2 cluster memberships
      const hit = cluster.seeds.some((seed) => words.has(seed));
      if (hit) {
        clusterArticles.get(cluster.id)!.push(article);
        assignedSet.add(article.title);
        matches++;
      }
    }
  }

  const other = articles.filter(
    (a) => a.title && !assignedSet.has(a.title),
  );

  const clusters: ClusterResult[] = CLUSTERS
    .map((cluster) => {
      const arts = clusterArticles.get(cluster.id)!;
      const scored = arts.filter((a) => a.sentiment_score !== null);
      const avg = scored.length > 0
        ? scored.reduce((s, a) => s + (a.sentiment_score ?? 0), 0) / scored.length
        : null;
      return { cluster, articles: arts, avgSentiment: avg };
    })
    .filter((r) => r.articles.length > 0)
    .sort((a, b) => b.articles.length - a.articles.length);

  return { clusters, other };
}

// ── Sentiment badge ───────────────────────────────────────────────────────────

function SentBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const label =
    score >= 0.2  ? "Bullish" :
    score >= 0.05 ? "Mildly +ve" :
    score >= -0.05 ? "Neutral" :
    score >= -0.2 ? "Mildly -ve" : "Bearish";
  const color =
    score >= 0.2  ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/50" :
    score >= 0.05 ? "text-teal-400 bg-teal-950/40 border-teal-800/50" :
    score >= -0.05 ? "text-slate-400 bg-slate-800/40 border-slate-700/50" :
    score >= -0.2 ? "text-orange-400 bg-orange-950/40 border-orange-800/50" :
    "text-rose-400 bg-rose-950/40 border-rose-800/50";
  return (
    <span className={`text-[9px] font-semibold border rounded px-1.5 py-0.5 ${color}`}>
      {label}
    </span>
  );
}

// ── Cluster card ──────────────────────────────────────────────────────────────

function ClusterCard({ result }: { result: ClusterResult }) {
  const [expanded, setExpanded] = useState(false);
  const { cluster, articles, avgSentiment } = result;
  const shown = expanded ? articles : articles.slice(0, 3);

  return (
    <div className={`rounded-xl border ${cluster.colorClass} ${cluster.bgClass} p-3 space-y-2`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none">{cluster.icon}</span>
          <span className={`text-xs font-bold ${cluster.colorClass.split(" ")[1]}`}>
            {cluster.label}
          </span>
          <span className="text-[10px] text-slate-600 font-mono">
            {articles.length}
          </span>
        </div>
        <SentBadge score={avgSentiment} />
      </div>

      {/* Article headlines */}
      <ul className="space-y-1.5">
        {shown.map((a, i) => (
          <li key={i} className="flex items-start gap-1.5">
            <span className={`mt-0.5 flex-shrink-0 h-1.5 w-1.5 rounded-full ${
              a.sentiment_label === "bullish" ? "bg-emerald-400" :
              a.sentiment_label === "bearish" ? "bg-rose-400" : "bg-slate-600"
            }`} />
            <a
              href={a.url ?? "#"}
              target={a.url ? "_blank" : undefined}
              rel="noopener noreferrer"
              className="text-[11px] text-slate-400 hover:text-slate-200 leading-tight transition-colors line-clamp-2"
              onClick={(e) => !a.url && e.preventDefault()}
            >
              {a.title}
            </a>
          </li>
        ))}
      </ul>

      {/* Expand/collapse */}
      {articles.length > 3 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className={`text-[10px] font-medium transition-colors ${cluster.colorClass.split(" ")[1]} hover:opacity-80`}
        >
          {expanded ? "Show less ↑" : `+${articles.length - 3} more ↓`}
        </button>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  articles: NewsArticleDto[];
  symbol: string;
}

export default function ArticleTopicClusters({ articles, symbol }: Props) {
  const { clusters, other } = useMemo(
    () => clusterArticles(articles),
    [articles],
  );

  if (!articles.length) return null;

  const coveredCount = articles.length - other.length;
  const coveragePct  = articles.length > 0
    ? Math.round((coveredCount / articles.length) * 100)
    : 0;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Topic Clusters</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {clusters.length} topic{clusters.length !== 1 ? "s" : ""} across {articles.length} headlines
            {" · "}{coveragePct}% classified
          </p>
        </div>
        <span className="text-[10px] text-slate-600 font-mono uppercase tracking-wider">
          {symbol}
        </span>
      </div>

      {clusters.length === 0 ? (
        <p className="text-sm text-slate-500 italic text-center py-4">
          Not enough headlines to identify topics yet.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {clusters.map((r) => (
            <ClusterCard key={r.cluster.id} result={r} />
          ))}

          {/* "Other" catch-all if there are unclassified articles */}
          {other.length > 0 && (
            <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-3 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-base">📰</span>
                <span className="text-xs font-bold text-slate-400">Other Headlines</span>
                <span className="text-[10px] text-slate-600 font-mono">{other.length}</span>
              </div>
              <ul className="space-y-1.5">
                {other.slice(0, 4).map((a, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="mt-0.5 flex-shrink-0 h-1.5 w-1.5 rounded-full bg-slate-700" />
                    <span className="text-[11px] text-slate-500 leading-tight line-clamp-2">
                      {a.title}
                    </span>
                  </li>
                ))}
                {other.length > 4 && (
                  <li className="text-[10px] text-slate-600">+{other.length - 4} more</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      <p className="text-[10px] text-slate-700">
        Headlines may appear in multiple clusters. Seed-word matching — not ML classification. Dot colour = FinBERT label.
      </p>
    </div>
  );
}
