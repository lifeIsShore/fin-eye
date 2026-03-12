# Fin-Eye — UI/UX Rules of Conduct

> This document defines the must-haves and consistency rules for every page and component
> in the Fin-Eye frontend. Any new feature, page, or component **must** comply with these rules
> before it is considered production-ready.

---

## 1. Design Tokens (Single Source of Truth)

**Rule**: Never hardcode color, radius, or spacing values directly in component files.  
All tokens live in `frontend/app/globals.css` under `@theme inline {}`.

```css
/* frontend/app/globals.css */
@import "tailwindcss";

@theme inline {
  /* Primary action */
  --color-primary:      #0284c7;   /* sky-600  — use for ALL primary buttons & focus rings */
  --color-primary-hover:#0369a1;   /* sky-700 */

  /* Semantic text */
  --color-text-base:    #f1f5f9;   /* slate-100 */
  --color-text-muted:   #94a3b8;   /* slate-400 — minimum on dark bg for WCAG AA */
  --color-text-subtle:  #64748b;   /* slate-500 — headings/labels only, never body text on dark */

  /* Surfaces */
  --color-surface:      #0f172a;   /* slate-950 — page background */
  --color-card:         #0f172a;   /* slate-900/50 — card background */
  --color-border:       #1e293b;   /* slate-800 */
  --color-border-muted: #334155;   /* slate-700 */

  /* Status */
  --color-bullish:      #34d399;   /* emerald-400 */
  --color-bearish:      #f87171;   /* red-400 */
  --color-neutral:      #fbbf24;   /* amber-400 */
  --color-info:         #38bdf8;   /* sky-400 */

  /* Radius */
  --radius-sm:   6px;
  --radius-md:   8px;
  --radius-lg:   12px;
  --radius-xl:   16px;
  --radius-pill: 9999px;
}
```

| Token | Usage |
|---|---|
| `--color-primary` | Primary CTA buttons, active nav highlight, focus rings |
| `--color-text-muted` | Subtitles, meta labels, captions (min contrast on dark bg) |
| `--color-border` | Card borders, dividers |
| `--radius-lg` | Cards, panels, modal containers |
| `--radius-md` | Inputs, buttons |
| `--radius-pill` | Badges, status pills |

---

## 2. Typography

| Role | Class(es) | Notes |
|---|---|---|
| Page `<h1>` | `text-2xl font-black tracking-tight` | One per page, describes the **current content** (not "Fin-Eye") |
| Section heading | `text-sm font-semibold text-slate-100` | Card/widget titles |
| Body copy | `text-sm text-slate-300` | Main readable content |
| Meta / caption | `text-xs text-slate-400` | Timestamps, source labels — **never use slate-500 on slate-950** |
| Monospace data | `font-mono tabular-nums` | Numbers, scores, ticker symbols |
| Label / eyebrow | `text-[11px] uppercase tracking-wide text-slate-500` | Card sub-labels, section dividers |

**Rules:**
- Every route must export a `metadata` object with a **unique** `title` and `description`.
- The global layout `<h1>` ("Fin-Eye") must be demoted to a styled `<span>` or `<p>`. Each page owns its single `<h1>`.
- Do not use `text-slate-500` for body/paragraph text on `slate-950` backgrounds — minimum is `text-slate-400`.

---

## 3. Color Usage

| Context | Correct | ❌ Wrong |
|---|---|---|
| Primary button | `bg-sky-600 hover:bg-sky-500` | `bg-blue-600`, `bg-indigo-600` |
| Destructive action | `bg-red-700 hover:bg-red-600` | `bg-rose-600` |
| Success state | `text-emerald-400` / `bg-emerald-900/40` | `text-green-400` |
| Warning / neutral | `text-amber-400` | `text-yellow-400` |
| Info / sky accent | `text-sky-400` | `text-blue-400` |
| Focus ring | `focus-visible:ring-2 focus-visible:ring-sky-500` | `focus:ring-1 focus:ring-blue-500` |
| Muted text on dark | `text-slate-400` (min) | `text-slate-500` (fails contrast) |

**Rule**: Never mix the primary palette across pages. If a button is `sky-600` on the Dashboard, it is `sky-600` everywhere.

---

## 4. Spacing & Layout

