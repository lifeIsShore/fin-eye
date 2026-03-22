"use client";

/**
 * components/SentimentKeywordCloud.tsx — Sprint 17
 *
 * Extracts keywords from article headlines and renders them as a Recharts
 * Treemap — cell size = frequency, cell colour = aggregate sentiment.
 *
 * No extra API call needed: receives the articles array already fetched by
 * the news-sentiment page.
 */

import { useMemo } from "react";
import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import type { NewsArticleDto } from "../lib/api";

// ── Stop-words to filter out ──────────────────────────────────────────────────

const STOP_WORDS = new Set([
  "the","a","an","and","or","but","in","on","at","to","for","of","with","is",
  "are","was","were","be","been","has","have","had","will","would","could","should",
  "its","it","as","by","from","that","this","these","those","not","no","new","up",
  "after","after","amid","about","over","into","than","as","than","their","they",
  "says","said","he","she","we","you","i","s","re","ve","ll","don","t","can","does",
  "do","did","if","while","when","how","what","which","who","why","where","per",
  "top","vs","key","amid","amid","amid","just","also","may","still","than","more",
  "now","here","back","report","reports","quarterly","q1","q2","q3","q4","ytd",
  "year","years","month","months","week","weeks","billion","million","trillion",
]);

// ── Sentiment colour mapping ───────────────────────────────────────────────────

function sentimentColor(score: number): string {
  if (score >= 0.25)  return "#10b981"; // emerald
  if (score >= 0.05)  return "#34d399"; // emerald light
  if (score >= -0.05) return "#64748b"; // slate
  if (score >= -0.25) return "#fb923c"; // orange
  return "#f87171";                     // rose
}

// ── Extraction logic ──────────────────────────────────────────────────────────

interface KeywordEntry {
  name: string;
  size: number;          // frequency
  avgSentiment: number;  // avg sentiment_score across headlines containing this word
  fill: string;
}

function extractKeywords(articles: NewsArticleDto[]): KeywordEntry[] {
  const freq: Record<string, { count: number; sentSum: number }> = {};

  for (const a of articles) {
    if (!a.title) continue;
    const score = a.sentiment_score ?? 0;
    const words = a.title
      .toLowerCase()
      .replace(/[^a-z0-9\s'-]/g, " ")
      .split(/\s+/)
      .map(w => w.replace(/^['-]+|['-]+$/g, "")) // strip leading/trailing punctuation
      .filter(w => w.length >= 4 && !STOP_WORDS.has(w) && !/^\d+$/.test(w));

    const seen = new Set<string>();
    for (const word of words) {
      if (seen.has(word)) continue;
      seen.add(word);
      if (!freq[word]) freq[word] = { count: 0, sentSum: 0 };
      freq[word].count++;
      freq[word].sentSum += score;
    }
  }

  return Object.entries(freq)
    .filter(([, v]) => v.count >= 2) // only show words appearing ≥ 2 times
    .map(([word, { count, sentSum }]) => {
      const avg = sentSum / count;
      return {
        name:         word.charAt(0).toUpperCase() + word.slice(1),
        size:         count,
        avgSentiment: avg,
        fill:         sentimentColor(avg),
      };
    })
    .sort((a, b) => b.size - a.size)
    .slice(0, 40); // top 40 keywords
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

const CloudTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d: KeywordEntry = payload[0].payload;
  const sentLabel =
    d.avgSentiment >= 0.25  ? "Bullish" :
    d.avgSentiment >= 0.05  ? "Mildly Bullish" :
    d.avgSentiment >= -0.05 ? "Neutral" :
    d.avgSentiment >= -0.25 ? "Mildly Bearish" : "Bearish";

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs shadow-xl space-y-0.5">
      <p className="font-bold text-slate-100">{d.name}</p>
      <p className="text-slate-400">{d.size} headline{d.size !== 1 ? "s" : ""}</p>
      <p style={{ color: d.fill }} className="font-semibold">{sentLabel}</p>
    </div>
  );
};

// ── Custom content renderer ───────────────────────────────────────────────────

const CustomCell = (props: any) => {
  const { x, y, width, height, name, fill, size } = props;
  const showLabel = width > 40 && height > 20;
  return (
    <g>
      <rect
        x={x + 1} y={y + 1}
        width={Math.max(0, width - 2)} height={Math.max(0, height - 2)}
        style={{ fill, fillOpacity: 0.75, stroke: "#0f172a", strokeWidth: 2 }}
        rx={4}
      />
      {showLabel && (
        <>
          <text
            x={x + width / 2}
            y={y + height / 2 - (size > 3 ? 6 : 0)}
            textAnchor="middle"
            dominantBaseline="middle"
            style={{
              fill: "#f1f5f9",
              fontSize: Math.min(14, Math.max(9, width / 5)),
              fontWeight: 600,
              fontFamily: "sans-serif",
            }}
          >
            {name}
          </text>
          {size > 3 && width > 60 && (
            <text
              x={x + width / 2}
              y={y + height / 2 + 10}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{ fill: "#94a3b8", fontSize: 9, fontFamily: "sans-serif" }}
            >
              ×{size}
            </text>
          )}
        </>
      )}
    </g>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  articles: NewsArticleDto[];
  symbol: string;
}

export default function SentimentKeywordCloud({ articles, symbol }: Props) {
  const keywords = useMemo(() => extractKeywords(articles), [articles]);

  if (!articles.length) return null;

  if (keywords.length < 3) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-6 text-center">
        <p className="text-sm text-slate-500">
          Not enough headlines to build a keyword cloud yet.
        </p>
      </div>
    );
  }

  // Legend items
  const LEGEND = [
    { color: "#10b981", label: "Bullish" },
    { color: "#64748b", label: "Neutral" },
    { color: "#f87171", label: "Bearish" },
  ];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Headline Keywords</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {keywords.length} keywords from {articles.length} headlines · size = frequency · colour = sentiment
          </p>
        </div>
        <div className="flex gap-3">
          {LEGEND.map(({ color, label }) => (
            <span key={label} className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <span className="h-2.5 w-2.5 rounded-sm flex-shrink-0" style={{ background: color, opacity: 0.75 }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={keywords}
            dataKey="size"
            aspectRatio={4 / 3}
            content={<CustomCell />}
            isAnimationActive={false}
          >
            <Tooltip content={<CloudTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>

      <p className="text-[10px] text-slate-600">
        Stop-words, numbers, and words appearing only once are excluded.
        Sentiment colour = average FinBERT score across matching headlines.
      </p>
    </div>
  );
}
