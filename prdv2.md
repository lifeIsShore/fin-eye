# Product Requirements Document v2: Fin-Eye (NeuroLoad) 🚀

## 1. Executive Summary & Vision
**Fin-Eye** (Working Name: *NeuroLoad*) is a hybrid platform that translates institutional-grade market data, global macro sentiment, and quantitative modeling into clear, student-friendly financial literacy coaching.

### Core Philosophy: "Transparency over Hype"
Unlike "Signal Groups" that promise high-accuracy price targets, Fin-Eye focuses on **Market Regime Intelligence**. We believe that understanding the *why* behind a market move is more valuable for long-term wealth than following a "Buy/Sell" alert.

### 💎 The Strategic Moat
Instead of focusing on prediction accuracy, our moat is built on:
- **Structure:** Institutional logic for retail users.
- **Education:** Translating complex data into "Mini-Lessons."
- **Multi-layer Interpretation:** Correlating Technicals, Social Sentiment, Political Tones (G20/IMF), and Macro Liquidity (FRED).
- **Planning Integration:** Connecting market insights to personal FIRE goals.

---

## 2. Target Audience & Positioning
### 🎯 Your Real Target
*   **Finance & econ students:** Seeking real-world application of theory.
*   **Curious retail investors:** Moving beyond basic ticker feeds.
*   **Beginners who feel overwhelmed:** Seeking structure and "coaching."
*   **Intermediate learners who want structure:** People who read the Fed/IMF news but don't know how to connect it to price.

**Fin-Eye is not a trading app; it is a Market Understanding Platform.**

### Positioning Strategy: The "Bridge"
Fin-Eye is not just a tool; it is the **Bridge between confusion and understanding**. We don't compete with high-end quants; we empower everyone else.

*   **Why This Is Strong:** 
    1.  **Alignment over Prediction:** We measure environmental synchronization, not crystal-ball accuracy.
    2.  **Structured Interpretation:** Turning "Data Noise" into "Systematic Insights."
    3.  **Institutional Feel, Simplified Tone:** High-end logic delivered in plain English.

> [!TIP]
> **Positioning:** "Don't just watch the market—understand the forces behind its movements."

---

## 3. Core Differentiator: MRIE & GAS
Fin-Eye is engineered around one central concept that turns a complex dashboard into a educational product.

### 🎯 Core Concept: Market Regime Intelligence Engine (MRIE)
Instead of predicting price (e.g., “AI predicts 125$ target”), the MRIE classifies the current global market regime and shows how aligned the ticker is with it.
*   **The Shift:** From "Crystal Ball" to **Environmental Synchronization**.
*   **The Output:** “Current regime: Risk-On Momentum, 73% macro alignment, 4/5 timeframes bullish, retail sentiment overheating.”

### 🧠 The Unique Feature: Global Alignment Score (GAS)
A single score that measures synchronization across five distinct market layers. No major retail app visualizes conflict between these layers clearly.

| Layer | What it Measures |
| :--- | :--- |
| **Macro** | Interest rates, inflation trend, liquidity |
| **Political** | G20, IMF tone, geopolitical stress |
| **Retail** | Social sentiment, Google trends spike |
| **Technical** | Multi-timeframe ML consensus |
| **Volatility** | Regime classification (low/high stress) |

*   **Display:** "Alignment: 68% Supportive" vs. "Conflict: Retail euphoric vs. Macro tightening."

### 🛡 Real Differentiation (The "Institutional" Edge)
Fin-Eye differentiates itself by combining five factors that few retail apps ever integrate together:
1.  **ML Price Forecast:** Ensemble multi-timeframe consensus.
2.  **Political Sentiment:** Real-time GDELT & IMF tone analysis.
3.  **Retail Sentiment:** Social media volume and mood spikes.
4.  **Macro Stress Index:** Liquidity and inflation trend modeling.
5.  **Volatility Regime Detection:** Adaptive state classification (Low vs. High Stress).

---