- **Page padding**: `px-4 py-6` (managed by `layout.tsx` — do not override in page files)
- **Card internal padding**: `p-4` (compact) or `p-6` (default) — pick one per card, don't mix
- **Gap between cards/sections**: `gap-4` (tight grid) or `gap-6` (default)
- **Max content width**: `max-w-6xl mx-auto` (managed by layout — do not re-wrap in page files)
- **Section vertical rhythm**: `space-y-6` between major sections on a page

---

## 5. Component Rules (shadcn First)

> Before building any UI element from scratch, check if a shadcn component exists for it.

| Need | Use | ❌ Do NOT |
|---|---|---|
| Button | `<Button>` from `@/components/ui/button` | Raw `<button>` with inline Tailwind |
| Text input | `<Input>` from `@/components/ui/input` | Raw `<input className="border ...">` |
| Toggle / switch | `<Switch>` from `@/components/ui/switch` | Custom Toggle component |
| Card container | `<Card>` from `@/components/ui/card` | Ad-hoc `<div className="rounded-xl border ...">` |
| Badge / pill | `<Badge>` from `@/components/ui/badge` | Inline `<span className="rounded-full ...">` |
| Modal / dialog | `<Dialog>` from `@/components/ui/dialog` | Custom fixed-position div overlays |
| Loading state | `<Skeleton>` from `@/components/ui/skeleton` | `animate-pulse` text or blank divs |
| Toast feedback | `<Toaster>` (Sonner) from `@/components/ui/sonner` | Inline status `<div>` blocks |
| Select / dropdown | `<Select>` from `@/components/ui/select` | Raw `<select>` element |

Install missing components with: `npx shadcn add <component-name>`

---

## 6. Border Radius

Use **one** radius per element type — do not mix:

| Element | Token | Tailwind class |
|---|---|---|
| Cards / panels | `--radius-lg` | `rounded-xl` |
| Inputs / buttons | `--radius-md` | `rounded-lg` |
| Badges / pills | `--radius-pill` | `rounded-full` |
| Tooltips / small popovers | `--radius-sm` | `rounded-md` |
| Modals / drawers | `--radius-xl` | `rounded-2xl` |

---

## 7. Navigation

**Rule**: The navigation must use a **grouped sidebar** (desktop) with a **hamburger drawer** (mobile).  
The flat 19-item horizontal list is retired.

```
Sidebar groups:
  Overview      → Dashboard, Macro Intel, Indicators, Fed Policy
  Sentiment     → News Sentiment, Retail Sentiment, Adv. Sentiment
  Markets       → Options, Sectors, Insiders, Earnings, Shorts
  Tools         → Backtesting, Hedge, Portfolio, Alerts, Pro Tools
  Community     → Learn, Community
```

- Active nav item: `aria-current="page"` attribute + visual highlight
- Mobile: sidebar opens as a `<Sheet>` (shadcn drawer from the left)
- The sidebar must include a **skip navigation link** as the first focusable element:
  ```html
  <a href="#main-content" class="sr-only focus:not-sr-only">Skip to content</a>
  ```
- Label the `<nav>` element: `<nav aria-label="Main navigation">`
- `UserMenu` dropdown must have `role="menu"` and each item `role="menuitem"`

---

## 8. Accessibility (WCAG AA — Non-Negotiable)

