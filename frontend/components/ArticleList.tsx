import type { NewsArticleDto } from "../lib/api";

interface Props {
  articles: NewsArticleDto[];
}

export function ArticleList({ articles }: Props) {
  if (!articles.length) {
    return (
      <p className="text-sm text-slate-400">
        No recent articles found for this symbol.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-slate-800">
      {articles.map((article) => {
        const published = new Date(article.published_at);
        const formatted = published.toLocaleString(undefined, {
          month: "short",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        });

        // Prefer sentiment_label from FinBERT if available, else derive from VADER score
        const sentimentLabel = article.sentiment_label
          ? article.sentiment_label.charAt(0).toUpperCase() + article.sentiment_label.slice(1)
          : (() => {
              const score = article.sentiment_score;
              if (score === null) return "Neutral";
              if (score > 0.2)  return "Bullish";
              if (score < -0.2) return "Bearish";
              return "Neutral";
            })();

        const scoreColor =
          sentimentLabel === "Bullish" ? "text-emerald-400" :
          sentimentLabel === "Bearish" ? "text-rose-400" :
                                         "text-slate-300";

        const score = article.sentiment_score;

        return (
          <li key={`${article.symbol}-${article.title}-${article.published_at}`} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {/* Phase 5.7 — Clickable URL if available, plain title otherwise */}
                {article.url ? (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group"
                  >
                    <p className="text-sm font-medium text-slate-50 group-hover:text-sky-400 transition-colors leading-snug">
                      {article.title}
                    </p>
                    <span className="text-[11px] text-sky-600 group-hover:text-sky-400 transition-colors mt-0.5 inline-block">
                      Read article →
                    </span>
                  </a>
                ) : (
                  <p className="text-sm font-medium text-slate-50 leading-snug">
                    {article.title}
                  </p>
                )}
                <p className="mt-1 text-xs text-slate-500">
                  {article.source ?? "Unknown source"} · {formatted}
                </p>
              </div>

              <div className="shrink-0 text-right">
                <p className={`text-xs font-semibold ${scoreColor}`}>
                  {sentimentLabel}
                </p>
                {score !== null && (
                  <p className="text-xs text-slate-400">
                    Score: {score.toFixed(2)}
                  </p>
                )}
                {article.finbert_score !== null && article.finbert_score !== undefined && (
                  <p className="text-[10px] text-slate-600 mt-0.5">
                    conf: {(article.finbert_score * 100).toFixed(0)}%
                  </p>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