## 4. Market Weather & Intelligence Presentation
Fin-Eye translates the complex GAS output into intuitive "Market Weather" analogies.

### 1️⃣ Market Weather System 🌤
Instead of technical jargon, we simplify the Global Alignment Score (GAS) into an intuitive analogy:
*   **☀️ Strong Tailwind**
*   **🌤 Mild Support**
*   **Status: 🌥 Mixed Signals**
*   **📉 Headwind**
*   **🌪 High Instability**
*   *Note:* Finance students LOVE analogies.

### 🧭 “Why Is The Market Moving?” Engine (Unique Feature)
Instead of just showing a target price (e.g., Target price: 123€), the app explains the **Current Market State**:
*   🔵 **Current Market State**
    *   Regime: Risk-On / Risk-Off
    *   Liquidity Trend: Expanding / Tightening
    *   Retail Mood: Euphoric / Neutral / Fearful
    *   Macro Stress: Low / Medium / High
*   🟡 **Alignment Explanation (Simple Language)**
    *   *Example:* “The stock is rising mainly because retail optimism and short-term momentum align. However, macro liquidity is tightening, which historically reduces sustainability.”

### 🚨 Conflict Detector & Thesis Breaker
Explicitly identifies when market layers are out of sync to teach market structure.

#### 💎 High-End Feature: "What Would Break This Thesis?"
Automatically detect regime shifts and warn the user:
*   **Logic:** "This bullish alignment would weaken significantly if VIX rises above 25 or if Bond Yields increase by 0.5%."
*   **Value:** This makes the app feel like a personal strategist, providing a "Negative Case" for every signal.

**Goal:** This teaches users how layers interact and why some rallies are more "fragile" than others.

---

## 5. The 4-Tab App Experience (In-Depth)

### Tab 1: Market Intelligence (The "What")
*   **Multi-Timeframe Consensus:** Visual "Heatmap" showing if 1H, 4H, Daily, and Weekly are in alignment.
*   **Reliability Score:** A percentage based on how much the 4 different ML models agree.
*   **Target/Stop-Loss:** Generated by the consensus model (with Confidence Bands to emphasize uncertainty).

### Tab 2: Global Pulse (The "Why")
*   **Sentiment Scored by Source:** Separate scores for Institutional (IMF/G20/News) vs. Retail (Social Media).
*   **The "Conflict Detector":** A notification if price is rising but macro sentiment is falling (e.g., a "Fragile Rally" warning).
*   **Geopolitical Risk Heatmap:** Visualizes regions of high political tone/instability using GDELT real-time event data.

### Tab 3: Risk & Hedging (The "Safety")
*   **Beta Analysis:** Show how much the ticker moves compared to the S&P 500.
*   **🛡 Hedging Scenario Builder (Pro/Premium Edge):**
    *   User selects: Stock + Put option or ETF hedge (e.g., Gold/Shield).
    *   Show: **Beta reduction**, **Max drawdown improvement**, and **Correlation heatmap**.
    *   Logic: Uses `PyPortfolioOpt` + ML regime projections to show how the position behaves in the "Current Weather."
*   **3️⃣ “If You Were a Portfolio Manager...”:**
    *   Simulate Beta exposure and simple hedge examples.
    *   *Visualized Math:* “Adding 20% bonds reduces drawdown by X% historically.”
*   **Library:** Uses `QuantStats` for professional "Tear Sheets."

### Tab 4: The Coaching Lab (The "Learning")
This tab is the heart of the "Education Moat," designed for real-life "what-if" scenario testing and long-term financial mindset training.

#### 1. The 4% Rule & Safe Withdrawal Rates (SWR)
*   **The Critique:** Moving beyond the 1998 "Trinity Study." In low-yield or high-valuation regimes, 4% is often too aggressive for 40-50 year retirements.
*   **The "New Safe":** The app models a conservative **3% to 3.25% SWR** to ensure higher probability of success.
*   **The Myth:** Debunking the idea that 4% is a guarantee. We show how it depends on historical sequences and current market valuations.