| Rule | How |
|---|---|
| Single `<h1>` per page | Page `<h1>` = current page title. Layout brand → `<p>` or `<span>` |
| Colour contrast ≥ 4.5:1 (normal text) | Use `text-slate-400` minimum on `slate-950` backgrounds |
| Colour contrast ≥ 3:1 (large text / UI) | Score numerals (≥18px bold) can use `text-slate-500` |
| Visible focus indicator | `focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2` on **all** interactive elements — never `focus:outline-none` alone |
| ARIA on interactive components | Dropdowns: `role="menu/menuitem"`, Toggles: `role="switch" aria-checked`, Icons-only: `aria-label` |
| `aria-current="page"` | Active nav link must carry this attribute |
| Skip navigation | First element in `<body>` must be a skip link |
| No colour as sole meaning | Always pair colour with icon or text (e.g., don't show only a red dot for "error") |
| Image alt text | Every `<img>` and `<Image>` must have descriptive `alt` text |

---

## 9. Page Structure (Every Route)

Every page file must include the following:

```tsx
// app/[route]/page.tsx

import type { Metadata } from "next";

// 1. Unique metadata per page
export const metadata: Metadata = {
  title: "Page Name — Fin-Eye",
  description: "One-sentence description of what this page shows.",
  openGraph: {
    title: "Page Name — Fin-Eye",
    description: "...",
    type: "website",
  },
};

// 2. Single h1 that matches the page purpose
export default function PageName() {
  return (
    <div id="main-content">          {/* id used by skip nav link */}
      <h1 className="text-2xl font-black tracking-tight">Page Name</h1>
      <p className="mt-1 text-sm text-slate-400">Short description.</p>
      ...
    </div>
  );
}
```

---

## 10. Loading & Error States

**Rule**: Every data-dependent section must handle all three states explicitly.

| State | Implementation |
|---|---|
| Loading | `<Skeleton>` (shadcn) — match the shape of the real content |
| Error | `<Alert variant="destructive">` (shadcn) with human-readable message + retry option |
| Empty | Centered empty state with icon, label, and a clear call-to-action |

```tsx
// ✅ Correct pattern
if (isLoading) return <Skeleton className="h-32 w-full rounded-xl" />;
if (error)     return <Alert variant="destructive"><AlertDescription>{error.message}</AlertDescription></Alert>;
if (!data)     return <EmptyState message="No data yet" action={<Button>Refresh</Button>} />;
```

---

## 11. Forms & Inputs

- Always use `<Input>` and `<Button>` from shadcn — never raw `<input>` / `<button>`
- Every input must have an associated `<Label>` (either visible or `sr-only`)
- Primary submit button: `bg-sky-600 hover:bg-sky-500` — consistent across all forms
- Destructive action buttons: always require a **confirmation step** (modal or type-to-confirm)
- `focus-visible:ring-2 focus-visible:ring-sky-500` on all inputs
- Validation errors must appear as `text-xs text-red-400` beneath the field, not as alerts

---

## 12. API & Environment

- **Never hardcode `http://localhost:8000`** in component files
- Use `process.env.NEXT_PUBLIC_API_URL` as the base URL for all API calls
- All authenticated API calls must go through the shared `fetcher` in `frontend/lib/api.ts`
- SWR keys must be descriptive strings (e.g., `gas-snapshot-${symbol}`, not just `symbol`)

---

## 13. Performance

| Rule | Target |
|---|---|
| FCP (First Contentful Paint) | < 2.5 s |
| CLS (Cumulative Layout Shift) | < 0.1 |
| Page bundle size | No page-level chunk > 200 KB gzipped |
| Duplicate component rendering | Never render the same data-fetching component twice in the DOM — use CSS for show/hide |
| Images | Always use `next/image` for local assets; `<img>` for external URLs |
| Favicon | `frontend/app/favicon.ico` must exist (32×32 px) |

**Prevent CLS**: Reserve space for all loading regions using `<Skeleton>` before data arrives. Do not render empty placeholders and fill them later — use conditional rendering with pre-reserved height.

---

## 14. Onboarding & Tours

- The guided tour must **not auto-start** on every page load
- Check `localStorage.getItem('fin-eye-tour-done')` before showing the tour
- Set the key on Skip or completion: `localStorage.setItem('fin-eye-tour-done', '1')`
- The "Tour" trigger button must live **outside** any `<form>` element

---

## 15. Consistency Checklist (Before Every PR)

Run through this checklist before any UI pull request:

- [ ] No raw `<input>`, `<button>`, `<select>` — replaced with shadcn equivalents
- [ ] All interactive elements have visible focus rings (`focus-visible:ring-2 focus-visible:ring-sky-500`)
- [ ] Page exports unique `metadata` with `title` and `description`
- [ ] Page has exactly one `<h1>` that describes the current content
- [ ] No colour-only meaning — icons or text always accompany colour signals
- [ ] Loading → `<Skeleton>`, Error → `<Alert>`, Empty → descriptive empty state
- [ ] No hardcoded `localhost` URLs
- [ ] Primary button colour is `sky-600` (not blue, not indigo)
- [ ] Card border-radius is `rounded-xl` (not rounded-2xl, not rounded-lg)
- [ ] No new CSS variables or colours added outside `globals.css`
- [ ] `aria-current="page"` on active nav link
- [ ] `alt` text on all images

---

*Last updated: 2026-03-12 — derived from full Fin-Eye design review.*
