# Fin-Eye — SaaS Business Infrastructure & Budget Plan
**Scenario:** 1,000 clients worldwide · 2,000 tickers · Full server-side ML  
**Model:** Home Server Primary + Hybrid Cloud Edge  
**Status:** Planning  

---

## 0. Why Home Server + Hybrid Cloud Is the Right Call

Your reasoning is correct. Here's the full case:

| Factor | Home Server | Cloud Only |
|--------|-------------|-----------|
| Compute cost (monthly) | ~$15–25 electricity | $300–600/month |
| Upfront | ~$800–1,200 hardware | $0 |
| Breakeven | ~3–4 months | Never |
| Depreciation | Yes — ~3yr asset life, tax deductible in many countries | No |
| Resale value at shutdown | 40–60% of hardware cost | $0 |
| Scaling | Add RAM/disk cheaply | Pay more monthly forever |
| Control | Full | Limited |
| Risk | Power/internet outage | Vendor price changes |

**The hybrid model balances both:** Home server handles all heavy compute (ML training, GAS batch). Cloud edge handles global latency, SSL termination, and failover. You get institutional compute at bootstrap cost.

---

## 1. Hardware Configuration for 1,000 Clients / 2,000 Tickers

### 1.1 Primary Compute Server ("The Engine")

This machine runs: ML training, GAS batch, FinBERT, Postgres, Redis, FastAPI

```
Component               Model                           Price (USD)
──────────────────────────────────────────────────────────────────
CPU                     AMD Ryzen 9 7900X (12C/24T)     $290
                        OR Intel Core i9-13900K (24C)   $350
Motherboard             ASUS ProArt B650-CREATOR         $220
                        OR MSI MAG Z790 TOMAHAWK         $230
RAM                     64 GB DDR5 6000MHz (2×32 GB)    $140
                        (Kingston Fury Beast / G.Skill)
Primary SSD (OS+DB)     2 TB Samsung 990 Pro NVMe        $130
Secondary SSD (Models)  2 TB Samsung 870 EVO SATA        $110
PSU                     Seasonic Focus GX-650 80+ Gold   $100
Case                    Fractal Design Define 7 (quiet)  $130
CPU Cooler              Noctua NH-D15 (silent 24/7)      $100
──────────────────────────────────────────────────────────────────
Subtotal (Server)                                       ~$1,220

Optional UPS (power protection):
APC Back-UPS 1500VA                                      $130

Optional 2.5 GbE NIC (faster local network):             $30
──────────────────────────────────────────────────────────────────
TOTAL PRIMARY SERVER                                    ~$1,380
```

**Why these choices:**
- Ryzen 9 7900X: 12 cores handles 4 Celery training workers + inference + API simultaneously with headroom
- 64 GB RAM: 2,000 symbols × ~20 MB working memory + Postgres + Redis + OS = comfortable at 35–40 GB peak
- 2 TB NVMe: OS + Postgres + hot data, fast random reads for inference
- 2 TB SATA: model_store (slower reads ok for weekly-trained models)
- Noctua NH-D15: runs silent indefinitely — this is a 24/7 machine, fan noise matters

### 1.2 Network Device (Home → Internet)

```
Component               Model                           Price
──────────────────────────────────────────────────────────────
Router (if upgrading)   TP-Link ER7206 (SMB router)     $100
  OR use existing home router if gigabit capable         $0

Unmanaged Switch        TP-Link TL-SG108 (8-port)       $20
──────────────────────────────────────────────────────────────
Network upgrade (opt)                                   ~$120
```

### 1.3 Total Hardware Investment

```
Core server:            $1,220
UPS:                    $130
Network (optional):     $120
──────────────────────
TOTAL HARDWARE:        ~$1,470 USD
```

**Depreciation:** At 3-year straight-line, that's ~$490/year or ~$41/month depreciation cost.  
**Resale value at 2 years:** ~50–60% → ~$700–800 recovered if you shut down.

---

## 2. Monthly Operating Costs

### 2.1 Electricity