#### 2. Sequence of Return Risk (The "Hidden" Danger)
*   **Timing of Returns:** Explaining that a market crash in the first 2-3 years of retirement is more damaging than one later on, even with the same average returns.
*   **Visualized Math:** "If the market drops 20% in Year 1 while you withdraw 4%, your recovery time doubles."
*   **The Solution:** Modeling a **"Cash Buffer"** (1-2 years of high-yield savings) so users never have to sell stocks during a downturn.

#### 3. Coast FIRE vs. Traditional FIRE
*   **Traditional FIRE:** Goal tracking for the **25x annual expenses** (FI Number).
*   **Coast FIRE:** The "on-ramp" strategy. Save early, then stop contributing and let compound interest do the rest while you work only to cover living expenses.
*   **Example Simulation:** "If you have 200k€ at age 30, you could 'coast' to 1.5M€ by age 65 (at 6% real return) without another penny added."

#### 4. Macro Impact & Inflation Risk
*   **Inflation (The Silent Killer):** Automatically adjusting "real" growth. (e.g., 7% return - 3% inflation = 4% real growth).
*   **Conservative Modeling:** Defaulting long-term assumptions to **5% real return** instead of the aggressive 8-10% historical averages.
*   **Dynamic Spending (Guardrails):** If the GAS/MRIE engine detects a high-stress macro environment, the app suggests a **10% spending reduction** for that year to preserve principal.

#### 5. 🧠 Consensus Reliability Score (The "Trust" Layer)
*   **What it shows:**
    *   **TF Alignment:** % of mapped timeframes (1H, 4H, D, W) in synchronization.
    *   **Model Agreement:** How much the ensemble ML models agree on the direction.
    *   **Confidence Band:** Visual range of uncertainty based on regime volatility.
*   **Value:** This turns "Black Box" AI into a transparent, institutional-grade trust tool.

**Goal:** To make the user feel empowered through "What-If" testing and high-transparency reliability metrics.

---

## 6. Intelligence Engine & Tech Stack
The engine is built for speed, accuracy in financial context, and institutional-grade reporting.

### 1. Market & Backtesting (The Engine)
*   **VectorBT (Pro/Binary):** Utilized for large-scale ML signal testing. With 4 models across 5 timeframes, VectorBT's performance is significantly faster than traditional event-driven frameworks, ensuring quick iterations.
*   **TA-Lib / Pandas-TA:** Technical indicator libraries. **Pandas-TA** is prioritized for its ease of integration into modern ML pipelines.
*   **QuantStats:** Essential for professional "Tear Sheets." It generates Sharpe, Sortino, and Drawdown metrics, giving the app an institutional feel in the Risk & Strategy tabs.

### 2. Sentiment & Social (The "G20/IMF" Layer)
*   **FinBERT / FinMarBa:** Financial-specific LLMs. We leverage the **FinMarBa dataset (2025)** and FinBERT for high-accuracy interpretation of "Central Bank speak," which generic sentiment tools often miss.
*   **GDELT Project:** A core "hidden gem" that monitors global news in real-time across 100 languages. Used to track "Political Stability" and "G20 Keyword Spikes."
*   **PRAW (Reddit) & snscrape (Public X):** Used to build the "Retail Sentiment Index," tracking social euphoria and trend spikes.

### 3. Macro & Economic (The "Global Pulse" Dashboard)
*   **📊 Macro Sentiment Dashboard:**
    *   **IMF Tone:** Real-time sentiment analysis of global outlook reports.
    *   **Fed Sentiment:** Hawks vs. Doves spectrum mapping (FinBERT).
    *   **Political Volatility:** GDELT-driven frequency of geopolitical "Shock" keywords.
    *   **Retail Sentiment Index:** Euphoria vs. Panic weightings from social clusters.
*   **FRED API (Federal Reserve):** Source for interest rates, inflation data, and yield curves.
*   **IMF Data Portal / World Bank API:** Global outlook data used to correlate GDP growth and debt levels with price targets.

