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

        const score = article.sentiment_score;
        let scoreLabel = "Neutral";
        let scoreColor = "text-slate-300";

        if (score !== null) {
          if (score > 0.2) {
            scoreLabel = "Bullish";
            scoreColor = "text-emerald-400";
          } else if (score < -0.2) {
            scoreLabel = "Bearish";
            scoreColor = "text-rose-400";
          }
        }

        return (
          <li key={`${article.symbol}-${article.title}-${article.published_at}`} className="py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-50">
                  {article.title}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {article.source ?? "Unknown source"} · {formatted}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className={`text-xs font-semibold ${scoreColor}`}>
                  {scoreLabel}
                </p>
                {score !== null && (
                  <p className="text-xs text-slate-400">
                    Score: {score.toFixed(2)}
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

