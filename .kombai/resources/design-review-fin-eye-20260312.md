# Design Review Results: Fin-Eye — All Routes

**Review Date**: 2026-03-12
**Routes**: All routes (`/`, `/macro`, `/sentiment`, `/retail`, `/settings`, `/portfolios`, and all others)
**Focus Areas**: Visual Design · UX/Usability · Responsive/Mobile · Accessibility · Micro-interactions/Motion · Consistency · Performance
**Review Method**: Live browser inspection (screenshots) + static code analysis

---

## Summary

Fin-Eye has a solid dark-theme aesthetic and well-structured data components, but carries **significant systemic issues** across navigation, accessibility, consistency, and performance. The most critical problems are: a completely unusable mobile navigation (19 flat items with no hamburger), the `/sentiment` (Retail) page using undefined CSS variables that break its UI, duplicate `<h1>` tags across every page, and consistently high FCP (3–4.5s) and CLS scores that harm both UX and SEO. Fixing the navigation architecture and CSS token consistency would resolve roughly 40% of all issues in one sweep.

---

## Issues

| # | Issue | Criticality | Category | Location |
|---|-------|-------------|----------|----------|
| 1 | `/sentiment` (Retail) page uses undefined shadcn CSS variables (`bg-card`, `text-muted-foreground`, `bg-primary`, `ring-offset-background`, `border-input`) that don't exist in `globals.css`, causing invisible/broken UI elements (black cards, invisible buttons) | 🔴 Critical | Consistency | `frontend/app/sentiment/page.tsx:53-58, 84, 86, 99` |
| 2 | Mobile navigation is completely unusable at 390px — 19 flat nav items wrap across 5 rows alongside the logo, with no hamburger menu or drawer pattern | 🔴 Critical | Responsive/Mobile | `frontend/components/Nav.tsx:149-177` |
| 3 | CLS (Cumulative Layout Shift) score of **0.115–0.158** consistently exceeds the "good" threshold of 0.1 across all pages. Layout shifts occur during data loading on the dashboard | 🔴 Critical | Performance | `frontend/app/page.tsx:544-628` |
| 4 | FCP (First Contentful Paint) of **3.1–4.5s** on all pages — exceeds the 2.5s "good" threshold. TTFB at 2.5–2.8s indicates slow backend calls before render | 🔴 Critical | Performance | `frontend/app/layout.tsx` (global) |
| 5 | Missing `favicon.ico` causes a 404 error logged on every single page load — basic branding asset missing | 🔴 Critical | Visual Design | `frontend/app/` (missing `favicon.ico`) |
| 6 | Duplicate `<h1>` tags on every page: `layout.tsx` renders `<h1>Fin-Eye</h1>` in the global header while `page.tsx` renders `<h1>AAPL Intelligence</h1>` — violates WCAG 1.3.1 and harms SEO | 🔴 Critical | Accessibility | `frontend/app/layout.tsx:22`, `frontend/app/page.tsx:498` |
| 7 | 19 navigation items displayed in a single flat horizontal list with no grouping, categories, or visual hierarchy — extreme cognitive overload, especially for new users | 🟠 High | UX/Usability | `frontend/components/Nav.tsx:9-29` |
| 8 | No skip navigation link — keyboard users must tab through all 19 nav items before reaching main content on every page | 🟠 High | Accessibility | `frontend/app/layout.tsx:13-63` |
| 9 | Navigation links have no `aria-current="page"` attribute on the active item — screen readers cannot identify current page location | 🟠 High | Accessibility | `frontend/components/Nav.tsx:155-168` |
| 10 | `UserMenu` dropdown missing `role="menu"`, `role="menuitem"` ARIA attributes — not accessible via screen readers | 🟠 High | Accessibility | `frontend/components/Nav.tsx:63-146` |
| 11 | No per-page `<title>` tags — every route shows "Fin-Eye" as the browser tab title, preventing users from distinguishing tabs and harming SEO for individual routes | 🟠 High | UX/Usability | All `app/*/page.tsx` files |
| 12 | Guided tour auto-starts on **every** page load without checking `localStorage` for previous completion — intrusive and disruptive UX | 🟠 High | UX/Usability | `frontend/components/onboarding/GuidedTour.tsx` |
| 13 | `slate-500` text (`#64748b`) on `slate-950` background (`#020617`) achieves approximately **3.1:1** contrast ratio — fails WCAG AA requirement of 4.5:1 for normal text (used in subtitles, meta text, footer throughout the app) | 🟠 High | Accessibility | `frontend/app/layout.tsx:25`, `frontend/app/page.tsx:501`, multiple locations |
| 14 | Multiple custom interactive elements use `focus:outline-none` without providing any alternative visible focus indicator — keyboard users have no visible focus cue | 🟠 High | Accessibility | `frontend/app/page.tsx:514`, `frontend/app/settings/page.tsx:163`, multiple locations |
| 15 | Inconsistent primary action color: `sky-600` on Dashboard, `blue-600` on Settings/Portfolios, `indigo-600` on 2FA confirm button — no design token governing the primary brand color | 🟡 Medium | Consistency | `frontend/app/page.tsx:518`, `frontend/app/settings/page.tsx:926`, `frontend/app/settings/page.tsx:317` |
| 16 | Inconsistent border-radius across visually equivalent card/panel components: `rounded-md`, `rounded-lg`, `rounded-xl`, `rounded-2xl` all used for similar card containers | 🟡 Medium | Consistency | `frontend/app/page.tsx:570`, `frontend/app/macro/page.tsx:35`, `frontend/app/settings/page.tsx:31` |
| 17 | Inconsistent focus ring implementation: `focus:ring-1 focus:ring-sky-500` vs `focus:ring-2 focus:ring-ring` vs `focus:ring-1 focus:ring-blue-500` vs `focus:ring-1 focus:ring-red-500` used on similar input elements across pages | 🟡 Medium | Consistency | `frontend/app/page.tsx:514`, `frontend/app/sentiment/page.tsx:53`, `frontend/app/settings/page.tsx:162` |
| 18 | No skeleton loading UI on any page — loading states are either empty (`animate-pulse` text only) or completely blank, causing jarring layout shifts when data arrives | 🟡 Medium | UX/Usability | `frontend/app/page.tsx:544-547`, `frontend/app/portfolios/page.tsx:55` |
| 19 | `"Tour"` button is embedded inside the ticker search `<form>` element — pressing Enter in the text input can unexpectedly activate it; button should be placed outside the form | 🟡 Medium | UX/Usability | `frontend/app/page.tsx:523-532` |
| 20 | `settings/page.tsx` implements a custom `Toggle` switch component (lines 648–674) instead of using the existing shadcn `Switch` component — duplicates functionality and diverges from the design system | 🟡 Medium | Consistency | `frontend/app/settings/page.tsx:648-674` |
| 21 | `portfolios/page.tsx` hardcodes `http://localhost:8000` as the API base URL directly in component code — will fail in all non-local environments | 🟡 Medium | Performance | `frontend/app/portfolios/page.tsx:25, 34` |
| 22 | No Open Graph (`og:title`, `og:description`, `og:image`) or Twitter card meta tags on any route — poor social sharing experience and SEO penalty | 🟡 Medium | UX/Usability | `frontend/app/layout.tsx:8-11` |
| 23 | `GAS / MarketWeatherWidget` renders a prominent amber/orange gradient glow border around the entire card — this visual treatment lacks purpose and distracts from the data. No other widget uses this pattern | 🟡 Medium | Visual Design | `frontend/components/MarketWeatherWidget.tsx` |
| 24 | `WatchlistWidget` is rendered **twice** in the DOM on all screen sizes (once in `xl:hidden` div, once in `hidden xl:block aside`) — both mount, fetch data, and add event listeners regardless of visibility | 🟡 Medium | Performance | `frontend/app/page.tsx:485-491, 537-540` |
| 25 | `globals.css` has no design tokens defined — all colors, spacing, and typography values are hardcoded directly in component files as arbitrary Tailwind values with no centralized source of truth | 🟡 Medium | Consistency | `frontend/app/globals.css:1-7` |
| 26 | Navigation abbreviations are hard to understand at a glance: "Adv. Sentiment" is ambiguous; "Retail" without context doesn't communicate it means Reddit/social sentiment | ⚪ Low | UX/Usability | `frontend/components/Nav.tsx:17-19` |
| 27 | No page transition animations — navigating between routes switches abruptly without any visual continuity (fade, slide, etc.) | ⚪ Low | Micro-interactions/Motion | `frontend/app/layout.tsx:13-63` |
| 28 | Footer disclaimer text is duplicated — `layout.tsx` footer already contains the educational disclaimer, but some pages also include their own inline copy | ⚪ Low | Consistency | `frontend/app/layout.tsx:33-56`, `frontend/app/page.tsx:27-30` |
| 29 | `input` and `button` elements throughout the app use raw HTML elements rather than the shadcn `Input` and `Button` components — misses keyboard, accessibility, and theming benefits | ⚪ Low | Consistency | `frontend/app/page.tsx:509-532`, `frontend/app/portfolios/page.tsx:66-79` |