```
Server power draw:
  Idle (no training):     ~65W
  GAS batch (15-min):     ~120W (peaks, 15 min every 15 min during market hours)
  ML training (weekly):   ~180W (Sunday night batch, ~8 hours)
  Average 24/7 draw:      ~85W estimated

Monthly kWh:
  85W × 24hr × 30 days = 61.2 kWh/month

Cost by region:
  Turkey (~$0.08/kWh):    ~$5/month   ← your likely location
  EU average ($0.25):     ~$15/month
  USA average ($0.12):    ~$7/month
```

**Electricity at your location (TR): ~$4–6/month**

### 2.2 Internet Connection

```
You need: Stable upload bandwidth for 1,000 clients
  
API response payload per request: ~5–20 KB (GAS snapshot JSON)
Peak concurrent users (1,000 clients): assume 5% active = 50 simultaneous
50 users × 20 KB/request × 1 req/5 sec = ~200 KB/s = ~1.6 Mbps upload needed

A standard 100 Mbps fiber line is more than enough.

Cost: Your existing home internet — $0 incremental IF it's stable fiber.
  If you need business-grade SLA: add ~$30–50/month for a dedicated line.

Recommendation: Start with home fiber, upgrade if uptime SLA becomes critical.
```

### 2.3 Cloud Edge Services (The Hybrid Part)

This is what you cannot replace with home hardware — global availability, DDoS protection, and SSL without exposing your home IP.

```
Service             Purpose                         Monthly Cost
──────────────────────────────────────────────────────────────
Cloudflare Free     CDN + DDoS + SSL + DNS          $0
Cloudflare Tunnel   Exposes home server securely    $0
  (no static IP needed — runs as a daemon on server)

Hetzner CX22 VPS    Edge proxy / failover node      €3.79 (~$4)
  (2 vCPU / 4 GB / 40 GB, Frankfurt or Helsinki)
  Runs: Nginx reverse proxy, health checks
  If your home server goes down, VPS serves cached responses

Hetzner Object      model_store backup + CDN        €0.05/GB
Storage             for static frontend assets
  Estimated 20 GB models + 5 GB assets = 25 GB   = €1.25/mo

──────────────────────────────────────────────────────────────
Cloud edge total:                                  ~$7/month
```

### 2.4 External APIs & Data Services

Your app depends on external data. This is a real ongoing cost:

```
Service             What you use it for             Free Tier    Paid
──────────────────────────────────────────────────────────────────────
Yahoo Finance API   OHLCV price data (yfinance)     Unlimited*   $0
  *unofficial, rate-limited, may break — acceptable for MVP

Alpha Vantage       OHLCV + fundamentals            500 req/day  $50/mo (premium)
  OR Polygon.io     OHLCV + options + news          $29/mo (starter, 2yr lag)
                                                    $199/mo (real-time)

FRED API            Macro indicators (free forever) Unlimited    $0

NewsAPI / GDELT     News for FinBERT sentiment      1000 req/day $449/mo (pro)
  OR Alpaca News    News feed with symbols          $0 (free tier, delayed)
  OR use yfinance   News scraping (already built)   Free         $0

Reddit API          reddit_service.py               Free tier    $0–$12/mo

StockTwits API      stocktwits_service.py           Free tier    $0

──────────────────────────────────────────────────────────────────────
MINIMUM (free tiers + yfinance):                   $0/month
RECOMMENDED (Polygon.io starter + Alpaca):         $30–50/month
PRODUCTION (Polygon real-time + NewsAPI):          $200–250/month
```

**Recommendation for 2,000 tickers at launch:** Polygon.io Starter ($29/mo) covers OHLCV with 2-year history, which is plenty for ML training. Use free FRED + Alpaca News for the rest.

### 2.5 Software & SaaS Tools

```
Service             Purpose                         Monthly Cost
──────────────────────────────────────────────────────────────
GitHub              Code hosting + Actions CI/CD    $0 (free for private)
Vercel / Cloudflare Pages  Frontend hosting         $0 (free tier)
Sentry              Error monitoring                $0 (5K errors/mo free)
Uptime Robot        Server monitoring + alerts      $0 (50 monitors free)
Resend / Brevo      Transactional email             $0 (<100 emails/day free)
  (alerts, onboarding, billing emails)              $20/mo (higher volume)
Stripe              Payment processing              2.9% + $0.30/transaction
  At $50 avg subscription × 1,000 clients:
  Stripe fee: ~$1,800/month (2.9% of $50,000 GMV)
  But this is revenue-linked, not a fixed cost.

──────────────────────────────────────────────────────────────
Fixed software costs:                              ~$20–40/month
Stripe: variable (2.9% of revenue)
```

