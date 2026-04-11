"use client";
/**
 * app/learn/glossary/page.tsx
 * Sprint 43 — Searchable A–Z glossary of all Fin-Eye terms.
 */

import { useState, useMemo } from "react";
import Link from "next/link";
import { BookOpen, Search, X, ArrowRight } from "lucide-react";

interface GlossaryEntry {
  term: string;
  definition: string;
  link?: { href: string; label: string };
  tags?: string[];
}

const ENTRIES: GlossaryEntry[] = [
  // A
  { term: "ATR (Average True Range)", definition: "A volatility measure showing the average price movement range over N bars. Fin-Eye uses ATR to set price targets — wider ATR means wider targets. Higher ATR = more volatile asset.", link: { href: "/", label: "Price Targets on dashboard" }, tags: ["atr", "volatility", "range"] },
  { term: "Asset Class", definition: "Category of financial instrument — Equity, ETF, Crypto, Commodity, or FX. Fin-Eye auto-detects the asset class for each ticker and adapts analysis (e.g. skipping earnings calendar for crypto).", link: { href: "/", label: "Dashboard header badge" } },
  // B
  { term: "Backtesting", definition: "Simulating a trading strategy on historical data to see how it would have performed. Fin-Eye supports multiple strategies (trend-following, mean-reversion, macro-responsive) with configurable parameters.", link: { href: "/backtesting", label: "Backtesting page" } },
  { term: "Benchmark", definition: "A reference portfolio or index (e.g. SPY, QQQ, BTC) used to compare strategy performance. Fin-Eye lets you toggle a benchmark overlay on the equity curve.", link: { href: "/backtesting", label: "Backtesting page" } },
  { term: "Bollinger Bands (BB%B)", definition: "Bands plotted at N standard deviations above/below a moving average. BB%B shows where price sits within the band (0 = lower band, 1 = upper band). Used as an ML feature and in the Mean Reversion strategy.", tags: ["bollinger", "bb", "bands"] },
  // C
  { term: "Cluster Buying", definition: "When 3 or more corporate insiders buy shares within a short period. Historically a strong bullish signal. OpenInsider cluster buy score ≥80 indicates strong cluster buying.", link: { href: "/insiders", label: "Insider Intelligence page" } },
  { term: "Confidence Score", definition: "How certain the ML model is about its directional prediction (0–100%). Strong = ≥65%, Moderate = ≥55%, Weak = ≥45%, Uncertain = below 45%.", link: { href: "/", label: "Technical Consensus on dashboard" } },
  { term: "Conflict Detector", definition: "Fin-Eye's signal to warn you when Technical, Sentiment, and Macro layers disagree. A conflict ≥40 points apart between any two layers triggers a warning. Acts as a built-in sanity check.", link: { href: "/", label: "Dashboard Conflict Detector panel" } },
  // D
  { term: "DCA (Dollar-Cost Averaging)", definition: "Investing a fixed amount at regular intervals regardless of price. Smooths out entry timing. Fin-Eye's DCA simulator compares it against lump-sum investing.", link: { href: "/portfolio/dca", label: "DCA Simulator" } },
  { term: "Drawdown", definition: "The peak-to-trough decline in portfolio value. Maximum Drawdown (MDD) is the worst such decline over the test period. Lower MDD = better capital preservation.", link: { href: "/backtesting", label: "Backtesting results" } },
  { term: "Drift (Model Drift)", definition: "When a trained ML model's live accuracy falls significantly below its validation accuracy. Fin-Eye detects drift every hour and can auto-retrain affected models.", tags: ["drift", "accuracy", "retrain"] },
  // E
  { term: "EDGAR (SEC EDGAR)", definition: "The SEC's Electronic Data Gathering, Analysis, and Retrieval system. Fin-Eye queries Form 4 filings (insider transactions) from EDGAR daily using the free public API.", link: { href: "/insiders", label: "Insider page" } },
  { term: "Equity Curve", definition: "A chart showing portfolio value over time during a backtest. A smooth, rising equity curve indicates consistent strategy performance. Steep drops indicate periods of drawdown.", link: { href: "/backtesting", label: "Backtesting equity chart" } },
  // F
  { term: "Fear & Greed Index", definition: "A 0–100 composite sentiment gauge. Below 25 = Extreme Fear (often a buying opportunity), above 75 = Extreme Greed (caution). Fin-Eye tracks CNN's equity Fear & Greed and Alternative.me's Crypto Fear & Greed separately.", link: { href: "/macro", label: "Macro page" } },
  { term: "FinBERT", definition: "A BERT-based NLP model fine-tuned on financial text. Fin-Eye uses ProsusAI/FinBERT to classify news headlines as Bullish, Bearish, or Neutral with a confidence score.", link: { href: "/news-sentiment", label: "Sentiment page" }, tags: ["finbert", "nlp", "bert", "sentiment"] },
  { term: "FOMC (Federal Open Market Committee)", definition: "The Fed committee that sets US interest rates. FOMC meetings typically cause market volatility. Fin-Eye shows a countdown to the next scheduled meeting on the Macro page.", link: { href: "/macro", label: "FOMC countdown on Macro page" } },
  { term: "Form 4", definition: "An SEC filing that corporate insiders must submit within 2 business days of a share transaction. Fin-Eye parses Form 4 XML from EDGAR to detect insider buying/selling patterns.", link: { href: "/insiders", label: "Insider page" } },
  { term: "FRED (Federal Reserve Economic Data)", definition: "A database of 800,000+ economic time series maintained by the St. Louis Federal Reserve. Fin-Eye pulls 12 key indicators (VIX, CPI, yield spread, unemployment, etc.) from FRED for the Macro score.", link: { href: "/macro", label: "Macro page" } },
  { term: "Freshness Indicator", definition: "Coloured dot showing data age — green = fresh (<30 min), amber = aging (<60 min), red = stale. Helps you know whether you're seeing current or cached data.", link: { href: "/", label: "Dashboard header" } },
  // G
  { term: "GAS (Global Alignment Score)", definition: "Fin-Eye's core composite metric (0–100). Blends Technical (40%), Sentiment (30%), and Macro (30%). Above 60 = bullish alignment, below 40 = bearish pressure, 40–60 = neutral.", link: { href: "/", label: "Dashboard GAS widget" }, tags: ["gas", "global alignment", "score"] },
  { term: "Grade (Signal Grade)", definition: "A letter grade (A+, A, B, C, D, F) summarising overall signal quality. Computed from GAS Score (40pts), Component Alignment (30pts), Model Sharpe (20pts), and Signal Conviction (10pts). A+ = ≥90pts, F = <40pts.", link: { href: "/watchlist-overview", label: "Watchlist Overview grades" } },
  { term: "Google Trends", definition: "A measure of search interest for a topic (0–100) from Google. Fin-Eye fetches weekly Trends interest for tracked symbols via pytrends (geo=DE by default) and uses it as an ML feature.", tags: ["google trends", "search interest", "attention"] },
  // H
  { term: "Half-Kelly", definition: "A conservative variant of Kelly Criterion that halves the suggested position size to reduce volatility and risk of ruin. Fin-Eye recommends Half-Kelly sizing, capped at 25% of portfolio.", link: { href: "/", label: "Risk Management in AI Insight card" } },
  { term: "Hedge", definition: "A position taken to offset risk in another position. Fin-Eye's Hedge page suggests inverse ETFs and put options based on portfolio exposure and macro regime.", link: { href: "/hedge", label: "Hedging Strategy page" } },
  // I
  { term: "Insider Trading (Legal)", definition: "Legal insider trading refers to purchases/sales by corporate officers, directors, and major shareholders — disclosed via Form 4. Fin-Eye tracks this as a signal (not illegal insider trading).", link: { href: "/insiders", label: "Insider page" } },
  // K
  { term: "Kelly Criterion", definition: "A mathematical formula for optimal position sizing: f = (p/a) − (q/b), where p = win probability, q = loss probability, a = average loss, b = average gain. Fin-Eye computes this from live ML prediction accuracy.", link: { href: "/", label: "LLM Insight Card Risk section" } },
  // L
  { term: "LightGBM", definition: "A gradient boosting framework by Microsoft — one of Fin-Eye's three core ML classifiers (alongside XGBoost and Logistic Regression). Often wins the model competition on high-frequency data.", tags: ["lightgbm", "gradient boosting", "ml", "model"] },
  { term: "LSTM (Long Short-Term Memory)", definition: "A type of recurrent neural network that captures sequential dependencies. Fin-Eye includes a bidirectional LSTM with attention as a 4th model competitor in the ML pipeline (added in Sprint 41).", tags: ["lstm", "rnn", "neural network", "deep learning"] },
  // M
  { term: "MACD Histogram", definition: "Moving Average Convergence Divergence histogram — difference between the MACD line and signal line. Positive = bullish momentum building. One of the top ML features in Fin-Eye.", tags: ["macd", "momentum", "moving average"] },
  { term: "Macro Score", definition: "A 0–100 composite from FRED indicators: Yield Spread, VIX, Unemployment, CPI YoY, ISM PMI, Fed Funds Rate, and more. Represents the macroeconomic backdrop — 30% of GAS.", link: { href: "/macro", label: "Macro page" } },
  { term: "Max Drawdown (MDD)", definition: "The largest peak-to-trough decline in a backtest. A key risk metric — lower is better. Fin-Eye shows MDD alongside Sharpe Ratio and total return.", link: { href: "/backtesting", label: "Backtesting results" } },
  { term: "Model Registry", definition: "Fin-Eye's JSONL file recording the winner model (XGBoost, LightGBM, Logistic, or LSTM), Sharpe ratio, accuracy, and artifact path for every symbol/timeframe combination.", tags: ["model registry", "registry", "artifact", "winner"] },
  // O
  { term: "Optuna", definition: "A hyperparameter optimisation framework. Fin-Eye runs Optuna overnight (30 trials each for XGBoost and LightGBM) when ENABLE_HYPERTUNING=True, storing best params for the next retrain.", tags: ["optuna", "hyperparameter", "tuning", "optimisation"] },
  { term: "Out-of-Sample (OOS)", definition: "Data the model was not trained on — the true test of predictive power. Walk-Forward validation splits data into IS (training) and OOS (testing) folds. OOS Sharpe is the most reliable performance metric.", link: { href: "/backtesting", label: "Walk-Forward panel" } },
  // P
  { term: "Pearson Correlation", definition: "A measure of linear correlation between two assets (−1 to +1). Fin-Eye's portfolio correlation matrix uses Pearson on daily returns. High positive correlation = assets move together (less diversification).", link: { href: "/portfolios", label: "Portfolio correlation matrix" } },
  { term: "Position Sizing", definition: "How much capital to allocate to a trade. Fin-Eye suggests Half-Kelly sizing based on live ML win rate and average return. Always shown as a mathematical suggestion, not advice.", link: { href: "/", label: "LLM Insight Card Risk section" } },
  { term: "Pro Gate", definition: "Features behind a Pro subscription paywall — Walk-Forward validation, AI Allocator, Fed Policy, Advanced Sentiment, and Indicators. Free 7-day trial available.", link: { href: "/billing", label: "Billing page" } },
  // R
  { term: "Regime (Market Regime)", definition: "The current market environment characterised by trend direction and volatility. Fin-Eye classifies regime as Risk-On, Risk-Off, Transitional, or sub-types. Stored per GAS snapshot.", link: { href: "/", label: "Regime widget on dashboard" } },
  { term: "RSI (Relative Strength Index)", definition: "A momentum oscillator (0–100). Below 30 = oversold (potential buy signal), above 70 = overbought (caution). Fin-Eye uses 14-period RSI as a core ML feature.", tags: ["rsi", "momentum", "oscillator"] },
  // S
  { term: "Sentiment Score", definition: "Fin-Eye's news sentiment aggregated to 0–100 (mapped from −1 to +1 FinBERT output). Above 60 = positive tone in recent coverage. Represents 30% of the GAS score.", link: { href: "/news-sentiment", label: "Sentiment page" } },
  { term: "Sharpe Ratio", definition: "Risk-adjusted return: (mean return − risk-free rate) / standard deviation of returns. Higher = better. Fin-Eye uses Sharpe to weight timeframe signals — better Sharpe = more influence on the consensus.", tags: ["sharpe", "risk-adjusted", "return"] },
  { term: "SHAP (SHapley Additive exPlanations)", definition: "A method to explain ML model predictions by assigning each feature an importance value. Fin-Eye shows top-5 SHAP features in the 'What drove this?' panel after tree-based model training.", link: { href: "/", label: "SHAP panel on dashboard" }, tags: ["shap", "explainability", "feature importance"] },
  { term: "StockTwits", definition: "A social network for traders where users tag posts as Bullish or Bearish. Fin-Eye fetches the 30 most recent tagged messages per ticker and computes a sentiment ratio.", link: { href: "/", label: "Social Signals panel on dashboard" } },
  // T
  { term: "Technical Confidence Score", definition: "A 0–100 score derived from the Sharpe-weighted average of all trained timeframe ML signals. 50 = perfectly neutral, >60 = bullish lean, <40 = bearish lean. Represents 40% of GAS.", link: { href: "/", label: "Technical Consensus section" } },
  { term: "Timeframe", definition: "The chart period used to train an ML model — 1m, 5m, 15m, 1h, 4h, 1d, 1wk. Each timeframe has its own trained model. Dashboard shows signals for all available timeframes side by side.", link: { href: "/", label: "Timeframe grid on dashboard" } },
  // V
  { term: "VIX (CBOE Volatility Index)", definition: "Measures expected 30-day S&P 500 volatility implied by options prices. Below 15 = calm, 15–25 = normal, above 25 = elevated fear. Fin-Eye fetches it from FRED (series VIXCLS).", link: { href: "/macro", label: "Macro page" } },
  // W
  { term: "Walk-Forward Validation", definition: "A rigorous backtesting technique that splits data into multiple IS/OOS folds to test strategy robustness. Fin-Eye supports 3–8 folds with expanding windows. OOS Sharpe degradation >0.4 triggers an overfitting warning.", link: { href: "/backtesting", label: "Walk-Forward panel (Pro)" } },
  { term: "Watchlist", definition: "Your saved list of symbols tracked in Fin-Eye. Drives the What Changed Today panel, Watchlist Overview grades, EarningsCalendarStrip, and auto-created GAS alerts.", link: { href: "/watchlist-overview", label: "Watchlist Overview" } },
  // X
  { term: "XGBoost", definition: "eXtreme Gradient Boosting — one of Fin-Eye's three core ML classifiers. Typically performs well on tabular OHLCV + indicator data. Competes with LightGBM, Logistic Regression, and LSTM each training run.", tags: ["xgboost", "gradient boosting", "ml", "model"] },
  // Y
  { term: "Yield Curve", definition: "The relationship between bond yields and maturities. Fin-Eye monitors the 10Y–2Y spread: inversion (spread < 0) has historically preceded recessions by 6–18 months. Triggers an amber warning banner on the Macro page.", link: { href: "/macro", label: "Macro page inversion banner" } },
  { term: "Yield Spread", definition: "The difference between the 10-year and 2-year US Treasury yields. Fin-Eye uses FRED series T10Y2Y. Positive = normal curve, negative = inverted.", link: { href: "/macro", label: "Macro page" } },
];