---

## Criticality Legend

- 🔴 **Critical**: Breaks functionality, fails accessibility standards, or severely harms core UX
- 🟠 **High**: Significantly impacts user experience, accessibility, or design quality
- 🟡 **Medium**: Noticeable issue that should be addressed in the next iteration
- ⚪ **Low**: Nice-to-have improvement

---

## Next Steps (Prioritized)

### 🔴 Immediate (Fix Before Launch)
1. **Fix `/sentiment` CSS variables** — Define shadcn design tokens in `globals.css` OR migrate the Retail page to use raw Tailwind classes consistent with the rest of the app
2. **Add mobile navigation** — Replace the flat 19-item nav with a grouped sidebar (desktop) + hamburger drawer (mobile). See wireframe in `.kombai/resources/lofi-wireframe-20260312-dashboard.html`
3. **Fix duplicate `<h1>`** — Demote layout header "Fin-Eye" to an `<h2>` or a styled `<p>` tag; keep the page-level heading as the single `<h1>`
4. **Add `favicon.ico`** — Place a 32×32 favicon in `frontend/app/` (Next.js App Router auto-serves it)
5. **Fix guided tour** — Check `localStorage.getItem('fin-eye-tour-completed')` before showing the tour; set it on completion/skip

### 🟠 High Priority (Sprint 1)
6. **Add `aria-current="page"`** to active nav item and `role="menu/menuitem"` to `UserMenu`
7. **Add skip navigation link** as the first focusable element in `layout.tsx`
8. **Add per-page metadata** (`title`, `description`) using Next.js 14's `generateMetadata` or static `metadata` export
9. **Fix contrast ratios** — Replace `text-slate-500` with `text-slate-400` on dark backgrounds for body/meta text
10. **Replace `focus:outline-none`** with `focus-visible:ring-2 focus-visible:ring-sky-500` on all interactive elements

### 🟡 Medium Priority (Sprint 2)
11. **Create design token system** — Add CSS variables to `globals.css` for `--color-primary`, `--radius-card`, `--color-text-muted` etc.
12. **Replace custom Toggle** in Settings with shadcn `Switch` component
13. **Add skeleton loading UIs** (shadcn `Skeleton`) for Dashboard, Macro, and Portfolio pages
14. **Fix environment-based API URLs** — Use `process.env.NEXT_PUBLIC_API_URL` instead of hardcoded localhost
15. **Move "Tour" button** outside the search form

### ⚪ Low Priority (Backlog)
16. Add page transition animations (CSS transitions or Framer Motion)
17. Rename ambiguous nav labels ("Adv. Sentiment" → "Advanced Sentiment", "Retail" → "Reddit Sentiment")
18. Migrate raw `input`/`button` elements to shadcn `Input` and `Button` components
19. Deduplicate the `WatchlistWidget` rendering (render once, use CSS for show/hide)
20. Consolidate disclaimer text — use `layout.tsx` footer as the single source of truth