### 2.6 Legal / Business

```
Item                                                Annual Cost
──────────────────────────────────────────────────────────────
Domain name (fin-eye.com or similar)                $12/year
Business registration (varies by country)           $50–200/year
Privacy policy / Terms of service (template)        $0–50 one-time
Financial disclaimer / compliance review            $200–500 one-time
SSL certificate                                     $0 (Cloudflare)
──────────────────────────────────────────────────────────────
Legal/domain annual:                               ~$300–700/year
Monthly equivalent:                                ~$25–60/month
```

---

## 3. Full Monthly Cost Summary

### 3.1 Operating Costs (1,000 clients / 2,000 tickers)

```
Category                            Monthly (USD)   Notes
──────────────────────────────────────────────────────────────────────────
Electricity (server)                $5              Turkey rates
Cloud edge (Hetzner VPS + storage)  $7
External data APIs (Polygon.io)     $30             Recommended minimum
Software tools                      $25
Email service                       $20
Domain + legal (amortized monthly)  $35
Hardware depreciation (3yr)         $41             $1,470 ÷ 36 months
──────────────────────────────────────────────────────────────────────────
TOTAL MONTHLY OPERATING COST        ~$163/month
Without depreciation (cash cost):   ~$122/month
```

### 3.2 Comparison: Home Server vs Pure Cloud

```
                    Home Server     Hetzner Only    AWS Only
──────────────────────────────────────────────────────────────
Monthly cash cost   $122/month      $85/month       $580/month
Year 1 total        $1,470 + $1,464 $1,020          $6,960
  (hardware + ops)  = $2,934
Year 2 total        $1,464          $1,020          $6,960
Year 3 total        $1,464          $1,020          $6,960
──────────────────────────────────────────────────────────────
3-year total        $5,862          $3,060          $20,880
3-year vs AWS savings: $15,018 saved vs AWS
3-year vs Hetzner:  Home server costs $2,800 more over 3 years
                    BUT you own $700–800 resale value hardware
                    AND have full control + zero vendor dependency
```

**Verdict:** If you're comfortable with home server maintenance, it wins vs AWS massively. Vs Hetzner, it's roughly equivalent over 3 years once you factor in resale, and you gain control + upgrade flexibility.

---

## 4. Revenue Model to Cover Costs

```
Break-even calculation:

Monthly costs:          ~$122/month (cash)
  (not counting depreciation — you own the asset)

Pricing scenarios:
──────────────────────────────────────────────────────
Tier        Price/month  Clients needed to break even
──────────────────────────────────────────────────────
$9/month    Basic        14 clients
$19/month   Standard     7 clients
$49/month   Pro          3 clients
──────────────────────────────────────────────────────

At 1,000 clients × $19/month = $19,000 GMV/month
  Stripe fees: ~$570 (2.9%)
  Net revenue: ~$18,430/month
  Operating cost: ~$122/month
  ─────────────────────────────
  Operating profit: ~$18,308/month (96% margin)

At 1,000 clients × $49/month = $49,000 GMV/month
  Net revenue after Stripe: ~$47,580/month
  Operating profit: ~$47,458/month
```

> Your infrastructure cost at this scale is essentially a rounding error on revenue.  
> The home server model gives you ~96% gross margin on infrastructure alone.

---

## 5. Architecture Blueprint (1,000 Clients / 2,000 Tickers)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS (worldwide)                       │
│              Browser / Mobile → HTTPS requests                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   CLOUDFLARE (free tier)                         │
│    CDN + DDoS protection + SSL termination + DNS                 │
│    Static frontend assets served from edge (Next.js export)      │
└────────────────────────┬────────────────────────────────────────┘
                         │ Cloudflare Tunnel (encrypted)
