# Skill: Frontend Next.js Fintech (fin-eye specific)
# When to load: Before building or reviewing any frontend component, data fetching,
#               chart, or dashboard layout.

## Data Fetching Pattern (SWR)
fin-eye uses SWR for all dashboard data. Key conventions:
- Revalidate interval for GAS snapshot: 900s (matches backend Redis TTL)
- Always handle `isLoading`, `isValidating`, and `error` states explicitly — never render stale data silently
- Wrap each data section in its own ErrorBoundary so one failing fetch doesn't crash the dashboard

```typescript
const { data, error, isValidating } = useSWR(`/api/v1/gas/snapshot/${symbol}`, fetcher, {
  refreshInterval: 900_000,
  revalidateOnFocus: false,
});
```

## Color Semantics (DO NOT deviate from these)
| State | Tailwind Class | Hex |
|-------|---------------|-----|
| Bullish / Positive | `text-emerald-400` / `bg-emerald-400` | #34d399 |
| Bearish / Negative | `text-rose-400` / `bg-rose-400` | #fb7185 |
| Neutral / Mixed | `text-amber-400` / `bg-amber-400` | #fbbf24 |
| Loading / Updating | `text-sky-400` / `bg-sky-400` | #38bdf8 |

These must be consistent across StrategyCard, TimeframeGrid, RegimeWidget, and all badges.

## GAS Weather Label Colors
| Label | Color |
|-------|-------|
| Strong Tailwind | emerald |
| Mild Support | emerald (lighter) |
| Mixed Signals | amber |
| Headwind | rose (lighter) |
| High Instability | rose |

## Chart Standards (Recharts)
- Always use `ResponsiveContainer` — never hardcode pixel widths
- GAS history sparkline: simple LineChart, no axes, minimal grid, emerald line
- Macro score chart: AreaChart with gradient fill
- Confidence indicators: RadialBarChart or simple numeric with color coding

## Loading States
- Use skeleton loaders that match the shape of the final content (not generic spinners)
- Show `isValidating` state with a subtle spinning indicator on the component header, not a full overlay
- Never show a blank div — always show skeleton or previous data

## Empty States
Every data section must have a designed empty state:
- Icon (from lucide-react)
- Message explaining why it's empty
- CTA action where relevant (e.g. "Add a ticker to your watchlist")

## Component Conventions
- All score widgets accept a `score: number` and `label: string` prop
- Explain panels (ScoreExplainPanel) are collapsible by default
- Pro-only features show a lock icon + tooltip, not a disabled state
- Never use `any` for API response types — define typed DTOs matching backend Pydantic schemas
