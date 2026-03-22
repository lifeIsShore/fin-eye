"use client";

/**
 * components/ArticleList.tsx — Sprint 14 redesign
 *
 * Full article timeline with:
 *   - FinBERT sentiment chips (Bullish / Bearish / Neutral) with confidence %
 *   - Source reliability tier badges (Tier 1 / Tier 2 / Other)
 *   - Freshness indicator (age of article)
 *   - Time-grouped sections (Today / Yesterday / This week / Older)
 *   - Score bar showing magnitude of sentiment
 *   - Filter bar: All / Bullish / Bearish / Neutral
 */

import { useState, useMemo } from "react";
import type { NewsArticleDto } from "../lib/api";

// ── Source reliability tiers ───────────────────────────────────────────────

const TIER1_SOURCES = new Set([
  "reuters", "bloomberg", "financial times", "ft", "wall street journal", "wsj",
  "barrons", "barron's", "cnbc", "marketwatch", "seeking alpha", "the motley fool",
  "motley fool", "yahoo finance", "benzinga", "ap", "associated press",
  "business insider", "fortune", "forbes",
]);

const TIER2_SOURCES = new Set([
  "investopedia", "zacks", "the street", "thestreet", "briefing", "streetinsider",
  "globe newswire", "pr newswire", "businesswire", "accesswire",
]);

function sourceTier(source: string | null): "tier1" | "tier2" | "other" {
  if (!source) return "other";
  const lower = source.toLowerCase();
  if (TIER1_SOURCES.has(lower)) return "tier1";
  if (TIER2_SOURCES.has(lower)) return "tier2";
  // Partial match for common publishers
  for (const t1 of TIER1_SOURCES) {
    if (lower.includes(t1) || t1.includes(lower)) return "tier1";
  }
  for (const t2 of TIER2_SOURCES) {
    if (lower.includes(t2) || t2.includes(lower)) return "tier2";
  }
  return "other";
}

const TIER_CONFIG = {
  tier1: { label: "Tier 1",  bg: "bg-emerald-950/40 border-emerald-800/50 text-emerald-400" },
  tier2: { label: "Tier 2",  bg: "bg-sky-950/40 border-sky-800/50 text-sky-400" },
  other: { label: "Source",  bg: "bg-slate-800/60 border-slate-700/50 text-slate-500" },
} as const;

// ── Sentiment helpers ──────────────────────────────────────────────────────

type SentimentFilter = "all" | "bullish" | "bearish" | "neutral";

function deriveSentiment(article: NewsArticleDto): "bullish" | "bearish" | "neutral" {
  if (article.sentiment_label) {
    const l = article.sentiment_label.toLowerCase();
    if (l === "bullish" || l === "positive") return "bullish";
    if (l === "bearish" || l === "negative") return "bearish";
    return "neutral";
  }
  const s = article.sentiment_score;
  if (s == null) return "neutral";
  if (s > 0.15) return "bullish";
  if (s < -0.15) return "bearish";
  return "neutral";
}

const SENT_CHIP: Record<string, string> = {
  bullish: "bg-emerald-950/40 border-emerald-800/50 text-emerald-300",
  bearish: "bg-rose-950/40 border-rose-800/50 text-rose-300",
  neutral: "bg-slate-800/50 border-slate-700/50 text-slate-400",
};

const SENT_LABEL: Record<string, string> = {
  bullish: "Bullish", bearish: "Bearish", neutral: "Neutral",
};

const SENT_BAR: Record<string, string> = {
  bullish: "bg-emerald-500", bearish: "bg-rose-500", neutral: "bg-slate-600",
};

// ── Age helpers ────────────────────────────────────────────────────────────

