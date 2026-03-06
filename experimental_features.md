New APIs & Data Sources Worth Adding
Here's what would genuinely make Fin-Eye more powerful, organized by effort vs. impact:
High value, free/easy to get:

StockTwits (replaces Reddit, zero auth needed) — retail sentiment
GDELT — already in your user stories! Global event database, tracks news from 100+ countries, free, no key needed. Perfect for geopolitical risk scoring.
OpenFIGI (by Bloomberg) — free ticker-to-company mapping, sector classification, country of domicile
SEC EDGAR — free, no key needed. Earnings dates, insider trading filings (Form 4), institutional holdings (13F). Huge alpha signal.
Yahoo Finance via yfinance — you likely already use this for OHLCV, but it also gives options chain data (put/call ratio is a great sentiment indicator)

Medium effort, high value:

World Bank API — free, no key. GDP, inflation, debt-to-GDP for 200 countries. Great for emerging market macro scoring.
BLS (Bureau of Labor Statistics) — free, no key needed. More granular jobs data than FRED.
ECB Data Portal — European macro data (Eurozone rates, inflation). Makes your macro layer globally aware.
Quandl/NASDAQ Data Link — some free datasets (futures positioning, COT reports)

Premium but worth it eventually:

Polygon.io — $29/mo, gives real-time options data, institutional flow, news with tickers pre-tagged
NewsAPI — broader news coverage than Finnhub for sentiment


Wave 1 — This week, no new keys needed:

Options Put/Call Fear & Greed (yfinance, already installed)
Sector Rotation Heatmap (yfinance)
Earnings Surprise Predictor (Finnhub, already have the key)

Wave 2 — 2–3 week sprint, all free:

Insider Trading Tracker (SEC EDGAR Form 4 filings)
Geopolitical Risk Score (GDELT — global event database, no key)
World Bank + ECB Global Macro Layer (GDP, inflation for G20+, no key)
Economic Event Calendar (BLS + Fed + ECB + Finnhub earnings)
Google Trends Retail Interest Tracker
Cross-Asset Correlation & Contagion Monitor

Wave 3 — Premium / Experimental:

Central Bank Language Analyzer (Fed + ECB hawkish/dovish tone score)
World Leaders & Political Risk Monitor (G20 + elections calendar + GDELT)
AI Market Narrator via Claude API (daily plain-English briefing)
Earnings Call Transcript Sentiment
Institutional 13F Smart Money Tracker