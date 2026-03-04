---
title: "Understanding the Global Alignment Score (GAS)"
summary: "How technical, sentiment, and macro data combine into a single powerful metric."
readTime: "4 min"
date: "2026-03-02"
category: "Platform Concepts"
---

# Understanding the Global Alignment Score (GAS)

Traders are frequently bombarded with conflicting signals. The chart might look wildly bullish, while macroeconomic data suggests an impending recession, and Twitter sentiment swings wildly by the hour. How do you make sense of this noise? Enter the **Global Alignment Score (GAS)**.

## What is GAS?

The GAS is a proprietary composite metric ranging from **0 (Maximum Headwind/Bearish)** to **100 (Maximum Tailwind/Bullish)**. It's designed to give you a single unified "weather report" on a particular asset before you place a trade.

## The Three Pillars

The GAS combines three distinct layers of analysis:

1. **Technical Consensus (40%)**: We feed live price data through advanced machine learning models (XGBoost, Prophet, LSTMs) across 5 different timeframes (from 1-minute to 1-week charts). We weight the predictions by the historical accuracy of the models.
2. **Sentiment Analysis (30%)**: We ingest news headlines from major financial publications and retail chatter from Reddit. Natural Language Processing (NLP) models, like FinBERT and VADER, synthesize whether the narrative is overwhelmingly positive or deeply cynical.
3. **Macro Environment (30%)**: We evaluate whether broad economic conditions (interest rates, inflation, volatility) are supportive of risk assets or hostile to them.

## Interpreting the Score

- **80–100 (Strong Tailwind)**: All three pillars are singing in harmony. 
- **60–79 (Mild Support)**: Generally favorable conditions, though one pillar might be lagging.
- **40–59 (Mixed Signals)**: Caution advised. You might see a strong technical chart battling a toxic macro backdrop.
- **20–39 (Headwind)**: Broadly unfavorable conditions.
- **0–19 (High Instability)**: Severe structural weakness across technicals, sentiment, and macro.

*Disclaimer: The Global Alignment Score is an educational and analytical tool. It is not financial advice.*