function ageLabel(publishedAt: string): string {
  const diff = Date.now() - new Date(publishedAt).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(publishedAt).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function ageDotColor(publishedAt: string): string {
  const hrs = (Date.now() - new Date(publishedAt).getTime()) / 3_600_000;
  if (hrs < 6) return "bg-emerald-400";
  if (hrs < 24) return "bg-sky-400";
  if (hrs < 72) return "bg-amber-400";
  return "bg-slate-600";
}

type Group = "Today" | "Yesterday" | "This week" | "Older";

function timeGroup(publishedAt: string): Group {
  const diff = Date.now() - new Date(publishedAt).getTime();
  const hrs = diff / 3_600_000;
  if (hrs < 24)  return "Today";
  if (hrs < 48)  return "Yesterday";
  if (hrs < 168) return "This week";
  return "Older";
}

const GROUP_ORDER: Group[] = ["Today", "Yesterday", "This week", "Older"];

// ── Article card ───────────────────────────────────────────────────────────

function ArticleCard({ article }: { article: NewsArticleDto }) {
  const sentiment = deriveSentiment(article);
  const tier      = sourceTier(article.source);
  const conf      = article.finbert_score != null
    ? Math.round(article.finbert_score * 100)
    : null;

  // Score bar magnitude: map sentiment_score (-1 to +1) → 0–100%
  const barWidth = article.sentiment_score != null
    ? Math.round(Math.abs(article.sentiment_score) * 100)
    : conf ?? 0;

  return (
    <div className="group relative flex gap-3 py-3 px-1">
      {/* Left timeline line + dot */}
      <div className="flex flex-col items-center flex-shrink-0 w-4">
        <span className={`h-2.5 w-2.5 rounded-full flex-shrink-0 mt-1.5 ${ageDotColor(article.published_at)}`} />
        <div className="w-px flex-1 bg-slate-800/60 mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-1">
        {/* Title */}
        {article.url ? (
          <a href={article.url} target="_blank" rel="noopener noreferrer" className="group/link">
            <p className="text-sm font-medium text-slate-200 group-hover/link:text-sky-400 transition-colors leading-snug line-clamp-2">
              {article.title}
            </p>
          </a>
        ) : (
          <p className="text-sm font-medium text-slate-200 leading-snug line-clamp-2">
            {article.title}
          </p>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
          {/* Source + tier */}
          <span className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${TIER_CONFIG[tier].bg}`}>
            {article.source ?? "Unknown"} · {TIER_CONFIG[tier].label}
          </span>

          {/* Age */}
          <span className="text-[10px] text-slate-600">
            {ageLabel(article.published_at)}
          </span>
        </div>

        {/* Sentiment chip + confidence + score bar */}
        <div className="flex items-center gap-2 mt-2">
          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${SENT_CHIP[sentiment]}`}>
            {sentiment === "bullish" ? "↑" : sentiment === "bearish" ? "↓" : "→"}{" "}
            {SENT_LABEL[sentiment]}
            {conf != null && (
              <span className="opacity-70 font-normal">{conf}%</span>
            )}
          </span>

          {/* Score magnitude bar */}
          {barWidth > 0 && (
            <div className="flex-1 max-w-[80px] h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full rounded-full ${SENT_BAR[sentiment]}`}
                style={{ width: `${Math.min(100, barWidth)}%` }}
              />
            </div>
          )}

          {/* Raw score */}
          {article.sentiment_score != null && (
            <span className="text-[10px] text-slate-600 font-mono tabular-nums">
              {article.sentiment_score >= 0 ? "+" : ""}{article.sentiment_score.toFixed(2)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface Props {
  articles: NewsArticleDto[];
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;
type PageSize = typeof PAGE_SIZE_OPTIONS[number];

export function ArticleList({ articles }: Props) {
  const [filter, setFilter]     = useState<SentimentFilter>("all");
  const [pageSize, setPageSize] = useState<PageSize>(25);
  const [page, setPage]         = useState(0);

  const handleFilterChange   = (f: SentimentFilter) => { setFilter(f); setPage(0); };
  const handlePageSizeChange = (ps: PageSize) => { setPageSize(ps); setPage(0); };

  const filtered = useMemo(() => {
    if (filter === "all") return articles;
    return articles.filter((a) => deriveSentiment(a) === filter);
  }, [articles, filter]);

  const totalPages = Math.ceil(filtered.length / pageSize);

  const paginated = useMemo(() => {
    const start = page * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page, pageSize]);

  // Count per filter
  const counts = useMemo(() => {
    const c = { bullish: 0, bearish: 0, neutral: 0 };
    articles.forEach((a) => { c[deriveSentiment(a)]++; });
    return c;
  }, [articles]);

  // Group by time (based on paginated slice so group headers reflect current page)
  const grouped = useMemo(() => {
    const map: Partial<Record<Group, NewsArticleDto[]>> = {};
    for (const a of paginated) {
      const g = timeGroup(a.published_at);
      if (!map[g]) map[g] = [];
      map[g]!.push(a);
    }
    return map;
  }, [paginated]);

  if (!articles.length) {
    return (
      <p className="text-sm text-slate-500 py-4">No recent articles found for this symbol.</p>
    );
  }

  const FILTER_OPTS: { key: SentimentFilter; label: string; count: number }[] = [
    { key: "all",     label: "All",     count: articles.length },
    { key: "bullish", label: "Bullish", count: counts.bullish  },
    { key: "bearish", label: "Bearish", count: counts.bearish  },
    { key: "neutral", label: "Neutral", count: counts.neutral  },
  ];

  const startIdx = page * pageSize + 1;
  const endIdx   = Math.min((page + 1) * pageSize, filtered.length);

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/50 p-1 w-fit">
        {FILTER_OPTS.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => handleFilterChange(key)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              filter === key
                ? "bg-slate-700 text-slate-100"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {label}
            <span className={`text-[10px] rounded-full px-1.5 py-0.5 ${
              filter === key ? "bg-slate-600 text-slate-200" : "bg-slate-800/60 text-slate-600"
            }`}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-[10px] text-slate-600">
        <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Fresh (&lt;6h)</span>
        <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-sky-400" /> Today</span>
        <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-amber-400" /> &lt;3 days</span>
        <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-slate-600" /> Older</span>
        <span className="flex items-center gap-1 ml-auto text-slate-500">
          Click a headline to read the full article ↗
        </span>
      </div>

      {/* Timeline groups */}
      {paginated.length === 0 && (
        <p className="text-sm text-slate-600 py-4 text-center">No articles match this filter.</p>
      )}
      {GROUP_ORDER.map((group) => {
        const items = grouped[group];
        if (!items?.length) return null;
        return (
          <div key={group}>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 mb-1 pl-7">
              {group} · {items.length} article{items.length !== 1 ? "s" : ""}
            </p>
            <div className="divide-y divide-slate-800/40">
              {items.map((article) => (
                <ArticleCard
                  key={`${article.symbol}-${article.title}-${article.published_at}`}
                  article={article}
                />
              ))}
            </div>
          </div>
        );
      })}

      {/* Pagination footer */}
      {filtered.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-3 mt-1">
          {/* Prev / page info / next */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 border border-slate-800 hover:border-slate-700 transition"
            >
              ←
            </button>
            <span className="text-[11px] text-slate-500 tabular-nums">
              {startIdx}–{endIdx} of {filtered.length}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2.5 py-1 rounded-md text-xs text-slate-400 hover:text-slate-200 disabled:opacity-30 border border-slate-800 hover:border-slate-700 transition"
            >
              →
            </button>
          </div>

          {/* Page-size selector */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-600">Show</span>
            <div className="flex gap-0.5 rounded-lg border border-slate-800 bg-slate-900/50 p-0.5">
              {PAGE_SIZE_OPTIONS.map((ps) => (
                <button
                  key={ps}
                  onClick={() => handlePageSizeChange(ps)}
                  className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                    pageSize === ps
                      ? "bg-slate-700 text-slate-100"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {ps}
                </button>
              ))}
            </div>
            <span className="text-[11px] text-slate-600">per page</span>
          </div>
        </div>
      )}
    </div>
  );
}