┌────────────────────────▼────────────────────────────────────────┐
│              HETZNER CX22 VPS (~$4/month)                        │
│         Nginx reverse proxy + health check + failover            │
│   If home server down → serve cached GAS snapshots + 503 page   │
└────────────────────────┬────────────────────────────────────────┘
                         │ Private tunnel
┌────────────────────────▼────────────────────────────────────────┐
│                   HOME SERVER (primary)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  FastAPI     │  │  Postgres    │  │  Redis               │  │
│  │  (backend)   │  │  (main DB)   │  │  (GAS cache, 15min)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              APScheduler / Celery Workers                 │   │
│  │   GAS Batch (15min) │ ML Training (weekly) │ Macro (15min)│  │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────────────────────────────┐     │
│  │ model_store/ │  │  ohlcv_fetcher + sentiment_service   │     │
│  │ 2,000 models │  │  + news_data + macro_data            │     │
│  └──────────────┘  └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                         │ Backup
┌────────────────────────▼────────────────────────────────────────┐
│         HETZNER OBJECT STORAGE (~€1.25/month)                    │
│   Daily DB backup + model_store snapshot + frontend builds       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Uptime & Reliability Strategy

The main risk of home server is downtime. Here's how to mitigate it:

### 6.1 What happens when your home server goes down?

```
Without mitigation:
  → All 1,000 clients see 502/503 errors
  → Bad for retention

With mitigation strategy:
  1. Hetzner VPS detects home server offline (health check every 30s)
  2. VPS switches to "stale cache mode":
     - Serves last known GAS snapshots (stored on VPS, max 15min old)
     - Shows a "Data refresh delayed" banner on dashboard
     - Clients still see data, just slightly stale
  3. Home server comes back online:
     - VPS detects recovery, switches back to live proxying
     - GAS batch runs immediately on recovery
  
  Acceptable degraded window: ~15 minutes
  Client experience: data is slightly old, UI works normally
```

### 6.2 Common outage sources and fixes

```
Risk                    Mitigation
──────────────────────────────────────────────────────────────────
Power outage            UPS ($130) — covers ~20–30 min of bridge time
                        Most outages are < 5 min
Home internet down      Dual-SIM 4G/5G USB failover dongle (~$30 device)
                        Activate mobile data hotspot on outage
Server crash / freeze   Systemd watchdog restarts services automatically
                        Uptime Robot alerts you on email/SMS within 1 min
OS update reboots       Schedule during 02:00–04:00 UTC (market closed)
Hardware failure        Hetzner VPS serves cache while you diagnose
                        SATA drive for model_store (5yr warranty) is low risk
```

### 6.3 Realistic uptime expectation

```
Home server with UPS + 4G failover:  99.5–99.8% uptime
  = 1–4 hours downtime per month
  
Hetzner VPS alone:                   99.9% uptime (SLA)

Hybrid (home + VPS cache fallback):  99.8–99.95% effective uptime
  (most outages invisible to clients due to stale cache serving)
```

---

## 7. Scaling Path as Business Grows

```
Stage           Clients     Tickers     Infrastructure
──────────────────────────────────────────────────────────────────
Launch          0–100       200         Home server (current spec)
                                        $122/month costs
                                        Break even: ~7 clients at $19

Growth          100–500     500         Same home server
                                        Upgrade RAM to 64 GB if needed (+$70)
                                        Add 2nd NVMe for DB ($130)

Scale           500–1,000   2,000       Same home server (fully spec'd)
                                        Add Hetzner VPS for edge ($4/mo)
                                        Total: ~$163/month

Expansion       1,000–5,000 5,000       Add 2nd home server as worker node
                                        (~$800 used/refurbished)
                                        OR rent Hetzner AX41 dedicated (~$40/mo)
                                        for training-only workloads

Enterprise      5,000+      10,000+     Migrate training to Hetzner dedicated
                                        Keep home server as primary DB/API
                                        OR fully migrate to cloud at this point
                                        Revenue justifies it
```

---

## 8. Hardware Upgrade Path