### Model Layer (MVP Implementation)
To ensure rapid delivery, the system follows a **Lean Alternative Architecture** for the MVP, with the ability to scale to multi-model tournaments later.

#### Option A: Regime-Aware Model (Strongest MVP Choice)
*   **Approach:** A single strong ML model conditioned on the detected Market Regime.
*   **Output:** Predictive signal + a **Confidence Score** based on historical regime alignment.

#### Option B: Signal Aggregator (The "No-Heavy-ML" Alternative)
*   **Approach:** Weighted consensus of core indices (Technical, Sentiment, Macro, Volatility).
*   **Outcome:** A weighted consensus that avoids heavy ML competition logic initially.

---

---

## 7. The Alternative Data Playbook (The "Hidden Forces")
To empower users to think like strategists, the engine leverages "Alternative Data" that explains the hidden physics of market movements.

### 🌊 Global Liquidity Stress Index (Macro Moat)
*   **Data Sources:** FRED (TGA, Fed Balance Sheet, Reverse Repo).
*   **The "Why":** Markets move on dollars, not just news.
*   **Educational Hook:** "Is the system being flooded with liquidity or drained? This gauge tells you if the 'Market Tide' is coming in or going out."

### 🐳 Insider Conviction & Whale Tracking (Transparency Moat)
*   **Data Sources:** SEC Form 4 (Insider activity via EDGAR).
*   **The "Why":** Following the money of those with the most information.
*   **Educational Hook:** "Divergence Warning: If CEOs are selling while retail is buying, the rally is fragile. Watch what they do, not what they say."

### 🌍 Geopolitical Risk & GDELT News Tone (Event Moat)
*   **Data Sources:** GDELT Project (tracking global news tone in real-time).
*   **The "Why":** Quantifying "Geopolitical Shock" keywords to anticipate volatility spikes.
*   **Educational Hook:** "Geopolitical risk is often a 'binary event.' This index measures if global tensions are reaching a boiling point before it hits the price."

---

### 🌍 Geopolitical Risk & GDELT News Tone (Event Moat)
*   **Data Sources:** GDELT Project (tracking global news tone in real-time).
*   **The "Why":** Quantifying "Geopolitical Shock" keywords to anticipate volatility spikes.
*   **Educational Hook:** "Geopolitical risk is often a 'binary event.' This index measures if global tensions are reaching a boiling point before it hits the price."

---

## 8. MVP Recommendation & Priorities
Based on the lean architecture, the initial push focuses on these high-leverage features:

### ✅ Keep for MVP
*   **Multi-timeframe confirmation:** Visual alignment across indices.
*   **Confidence bands:** Visualizing uncertainty for educational trust.
*   **Regime filter:** Core "Market Weather" logic.

### ⏳ Postpone for Post-MVP
*   **Model tournaments:** Competition between 4+ models per timeframe.
*   **Automatic best-model selection layer:** Advanced switching logic.
*   *Note:* Build these only if users demand deeper quant layers or when scaling to the Advanced tier.

---

### 🛡 The Defensive Layer
*   **"What Would Break This Thesis?":** Automatic detection of "Regime Flips." 
    *   *Logic:* "This bullish alignment breaks if VIX rises above 25 or if Bond Yields increase by 0.5%."

---

## 9. Educational & Training Pillars
These pillars represent the core curriculum for our users and the fundamental targets for our **experimental ML training** and **external dataset creation**.

### 🏛 Pillar 1 — Macro Education
**Goal:** Understanding the "Global Weather."
*   **Liquidity cycles:** Identifying expansionary vs. contractionary phases.
*   **Yield curve:** Analyzing the "Predictive Power" of inversions.
*   **Inflation regimes:** Real vs. Nominal growth impacts.
*   **Risk-on vs Risk-off:** Macro environments for asset allocation.
*   **Volatility clustering:** Understanding why "stress begets stress."
*   **Monetary tightening effects:** Central bank impact on liquidity.
*   **IMF outlook interpretation:** Translating global debt/GDP into local risk.
*   **Fiscal vs monetary policy impact:** How gov spending vs. rates move markets.