function groupByLetter(entries: GlossaryEntry[]) {
  const map = new Map<string, GlossaryEntry[]>();
  for (const e of entries) {
    const letter = e.term[0].toUpperCase();
    if (!map.has(letter)) map.set(letter, []);
    map.get(letter)!.push(e);
  }
  return map;
}

export default function GlossaryPage() {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return ENTRIES;
    return ENTRIES.filter(
      (e) =>
        e.term.toLowerCase().includes(q) ||
        e.definition.toLowerCase().includes(q) ||
        e.tags?.some((t) => t.includes(q)),
    );
  }, [query]);

  const grouped = useMemo(() => groupByLetter(filtered), [filtered]);
  const letters = useMemo(() => Array.from(grouped.keys()).sort(), [grouped]);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-sky-800/50 bg-sky-950/40">
          <BookOpen className="h-5 w-5 text-sky-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Fin-Eye Glossary</h1>
          <p className="mt-1 text-sm text-slate-400">
            Plain-English definitions for every term used across the platform.
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search terms, e.g. SHAP, GAS, Sharpe…"
          className="w-full rounded-xl border border-slate-700 bg-slate-900 py-2.5 pl-10 pr-10 text-sm text-slate-200 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
        />
        {query && (
          <button onClick={() => setQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* A–Z quick-jump */}
      {!query && (
        <div className="flex flex-wrap gap-1.5">
          {letters.map((l) => (
            <a key={l} href={`#letter-${l}`}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/60 text-xs font-bold text-slate-400 hover:border-sky-700 hover:text-sky-400 transition-colors">
              {l}
            </a>
          ))}
        </div>
      )}

      {/* Results */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-700 py-16 text-center">
          <BookOpen className="h-8 w-8 text-slate-600" />
          <p className="text-sm text-slate-500">No terms match &ldquo;{query}&rdquo;</p>
          <button onClick={() => setQuery("")} className="text-xs text-sky-400 hover:text-sky-300 transition-colors">Clear search</button>
        </div>
      ) : (
        <div className="space-y-10">
          {letters.map((letter) => (
            <section key={letter} id={`letter-${letter}`}>
              <div className="mb-4 flex items-center gap-3">
                <span className="text-2xl font-black text-sky-500">{letter}</span>
                <div className="flex-1 border-t border-slate-800" />
              </div>
              <div className="space-y-4">
                {grouped.get(letter)!.map((entry) => (
                  <div key={entry.term} className="rounded-xl border border-slate-800 bg-slate-900/40 px-5 py-4 space-y-2">
                    <h3 className="text-sm font-bold text-slate-100">{entry.term}</h3>
                    <p className="text-sm text-slate-400 leading-relaxed">{entry.definition}</p>
                    {entry.link && (
                      <a href={entry.link.href} className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:text-sky-300 transition-colors">
                        <ArrowRight className="h-3 w-3" />
                        {entry.link.label}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <div className="border-t border-slate-800 pt-6 text-center">
        <p className="text-xs text-slate-600">
          Missing a term?{" "}
          <Link href="/learn" className="text-sky-500 hover:text-sky-400 transition-colors">
            See full Learn Hub →
          </Link>
        </p>
      </div>
    </div>
  );
}