```
Year 1 (launch):
  Build as spec'd: $1,470 total

Year 2 (if > 500 clients):
  Add 64 GB more RAM:              ~$140 (DDR5 prices dropping)
  Add 4 TB NVMe for model_store:   ~$200
  Upgrade: $340

Year 3 (if > 1,000 clients):
  Option A: Second server (refurb): ~$600–800
  Option B: Hetzner AX41 dedicated: $40/month for training only
  Home server handles API + DB only (lighter load, faster responses)

Resale scenario at year 3:
  Original server (3yr old):       $400–600 recovered
  Net depreciation over 3yr:       ~$870 (vs $0 resale for cloud)
```

---

## 9. One-Time Setup Costs

```
Item                                            Cost
──────────────────────────────────────────────────────
Hardware (as spec'd)                            $1,470
OS setup (Ubuntu Server 24.04 LTS)              $0
Docker + Docker Compose setup                   $0
Cloudflare Tunnel setup                         $0
Domain name                                     $12
SSL certificate                                 $0
Business registration (Turkey)                  ~$50–100
Privacy policy / ToS template                   $0–50
Stripe account setup                            $0
Financial disclaimer (lawyer review, opt.)      $200–400
Initial data backfill (2,000 tickers × 5yr)
  yfinance: free but takes ~4–8 hours to run    $0
  Polygon.io historical pull: included in plan  $0

──────────────────────────────────────────────────────
TOTAL ONE-TIME:                                ~$1,800–2,100
```

---

## 10. Complete Budget Summary (Year 1)

```
                                        Cost
──────────────────────────────────────────────────────────────
ONE-TIME
Hardware                                $1,470
Setup & legal                           $350
─────────────────────────────────────────────
One-time total:                         $1,820

MONTHLY RECURRING (×12)
Electricity                             $5 × 12  = $60
Hetzner VPS + storage                   $7 × 12  = $84
Data APIs (Polygon.io)                  $30 × 12 = $360
Software / email tools                  $25 × 12 = $300
Domain + legal amortized                $35 × 12 = $420
─────────────────────────────────────────────
Annual recurring:                       $1,224

──────────────────────────────────────────────────────────────
YEAR 1 TOTAL COST:                      ~$3,044
YEAR 2 TOTAL COST:                      ~$1,224 (no hardware)
YEAR 3 TOTAL COST:                      ~$1,224

3-YEAR TOTAL:                           ~$5,492
Less hardware resale value:             -$700
Net 3-year cost:                        ~$4,792

──────────────────────────────────────────────────────────────
BREAK-EVEN ANALYSIS
At $19/month plan:  Need 9 clients to cover monthly operating costs
At $49/month plan:  Need 3 clients to cover monthly operating costs

Revenue at 1,000 clients ($19/mo): $19,000/month
Annual revenue:                     $228,000
Year 1 total costs:                 $3,044
Year 1 profit (pre-tax, no salary): ~$224,956 at 1,000 clients
Infrastructure margin:              98.7%
```

---

## 11. Best Practice Recommendations

### Technical
1. **Cloudflare Tunnel over port-forwarding** — Never expose your home IP. Free, encrypted, hides your home address.
2. **Systemd for all services** — Not Docker Compose for 24/7 production. Systemd restarts on crash, logs properly, starts on boot.
3. **Daily encrypted DB backup to Hetzner Object Storage** — `pg_dump | gzip | rclone copy` in a cron job. 30-day retention. ~$0.05/GB/month.
4. **asyncio.Semaphore(20) for GAS batch** — The single most impactful code change for 2,000 tickers. Do this before going live.
5. **Model artifacts on SATA, DB on NVMe** — Models are read once per inference, DB is random access constantly. Match the storage to the workload.
6. **Celery + Redis broker for training jobs** — Training should never block the API. Background worker queue from day one.

### Business
1. **Start with 200 tickers** — Launch lean, prove the model works, then expand. Expanding to 2,000 tickers is a config change + backfill run.
2. **Free tier for 50 tickers** — Drives signups, conversion to paid at ~200 tickers. Low marginal cost to you.
3. **Annual plan discount (20%)** — Locks in cash flow, reduces churn. Critical for a bootstrapped SaaS.
4. **Stripe Billing, not manual invoices** — From day one. Recurring billing, dunning (failed payment retries), and proration are not worth building yourself.
5. **Status page (statuspage.io free or Upptime on GitHub)** — 1,000 clients will ask "is it down?" instantly. A public status page absorbs support load.