### 🏛 Pillar 2 — Market Structure
**Goal:** Understanding the "Engine Physics."
*   **Momentum vs mean reversion:** Identifying structural trends.
*   **Beta explained simply:** Measuring sensitivity to the SPY benchmark.
*   **Correlation breakdown:** Why "diversification fails" during panics.
*   **Regime shifts:** Detecting the transition from support to headwind.
*   **Drawdown mechanics:** The math of recovery (20% loss needs 25% gain).
*   **Portfolio construction basics:** Simplified institutional allocation.
*   **Risk-adjusted returns:** Moving beyond raw profits to Sharpe/Sortino logic.

### 🏛 Pillar 3 — Behavioral & Sentiment
**Goal:** Understanding the "Human Noise."
*   **Retail euphoria:** Identifying trend exhaustion via social mood.
*   **Fear index (VIX) explained:** Translating volatility into market sentiment.
*   **Social sentiment distortions:** Separating "signal" from social media "noise."
*   **Narrative cycles:** How themes (AI, Inflation) drive institutional flow.
*   **Overreaction vs underreaction:** Exploiting psychological lags.
*   **Political shock impact:** Historical analysis of geopolitical instability.

### 🏛 Pillar 4 — FIRE & Financial Planning
**Goal:** Understanding the "Long-term Math."
*   **Safe Withdrawal Rates (SWR):** Critique of the 4% rule vs. modern 3.25% "new safe."
*   **Sequence of Return Risk:** Why the timing of early retirement returns is critical.
*   **Coast FIRE modeling:** Compound interest math for early-phase savers.
*   **Inflation risk in retirement:** Protecting real purchasing power over 30+ years.
*   **Dynamic spending guardrails:** Adjusting lifestyle based on macro stress.

---

## 10. Clean Architecture Overview
Here’s the structural logic of the Fin-Eye system:

#### 1. DATA LAYER
*   **Market Prices:** Multi-timeframe price feeds.
*   **Technical Indicators:** TA-Lib / Pandas-TA outputs.
*   **News Feeds:** Real-time financial headlines.
*   **Macro APIs:** FRED (Rates/Inflation), IMF (Global Debt/GDP).
*   **Social Media:** PRAW (Reddit), snscrape (X).
*   **Political Event Database:** GDELT Project (100+ languages).

> [!NOTE]
> **Flow:** Data → Feature Engineering

#### 2. FEATURE ENGINEERING
*   **Sentiment Scores:** FinBERT / FinMarBa interpretations.
*   **Macro Regime Indicators:** Liquidity & Stress signals.
*   **Volatility Regime Detection:** Low vs. High Stress states.
*   **Correlation & Beta:** Multi-asset relationship modeling.
*   **Multi-timeframe Features:** Aggregated TF inputs.

#### 3. MODEL LAYER (Lean Approach)
*   **Regime Conditioning:** Feeding market state into the primary model.
*   **Signal Aggregation:** Weighting Technical, Sentiment, and Macro inputs.
*   **Cross-timeframe Consensus:** Aligning 1H, 4H, Daily, Weekly signals.
*   **Reliability Score Calculation:** Measuring agreement across indices.

#### 4. REGIME ENGINE (CORE)
*   **Macro Score:** Economic health weight.
*   **Political Stress Score:** News tone & geopolitical stability.
*   **Retail Sentiment Score:** Euphoria vs. Panic weight.
*   **Technical Consensus Score:** ML output weight.
*   **Volatility Regime:** Market stability state.

#### 5. PRESENTATION LAYER
*   **Global Alignment Score (GAS):** The primary 0-100 metric.
*   **Regime Label:** "Market Weather" status.
*   **Conflict Warnings:** "Fragile Rally" or divergence alerts.
*   **Hedge Simulation:** Scenario building outputs.
*   **Backtesting Tab:** Professional Tear Sheets.
*   **Educational Explanation Layer:** Plain language insights.
*   **Blog Insights:** Daily Macro-Snacks.

