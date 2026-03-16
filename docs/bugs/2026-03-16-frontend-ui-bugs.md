# Frontend UI Bug Report
> **Date:** 2026-03-16  
> **Files:** `frontend/app/layout.tsx` · `frontend/components/Nav.tsx` · `frontend/app/page.tsx` · `frontend/components/WatchlistWidget.tsx`  
> **Status:** ✅ All Fixed

---

## Bug #1 — Header / Nav Catastrophic Overflow on Mobile & Tablet 🔴
**Severity:** Critical — app unusable on any screen below ~1200px wide

**Symptoms:**
- Logo, subtitle, nav, and user menu all fought for horizontal space in a single row
- 19 nav items overflowed even on desktop with invisible horizontal scroll
- On mobile, UserMenu disappeared or collided with the logo
- No hamburger / drawer — nav just truncated or wrapped chaotically

**Root Cause:**  
`layout.tsx` header used `lg:flex-row` with Nav and UserMenu sharing a `flex-1` container. `Nav.tsx` rendered all 19 items flat in a single scrollable row with no grouping or mobile alternative.

**Fix Applied:**
- `layout.tsx` — restructured header into three clear zones: `Logo | Nav (centre, flex-1) | UserMenu + MobileNav (right, flex-shrink-0)`
- `Nav.tsx` — primary 5 items always visible on desktop; remaining 14 collapsed into a "More ▾" dropdown
- `Nav.tsx` — new `MobileNav` component: hamburger button (hidden on `md+`) triggers a slide-in drawer with all 19 items in a vertical list + close button + overlay
- Drawer auto-closes on route change

---

## Bug #2 — Ticker Input Has No Dropdown / Validation 🔴
**Severity:** High — led to inconsistent symbol names, failed API calls, silent errors

**Symptoms:**
- Free-text allowed anything: lowercase, spaces, invalid symbols
- No feedback on invalid tickers
- No shortcut to re-select symbols with already-trained ML models

**Fix Applied (`page.tsx`):**
- `TICKER_REGEX = /^[A-Z]{1,5}(-[A-Z]{2,4})?$/` — covers equities (`AAPL`), ETFs (`SPY`), crypto pairs (`BTC-USD`)
- `normalizeTicker()` — trims + uppercases + strips spaces before validation
- On focus/type — dropdown shows trained symbols from `/api/v1/technical/trained-symbols`, filtered live by input, with "trained" badge on each
- On submit — regex validated; inline red error shown if invalid
- Clicking a suggestion immediately sets the active symbol (no need to press Analyze)
- Tour button removed from header

---

## Bug #3 — Watchlist Input Has No Validation or Suggestions 🟠
**Severity:** High — same inconsistency problem as Bug #2

**Fix Applied (`WatchlistWidget.tsx`):**
- Same `TICKER_REGEX` + `normalizeTicker()` applied
- Trained-symbols dropdown on focus/type, filtered to exclude already-watchlisted items
- Clicking a suggestion immediately adds the ticker to the watchlist (one-tap shortcut)
- Duplicate guard: inline error `"${sym} is already in your watchlist"` 
- Invalid format: inline error `"Invalid format — use e.g. AAPL or BTC-USD"`

---

## Bug #4 — Tour Button Clutters Dashboard Header 🟡
**Severity:** Low — UX noise permanently visible after tour completion

**Fix Applied (`page.tsx`):**
- Removed the Tour button from the search bar / header area
- `GuidedTour` component remains mounted for programmatic restart
- Tour can be re-triggered from Settings page (next todo)

---

## Fix Summary

| # | Component | Change | Status |
|---|-----------|--------|--------|
| 1 | `layout.tsx` + `Nav.tsx` | Three-zone header, More dropdown, mobile hamburger drawer | ✅ Done |
| 2 | `page.tsx` | Regex validation + trained-symbols dropdown + Tour button removed | ✅ Done |
| 3 | `WatchlistWidget.tsx` | Regex validation + suggestions dropdown + duplicate guard | ✅ Done |
| 4 | `page.tsx` | Tour button removed from header | ✅ Done |

---

## Remaining / Follow-up

- [ ] Add tour restart option in `/settings` page (Help & Onboarding section)
- [ ] Backend endpoint `GET /api/v1/technical/trained-symbols` — returns list of symbols that have a trained model in the registry (needed for suggestions to be populated)
- [ ] Show model freshness date next to each suggestion in the dropdown (e.g. "trained 2d ago")
