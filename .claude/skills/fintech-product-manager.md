# Skill: Fintech Product Manager
# When to load: When prioritizing features from todos.md, deciding what to build next,
#               designing the free/pro split, or measuring product success.

## Feature Prioritization Framework

Use this order of priority when deciding what to build next:

1. **Fixes broken things** (data feed failures, silent errors, GAS computing wrong)
2. **Removes blockers to activation** (user can't understand what GAS means → add tooltips)
3. **Removes blockers to conversion** (free user can't see value of Pro → improve upgrade gate UX)
4. **Improves retention** (daily return trigger → GAS history sparkline, regime change alerts)
5. **Nice to haves** (social features, gamification, white label)

The critical principle: **you cannot retain what you haven't activated. Fix activation before retention.**

## The Activation Funnel for fin-eye
A user is "activated" when they have completed all of:
1. Searched a ticker (saw a GAS score)
2. Opened the explain panel (understood what GAS means)
3. Visited the Macro or Sentiment page (explored beyond the default dashboard)
4. Added a watchlist item

Track these as events. The step with the biggest drop-off is your top priority.

## Free vs Pro Split Guidelines
The line between free and pro should be:
- **Free:** Core value proposition — GAS score, basic technical score, basic macro data, news sentiment
- **Pro:** Depth, history, and alerts — GAS history, advanced sentiment, backtesting, portfolio tools, email alerts, options/insider/short data

**Never gate things that are required to understand the product.** Tooltips, explanations, the learn hub — these must be free. Gating education kills activation.

## Metrics That Matter
| Metric | Target | Notes |
|--------|--------|-------|
| Time to first GAS score seen | < 60 seconds from signup | Activation speed |
| Explain panel open rate | > 40% of sessions | Comprehension proxy |
| Day 7 retention | > 30% | Industry benchmark for fintech |
| Free → Pro conversion | > 3% | Typical SaaS range |
| NPS | > 40 | Referral threshold |

## When to Say No
Say no to a feature request when:
- It requires significant backend work but has unclear user value (build a simpler version first)
- It duplicates something that already exists but is just undiscovered (fix discoverability first)
- It is requested by one user but would confuse many others (consider making it optional/pro-only)
- The todos.md item is 🟢 Nice-to-have and there are unresolved 🔴 Critical items

## Regulatory Awareness
fin-eye operates in a regulated space. Always keep in mind:
- GAS is a signal tool, not financial advice. Every data-driven page needs a risk disclaimer.
- Backtesting results must display "past performance does not guarantee future results"
- GDPR: users have the right to data deletion — the delete flow must work
- Cookie consent must gate analytics (not just show the banner)
- Do not use language like "guaranteed returns," "proven strategy," or "accurate predictions" anywhere in UI copy