---

---

---

## 11. Decentralized Processing & Security Strategy
To scale to 1 million+ users with minimal infrastructure overhead, Fin-Eye employs a **Client-Side Heavy** architecture. This offloads expensive computation to user hardware while keeping sensitive data securely locked in a backend vault.

### 🏛 The Backend "Vault" (Security First)
The server-side database is a minimalist "High-Security Vault."
*   **Stored Data:** 
    *   Authentication (JWT/Clerk).
    *   User Profile & Subscription Tier.
    *   Portfolio *Metadata* (Pointers to assets, not raw price history).
    *   Security Logs & Audit Trails.
*   **Security:** End-to-end encryption for profile fields and JWT-protected API gateways.
*   **Database:** Supabase/PostgreSQL (optimized for high-concurrency metadata lookups, not heavy data crunching).

### ⚙️ The Client-Side "Engine Room" (Performance & Scale)
Data handling, transformation, and feature engineering happen on the user's device (Browser/Mobile).
*   **Transformation:** Raw API feeds (FRED, IMF, GDELT) are cleaned and standardized locally.
*   **Feature Engineering:** Calculation of technical indicators (Pandas-TA), rolling volatility windows, and sentiment weightings.
*   **ML Inference (Edge AI):** Small, optimized models (TFLite/ONNX) run on-device. This eliminates server-side GPU costs and ensures zero-latency interaction.
*   **Local Storage:** Large historical datasets are cached in the client's **IndexedDB** or LocalStorage. The server only transmits "Diffs" (the latest data points), reducing bandwidth by 90%.

### 🛡 Security Logic
1.  **Rate Limiting:** Aggressive protection on our data aggregation APIs to prevent "Data Scraping" of our processed feeds.
2.  **Trade Secret Protection:** Heavy model weights remain server-side if necessary; only lite versions are deployed to clients.
3.  **No Local Credentials:** No API keys for external services (FRED/IMF) are ever stored on the client; all go through a secure server proxy.

---

## 12. Design System & Visual Identity: "The Tasty & Relaxed" Aesthetic
To encourage long-term user retention, Fin-Eye moves away from high-stress "Finance Red/Green" and adopts a **Nourishing & Relaxed** aesthetic. The goal is to make the app feel like a premium, "tasty" digital product that users enjoy spending time in.

### 🎨 The "Nourishing Wealth" Palette
We use colors that evoke a sense of abundance, growth, and calm.

| Token | Hex | Feel | Purpose |
| :--- | :--- | :--- | :--- |
| **Clarity Cream** | `#FBF9F5` | Airy, clean, edible | Primary Background (Light Mode) |
| **Velvet Obsidian** | `#1A1D1A` | Deep, premium, soft | Primary Background (Dark Mode) |
| **Matcha Harvest** | `#8BA888` | Organic, growth, calm | Success signals, "Green" days |
| **Deep Fig/Berry** | `#4A2C40` | Rich, sophisticated | Headers, Primary Buttons |
| **Honey Saffron** | `#E0B354` | Warm, valuable, tasty | Accents, Highlights, GAS Score |
| **Slate Espresso** | `#2D2926` | Earthy, grounded | Primary Typography |

### 🛠 UI Principles: "Soft & Satisfying"
1.  **Glassmorphism:** Use subtle "frosted glass" effects for cards to create depth without visual clutter.
2.  **Soft Shadows:** Avoid harsh outlines. Use wide, low-opacity shadows to make elements feel "plush."
3.  **Haptic & Visual Feedback:** Every interaction (button press, toggle) should have a smooth, "tasty" micro-animation (e.g., a subtle bounce or glow).
4.  **Analogous Charts:** Instead of neon lines, use gradients that move between **Matcha Green** and **Honey Saffron**.

### 🖋 Typography
*   **Headline:** `Outfit` - Geometric, premium, and friendly.
*   **Body:** `Inter` - High readability for complex data interpretation.

---

## 13. Business Model & Monetization
We prioritize recurring value through the "Interpretation Layer."

