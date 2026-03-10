# Fin-Eye UX & Feature Improvements

## 1. News Feed Enhancements
- [ ] **External Links**: Add clickable URL links to news articles so users can read the full story on the original source.
- [ ] **Pagination/Infinite Scroll**: Implement pagination (e.g., 10 items per page with a selector) or infinite scrolling to prevent performance issues when loading large numbers of articles.
- [ ] **Filtering & Sorting**: 
  - Filter by sentiment (Bullish, Bearish, Neutral).
  - Filter by news source/publisher.
  - Sort by date or by highest/lowest sentiment score.

## 2. Educational & Documentation UX (The "Fin-Eye" Mission)
- [ ] **Tooltips & Hover States**: Add `[i]` (info) or `?` icons next to complex financial terms, GAS scores, and technical indicators. Hovering should pop up a brief, clear explanation of the metric.
- [ ] **Dedicated Documentation / "Learn" Hub**: Build out a dedicated knowledge base page explaining the methodology behind the FinBERT sentiment analysis, Technical Consensus, and GAS scoring.
- [ ] **Interactive Onboarding/Tour**: Add a guided product tour for first-time users explaining the dashboard layout.

## 3. General UI/UX Polish
- [ ] **Skeleton Loaders**: Instead of a simple "Loading..." text or spinner, use skeleton screens that mimic the layout of the data while it is fetching from the backend for a smoother perceived load time.
- [ ] **Data Visualizations & Charts**: Enhance the dashboard by using interactive charts (e.g., Recharts, Chart.js) for time-series data (like historical sentiment or macro trends) allowing users to hover over data points for specific dates and values.
- [ ] **Empty States & Error Handling**: Design friendly empty states for when there's no data (e.g., "No news found for this filter") and show elegant toast notifications if an API request fails, rather than a silent failure or raw error message.
- [ ] **Responsive Design & Mobile Optimization**: Ensure the dashboard tables and navigation collapse gracefully on smaller tablet and mobile screens.
- [ ] **Color Coding & Badges**: Use highly semantic colors (e.g., soft greens for bullish/positive, soft reds for bearish/negative, and high-contrast badges) to make scanning financial data instantaneous.