### 💸 Subscription Tiers

#### 🟢 Free Tier (The Funnel)
*   **Features:** Limited Market Weather (Basic Emojis), 1 stock alignment view per day, Basic Sentiment Score, Basic FIRE Calculator (Static).
*   **UX "The Hook":** Daily "Macro Alignment Snack" for one major ticker (e.g., SPY or BTC).
*   **The "Tease" Notification:** Periodic alerts for major layer conflicts on Top-10 global assets (view-only, requires Pro to see details).
*   **Visual Teaser:** "Locked" indicators for advanced metrics to show the user what they are missing (e.g., Institutional vs Retail flow).
*   **The Goal:** Drive curiosity and habit-building.

#### 🔵 Pro Tier (14,99€ / month)
*   **Primary Target:** Students & Serious Learners.
*   **Features:** **Full MRIE Engine**, Multi-timeframe alignment, Conflict Detector alerts, Basic Hedge Simulator, Portfolio Beta & Correlation analysis, Advanced FIRE projections, Historical regime analysis.
*   **Experience:** No ads, full access to the "Why" behind market moves.

#### 🟣 Premium / Annual
*   **Offer:** Discounted yearly billing.
*   **Features:** 
    *   **Advanced Hedge Scenarios:** Full Portfolio Scenario Builder.
    *   **Institutional PDF Exports:** One-click "Market Intelligence Reports" for any ticker.
    *   **Custom Macro-Alerts (API/Webhook):** Set custom triggers for regime flips sent to Email/Discord.
    *   **Priority Feature Access:** Beta testing for new ML models.
*   **Incentive:** Exclusive discounts on Digital Products.

### 🛒 External Digital Products (One-Time Purchases)
For users seeking deep-dive tools outside the app:
*   **Advanced Excel Portfolio Template:** Professional-grade tracker.
*   **Macro-Adjusted FIRE Sheet:** Retirement modeling workbook.
*   **Risk Dashboard Spreadsheet:** Custom risk/reward calculator.
*   **Investment Planning Toolkit:** Comprehensive planning guides.
*   **Scenario Modeling Workbook:** What-if analysis for volatile markets.

---

## 14. 90-Day Launch Plan Blueprint

### Phase 1: Foundation (Days 1–30)
*   **Product:**
    *   Define MVP scope freeze.
    *   Build Market Weather dashboard.
    *   Basic stock intelligence page.
    *   Simple sentiment integration.
    *   Basic FIRE calculator.
    *   Legal disclaimer draft.
*   **Branding:**
    *   Finalize product name.
    *   Domain purchase.
    *   Landing page draft.
    *   Visual identity direction.
*   **Content Preparation:**
    *   10 evergreen blog articles written.
    *   20 short educational posts prepared.
    *   5 macro regime explainer visuals.

### Phase 2: Beta & Authority (Days 31–60)
*   **Beta Launch:**
    *   50–150 student beta testers.
    *   Feedback loop & UX friction fixes.
    *   Simplify explanations.
*   **Authority Building:**
    *   LinkedIn weekly macro post.
    *   X threads twice weekly.
    *   1 Substack article weekly.
    *   1 short educational infographic weekly.
*   **University Outreach:**
    *   Contact finance clubs.
    *   Offer demo sessions & student access.

### Phase 3: Public Launch (Days 61–90)
*   **Launch Assets:**
    *   Demo video & Product explainer PDF.
    *   Transparent methodology page.
    *   Pricing page finalized.
*   **Funnel Activation:**
    *   Free tier live.
    *   Email onboarding sequence & upgrade nudges.
*   **Growth Push:**
    *   Guest post on finance blogs.
    *   Reddit FIRE educational posts.
    *   Student ambassador recruitment.

**Goal:** 200–300 paying users initially | 800–1000 total users.

---

## 15. Content Strategy Calendar Blueprint
We structure our authority building and user engagement across 4 distinct pillars:
*   **Macro Monday:** Deep dives into Liquidity, Inflation, and Yield Curves.
*   **Technical Tuesday:** Explaining ML ensemble models and "Regime Flips."
*   **Whining Wednesday (Psychology):** Addressing retail euphora and narrative cycles.
*   **FIRE Friday:** Long-term math, SWR myths, and "What-If" scenario testing results.

---

## 16. Strategic Vision: Can 1000 Users Happen?
**Yes**, if we maintain the educational focus:
*   **Branding:** Positioned as "Understand markets like a strategist."
*   **Trust:** Built through transparency and explaining the *why* behind signals.
*   **Content:** Weekly macro-snacks and mini-lessons to keep users engaged.
*   **Community:** Huge opportunity with finance students who love structured dashboards.

> [!CAUTION]
> **🚨 Branding Rule: The "Prediction" Trap**  
> Never market as: *"AI predicts the next move."*  
> Always market as: **"Understand the forces behind price movements."**  
> This removes the "scam" perception entirely and builds a high-integrity brand.

## 17. Project Viability & Integrity (Honest Assessment)
This section provides an honest look at the project's potential and ethical grounding.

#### 1️⃣ Is it useful?
**Yes.** Retail investors increasingly want macro context, sentiment interpretation, and simple explanations of complex finance. Fin-Eye fills the gap between raw chart noise and institutional-grade interpretation.

#### 2️⃣ Is it unique?
**Moderately unique.** While tools like TradingView or Seeking Alpha offer parts of this, the combination of **Multi-timeframe ML competition, Political/Macro/Retail sentiment integration, and the Education Layer** is a rare and powerful edge.

#### 3️⃣ Can we reach 1000 users?
**Yes.** At 14,99€/month, 1000 users equates to ~15k€ MRR. This is realistic if the focus remains on **Education over Hype** and the UX stays clean and trustworthy.

#### 4️⃣ Is it a scam?
**No.** Provided the app:
*   Avoids "90% accuracy" prediction hype.
*   Explains model limitations and uncertainty ranges.
*   Focuses on **Environmental Alignment** rather than guaranteed returns.
*   Maintains a transparent, analytical tone.

---

## 18. Important Strategic Advice
Since the platform operates on a subscription model (14,99€/month), maintaining high integrity and legal safety is mandatory.

*   **Avoid Direct Instructions:** Never provide explicit "Buy" or "Sell" instructions.
*   **Educational Analytics:** Frame every output as **"Educational Analytics"** rather than financial advice.
*   **Mandatory Disclaimer:** Ensure a clear legal disclaimer is present on all price-related views.
*   **Risk Education:** Emphasize risk management (e.g., drawdown math) over profit potential.
*   **Core Message:** "Understand what the market environment is signaling." This protects the brand legally and builds deep user trust.

---

## 19. ML Competition — Strategic Stress Test Blueprint
A high-level framework for evaluating the long-term viability of the multi-model architecture.

### A. Core Question
Is the complex ML ensemble a true differentiator, or is it "invisible backend complexity" that users don’t value?

### B. User Value Test Framework
1.  **Visibility Test:** Does the user see and feel the benefit of the model competition, or is it just backend optimization?
2.  **Educational Alignment Test:** Does the complexity help the user *understand* the market better, or just improve a marginal forecast?
3.  **Maintenance vs. Value:** Does the cost of managing model drift, overfitting, and infrastructure actually justify the output for a coaching platform?

---

## 20. Appendix: Technical Stack Summary
*   **Engine:** `VectorBT` (High-speed backtesting), `TA-Lib` / `Pandas-TA` (Indicators).
*   **Intelligence:** `FinBERT` / `FinMarBa` (Financial Sentiment), `GDELT Project` (Global Event Hub).
*   **Data Sources:** `FRED API` (Macro), `IMF Data Portal` / `World Bank API` (Global Economic Trends), `PRAW` (Reddit), `snscrape` (Public X).
*   **Risk & Portfolio:** `PyPortfolioOpt` (Optimizations), `QuantStats` (Institutional Performance Reporting).
